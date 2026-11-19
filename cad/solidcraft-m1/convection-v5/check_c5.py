"""Independent checks on C5 exported triangles, five exact SOURCE bodies and explicit gauges."""
import itertools, json, math
from build_c5 import *
import check_c4 as q
k,md=q.k,q.md
box3,desk,wp,rod=q.box3,q.desk,q.wp,q.rod
def rect(lo,hi):return box3(np.asarray(lo),np.asarray(hi))
def aud():
    parts=k.load_parts(OUT,FILES);src={n:desk(s) for n,s in k.refs().items()};full={**parts,**src}
    stats=json.loads((OUT/"cad-validation.json").read_text()); checks={};failed=[]
    def compare(label,pairs):
        hits={};count=0
        for a,s,b,t in pairs:
            count+=1;v=k.volume(s,t)
            if v>.002:hits[a+" / "+b]=v
        checks[label]={"pairs":count,"overlap_mm3":hits}
        if hits:failed.append(label);print(label,hits,flush=True)
    def cross(l,r):return ((n,s,m,t) for n,s in l.items() for m,t in r.items())
    def within(g):return ((n,s,m,t) for (n,s),(m,t) in itertools.combinations(g.items(),2))
    def poses(name,g,h,ds):
        compare(name,((n+str(d),s.translate(d),m,t) for d in ds for n,s in g.items() for m,t in h.items()))
    mesh_limits={}
    for n,s in parts.items():
        b=stats["bodies"][n]
        error=float(np.max(np.abs(q.bounds(s)-[b["bbox"]["min"],b["bbox"]["max"]])))
        # The native fitted spline's reported extrema differ slightly from its finest
        # tessellation. STEP-to-native still has its own 0.002 mm check in build_c5.
        if n in WIRE:mesh_limits[n]=round(error,5)
        assert error<(.020 if n in WIRE else .006),(n,error)
        assert abs(s.volume()/b["volume_mm3"]-1)<.012 and len([p for p in s.decompose() if p.volume()>.0002])==1,(n,s.volume(),b["volume_mm3"])
    compare("native bodies",within(parts));compare("all native vs retained SOURCE",cross(parts,src))
    hw={}
    for i,(x,y) in enumerate(c.board_data()[0]):
        high=y>40;fix=rod(x,y,28.55,3.1,.85)+rod(x,y,29.4,1.6,8 if high else 5)+rod(x,y,35.58 if high else 32.4,3.7,1.3)
        hw[f"PD {i}"]=desk(k.placed(fix))
    for i,(x,y) in enumerate(c.TRAY_CENTRES):hw[f"tray {i}"]=desk(rod(x,y,-2.15,3.8,2)+rod(x,y,-.15,5,.3)+rod(x,y,-.15,2,6))
    for i,(x,y) in enumerate(HOOD_FIX):hw[f"floor {i}"]=desk(rod(x,y,19.8,3.8,2)+rod(x,y,21.8,2,8))
    compare("candidate PCB, floor, tray fixings",cross(hw,full));compare("fixings against one another",within(hw))
    reserves={"solder 1.0":desk(k.placed(rect([-41,7.85,29.8],[-21,56.35,30.8]))),
              "population 8.5":desk(k.placed(rect([-41,7.85,32.4],[-21,56.35,40.9])))}
    compare("whole-board reserve excluding own carrier",cross(reserves,{**src,**{n:parts[n] for n in (FLOOR,FRAME,ROOF,*FILES["wiring"])}}))
    compare("continuous 36 mm side insertion with J1 keeper off",cross({n:q.continuous_box(parts[n],[-36,0,0]) for n in POWER},{IO:parts[IO]}))
    raw={"bridge":rect([-40.48,47.87,34.03],[-21.52,49.48,35.58])}
    for x in (-38.5,-23.5):raw[str(x)]=rect([x-1.98,47.87,32.4],[x+1.98,53.83,35.58])
    compare("continuous keeper insertion on detached rear assembly",cross(
        {n:q.continuous_box(desk(k.placed(s)),[-36,0,0]) for n,s in raw.items()},{n:parts[n] for n in (IO,*POWER)}))
    thrust=k.volume(parts[c.USB].translate([0,-.35,0]),parts[KEEP]);assert thrust>.01
    leg=json.loads((v.old.C2/"layout-validation.json").read_text())
    plugs={};faces={"USB-A 1":56.45,"USB-A 2":56.45,"HDMI":56.45,"TB1":56.35,"TB2":56.35,"RJ45":56.45,"Audio":56.45,"PD boot":57.089}
    for n,b in leg["assumed_plugs_mm"].items():
        x,z=b["xz_center"];y0,y1=b["y"]
        if "diameter" in b:s=rod(x,0,0,b["diameter"],y1-y0).rotate([-90,0,0]).translate([0,y0,z])
        else:
            w,h=b["width_height"];s=rect([x-w/2,y0,z-h/2],[x+w/2,y1,z+h/2]);s=k.placed(s) if n.startswith("PD ") else s
        plugs[n]=desk(s)
    table=rect([-150,-150,-10],[150,150,0]); complete={**full,**hw,"desk":table}
    compare("simultaneous boot and neck scenarios vs installed assembly",cross(plugs,complete));compare("adjacent overmoulds",within(plugs))
    # SOURCE sockets are solid envelopes. Check the short approach from their face to
    # the boot start. The solid SOURCE TB2 has a 1.50 mm blind pocket inside its lip.
    necks={}
    for n,(w,h) in {"USB-A 1":(12.0,4.5),"USB-A 2":(12.,4.5),"HDMI":(13.8,4.4),
                    "TB1":(8.32,2.62),"TB2":(8.32,2.62),"RJ45":(11.8,7.5)}.items():
        x,z=leg["assumed_plugs_mm"][n]["xz_center"]; end=leg["assumed_plugs_mm"][n]["y"][0]
        necks[n]=desk(rect([x-w/2,faces[n]+.04,z-h/2],[x+w/2,end,z+h/2]))
    necks["Audio"]=desk(rod(-41.3,0,0,3.45,.06).rotate([-90,0,0]).translate([0,56.49,7.8]))
    compare("external native plug necks right up to source face, not contacts",cross(necks,complete))
    def depth_at(x,z):
        return round(src["SOURCE_20"].ray_cast([-x,64,40-z],[-x,50,40-z])[0].position[1],3)
    tb_lip,tb_pocket=depth_at(29.52,18),depth_at(33.7,18)
    assert (tb_lip,tb_pocket)==(56.35,54.85)
    testshape=md.CrossSection.square([5.87,.02],center=True).offset(1.19,md.JoinType.Round,circular_segments=72)
    tb_probe=desk(testshape.extrude(56.55-(tb_pocket+.04)).rotate([90,0,0]).translate([33.7,56.55,18]))
    tb_internal=k.volume(tb_probe,src["SOURCE_20"]);assert tb_internal>.01 and k.volume(tb_probe,parts[IO])==0
    access={"latch travel reserve":desk(rect([58,58.5,24.5],[71,86,28])),
            "finger 13 x 20 x 12 from outside new face":desk(rect([58,FACE_Y+.15,24.6],[71,FACE_Y+20.15,36.6]))}
    compare("access below Ethernet latch",cross(access,{**complete,**{n:s for n,s in plugs.items() if n!="RJ45"}}))
    # Test connected gauge volumes, not unconnected probes just at the two skins.
    air={};square=1.40
    for i,x in enumerate(AX):
        air[f"M1-{i+1}-floor"]=[[-x,-67,3.0],[-x,-47.5,3.0],[-x,-47.5,10.3],[-x,-54.38,10.3],[-x,-54.38,28.2],
                                  [-x,18.,28.2],[-x,18.,48.0]]
        air[f"M1-{i+1}-nose"]=[[-x,-64,11.25],[-x,-54.38,11.25],[-x,-54.38,28.2],[-x,-13.,28.2],[-x,-13.,48.0]]
    air["power"]=[[-98,10.,3.],[-86.75,10.,3.],[-86.75,10.,48.]]
    routes={f"{n} edge {i+1}":rect(np.minimum(a,b)-square/2,np.maximum(a,b)+square/2) for n,path in air.items() for i,(a,b) in enumerate(zip(path,path[1:]))}
    compare("connected gauges through front plenum, OEM channels, roof and PD bay",cross(routes,complete))
    # Aperture area from intersections of actual mesh slices, excluding surrounding solid and adjacent vents.
    def sampled_area(body,z,xx,y0,y1,width):
        plane=parts[body].slice(z); total=0
        for x in xx:
            x=-x;w=width+.24;l=y1-y0+.24
            region=md.CrossSection.square([w,l],center=True).translate([x,(y0+y1)/2])
            total+=(region-plane).area()
        return total
    def capsule(ell,w):return (ell-w)*w+math.pi*(w/2)**2
    areas={}
    for zone,n,z,xx,spans,w in [("OEM floor",FLOOR,7.4,AX,[IN_SPAN],IN_W),("OEM roof",ROOF,45.,AX,ROOF_SPANS,VENT_W),
             ("PD floor",FLOOR,7.4,PD_X,PD_SPANS,PD_W),("PD roof",ROOF,45.,PD_X,PD_SPANS,PD_W)]:
        measured=sum(sampled_area(n,z,xx,lo,hi,w) for lo,hi in spans)
        theoretical=len(xx)*sum(capsule(hi-lo,w) for lo,hi in spans)
        assert abs(measured/theoretical-1)<.012,(zone,measured,theoretical)
        areas[zone]=round(measured,1)
    # Actual common material above a sampled OEM crest at the transverse roof web.
    fin_z=[];roof_z=[]
    for x in AX:
        xx=-(x+1.6);yy=4.6
        fin_z.append(src["SOURCE_20"].ray_cast([xx,yy,50],[xx,yy,20])[0].position[2])
        roof_z.append(parts[ROOF].ray_cast([xx,yy,37],[xx,yy,50])[0].position[2])
    assert np.allclose(fin_z,36.9,atol=.01) and np.allclose(roof_z,43.6,atol=.01)
    without=lambda *names:{n:s for n,s in full.items() if n not in names}
    poses("lid lift with screws out",{ROOF:parts[ROOF]},without(ROOF,*SCREWS),[(0,0,z) for z in (.5,2,6,26)])
    poses("floor and feet drop with inverted unit, desk omitted",{n:parts[n] for n in (FLOOR,*FEET)},without(FLOOR,*FEET),[(0,0,-z) for z in (.6,3,12,35)])
    poses("tray load before wires and removable panels",src,{FRAME:parts[FRAME]},[(0,0,-z) for z in (36,22,10,3,.5)])
    module={n:parts[n] for n in (IO,KEEP,*POWER)};module.update({n:s for n,s in hw.items() if n.startswith("PD ")})
    poses("rear module; floor and lid removed, service pair released and lifted clear",module,{FRAME:parts[FRAME],**src,**{n:s for n,s in hw.items() if n.startswith("tray ")}},
          [(0,y,-3.6) for y in (66,48,34,22,14,8,4,2,1,0)]+[(0,0,-z) for z in (2.4,1.2,.4)])
    tools={str(i):desk(rod(x,y,-12,4.2,33.79)) for i,(x,y) in enumerate(HOOD_FIX)}
    compare("floor screw driver with lid off",cross(tools,without(ROOF,*SCREWS)))
    for i,z in enumerate([BUTTON_Z-7.7,BUTTON_Z+7.7]):
        gauge=md.Manifold.cylinder(23,1.65,1.65,36).rotate([-90,0,0]).translate([BUTTON_X,PCB_Y+2.53,z])
        compare("front switch screw access "+str(i+1),cross({"driver":desk(gauge)},full))
    exits={p:desk(k.placed(rod(*c.xy(x,y),33.,2.7,5.8))) for p,x,y in v.fab()["footprints"]["J2"]["pads"]}
    compare("local J2 insulated wire exit only",cross(exits,complete));compare("local J2 exits against one another",within(exits))
    # Only the moving cap is allowed into the stationary rim: radial running clearance, not actual switch travel.
    finger=md.Manifold.cylinder(12,6.0,6.0,48).rotate([-90,0,0]).translate([BUTTON_X,PCB_Y-8.4-12,BUTTON_Z])
    compare("finger touches proud switch before case",cross({"touch gauge":desk(finger)},without(CAP)))
    module_names=(PCB,CAP,SW,*PINS)
    compare("continuous conservative 12 mm front module insertion, two screws fitted afterwards",cross(
        {n:md.Manifold.batch_hull([parts[n],parts[n].translate([0,12,0])]) for n in module_names},
        {FRAME:parts[FRAME],FLOOR:parts[FLOOR],**src}))
    caps={CAP:parts[CAP]}
    poses("0.25 mm illustrative cap motion, not a specified switch stroke",caps,without(CAP),[(0,.125,0),(0,.25,0)])
    compare("3 mm unplug envelope in front of stationary mate; flexible lead released",cross(
        {PLUG:q.continuous_box(parts[PLUG],[-3,0,0])},without(PLUG,*WIRE)))
    d=np.ptp(np.concatenate([q.bounds(s) for s in parts.values()]),axis=0).round(3).tolist()
    gaps={"PCB back reserve to Mac":k.gap(reserves["solder 1.0"],src["SOURCE_20"]),"RJ boot to PD boot":k.gap(plugs["RJ45"],plugs["PD boot"]),
          "latch fingertip to desk":k.gap(access["finger 13 x 20 x 12 from outside new face"],table),
          "roof above OEM crest at bridging strip":round(min(np.subtract(roof_z,fin_z)),3),
          "button wire to OEM antenna 14":min(k.gap(parts[n],src["SOURCE_14"]) for n in WIRE),
          "wire to assumed populated power envelope":min(k.gap(parts[n],reserves["population 8.5"]) for n in WIRE)}
    log={"date":"2026-11-18","scope":"CAD scenarios only; no physical, thermal, electrical or RF measurements","parts":len(parts),"sources":len(src),
         "pairs":sum(d["pairs"] for d in checks.values()),"overlap_threshold_mm3":.002,"tests":checks,"failed":failed,
         "desk_dimensions_mm":d,"gaps_mm":gaps,"area_open_mm2_from_exported_skin":areas,
         "nose_additional_area_nominal_mm2":round(sum((AX[i+1]-AX[i]+4.76)*4.35-(4-math.pi)*1.55**2 for i in range(0,10,2)),1),
         "door_to_socket_face_recess_mm":{n:round(FACE_Y-y,3) for n,y in faces.items()},
         "TB2_source_detail":{"outer_shield_lip_Y":tb_lip,"blind_pocket_floor_Y":tb_pocket,
             "distance_fascia_to_pocket_floor_mm":round(FACE_Y-tb_pocket,2),"assumed_rounded_probe_mm":[8.25,2.4],
             "inside_SOURCE_pocket_overlap_mm3":tb_internal,"inside_new_fascia_overlap_mm3":0,
             "meaning":"SOURCE has a blind pocket, not true socket mating geometry. Do not use its floor as the front plane or claim full electrical seating."},
         "minimum_nominal_port_web_mm":min(PORTS[1][0]-PORTS[0][1],PORTS[3][0]-PORTS[2][1]),"J1_thrust_challenge_mm3":thrust,
         "air_square_width_mm":square,"connected_air_gauges_desk_mm":air,
         "mesh_vs_native_wire_bbox_max_difference_mm":mesh_limits,
         "modelled_wire_lengths_to_service_connector_mm":{n:round(stats["bodies"][n]["volume_mm3"]/(math.pi*(.87/2)**2),1) for n in WIRE},
         "source_hashes":leg["source_hashes"],"pcb_sha256":v.fab()["source_sha256"],"export_sha256":{f.name:c.sha(f) for f in (OUT/"geometry").glob("*.glb")}}
    c.dump(OUT/"fit-validation.json",log);print(log["pairs"],d,gaps,areas,"failed",failed,flush=True)
    if failed:raise SystemExit(1)
if __name__=="__main__":aud()
