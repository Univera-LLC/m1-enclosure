"""Collision, approach and service gauges on exported C5R solids. All dimensions are scenarios."""
import itertools, json, math, zipfile
import trimesh
from build_rear import *
import check_c5 as cq
k,q,md,desk,rect,rod=cq.k,cq.q,cq.md,cq.desk,cq.rect,cq.rod
def run():
    parts=k.load_parts(OUT,FILES);src={n:desk(s) for n,s in k.refs().items()}; allp={**parts,**src}
    prev=json.loads((C5/"fit-validation.json").read_text()); cad=json.loads((OUT/"cad-validation.json").read_text())
    old=json.loads((v.old.C2/"layout-validation.json").read_text()); gauges=old["assumed_plugs_mm"]
    result={};failed=[]; audit={}
    def cross(a,b):return ((n,s,l,t) for n,s in a.items() for l,t in b.items())
    def within(a):return ((n,s,l,t) for (n,s),(l,t) in itertools.combinations(a.items(),2))
    def check(title,pairs):
        num=0;hit={}
        for n,s,l,t in pairs:
            num+=1;vol=k.volume(s,t)
            if vol>.002:hit[n+" / "+l]=vol
        result[title]={"pairs":num,"overlap_mm3":hit}
        if hit:print(title,hit,flush=True);failed.append(title)
    def poses(title,objs,obstacles,translations):
        check(title,((n+str(d),s.translate(d),l,t) for d in translations for n,s in objs.items() for l,t in obstacles.items()))
    for n,s in parts.items():
        p=cad["bodies"][n]
        assert np.allclose(q.bounds(s),[p["bbox"]["min"],p["bbox"]["max"]],atol=.020 if n in b.WIRE else .006),n
        assert abs(s.volume()/p["volume_mm3"]-1)<.012 and len([p for p in s.decompose() if p.volume()>.0002])==1,n
    check("native body pairs",within(parts));check("native vs retained source",cross(parts,src))
    hw={}
    for i,(x,y) in enumerate(c.board_data()[0]):
        high=y>40
        hw["PD "+str(i)]=desk(k.placed(rod(x,y,28.55,3.1,.85)+rod(x,y,29.4,1.6,8 if high else 5)+rod(x,y,35.58 if high else 32.4,3.7,1.3)))
    for i,(x,y) in enumerate(c.TRAY_CENTRES):hw["tray "+str(i)]=desk(rod(x,y,-2.15,3.8,2)+rod(x,y,-.15,5,.3)+rod(x,y,-.15,2,6))
    for i,(x,y) in enumerate(HOOD_FIX[:2]):hw["floor "+str(i)]=desk(rod(x,y,19.8,3.8,2)+rod(x,y,21.8,2,8))
    check("installed screw gauges",cross(hw,allp));check("screw gauges each other",within(hw))
    assembled={**allp,**hw,"table":rect([-150,-150,-10],[150,150,0])}
    def without(g,*names):return {n:s for n,s in g.items() if n not in names}
    # Keep the former full-size boots exactly, including their start planes. They
    # describe a real limitation of the installed inlay; record it as such.
    plugs={}
    for n,d in gauges.items():
        x,z=d["xz_center"];lo,hi=d["y"]
        if "diameter" in d:s=rod(x,0,0,d["diameter"],hi-lo).rotate([-90,0,0]).translate([0,lo,z])
        else:
            w,h=d["width_height"];s=rect([x-w/2,lo,z-h/2],[x+w/2,hi,z+h/2])
            if n.startswith("PD "):s=k.placed(s)
        plugs[n]=desk(s)
    check("original C5 full-shoulder gauges with inlay removed",cross(plugs,without(assembled,SKIN,*RIVETS)))
    check("original gauges against adjacent cables",within(plugs))
    old_hits={n:k.volume(s,parts[SKIN]) for n,s in plugs.items() if k.volume(s,parts[SKIN])>.002}
    proxy={"USB-A 1":(12.,4.5),"USB-A 2":(12.,4.5),"HDMI":(13.8,4.4),"TB1":(8.32,2.62),"TB2":(8.32,2.62),"RJ45":(11.8,7.5)}
    faces={"USB-A 1":56.45,"USB-A 2":56.45,"HDMI":56.45,"TB1":56.35,"TB2":56.35,"Audio":56.45,"RJ45":56.45,"PD boot":57.089}
    panel={n:FIELD if n=="Audio" else WELL for n in faces}
    # A boot can touch the rolled upper shoulder before it reaches the central face.
    # Evaluate the complete projected shoulder, particularly the tall RJ45 and audio.
    highest={};start={}
    for n,d in gauges.items():
        if n.startswith("PD "):continue
        x,z=d["xz_center"]
        if "diameter" in d:prism=rod(x,0,0,d["diameter"],8).rotate([-90,0,0]).translate([0,55,z])
        else:
            w,h=d["width_height"];prism=rect([x-w/2,55,z-h/2],[x+w/2,63,z+h/2])
        contact=parts[SKIN]^desk(prism);assert contact.volume()>.01,n
        highest[n]=float(q.bounds(contact)[1,1]);start[n]=highest[n]+.30
    start["PD boot"]=gauges["PD boot"]["y"][0]
    seated={"PD boot":plugs["PD boot"],"PD neck":plugs["PD neck"]}
    for n in [k for k in faces if k!="PD boot"]:
        x,z=gauges[n]["xz_center"];y0=faces[n]+.025;y1=start[n]
        if n=="Audio":
            s=rod(x,0,0,3.50,y1-y0).rotate([-90,0,0]).translate([0,y0,z])
        else:
            w,h=proxy[n];s=rect([x-w/2,y0,z-h/2],[x+w/2,y1,z+h/2])
        seated[n+" neck"]=desk(s)
        seated[n+" shoulder"]=plugs[n].translate([0,y1-gauges[n]["y"][0],0])
    check("installed inlay: simultaneous necks and shoulders",cross(seated,assembled));check("installed cables vs one another",within(seated))
    latch={"tab below RJ":desk(rect([58,58.5,24.5],[71,86,28.])),
           "finger below tab":desk(rect([58,60.65,24.6],[71,80.65,36.6]))}
    check("original underneath latch access and finger to desk",cross(latch,{**assembled,**{n:s for n,s in seated.items() if not n.startswith("RJ45")}}))
    check("36 mm continuous PSU insertion on detached fork",cross({n:q.continuous_box(parts[n],[-36,0,0]) for n in b.POWER},{n:parts[n] for n in (IO,SKIN,*RIVETS)}))
    thrust=k.volume(parts[c.USB].translate([0,-.35,0]),parts[b.KEEP]);assert thrust>.01
    reservations={"population":desk(k.placed(rect([-41,7.85,32.4],[-21,56.35,40.9]))),
                  "solder":desk(k.placed(rect([-41,7.85,29.8],[-21,56.35,30.8])))}
    check("board reserves vs chassis, wire and retained parts",cross(reservations,{**src,**{n:parts[n] for n in (FRAME,FLOOR,ROOF,*b.WIRE)}}))
    check("front two floor screws, driver with lid removed",cross({str(i):desk(rod(x,y,-12.,4.2,33.79)) for i,(x,y) in enumerate(HOOD_FIX[:2])},without(allp,ROOF,*b.SCREWS)))
    check("rear floor fixings, underside access with unit inverted",cross({str(i):desk(rod(x,y,32.30,3.70,17.0)) for i,(x,y) in enumerate(SIDE)},without(allp,*FOOT_SCREWS)))
    pull={n:parts[n] for n in (IO,b.KEEP,*b.POWER,SKIN,*RIVETS)};pull.update({n:s for n,s in hw.items() if n.startswith("PD ")})
    poses("rear carrier with attached inlay; lid, floor and flexible pair released",pull,{FRAME:parts[FRAME],**src,**{n:s for n,s in hw.items() if n.startswith("tray ")}},
          [(0,y,-3.6) for y in (66,48,34,22,14,8,4,2,1,0)]+[(0,0,-z) for z in (2.4,1.2,.4)])
    poses("tray loading with rear module out",src,{FRAME:parts[FRAME]},[(0,0,-z) for z in (36,22,10,3,.5)])
    poses("inlay withdraws straight aft after removing inlay screws",{SKIN:parts[SKIN]},without(allp,SKIN,*RIVETS),[(0,y,0) for y in (.1,.4,1,2,3,5,15)])
    poses("lid lifts", {ROOF:parts[ROOF]},without(allp,ROOF,*b.SCREWS),[(0,0,z) for z in (.4,2,6,26)])
    poses("lower shell drops after underside screws removed", {n:parts[n] for n in (FLOOR,*b.FEET)},without(allp,FLOOR,*b.FEET,*FOOT_SCREWS),[(0,0,-z) for z in (.6,3,12,35)])
    driver={str(i):desk(md.Manifold.cylinder(23,1.65,1.65,36).rotate([-90,0,0]).translate([x,28.72,z])) for i,(x,z) in enumerate(FIX)}
    check("inlay screw access from inside removed module",cross(driver,pull))
    air={f"{n} / {i}":rect(np.minimum(a,d)-.7,np.maximum(a,d)+.7) for n,path in prev["connected_air_gauges_desk_mm"].items() for i,(a,d) in enumerate(zip(path,path[1:]))}
    check("same 21 connected convection gauges",cross(air,assembled))
    # Sample the exterior near each working zone independently of the builder dimensions.
    sample={}
    for n,(x,z) in {"data":(-15.0,16.0),"audio header":(-37.6,7.8),"network":(64.65,26.2),"power":(79.93,24.0)}.items():
        yy=parts[SKIN].ray_cast([-x,64,40-z],[-x,54,40-z])[0].position[1];sample[n]=round(yy,3)
    assert all(abs(sample[n]-y)<.01 for n,y in [("data",WELL),("audio header",FIELD),("network",WELL),("power",WELL)]),sample
    webs={}
    for n,x1,x2 in [("USB-A pair",-49.9,-32.7),("HDMI to first TB",1.525,19.05),("TB pair",19.05,33.7)]:
        hits=parts[SKIN].ray_cast([-x1,57.72,22],[-x2,57.72,22]);assert len(hits)==2,n
        webs[n]=round(abs(hits[0].position[0]-hits[1].position[0]),3)
    validation={"date":"2026-11-18","scope":"CAD scenarios, mm; no measurements of physical product","tests":result,"failed":failed,
        "pairs":sum(t["pairs"] for t in result.values()),"overlap_threshold_mm3":.002,"native":len(parts),"source":len(src),
        "assembly_xyz_mm":np.ptp(np.concatenate([q.bounds(s) for s in parts.values()]),axis=0).round(3).tolist(),
        "baseline_unchanged_full_shoulders_intersect_installed_inlay_mm3":old_hits,"exterior_y_from_export_mm":sample,
        "nominal_face_to_socket_lip_mm":{n:round(panel[n]-y,3) for n,y in faces.items()},
        "gauged_shoulder_setback_from_lip_mm":{n:round(start[n]-y,3) for n,y in faces.items()},
        "material_between_cutouts_at_row_center_mm":webs,
        "power_population_reserve_to_fixed_chassis_mm":k.gap(reservations["population"],parts[FRAME]),
        "neck_proxies_mm":proxy,"beam_above_latch_mm":round(58.50-WELL,3),"J1_stop_challenge_mm3":thrust,
        "all_C5_plug_data_sha256":c.sha(v.old.C2/"layout-validation.json"),
        "SOURCE_TB2":"Lip Y56.35, blind pocket floor Y54.85 per C5, same source. No claim about mating depth.",
        "source_hashes":old["source_hashes"],
        "input_geometry_sha256":{name+".glb":c.sha(OUT/"geometry"/(name+".glb")) for name in FILES}}
    c.dump(OUT/"fit-validation.json",validation);print(validation["pairs"],validation["assembly_xyz_mm"],sample,old_hits,failed,flush=True)
    if failed:raise SystemExit(1)
    # Standalone slicer-review parts. Lower-Z is the chosen surface against the print bed.
    folder=OUT/"slicer-review";folder.mkdir(exist_ok=True);info={}
    for n,angle in [(ROOF,[180,0,0]),(FRAME,[180,0,0]),(FLOOR,[0,0,0]),(IO,[-90,0,0]),(b.KEEP,[0,-90,0]),(SKIN,[0,0,0])]:
        p=parts[n].rotate(angle);lo,hi=q.bounds(p);p=p.translate([7-lo[0],7-lo[1],-lo[2]])
        me=p.to_mesh64();mesh=trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts,process=False)
        f=folder/(n+".stl");mesh.export(f);r=trimesh.load_mesh(f,process=True)
        assert r.is_watertight and np.allclose(r.extents,hi-lo,atol=.0001) and min(r.bounds[:,2])<.001 and max((hi-lo)[:2])+14<220
        info[n]={"size_mm":(hi-lo).round(3).tolist(),"bed_rotation_deg":angle,"sha256":c.sha(f)}
    c.dump(folder/"checks.json",{"parts":info,"warning":"Review only. Inlay stands on its straight long lower edge. Try a 6–8 mm brim, review short port bridges and support only at inner bosses if required; check warping and M2 pilots in P5."})
    with zipfile.ZipFile(OUT/"c5r-slicer-review.zip","w",zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.iterdir()):z.write(f,f.name)
if __name__=="__main__":run()
