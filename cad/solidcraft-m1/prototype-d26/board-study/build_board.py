"""Build the D2.6 registered physical board reference (STL + glTF) with photographed USB-A/audio T-block and protruding collar."""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
import trimesh as tm
from port_faces import HERE, DATA, ROOT_Y, FLOOR_Y, md, grouped, shared_shields, contract

SOURCE = HERE.parents[1] / 'prototype-d23/review/reference/mac-board-reference.glb'
DEST = HERE / 'mac-board-reference.glb'
STL = HERE / 'registered-board.stl'
CAP = 'oem__ports__macsolder__D26_common_rear'
MUTABLE = {'oem__ports__macmetal__SOURCE_20_ports_macmetal_oem',
           'oem__logic__maccomponent__SOURCE_20_logic_maccomponent_oem',
           'oem__logic__macfr4__SOURCE_20_logic_macfr4_oem'}
GROWN = 'owner-23-crest-field'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unpack(path):
    buf = Path(path).read_bytes()
    magic, vers, total, js, kind = struct.unpack_from('<4sIII4s', buf)
    assert (magic, vers, total, kind) == (b'glTF', 2, len(buf), b'JSON')
    hdr = json.loads(buf[20:20 + js])
    length, kind = struct.unpack_from('<I4s', buf, 20 + js)
    assert kind == b'BIN\0'
    return hdr, bytearray(buf[28 + js:28 + js + length])


def acc(h, b, i):
    a = h['accessors'][i]
    v = h['bufferViews'][a['bufferView']]
    out = np.frombuffer(b, dtype={5126: '<f4', 5125: '<u4', 5123: '<u2'}[a['componentType']],
                        offset=a.get('byteOffset', 0) + v.get('byteOffset', 0),
                        count=a['count'] * (3 if a['type'] == 'VEC3' else 1))
    return out.reshape(-1, 3) if a['type'] == 'VEC3' else out


def mesh_data(h, b, n):
    p = h['meshes'][n['mesh']]['primitives'][0]
    f = acc(h, b, p['indices']).reshape(-1, 3)
    return tuple(acc(h, b, p['attributes'][k])[f].astype(float) for k in ('POSITION', 'NORMAL'))


def desk(gl):
    return gl[:, :, [0, 2, 1]] * np.array([1000., -1000., 1000.])


def gl(desk_points):
    return (desk_points[:, :, [0, 2, 1]] * np.array([.001, .001, -.001])).astype('<f4')


def is_physical(name):
    return '__SOURCE_20_' in name or name.endswith(GROWN) or '__D24_' in name or '__D26_' in name


def manifold_from(tris, labels=None):
    v, f = np.unique(np.round(tris.reshape(-1, 3), 5), axis=0, return_inverse=True)
    args = {}
    if labels:
        start = md.Manifold.reserve_ids(len(labels))
        ids = np.arange(start, start + len(labels), dtype=np.uint32)
        ends = np.cumsum([0] + [3 * n for n in labels.values()]).astype(np.uint64)
        args = {'run_index': ends, 'run_original_id': ids, 'face_id': np.arange(len(tris), dtype=np.uint64)}
    obj = md.Manifold(md.Mesh64(np.ascontiguousarray(v), f.reshape(-1, 3).astype(np.uint64), **args))
    assert obj.status() == md.Error.NoError and obj.volume() > 0
    return (obj, dict(zip(map(int, ids), labels))) if labels else obj


def source_body(h, b):
    parts = {n['name']: desk(mesh_data(h, b, n)[0]) for n in h['nodes'] if is_physical(n['name'])}
    assert {n for n, t in parts.items() if t[:, :, 1].max() > ROOT_Y} == MUTABLE
    return manifold_from(np.concatenate(list(parts.values())), {n: len(t) for n, t in parts.items()})


def tagged_result():
    h, b = unpack(SOURCE)
    old, tags = source_body(h, b)
    cut = md.Manifold.cube([170., 12., 44.]).translate([-85., ROOT_Y, 5.]).as_original()
    tags[cut.original_id()] = CAP
    cols = [old - cut]
    for name in DATA:
        for label, s in grouped(name).items():
            assert s.status() == md.Error.NoError and s.volume() > 0, label
            tags[s.original_id()] = label
            cols.append(s)
    for label, s in shared_shields().items():
        assert s.status() == md.Error.NoError and s.volume() > 0, label
        tags[s.original_id()] = label
        cols.append(s)
    result = md.Manifold.batch_boolean(cols, md.OpType.Add).simplify(.00001)
    assert result.status() == md.Error.NoError and len(result.decompose()) == 1
    return old, result, tags


def split_mesh(body, tags):
    m = body.to_mesh64()
    t = np.asarray(m.vert_properties)[:, :3][np.asarray(m.tri_verts)]
    out = {}
    for rid, lo, hi in zip(m.run_original_id, m.run_index, m.run_index[1:]):
        if hi > lo:
            out.setdefault(tags[rid], []).append(t[lo // 3:hi // 3])
    return {k: np.concatenate(v) for k, v in out.items()}


def put_acc(h, b, arr, kind):
    arr = np.ascontiguousarray(arr)
    off = len(b)
    assert off % 4 == 0
    flat = arr.reshape(-1, 3) if kind == 'VEC3' else arr.reshape(-1, 1)
    h['bufferViews'].append({'buffer': 0, 'byteOffset': off, 'byteLength': arr.nbytes,
                             'target': 34962 if kind == 'VEC3' else 34963})
    h['accessors'].append({'bufferView': len(h['bufferViews']) - 1,
                           'componentType': 5126 if kind == 'VEC3' else 5125,
                           'count': len(flat), 'type': kind,
                           'min': flat.min(axis=0).tolist(), 'max': flat.max(axis=0).tolist()})
    b.extend(arr.tobytes())
    return len(h['accessors']) - 1


def weld_triangles(tri):
    tri = np.round(tri, 5)
    same = (tri == np.roll(tri, 1, axis=1)).all(axis=2).any(axis=1)
    return tri[~same]


def write_mesh(h, b, tri, mid, olddata):
    tri = gl(weld_triangles(tri))
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(cross, axis=1)
    valid = ln > 0
    tri, cross, ln = tri[valid], cross[valid], ln[valid]
    n = (cross / ln[:, None])[:, None, :].repeat(3, axis=1)
    if olddata:
        a, nn = olddata
        vv = a.reshape(-1, 3)
        aa = np.cross(a[:, 1] - a[:, 0], a[:, 2] - a[:, 0])
        aa /= np.linalg.norm(aa, axis=1)[:, None]
        lookup = {tuple(v): nv for v, nv in zip(np.c_[vv, aa.repeat(3, axis=0)].round(6), nn.reshape(-1, 3))}
        flat = n.reshape(-1, 3)
        for i, k in enumerate(np.c_[tri.reshape(-1, 3), flat].round(6)):
            saved = lookup.get(tuple(k))
            if saved is not None:
                flat[i] = saved
    values, ix = np.unique(np.c_[tri.reshape(-1, 3), n.reshape(-1, 3)].astype('<f4'), axis=0, return_inverse=True)
    return {'attributes': {'POSITION': put_acc(h, b, values[:, :3], 'VEC3'),
                           'NORMAL': put_acc(h, b, values[:, 3:], 'VEC3')},
            'indices': put_acc(h, b, ix.astype('<u4'), 'SCALAR'), 'mode': 4, 'material': mid}


def write_glb(groups):
    h, b = unpack(SOURCE)
    oldnodes = {n['name']: n for n in h['nodes']}
    mats = {m['name']: i for i, m in enumerate(h['materials'])}
    old_data = {name: mesh_data(h, b, oldnodes[name]) for name in MUTABLE}
    for name, tri in sorted(groups.items()):
        if name in oldnodes and name not in MUTABLE:
            continue
        prim = write_mesh(h, b, tri, mats[name.split('__')[2]], old_data.get(name))
        if name in oldnodes:
            h['meshes'][oldnodes[name]['mesh']]['primitives'] = [prim]
        else:
            h['meshes'].append({'name': name, 'primitives': [prim]})
            h['nodes'].append({'name': name, 'mesh': len(h['meshes']) - 1,
                               'extras': {'role': 'connector entrance', 'status': 'DOCUMENTED photo-updated geometry / SOURCE registration'}})
            h['scenes'][0]['nodes'].append(len(h['nodes']) - 1)
    h['asset']['extras']['port_study'] = {
        'revision': 'D2.6',
        'registration': 'same unscaled desk coordinates',
        'geometry_scope': 'Photo-updated USB-A/audio inverted-T block, protruding Ø5.0 mm audio collar, silver T-bridge, HDMI/RJ bezels and shared TB shield.',
    }
    h['buffers'][0]['byteLength'] = len(b)
    data = json.dumps(h, ensure_ascii=False, separators=(',', ':')).encode()
    data += b' ' * (-len(data) % 4)
    b += b'\0' * (-len(b) % 4)
    DEST.write_bytes(struct.pack('<4sIII4s', b'glTF', 2, 28 + len(data) + len(b), len(data), b'JSON') +
                     data + struct.pack('<I4s', len(b), b'BIN\0') + b)


def registered_body(path=STL):
    """Public CAD helper: closed, desk-mm registered physical board, no photo overlays."""
    m = tm.load_mesh(path, process=False)
    return manifold_from(m.triangles)


def run():
    old, body, tags = tagged_result()
    groups = split_mesh(body, tags)
    assert set(groups).issuperset(MUTABLE | {CAP})
    write_glb(groups)
    mesh = body.to_mesh64()
    t = weld_triangles(np.asarray(mesh.vert_properties)[:, :3][np.asarray(mesh.tri_verts)])
    v, f = np.unique(t.reshape(-1, 3), axis=0, return_inverse=True)
    tm.Trimesh(v, f.reshape(-1, 3), process=False).export(STL)
    (HERE / 'port-contract.json').write_text(json.dumps(contract(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Wrote', DEST.name, DEST.stat().st_size, 'bytes;', STL.name, STL.stat().st_size, 'bytes')


if __name__ == '__main__':
    run()
