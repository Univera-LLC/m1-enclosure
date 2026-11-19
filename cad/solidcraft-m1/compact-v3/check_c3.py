"""Reproduce C2 vs C3 placement evidence from the actual exported solids and SOURCE triangles."""
import itertools
import numpy as np
import trimesh
from build_c3 import *
import check_layout as qa

md,box,rod=qa.md,qa.as_box,qa.rod
def load_parts(folder,groups):
    parts={}
    for g,names in groups.items():
        sc=trimesh.load(folder/"geometry"/(g+".glb"),force="scene",process=False)
        assert set(names)==set(sc.graph.nodes_geometry)
        for n in names:
            matrix,geom=sc.graph[n]; mesh=sc.geometry[geom].copy()
            mesh.apply_transform(qa.TO_CAD@matrix);parts[n]=qa.solid(mesh)
    return parts
def refs():
    parts={}
    for n,tri in qa.sources().items():
        v,idx=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True)
        parts["SOURCE_"+str(n)]=qa.solid(trimesh.Trimesh(v,idx.reshape(-1,3),process=False))
    return parts
def xform(s,rm,tr):return s.transform(np.column_stack([rm,tr]))
def placed(s):return xform(s,rot,shift)
def volume(a,b):return round(max(0.,(a^b).volume()),5)
def gap(a,b,limit=50):return round(a.min_gap(b,limit),4)

def audit():
    native=json.loads((OUT/"cad-validation.json").read_text())
    b=load_parts(OUT,FILES);src=refs(); fixed={**b,**src}
    for n,solid in b.items():
        d=native["bodies"][n]
        assert np.allclose(np.reshape(solid.bounding_box(),(2,3)),[d["bbox"]["min"],d["bbox"]["max"]],atol=.004),n
        assert abs(solid.volume()/d["volume_mm3"]-1)<.003 and len([s for s in solid.decompose() if s.volume()>1e-4])==1,n
    old=load_parts(C2,c.FILES)
    # Independent equivalence with the registered C2 KiCad model, including handedness / socket face.
    for n in POWER:
        q=placed(old[n])
        assert np.allclose(q.bounding_box(),b[n].bounding_box(),atol=.004),n
        assert abs(q.volume()-b[n].volume())<.007*max(1.,q.volume()),n
    tests={};fails=[]
    def check(label,pairs):
        bad={};count=0
        for n,a,m,s in pairs:
            count+=1;v=volume(a,s)
            if v>.002:bad[n+" / "+m]=v
        tests[label]={"pairs":count,"overlap_mm3":bad}
        if bad:fails.append([label,bad])
    def cross(l,r):return ((n,a,m,s) for n,a in l.items() for m,s in r.items())
    def inside(g):return ((n,a,m,s) for (n,a),(m,s) in itertools.combinations(g.items(),2))
    check("native bodies",inside(b));check("native vs retained triangles",cross(b,src))
    below=box([-41,7.85,29.8],[-21,56.35,30.8]); above=box([-41,7.85,32.4],[-21,56.35,40.9])
    res={"solder 1.0":placed(below),"population 8.5":placed(above)}
    check("whole-board scenario except own mount and fasteners",cross(res,{**src,**{n:b[n] for n in (CAP,FRAME,BASE,NAMES[c.GRILLE],c.BLOWER)}}))
    prior=json.loads((C2/"layout-validation.json").read_text())
    plugs={}
    for n,d in prior["assumed_plugs_mm"].items():
        x,z=d["xz_center"];y0,y1=d["y"]
        if "diameter" in d:
            plugs[n]=md.Manifold.cylinder(y1-y0,d["diameter"]/2,d["diameter"]/2,64).rotate([-90,0,0]).translate([x,y0,z])
        else:
            w,h=d["width_height"];q=box([x-w/2,y0,z-h/2],[x+w/2,y1,z+h/2])
            plugs[n]=placed(q) if n.startswith("PD ") else q
    check("simultaneous plug envelopes vs C3 and Mac",cross(plugs,fixed));check("plug vs plug",inside(plugs))
    corridor={"latch":box([58,58.5,24.5],[71,86,28]),"finger outside":box([58,60.6,24.6],[71,80.6,36.6])}
    check("RJ release",cross(corridor,{**fixed,**{n:v for n,v in plugs.items() if n!="RJ45"}}))
    tool={str(i+1):rod(x,y,-12,4.2,33.79) for i,(x,y) in enumerate(c.HOOD_FIX)}
    check("lid driver, bottom off",cross(tool,{n:v for n,v in fixed.items() if n not in (BASE,NAMES[c.GRILLE])}))
    hw={}
    for i,(x,y) in enumerate(c.BASE_FIX):
        hw["bottom "+str(i)]=rod(x,y,-8.1,5.5,3)+rod(x,y,-5.1,7,.5)+rod(x,y,-5.1,3,10)
    for i,(x,y) in enumerate(c.TRAY_CENTRES):
        hw["tray "+str(i)]=rod(x,y,-2.15,3.8,2)+rod(x,y,-.15,5,.3)+rod(x,y,-.15,2,6)
    for i,(x,y) in enumerate(c.SHEET_CENTRES):
        hw["sheet "+str(i)]=rod(x,y,-6,3,6)+rod(x,y,0,5.7,1.65)
    for i,(x,y) in enumerate(c.HOOD_FIX):
        hw["lid "+str(i)]=rod(x,y,19.8,3.8,2)+rod(x,y,21.8,2,8)
    for i,(x,y) in enumerate(c.board_data()[0]):
        hw["PD "+str(i)]=placed(rod(x,y,28.55,3.1,.85)+rod(x,y,29.4,1.6,5)+rod(x,y,32.4,3.7,1.3))
    check("candidate hardware vs CAD",cross(hw,fixed)); check("hardware vs hardware",inside(hw))
    def poses(label,moving,targets,deltas):
        check(label,((n+"@"+str(v),a.translate(v),m,s) for v in deltas for n,a in moving.items() for m,s in targets.items()))
    module={n:b[n] for n in [REAR,*POWER]}
    module.update({n:v for n,v in hw.items() if n.startswith("PD ")})
    case_installed={**src,FRAME:b[FRAME],**{n:v for n,v in hw.items() if n.startswith("tray ")}}
    poses("rear module sampled, lid and service bottom off",module,case_installed,
          [(0,y,3.6) for y in (64,48,34,22,14,8,4,2,1,0)]+[(0,0,z) for z in (2.4,1.2,.4)])
    poses("lid lift",{CAP:b[CAP]}, {n:v for n,v in fixed.items() if n!=CAP},[(0,0,z) for z in (1,4,10,20,34)])
    base={n:b[n] for n in (BASE,NAMES[c.GRILLE])}
    poses("service bottom drop",base,{n:v for n,v in fixed.items() if n not in base},[(0,0,-z) for z in (1,3,8,16)])
    poses("load source tray through open chassis",src,{FRAME:b[FRAME]},[(0,0,z) for z in (36,24,16,8,4,2,1,.5)])
    exits={str(i):box([-15.48+10.2*i,33.6,1.22],[-7.12+10.2*i,64,8.58]) for i in range(6)}
    throat={str(i):box([-15.48+10.2*i,31.5,2.57],[-7.12+10.2*i,64,8.58]) for i in range(6)}
    check("low exhaust and throat gauges",cross({**{"exit "+n:s for n,s in exits.items()},**throat},fixed))
    stops={}
    for label,member,target,dy in (("fascia push",REAR,CAP,-.4),("fascia pull",REAR,CAP,.4),("J1 push",c.USB,REAR,-.35)):
        v=volume(b[member].translate([0,dy,0]),b[target]);assert v>.01,(label,v)
        stops[label]=v
    # Alternatives: each is a declared test pose, not a proof about every possible PCB or enclosure.
    flip=np.diag([-1,1,-1]); flat=np.eye(3); yaw=np.array([[0,1,0],[-1,0,0],[0,0,1]])
    options={
       "flat under RJ, parts up":(flat,[64.65-c.PD_X,0,2-c.BOARD_Z]),
       "flat under RJ, parts down":(flip,[64.65+c.PD_X,0,1+c.BOARD_Z]),
       "upright inside unchanged width, on inner side of RJ":(rot,[53-c.BOARD_Z,0,10.8+c.PD_X]),
       "quarter turn in plan along rear, J1 points right":(yaw,[76.5-c.EDGE_Y,44+c.PD_X,2-c.BOARD_Z]),
       "C3 pose in unchanged C2 enclosure":(rot,shift)}
    options_data={}
    obstacles={**src,"C2 chassis":old[c.FRAME],"C2 service bottom":old[c.BASE],"C2 rear/fork/collector":old[c.REAR],
               "C2 sheet":old[c.GRILLE],"C2 lid":old[c.CAP],"right tray screw":hw["tray 2"]}
    for label,(mat,delta) in options.items():
        p={n:xform(old[n],mat,delta) for n in POWER}
        collisions={n:{k:v for k,s in obstacles.items() if (v:=volume(a,s))>.002} for n,a in p.items()}
        options_data[label]={"laminate_bbox_mm":list(p[c.BOARD].bounding_box()),"positive_overlaps_mm3":collisions}
    alt=options_data
    assert alt["flat under RJ, parts up"]["positive_overlaps_mm3"][c.BOARD]["SOURCE_25"]>0
    assert alt["flat under RJ, parts down"]["positive_overlaps_mm3"][c.BOARD]["right tray screw"]>0
    assert alt["upright inside unchanged width, on inner side of RJ"]["positive_overlaps_mm3"][c.USB]["SOURCE_20"]>0
    assert alt["quarter turn in plan along rear, J1 points right"]["positive_overlaps_mm3"][c.BOARD]["C2 rear/fork/collector"]>0
    # Z at the centre of the Ethernet housing. This local value is not clearance over the entire board.
    hits=src["SOURCE_20"].ray_cast([64.65,42,-5],[64.65,42,35])
    z_eth=round(hits[0].position[2],3);assert abs(z_eth-9.7)<.01
    outer=lambda dic: np.ptp(np.concatenate([np.array(v.bounding_box()).reshape(2,3) for v in dic.values()]),axis=0).round(3).tolist()
    full=outer({n:b[n] for n in HARD});shell=outer({CAP:b[CAP],FRAME:b[FRAME]});oldfull=prior["installed_envelopes_mm"]["including_button_feet"]
    assert shell==[168,118,34] and full==[168,119.6,44.6],(shell,full)
    dims={"C2 shell":[155,118,44],"C3 shell":shell,"C2 including feet and button":oldfull,"C3 including feet and button":full,
          "C2_bbox_L":round(np.prod(oldfull)/1e6,4),"C3_bbox_L":round(np.prod(full)/1e6,4),
          "footprint_change_pct":round(100*(full[0]*full[1]/(oldfull[0]*oldfull[1])-1),2),
          "installed_bbox_reduction_pct":round(100*(1-np.prod(full)/np.prod(oldfull)),2)}
    gaps={"RJ boot to PD boot":gap(plugs["RJ45"],plugs["PD boot"]),
          "laminate to right antenna 14":gap(b[c.BOARD],src["SOURCE_14"]),
          "C2 capacitor proxy to antenna 14":gap(b[c.BULK],src["SOURCE_14"]),
          "laminate to Mac":gap(b[c.BOARD],src["SOURCE_20"]),
          "backside solder reserve to Mac":gap(res["solder 1.0"],src["SOURCE_20"]),
          "8.5 population reserve to lid":gap(res["population 8.5"],b[CAP]),
          "8.5 population reserve to chassis":gap(res["population 8.5"],b[FRAME]),
          "flat ceiling above highest retained part C2":round(41.6-max(s.bounding_box()[5] for s in src.values()),3),
          "flat ceiling above highest retained part C3":round(H-2.4-max(s.bounding_box()[5] for s in src.values()),3)}
    result={"version":"C3 / 2026-11-18","method":"Manifold3D on native exported GLB and registered retained SOURCE triangles; positive overlap >0.002 mm3. Contact allowed. Discrete positions, assumed hardware/plug sizes. Gaps from tessellations.",
            "inputs":{"source_pcb":native["source_pcb_sha256"],"source_triangles":prior["source_hashes"]},"tests":tests,"failures":fails,
            "pairs":sum(v["pairs"] for v in tests.values()),"positive_stop_challenges_mm3":stops,
            "digital_dimensions_mm":dims,"clearances_mm":gaps,"J1_axis_xz_mm":[round(BX+1.6+1.625,3),CZ],
            "world_pcb_bounds_mm":b[c.BOARD].bounding_box(),"PD_boot_C3_mm":plugs["PD boot"].bounding_box(),"RJ_boot_mm":plugs["RJ45"].bounding_box(),
            "Z_ethernet_underside_at_x64.65_y42_mm":z_eth,"right_tray_screw_xyz_bottom":[*c.TRAY_CENTRES[-1],-2.15],
            "alternatives_at_specified_poses":options_data,"unchanged_vent_sections_mm2":prior["areas_mm2"],
            "limits":"4 package proxies; upper 8.5 and lower 1.0 mm reservations exclude own fork/stops and fasteners. No final J1/cable/harness or retained RF mount. No electrical, thermal, RF, physical, or print acceptance."}
    c.dump(OUT/"placement-check.json",result)
    print(json.dumps({"pairs":result["pairs"],"failures":fails,"gaps":gaps,"dimensions":dims},indent=2),flush=True)
    if fails:raise SystemExit(1)
if __name__=="__main__":audit()
