"""C5R-D1, two commercial power boards and a blank front. All new coordinates in desk mm."""
from pathlib import Path
import hashlib, json, math, sys
import numpy as np

OUT = Path(__file__).resolve().parent
REF = OUT.parent / "convection-v5r"
sys.path.insert(0, str(REF))
import build_rear as r

b, c, v = r.b, r.c, r.v
box, cyl, cmd = r.box, r.cyl, r.cmd
FRAME, PANEL = "D1_FIXED_CHASSIS", "D1_REAR_PORT_CARRIER"
SLED, CAP, BLANK = "D1_POWER_SLED", "D1_EDGE_RETAINER", "D1_FRONT_BLANK"
PD, BUCK, SOCKET = "D1_CMTPD_FR4_GAUGE", "D1_MINI560_FR4_GAUGE", "D1_USB_C_SHELL_GAUGE"
CHIPS = ["D1_CMTPD_POPULATION_GAUGE", "D1_MINI560_POPULATION_GAUGE"]
BACKS = ["D1_CMTPD_SOLDER_GAUGE", "D1_MINI560_SOLDER_GAUGE"]
NEW_SCREWS = ["D1_SLED_SCREW_A","D1_SLED_SCREW_B","D1_BAR_SCREW_A","D1_BAR_SCREW_B","D1_BAR_SCREW_C"]
BLANK_SCREWS = ["D1_BLANK_SCREW_A","D1_BLANK_SCREW_B"]
FILES = {"frame":[FRAME],"rear":[PANEL],"floor":[r.FLOOR],"roof":[r.ROOF],"inlay":[r.SKIN],
         "feet":b.FEET, "sled":[SLED],"retainer":[CAP],"blank":[BLANK],"boards":[PD,BUCK],
         "population":[*CHIPS,*BACKS],"socket":[SOCKET],"screws":[*b.SCREWS,*r.RIVETS,*r.FOOT_SCREWS,*NEW_SCREWS,*BLANK_SCREWS]}
NAMES = sum(FILES.values(), [])
COLORS = {"frame":"#414749","rear":"#42474a","floor":"#444c4c","roof":"#49504e","inlay":"#262b2c","feet":"#252928",
          "sled":"#548575","retainer":"#d39558","blank":"#454c4a","boards":"#294a65","population":"#616564","socket":"#9ba4a6","screws":"#6b6f70"}
MOUNTS = [(-86.8,-24.75),(-86.8,32.5)]
POSTS = [(-77.5,-24.75),(-77.5,11.35),(-84.90,44.0)]
Y_REAR, GAP, PD_L, PD_W, BUCK_L, BUCK_W = 56.35, 8., 41., 17., 29., 18.
Y_PD = Y_REAR-PD_L
Y_B = Y_PD-GAP
Y_F = Y_B-BUCK_L
CX, CZ, PCB_T = -77.5, 22.2, 1.60  # assumed FR4 thickness, both modules
GROOVE = 2.20                        # 0.30 nominal clearance per face at 1.60 FR4
PD_LOW,PD_HIGH=CZ-PD_W/2,CZ+PD_W/2
B_LOW,B_HIGH=CZ-BUCK_W/2,CZ+BUCK_W/2
BASE_Z, BAR_Z = 12.50, 31.72
SHELL_REAR, SHELL_FACE = 49.74, 57.09  # exact placement of the commercial USB shell is unmeasured
# Distance from each board's rear short edge. The shorter CMTPD land avoids the
# plated mounting rings beside USB and the next row of parts in the vendor photo.
PD_LANDS = [(5.90, 7.70), (33.15, 35.95)]
BUCK_LANDS = [(4.10, 6.10), (21.40, 23.80)]

def block(n,op,x0,y0,z0,x1,y1,z1,label):
    return box(n,op,[x0,y0,z0],[x1-x0,y1-y0,z1-z0],label)

def screw(n,x,y,z,diam,length,axis="Z",up=False):
    # z (or y for axis Y) is the head bearing plane. Effective screw travels in negative axis.
    pos=[x,y,z]; a=2 if axis=="Z" else 1
    p=pos.copy();p[a]-=.03 if up else length
    h=pos.copy();h[a]-=1.64 if up else 0.
    return [cyl(n,"new",p,diam,length+.03,"Nominal shank; no threads",axis),
            cyl(n,"join",h,3.80,1.64,"M2 head envelope",axis)]

def base():
    groups=r.build()
    old={"Open fork rail","Longitudinal web beside PCB; no unsupported chassis crossbar",
         "Saddle return clears laminate edge","Raised harness saddle on same removable fork as J2",
         "Removable small tie slot; route to Mac OPEN","Insulating support; allowable land OPEN",
         "M1.6 candidate clearance; retainer SKU OPEN","Recess low head below rail, nut above PCB; actual SKU OPEN"}
    groups["fascia"]=[op for op in groups["fascia"] if op["params"].get("name") not in old]
    assert len(groups["fascia"])==8
    for key in ("removable connector keeper","upright PCB","26 more KiCad package envelopes"):
        del groups[key]
    key="replaceable front control on fixed chassis"
    # Keep all physical chassis datums and standoffs for a later button, omit all electrical mockups.
    groups[key]=[op for op in groups[key] if op["params"].get("body")==r.FRAME or op["params"].get("targets")==[r.FRAME]]
    groups["flush rear interface"]=[op for op in groups["flush rear interface"] if op["params"].get("name")!="Clear full side insertion of J1 on detached fork"]
    kept=[r.FRAME,r.FLOOR,r.IO,r.ROOF,*b.FEET,*b.SCREWS,r.SKIN,*r.RIVETS,*r.FOOT_SCREWS]
    groups["desk registration"][0]["params"]["bodies"]=kept
    # Same features as C5R for the native I/O and envelope; unique names for the changed prints.
    return json.loads(json.dumps(groups).replace(r.FRAME,FRAME).replace(r.IO,PANEL))

def hardware():
    ops=[]
    for i,(x,y) in enumerate(MOUNTS):
        ops += [block(FRAME,"join",-90.6,y-3.3,22.20,-83.55,y+3.3,27.35,"Overhead seat; cassette releases through open floor"),
                cyl(FRAME,"cut",[x,y,22.10],1.70,4.65,"Underside blind M2 pilot for plastic-forming screw")]
        ops += screw(NEW_SCREWS[i],x,y,20.,2.,6.,up=True)
    ops += [block(PANEL,"cut",-81.00,53.8,29.65,-74.9,58.12,34.13,"Hidden relief for the upper FR4 end fence"),
            block(PANEL,"cut",-81.90,54.5,17.38,-77.98,57.56,27.02,"Throat clears commercial USB shell on its way to the inlay")]
    for i,(x,y) in enumerate(POSTS):
        ops+=screw(NEW_SCREWS[2+i],x,y,33.84,2.,6.)
    # Use the existing rear-facing M2 insert positions on the front wall. No loose plug or flex.
    ops += [block(BLANK,"new",-85.75,-53.44,14.95,-77.25,-51.64,35.45,"Back plate on the two original C5R button bosses"),
            cyl(BLANK,"join",[-81.5,-59.65,25.2],7.80,6.35,"Solid stem, cannot actuate a switch","Y"),
            cyl(BLANK,"join",[-81.5,-61.36,25.2],10.10,1.90,"Cap recessed 0.14 mm from the front face","Y")]
    for i,z in enumerate((17.50,32.90)):
        ops += [cyl(BLANK,"cut",[-81.5,-53.54,z],2.45,2.03,"M2 removable blank clearance","Y")]
        ops+=screw(BLANK_SCREWS[i],-81.5,-51.64,z,2.,4.,"Y")
    return ops

def clamp(n, low, y, width, edge, back_only=False):
    # Only short ledges on the long FR4 edges. Broad components and castellated ends stay open.
    root=BASE_Z if low else BAR_Z
    a,bz=sorted((root+(-.08 if low else .08),edge))
    tip=edge+(.72 if low else -.72)
    z0,z1=sorted((edge+(-.12 if low else .12),tip))
    face=[] if back_only else [block(n,"join",-79.72,y,z0,CX-GROOVE/2,y+width,z1,"Outward FR4 edge lip")]
    return [block(n,"join",CX-.25 if back_only else -79.40,y,a,-75.60,y+width,bz,"Short edge seat"),*face,
            block(n,"join",CX+GROOVE/2,y,z0,-75.28,y+width,z1,"Inward FR4 edge lip")]

def carriage():
    a=[block(SLED,"new",-80.40,Y_F-5.50,10.42,-75.15,54.70,BASE_Z,"Spine ends 0.60 mm before the rear carrier; both board faces exposed"),
       block(CAP,"new",CX-.25,Y_F-5.50,BAR_Z,-75.15,54.10,33.84,"Continuous upper rail runs on the unpopulated side of the buck"),
       block(CAP,"join",-80.40,Y_F-5.50,BAR_Z,-75.15,Y_F-.20,33.84,"Front post fixing pad"),
       block(CAP,"join",-80.40,Y_B+.20,BAR_Z,-75.15,54.10,33.84,"Full retainer over the trigger and two remaining fixing posts"),
       block(CAP,"join",-80.40,Y_B-6.55,BAR_Z,-75.15,Y_B-3.75,33.84,"Single full-width buck pad over the free edge beside the choke")]
    # Two short lands per PCB, away from the plated end connections. Lower edge is the Z datum.
    for rear,lands,lo,hi,is_buck in [(Y_B,BUCK_LANDS,B_LOW,B_HIGH,True),(Y_REAR,PD_LANDS,PD_LOW,PD_HIGH,False)]:
        for start,end in lands:
            a+=clamp(SLED,True,rear-end,end-start,lo)
            a+=clamp(CAP,False,rear-end,end-start,hi+.35,back_only=(is_buck and start>7.))
    # Front and middle pillars; outboard rear pillar leaves the PD button and terminal pads open.
    for x,y in POSTS[:2]:
        a += [block(SLED,"join",x-2.55,y-2.7,12.38,x+2.50,y+2.70,BAR_Z,"Insulating upper bar screw column")]
    x,y=POSTS[2]
    a += [block(SLED,"join",x-2.20,y-2.7,10.42,-77.45,y+2.70,BASE_Z,"Outboard pillar lower crosspiece"),
          block(SLED,"join",x-2.20,y-2.7,12.38,x+2.15,y+2.70,BAR_Z,"Third column outside populated PD face"),
          block(CAP,"join",x-2.20,y-2.7,BAR_Z,-77.45,y+2.70,33.84,"Outboard retainer ear")]
    for x,y in POSTS:
        a += [cyl(SLED,"cut",[x,y,26.7],1.70,5.22,"Blind pilot for M2 plastic screw"),
              cyl(CAP,"cut",[x,y,BAR_Z-.1],2.45,2.5,"Retainer clearance; clamping force goes to pillar, not PCB")]
    # End fences set Y with 0.3 mm play. They contact the narrow end face, not the plated faces.
    for y0,y1 in [(Y_F-1.7,Y_F-.30),(Y_B+.30,Y_B+1.8),(Y_PD-1.8,Y_PD-.30)]:
        a += [block(SLED,"join",CX-.65,y0,12.38,CX+.65,y1,15.35,"Positive lower end fence")]
    # Rear PCB corner captured on withdrawal, while the independent metal-shell shoulders take insertion.
    a += [block(CAP,"join",-78.85,53.65,BAR_Z,-76.15,57.76,33.55,"Short upper extension for capture on cable withdrawal"),
          block(CAP,"join",-78.40,Y_REAR+.27,29.98,-76.55,57.76,32.05,"Rear FR4 end fence above USB, inside relieved structural face"),
          block(CAP,"join",-81.30,SHELL_REAR-1.85,26.04,-78.75,SHELL_REAR-.25,32.08,"Upper metal shell thrust finger"),
          block(SLED,"join",-81.30,SHELL_REAR-1.85,12.22,-78.75,SHELL_REAR-.25,18.37,"Lower metal shell thrust finger")]
    # Strain relief forward of converter: tie goes through the transverse slot, only around insulated leads.
    a += [block(SLED,"join",-84.7,Y_F-12.3,10.42,-77.1,Y_F-4.60,15.70,"Output wire saddle"),
          block(SLED,"cut",-84.9,Y_F-10.1,12.05,-76.9,Y_F-6.8,14.25,"Through slot for a 2.5 mm cable tie")]
    a += [block(SLED,"join",-89.15,-27.55,20.,-77.20,-22.05,22.20,"Front chassis mounting ear"),
          block(SLED,"join",-86.50,30.65,20.,-83.05,44.50,22.20,"Rear outrigger to third column"),
          block(SLED,"join",-89.15,29.70,20.,-83.30,35.30,22.20,"Rear chassis mounting ear")]
    for x,y in MOUNTS:
        a += [cyl(SLED,"cut",[x,y,19.90],2.45,2.40,"Mount clearance on fixed wall socket")]
    return a

def gauges():
    x0,x1=CX-PCB_T/2,CX+PCB_T/2
    return [block(PD,"new",x0,Y_PD,PD_LOW,x1,Y_REAR,PD_HIGH,"CMTPD seller outline; assumed laminate"),
            block(BUCK,"new",x0,Y_F,B_LOW,x1,Y_B,B_HIGH,"Mini-560 seller outline; assumed laminate"),
            block(SOCKET,"new",-81.55,SHELL_REAR,17.73,x0,SHELL_FACE,26.67,"CMTPD mating-shell alignment gauge, not vendor CAD"),
            block(CHIPS[0],"new",-82.30,Y_PD+.65,PD_LOW+.90,x0,SHELL_REAR-2.2,PD_HIGH-.90,"Assumed population outside USB and edge-contact lands"),
            block(CHIPS[0],"join",-82.30,Y_REAR-28.45,PD_LOW,x0,Y_REAR-8.95,PD_HIGH,"CMTPD center region can be populated to either long edge; includes visible mode switch"),
            block(CHIPS[1],"new",-82.10,Y_F,B_LOW+.90,x0,Y_B,B_HIGH-.90,"Mini-560 total 5.4 mm; face and edge allowance to verify"),
            block(CHIPS[1],"join",-82.10,Y_F,B_HIGH-1.5,x0,Y_B-7.,B_HIGH+.70,"4R7 and close-edge capacitors may project 0.7 mm beyond upper FR4 edge"),
            block(CHIPS[1],"join",-82.10,Y_B-3.4,B_HIGH-1.5,x0,Y_B,B_HIGH+.70,"Upper rear terminal and solder; keep the populated face open"),
            block(BACKS[0],"new",x1,Y_PD,PD_LOW+.90,x1+1.,Y_REAR,PD_HIGH-.90,"Assumed 1 mm backside solder; bare edge lands must be measured"),
            block(BACKS[1],"new",x1,Y_F,B_LOW+.90,x1+1.,Y_B,B_HIGH-.90,"Assumed 1 mm backside solder; bare edge lands must be measured")]

def seed():
    # A native stage with its feature tree intact. Reused only for identical upstream commands.
    gs=base()
    digest=hashlib.sha256(json.dumps(gs,sort_keys=True).encode()).hexdigest()[:16]
    path=OUT.parents[2]/"tmp"/("d1-base-"+digest+".sc")
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        with c.SolidCraftMCP(timeout=300) as m:
            for key,ops in gs.items():
                print(key,len(ops),flush=True);v.batch(m,ops)
            m.call("save",{"path":str(path)})
    return path

def run():
    geo=OUT/"geometry"; geo.mkdir(exist_ok=True)
    groups={"Mounts and blank":hardware(),"Split side carrier":carriage(),"Two module gauges":gauges()}
    plastics=[FRAME,PANEL,SLED,CAP,BLANK,r.FLOOR,r.ROOF,r.SKIN]
    files={"d1-printable.step":plastics,"d1-assembly.step":NAMES}
    record={"variant":"C5R-D1 / fit prototype without electrical button","date":"2026-11-18","units":"mm / desk registration"}
    with c.SolidCraftMCP(design=seed(),timeout=300) as m:
        for key,ops in groups.items():
            print(key,len(ops),flush=True); v.batch(m,ops)
        bodies=v.measures(m)
        assert set(bodies)==set(NAMES) and all(x["closed"] and x["volume_mm3"]>0 for x in bodies.values())
        t=m.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not [i for i in t if i.get("error")]; record.update(features=len(t),warnings=[i for i in t if i.get("warning")])
        for g,ns in FILES.items():
            v.batch(m,[cmd("appearance.assign",bodies=ns,color=COLORS[g]),cmd("file.export",path=str(geo/(g+".glb")),bodies=ns,quality="standard")])
        for f,ns in files.items():m.call("export",{"path":str(OUT/f),"bodies":ns})
        v.batch(m,[cmd("file.insert_mesh",path=str(r.C5/"geometry/retained-source.obj"),units="mm",origin=False,name="Retained SnazzyLabs SOURCE, C5R datum")])
        m.call("save",{"path":str(OUT/"d1-workbench.sc")})
    back={}
    for f,ns in files.items():
        with c.SolidCraftMCP(design=OUT/f,timeout=300) as m:
            solids=v.measures(m); assert set(solids)==set(ns)
            for n,p in solids.items():
                assert p["closed"] and math.isclose(p["volume_mm3"],bodies[n]["volume_mm3"],rel_tol=.00006,abs_tol=.0003),n
                assert all(np.allclose(p["bbox"][e],bodies[n]["bbox"][e],atol=.003) for e in ("min","max")),n
            back[f]=len(solids)
    with c.SolidCraftMCP(design=OUT/"d1-workbench.sc",timeout=300) as m:
        scene=m.json("inspect_design",{"measure":False,"sketches":False})
        assert len(scene["bodies"])==len(NAMES)+5 and not any(i.get("error") for i in scene["timeline"])
        back["d1-workbench.sc"]=len(scene["bodies"])
    c.dump(OUT/"cad-validation.json",{**record,"readback":back,"bodies":bodies}); print("readback:",back,flush=True)

if __name__=="__main__":run()
