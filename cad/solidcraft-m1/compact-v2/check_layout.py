"""Audit the exported geometry against the exact retained SnazzyLabs faces. Units: mm."""
import itertools, math
from pathlib import Path
import numpy as np
import trimesh
from build_compact import *
from audit_source_mounts import sources
import manifold3d as md

# Standard glTF metres, +Y up -> project mm, +Z up, rear +Y.
TO_CAD=np.array([[1000,0,0,0],[0,0,-1000,0],[0,1000,0,0],[0,0,0,1]])
def solid(mesh):
    v,inverse=np.unique(np.round(mesh.vertices,5),axis=0,return_inverse=True)
    body=md.Manifold(md.Mesh64(np.ascontiguousarray(v),np.ascontiguousarray(inverse[mesh.faces],dtype=np.uint64)))
    assert body.status()==md.Error.NoError and body.volume()>0, (mesh.metadata,body.status(),body.volume())
    return body
def as_box(lo,hi):return md.Manifold.cube(np.subtract(hi,lo)).translate(lo)
def rod(x,y,z,d,h):return md.Manifold.cylinder(h,d/2,d/2,48).translate([x,y,z])

def audit():
    bodies={}; refs={}; drawn={}
    native=json.loads((OUT/"cad-validation.json").read_text())
    for group,names in FILES.items():
        scene=trimesh.load(OUT/"geometry"/(group+".glb"),force="scene",process=False)
        assert set(scene.graph.nodes_geometry)==set(names)
        for n in names:
            matrix,geom=scene.graph[n]; mesh=scene.geometry[geom].copy()
            mesh.apply_transform(TO_CAD@matrix); b=solid(mesh); bodies[n]=b
            nb=native["bodies"][n]
            assert np.allclose(mesh.bounds,[nb["bbox"]["min"],nb["bbox"]["max"]],atol=.004),n
            assert abs(b.volume()/nb["volume_mm3"]-1)<.003,n
            assert len([s for s in b.decompose() if s.volume()>1.e-4])==1,n
    # Positive signed volumes; make a small correctly registered GLB for each retained SOURCE reference.
    for k,t in sources().items():
        v,ix=np.unique(t.reshape(-1,3),axis=0,return_inverse=True)
        mesh=trimesh.Trimesh(v,ix.reshape(-1,3),process=False)
        n="SOURCE_"+str(k); refs[n]=solid(mesh); mesh.apply_transform(np.linalg.inv(TO_CAD))
        (OUT/"geometry"/(n+".glb")).write_bytes(trimesh.Scene({n:mesh}).export(file_type="glb"))
    numeric={}; fails=[]
    def test(key,a,b):
        vol=max(0.,(a^b).volume())
        # Numerical tessellation threshold, never a fit tolerance.
        if vol>.002: fails.append([key,round(vol,4)])
        return round(vol,6)
    def compare(label,pairs):
        pairs=list(pairs); overlaps=[]
        for n,a,m,b in pairs:
            vol=test(label+":"+n+"/"+m,a,b)
            if vol>.002:overlaps.append([n,m,vol])
        numeric[label]={"pairs":len(pairs),"overlaps_mm3":overlaps}
    compare("exported solids",((n,a,m,b) for (n,a),(m,b) in itertools.combinations(bodies.items(),2)))
    compare("against retained SOURCE",((n,a,m,b) for n,a in bodies.items() for m,b in refs.items()))
    # The actual power board has unmodeled components, leads and wires. Check reserved Z explicitly.
    keepouts={"underside solder allowance 1.0":as_box([-41,7.85,BOARD_Z-1],[-21,56.35,BOARD_Z]),
              "upper population 8.5":as_box([-41,7.85,BOARD_Z+1.6],[-21,56.35,BOARD_Z+1.6+8.5])}
    compare("full PCB reservations vs Apple and lid",((n,a,m,b) for n,a in keepouts.items() for m,b in {**refs,CAP:bodies[CAP]}.items()))
    # Mechanical scenarios, not the dimensions of any purchased cable. Full rectangular swept envelopes except audio.
    plugs={}; dims={}
    def boot(n,x,z,w,h,y0=56.55,y1=84.5):
        plugs[n]=as_box([x-w/2,y0,z-h/2],[x+w/2,y1,z+h/2])
        dims[n]={"xz_center":[x,z],"width_height":[w,h],"y":[y0,y1]}
    boot("USB-A 1",-49.9,18,16.2,8.8); boot("USB-A 2",-32.7,18,16.2,8.8)
    boot("HDMI",1.525,17.9,21,9);boot("TB1",19.05,18,12,8.4);boot("TB2",33.7,18,12.4,8.4)
    boot("RJ45",64.65,17,16.8,15);boot("PD boot",-31,34.025,12.2,6.8,58.75,86.5)
    boot("PD neck",-31,34.025,8.35,2.55,57.10,58.75)
    plugs["Audio"]=md.Manifold.cylinder(28,3.9,3.9,64).rotate([-90,0,0]).translate([-41.3,56.55,7.8])
    dims["Audio"]={"xz_center":[-41.3,7.8],"diameter":7.8,"y":[56.55,84.55]}
    compare("plug sweeps vs assembly",((n,a,m,b) for n,a in plugs.items() for m,b in {**bodies,**refs}.items()))
    compare("adjacent plug bodies",((n,a,m,b) for (n,a),(m,b) in itertools.combinations(plugs.items(),2)))
    access={"RJ latch":as_box([58,58.5,24.5],[71,86,28]),
            "finger above latch outside rim":as_box([58,60.6,24.6],[71,80.6,36.6])}
    compare("RJ release corridor vs case and other plugs",((n,a,m,b) for n,a in access.items() for m,b in {**bodies,**refs,**plugs}.items() if m!="RJ45"))
    tools={str(i+1):rod(x,y,-12,4.2,36.79) for i,(x,y) in enumerate(HOOD_FIX)}
    compare("lid driver with bottom removed",((n,a,m,b) for n,a in tools.items() for m,b in {**bodies,**refs}.items() if m not in (BASE,GRILLE)))
    fixed={**bodies,**refs}
    screw={}
    for i,(x,y) in enumerate(BASE_FIX):
        screw[f"base M3x10 / {i+1}"]=rod(x,y,-8.1,5.5,3)+rod(x,y,-5.1,7,.5)+rod(x,y,-5.1,3,10)
    for i,(x,y) in enumerate(TRAY_CENTRES):
        screw[f"tray M2x6 / {i+1}"]=rod(x,y,-2.15,3.8,2)+rod(x,y,-.15,5,.3)+rod(x,y,-.15,2,6)
    for i,(x,y) in enumerate(SHEET_CENTRES):
        screw[f"sheet M3x6 / {i+1}"]=rod(x,y,-6,3,6)+rod(x,y,0,5.7,1.65)
        screw[f"sheet pilot clear core / {i+1}"]=rod(x,y,-7.18,3.85,5.66)
    for i,(x,y) in enumerate(HOOD_FIX):
        screw[f"lid M2x8 / {i+1}"]=rod(x,y,22.8,3.8,2)+rod(x,y,24.8,2,8)
    for i,(x,y) in enumerate(board_data()[0]):
        screw[f"PCB M1.6x5 and nut / {i+1}"]=rod(x,y,28.55,3.1,.85)+rod(x,y,29.4,1.6,5)+rod(x,y,32.4,3.7,1.3)
    compare("candidate hardware envelopes vs geometry",((n,a,m,b) for n,a in screw.items() for m,b in fixed.items()))
    def poses(label,moving,deltas,targets):
        compare(label,((f"{n}@{tuple(d)}",fixed[n].translate(d),m,fixed[m]) for d in deltas for n in moving for m in targets))
    poses("lid lift, sampled", [CAP],[(0,0,d) for d in (1,4,10,20,44)],[n for n in fixed if n!=CAP])
    poses("bottom drop, sampled",[BASE,GRILLE],[(0,0,-d) for d in (1,3,8,16)], [n for n in fixed if n not in (BASE,GRILLE)])
    poses("load retained assembly through open top, sampled",list(refs),[(0,0,z) for z in (36,26,18,12,8,5,3,1,.5)], [FRAME])
    collector=[REAR,BOARD,USB,COIL,BULK,BUCK]
    target=[FRAME,*refs]
    poses("rear module insertion, lid and bottom off / sampled",collector,
          [(0,y,3.6) for y in (64,48,34,22,14,8,4,2,1,0)]+[(0,0,z) for z in (2.4,1.2,.4)],target)
    # Recover the fin direction from recurring parallel vertical faces; restrict to the repeated interior ribs.
    t=sources()[20]; a=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
    sel=(np.abs(a[:,0])>580)&(np.abs(a[:,1])<1e-5)&(np.abs(a[:,2])<1e-5)&(t[:,:,2].min(1)<5)&(np.abs(t.mean(1)[:,0])<15)
    fin=np.round(t[sel].reshape(-1,3),3); fin_range=[fin.min(0).tolist(),fin.max(0).tolist()]
    assert np.allclose(np.asarray(fin_range)[:,1:], [[-20.15,3.35],[31.35,14.85]],atol=.02)
    # A rectangular duct gauge physically passes through each of the six panel holes.
    exits={str(i+1):as_box([-15.48+10.2*i,33.6,1.22],[-7.12+10.2*i,64,8.58]) for i in range(6)}
    throat={str(i+1):as_box([-15.48+10.2*i,31.5,2.57],[-7.12+10.2*i,64,8.58]) for i in range(6)}
    compare("low exhaust downstream of bypass fence",((n,a,m,b) for n,a in exits.items() for m,b in fixed.items()))
    compare("fin exit through throat and rear slots",((n,a,m,b) for n,a in throat.items() for m,b in fixed.items()))
    stops={}
    for label,member,other,dy in [("panel insertion seats",REAR,CAP,-.4),("panel pull-out returns",REAR,CAP,.4),("J1 insertion reaction",USB,REAR,-.35)]:
        volume=(fixed[member].translate([0,dy,0])^fixed[other]).volume()
        assert volume>0.01,(label,volume)
        stops[label]={"deliberate_motion_y_mm":dy,"positive_stop_overlap_mm3":round(volume,4),"interpretation":"nominal stop contact; not strength or load proof"}
    def envelope(items):
        lo=np.min([v["min"] for v in items],axis=0);hi=np.max([v["max"] for v in items],axis=0)
        return np.round(hi-lo,3).tolist()
    installed=envelope([native["bodies"][n]["bbox"] for n in (CAP,FRAME,REAR,BASE,GRILLE,BUTTON,GUIDE,CARRIER)])
    old=json.loads((CAD/"mechanical-v1/validation.json").read_text())
    old_installed=envelope([v["bbox"] for v in old["analytic"].values()])
    assert installed==[155,119.6,54.6] and old_installed==[155,128.6,58.6],(installed,old_installed)
    assert abs(native["bodies"][BULK]["bbox"]["max"][2]-40.1)<.001
    result={"version":"compact-v2 / DIGITAL ONLY","method":"Manifold3D volume intersection, welded GLB tessellation at 1e-5 mm and exact retained source triangles; positive overlap threshold 0.002 mm3. Touching allowed. Poses sampled, not automated continuous motion.",
        "tests":numeric,"positive_thrust_stop_challenges":stops,"source_components":[20,25,11,13,14],"CAD_glb_single_connected_solids":len(bodies),
        "assumed_plugs_mm":dims,"source_fin_faces_range_mm":fin_range,
        "source_hashes":{p.name:sha(p) for p in (CAD/"source-analysis").glob("*.npy") if p.name in ("faces.npy","vertices.npy","face-component-labels.npy")},
        "areas_mm2":{"inlet":round(3*((56-3.6)*3.6+math.pi*1.8**2),2),"low_exhaust":round(6*8.4*7.4,2),"collector_above_fence":round((43.9+15.6)*(8.6-2.55),2),"independent_upper_vent":round(4*10.8*3.2,2)},
        "installed_envelopes_mm":{"chassis_width_depth":envelope([native["bodies"][FRAME]["bbox"]])[:2],"including_button_feet":installed,
                                  "comparison_mechanical_v1_including_button_feet":old_installed,
                                  "bbox_volume_reduction_percent":round(float(100*(1-np.prod(installed)/np.prod(old_installed))),3)},
        "housing_heights_mm":{"inside_ceiling":41.6,"pcb_low":30.8,"pcb_top":32.4,"nominal_bulk_top":40.1,"nominal_bulk_to_ceiling":1.5,
                              "full_8.5_mm_allowance_to_ceiling":.7,"PD_fab_face_to_fascia_exterior":round(58.5-(board_data()[1]["J1"][1]+3.675),4)},
        "physical_tests":"NOT TESTED / button NOT ACCEPTED; no selected fan; no final board Z, cable, retaining hardware, RF or material proof",
        "failures":fails}
    dump(OUT/"layout-validation.json",result)
    for x in fails[:44]:print(x)
    print("layout:",sum(v["pairs"] for v in numeric.values()),"checks;",len(fails),"overlaps",flush=True)
    if fails: raise SystemExit(1)
if __name__=="__main__":audit()
