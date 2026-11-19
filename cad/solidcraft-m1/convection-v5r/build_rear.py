"""C5R: one curved replaceable I/O inlay and two hidden fixings.
Build at the unchanged legacy connector datums; the last operation registers to the desk."""
from pathlib import Path
import sys, math, json
import numpy as np

OUT=Path(__file__).resolve().parent
C5=OUT.parent/"convection-v5"
sys.path.insert(0,str(C5))
import build_c5 as b
c,v=b.c,b.v
cmd,box,cyl=b.cmd,b.box,b.cyl
SKIN="C5R_IO_INLAY"
RIVETS=["C5R_INLAY_SCREW_L","C5R_INLAY_SCREW_R"]
FOOT_SCREWS=["C5R_UNDERSIDE_SCREW_L","C5R_UNDERSIDE_SCREW_R"]
FILES={**b.FILES,"inlay":[SKIN],"inlay_fixings":[*RIVETS,*FOOT_SCREWS]}
NAMES=sum(FILES.values(),[])
FIX=[(-15.,15.85),(46.,15.85)]
SIDE=[(-74.25,52.),(89.80,51.30)]
HOOD_FIX=[*b.HOOD_FIX[:2],*SIDE]
FIELD=59.72; BACK=58.68; WELL=58.19
FRAME,FLOOR,IO,ROOF=b.FRAME,b.FLOOR,b.IO,b.ROOF
def combine(dst,tool,op):return cmd("solid.combine",target=dst,tools=[tool],operation=op,keep_tools=False)
def rounded(dst,ranges,r,op,nm):
    tool="R_PROFILE_TOOL" if op!="new" else dst
    return b.rounded_xz(tool,*ranges,r,"new",nm)+([combine(dst,tool,op)] if op!="new" else [])
def opening(dst,x0,x1,z0,z1,r,label,y0=54.85,y1=60.05):
    return rounded(dst,(x0,x1,y0,y1,z0,z1),r,"cut",label)
def blade():
    # Ruled surface with two tangent cubic returns; no seam or individual well
    # separating Ethernet from the rest of the product. Sketch in Y,Z, extrude along X.
    outer=[[(FIELD,.9),(FIELD,8.)],[(FIELD,8.),(FIELD,9.85),(WELL,10.55),(WELL,12.55)],
           [(WELL,12.55),(WELL,28.30)],[(WELL,28.30),(WELL,29.52),(FIELD,30.00),(FIELD,30.98)],
           [(FIELD,30.98),(FIELD,32.)]]
    inner=[[(y-1.04,z) for y,z in seg[::-1]] for seg in outer[::-1]]
    edges=[*outer,[outer[-1][-1],inner[0][0]],*inner,[inner[-1][-1],outer[0][0]]]
    a=[cmd("sketch.create",plane="YZ",offset=-72.40,name="Rear face / two tangent full-width returns")]
    for e in edges:a+=[cmd("sketch.line" if len(e)==2 else "sketch.spline.control_point",points=e)]
    a += [cmd("sketch.finish"),cmd("solid.extrude",operation="new",body_name=SKIN,distance=159.65,name="Continuous 1.04 mm inlay in Y")]
    a+=rounded("R_TRIM",(-72.14,86.92,56.60,60.25,2.04,31.25),1.13,"new","Trim to case reveal")
    a += [combine(SKIN,"R_TRIM","intersect")]
    return a
def build():
    g=b.build()
    del g["continuous rear face and eight access windows"]
    old=g["fascia"]
    g["fascia"]=[q for i,q in enumerate(old) if i not in range(3,11)]
    # The short OEM flex, PSU and service-plug position do not change. The floor
    # fasteners now bear on the side walls, not on posts emerging between sockets.
    m=g["mounts"]; alt=[]
    for i,op in enumerate(m):
        p=op["params"];n=p.get("name","")
        if 12<=i<=23:continue
        if i in (49,50):continue
        if i in (40,41):p["base"][1]=55.60
        if n in ("Fascia tenon socket","Captured by lid; clearance each side 0.3","Additional PD-end fascia socket","Additional tenon clearance"):
            p["corner"][1]-=1.15
            if n=="Fascia tenon socket" and p["corner"][0]<0:
                p["corner"][1]+=.48;p["width"]-=.48
        alt.append(op)
    for (x,y),n in zip(SIDE,FOOT_SCREWS):
        d=5.26 if x>0 else 5.60
        alt+=[cyl(FRAME,"join",[x,y,18.9],d,6.1,"Rear floor anchor, screw from underside"),
              cyl(FRAME,"cut",[x,y,20.18],2.85,4.87,"M2 blind insert, opening towards the floor"),
              cyl(FRAME,"cut",[x,y,19.42],2.20,.85,"Tip reserve"),
              cyl(FLOOR,"join",[x,y,25.0],d,8.32,"Short side land for underside fixing"),
              cyl(FLOOR,"cut",[x,y,24.90],2.35,9.3,"Underside clearance through floor"),
              cyl(FLOOR,"cut",[x,y,30.65],4.30,3.7,"Underfloor screw pocket"),
              cyl(n,"new",[x,y,22.65],2.,8.1,"M2 x 8 rear closure shank, nominal"),
              cyl(n,"join",[x,y,30.65],3.80,1.65,"Rear closure head, below underside"),
              cyl(n,"cut",[x,y,31.50],1.80,.92,"Underside driver recess")]
    g["mounts"]=alt
    for key in ("printed roof, breathing floor and feet","removable lid fasteners"):
        for op in g[key]:
            p=op["params"]
            if "base" in p and p["base"][:2]==[-68,56.3]:p["base"][1]=55.60
            for e in p.get("edges",[]):
                if abs(e[1]-56.3)<.001:e[1]=55.60
            if p.get("center")==[-68,56.3]:p["center"][1]=55.60
    for op in g["fascia"]:
        p=op["params"]
        if p.get("name","") in ("Slot tenon","PD-end tenon"):p["corner"][1]-=1.15
    # The continuous sheet above each shifted tenon still engages it.
    arr=g["replaceable front control on fixed chassis"]
    j=next(i for i,s in enumerate(arr) if s["params"].get("name","")=="Fixed rear shelf under adapter mate")
    arr.insert(j,box(FRAME,"join",[49.05,55.55,2.84],[3.6,3.92,1.45],"Support service shelf from fixed upper sill"))
    arr[:]=[s for s in arr if not s["params"].get("name","").startswith("Reopen driver bore")]
    a=[]
    # Flush receiving pocket; the upper rail is still continuous behind the driver's land.
    for n in (FRAME,FLOOR):
        a+=rounded(n,(-72.45,87.23,58.58,61.,1.73,31.56),1.40,"cut","Register back blade inside case silhouette")
    # Keep left and right closure seats clear throughout the final 3.6-mm rear-module drop.
    a += opening(IO,-72.48,-63.58,4.58,7.78,.22,"Roof fixing clearance L")
    a += opening(IO,61.55,70.45,4.58,7.78,.22,"Roof fixing clearance R")
    # Recess the structural rib beneath the common port plane. Original upper tenons,
    # floor thrust seats and PSU rails keep their datums.
    a += [box(IO,"join",[-72.19,55.30,7.99],[159.14,1.80,22.84],"Forward web under inlay / bridges between groups"),
          box(IO,"cut",[-72.31,57.04,8.02],[159.58,2.02,22.82],"Clear entire swept port field, not separate tunnels")]
    for lo,top in [(-49.8,28.6),(-16.8,28.6),(60.5,28.6),(81.7,29.65)]:
        a += [box(IO,"cut",[lo-.34,55.15,top-.22],[4.88,1.68,31.5-top+.22],"Pocket existing floor thrust seat")]
    a += [box(IO,"cut",[74.05,55.19,7.60],[14.10,1.53,20.4],"Keep end of PCB and lateral insertion passage open")]
    for x0,x1,z0,z1,r,l in [(-59.6,-23.05,9.05,23.25,.65,"Twin A common bay and vertical carrier approach"),
        (-10.25,41.0,10.45,23.17,.66,"Display and Thunderbolt common bay and vertical approach"),
        (55.15,74.20,7.86,29.15,.70,"Network insertion, drop and latch envelope")]:
        a+=opening(IO,x0,x1,z0,z1,r,l)
    a+=opening(IO,-47.18,-35.54,7.90,13.70,.32,"Relieve entire SOURCE audio shield below carrier header")
    a+=[cyl(IO,"cut",[-41.3,54.85,7.8],8.95,5.3,"Large audio-boot access behind inlay","Y")]
    # Lip-side sweep only; do not notch the load-bearing longitudinal fork below the connector.
    a += [box(IO,"cut",[77.72,54.82,12.78],[16.,4.02,10.08],"Clear full side insertion of J1 on detached fork")]
    for x,z in FIX:
        a += [cyl(IO,"join",[x,53.17,z],7.80,2.36,"Inner seat for inlay fixing","Y"),
              cyl(IO,"cut",[x,53.06,z],2.35,4.15,"Screw clearance through carrier web","Y"),
              cyl(IO,"cut",[x,54.31,z],5.92,3.12,"Register integral inlay post behind the field","Y")]
    a+=blade()
    for x,z in FIX:
        a+=[cyl(SKIN,"join",[x,57.04,z],7.60,.34,"Two positive seating collars","Y"),
            cyl(SKIN,"join",[x,54.55,z],5.50,2.88,"Blind polymer fixing boss","Y"),
            cyl(SKIN,"cut",[x,54.45,z],1.68,3.00,"Thread-forming M2 pilot; prototype fit","Y")]
    for x in (-49.9,-32.7):
        a+=opening(SKIN,x-6.82,x+6.82,14.91,21.09,.65,"USB-A shield profile")
    a+=[cyl(SKIN,"cut",[-41.3,56.6,7.8],5.88,3.7,"Headphone rim clearance","Y")]
    x,z=1.525,17.9;tool="R_HDMI_KEY"
    a+=[box(tool,"new",[x-7.68,56.4,z-2.99],[15.36,4.45,5.98],"Keyed HDMI mouth"),
        cmd("solid.chamfer",body=tool,edges=[[x-7.68,58.2,z-2.99],[x+7.68,58.2,z-2.99]],distance=1.05,name="Polarized shield corners"),
        combine(SKIN,tool,"cut")]
    for x in (19.05,33.7):a+=opening(SKIN,x-4.79,x+4.79,16.02,19.98,1.94,"Thunderbolt shield profile")
    a+=opening(SKIN,58.12,71.18,12.86,20.91,.40,"Ethernet contact cavity")
    a+=opening(SKIN,61.00,68.30,19.95,22.96,.32,"Integrated Ethernet keyway")
    a+=opening(SKIN,77.88,81.98,12.82,22.78,1.98,"Vertical independent power inlet")
    for (x,z),n in zip(FIX,RIVETS):
        a+=[cyl(n,"new",[x,51.72,z],3.90,1.45,"Inlay fixing accessed from inside; head","Y"),
            cyl(n,"join",[x,53.13,z],1.60,4.04,"M2 x 4 thread root scenario; thread not modelled","Y"),
            cyl(n,"cut",[x,51.66,z],1.64,.78,"Driver recess envelope","Y")]
    register=g.pop("desk registration")
    g["flush rear interface"]=a
    register[0]["params"]["bodies"]=NAMES
    g["desk registration"]=register
    return g
def run():
    geo=OUT/"geometry";geo.mkdir(exist_ok=True)
    exchange={"c5r-enclosure.step":[n for n in NAMES if n not in b.POWER],"c5r-psu.step":b.POWER}
    rec={"date":"2026-11-18","units":"mm; desk basis","digital_only":True,"pcb_sha256":v.fab()["source_sha256"]}
    with c.SolidCraftMCP(timeout=350) as m:
        for key,ops in build().items():
            print(key,len(ops),flush=True);v.batch(m,ops)
        bs=v.measures(m);assert set(bs)==set(NAMES) and all(p["closed"] and p["volume_mm3"]>0 for p in bs.values())
        timeline=m.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not [t for t in timeline if t.get("error")];rec["native_features"]=len(timeline);rec["warnings"]=[t for t in timeline if t.get("warning")]
        for group,nn in FILES.items():
            v.batch(m,[cmd("appearance.assign",bodies=nn,color={"inlay":"#252b2e","inlay_fixings":"#464a4d"}.get(group,b.COLORS.get(group)))])
            v.batch(m,[cmd("file.export",path=str(geo/(group+".glb")),bodies=nn,quality="finest" if group=="wiring" else "standard")])
        for f,nn in exchange.items():m.call("export",{"path":str(OUT/f),"bodies":nn})
        v.batch(m,[cmd("file.insert_mesh",path=str(C5/"geometry/retained-source.obj"),units="mm",origin=False,name="Retained SnazzyLabs SOURCE / same registration")])
        m.call("save",{"path":str(OUT/"c5r-workbench.sc")})
    rec["bodies"]=bs;rec["readback"]={}
    for f,nn in exchange.items():
        with c.SolidCraftMCP(design=OUT/f,timeout=350) as m:
            fresh=v.measures(m);assert set(fresh)==set(nn)
            for n,p in fresh.items():
                assert p["closed"] and math.isclose(p["volume_mm3"],bs[n]["volume_mm3"],rel_tol=4e-5,abs_tol=.0002),n
                assert all(np.allclose(p["bbox"][key],bs[n]["bbox"][key],atol=.002) for key in ("min","max")),n
            rec["readback"][f]=len(nn)
    with c.SolidCraftMCP(design=OUT/"c5r-workbench.sc",timeout=350) as m:
        read=m.json("inspect_design",{"measure":False,"sketches":False});assert len(read["bodies"])==len(NAMES)+5 and not any(f.get("error") for f in read["timeline"])
        rec["readback"]["c5r-workbench.sc"]=len(read["bodies"])
    c.dump(OUT/"cad-validation.json",rec);print(rec["readback"],flush=True)
if __name__=="__main__":run()
