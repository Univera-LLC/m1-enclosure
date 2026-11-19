"""Build the D2.7 cold-fit candidate alongside an immutable verified D2.6 build."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVISION = 'D2.7'
NEW = {'01-power-saddle.stl', '03-monolithic-base.stl',
       '04-vented-lid.stl', '06-board-datum-strip.stl', '08-lid-stop-sample.stl'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(baseline, out, geometry):
    s = geometry.d26
    d1 = s.d1
    groups = geometry.groups()
    dest = out / 'geometry'
    dest.mkdir()
    exports = {'d27-printable.step': s.PLASTICS, 'd27-assembly.step': s.NAMES}
    with d1.c.SolidCraftMCP(timeout=360) as cad:
        for label, ops in groups:
            print(label, len(ops), flush=True)
            d1.v.batch(cad, ops)
        bodies = d1.v.measures(cad)
        assert set(bodies) == set(s.NAMES) and all(v['closed'] for v in bodies.values())
        for label, names in s.FILES.items():
            d1.v.batch(cad, [d1.cmd('file.export', path=str(dest / (label + '.glb')),
                                   bodies=names, quality='standard')])
        for name, names in exports.items():
            cad.call('export', {'path': str(out / name), 'bodies': names})
        board = baseline / 'board-study/mac-board-reference.glb'
        d1.v.batch(cad, [d1.cmd('file.insert_mesh', path=str(board), origin=False,
                               name='Registered SOURCE Mac with photographed connector mouths')])
        cad.call('save', {'path': str(out / 'd27-workbench.sc')})

    def compare(a, b):
        assert a['closed'] and np.isclose(a['volume_mm3'], b['volume_mm3'], rtol=.00006, atol=.0003)
        assert all(np.allclose(a['bbox'][k], b['bbox'][k], atol=.003, rtol=0) for k in ('min', 'max'))

    counts = {}
    for name, names in {**exports, 'd27-workbench.sc': s.NAMES}.items():
        with d1.c.SolidCraftMCP(design=out / name, timeout=360) as cad:
            got = d1.v.measures(cad)
            if name.endswith('.sc'):
                timeline = cad.json('inspect_design', {'measure': False, 'sketches': False})['timeline']
                assert not any(op.get('error') or op.get('warning') for op in timeline)
                assert set(got) == set(names) | set(trimesh.load_scene(board).graph.nodes_geometry)
            else:
                assert set(got) == set(names)
            for n in names:
                compare(got[n], bodies[n])
            counts[name] = len(got)
    report = {'revision': REVISION, 'basis': 'desk mm; +Y rear, +Z up', 'features': len(timeline),
              'baseline_cad_report_sha256': digest(baseline / 'cad-validation.json'),
              'owner_board_sha256': digest(board), 'port_contract_sha256': digest(board.with_name('port-contract.json')),
              'groups': s.FILES, 'print_bodies': s.PLASTICS, 'readback': counts, 'bodies': bodies,
              'files_sha256': {n: digest(out / n) for n in counts}}
    write(out / 'cad-validation.json', report)
    print('Native readback:', counts, flush=True)


def print_parts(baseline, out, before, after, qa, slicer):
    folder = out / 'print'
    folder.mkdir()
    baseline_prints = read(baseline / 'print/stl-checks.json')['parts']
    baseline_slices = read(baseline / 'print/slice-checks.json')['parts']
    engine = slicer[0]
    engine.TMP = out / '.slice'
    cfg, vendor = engine.config(slicer[1])
    rows, slices = {}, {}
    for name, record in baseline_prints.items():
        body = record['body']
        a, b = before[body], after[body]
        if crop := record['crop_desk_mm']:
            keep = qa.rect(*crop)
            a, b = a ^ keep, b ^ keep
        target = folder / name
        if name in NEW:
            solid = b.rotate(record['rotation_xyz_deg'])
            lo, hi = qa.bounds(solid)
            mesh = solid.translate((-lo).tolist()).to_mesh64()
            trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False).export(target)
            result = trimesh.load_mesh(target, process=True)
            assert result.is_volume and result.body_count == 1, name
            assert np.allclose(result.bounds, [[0., 0., 0.], hi-lo], atol=.0002, rtol=0), name
            assert np.isclose(result.volume, b.volume(), rtol=.0001, atol=.0001), name
            sliced = engine.slice_one(slicer[1], cfg, target)
            assert not sliced['warnings'] and sliced['input_sha256'] == digest(target), sliced
            print(name, round(b.volume(), 2), 'mm³,', sliced['layers'], 'layers', flush=True)
        else:
            delta = (a-b).volume() + (b-a).volume()
            assert delta < .0004, (name, delta)
            shutil.copyfile(baseline / 'print' / name, target)
            sliced = baseline_slices[name]
            assert digest(target) == record['sha256'] == sliced['input_sha256'], name
        shared = name not in NEW
        rows[name] = {**(record if shared else {k: record[k] for k in ('body', 'rotation_xyz_deg', 'crop_desk_mm', 'closed_shells')}),
                      'size_xyz_mm': np.ptp(qa.bounds(b.rotate(record['rotation_xyz_deg'])), axis=0).round(3).tolist(),
                      'volume_mm3': round(b.volume(), 3), 'baseline_volume_mm3': record['volume_mm3'],
                      'identical_d26_stl': shared, 'sha256': digest(target)}
        slices[name] = {**sliced, 'reused_d26_toolpath_check': shared}
    provenance = {'revision': REVISION, 'physical_status': 'NOT TESTED',
                  'cad_report_sha256': digest(out / 'cad-validation.json'),
                  'fit_report_sha256': digest(out / 'fit-validation.json')}
    write(folder / 'stl-checks.json', {**provenance, 'parts': rows})
    write(folder / 'slice-checks.json', {**provenance, 'presets': engine.PRESETS, 'vendor_ini_sha256': vendor,
          'panel_layer_height_mm': .10, 'panel_first_layer_height_mm': .10,
          'scope': 'Five updated STLs sliced at 0.20 mm; three exact D2.6 STLs retain their verified slices. No supports.',
          'parts': slices})


def kit(out):
    for ref, names in ((HERE, ('FIT-FIRST.md', 'CREDITS.txt')), (ROOT, ('LICENSE', 'THIRD_PARTY.md'))):
        for name in names:
            shutil.copyfile(ref / name, out / name)
    notes = [out / name for name in ('FIT-FIRST.md', 'CREDITS.txt', 'LICENSE', 'THIRD_PARTY.md',
                                     'print/stl-checks.json', 'print/slice-checks.json')]
    for name, parts in [('first-fit', {'01', '02', '06', '07', '08'}),
                        ('cold-fit-kit', {'01', '02', '03', '04', '05'})]:
        members = [p for p in sorted((out / 'print').glob('*.stl')) if p.name[:2] in parts] + notes
        assert len(members) == 11
        path = out / f'd2.7-{name}.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for p in members:
                archive.write(p, p.name)
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            assert all(hashlib.sha256(archive.read(p.name)).hexdigest() == digest(p) for p in members)


def finish(source, out, geometry, prusa):
    from check_d27 import assess
    import check_geometry as qa
    import check_slices

    report = read(out / 'cad-validation.json')
    assert all(digest(out / name) == sha for name, sha in report['files_sha256'].items())
    assert digest(source / 'cad-validation.json') == report['baseline_cad_report_sha256']
    before = qa.parts()
    after = qa.qa.k.load_parts(out, geometry.d26.FILES)
    proof = assess(before, after)
    proof.update(cad_report_sha256=digest(out / 'cad-validation.json'), owner_board_sha256=report['owner_board_sha256'],
                 specialized={k: v['comparisons'] for k, v in proof['details'].items()})
    for name, result in proof['details'].items():
        write(out / (name + '-fit.json'), {**result, 'cad_report_sha256': proof['cad_report_sha256']})
    write(out / 'fit-validation.json', proof)
    print('Digital fit:', proof['comparisons'], 'comparisons', flush=True)
    print_parts(source, out, before, after, qa, (check_slices.slicer, prusa))
    for name in ('board-study/mac-board-reference.glb', 'board-study/port-contract.json',
                 'connector-section.svg', 'd25-vs-d26-usb-audio-comparison.svg', 'fascia-contract.json',
                 'reference-crosscheck.json'):
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, path)
    kit(out)
    write(out / 'verified.json', {'revision': REVISION, 'status': 'passed', 'physical_status': 'NOT TESTED',
          'sha256': {p.relative_to(out).as_posix(): digest(p) for p in sorted(out.rglob('*'))
                     if p.is_file() and '.slice' not in p.relative_to(out).parts}})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True, help='verified D2.6 build directory')
    ap.add_argument('--output', type=Path, required=True, help='new directory under build/')
    args = ap.parse_args()
    baseline, out = args.baseline.resolve(), args.output.resolve()
    local_builds = ROOT / 'build'
    if not baseline.is_relative_to(local_builds) or not out.is_relative_to(local_builds) \
            or out == local_builds or out.is_relative_to(baseline):
        ap.error('choose a verified baseline and a separate new output directory under build/')
    sys.path.insert(0, str(ROOT / 'tools'))
    import cad_build
    cad_build.verify(baseline)
    solid, prusa, _ = cad_build.toolchain()
    os.environ['SOLIDCRAFT_CLI'] = str(solid)
    source = baseline / 'workspace' / cad_build.ACTIVE
    sys.path.insert(0, str(source))
    import geometry
    import solidcraft_mcp

    # The staged client defaults to the baseline's workspace. Authorize the
    # common build folder for this process so it can also write the candidate.
    assert geometry.d1.c.SolidCraftMCP is solidcraft_mcp.SolidCraftMCP
    solidcraft_mcp.WORKSPACE = local_builds
    out.mkdir(parents=True, exist_ok=False)
    build(source, out, geometry)
    finish(source, out, geometry, prusa)


if __name__ == '__main__':
    main()
