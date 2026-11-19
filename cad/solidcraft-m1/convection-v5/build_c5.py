"""C5. Native mm geometry; construct at the SOURCE datums, register once to the desk.
The front harness ends at a service interface. No guessed Mac plug or copper mapping."""
from pathlib import Path
import copy, json, math, sys
import numpy as np

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/"passive-v4"))
import build_c4 as v
c=v.c
cmd,box,cyl=c.cmd,c.box,c.cyl
FLOOR,FRAME,IO,ROOF,KEEP=("C5_"+s for s in ("LOWER_SHELL","FIXED_CHASSIS","REAR_FACE_AND_PD_FORK","VENTED_LID","J1_KEEPER"))
SW,CAP,PCB,PLUG,HALF=("C5_"+s for s in ("SWITCH_BODY","SWITCH_CAP","BUTTON_FR4","SERVICE_PAIR_A","SERVICE_PAIR_B"))
WIRE=["C5_BUTTON_LEAD_A","C5_BUTTON_LEAD_B"]
M2=["C5_SWITCH_SCREW_A","C5_SWITCH_SCREW_B"]
PINS=v.numbered("C5_SWITCH_LEG",6)
FEET=v.numbered("C5_FOOT",4);SCREWS=v.numbered("C5_ROOF_FIXING",4)
FILES={"floor":[FLOOR],"chassis":[FRAME],"fascia":[IO],"roof":[ROOF],"keeper":[KEEP],"feet":FEET,
       "button":[SW,CAP,PCB,*PINS],"wiring":[*WIRE,PLUG,HALF],"fasteners":[*SCREWS,*M2],
       "pcb":v.FILES["pcb"],"packages":v.FILES["packages"]}
COLORS={"floor":"#474e50","chassis":"#474e50","fascia":"#303637","roof":"#474e50","keeper":"#555d56",
        "feet":"#262c2b","button":"#848882","wiring":"#8b7360","fasteners":"#414749","pcb":"#315946","packages":"#555753"}
NAMES=sum(FILES.values(),[]);POWER=FILES["pcb"]+FILES["packages"];AX=v.TEETH
ROOF_SPANS=[(-25.,3.2),(6.,34.2)];PD_SPANS=[(-16.,3.2),(6.,30.)]
PD_X=[75.8,81.3,86.8]
IN_SPAN=(-57.8,-32.4);VENT_W=3.8;IN_W=4.1;PD_W=2.8
BUTTON_X,BUTTON_Z=81.5,14.8
FRONT=-61.5;PCB_Y=-53.44;FACE_Y=62.2
HOOD_FIX=[(57. if x==35 and y<0 else x,y-3.2 if y<0 else y) for x,y in c.HOOD_FIX]
# Legacy x increases to the right as seen by somebody facing the *back*. z increases down.
PORTS=[(-58.52,-41.73,13.05,22.95,.42,"USB-A 1"),(-40.87,-24.08,13.05,22.95,.42,"USB-A 2"),
       (-9.55,12.095,12.95,22.85,.42,"HDMI"),(12.98,25.6,13.25,22.75,.42,"Thunderbolt 1"),
       (26.96,40.44,13.24,22.76,.48,"Thunderbolt 2"),(55.71,73.59,9.,25.,.65,"Ethernet"),
       (76.08,83.80,11.12,24.48,.5,"PD power outer boot")]
LEGENDS=[(-56.7,7.65,"AUDIO"),(-41.3,26.42,"USB-A"),(1.525,26.42,"HDMI"),(19.05,26.42,"TB 1"),
         (33.7,26.42,"TB 2"),(64.65,6.2,"ETH"),(79.93,6.2,"PD IN")]
RENAME={v.FLOOR:FLOOR,v.FRAME:FRAME,v.IO:IO,v.KEEP:KEEP}
def rename(q):
    p=q["params"]
    for f in ("body_name","body","target"):
        if f in p:p[f]=RENAME.get(p[f],p[f])
    if "targets" in p:p["targets"]=[RENAME.get(n,n) for n in p["targets"]]
    return q
def rounded_xz(n,x0,x1,y0,y1,z0,z1,r,op,label):
    return [box(n,op,[x0,y0,z0],[x1-x0,y1-y0,z1-z0],label),
            c.fil(n,[[x,(y0+y1)/2,z] for x in (x0,x1) for z in (z0,z1)],r)]
def aperture(x0,x1,z0,z1,r,label,at=56.5):
    # Round the cutter before reaching the stepped back, to keep the socket profile
    # identical through the entire skin even where the inner fork has pillar relief.
    tool="C5_PORT_TOOL"
    return rounded_xz(tool,x0,x1,at,FACE_Y+.2,z0,z1,r,"new",label)+[
        cmd("solid.combine",target=IO,tools=[tool],operation="cut",keep_tools=False)]
def wire_points(i):
    # Two insulated leads from separate pads on the small FR4. Ends touch the removable
    # service connector near the OEM button region, not the unidentified board socket.
    dz=(-.68,.68)[i]; xx=(84.65,86.25)[i]
    path=[[xx,-52.44,14.8+dz],[xx,-50.9,14.8+dz],[xx+.22,-49.1,14.8+dz],
        [87.0+(.24 if i else -.24),-45.7,14.8+dz],[88.05,-41,14.8+dz],
        *[[88.1,y,14.8+dz] for y in (-34,-22,-8,5,18,26,31)],
        [88.1,34.2,14.45+dz],[88.1,36.9,12.7+dz],[88.1,39.0,8.65+dz],
        [87.8,40.5,5.4+dz],[86.1,42,3.52+dz],[83.4,43.5,2.55+dz],
        [79.5,44.8,2.45+dz],[73,46,2.45+dz],[65.5,46.7,2.45+dz],[60,46.8,2.45+dz],[56.4,46.8,2.45+dz]]
    for pt in path:
        f=max(0.,min(1.,(pt[1]-26)/8,(44-pt[1])/3.))
        pt[0]+=.36*max(0.,min(1.,(pt[0]-87.)/1.1))
        pt[0]+=dz*f;pt[1]+=dz*1.8*f
    return path
def build():
    o=v.build(); g={"shared datums":o["inherited parameters"]}
    for group in ("floor","chassis","mounts","fascia","removable connector keeper","upright PCB","26 more KiCad package envelopes"):
        a=[]
        for raw in o[group]:
            q=rename(copy.deepcopy(raw));p=q["params"];label=p.get("name","")
            if label in ("Original front button guide","Low exhaust sill","Lower exhaust tongue") or label.startswith(("Engraved PD","High passive rear","Low passive rear")):continue
            if group in ("floor","chassis"):
                if label=="FDM blank": p["corner"][1]-=4;p["width"]+=4
                if "edges" in p:
                    for pt in p["edges"]:
                        if pt[1]<-56:pt[1]-=4
            if group=="mounts":
                if label in ("Hidden lid screw pillar","Roof boss above pillar") and p["corner"][1]<0:
                    p["corner"][1]-=3.2
                    if p["corner"][0]>0:p["corner"][0]+=22
                if label in ("Underside driver and head passage","M2 shank only","M2 insert pilot ASSUMED","Blind tip reserve") and p["base"][1]<0:
                    p["base"][1]-=3.2
                    if p["base"][0]>0:p["base"][0]+=22
                if label=="Independent bottom closure" and p["corner"][1]<0:p["corner"][1]-=4;p["width"]+=4
            a.append(q)
        g[group]=a
    # Retain the insertion relief on the inner fork. A solid skin covers every post.
    a=[box(IO,"cut",[77.95,56.8,12.95],[16,.86,9.70],"J1 insertion sweep, internal only"),
       box(IO,"join",[-72.18,58.465,4.84],[159.14,2.36,26.42],"Full depth backplate support")]
    for x0,x1,z0,z1 in [(-65.82,-58.18,4.65,31.6),(45.68,53.32,4.65,31.6),(-72.4,-63.68,4.65,7.75),
                           (61.65,70.35,4.65,7.75),(-58.65,-49.35,4.55,5.06),(53.35,62.65,4.55,5.06),(77.35,86.65,4.55,5.06)]:
        a.append(box(IO,"cut",[x0,58.45,z0],[x1-x0,2.20,z1-z0],"Hidden pillar / closure clearance"))
    mask="C5_FACE_BLANK"
    a+=rounded_xz(mask,-73.18,88.08,60.70,FACE_Y,1.35,32.34,2.35,"new","Continuous rounded outer face")
    a += [cmd("solid.chamfer",body=mask,edges=[[0,FACE_Y,1.35]],distance=.28,name="Soft face perimeter"),
          cmd("solid.combine",target=IO,tools=[mask],operation="join",keep_tools=False)]
    for p in PORTS:a+=aperture(*p,at=58.505 if p[-1].startswith("PD ") else 56.53)
    a+=aperture(77.70,82.13,12.35,23.25,.38,"Continuous J1 neck throat",at=57.63)
    a += [cyl(IO,"cut",[-41.3,56.49,7.8],8.55,6.1,"Headphone collar through both levels","Y")]
    a += aperture(57.43,71.86,23.85,28.65,.65,"Downward latch relief")
    g["continuous rear face and eight access windows"]=a
    # Internal roof pocket leaves a 2.4-mm vented skin at desk Z=43.6. Pillar pads remain solid.
    a=v.roundbox(ROOF,[-77.25,-61.25,-6],[169.5,121.5,6],5.75,"Solid roof blank")
    a += [cmd("solid.chamfer",body=ROOF,edges=[[0,-61.25,-6]],distance=.9,name="Soft roof edge"),
          box(ROOF,"cut",[-71.7,-44.6,-3.6],[133.5,94.2,3.8],"Plenum above OEM fins"),
          box(ROOF,"cut",[71.4,-36,-3.6],[18.3,79.2,3.8],"Power-side high plenum")]
    for x,y in c.BASE_FIX:
        a += [cyl(ROOF,"cut",[x,y,-6.1],3.4,6.3,"Shank clearance"),
              cyl(ROOF,"cut",[x,y,-6.1],5.9,2.33,"Flush fixing head")]
    for x,y in c.TRAY_CENTRES:a.append(cyl(ROOF,"cut",[x,y,-2.4],6.,2.55,"Tray fixing head clearance"))
    for x in AX:
        for lo,hi in ROOF_SPANS:a+=v.slot_y(ROOF,x,lo,hi,VENT_W,-6.15,6.35,"Exhaust in line with OEM channel")
        a+=v.slot_y(FLOOR,x,*IN_SPAN,IN_W,31.48,2.8,"Under-nose intake")
    for x in PD_X:
        for lo,hi in PD_SPANS:
            a+=v.slot_y(ROOF,x,lo,hi,PD_W,-6.15,6.35,"Power bay outlet")
            a+=v.slot_y(FLOOR,x,lo,hi,PD_W,31.48,2.8,"Power bay inlet")
    for x0,x1 in [(AX[i]-2.38,AX[i+1]+2.38) for i in range(0,10,2)]:
        a += rounded_xz("C5_NOSE_TOOL",x0,x1,FRONT-.2,FRONT+3.0,26.55,30.9,1.55,"new","Low horizontal nose intake")
        a += [cmd("solid.combine",target=FLOOR,tools=["C5_NOSE_TOOL"],operation="cut",keep_tools=False)]
    for n,(x,y) in zip(FEET,v.FEET):
        a += [cyl(FLOOR,"cut",[x,y,33.45],12.35,.75,"Foot pocket"),cyl(n,"new",[x,y,33.45],12,6.55,"Elastomer foot"),
              c.fil(n,[[x+6,y,40]],.65)]
    g["printed roof, breathing floor and feet"]=a
    a=[]
    for idx,((x,y),n) in enumerate(zip(c.BASE_FIX,SCREWS)):
        a += [cyl(n,"new",[x,y,-5.77],5.5,2,"Dark flush roof fixing"),cyl(n,"join",[x,y,-3.79],3,8.02,"M3 x 8 scenario"),c.fil(n,[[x+2.75,y,-5.77]],.2)]
        a+=v.socket(n,x,y,-5.85,1.09,1.16,11+idx*13)
    g["removable lid fasteners"]=a
    x,z=BUTTON_X,BUTTON_Z
    a=[cyl(FRAME,"cut",[x,FRONT-.2,z],10.7,3.5,"Bezel running clearance; cap has its own OEM guide","Y"),
       cmd("solid.chamfer",body=FRAME,edges=[[x+5.35,FRONT,z]],distance=.24,name="Finger edge break"),
       box(PCB,"new",[x-6.25,PCB_Y,z-9.95],[12.5,1.,19.9],"Removable FR4 switch board")]
    for k,n in zip((z-7.7,z+7.7),M2):
        a += [cyl(FRAME,"join",[x,FRONT+2.1,k],5.9,PCB_Y-(FRONT+2.1),"Integral button standoff","Y"),
              cyl(FRAME,"cut",[x,PCB_Y-4.7,k],2.85,4.8,"M2 insert pocket; blind at front","Y"),
              cyl(PCB,"cut",[x,PCB_Y-.1,k],2.3,1.25,"M2 clearance","Y"),
              cyl(n,"new",[x,PCB_Y-3,k],2,4.08,"M2 x 4 button carrier","Y"),
              cyl(n,"join",[x,PCB_Y+1,k],3.65,1.5,"Button screw head","Y"),
              cyl(n,"cut",[x,PCB_Y+1.7,k],1.60,1.0,"Recess, head envelope","Y")]
    a += [cyl(FRAME,"cut",[x,FRONT+2.05,z],10.70,6.1,"Clear bezel across inner post roots","Y"),
          box(FRAME,"cut",[x-3.1,FRONT+2.07,24.84],[6.2,6.09,1.4],"Keep bottom standoff off removable floor")]
    a += [box(SW,"new",[x-3.0,PCB_Y-4.85,z-3.05],[6.,4.85,6.10],"Switch base envelope"),
          cyl(SW,"join",[x,-60.82,z],9.8,2.72,"Stationary bezel per datasheet","Y"),
          cyl(SW,"cut",[x,-60.9,z],8.36,1.92,"Cap guide opening","Y"),
          cyl(CAP,"new",[x,PCB_Y-8.4,z],8.2,1.97,"Actuating cap; datasheet OD and overall height","Y"),
          c.fil(CAP,[[x+4.1,PCB_Y-8.4,z]],.20)]
    pads=[(-2.25,-3.25),(-2.25,3.25),(2.25,-3.25),(2.25,3.25),(-2.7,0),(2.7,0)]
    for i,((dx,dz),n) in enumerate(zip(pads,PINS)):
        a += [cyl(PCB,"cut",[x+dx,PCB_Y-.1,z+dz],1.,1.2,"Switch footprint through hole","Y"),
              box(n,"new",[x+dx-.2,PCB_Y,z+dz-.10],[.4,(3.2 if i<4 else (4.1,5.6)[i-4]),.20],"Simplified untrimmed lead keepout")]
    # Small open-top cradles on fixed wall; thread/release the pair with the roof off.
    for y in (-32.,-5.,24.):
        a.extend([box(FRAME,"join",[87.06,y-1.55,16.20],[3.74,3.1,1.45],"Signal pair shelf"),
                  box(FRAME,"join",[87.06,y-1.55,13.8],[.80,3.1,2.60],"Low retaining lip; press-in foam strip optional")])
    # Socket sits in the rear service region beside the fixed pillar, without a model of the Mac ZIF.
    a += [box(FRAME,"join",[49.05,44.,4.0],[3.6,12.1,1.19],"Fixed rear shelf under adapter mate"),
          box(FRAME,"join",[49.4,44.,2.35],[3.6,.60,2.25],"Service socket saddle, front cheek"),
          box(FRAME,"join",[49.4,48.98,2.35],[3.6,.70,2.25],"Service socket saddle, rear cheek"),
          cyl(FRAME,"cut",[49.5,57.8,-.12],4.60,7.2,"Reopen driver bore through the joined shelf root"),
          box(PLUG,"new",[53.35,44.75,.92],[3.05,4.10,3.06],"Harness-side detachable two-way housing, envelope only"),
          cmd("solid.chamfer",body=PLUG,edges=[[53.35,46.8,.92]],distance=.15,name="Service plug thumb edge"),
          box(HALF,"new",[49.85,44.75,.92],[3.50,4.10,3.06],"Adapter-side mate; Mac-side termination OPEN"),
          cmd("solid.chamfer",body=HALF,edges=[[53.35,46.8,.92]],distance=.15,name="Visible separable joint")]
    for i,n in enumerate(WIRE):
        nm="Signal lead "+str(i+1)
        a += [cmd("sketch.create",plane="XY",name=nm),cmd("sketch.options",sketch_3d=True),
              cmd("sketch.spline3d",points=wire_points(i)),cmd("sketch.finish"),
              cmd("solid.pipe",path_sketch=nm,path=["w1"],diameter=.87,operation="new",body_name=n,name="Insulated button lead, assumed")]
    g["replaceable front control on fixed chassis"]=a
    g["desk registration"]=[cmd("solid.move",bodies=NAMES,axis=[0,1,0],angle=180,origin=[0,0,0],translate=[0,0,40],name="Desk Z0 / rear +Y / OEM fins up")]
    return g
def run():
    geo=OUT/"geometry";geo.mkdir(exist_ok=True)
    rec={"date":"2026-11-18","units":"mm, desk Z=0, rear +Y","pcb_sha256":v.fab()["source_sha256"],"digital_only":True}
    exchange={"c5-enclosure.step":[n for n in NAMES if n not in POWER],"c5-psu-envelope.step":POWER}
    with c.SolidCraftMCP(timeout=350) as m:
        for key,ops in build().items():
            print(key,len(ops),flush=True);v.batch(m,ops)
        bs=v.measures(m);assert set(bs)==set(NAMES) and all(b["closed"] and b["volume_mm3"]>0 for b in bs.values())
        health=m.json("inspect_design",{"measure":False,"sketches":False})["timeline"]
        assert not [f for f in health if f.get("error")];rec["native_features"]=len(health);rec["warnings"]=[f for f in health if f.get("warning")]
        for group,nn in FILES.items():
            v.batch(m,[cmd("appearance.assign",bodies=nn,color=COLORS[group])])
            v.batch(m,[cmd("file.export",path=str(geo/(group+".glb")),bodies=nn,quality="finest" if group=="wiring" else "standard")])
        for file,nn in exchange.items():m.call("export",{"path":str(OUT/file),"bodies":nn})
        src=geo/"retained-source.obj";v.desk_obj(c.CAD/"interface-v1/source-reference-no-legacy.obj",src)
        v.batch(m,[cmd("file.insert_mesh",path=str(src),units="mm",origin=False,name="Five retained SnazzyLabs SOURCE bodies")])
        m.call("save",{"path":str(OUT/"c5-workbench.sc")})
    rec["bodies"]=bs;rec["readback"]={}
    for file,nn in exchange.items():
        with c.SolidCraftMCP(design=OUT/file,timeout=350) as m:
            back=v.measures(m);assert set(back)==set(nn)
            for n,b in back.items():
                assert b["closed"] and math.isclose(b["volume_mm3"],bs[n]["volume_mm3"],rel_tol=4e-5,abs_tol=.0002),(n,b)
                assert all(np.allclose(b["bbox"][s],bs[n]["bbox"][s],atol=.002) for s in ("min","max")),n
            rec["readback"][file]=len(back)
    with c.SolidCraftMCP(design=OUT/"c5-workbench.sc",timeout=350) as m:
        d=m.json("inspect_design",{"measure":False,"sketches":False});assert len(d["bodies"])==len(NAMES)+5 and not [f for f in d["timeline"] if f.get("error")]
        rec["readback"]["c5-workbench.sc"]=len(d["bodies"])
    c.dump(OUT/"cad-validation.json",rec);print(rec["readback"],flush=True)
if __name__=="__main__":run()
