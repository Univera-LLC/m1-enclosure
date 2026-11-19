"""D2.2: top-loading rear I/O plate. Authoritative desk coordinates: mm, +Y rear, +Z up."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import trimesh

OUT=Path(__file__).resolve().parent
CAD=OUT.parent
OLD=CAD/"prototype-d2"
WORK=CAD.parents[1]/"tmp/d22-native"
sys.path.insert(0,str(OLD))
import build_d2 as old
# The shared stack loads several older directories. Revision-local helpers
# (notably the mirrored first-layer contour check) must resolve first.
sys.path.insert(0,str(OUT))
base, rear, power, d1 = old.base, old.rear, old.power, old.d1
dump, digest, operations_hash = old.dump, old.digest, old.operations_hash
REVISION="D2.2"
PANEL="D22_FLAT_IO_PLATE"
FILES={**old.FILES,"panel":[PANEL]}
NAMES=sum((list(v) for v in FILES.values()),[])
PLASTICS=[base.BASE,base.LID,PANEL,power.HOLDER,base.BLANK]
BOARD=OLD/"photo-study/mac-board-reference.glb"

def shared():
    return [("One-piece base and independent cover",base.operations()),("Power saddle and two modules",power.operations())]

def features():
    import plate_d22, mount_d22
    assert plate_d22.PANEL==PANEL
    return shared()+[("Face-down rear plate and eight sockets",plate_d22.operations()),
                    ("Open-top side guides, lower seat and lid retention",mount_d22.operations())]

def seed():
    # Expensive unchanged CAD operations, in a private file. Every revision to
    # their commands invalidates the seed, so it also works for trial fits.
    groups=shared();WORK.mkdir(exist_ok=True,parents=True)
    path=WORK/("base-power-"+operations_hash(groups)[:20]+".sc")
    if not path.is_file():
        with d1.c.SolidCraftMCP(timeout=360) as session:
            for label,ops in groups:
                print(label,len(ops),flush=True)
                d1.v.batch(session,ops)
            check=d1.v.measures(session)
            assert set(check)==set(NAMES)-{PANEL}
            session.call("save",{"path":str(path)})
    return path

def run():
    groups=features()
    (OUT/"geometry").mkdir(exist_ok=True)
    exports={"d22-printable.step":PLASTICS,"d22-assembly.step":NAMES}
    prior=json.loads((OLD/"cad-validation.json").read_text(encoding="utf-8"))
    owner=json.loads((OLD/"photo-study/solidcraft-readback.json").read_text(encoding="utf-8"))
    assert owner["reference_glb_sha256"]==digest(BOARD)
    with d1.c.SolidCraftMCP(design=seed(),timeout=360) as session:
        for label,ops in groups[2:]:
            print(label,len(ops),flush=True)
            d1.v.batch(session,ops)
        native=d1.v.measures(session)
        assert set(native)==set(NAMES) and all(v["closed"] and v["volume_mm3"]>0 for v in native.values())
        timeline=session.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not any(f.get("error") or f.get("warning") for f in timeline)
        for group,names in FILES.items():
            d1.v.batch(session,[d1.cmd("appearance.assign",bodies=names,color=old.COLORS.get(group,"#9da5a5")),
                d1.cmd("file.export",path=str(OUT/"geometry"/(group+".glb")),bodies=names,quality="standard")])
        for name,bodies in exports.items():session.call("export",{"path":str(OUT/name),"bodies":bodies})
        d1.v.batch(session,[d1.cmd("file.insert_mesh",path=str(BOARD),origin=False,name="Owner Mac — photo reference, antennas detached")])
        session.call("save",{"path":str(OUT/"d22-workbench.sc")})
    reads={}
    def compare(got,want):
        assert got["closed"] and np.isclose(got["volume_mm3"],want["volume_mm3"],rtol=.00006,atol=.0003)
        assert all(np.allclose(got["bbox"][k],want["bbox"][k],atol=.003,rtol=0) for k in ("min","max"))
    for name,names in exports.items():
        with d1.c.SolidCraftMCP(design=OUT/name,timeout=360) as session: got=d1.v.measures(session)
        assert set(got)==set(names)
        for n in names:compare(got[n],native[n])
        reads[name]=len(names)
    with d1.c.SolidCraftMCP(design=OUT/"d22-workbench.sc",timeout=360) as session:
        got=d1.v.measures(session)
        tree=session.json("inspect_design",{"measure":False,"sketches":False})
    assert not any(f.get("error") or f.get("warning") for f in tree["timeline"])
    scene=trimesh.load_scene(BOARD,process=False)
    assert set(got)==set(NAMES)|set(scene.graph.nodes_geometry)
    desk=np.array([[1000,0,0,0],[0,0,-1000,0],[0,1000,0,0],[0,0,0,1]])
    for n in scene.graph.nodes_geometry:
        pose,key=scene.graph[n];m=scene.geometry[key].copy();m.apply_transform(desk@pose)
        assert np.allclose(m.bounds,[got[n]["bbox"][k] for k in ("min","max")],rtol=0,atol=.001),n
    for n in NAMES:compare(got[n],native[n])
    reads["d22-workbench.sc"]=len(got)
    unchanged=sorted(set(NAMES)-{base.BASE,base.LID,PANEL})
    for n in unchanged:compare(native[n],prior["bodies"][n])
    dump(OUT/"cad-validation.json",dict(variant=REVISION+" / top loading",revision=REVISION,date="2026-11-18",
        units="desk mm",features=len(timeline),warnings=[],groups=FILES,bodies=native,print_bodies=PLASTICS,
        operations_sha256=operations_hash(groups),unchanged_from_d21=unchanged,readback=reads,
        files_sha256={name:digest(OUT/name) for name in reads},owner_board_sha256=digest(BOARD),fitted_antenna_references=0))
    print(reads,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--seed",action="store_true");args=p.parse_args()
    if args.seed:print(seed())
    else:run()
