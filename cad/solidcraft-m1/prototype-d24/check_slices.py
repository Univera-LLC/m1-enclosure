"""Offline D2.4 slicer check: compare programmed beads with the installed socket rims.

Print XY = installed desk XZ; increasing print Z goes *into* the enclosure.
The material to keep out of the holes is taken from the released 3D sockets.
Cable overmoulds remain outside and are not used as aperture gauges.
"""
import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import numpy as np
import trimesh as tm

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
import manifold3d as md


def module(name, path):
    spec = spec_from_file_location(name, path)
    value = module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


slicer = module("d2_prusa", OUT.parent / "prototype-d2/check_slices.py")
paths = module("d22_gcode", OUT.parent / "prototype-d22/panel_toolpaths.py")
slicer.TMP = ROOT / "tmp/d24-slicer"
TO_DESK = np.array([[1000,0,0,0],[0,0,-1000,0],[0,1000,0,0],[0,0,0,1]])
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_meshes(path, names):
    scene = tm.load_scene(path, process=False)
    assert set(names) <= set(scene.graph.nodes_geometry)
    meshes = {}
    for name in names:
        pose, key = scene.graph[name]
        mesh = scene.geometry[key].copy()
        mesh.apply_transform(TO_DESK @ pose)
        meshes[name] = mesh
    return meshes


def solid_mesh(mesh):
    v, idx = np.unique(mesh.vertices.round(5), axis=0, return_inverse=True)
    solid = md.Manifold(md.Mesh64(np.ascontiguousarray(v), np.ascontiguousarray(idx[mesh.faces], dtype=np.uint64)))
    assert solid.status() == md.Error.NoError and solid.volume() > 0
    return solid


def read_solids(path,names):
    return {name:solid_mesh(mesh).rotate([-90,0,0]) for name,mesh in read_meshes(path,names).items()}


def complete_board():
    return solid_mesh(tm.load_mesh(OUT/"board-study/registered-board.stl",process=False))


def load_gauges(native):
    contract = read(OUT/"board-study/port-contract.json")["ports"]
    rims = {n: next(m for m in row["mesh_names"] if m.endswith("_lip")) for n,row in contract.items()}
    faces = read_meshes(OUT/"board-study/mac-board-reference.glb", rims.values())
    board = complete_board()
    by_port = {}
    for n,m in rims.items():
        bb=faces[m].bounds
        assert abs(bb[1,1]-contract[n]["source_lip_y_mm"]) < .001
        # The GLB uses open material partitions of this single connected solid.
        # Extract the region of the ENTIRE registered STL, including the tongue.
        lo=bb[0]-[1.,0,1.]; hi=bb[1]+[1.,.2,1.]; lo[1]=54.1
        cut=board ^ md.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
        assert not cut.is_empty()
        by_port[n]=cut.rotate([-90,0,0])
    power = read_solids(OUT/"geometry/socket.glb", native["groups"]["socket"])
    by_port["PD"] = md.Manifold.batch_boolean(list(power.values()), md.OpType.Add)
    centres = {n: np.asarray(row["axis_xz_mm"]) for n,row in contract.items()}
    for n,row in contract.items():
        assert abs(-by_port[n].bounding_box()[2] - row["source_lip_y_mm"]) < .001
    centres["PD"] = np.array(paths.CENTRES["PD IN"])
    return by_port, centres


def bead_gap(seg, polygon):
    """Signed clearance from the filled convex socket outline to G-code capsules."""
    p = np.asarray(polygon)
    if np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)) < 0:
        p = p[::-1]
    edges = np.roll(p,-1,axis=0)-p
    # AABB gives a proven lower bound, even for long diagonal infill segments.
    low = np.maximum(p.min(axis=0)-np.maximum(seg[:,:2],seg[:,2:4]),0)
    high = np.maximum(np.minimum(seg[:,:2],seg[:,2:4])-p.max(axis=0),0)
    lower = np.linalg.norm(low+high,axis=1)-seg[:,4]/2
    best = np.inf
    for limit in (1., 3., np.inf):
        cand = seg[lower<=limit]
        if len(cand):
            a = cand[:,:2]; d = cand[:,2:4]-a; sq = (d*d).sum(axis=1)
            lo=np.zeros(len(a)); hi=np.ones(len(a)); valid=np.ones(len(a),bool)
            distance = np.full(len(a),np.inf)
            for v,e in zip(p,edges):
                d0 = a-v
                at = e[0]*d0[:,1]-e[1]*d0[:,0]
                slope = e[0]*d[:,1]-e[1]*d[:,0]
                pos, neg = slope>1e-10, slope < -1e-10
                valid &= pos | neg | (at>=-1e-10)
                lo[pos] = np.maximum(lo[pos],-at[pos]/slope[pos])
                hi[neg] = np.minimum(hi[neg],-at[neg]/slope[neg])
                # Closest features of two nonintersecting segments include an endpoint.
                t=np.clip(-np.sum(d0*d,axis=1)/sq,0,1)
                distance=np.minimum(distance,np.linalg.norm(d0+t[:,None]*d,axis=1))
                for endpoint in (d0,d0+d):
                    u=np.clip(endpoint@e/(e@e),0,1)
                    distance=np.minimum(distance,np.linalg.norm(endpoint-u[:,None]*e,axis=1))
            distance[valid & (lo<=hi)] = 0.
            best = float(np.min(distance-cand[:,4]/2))
            if best <= limit:
                break
    assert np.isfinite(best)
    return best


def gauge_silhouette(solid, ymin, ymax, play):
    # Complete projection of material which can enter this deposited layer,
    # over its thickness and the full independent limits of axial panel play.
    cut = solid.trim_by_plane([0,0,1], -ymax).trim_by_plane([0,0,-1], ymin)
    if cut.is_empty() or cut.volume() < 1e-8:
        return None
    outline = cut.project().hull()  # conservative, e.g. for shell ears
    swept = md.CrossSection.batch_hull([outline.translate([-dx,-dz])
        for dx in play[:,0] for dz in play[:,2]])
    return np.asarray(swept.to_polygons()[0])


def deposited_web(seg, xz, window):
    # A conservative lower bound: use the actual bead radius perpendicular
    # to X (projected width is greater for slanted traces). Merge overlaps.
    a,b=seg[:,:2],seg[:,2:4]
    mask=(a[:,1]>xz[1])!=(b[:,1]>xz[1]); a,b=a[mask],b[mask]
    x=a[:,0]+(b[:,0]-a[:,0])*(xz[1]-a[:,1])/(b[:,1]-a[:,1]); w=seg[mask,4]
    intervals=sorted((max(xz[0]-window,c-d/2),min(xz[0]+window,c+d/2))
                     for c,d in zip(x,w) if abs(c-xz[0])<window)
    combined=[]
    for lo,hi in intervals:
        if combined and lo<=combined[-1][1]: combined[-1][1]=max(hi,combined[-1][1])
        else: combined.append([lo,hi])
    width=sum(b-a for a,b in combined)
    assert len(intervals)>=2 and width>.75,(xz,intervals,width)
    return dict(extrusion_crossings=len(intervals), material_width_lower_bound_mm=round(width,4))


def assessment(gcode):
    native=read(OUT/"cad-validation.json")
    name,=native["groups"]["panel"]; box=native["bodies"][name]["bbox"]
    panel_face=box["max"][1]; mid=(np.array(box["min"])+box["max"])[[0,2]]/2
    # Includes rigid-body rock at the port field, not just a parallel shift.
    play=np.array(read(OUT/"mount-fit.json")["field_motion_conservative_xyz_mm"])
    assert play.shape==(2,3) and np.all(play[0]<=0) and np.all(play[1]>=0)
    solids, centres=load_gauges(native)
    layers=paths.deposited(gcode)
    assert list(layers)==[.2,.4,.6,.8,1.,1.2,1.4,1.6,1.8]
    result={};z0=0.;origin=None;nseg=0
    for z,layer in layers.items():
        rings=layer["rings"]
        outer=max(range(len(rings)),key=lambda i:np.ptp(rings[i][0][:,0]))
        boundary=rings[outer][0]
        if origin is None:
            assert np.all(np.ptp(boundary,axis=0)>[160.,31.])
            origin=(boundary.min(axis=0)+boundary.max(axis=0))/2-mid
        seg=np.array(layer["segments"]);seg[:,:2]-=origin;seg[:,2:4]-=origin
        nseg+=len(seg)
        ids={}
        for n,at in centres.items():
            ids[n]=[i for i,(ring,*_) in enumerate(rings) if i!=outer and paths.inside(*(origin+at),ring)]
        # All eight must be separate at the bed; a blind component recess
        # behind the commercial PD socket may communicate with its foot.
        checked = [n for n in ids if z<=.4 or (z<=1.4 and n!="PD")]
        assert all(len(ids[n])==1 for n in checked) and len({ids[n][0] for n in checked})==len(checked),(z,ids)
        gaps={}
        for n,solid in solids.items():
            p=gauge_silhouette(solid,panel_face+play[0,1]-z,panel_face+play[1,1]-z0,play)
            if p is None:
                assert z>1.4,(z,n,"no rim in axial slab")
                continue
            gap=bead_gap(seg,p)
            assert gap>.10,(z,n,gap,"less than 0.10 mm between a programmed bead and the seated rim")
            gaps[n]=round(gap,4)
        result[z]={"separate_socket_holes":len({v[0] for v in ids.values() if len(v)==1}),
                   "socket_to_bead_mm":gaps}
        if z<=1.4:
            result[z]["deposited_webs"]={label:deposited_web(seg,(centres[a]+centres[b])/2,window)
                for label,a,b,window in [("USB-A pair","A1","A2",1.25),("Thunderbolt pair","TB1","TB2",1.4)]}
        z0=z
    return dict(positive_extrusion_segments=nseg,installed_field_motion_xyz_bounds_mm=play.tolist(),
                layer_results=result,minimum_socket_to_bead_mm={n:min(row["socket_to_bead_mm"][n] for row in result.values() if n in row["socket_to_bead_mm"]) for n in solids},
                scope="Convex XZ projection of the exported socket rim over each full G-code layer. Conservative field motion at the port includes permitted translation and tilt of the closed rigid panel. Programmed bead widths; physical tolerance and force are not measured.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--slicer",type=Path,default=slicer.DEFAULT)
    exe=p.parse_args().slicer.resolve();cfg,vendor=slicer.config(exe)
    folder=OUT/"print"; stls=read(folder/"stl-checks.json");refs=stls["parts"]
    fit_hash=sha256((OUT/"fit-validation.json").read_bytes()).hexdigest()
    cad_hash=sha256((OUT/"cad-validation.json").read_bytes()).hexdigest()
    assert stls["fit_report_sha256"]==fit_hash and stls["cad_report_sha256"]==cad_hash
    assert len(refs)==8 and refs["02-flat-rear-panel.stl"]["bed_face"]["side"]=="exterior"
    parts={}
    for name,record in refs.items():
        info=slicer.slice_one(exe,cfg,folder/name)
        assert not info["warnings"] and info["input_sha256"]==record["sha256"],(name,info)
        parts[name]=info
    assert parts["02-flat-rear-panel.stl"]["bridge_regions"]==0
    paths_report=assessment((slicer.TMP/"02-flat-rear-panel.gcode").read_text(encoding="utf-8"))
    base="03-monolithic-base.stl";sample=parts[base];seams={sample["seam_position"]:sample}
    for seam in ("aligned","rear"):
        if seam not in seams:
            seams[seam]=slicer.slice_one(exe,cfg,folder/base,seam)
    assert len(seams)==3 and all(not r["warnings"] and r["input_sha256"]==refs[base]["sha256"] for r in seams.values())
    out=dict(revision="D2.4",slicer=subprocess.check_output([str(exe),"--help"],encoding="utf-8",errors="replace").splitlines()[0],
             presets=slicer.PRESETS,vendor_ini_sha256=vendor,parts=parts,full_base_seam_checks=seams,extrusion_paths=paths_report,
             fit_report_sha256=fit_hash,cad_report_sha256=cad_hash,
             scope="Ender-3 Pro / 0.4-mm nozzle / 0.20 mm / PETG, supports off; faceplate 100% Rectilinear, Classic. No hardware used. Machine-specific G-code is not distributed.")
    (folder/"slice-checks.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(paths_report["minimum_socket_to_bead_mm"])


if __name__=="__main__":
    main()
