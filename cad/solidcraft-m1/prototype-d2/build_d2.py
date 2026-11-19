"""FDM D2.1. All design modules use the same millimetre datum, +Y rear and +Z up."""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
CAD = OUT.parent
sys.path.insert(0, str(CAD / "prototype-d1"))
import build_d1 as d1
import base, rear, power

FILES = {g:n for g,n in {**base.FILES, "panel":[rear.PANEL], **power.FILES}.items() if n}
NAMES = sum((list(names) for names in FILES.values()), [])
assert len(set(NAMES)) == len(NAMES)
PLASTICS = [base.BASE, base.LID, rear.PANEL, power.HOLDER, *FILES.get("blank", [])]
SOURCE_IDS = (20,11,13,14)  # OEM assembly, three RF references. Never the author's tray (25).
SOURCE_FILE = OUT / "geometry/retained-source.obj"
REVISION = "D2.1"
COLORS = {"base":"#414e50","lid":"#536263","panel":"#313b3c","saddle":"#50836f",
          "blank":"#424b4a","feet":"#303433","boards":"#345b52","population":"#929b9a","socket":"#bcc4c0"}
def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def features():
    import rear_plate_d21, rear_mount_d21
    return [("Base and lid",base.operations()),("Eight profiled rear openings",rear_plate_d21.operations()),
            ("Low floor track and cover capture",rear_mount_d21.operations()),("Power saddle",power.operations())]

def operations_hash(groups):
    return hashlib.sha256(json.dumps(groups,sort_keys=True).encode()).hexdigest()

def retained():
    """Copy only the four original object face lists; remap their global OBJ vertex IDs."""
    origin = CAD / "convection-v5/geometry/retained-source.obj"
    verts=[]; faces={}; active=None
    for line in origin.read_text().splitlines():
        if line.startswith("v "): verts.append(line)
        elif line.startswith("o "):
            active=int(line.split("_")[-1])
            faces[active]=[]
        elif line.startswith("f "):
            face=tuple(int(s.split("/")[0]) for s in line.split()[1:]); assert len(face)==3
            faces[active].append(face)
    assert set(faces)=={*SOURCE_IDS,25} and len(faces[20])==9680
    output=["# SnazzyLabs Printables 139893, CC BY-NC. Desk mm. OEM and RF references only."]
    count=0
    for n in SOURCE_IDS:
        output.append(f"o SOURCE_REFERENCE_COMPONENT_{n}")
        ids=sorted({v for face in faces[n] for v in face})
        lookup={v:i for i,v in enumerate(ids,count+1)}
        output.extend(verts[v-1] for v in ids)
        output.extend("f "+" ".join(str(lookup[v]) for v in face) for face in faces[n])
        count+=len(ids)
    SOURCE_FILE.write_text("\n".join(output)+"\n",encoding="ascii")
    return {"origin_sha256":digest(origin),"export_sha256":digest(SOURCE_FILE),"triangles":{n:len(faces[n]) for n in SOURCE_IDS}}

def run():
    (OUT/"geometry").mkdir(exist_ok=True)
    source=retained()
    exports={"d2-printable.step":PLASTICS, "d2-assembly.step":NAMES}
    groups=features()
    inputs_sha=operations_hash(groups)
    with d1.c.SolidCraftMCP(timeout=300) as m:
        for label,ops in groups:
            print(label,len(ops),flush=True)
            d1.v.batch(m,ops)
        native=d1.v.measures(m)
        assert set(native)==set(NAMES),(set(native)^set(NAMES))
        assert all(b["closed"] and b["volume_mm3"]>0 for b in native.values())
        timeline=m.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not [f for f in timeline if f.get("error") or f.get("warning")], "Native feature warning/error"
        for key,names in FILES.items():
            d1.v.batch(m,[d1.cmd("appearance.assign",bodies=names,color=COLORS.get(key,"#9da5a5")),
                          d1.cmd("file.export",path=str(OUT/"geometry"/(key+".glb")),bodies=names,quality="standard")])
        for dest,names in exports.items(): m.call("export",{"path":str(OUT/dest),"bodies":names})
        d1.v.batch(m,[d1.cmd("file.insert_mesh",path=str(SOURCE_FILE),units="mm",origin=False,name="OEM and three RF references / SnazzyLabs")])
        m.call("save",{"path":str(OUT/"d2-workbench.sc")})
    readback={}
    for dest,names in exports.items():
        with d1.c.SolidCraftMCP(design=OUT/dest,timeout=300) as m:
            bodies=d1.v.measures(m)
            assert set(bodies)==set(names),dest
            for n,b in bodies.items():
                assert b["closed"] and math.isclose(b["volume_mm3"],native[n]["volume_mm3"],rel_tol=.00006,abs_tol=.0003),(dest,n)
                assert all(np.allclose(b["bbox"][e],native[n]["bbox"][e],atol=.003,rtol=0) for e in ("min","max")),(dest,n)
            readback[dest]=len(bodies)
    with d1.c.SolidCraftMCP(design=OUT/"d2-workbench.sc",timeout=300) as m:
        scene=m.json("inspect_design",{"measure":False,"sketches":False})
        assert len(scene["bodies"])==len(NAMES)+len(SOURCE_IDS) and not any(f.get("error") for f in scene["timeline"])
        readback["d2-workbench.sc"]=len(scene["bodies"])
    dump(OUT/"cad-validation.json",{"variant":REVISION+" / FDM cold fit","date":"2026-11-18","units":"desk mm","features":len(timeline),"warnings":[],
        "operations_sha256":inputs_sha,"groups":FILES,"print_bodies":PLASTICS,"source":source,"readback":readback,"bodies":native})
    print(readback,flush=True)
if __name__=="__main__":run()
