"""C3: upright PD v1 to the outside of the native Ethernet socket. Project mm, +Y rear."""
from pathlib import Path
import copy, json, math, sys
import numpy as np

OUT = Path(__file__).resolve().parent
C2 = OUT.parent / "compact-v2"
sys.path.insert(0, str(C2))
import build_compact as c

RIGHT, RAD, H, SPLIT = 90.5, 6., 34., 25.
BX, CZ = 76.7, 17.8       # plane of B.Cu, centre of 20 mm edge; low rail clears fascia socket
CAP, FRAME, REAR, BASE = "C3_LID", "C3_CHASSIS", "C3_IO_AND_UPRIGHT_FORK", "C3_SERVICE_BOTTOM"
NAMES = {c.CAP:CAP, c.FRAME:FRAME, c.REAR:REAR, c.BASE:BASE, c.GRILLE:"C3_INTAKE_SHEET"}
FILES = {g:[NAMES.get(n,n) for n in l] for g,l in c.FILES.items()}
HARD = sum((FILES[k] for k in ("cap","chassis","rear","bottom","grille","button","guide")),[])
POWER = FILES["pcb"] + FILES["packages"]
rot = np.array([[0,0,1],[0,1,0],[-1,0,0]])
shift = np.array([BX-c.BOARD_Z,0,CZ+c.PD_X])
def pose(p):
    return np.round(rot @ np.asarray(p) + shift,6).tolist()
def rename(q):
    q = copy.deepcopy(q); p=q["params"]
    for k in ("body_name","body"):
        if k in p: p[k]=NAMES.get(p[k],p[k])
    if "targets" in p: p["targets"]=[NAMES.get(n,n) for n in p["targets"]]
    return q
def turn(q):
    q=rename(q); p=q["params"]
    if q["command"]=="solid.cylinder":
        assert p["axis"]=="Z"; p["axis"]="X"; p["base"]=pose(p["base"])
    else:
        assert q["command"]=="solid.box"
        corner=np.array(p["corner"]); size=np.array([p[k] for k in ("length","width","height")])
        low,high=pose(corner),pose(corner+size)
        p["corner"]=np.minimum(low,high).tolist()
        p["length"],p["width"],p["height"]=np.round(np.abs(np.subtract(high,low)),6).tolist()
    return q
def build():
    old=c.build(); groups={}
    groups["dimensions"]=[c.cmd("parameters.add",name=k,expression=f"{v} mm",unit="mm",comment="C3 CAD scenario, ASSUMED")
                          for k,v in (("c3_h",H),("c3_wall",2.4))]
    for body,lid in ((CAP,True),(FRAME,False)):
        z=SPLIT if lid else 0
        a=[c.box(body,"new",[-77.5,-57.5,z],[RIGHT+77.5,118,"c3_h-25 mm" if lid else SPLIT],"FDM blank"),
           c.fil(body,[[x,y,z+3] for x in (-77.5,RIGHT) for y in (-57.5,60.5)],RAD)]
        if lid:a.append(c.cmd("solid.chamfer",body=body,edges=[[0,-57.5,H]],distance=.6,name="Bed-side lead-in"))
        a.extend([c.cmd("solid.shell",body=body,faces=[[0,0,z]] if lid else [[0,0,0],[0,0,SPLIT]],thickness="c3_wall",name="Open chassis or lid"),
                  c.cmd("solid.chamfer",body=body,edges=[[0,-57.5,SPLIT]],distance=.35,name="Service seam")])
        if lid:
            a.append(c.box(body,"cut",[-72.5,54.7,24.8],[159.8,9,"c3_h-c3_wall-24.8 mm"],"Fixed fascia stays on chassis"))
            for x in (-49.8,-16.8,60.5,81.7):
                a.append(c.box(body,"join",[x,54.05,28.6],[4.2,2.55,"c3_h-c3_wall-28.6 mm"],"Upper fascia thrust seat"))
        else:
            a.extend([c.box(body,"cut",[-72.5,54.7,4.8],[159.8,9,22],"Rear fascia recess"),
                      c.box(body,"cut",[-18,54.7,.45],[65,9,5],"Low exhaust sill"),
                      c.cyl(body,"cut",[0,-58.1,17.4],10.8,5,"Original front button guide","Y")])
        groups["lid" if lid else "chassis"]=a
    a=[]
    for raw in old["mounts"]:
        q=rename(raw); p=q["params"]; n=p["name"]
        if n=="Hidden lid screw pillar": p["height"]=SPLIT
        elif n.startswith(("Underside driver","Continue rear driver")): p["height"]-=3
        elif n=="M2 shank only": p["base"][2]-=3
        elif n=="Roof boss above pillar": p["corner"][2]=SPLIT;p["height"]="c3_h-c3_wall-25 mm"
        elif n in ("M2 insert pilot ASSUMED","Blind tip reserve"):p["base"][2]-=3
        elif n.startswith("Tray source landing") and p["corner"][0]>0:p["length"]+=13
        elif n=="Outboard web" and p["corner"][0]>0:p["corner"][0]+=13
        a.append(q)
    # Short stiffening ribs under the two extended right-hand tray landings; clear the PD rails.
    for x,y in c.TRAY_CENTRES:
        if x>0:a.append(c.box(FRAME,"join",[x+4.5,y-1.2,2.95],[89.5-(x+4.5),2.4,.9],"Shallow rib below the PD bay"))
    a.extend([c.box(FRAME,"join",[77.5,55.7,0],[9,4.5,4.8],"Additional PD-end fascia socket"),
              c.box(FRAME,"cut",[78.7,56.6,1.2],[6.6,2.2,3.7],"Additional tenon clearance")])
    groups["mounts"]=a
    a=[]; fork=False
    for raw in old["rear"]:
        n=raw["params"]["name"]
        if n=="Open fork rail":fork=True
        if fork:
            a.append(turn(raw));continue
        q=rename(raw);p=q["params"]
        if n=="Stationary replaceable I/O panel":
            p["length"]=159.2;p["height"]="c3_h-c3_wall-5.1 mm"
        elif n in ("Return behind pillar","Printable U around lid pillar"):
            p["corner"][2]=28.8;p["height"]=2.15
        elif n=="Clear fixed/upper pillar":p["height"]="c3_h-c3_wall-4.65 mm"
        elif n=="Clear independent lower closure boss" and p["corner"][0]>0:p["length"]=8.65
        elif n=="PD inlet; distinct upper row":
            q=turn(raw);q["params"]["name"]="Upright USB-C inlet beside Ethernet"
        elif n.startswith("Engraved PD legend"):
            p["corner"][0]+=123.2;p["corner"][2]-=7.5
        elif n.startswith("Upper electronics ventilation"):p["corner"][2]=25.5
        a.append(q)
    a.append(c.box(REAR,"join",[79,56.9,1.5],[6,1.6,3.5],"PD-end tenon"))
    groups["fascia"]=a
    a=[]
    for raw in old["base"]:
        q=rename(raw);p=q["params"];n=p.get("name")
        if n=="Inset service pan":p["length"]+=13
        elif q["command"]=="solid.fillet":
            for v in p["edges"]:
                if v[0]>0:v[0]+=13
            p["radius"]=4.
        elif n=="Six mm desk standoff" and p["base"][0]>0:
            if p["base"][1]>0:p["base"][:2]=[76.5,48.5]  # keep clear of rear bottom screw and washer
            else:p["base"][0]+=13
        a.append(q)
    groups["service bottom"]=a
    groups["front control"]=old["button"]
    groups["upright PCB / reference blower"]=[turn(q) if q["params"].get("body_name")!=c.BLOWER else q for q in old["reference envelopes"]]
    return groups

def run():
    geo=OUT/"geometry";geo.mkdir(exist_ok=True)
    names=sum(FILES.values(),[]); stats={"date":"2026-11-18","version":"C3 / digital only","units":"mm","source_pcb_sha256":c.sha(c.PCB_FILE)}
    def runbatch(m,ops):
        r=m.json("batch",{"commands":ops,"verbose":False})
        if not r.get("ok"):raise ValueError(r)
    def measures(m):return {b["name"]:b for b in m.json("measure",{"summary":True})["bodies"]}
    with c.SolidCraftMCP(timeout=180) as m:
        for n,a in build().items():
            runbatch(m,a);print(n,len(a),flush=True)
        bodies=measures(m);assert set(bodies)==set(names)
        assert all(b["closed"] and b["volume_mm3"]>0 for b in bodies.values())
        timeline=m.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not any(f.get("error") for f in timeline)
        stats["warnings"]=[f.get("warning") for f in timeline if f.get("warning")]
        for group,parts in FILES.items():
            runbatch(m,[c.cmd("appearance.assign",bodies=parts,color=c.COLORS[group])])
            m.call("export",{"path":str(geo/(group+".glb")),"bodies":parts})
        for h in (36,34):
            r=m.json("set_parameter",{"name":"c3_h","value":f"{h} mm"});assert not r.get("errors"),r
            alt=measures(m)
            assert abs(alt[CAP]["bbox"]["max"][2]-h)<.001 and abs(alt[REAR]["bbox"]["max"][2]-(h-2.7))<.001
            for n in set(names)-{CAP,REAR}:
                assert abs(alt[n]["volume_mm3"]-bodies[n]["volume_mm3"])<.001,n
        stats["roof_rebuild_mm"]=[34,36,34]
        for filename,parts in (("c3-enclosure.step",HARD),("c3-pd-v1.step",POWER)):
            m.call("export",{"path":str(OUT/filename),"bodies":parts})
        for path,label in ((c.CAD/"interface-v1/source-reference-no-legacy.obj","Retained SnazzyLabs SOURCE"),
                           (c.CAD/"interface-v1/front-switch-source-relocated.obj","Front switch NOT ACCEPTED")):
            runbatch(m,[c.cmd("file.insert_mesh",path=str(path),units="mm",origin=False,name=label)])
        m.call("save",{"path":str(OUT/"c3-workbench.sc")})
    stats["bodies"]=bodies
    for filename,parts in (("c3-enclosure.step",HARD),("c3-pd-v1.step",POWER),("c3-workbench.sc",names)):
        with c.SolidCraftMCP(design=OUT/filename,timeout=180) as m:
            if filename.endswith(".sc"):
                tree=m.json("inspect_design",{"measure":False,"sketches":False})
                assert len(tree["bodies"])==len(names)+6 and not any(f.get("error") for f in tree["timeline"])
                assert set(names)<={v["name"] for v in tree["bodies"]};stats[filename+" body count"]=len(tree["bodies"]);continue
            actual=measures(m);assert set(actual)==set(parts)
            for n,b in actual.items():
                assert b["closed"] and math.isclose(b["volume_mm3"],bodies[n]["volume_mm3"],rel_tol=2e-5),(n,b)
                assert all(np.allclose(b["bbox"][k],bodies[n]["bbox"][k],atol=.002) for k in ("min","max")),n
            stats[filename+" body count"]=len(actual)
    c.dump(OUT/"cad-validation.json",stats);print("C3 SC / both STEP readbacks OK",flush=True)
if __name__=="__main__":run()
