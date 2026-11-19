"""Independent Manifold intersections on CAD exports and exact retained source faces.
Native contact surfaces may touch. Pose tests are named separately from continuous sweeps."""
import itertools, json, math
from build_c4 import *
import check_c3 as k
md,box3,rod=k.md,k.box,k.rod
D=np.diag([-1.,1.,-1.]); T=np.array([0.,0.,40.])
def desk(s):return k.xform(s,D,T)
def wp(p):return D@p+T
def bounds(s):return np.array(s.bounding_box()).reshape(2,3)
def continuous_box(s,delta):
    b=bounds(s);return box3(np.minimum(b[0],b[0]+delta),np.maximum(b[1],b[1]+delta))
def audit():
    parts=k.load_parts(OUT,FILES); src={n:desk(s) for n,s in k.refs().items()}; full={**parts,**src}
    # The front switch was separately registered in C3 and is a clearance proxy, not an accepted actuator.
    import trimesh
    sw=trimesh.load(OUT/"geometry/front-switch-source-relocated.obj",force="mesh",process=False)
    src["SWITCH_source"]=k.qa.solid(sw);full.update(src)
    tests={}; failures=[]
    def compare(label,pairs):
        hits={};num=0
        for n,a,m,b in pairs:
            num+=1;v=k.volume(a,b)
            if v>.002:hits[n+" / "+m]=v
        tests[label]={"pairs":num,"overlap_mm3":hits}
        if hits:failures.append(label);print(label,hits,flush=True)
    def cross(left,right):return ((n,a,m,b) for n,a in left.items() for m,b in right.items())
    def within(d):return ((n,a,m,b) for (n,a),(m,b) in itertools.combinations(d.items(),2))
    stats=json.loads((OUT/"cad-validation.json").read_text(encoding="utf8"))
    for n,s in parts.items():
        b=stats["bodies"][n]
        assert np.allclose(bounds(s),[b["bbox"]["min"],b["bbox"]["max"]],atol=.004),n
        assert abs(s.volume()/b["volume_mm3"]-1)<.009 and len([v for v in s.decompose() if v.volume()>1e-4])==1,n
    compare("all native pairs (allows surface contact)",within(parts))
    compare("all native vs retained and relocated source",cross(parts,src))
    reserve={"back 1.0":desk(k.placed(box3([-41,7.85,29.8],[-21,56.35,30.8]))),
             "front 8.5":desk(k.placed(box3([-41,7.85,32.4],[-21,56.35,40.9])))}
    compare("whole population vs enclosure except its own fork",cross(reserve,{**src,**{n:parts[n] for n in [FRAME,ROOF,FLOOR,METAL,*PINS]}}))
    # Normal approach on a detached panel. Each bounding prism contains the full swept solid.
    compare("continuous 36 mm normal PCB insertion with keeper off",cross(
        {n:continuous_box(parts[n],[-36,0,0]) for n in POWER},{IO:parts[IO]}))
    raw={"bridge":box3([-40.48,47.87,34.03],[-21.52,49.48,35.58])}
    for x in (-38.5,-23.5):raw["ear "+str(x)]=box3([x-1.98,47.87,32.4],[x+1.98,53.83,35.58])
    ks={n:continuous_box(desk(k.placed(s)),[-36,0,0]) for n,s in raw.items()}
    compare("continuous 36 mm keeper insertion with board seated, screws later",cross(ks,{n:parts[n] for n in [IO,*POWER]}))
    stop=k.volume(parts[c.USB].translate([0,-.35,0]),parts[KEEP])
    assert stop>.01,stop
    hardware={}
    for i,(x,y) in enumerate(c.board_data()[0]):
        is_keeper=y>40
        shank=8 if is_keeper else 5
        nut_z=35.58 if is_keeper else 32.4
        screw=rod(x,y,28.55,3.1,.85)+rod(x,y,29.4,1.6,shank)+rod(x,y,nut_z,3.7,1.3)
        hardware[f"board {i+1}"]=desk(k.placed(screw))
    for i,(x,y) in enumerate(c.TRAY_CENTRES):hardware[f"tray {i+1}"]=desk(rod(x,y,-2.15,3.8,2)+rod(x,y,-.15,5,.3)+rod(x,y,-.15,2,6))
    for i,(x,y) in enumerate(c.HOOD_FIX):hardware[f"floor {i+1}"]=desk(rod(x,y,19.8,3.8,2)+rod(x,y,21.8,2,8))
    compare("candidate board, tray and floor hardware",cross(hardware,full))
    compare("non-exported candidate hardware against one another",within(hardware))
    # Ports and the downward-facing Ethernet latch in the actual desk pose.
    legacy=json.loads((old.C2/"layout-validation.json").read_text(encoding="utf8"))
    plugs={}
    for n,d in legacy["assumed_plugs_mm"].items():
        x,z=d["xz_center"];y0,y1=d["y"]
        if "diameter" in d:s=md.Manifold.cylinder(y1-y0,d["diameter"]/2,d["diameter"]/2,64).rotate([-90,0,0]).translate([x,y0,z])
        else:
            w,h=d["width_height"];s=box3([x-w/2,y0,z-h/2],[x+w/2,y1,z+h/2])
            if n.startswith("PD "):s=k.placed(s)
        plugs[n]=desk(s)
    deskblock=box3([-150,-150,-10],[150,150,0]); complete={**full,**hardware,"desk":deskblock}
    compare("simultaneous plug envelopes including desk",cross(plugs,complete));compare("neighbouring plugs",within(plugs))
    access={"latch":desk(box3([58,58.5,24.5],[71,86,28])),
            "finger 13 x 20 x 12":desk(box3([58,60.6,24.6],[71,80.6,36.6]))}
    compare("downward Ethernet release including desk",cross(access,{**complete,**{n:s for n,s in plugs.items() if n!="RJ45"}}))
    # First local leg only of two 2.7 mm outside-diameter wires, 0.6 mm off the solder face.
    wires={}
    for no,kx,ky in fab()["footprints"]["J2"]["pads"]:
        x,y=c.xy(kx,ky)
        wires["wire exit "+no]=desk(k.placed(rod(x,y,33.,2.7,5.8)))
    compare("J2 straight exit gauges (not a routed harness)",cross(wires,complete))
    compare("local exit gauges vs each other",within(wires))
    topids=[ROOF,METAL,*PADS,*PINS,*SHIMS,*ALBOLTS]
    targets={n:v for n,v in {**full,**hardware}.items() if n not in [*topids,*SCREWS]}
    def poses(label,moving,targets,deltas):
        compare(label,((n+" @"+str(d),s.translate(d),m,t) for d in deltas for n,s in moving.items() for m,t in targets.items()))
    poses("complete top cassette vertical withdrawal (samples, closure screws out)",
          {n:parts[n] for n in topids},targets,[(0,0,z) for z in (.4,1.5,4,8,12,18)])
    stopfaces={}; source20=src["SOURCE_20"]
    for i,(x,name) in enumerate(zip(TEETH,PADS)):
        pad=parts[name]; metal_b=desk(box3([x-.6,-14,-3.1],[x+.6,26,14.5]))
        stopfaces[f"metal blade {i+1}"]=continuous_box(metal_b,[0,0,26])
        stopfaces[name]=continuous_box(pad,[0,0,26])
    compare("continuous conservative 26 mm swept teeth and pads vs retained solids",cross(stopfaces,src))
    # Root height from rays over both ends and centre; side margin via min_gap to SOURCE on each blade.
    thermal=[]
    for x,name in zip(TEETH,PADS):
        b=desk(box3([x-.6,-14,-3.1],[x+.6,26,14.5])); zs=[]
        for xx in (x-.599,x,x+.599):
            for y in (-13.999,6,25.999):
                hits=source20.ray_cast([-xx,y,55],[-xx,y,12]);zs.append(hits[0].position[2])
        assert max(abs(v-24.9) for v in zs)<.006 and k.gap(parts[name],source20)<.004
        thermal.append({"x_desk_mm":-x,"root_z_mm":[round(min(zs),4),round(max(zs),4)],
                        "smallest_hard_gap_any_direction_mm":k.gap(b,source20)})
    metal=parts[METAL]; localgap=k.gap(metal,source20)
    mm=metal.to_mesh64();points=np.asarray(mm.vert_properties)[:,:3][np.asarray(mm.tri_verts)]
    exposed=points[points[:,:,2].min(axis=1)>=46.499]
    area=float(np.linalg.norm(np.cross(exposed[:,1]-exposed[:,0],exposed[:,2]-exposed[:,0]),axis=1).sum()/2)
    assert FIN_H==28 and 69000<area<76000,area
    assert abs(metal.bounding_box()[5]-(46.5+FIN_H))<.01
    # Test capsule centrelines as end-to-end unobstructed air gauges through each actual skin.
    vents={}
    for zone,xx in VENTS.items():
        for x in xx:
            for j,(ya,yb) in enumerate(VENT_SPANS):
                for layer,lo,hi in (("low",30.9,35),("high",-5.4,.3)):
                    vents[f"{zone} {x} {j} {layer}"]=desk(box3([x-1.23,ya+1.5,lo],[x+1.23,yb-1.5,hi]))
    compare("through-slot gauges (not flow or CFD)",cross(vents,complete))
    air={"logic":[[49,-30.75,5],[49,-30.75,11],[49,-34.5,11],[48.25,-34.5,11],[48.25,-34.5,23],
                  [48.25,-29.25,23],[48.25,-29.25,38.75],[49,-29.25,38.75],[49,-29.25,45.5]],
         "power":[[-86.75,10,5],[-86.75,10,45.5]]}
    passages={f"{name} segment {i+1}":box3(np.minimum(a,b)-.7,np.maximum(a,b)+.7)
              for name,route in air.items() for i,(a,b) in enumerate(zip(route,route[1:]))}
    compare("continuous connected 1.4 mm square air gauges from under floor to above roof",cross(passages,complete))
    # Bottom removed, roof off: translate populated rear cassette with known assumed fasteners.
    moving={n:parts[n] for n in [IO,KEEP,*POWER]};moving.update({n:s for n,s in hardware.items() if n.startswith("board ")})
    fixed={FRAME:parts[FRAME],**src,**{n:s for n,s in hardware.items() if n.startswith("tray ")}}
    poses("populated rear cassette into open frame (samples)",moving,fixed,
          [(0,y,-3.6) for y in (66,48,34,22,14,8,4,2,1,0)]+[(0,0,-z) for z in (2.4,1.2,.4)])
    under={n:parts[n] for n in [FLOOR,*RUBBER]};poses("floor in free space with unit inverted; no desk (samples)",
          under,{n:s for n,s in full.items() if n not in under},[(0,0,-z) for z in (1,4,12,34)])
    poses("source tray into open frame, free space (samples)",{n:s for n,s in src.items() if n!="SWITCH_source"},
          {FRAME:parts[FRAME]},[(0,0,-z) for z in (36,22,12,6,2,.5)])
    tools={str(i):desk(rod(x,y,-12,4.2,33.79)) for i,(x,y) in enumerate(c.HOOD_FIX)}
    compare("floor driver, thermal cassette removed",cross(tools,{n:s for n,s in full.items() if n not in [*topids,*SCREWS]}))
    a=np.concatenate([bounds(p) for n,p in parts.items() if n not in POWER]);dims=np.ptp(a,axis=0).round(3).tolist()
    vents_area=6*((25-2.8)*2.8+math.pi*1.4**2)
    gaps={"power population scenario to chassis":k.gap(reserve["front 8.5"],parts[FRAME]),"power population scenario to floor":k.gap(reserve["front 8.5"],parts[FLOOR]),
          "board to antenna 14":k.gap(parts[c.BOARD],src["SOURCE_14"]),"RJ to PD boots":k.gap(plugs["RJ45"],plugs["PD boot"]),
          "finger gauge to desk":k.gap(access["finger 13 x 20 x 12"],deskblock),"metal bridge to OEM (all directions)":localgap,
          "power back reserve to Mac":k.gap(reserve["back 1.0"],source20),
          **{f"metal to antenna {i}":k.gap(metal,src[f"SOURCE_{i}"]) for i in (11,13,14)}}
    record={"date":"2026-11-18","scope":"digital C4, no physical measurements; positive overlap threshold 0.002 mm3, not a fit tolerance",
            "inputs":{**{p.name:c.sha(p) for p in (OUT/"geometry").glob("*.glb") if p.stem in FILES},
                      "KiCad":fab()["source_sha256"],**legacy["source_hashes"]},"pairs":sum(t["pairs"] for t in tests.values()),
            "tests":tests,"failed_groups":failures,"dimensions_with_feet_button_fins_mm":dims,
            "installed_bbox_l":round(math.prod(dims)/1e6,4),"gaps_mm":gaps,"J1_minus_0.35mm_thrust_challenge_mm3":stop,
            "root_contact":thermal,"nominal_interface_area_mm2":10*1.2*40,"external_fin_clear_spacing_mm":6.4-1.7,
            "thermal_screen":{"external_area_m2":round(area/1e6,6),"area_method":"CAD triangles completely at or above the top face of the base, Z=46.5 mm; excludes base edges/hidden underside and ignores fin efficiency",
                 "example_assumptions":{"heat_through_bridge_W":20,"ambient_C":25,"example_surface_C_not_acceptance_limit":50},
                 "required_effective_h_W_m2K_at_example":round(20/(area/1e6*25),2),
                 "ideal_TIM_K_W_at_k3":round(.0006/(3*.00048),3),"ideal_blades_K_W_at_k167":round(.0176/(167*.00048),3),
                 "scope":"Sizing screen only; no prediction of component or touch temperature. Missing real power split, contact resistance, compression, radiation view factors, fin efficiency, airflow and environment."},
            "free_slot_area_each_bank_each_skin_mm2":round(vents_area,2),"limits":"No cable bend/whole harness, board solder protrusion map, OEM fasteners, torque, contact pressure, flex, FDM distortion, RF, airflow or temperature proof."}
    record["natural_convection_gauges"]={"square_width_mm":1.4,"centreline_desk_xyz_mm":air,"meaning":"Geometric connectivity only, one path per zone, not cross-section of the whole flow or heat transfer."}
    c.dump(OUT/"fit-validation.json",record);print(record["pairs"],dims,gaps,"failed:",failures,flush=True)
    if failures:raise SystemExit(1)
if __name__=="__main__":audit()
