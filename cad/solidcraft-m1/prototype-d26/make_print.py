"""Export D2.6 with the outside face flat on the bed; cut guide and lid samples from the production solids."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import numpy as np
import trimesh
from build_d26 import OUT, FILES, PLASTICS, REVISION, base, PANEL, power, dump, digest
import design
import check_d1 as qa

def run():
    fit=json.loads((OUT/"fit-validation.json").read_text())
    assert fit.get("status")=="passed" and not fit["failures"] and fit["cad_report_sha256"]==digest(OUT/"cad-validation.json")
    parts=qa.k.load_parts(OUT,FILES)
    spec=[
        ("01-power-saddle",power.HOLDER,[0,0,0]),
        ("02-flat-rear-panel",PANEL,[-90,0,0]),
        ("03-monolithic-base",base.BASE,[0,0,0]),
        ("04-vented-lid",base.LID,[180,0,0]),
        ("05-front-blank",base.BLANK,[-90,0,0]),
    ]
    assert {s[1] for s in spec}==set(PLASTICS)
    coupons={"06-board-datum-strip":(base.BASE,[-57.40,-39.75,5.95],[53.35,-27.6,14.90],[0,0,0]),
             "07-side-guide-sample":(base.BASE,*design.COUPONS['side-guide'],[0,0,0]),
             "08-lid-stop-sample":(base.LID,*design.COUPONS['lid-stop'],[180,0,0])}
    targets=[(slug,n,parts[n],rot,None) for slug,n,rot in spec]
    for slug,(n,lo,hi,rot) in coupons.items():
        targets.append((slug,n,parts[n]^qa.rect(lo,hi),rot,[lo,hi]))
    out=OUT/"print";out.mkdir(exist_ok=True)
    records={}
    for slug,n,src,rot,crop in targets:
        v=src.rotate(rot);lo,hi=qa.q.bounds(v)
        m=v.translate((-lo).tolist()).to_mesh64()
        mesh=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False)
        f=out/(slug+".stl");mesh.export(f)
        s=trimesh.load_mesh(f,process=True)
        assert s.is_volume and s.body_count==1 and np.allclose(s.bounds[0],0,atol=.0002),slug
        assert np.allclose(s.extents,hi-lo,atol=.0002) and max(s.extents[:2])+16<=220,slug
        assert abs(s.volume/src.volume()-1)<.0001,slug
        layer_mm=.10 if n==PANEL else .20
        heights=np.arange(layer_mm/2,s.extents[2],layer_mm)
        bedsolid=v.translate((-lo).tolist());last=None;floating=[]
        for z in heights:
            layer=bedsolid.slice(z)
            if last is not None:
                support=last.offset(.20)
                for island in layer.decompose():
                    if island.area()>.10 and (island^support).area()<.005:floating.append(round(float(z),3))
            last=layer
        assert not floating,(slug,floating)
        records[f.name]={"body":n,"rotation_xyz_deg":rot,"size_xyz_mm":s.extents.round(3).tolist(),"volume_mm3":round(s.volume,3),
            "closed_shells":s.body_count,"crop_desk_mm":crop,"bed_contact_area_at_z_0_1_mm2":round(bedsolid.slice(.10).area(),2),
            "sample_layer_height_mm":layer_mm,"unsupported_new_islands":floating,"sha256":digest(f)}
        if n==PANEL:
            native=src.to_mesh64();tri=np.asarray(native.vert_properties)[np.asarray(native.tri_verts),:3]
            exterior=qa.q.bounds(src)[1,1];plane=tri[np.all(abs(tri[:,:,1]-exterior)<.0001,axis=1)]
            area=float(np.linalg.norm(np.cross(plane[:,1]-plane[:,0],plane[:,2]-plane[:,0]),axis=1).sum()/2)
            floor=np.max(np.abs(s.triangles[:,:,2]),axis=1)<.0001
            bed_area=float(s.area_faces[floor].sum())
            assert area>4200 and abs(area-bed_area)<.05 and np.all(s.face_normals[floor,2]<-.999)
            near=bedsolid.slice(.05)
            assert len(near.decompose())==1 and len(near.to_polygons())==9
            ratios=[near.area()/bedsolid.slice(z).area() for z in heights if z>0]
            assert min(ratios)>.96 and np.array_equal(rot,[-90,0,0])
            records[f.name]["bed_face"]={"side":"exterior","desk_y_mm":round(float(exterior),3),
                "outward_normal_print":[0,0,-1],"print_xy":"desk X and +Z, translated onto bed",
                "area_of_CAD_exterior_mm2":round(area,2),"area_of_downward_STL_triangles_at_Z0_mm2":round(bed_area,2),
                "islands_on_first_section":1,"openings_on_first_section":8,
                "first_to_largest_layer_area_ratio":round(min([1.0,*ratios]),5)}
    dump(out/"stl-checks.json",{"revision":REVISION,"cad_report_sha256":digest(OUT/"cad-validation.json"),"fit_report_sha256":digest(OUT/"fit-validation.json"),"scope":"Bed-oriented mm meshes. Five D2.6 parts: use 01-04 together; only 05 is carried over from D2.5. Three fit coupons are crops of the production base and lid. No reference tray, PCB, fastener or G-code is a print.","parts":records})
    print([s["size_xyz_mm"] for s in records.values()])

def package():
    out=OUT/"print";proof=json.loads((out/"stl-checks.json").read_text());records=proof["parts"]
    fit=json.loads((OUT/"fit-validation.json").read_text())
    assert fit["status"]=="passed" and not fit["failures"]
    assert proof["cad_report_sha256"]==fit["cad_report_sha256"]==digest(OUT/"cad-validation.json") and proof["fit_report_sha256"]==digest(OUT/"fit-validation.json"),"STL not generated from current native CAD and final fit gates"
    sliced=json.loads((out/"slice-checks.json").read_text())["parts"]
    assert records.keys()==sliced.keys()
    for n in records:assert digest(out/n)==records[n]["sha256"]==sliced[n]["input_sha256"],n
    for name,keys in [("d2.6-cold-fit-kit.zip",list(records)[:5]),("d2.6-first-fit.zip",[n for n in records if n[:2] in ("01","02","06","07","08")])]:
        members={n:out/n for n in keys}
        members.update({n:OUT/n for n in ("FIT-FIRST.md","CREDITS.txt")})
        members.update({n:out/n for n in ("slice-checks.json","stl-checks.json")})
        with zipfile.ZipFile(OUT/name,"w",zipfile.ZIP_DEFLATED) as archive:
            for n,path in members.items():archive.write(path,n)
        with zipfile.ZipFile(OUT/name) as archive:
            assert archive.testzip() is None and set(archive.namelist())==set(members)
            for n,path in members.items():assert hashlib.sha256(archive.read(n)).hexdigest()==digest(path)
        print(name,keys)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--package",action="store_true");a=p.parse_args()
    (package if a.package else run)()
