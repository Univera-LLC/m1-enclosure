"""D2.6: thickened flat rear panel (0.80/0.90/0.40 mm pocket walls), unified USB-A/audio T-pocket, Ø5.90 audio passage, and widened bezel reliefs. Desk mm, +Y rear, +Z up."""
import argparse
import json
import shutil
import sys
from pathlib import Path
import numpy as np
import trimesh

from design import OUT,CAD,OLD,base,power,d1,prior,PANEL,FILES,NAMES,PLASTICS,groups,INSERT,CONTRACT,FASCIA_CONTRACT,facade_contract
old=prior.old;dump,digest,operations_hash=prior.dump,prior.digest,prior.operations_hash
WORK=OUT/'.work';REVISION='D2.6';BOARD=OUT/'board-study/mac-board-reference.glb'

def shared():return groups()[:2]
def features():return groups()

def seed():
    groups=shared();WORK.mkdir(exist_ok=True,parents=True)
    fname="base-power-"+operations_hash(groups)[:20]+".sc"
    path=WORK/fname
    if not path.is_file():
        d25_seed=CAD/'prototype-d25/.work'/fname
        if d25_seed.is_file():
            shutil.copy2(d25_seed,path)
        else:
            with d1.c.SolidCraftMCP(timeout=360) as session:
                for label,ops in groups:
                    print(label,len(ops),flush=True)
                    d1.v.batch(session,ops)
                check=d1.v.measures(session)
                assert set(check)==set(NAMES)-{PANEL,INSERT}
                session.call("save",{"path":str(path)})
    return path

def run():
    dump(FASCIA_CONTRACT,facade_contract())
    groups=features()
    (OUT/"geometry").mkdir(exist_ok=True)
    exports={"d26-printable.step":PLASTICS,"d26-assembly.step":NAMES}
    prior=json.loads((OLD/"cad-validation.json").read_text(encoding="utf-8"))
    assert BOARD.is_file() and (OUT/"board-study/registered-board.stl").is_file()
    with d1.c.SolidCraftMCP(design=seed(),timeout=360) as session:
        for label,ops in groups[2:]:
            print(label,len(ops),flush=True)
            d1.v.batch(session,ops)
        native=d1.v.measures(session)
        assert set(native)==set(NAMES) and all(v["closed"] and v["volume_mm3"]>0 for v in native.values())
        timeline=session.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not any(f.get("error") or f.get("warning") for f in timeline)
        for group,names in FILES.items():
            d1.v.batch(session,[d1.cmd("appearance.assign",bodies=names,color=({"panel":"#303436","socket_insert":"#303235",**{k:v for k,v in old.COLORS.items() if k!="panel"}}).get(group,"#9da5a5")),
                d1.cmd("file.export",path=str(OUT/"geometry"/(group+".glb")),bodies=names,quality="standard")])
        for name,bodies in exports.items():session.call("export",{"path":str(OUT/name),"bodies":bodies})
        d1.v.batch(session,[d1.cmd("file.insert_mesh",path=str(BOARD),origin=False,name="Registered SOURCE Mac with seven photographed connector mouths; antennas detached")])
        saved=WORK/"assembled-native.sc"
        session.call("save",{"path":str(saved)})
    saved.replace(OUT/"d26-workbench.sc")
    reads={}
    def compare(got,want):
        assert got["closed"] and np.isclose(got["volume_mm3"],want["volume_mm3"],rtol=.00006,atol=.0003)
        assert all(np.allclose(got["bbox"][k],want["bbox"][k],atol=.003,rtol=0) for k in ("min","max"))
    for name,names in exports.items():
        with d1.c.SolidCraftMCP(design=OUT/name,timeout=360) as session: got=d1.v.measures(session)
        assert set(got)==set(names)
        for n in names:compare(got[n],native[n])
        reads[name]=len(names)
    with d1.c.SolidCraftMCP(design=OUT/"d26-workbench.sc",timeout=360) as session:
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
    reads["d26-workbench.sc"]=len(got)
    unchanged=sorted({base.BLANK,*base.FEET,*base.PCB_HARDWARE,*base.LID_HARDWARE,*base.BLANK_HARDWARE})
    for n in unchanged:compare(native[n],prior["bodies"][n])
    dump(OUT/"cad-validation.json",dict(variant=REVISION+" / flat 2.60 mm rear panel (0.80/0.90/0.40 mm pocket walls), unified USB-A/audio T-pocket, Ø5.90 audio passage, widened HDMI/RJ/TB reliefs",revision=REVISION,date="2026-11-19",
        units="desk mm",features=len(timeline),warnings=[],groups=FILES,bodies=native,print_bodies=PLASTICS,
        operations_sha256=operations_hash(groups),unchanged_from_d2=unchanged,readback=reads,
        files_sha256={name:digest(OUT/name) for name in reads},owner_board_sha256=digest(BOARD),owner_registered_stl_sha256=digest(OUT/"board-study/registered-board.stl"),port_contract_sha256=digest(CONTRACT),fascia_contract_sha256=digest(FASCIA_CONTRACT),fitted_antenna_references=0))
    print(reads,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--seed",action="store_true");args=p.parse_args()
    if args.seed:print(seed())
    else:run()
