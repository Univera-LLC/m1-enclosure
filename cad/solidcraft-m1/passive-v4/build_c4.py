"""C4, in mm. Construct at retained C3 datums, then register EVERY body to the desk.
PCB/flex are not redesigned. No production meshes or assumptions about physical fit."""
from pathlib import Path
from functools import lru_cache
import copy, math, json, sys
import numpy as np
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/"compact-v3"))
import build_c3 as old
c=old.c
box,cyl,cmd=c.box,c.cyl,c.cmd
FLOOR,FRAME,IO,ROOF,METAL,KEEP="C4_FLOOR","C4_CHASSIS","C4_IO_FORK","C4_ROOF_CARRIER","C4_FINNED_BRIDGE","C4_J1_KEEPER"
MAP={old.CAP:FLOOR,old.FRAME:FRAME,old.REAR:IO}
FIN_X=[round(-20.2+6.4*i,3) for i in range(12)]
FIN_H=28.0
TEETH=[-12.773,-6.202,.370,6.942,13.513,20.085,26.657,33.228,39.800,46.371]
GUIDES=[(-24.,-54.9),(89.,-39.)]
FEET=[(-62.,-45.),(75.,-44.),(-52.,47.),(72.,46.)]
VENTS={"logic":[-60.,-54.5,-49.],"power":[75.8,81.3,86.8]}
VENT_SPANS=[(-33.,-8.),(-2.9,22.1)]
# Stable names of this archived revision. D2.6 imports the geometry helpers,
# not this custom PCB. Validate its source only when PCB geometry is used.
EXTRA=sorted("C1 C3 C4 C5 C6 C7 C8 C9 C10 C11 D1 D2 D3 F1 Q1 R1 R2 R3 R6 R7 R8 R10 R11 R12 R13 U2".split())
@lru_cache(maxsize=1)
def fab():
    data=json.loads((OUT/"fab.json").read_text(encoding="utf8"))
    if data["source_sha256"] != c.sha(c.PCB_FILE) or sorted(set(data["footprints"])-{"J1","J2","JP1","C2","U3","L1"}) != EXTRA:
        raise ValueError("C4 PCB or its footprint contract has changed")
    return data
def heights(ref):
    fid=fab()["footprints"][ref]["id"]
    if ref.startswith("R"):return .55
    if ref.startswith("C"):return 2.5 if "1210" in fid else (1.35 if "0805" in fid else .9)
    return {"D1":2.35,"D2":2.35,"D3":1.0,"F1":1.2,"Q1":1.8,"U2":1.7}[ref]
def numbered(prefix,n):return [f"{prefix}_{i+1:02d}" for i in range(n)]
PADS=numbered("TIM_ROOT",10); SHIMS=numbered("THERMAL_STANDOFF",4)
PINS=numbered("GUIDE_PIN",2); RUBBER=numbered("ELASTOMER_FOOT",4)
SCREWS=numbered("ROOF_SCREW",4); ALBOLTS=numbered("BRIDGE_SCREW",4)
FILES={"floor":[FLOOR],"chassis":[FRAME],"fascia":[IO],"roof":[ROOF],"radiator":[METAL],
       "keeper":[KEEP],"button":[c.BUTTON],"guide":[c.GUIDE,c.CARRIER],"feet":RUBBER,"locators":PINS,
       "isolators":SHIMS,"fasteners":SCREWS+ALBOLTS,"tim":PADS,"pcb":[c.BOARD],
       "packages":[c.USB,c.COIL,c.BULK,c.BUCK]+["FAB_"+r for r in EXTRA]}
COLORS={"floor":"#465159","chassis":"#465159","roof":"#465159","fascia":"#313a3f","radiator":"#a9aaa7",
        "keeper":"#71786f","button":"#666b6b","guide":"#5a625b","feet":"#393b3a","locators":"#858989",
        "isolators":"#c0ab83","fasteners":"#616467","tim":"#8a9da1","pcb":"#31614d","packages":"#4b4d4a"}
NAMES=sum(FILES.values(),[]); POWER=FILES["pcb"]+FILES["packages"]
def nameswap(q):
    q=copy.deepcopy(q);p=q["params"]
    for key in ("body","body_name"):
        if key in p:p[key]=MAP.get(p[key],p[key])
    if "targets" in p:p["targets"]=[MAP.get(n,n) for n in p["targets"]]
    return q
def slot_y(n,x,ya,yb,w,z,h,label):
    return [cmd("sketch.create",plane="XY",offset=z,name=label+" profile"),
            cmd("sketch.slot.overall",p0=[x,ya],p1=[x,yb],width=w),cmd("sketch.finish"),
            cmd("solid.extrude",operation="cut",targets=[n],distance=h,name=label)]
def roundbox(n,at,size,r,label):
    x,y,z=at;l,w,h=size
    return [box(n,"new",at,size,label),c.fil(n,[[u,v,z+h/2] for u in (x,x+l) for v in (y,y+w)],r)]
def socket(n,x,y,z,depth,r,angle):
    return [cmd("sketch.create",plane="XY",offset=z,name="Driver pocket"),
            cmd("sketch.polygon.inscribed",center=[x,y],radius=r,sides=6,angle=angle),cmd("sketch.finish"),
            cmd("solid.extrude",operation="cut",targets=[n],distance=depth,name="Hex socket")]
def port(x0,x1,z0,z1,r,label):
    return [box(IO,"cut",[x0,56.55,z0],[x1-x0,2.15,z1-z0],label),
            c.fil(IO,[[x,57.75,z] for x in (x0,x1) for z in (z0,z1)],r)]
def build():
    o=old.build(); groups={}
    groups["inherited parameters"]=o["dimensions"]
    for key in ("lid","chassis","mounts","fascia","front control","upright PCB / reference blower"):
        a=[]
        for raw in o[key]:
            q=nameswap(raw); p=q["params"]; nm=p.get("name","")
            if nm.startswith(("Collector","Lower bypass","Clear nearest low","J1 shell insertion stop","Space study")):continue
            if nm in ("Paired USB-A","HDMI and two Thunderbolt","RJ45 including latch"):continue
            if nm=="FDM blank":p["length"]+=2
            if key in ("lid","chassis") and q["command"]=="solid.fillet":
                for v in p["edges"]:
                    if v[0]>0:v[0]+=2
            if nm.startswith(("Tray source landing","Shallow rib")) and p["corner"][0]>0:p["length"]+=2
            if nm=="Outboard web" and p["corner"][0]>0:p["corner"][0]+=2
            if nm=="Upper fascia thrust seat" and p["corner"][0]>80:
                p["corner"][2]=29.65;p["height"]="c3_h-c3_wall-29.65 mm"
            if nm.startswith("Engraved PD legend"):
                x,y,z=p["corner"];p["corner"]=[2*79.55-x-p["length"],y,2*26.55-z-p["height"]]
            if nm.startswith("Rear exhaust"):p["name"]="High passive rear opening"
            if nm.startswith("Upper electronics ventilation"):p["name"]="Low passive rear opening"
            a.append(q)
        groups[key.replace("lid","floor").replace(" / reference blower","")]=a
    groups["tailored rounded port bays"]=(port(-58.55,-24.05,13.06,22.94,.8,"USB-A pair; full boot width")+
        port(-9.55,25.62,12.95,22.95,.8,"HDMI and first Thunderbolt share narrow bridge")+
        port(26.99,40.41,13.30,22.70,.8,"Second Thunderbolt")+
        port(55.71,73.59,9.,25.,.8,"Ethernet boot")+
        [box(IO,"cut",[57.55,56.55,24.8],[13.9,2.15,3.65],"Down-facing Ethernet latch"),
         c.fil(IO,[[57.55,57.75,28.45],[71.45,57.75,28.45]],.65)])
    symbol="C4_STANDBY_POCKET_TOOL"
    groups["engraved front button"]=[cmd("solid.chamfer",body=c.BUTTON,edges=[[6.1,-59.1,17.4]],distance=.22,name="Finger-friendly rim"),
        cyl(symbol,"new",[0,-59.16,17.4],6.60,.50,"Standby engraving tool","Y"),
        cyl(symbol,"cut",[0,-59.22,17.4],5.04,.66,"Ring inner profile","Y"),
        box(symbol,"cut",[-1.43,-59.22,13.7],[2.86,.66,2.65],"Open ring towards desk-up"),
        cmd("solid.combine",target=c.BUTTON,tools=[symbol],operation="cut",keep_tools=False),
        box(c.BUTTON,"cut",[-.42,-59.16,13.68],[.84,.50,3.45],"Engraved power stroke; no electrical change")]
    groups["open board insertion and register the cassette"]=[
        box(IO,"cut",[77.95,56.8,12.95],[16,.86,9.70],"Inner pocket for the J1 shell sweep; external mouth remains"),
        box(FRAME,"join",[-27.5,-57.5,.0],[7,4.8,18.1],"Front round guide boss tied to wall"),
        box(FRAME,"join",[86.5,GUIDES[1][1]-3.5,0],[6,7,18.1],"Side floating guide boss"),
        cyl(FRAME,"cut",[-24,-54.9,-.1],2.85,17.5,"Round locating bore")]
    x,y=GUIDES[1]; groups["open board insertion and register the cassette"]+=c.slot(FRAME,x-1.95,x+1.95,y,2.85,-.1,17.5,"Second guide floats along X")
    k=[box(KEEP,"new",[-40.48,47.87,34.03],[18.96,1.61,1.55],"Keeper bridge; bears on back of J1 shell")]
    for xh in (-38.5,-23.5):
        k += [box(KEEP,"join",[xh-1.98,47.87,32.4],[3.96,5.96,3.18],"Insulating ear shares J1-end board hole"),
              cyl(KEEP,"cut",[xh,51.85,32.3],1.82,3.5,"M1.6 candidate through keeper")]
    groups["removable connector keeper"]=[old.turn(q) for q in k]
    a=[]
    for ref in EXTRA:
        x0,y0,x1,y1=fab()["footprints"][ref]["fab_bbox_including_stroke_mm"]
        corners=np.array([c.xy(x0,y0),c.xy(x1,y1)])
        a.append(old.turn(box("FAB_"+ref,"new",[*corners.min(axis=0).tolist(),32.4],
                              [*np.ptp(corners,axis=0).round(6).tolist(),heights(ref)],ref+" F.Fab XY; ASSUMED component height")))
    groups["26 more KiCad package envelopes"]=a
    a=roundbox(ROOF,[-77.25,-57.25,-4.6],[169.5,117.5,4.6],5.75,"Removable FDM roof carrier")
    a += [cmd("solid.chamfer",body=ROOF,edges=[[0,-57.25,-4.6]],distance=.55,name="Soft roof rim"),
          box(ROOF,"cut",[-24.32,-45.32,-4.8],[78.64,100.64,2.3],"Recess around metal island; thermal expansion"),
          box(ROOF,"cut",[-16.8,-38.,-4.8],[65.35,84.4,5.1],"Central bridge through opening")]
    for i,(x,y) in enumerate(c.BASE_FIX):
        a += [cyl(ROOF,"cut",[x,y,-4.75],3.4,4.9,"Roof shank clearance"),
              cyl(ROOF,"cut",[x,y,-4.75],5.9,2.35,"Flush low socket head; chassis sets cassette height")]
    for x,y in c.TRAY_CENTRES:a.append(cyl(ROOF,"cut",[x,y,-2.45],6,2.6,"Existing tray-head clearance"))
    for x,y in c.SHEET_CENTRES:a.append(cyl(ROOF,"cut",[x,y,-2.6],2.8,2.8,"Underside metal attachment"))
    for x,y in GUIDES:a.append(cyl(ROOF,"cut",[x,y,-3.35],2.62,3.5,"Blind retained guide-pin seat; bonding system open"))
    for group,xx in VENTS.items():
        for x in xx:
            for ya,yb in VENT_SPANS:
                a+=slot_y(ROOF,x,ya,yb,2.8,-4.8,5.1,group+" high outlet")
                a+=slot_y(FLOOR,x,ya,yb,2.8,31.48,2.8,group+" low inlet")
    for n,(x,y) in zip(RUBBER,FEET):
        a += [cyl(FLOOR,"cut",[x,y,33.45],12.35,.75,"Adhesive foot location"),
              cyl(n,"new",[x,y,33.45],12.,6.55,"Replaceable elastomer foot"),
              c.fil(n,[[x+6,y,40]],.65)]
    groups["paired convection banks / feet / roof"]=a
    a=roundbox(METAL,[-24,-45,-6.5],[78.,100.,3.4],3.5,"One metal base; no adhesive joint between comb and fins")
    a.append(cmd("solid.chamfer",body=METAL,edges=[[10,-45,-6.5]],distance=.37,name="Finished metal edge"))
    crest=-6.5-FIN_H
    for x in FIN_X:
        a += [box(METAL,"join",[x-.85,-42.6,crest],[1.7,95.2,FIN_H+.10],"External longitudinal fin"),
              c.fil(METAL,[[x,-42.6,crest],[x,52.6,crest]],4.5),
              c.fil(METAL,[[x-.85,4,crest],[x+.85,4,crest]],.55)]
    for x,n in zip(TEETH,PADS):
        a += [box(METAL,"join",[x-.6,-14,-3.2],[1.2,40,17.7],"Internal comb blade; hard endpoint"),
              box(n,"new",[x-.6,-14,14.5],[1.2,40,.6],"Insulating compliant interface; installed nominal only")]
    for (x,y),n in zip(c.SHEET_CENTRES,SHIMS):
        a += [cyl(METAL,"cut",[x,y,-5.9],2.60,2.95,"Blind M2.5 thread envelope; thread not modeled"),
              cyl(n,"new",[x,y,-3.1],6.,.6,"Insulating height-setting shim; SKU open"),
              cyl(n,"cut",[x,y,-3.2],2.8,.85,"Shim clearance")]
    groups["machined or extruded and machined aluminium / interfaces"]=a
    a=[]
    for (x,y),n in zip(GUIDES,PINS):
        a += [cyl(n,"new",[x,y,-3.25],2.5,19.25,"Registered cassette guide; 16 mm projection"),
              cmd("solid.chamfer",body=n,edges=[[x+1.25,y,16]],distance=.38,name="Guide lead-in")]
    for i,((x,y),n) in enumerate(zip(c.BASE_FIX,SCREWS)):
        a += [cyl(n,"new",[x,y,-4.4],5.5,2.0,"M3 low head; nominal envelope"),
              cyl(n,"join",[x,y,-2.45],3.,8.05,"M3x8 simplified"),
              c.fil(n,[[x+2.75,y,-4.4]],.22)]
        a+=socket(n,x,y,-4.5,1.12,1.16,11+i*13)
    for (x,y),n in zip(c.SHEET_CENTRES,ALBOLTS):
        a += [cyl(n,"new",[x,y,0],4.7,1.5,"M2.5 low head inside carrier"),
              cyl(n,"join",[x,y,-5.5],2.5,5.55,"Simplified candidate shank; length subject to BOM")]
        a+=socket(n,x,y,1.6,-.9,1.01,13)
    groups["service hardware"]=a
    groups["desk datum"]=[cmd("solid.move",bodies=NAMES,axis=[0,1,0],angle=180,origin=[0,0,0],translate=[0,0,40],name="Desk Z0; front -Y; OEM fins face up")]
    return groups

def desk_obj(inp,out):
    with inp.open(encoding="utf8") as f,out.open("w",encoding="utf8") as g:
        for line in f:
            if line.startswith(("v ","vn ")):
                kind,x,y,z=line.split();g.write(f"{kind} {-float(x):.9f} {float(y):.9f} {(40 if kind=='v' else 0)-float(z):.9f}\n")
            else:g.write(line)

def batch(m,ops):
    r=m.json("batch",{"commands":ops,"verbose":False})
    if not r.get("ok"):raise ValueError(r)
def measures(m):return {b["name"]:b for b in m.json("measure",{"summary":True})["bodies"]}
def run():
    geo=OUT/"geometry"; geo.mkdir(exist_ok=True)
    record={"date":"2026-11-18","units":"mm, desk Z=0, rear +Y","pcb_sha256":fab()["source_sha256"],"digital_only":True}
    exchange={"c4-enclosure.step":[n for n in NAMES if n not in POWER],"c4-psu-envelope.step":POWER}
    with c.SolidCraftMCP(timeout=300) as m:
        for key,ops in build().items():
            print(key,len(ops),flush=True);batch(m,ops)
        bs=measures(m);assert set(bs)==set(NAMES) and all(v["closed"] and v["volume_mm3"]>0 for v in bs.values())
        t=m.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not [s for s in t if s.get("error")]
        record["native_features"]=len(t);record["warnings"]=[s for s in t if s.get("warning")]
        for key,nn in FILES.items():
            batch(m,[cmd("appearance.assign",bodies=nn,color=COLORS[key])])
            m.call("export",{"path":str(geo/(key+".glb")),"bodies":nn})
        for name,nn in exchange.items():m.call("export",{"path":str(OUT/name),"bodies":nn})
        for src,label in (("source-reference-no-legacy.obj","Retained SnazzyLabs SOURCE"),("front-switch-source-relocated.obj","Button reference; flex/actuation OPEN")):
            dest=geo/src;desk_obj(c.CAD/"interface-v1"/src,dest)
            batch(m,[cmd("file.insert_mesh",path=str(dest),units="mm",origin=False,name=label)])
        m.call("save",{"path":str(OUT/"c4-workbench.sc")})
    record["bodies"]=bs;record["readback"]={}
    for name,nn in exchange.items():
        with c.SolidCraftMCP(design=OUT/name,timeout=300) as m:
            back=measures(m);assert set(back)==set(nn)
            for n,b in back.items():
                assert b["closed"] and math.isclose(b["volume_mm3"],bs[n]["volume_mm3"],rel_tol=3e-5,abs_tol=1e-4),n
                assert all(np.allclose(b["bbox"][s],bs[n]["bbox"][s],atol=.002) for s in ("min","max")),n
            record["readback"][name]=len(nn)
    with c.SolidCraftMCP(design=OUT/"c4-workbench.sc",timeout=300) as m:
        d=m.json("inspect_design",{"measure":False,"sketches":False});assert len(d["bodies"])==len(NAMES)+6
        assert not [f for f in d["timeline"] if f.get("error")];record["readback"]["c4-workbench.sc"]=len(d["bodies"])
    c.dump(OUT/"cad-validation.json",record);print(record["readback"],flush=True)
if __name__=="__main__":run()
