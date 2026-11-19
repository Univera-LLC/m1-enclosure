"""Compact C2. Rebuild in a private, mm/Z-up SolidCraft session; digital review only."""
from pathlib import Path
import sys, json, hashlib, math
import numpy as np

OUT = Path(__file__).resolve().parent
CAD = OUT.parent
ROOT = CAD.parents[1]
sys.path[:0] = [str(CAD / "tools"), str(CAD / "mechanical-v1")]
from solidcraft_mcp import SolidCraftMCP
from audit_source_mounts import TRAY_CENTRES, SHEET_CENTRES

CAP, FRAME, REAR = "C2_LID", "C2_CHASSIS", "C2_IO_AND_PSU_FORK"
BASE, GRILLE = "C2_SERVICE_BOTTOM", "C2_INTAKE_SHEET"
BOARD, USB, COIL, BULK, BUCK = "PD_V1_EDGE_CUTS", "J1_FAB_PROXY", "L1_PACKAGE_PROXY", "C2_FOOTPRINT_PROXY", "U3_PACKAGE_PROXY"
BUTTON, GUIDE, CARRIER = "FRONT_BUTTON_CAP_AND_ACTUATOR", "FRONT_BUTTON_GUIDE_WITH_STOP", "FRONT_SWITCH_CARRIER_PROPOSED"
BLOWER = "BLOWER_SPACE_ASSUMED"
HOOD_FIX = [(-35,-54.3), (35,-54.3), (-62,57.8), (49.5,57.8)]
BASE_FIX = [(-48,-50.5),(48,-50.5),(-68,56.3),(66,55.0)]
FEET = [(-66.8,-46.8),(66.8,-46.8),(-47,50.3),(46,49.5)]
PD_X, EDGE_Y, BOARD_Z = -31.0, 56.35, 30.8
HEIGHT, WALL, SEAM = 44., 2.4, 28.
FILES = {"cap": [CAP], "chassis":[FRAME], "rear":[REAR], "bottom":[BASE],
         "grille":[GRILLE], "pcb":[BOARD], "packages":[USB,COIL,BULK,BUCK],
         "button":[BUTTON], "guide":[GUIDE,CARRIER], "fan":[BLOWER]}
COLORS = {"cap":"#A7ABA8", "chassis":"#A7ABA8", "rear":"#66716C", "bottom":"#464E4C",
          "grille":"#BAC1BC","pcb":"#347550","packages":"#59625D","button":"#535F5A",
          "guide":"#668077","fan":"#C49A59"}
PCB_FILE = ROOT / "pcb/v1/mac_mini_pd_psu/mac_mini_pd_psu.kicad_pcb"
INV = ROOT / "docs/pcb-v1-review-2026-11-17/inventory.json"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def cmd(k,**p): return {"command":k,"params":p}
def boolean(target, op):
    return {"operation":op, **({"body_name":target} if op=="new" else {"targets":[target]})}
def box(target,op,at,size,name):
    return cmd("solid.box",corner=at,length=size[0],width=size[1],height=size[2],name=name,**boolean(target,op))
def cyl(target,op,at,d,h,name,axis="Z"):
    return cmd("solid.cylinder",base=at,diameter=d,height=h,axis=axis,name=name,**boolean(target,op))
def fil(target,edges,r):
    return cmd("solid.fillet",body=target,edges=edges,radius=r,name="Rounded edges")
def slot(target,x0,x1,y,w,z,h,label):
    return [cmd("sketch.create",plane="XY",offset=z,name=label+" profile"),
            cmd("sketch.slot.overall",p0=[x0,y],p1=[x1,y],width=w),
            cmd("sketch.finish"),cmd("solid.extrude",operation="cut",targets=[target],distance=h,name=label)]
def xy(kx,ky): return [round(PD_X-(ky-67),6),round(EDGE_Y-(kx-33),6)]
def board_data():
    inv=json.loads(INV.read_text()); assert sha(PCB_FILE)==inv["hashes"][PCB_FILE.name], "Review the new KiCad revision first"
    graphics=[{k:v for k,*v in g[1:] if isinstance(k,str)} for g in inv["graphics"] if g[0] in ("gr_rect","gr_circle")]
    outline=graphics[0]; assert outline["start"]==["33","57"] and outline["end"]==["81.5","77"]
    holes=[]
    for g in graphics[1:]:
        p,q=([float(n) for n in g[key]] for key in ("center","end"))
        assert math.isclose(math.dist(p,q),1); holes.append(xy(*p))
    assert len(holes)==4 and inv["general"][1]==["thickness","1.6"]
    fps={f["properties"]["Reference"]:f for f in inv["footprints"]}
    p={k:xy(*fps[k]["at"][:2]) for k in ("J1","J2","C2","L1","U3")}
    assert fps["J1"]["at"][2]==-90
    return holes,p

def build():
    holes,fp=board_data()
    groups={}
    groups["parameters"]=[cmd("parameters.add",name=k,expression=str(v)+" mm",unit="mm",comment="C2 ASSUMED design; not a measurement")
                          for k,v in (("c2_h",HEIGHT),("c2_wall",WALL),("c2_split",SEAM))]
    for part,lid in ((CAP,True),(FRAME,False)):
        z=SEAM if lid else 0
        a=[box(part,"new",[-77.5,-57.5,z],[155,118,"c2_h-c2_split" if lid else "c2_split"],"Outer FDM blank"),
           fil(part,[[x,y,z+8] for x in (-77.5,77.5) for y in (-57.5,60.5)],8)]
        if lid:
            a += [cmd("solid.chamfer",body=part,edges=[[0,-57.5,44]],distance=.6,name="Bed-face lead-in")]
        a += [cmd("solid.shell",body=part,faces=[[0,0,z]] if lid else [[0,0,0],[0,0,SEAM]],
                  thickness="c2_wall",name="Open hood" if lid else "Open chassis ring")]
        a.append(cmd("solid.chamfer",body=part,edges=[[0,-57.5,SEAM]],distance=.35,name="Fine reveal masks layer alignment at service seam"))
        if lid:
            a.append(box(part,"cut",[-72.5,54.7,27.8],[147.4,9,"c2_h-c2_wall-27.8 mm"],"Rear window open below; wired parts stay on chassis"))
            for x in (-49.8,-16.8,60.5):
                a.append(box(part,"join",[x,54.05,36.8],[4.2,2.55,"c2_h-c2_wall-36.8 mm"],"Upper fascia thrust seat; no load on chip clamp"))
        else:
            a += [box(part,"cut",[-72.5,54.7,4.8],[147.4,9,25],"Rear fascia drops into chassis"),
                  box(part,"cut",[-18,54.7,.45],[65,9,5],"Low exhaust, no sill across air path"),
                  cyl(part,"cut",[0,-58.1,17.4],10.8,5,"Existing switch guide datum","Y")]
        groups["hood" if lid else "ring"]=a

    a=[]
    for i,(x,y) in enumerate(HOOD_FIX):
        # Access tunnel in the fixed wall; an M2 head seats at 24.8. Lid bosses grow from the roof.
        rear=i>=2
        y0,y1=(55.25,60.5) if rear else (-57.05,-51.99)
        a += [box(FRAME,"join",[x-3.5,y0,0],[7,y1-y0,28],"Hidden lid screw pillar"),
              cyl(FRAME,"cut",[x,y,-.1],4.6,24.9,"Underside driver and head passage"),
              cyl(FRAME,"cut",[x,y,24.7],2.3,3.5,"M2 shank only"),
              box(CAP,"join",[x-3.5,y0,28],[7,y1-y0,"c2_h-c2_wall-28 mm"],"Roof boss above pillar"),
              cyl(CAP,"cut",[x,y,27.99],3.0,4.51,"M2 insert pilot ASSUMED"),
              cyl(CAP,"cut",[x,y,32.48],2.2,1.3,"Blind tip reserve")]
    for x,y in TRAY_CENTRES:
        x0,x1=(-76.5,x+4.5) if x<0 else (x-4.5,76.5)
        wx=-76.6 if x<0 else 73.2
        a += [box(FRAME,"join",[x0,y-4.5,.15],[x1-x0,9,3.],"Tray source landing, independent M2"),
              box(FRAME,"join",[wx,y-4.5,2.8],[3.4,9,4.35],"Outboard web"),
              cyl(FRAME,"cut",[x,y,-.1],2.2,3.5,"Original plastic post axis; not an OEM board screw")]
    for i,(x,y) in enumerate(BASE_FIX):
        if i<2: p=[x-5,-57.5,0]; size=[10,y+5+57.5,7.4]
        else: p=[x-4,y-3.6,0]; size=[8,60.0-(y-3.6),7.4]
        a += [box(FRAME,"join",p,size,"Independent bottom closure"),
              cyl(FRAME,"cut",[x,y,-.1],4.0,5.8,"M3 insert pilot"),
              cyl(FRAME,"cut",[x,y,5.68],3.4,.84,"Screw tip relief")]
    for x in (-54,58):
        a += [box(FRAME,"join",[x-4.5,55.7,0],[9,4.5,4.8],"Fascia tenon socket"),
              box(FRAME,"cut",[x-3.3,56.6,1.2],[6.6,2.2,3.7],"Captured by lid; clearance each side 0.3")]
    for x,y in HOOD_FIX[2:]:
        a.append(cyl(FRAME,"cut",[x,y,-.1],4.6,24.9,"Continue rear driver bore through adjoining bottom boss"))
    a.append(cyl(FRAME,"cut",[-41.3,55.5,7.8],9.,6.,"Audio boot scallop in rear sill","Y"))
    groups["mounts"]=a

    a=[box(REAR,"new",[-72.2,56.9,4.8],[146.85,1.6,"c2_h-c2_wall-5.1 mm"],"Stationary replaceable I/O panel"),
       box(REAR,"join",[-17.7,56.9,.55],[63.0,1.6,5.4],"Lower exhaust tongue")]
    for x in (-54,58):
        a.append(box(REAR,"join",[x-3,56.9,1.5],[6,1.6,3.5],"Slot tenon"))
    # A thin spine near the roof joins the rear spans above both reliefs (inside the rear pillars).
    for x,y in HOOD_FIX[2:]:
        a += [box(REAR,"join",[x-5.6,53.35,37.8],[1.75,3.75,2.8],"Return behind pillar"),
              box(REAR,"join",[x+3.85,53.35,37.8],[1.75,3.75,2.8],"Return behind pillar"),
              box(REAR,"join",[x-5.6,53.35,37.8],[11.2,1.6,2.8],"Printable U around lid pillar")]
    for x,y in HOOD_FIX[2:]:
        a.append(box(REAR,"cut",[x-3.8,56.5,4.7],[7.6,3,"c2_h-c2_wall-4.65 mm"],"Clear fixed/upper pillar"))
    for x,w,h in ((-72.35,8.65,3.15),(61.7,13.2,4.5)):
        a.append(box(REAR,"cut",[x,56.5,4.65],[w,3,h],"Clear independent lower closure boss"))
    # Windows are enlarged for the boot, so the native face need not be extended to the outer wall.
    for x0,x1,z0,z1,label in [(-59.5,-23.2,12.9,23.2,"Paired USB-A"),(-10.5,41.2,12.7,23.4,"HDMI and two Thunderbolt"),
                              (53.9,75.,8.2,28.7,"RJ45 including latch"),(-36.4,-25.6,31.9,36.35,"PD inlet; distinct upper row")]:
        a.append(box(REAR,"cut",[x0,56.5,z0],[x1-x0,3,z1-z0],label))
    a.append(cyl(REAR,"cut",[-41.3,56.5,7.8],8.5,3,"Headphone plug collar","Y"))
    # Viewed from +Y, text reads towards -X. Shallow 0.8 mm strokes can be paint-filled.
    for u,v,w,h in ((0,0,.8,4.4),(.65,3.6,1.95,.8),(.65,1.8,1.95,.8),(2.3,2.05,.8,2.1),
                    (4.2,0,.8,4.4),(4.85,3.6,1.85,.8),(4.85,0,1.85,.8),(6.55,.45,.8,3.5)):
        a.append(box(REAR,"cut",[-40-u-w,58.1,31.85+v],[w,.6,h],"Engraved PD legend, 0.4 mm deep"))
    for i in range(6):
        a.append(box(REAR,"cut",[-15.5+10.2*i,56.5,1.2],[8.4,3,7.4],"Rear exhaust "+str(i+1)))
    for i in range(4):
        a.append(box(REAR,"cut",[-14+13*i,56.5,32.1],[10.8,3,3.2],"Upper electronics ventilation "+str(i+1)))
    # Collector: floor is the closed portion of the removable grille. Roof and side cheeks print with fascia face down.
    a += [box(REAR,"join",[-17.2,31.9,8.6],[62.7,25.2,1.6],"Collector roof above rear exhaust"),
          box(REAR,"join",[-17.2,31.9,.2],[1.6,25.2,8.9],"Collector cheek left"),
          box(REAR,"join",[43.9,31.9,.2],[1.6,25.2,8.9],"Collector cheek right"),
          box(REAR,"join",[-16.8,31.9,.2],[61.9,1.65,2.35],"Lower bypass fence behind fin tips; no contact with heatsink")]
    a.append(cyl(REAR,"cut",[-20,52,-.2],7.,2.4,"Clear nearest low M3 sheet head while closing the service bottom"))
    for xlo,webx in ((-43.6,-43.6),(-25.85,-20.25)):
        a += [box(REAR,"join",[xlo,7.85,28.4],[7.45,49.35,1.6],"Open fork rail"),
              box(REAR,"join",[webx,7.85,29.9],[1.85,49.35,5.7],"Longitudinal web beside PCB; no unsupported chassis crossbar")]
    for xlo,width in ((-42.1,7.9),(-27.8,7.9)):
        a += [box(REAR,"join",[xlo,48.35,34.3],[width,1.1,1.3],"J1 shell insertion stop; fit and solder keepout OPEN")]
    for x in (-43.3,-20.1):
        a.append(box(REAR,"join",[x,6.9,31.6],[1.4,2.05,1.8],"Saddle return clears laminate edge"))
    a.append(box(REAR,"join",[-43.3,.8,31.6],[24.5,6.75,1.8],"Raised harness saddle on same removable fork as J2"))
    for x in (-37.8,-26.5):
        a.append(box(REAR,"cut",[x,2.4,31.45],[2.3,3.6,2.1],"Removable small tie slot; route to Mac OPEN"))
    for x,y in holes:
        a += [cyl(REAR,"join",[x,y,29.96],3.5,.84,"Insulating support; allowable land OPEN"),
              cyl(REAR,"cut",[x,y,28.2],1.75,2.8,"M1.6 candidate clearance; retainer SKU OPEN"),
              cyl(REAR,"cut",[x,y,28.2],3.4,1.2,"Recess low head below rail, nut above PCB; actual SKU OPEN")]
    groups["rear"]=a
    # Reuse the stepped H1 sheet seat and fastener pockets; change only perimeter, feet and vent field.
    a=[box(BASE,"new",[-74.8,-54.8,-4.6],[149.6,114.3,4.6],"Inset service pan"),
       fil(BASE,[[x,y,-2.3] for x in (-74.8,74.8) for y in (-54.8,59.5)],6.0),
       box(BASE,"cut",[-16,-38,-4.8],[62,86,5],"H1 window below sheet"),
       box(BASE,"cut",[-24.3,-46.3,-1.5],[78.6,102.6,1.8],"3.1 mm bearing ledge"),
       box(GRILLE,"new",[-24,-46,-1.5],[78,102,1.5],"Flat aluminium sheet; no CPU clamp load")]
    for x,y in FEET: a.append(cyl(BASE,"join",[x,y,-10.6],12,6.05,"Six mm desk standoff"))
    for x,y in SHEET_CENTRES:
        a += [cyl(BASE,"join",[x,y,-8.6],10,4.05,"Sheet insert reinforcement"),
              cyl(BASE,"cut",[x,y,-7.2],4.,6.,"Sheet insert pilot"),
              cyl(BASE,"cut",[x,y,-7.6],3.4,.5,"Blind tip"),
              cyl(GRILLE,"cut",[x,y,-1.7],3.4,2.,"Sheet fixing M3")]
    for i,y in enumerate((-35.4,-29.6,-23.8)): a += slot(GRILLE,-13,43,y,3.6,-1.7,2.,f"Inlet {i+1}")
    for x,y in BASE_FIX: a.append(cyl(BASE,"cut",[x,y,-4.7],3.4,4.9,"Independent M3 bottom clearance"))
    for x,y in TRAY_CENTRES: a.append(cyl(BASE,"cut",[x,y,-2.45],6,2.6,"Tray head relief; base does not hold tray"))
    groups["base"]=a
    legacy=json.loads((CAD/"interface-v1/build-commands.json").read_text())["commands"]
    groups["button"]=[c for c in legacy if any(c["params"].get("body_name")==k or k in c["params"].get("targets",[]) for k in (BUTTON,GUIDE,CARRIER))]
    a=[box(BOARD,"new",[-41,7.85,BOARD_Z],[20,48.5,1.6],"KiCad v1 SOURCE: board only")]
    for x,y in holes:a.append(cyl(BOARD,"cut",[x,y,BOARD_Z-.1],2.,2.,"Edge.Cuts circle, not a screw specification"))
    fp2=next(f for f in json.loads(INV.read_text())["footprints"] if f["properties"]["Reference"]=="J2")
    for p in fp2["pads"]:
        a.append(cyl(BOARD,"cut",[*xy(*p["global_at"]),BOARD_Z-.1],float(p["drill"][1]),2.,"SOURCE J2 solder wire drill"))
    x,y=fp["J1"]; top=BOARD_Z+1.6
    a += [box(USB,"new",[x-4.47,y-3.675,top],[8.94,7.35,3.25],"F.Fab XY; package height ASSUMED"),
          box(USB,"cut",[x-3.45,y+1.0,top+.64],[6.9,3,1.97],"Indicative socket mouth"),
          cyl(BULK,"new",[*fp["C2"],top],6.3,7.7,"SOURCE footprint nominal, not worst-case SKU"),
          box(COIL,"new",[fp["L1"][0]-4.09,fp["L1"][1]-4.32,top],[8.18,8.64,4.0],"L1 F.Fab XY rotated into assembly"),
          box(BUCK,"new",[fp["U3"][0]-1.5,fp["U3"][1]-1.5,top],[3.,3.,1.2],"U3 simplified thermal-location proxy"),
          box(BLOWER,"new",[0,-51,.3],[30,30,10],"Space study only; no motor, duct coupling or selected SKU")]
    groups["reference envelopes"]=a
    return groups

def run():
    (OUT/"geometry").mkdir(exist_ok=True)
    g=build(); record={"version":"compact-v2","date":"2026-11-18","cad_units":"mm Z-up",
        "kicad_board_sha256":sha(PCB_FILE),"world_hole_centres":board_data()[0],"footprint_origins":board_data()[1],
        "status":"P2/P4 candidate; no physical, electrical, thermal, RF or manufacturing acceptance",
        "component_status":"bare laminate SOURCE; package XY proxies and heights vary, see README; blower = free-space study",
        "stages":{}}
    def runbatch(m,commands):
        result=m.json("batch",{"commands":commands,"verbose":False})
        if not result.get("ok"): raise ValueError(result)
        return result
    def measure(m):return {b["name"]:b for b in m.json("measure",{"summary":True})["bodies"]}
    solid_names=sum(FILES.values(),[])
    with SolidCraftMCP(timeout=180) as m:
        for name,group in g.items():
            result=runbatch(m,group);record["stages"][name]=result["completed"]
            print(name,len(group),flush=True)
        original=measure(m)
        assert set(original)==set(solid_names) and all(b["closed"] and b["volume_mm3"]>0 for b in original.values()), [(n,b["closed"],b["volume_mm3"]) for n,b in original.items()]
        for key,names in FILES.items():
            runbatch(m,[cmd("appearance.assign",bodies=names,color=COLORS[key])])
            m.call("export",{"path":str(OUT/"geometry"/(key+".glb")),"bodies":names})
        health=m.json("inspect_design",{"measure":False,"sketches":False})
        assert not [f for f in health["timeline"] if f.get("error")]
        record["warnings"]=[(f.get("name"),f.get("warning")) for f in health["timeline"] if f.get("warning")]
        record["bodies"]=original
        # A taller PCB may call for a taller lid. Preserve the seam, mounted board and connector datum.
        for val in (46,44):
            change=m.json("set_parameter",{"name":"c2_h","value":str(val)+" mm"})
            assert not change.get("errors"),change
            alt=measure(m)
            assert abs(alt[CAP]["bbox"]["max"][2]-val)<.001 and abs(alt[REAR]["bbox"]["max"][2]-(val-2.7))<.001
            for n in set(solid_names)-{CAP,REAR}:
                assert abs(alt[n]["volume_mm3"]-original[n]["volume_mm3"])<.001,n
        record["roof_variant"]="44 -> 46 -> 44 mm rebuilt; stationary port and PCB fixed"
        parts=[n for key in ("cap","chassis","rear","bottom","grille","button","guide") for n in FILES[key]]
        m.call("export",{"path":str(OUT/"compact-v2-parts.step"),"bodies":parts})
        m.call("save",{"path":str(OUT/"compact-v2-layout.sc")})
        for path,label in [(CAD/"interface-v1/source-reference-no-legacy.obj","SnazzyLabs SOURCE"),
                           (CAD/"interface-v1/front-switch-source-relocated.obj","Switch NOT ACCEPTED")]:
            runbatch(m,[cmd("file.insert_mesh",path=str(path),units="mm",origin=False,name=label)])
        m.call("save",{"path":str(OUT/"compact-v2-workbench.sc")})
    for filename in ("compact-v2-layout.sc","compact-v2-parts.step","compact-v2-workbench.sc"):
        with SolidCraftMCP(design=OUT/filename,timeout=180) as m:
            if "workbench" in filename:
                health=m.json("inspect_design",{"measure":False,"sketches":False})
                assert len(health["bodies"])==len(solid_names)+6
                record["workbench_bodies"]=len(health["bodies"])
            else:
                back=measure(m); expected=solid_names if filename.endswith(".sc") else parts
                assert set(back)==set(expected)
                for n in expected:
                    b=back[n]; assert b["closed"] and math.isclose(b["volume_mm3"],original[n]["volume_mm3"],rel_tol=2e-5),(n,b)
                    assert all(np.allclose(b["bbox"][s],original[n]["bbox"][s],atol=.002) for s in ("min","max")), n
                record[filename+" readback"]=len(back)
    dump(OUT/"cad-validation.json",record)
    board_step()
    print("C2 native / STEP readback OK",flush=True)

def board_step():
    """Small exchange file in the same assembly datum for PCB/CAD collaboration."""
    names=FILES["pcb"]+FILES["packages"]; path=OUT/"pd-v1-envelope.step"
    record=json.loads((OUT/"cad-validation.json").read_text(encoding="utf-8"))
    with SolidCraftMCP(design=OUT/"compact-v2-layout.sc",timeout=120) as m:
        m.call("export",{"path":str(path),"bodies":names})
    with SolidCraftMCP(design=path,timeout=120) as m:
        bodies=m.json("measure",{"summary":True})["bodies"];assert {b["name"] for b in bodies}==set(names)
        for b in bodies:
            a=record["bodies"][b["name"]]; assert b["closed"] and math.isclose(a["volume_mm3"],b["volume_mm3"],rel_tol=2e-5)
            assert all(np.allclose(a["bbox"][k],b["bbox"][k],atol=.002) for k in ("min","max"))
    record["pd-v1-envelope.step readback"]=len(bodies);dump(OUT/"cad-validation.json",record)
if __name__=="__main__": board_step() if "--pcb-only" in sys.argv else run()
