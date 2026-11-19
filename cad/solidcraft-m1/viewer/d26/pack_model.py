"""Read back D2.6 panel/assembly GLBs, with the board reference with photo-based D2.6 port geometry."""
import argparse
import base64
import gzip
import hashlib
import io
import json
import re
from pathlib import Path

import manifold3d as md
import numpy as np
import trimesh as tm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = HERE.parents[1] / "prototype-d26"
TO_GL = np.array([[.001,0,0,0], [0,0,.001,0], [0,-.001,0,0], [0,0,0,1]])
TO_MM = np.linalg.inv(TO_GL)
scene = tm.Scene()
report = {"units":"CAD desk mm", "native":{}, "source":{}, "comparison":{}}

def read_glb(path):
    src=tm.load_scene(path,file_type="glb",process=False)
    for name in src.graph.nodes_geometry:
        transform,key=src.graph[name]
        mesh=src.geometry[key].copy()
        mesh.apply_transform(TO_MM @ transform)
        yield name,mesh

def add(name,mesh,part,finish,layer="d2"):
    key="__".join((layer,part,finish,re.sub(r"[^a-zA-Z0-9_-]+","-",name)))
    assert key not in scene.geometry,key
    mesh.visual=tm.visual.ColorVisuals(mesh=mesh)
    mesh.apply_transform(TO_GL)
    scene.add_geometry(mesh,node_name=key,geom_name=key)

def solid(mesh):
    vertices,inverse=np.unique(np.round(mesh.vertices,5),axis=0,return_inverse=True)
    body=md.Manifold(md.Mesh64(np.ascontiguousarray(vertices),
                               np.ascontiguousarray(inverse[mesh.faces],dtype=np.uint64)))
    assert body.status()==md.Error.NoError and body.volume()>0
    return body

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding="utf-8"))
def load_native(cad):
    palettes={"base":("chassis","shell"),"lid":("lid","shell"),"panel":("panel","faceplate"),"blank":("blank","graphite"),
        "feet":("feet","rubber"),"socket":("socket","macmetal"),"socket_insert":("socket","macinsulator"),"saddle":("saddle","jade"),
        "lid_screws":("lidscrews","screw"),"pcb_screws":("pcbscrews","screw"),"blank_screws":("blank","screw"),"power_hardware":("fixings","screw")}
    for group,names in cad["groups"].items():
        for name,m in read_glb(OUT/"geometry"/(group+".glb")):
            assert name in names
            error=float(np.max(np.abs(m.bounds-np.array([cad["bodies"][name]["bbox"][k] for k in ("min","max")]))))
            assert error<.012,(name,error)
            layer="d2"
            if group in ("boards","population"):
                id="trigger" if "CMTPD" in name else "buck"
                if group=="population":layer,finish="gauge","gauge"
                else:finish="pdfr4" if id=="trigger" else "buckfr4"
            else:id,finish=palettes[group]
            report["native"][name]={"group":id,"max_bbox_delta_mm":round(error,6)}
            add(name,m,id,finish,layer)
    assert set(cad["bodies"])==set(report["native"]) and len(cad["groups"]["socket_insert"])>=1

def load_board_and_rf():
    import struct
    data=BOARD.read_bytes();tree=json.loads(data[20:20+struct.unpack_from("<I",data,12)[0]])
    board=dict(read_glb(BOARD));old=dict(read_glb(FROZEN/"board-study/mac-board-reference.glb"))
    assert {n.split("__")[1] for n in board}=={"logic","sink","ports","coax","loom","studmarks"}
    assert not tree.get("images") and not tree.get("textures") and all("__rf__" not in n for n in board)
    for n,m in board.items():
        layer,id,finish,source=n.split("__",3);add(source,m.copy(),id,finish,layer)
    for n,m in old.items():
        if any(id in n for id in ("__sink__","__coax__","__loom__","__studmarks__")):
            assert n in board and np.array_equal(m.faces,board[n].faces) and np.allclose(m.vertices,board[n].vertices,atol=.00001,rtol=0),n
    report["owner_topside"]=read(HERE/"board-basis.json")
    owner=report["owner_topside"]
    owner["prior_photo_study_mesh_counts_D2_3"]={k:owner.pop(k) for k in ("source_face_groups","unchanged_source_triangles","original_source_triangles")}
    owner["prior_photo_study_mesh_counts_D2_3"]["scope"]="Historical counts before socket interiors were modelled in D2.4."
    owner["board_markings"]="Two case rings, four radiator tabs and visible faces on three coax sockets; original photo-registered finish on SOURCE."
    report["owner_topside"]["download"]={"file":BOARD.name,"bytes":len(data),"sha256":digest(BOARD),"meshes":len(board),"materials":len(tree.get("materials",[])),"material_names":[m["name"] for m in tree["materials"]],"textures":0,"units":"glTF m; same CAD datum","versioned_url":"reference/d2.6/mac-board-reference.glb"}
    return board

def rear_panel(bodies,mount,ports):
    panel=solid(next(m for n,m in bodies.items() if n.startswith("d2__panel__")))
    loops=[np.asarray(loop)*[1,-1] for loop in panel.rotate([90,0,0]).project().to_polygons()]
    boxes=[np.array([s.min(axis=0),s.max(axis=0)]) for s in loops]
    outer=np.argmax([np.prod(b[1]-b[0]) for b in boxes]);bbox=boxes.pop(outer);loops.pop(outer)
    assert len(loops)==8
    def contains(loop,x,z):
        return sum((q[1]>z)!=(r[1]>z) and x<(r[0]-q[0])*(z-q[1])/(r[1]-q[1])+q[0]
            for q,r in zip(loop,np.roll(loop,-1,axis=0)))%2==1
    aliases={"A1":"usb-a-1","A2":"usb-a-2","audio":"audio","HDMI":"hdmi","TB1":"tb-1","TB2":"tb-2","RJ":"ethernet","PD":"pd-in"}
    ids=[(name,*ports["ports"][key]["axis_xz_mm"]) for key,name in aliases.items()]
    seen=set();openings=[]
    for name,x,z in ids:
        matches=[i for i,s in enumerate(loops) if contains(s,x,z)]
        assert len(matches)==1 and matches[0] not in seen,(name,matches)
        i=matches[0];seen.add(i);u,v=loops[i].T
        openings.append(dict(id=name,probe_xz_mm=[x,z],bounds_xz_mm=boxes[i].round(3).tolist(),
            outline_xz_mm=loops[i].round(5).tolist(),through_area_mm2=round(abs(float(u@np.roll(v,1)-v@np.roll(u,1)))/2,3)))
    # Vertical rays through solid plastic just outside each opening measure
    # local wall thickness, different from the axial face-to-lip distance.
    xyz=np.asarray(panel.bounding_box()).reshape(2,3)
    assert abs(xyz[1,1]-ports["face_y_mm"])<.005
    face=float(xyz[1,1]);wall={}
    def panel_station(pt,thickness):
        px,pz=pt;hits=sorted(h.position[1] for h in panel.ray_cast([px,face-6,pz],[px,face+1,pz]))
        assert len(hits)==2 and abs(hits[-1]-face)<.005 and abs(hits[1]-hits[0]-thickness)<.006,(pt,hits,thickness)
        return {"probe_xz_mm":[round(px,5),round(pz,5)],"material_y_span_mm":np.round(hits,4).tolist(),"thickness_mm":round(hits[-1]-hits[0],4)}
    fields={}
    for key in aliases:
        item=ports["ports"][key]; wall[key]=panel_station(item["masked_bezel_probe_xz_mm"],item["mask_skin_thickness_mm"])
        fields[key]=panel_station(item["field_witness_xz_mm"],item["field_thickness_mm"])
    field=fields["A1"]
    assert all(field["thickness_mm"]==f["thickness_mm"] for f in fields.values()) and all(field["thickness_mm"]>a["thickness_mm"] for a in wall.values())
    return dict(wall_sections=wall,field=field,field_stations=fields,projection_bounds_xz_mm=bbox.round(3).tolist(),openings=openings,print_face="exterior",
        print_rotation_xyz_deg=[-90,0,0],mount={"travel_mm":mount["drop_mm"],"axis":[0,0,1],"installation_axis":[0,0,-1],
            "side_slots":2,"installation_xyz_mm":mount["waypoints_xyz_mm"],"roof_z_mm":round(float(xyz[1,2])+mount["locked_translation_bounds_xyz_mm"][1][2],3),"sill_z_mm":round(float(xyz[0,2]),3),
            "locked_translation_bounds_xyz_mm":mount["locked_translation_bounds_xyz_mm"]},
        scope="Through profiles and solid front wall stations of the packed panel only. Vertical travel in an empty chassis after unplugging and removing both assemblies and the lid.")

def sections(cad):
    report["power_view_sections"]={}
    for group,part,lo,hi in [("base","floorDetail",[-88.7,-30,5.95],[-72,58.41,16]),("lid","lidDetail",[-89,-30,8],[-72.5,58.41,46.05])]:
        [(name,mesh)]=read_glb(OUT/"geometry"/(group+".glb"))
        assert name==cad["groups"][group][0]
        shape=solid(mesh)^md.Manifold.cube(np.subtract(hi,lo)).translate(lo)
        assert shape.volume()>20
        m=shape.to_mesh64();add("section_of_"+name,tm.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False),part,"carrier","cutaway")
        report["power_view_sections"][name]={"box_mm":[lo,hi],"volume_mm3":round(float(shape.volume()),4)}

def add_illustrations(cad):
    # Only render-only groups come from the public assembly. All native and
    # board meshes are rebuilt above from the selected CAD, and cutaways are new.
    html=(FROZEN/"review/index.html").read_bytes()
    model=re.search(rb'<script id="model-bytes" type="application/octet-stream">([^<]+)</script>',html)
    assert model, "Missing frozen public model"
    packed=gzip.decompress(base64.b64decode(model[1],validate=True))
    baseline=read(HERE/"geometry-check.json"); old=read(FROZEN/"cad-validation.json")
    assert hashlib.sha256(packed).hexdigest()==baseline["sha256"]
    def box(d,g,match):
        n,=(n for n in d["groups"][g] if match in n)
        return np.array([d["bodies"][n]["bbox"][k] for k in ("min","max")])
    deltas={}
    for match,g,key in (("CMTPD","boards","trigger"),("MINI560","boards","buck"),("USB_C","socket","socket")):
        diff=box(cad,g,match)-box(old,g,match)
        deltas[key]=diff.mean(axis=0)
        if key=="socket":deltas[key][1]=diff[1,1]
    group_count={"v1":0,"rf":0,"look":0}
    for key,m in read_glb(io.BytesIO(packed)):
        layer,part,finish,name=key.split("__",3)
        if layer=="v1":
            assert name in baseline["comparison"] and np.allclose(m.bounds,baseline["comparison"][name],atol=.001,rtol=0)
            report["comparison"][name]=m.bounds.round(3).tolist()
            group_count["v1"]+=1
        elif part=="rf":
            label=name.split("_")[-1];info=baseline["source"][label]
            assert int(info["triangles"])==len(m.faces)
            report["source"][label]=info;group_count["rf"]+=1
        elif layer=="look" and part in ("buck","trigger"):
            m.apply_translation(deltas[part]);group_count["look"]+=1
        else: continue
        add(name,m,part,finish,layer)
    assert group_count=={"v1":31,"rf":3,"look":17},group_count
    report["illustration_source"]={"assembly_sha256":baseline["sha256"],"retained":group_count}
    return {k:(v+baseline["module_appearance_deltas_mm"][k]).round(4).tolist() for k,v in deltas.items()}

def front_prober(bodies):
    # First surface from +Y, directly against all DISPLAYED triangles in the
    # released assembly, including chassis, lid and independent PD insert.
    cache={}
    for name,m in bodies.items():
        l,g,_,_=name.split("__",3)
        if l in {"v1","gauge","cutaway"} or g=="rf":continue
        assert l!="portrait" and not(name.startswith("look__socket")),name
        cache[name]=(m.bounds,np.asarray(m.triangles))
    def read_ray(x,z,without_panel=False):
        surfaces=[]
        for name,(bounds,tri) in cache.items():
            if without_panel and name.startswith("d2__panel__"):continue
            if x<bounds[0,0] or x>bounds[1,0] or z<bounds[0,2] or z>bounds[1,2]:continue
            ok=(tri[:,:,0].min(axis=1)<=x)&(tri[:,:,0].max(axis=1)>=x)&(tri[:,:,2].min(axis=1)<=z)&(tri[:,:,2].max(axis=1)>=z)
            a,b,c=np.moveaxis(tri[ok],1,0)
            den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2])
            good=np.abs(den)>1.e-10
            a,b,c,den=a[good],b[good],c[good],den[good]
            u=((b[:,2]-c[:,2])*(x-c[:,0])+(c[:,0]-b[:,0])*(z-c[:,2]))/den
            v=((c[:,2]-a[:,2])*(x-c[:,0])+(a[:,0]-c[:,0])*(z-c[:,2]))/den
            weights=(u>=-1.e-6)&(v>=-1.e-6)&(u+v<=1+1.e-6)
            if np.any(weights):surfaces.append((float((u*a[:,1]+v*b[:,1]+(1-u-v)*c[:,1])[weights].max()),name))
        return max(surfaces) if surfaces else (-999,None)
    return read_ray

def front_area(mesh,lip,opening):
    # Project only the actual front-facing material at the lip plane. The
    # opening comes from the full through-profile of the packed solid plate.
    # No named bounding box or painted socket outline participates.
    def ccw(poly):
        x,z=np.asarray(poly).T
        return poly if x@np.roll(z,-1)-z@np.roll(x,-1)>0 else poly[::-1]
    tri=np.asarray(mesh.triangles)
    flat=tri[np.max(np.abs(tri[:,:,1]-lip),axis=1)<.004][:,:,[0,2]]
    assert len(flat)>2,(lip,len(flat))
    material=md.CrossSection([ccw(t) for t in flat],md.FillRule.NonZero)
    aperture=md.CrossSection([ccw(np.array(opening["outline_xz_mm"]))])
    total=material.area();visible=(material^aperture).area();covered=total-visible
    assert total>0 and covered>.1,(total,visible)
    allpts=flat.reshape(-1,2)
    return {"front_area_mm2":round(total,4),"bounds_xz_mm":np.round([allpts.min(axis=0),allpts.max(axis=0)],4).tolist(),"visible_through_aperture_mm2":round(visible,4),
            "covered_mm2":round(covered,4),"fraction_covered":round(covered/total,5)}

def face_rows(ports,contract,geom,face,bodies,cad):
    rows=[];ray=front_prober(bodies)
    order=("A1","A2","audio","HDMI","TB1","TB2","RJ","PD")
    shell,=cad["groups"]["socket"];insert,=cad["groups"]["socket_insert"]
    for k,opening in zip(order,geom["openings"]):
        v=ports["ports"][k];lip=v["socket_lip_y_mm"];depth=v["signed_face_minus_lip_mm"]
        assert abs(face-v["face_y_mm"])<.005 and abs(face-lip-depth)<.005 and depth>0,(k,v)
        xx,zz=v["axis_xz_mm"]
        if k!="PD":
            c=contract["ports"][k];assert abs(c["source_lip_y_mm"]-lip)<.005
            allowed=set(c["mesh_names"]);rim=next(n for n in allowed if n.endswith("_lip"))
            if k in ("TB1","TB2"):
                shield="oem__ports__macmetal__D26_tb_shared_shield"
                assert abs(bodies[shield].bounds[1,1]-contract["shared_bridges"]["tb_shared_shield_y_mm"])<.005
                allowed.add(shield)  # The shared envelope is the visible back stop in this shallow port study.
        else:
            allowed={n for n in bodies if n.split("__")[-1] in (shell,insert)}
            assert len(allowed)==2
            rim=next(n for n in allowed if n.endswith("__"+shell))
        probes={"masked_bezel":v["masked_bezel_probe_xz_mm"],"open_to_back":v["exposed_entrance_probe_xz_mm"]}
        tongue=[xx,zz] if k=="PD" else c["front_ray_probes_xz_mm"].get("tongue")
        if tongue and ray(*tongue)[1] in allowed:probes["tongue"]=tongue
        facts={}
        for role,pt in probes.items():
            y,n=ray(*pt)
            if role=="masked_bezel":
                assert n.startswith("d2__panel__") and abs(y-face)<.005,(k,role,pt,y,n)
                yy,nn=ray(*pt,without_panel=True)
                assert nn==rim and abs(yy-lip)<.012,(k,role,pt,yy,nn,rim)
            else:
                assert n in allowed,(k,role,pt,y,n)
                if role=="open_to_back":assert y<lip-.20 and abs(y-v["exposed_entrance_board_hit_y_mm"])<.018,(k,y,lip,v["exposed_entrance_board_hit_y_mm"])
            facts[role]={"xz_mm":np.round(pt,4).tolist(),"first_mesh":n,"y_mm":round(y,4),"depth_from_lip_mm":round(lip-y,4)}
        facts["masked_bezel"]["with_panel_removed"]={"first_mesh":nn,"y_mm":round(yy,4)}
        coverage=front_area(bodies[rim],lip,opening)
        if k.startswith("TB"):assert coverage["fraction_covered"]>.75,(k,coverage)
        lo,hi=np.asarray(opening["bounds_xz_mm"])
        assert np.allclose(hi-lo,v["aperture_xz_span_mm"],rtol=0,atol=.026),(k,hi-lo,v["aperture_xz_span_mm"])
        skin=geom["wall_sections"][k]["thickness_mm"];gap=v["nominal_axial_gap_mask_to_bezel_mm"]
        assert gap>0 and abs(gap+skin-depth)<.008,(k,skin,gap,depth)
        outer=v["outer_bezel_xz_span_mm"];side=None
        if k.startswith("TB"):
            back_center=c["outer_center_xz_mm"][0];ow=outer[0]
            side=[round(float(lo[0]-(back_center-ow/2)),4),round(float(back_center+ow/2-hi[0]),4)]
            assert min(side)>1.0 and abs(side[0]-side[1])<.02
        center=((hi+lo)*.5).round(4).tolist()
        below=round(max(0.,float(coverage["bounds_xz_mm"][0][1]-lo[1])),4) if k=="PD" else None
        rows.append(dict(id=k,lip_y_mm=lip,recess_mm=depth,axis_xz_mm=[xx,zz],skin_mm=skin,axial_clearance_mm=gap,front_overlap=coverage,outer_bezel_xz_span_mm=outer,masked_x_margin_mm=side,opening_center_xz_mm=center,aperture_below_lip_mm=below,
            opening_xz_mm=v["aperture_xz_span_mm"],bounds_xz_mm=opening["bounds_xz_mm"],probes=facts))
    return dict(face_y_mm=face,ports=rows,minimum_web_mm=ports["minimum_web_mm"],webs_face_mm=ports["webs_face_mm"],scope="Each positive recess consists of solid front mask plus air gap to the wider lip. Digital model only.")

def main(dest):
    reports={n:read(OUT/n) for n in ("cad-validation.json","fit-validation.json","ports-fit.json","mount-fit.json","board-install-fit.json","power-fit.json")}
    checked=reports["fit-validation.json"];cad=reports["cad-validation.json"]
    assert checked["status"]=="passed" and checked["cad_report_sha256"]==digest(OUT/"cad-validation.json")
    assert all(reports[n].get("revision")=="D2.6" and not reports[n].get("failures") for n in ("fit-validation.json","mount-fit.json","ports-fit.json","board-install-fit.json"))
    power_fit=reports["power-fit.json"];paths=power_fit["waypoints_xyz_mm"]
    assert not power_fit["failures"] and power_fit["comparisons"]==checked["specialized"]["power"] and paths[-1]==[0,0,0]
    assert len(paths)>1 and all(len(q)==3 for q in paths)
    mount=reports["mount-fit.json"];ports=reports["ports-fit.json"];board_fit=reports["board-install-fit.json"]
    assert len(board_fit["waypoints_xyz_mm"])>=3 and np.allclose(board_fit["waypoints_xyz_mm"][-1],[0,0,0])
    assert mount["waypoints_xyz_mm"][-1]==[0,0,0] and np.isclose(mount["waypoints_xyz_mm"][0][2],mount["drop_mm"]) and mount["continuous_travel"] and mount["comparisons"]>0 and ports["comparisons"]>0
    report.update(revision="D2.6",variant="D2.6-FDM")
    load_native(cad)
    reference=load_board_and_rf()
    sections(cad);report["module_appearance_deltas_mm"]=add_illustrations(cad)
    dest.mkdir(exist_ok=False,parents=True)
    data=tm.exchange.gltf.export_glb(scene,include_normals=True);path=dest/"assembly.glb";path.write_bytes(data)
    reader=dict(read_glb(path));assert len(reader)==len(scene.geometry)
    for n,v in reference.items():
        assert np.array_equal(reader[n].faces,v.faces) and np.allclose(reader[n].vertices,v.vertices,atol=.00001,rtol=0),n
    native=cad["bodies"]
    for n,m in reader.items():
        s=n.split("__")[-1]
        if s in native:assert np.allclose(m.bounds,[native[s]["bbox"][k] for k in ("min","max")],atol=.012,rtol=0),s
    panel_name=cad["groups"]["panel"][0]
    assert report["native"][panel_name]["group"]=="panel" and set(native)==set(report["native"])
    rear=rear_panel(reader,mount,ports)
    contract=read(STUDY/"port-contract.json")
    assert contract["revision"]==cad["revision"]=="D2.6"
    assert digest(BOARD)==cad["owner_board_sha256"]==checked["owner_board_sha256"]
    assert digest(STUDY/"port-contract.json")==cad["port_contract_sha256"]
    assert set(contract["ports"])==set(ports["ports"])-{"PD"}
    assert all(set(c["mesh_names"]) <= set(reference) for c in contract["ports"].values())
    report["owner_topside"]["registered_board_basis"]={"source":"prototype-d26/board-study/port-contract.json","mesh_nodes":len(reference),"open_port_faces":len(contract["ports"])}
    port_fit=face_rows(ports,contract,rear,native[panel_name]["bbox"]["max"][1],reader,cad)
    report["board_port_study"]={"contract_sha256":digest(STUDY/"port-contract.json"),"board_sha256":digest(BOARD)}
    service={"panel_remove_xyz_mm":list(reversed(mount["waypoints_xyz_mm"])),"board_install_xyz_mm":board_fit["waypoints_xyz_mm"],"pd_remove_xyz_mm":list(reversed(paths)),
             "power_scope":"The loaded saddle, both modules and USB-C socket follow the checked removal path with the Mac and the panel seated."}
    # Times are the presentation clock only; coordinates come from the CAD checks.
    def stops(path,known,lo,hi):
        return known if len(path)==len(known) else np.linspace(lo,hi,len(path)).round(3).tolist()
    service["board_remove_stops_pct"]=stops(service["board_install_xyz_mm"],[54,60,65,74],54,74)
    panel_path=service["panel_remove_xyz_mm"]
    service["panel_remove_stops_pct"]=[round(74+26*pt[2]/mount["drop_mm"],5) for pt in panel_path]
    service["pd_detail_stops_pct"]=stops(paths,[40,60,76,100],40,100)
    power_delta=report["module_appearance_deltas_mm"];service["power_datum_offsets_xyz_mm"]={**power_delta,"saddle":power_delta["trigger"]}
    report.update(meshes=len(reader),size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),rear_panel=rear,
        port_fit=port_fit,service=service,reports_sha256={name:digest(OUT/name) for name in reports})
    (dest/"geometry-check.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(len(native),"native bodies, 8 through profiles; board assembly path:",service["board_install_xyz_mm"],"packed:",report["sha256"])

if __name__=="__main__":
    if not __debug__:
        raise SystemExit("Geometry packing requires Python assertions; run without -O or PYTHONOPTIMIZE.")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cad-dir",type=Path,required=True,help="verified prototype-d26 from the CAD build")
    parser.add_argument("--output",type=Path,default=ROOT/"build/d26-packed",help="new directory")
    args=parser.parse_args()
    OUT=args.cad_dir.resolve();STUDY=OUT/"board-study";BOARD=STUDY/"mac-board-reference.glb"
    main(args.output.resolve())
