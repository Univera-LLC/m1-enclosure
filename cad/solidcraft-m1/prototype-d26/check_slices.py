"""Ender-3 Pro / 0.4 mm / PETG: prove D2.6 metal tips, protruding audio collar, T-bridge, and masked frames clear actual extrusions."""
import argparse
import os
import shutil
if not __debug__:
    raise RuntimeError("D2.6 slicer checks require Python without -O or PYTHONOPTIMIZE")
from hashlib import sha256
from importlib.util import spec_from_file_location,module_from_spec
import json
from pathlib import Path
import re
import subprocess
import numpy as np
from check_gauges import OUT,md,nose,extrusion,rj_spring

def module(n,p):
    spec=spec_from_file_location(n,p);m=module_from_spec(spec);spec.loader.exec_module(m);return m

old=module('prior_toolpath_math',OUT.parent/'prototype-d24/check_slices.py')
old.OUT=OUT
slicer=old.slicer
slicer.TMP=OUT/'.work'/'slicer'
paths=old.paths
read=old.read
PANEL='02-flat-rear-panel.stl'

def panel_config(cfg):
    data=cfg.read_text(encoding='utf8')
    for key in ('layer_height','first_layer_height'):
        data,n=re.subn('(?m)^'+key+r'\s*=.*$',key+' = 0.10',data);assert n==1
    out=cfg.with_name('d26-face-0p10.ini');out.write_text(data,encoding='utf8')
    return out

def material_depth(seg,point):
    a=seg[:,:2];d=seg[:,2:4]-a; delta=point-a
    t=np.clip(np.einsum('ij,ij->i',delta,d)/(d*d).sum(axis=1),0,1)
    return float(np.max(seg[:,4]/2-np.linalg.norm(delta-t[:,None]*d,axis=1)))

def load_gauges_d26(native):
    contract=read(OUT/'board-study/port-contract.json')['ports']
    rims={n:next(m for m in row['mesh_names'] if m.endswith('_lip')) for n,row in contract.items()}
    faces=old.read_meshes(OUT/'board-study/mac-board-reference.glb',rims.values())
    board=old.complete_board()
    by_port={}
    for n,m in rims.items():
        bb=faces[m].bounds
        want_y=contract[n].get('protruding_collar_tip_y_mm',contract[n]['source_lip_y_mm'])
        assert abs(bb[1,1]-want_y)<.001,(n,bb[1,1],want_y)
        lo=bb[0]-[1.,0,1.]; hi=bb[1]+[1.,.2,1.]; lo[1]=54.1
        cut=board ^ md.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
        assert not cut.is_empty()
        by_port[n]=cut.rotate([-90,0,0])
    # Also verify the photographed silver T-bridge, audio upper shield, and shared TB rear shield against G-code beads!
    for label,lo,hi in [
        ('USB_A_vertical_bridge',[24.5,54.1,17.5],[58.1,56.5,26.6]),
        ('Audio_horizontal_bridge_and_shield',[35.8,54.1,26.3],[46.8,56.5,36.1]),
        ('TB_shared_shield',[-39.8,54.1,17.1],[-12.8,55.3,25.0]),
    ]:
        cut=board ^ md.Manifold.cube([b-a for a,b in zip(lo,hi)]).translate(lo)
        assert not cut.is_empty(),label
        by_port[label]=cut.rotate([-90,0,0])
    power=old.read_solids(OUT/'geometry/socket.glb',native['groups']['socket'])
    by_port['PD']=md.Manifold.batch_boolean(list(power.values()),md.OpType.Add)
    centres={n:np.asarray(row.get('protruding_collar_center_xz_mm',row['axis_xz_mm'])) for n,row in contract.items()}
    for n,row in contract.items():
        want_y=row.get('protruding_collar_tip_y_mm',row['source_lip_y_mm'])
        assert abs(-by_port[n].bounding_box()[2]-want_y)<.001,(n,-by_port[n].bounding_box()[2],want_y)
    centres['PD']=np.array(paths.CENTRES['PD IN'])
    return by_port,centres

def assess(gcode):
    fit=read(OUT/'ports-fit.json');mount=read(OUT/'mount-fit.json')
    native=read(OUT/'cad-validation.json')
    face=fit['face_y_mm'];play=np.array(mount['field_motion_conservative_xyz_mm'])
    name,=native['groups']['panel'];bb=native['bodies'][name]['bbox']
    mid=(np.array(bb['min'])+bb['max'])[[0,2]]/2
    rims,centres=load_gauges_d26(native)
    metal={}
    for n,at in centres.items():
        lip=fit['ports'][n]['socket_lip_y_mm'];metal[n]=extrusion(nose(n,at),lip-.30,face+.25).rotate([-90,0,0])
    latch={n:m.rotate([-90,0,0]) for n,m in rj_spring(centres['RJ'][0],fit['ports']['RJ']['socket_lip_y_mm']).items()}
    layers=paths.deposited(gcode)
    assert np.allclose(list(layers),np.arange(.10,2.61,.10),atol=.0001) and len(layers)==26
    result={};z0=0.;origin=None;nseg=0
    for z,layer in layers.items():
        rings=layer['rings'];outer=max(range(len(rings)),key=lambda i:np.ptp(rings[i][0][:,0]))
        boundary=rings[outer][0]
        if origin is None:
            assert np.all(np.ptp(boundary,axis=0)>[159.,31.])
            origin=(boundary.min(axis=0)+boundary.max(axis=0))/2-mid
        seg=np.asarray(layer['segments']);seg[:,:2]-=origin;seg[:,2:4]-=origin;nseg+=len(seg)
        ids={n:[i for i,(ring,*_) in enumerate(rings) if i!=outer and paths.inside(*(origin+at),ring)] for n,at in centres.items()}
        if z<=.401:
            assert all(len(q)==1 for q in ids.values()) and len({q[0] for q in ids.values()})==8,(z,ids)
        gaps={}
        for label,solids in [('metal_nose_to_bead_mm',metal),('socket_frame_to_bead_mm',rims),('latch_to_bead_mm',latch)]:
            row={}
            for n,solid in solids.items():
                outline=old.gauge_silhouette(solid,face+play[0,1]-z,face+play[1,1]-z0,play)
                if outline is None:continue
                gap=old.bead_gap(seg,outline)
                criterion=.10 if n=='PD' and label=='metal_nose_to_bead_mm' else .012
                assert gap>criterion,(z,label,n,round(gap,5),'programmed bead intersects or consumes running clearance')
                row[n]=round(gap,4)
            gaps[label]=row
        depths={}
        for n,row in fit['ports'].items():
            mask=row['mask_skin_thickness_mm'];at=np.asarray(row['masked_bezel_probe_xz_mm'])
            if z<mask+.11:
                depths[n]=round(material_depth(seg,at),4)
                if n!='PD':
                    if z<=mask+.001:assert depths[n]>0.,(z,n,'mask missing',depths[n])
                    else:assert depths[n]<0.,(z,n,'pocket not open',depths[n])
        result[z]={'separate_socket_holes':len({q[0] for q in ids.values() if len(q)==1}),**gaps,
                   'signed_bead_coverage_of_mask_witness_mm':depths}
        if z<=.901:
            pairs=[('USB-A pair','A1','A2'),('TB pair','TB1','TB2')] if z<=.801 else [('TB pair','TB1','TB2')]
            result[z]['deposited_webs']={label:old.deposited_web(seg,(centres[a]+centres[b])/2,1.5)
                for label,a,b in pairs}
        z0=z
    def minima(key,items):
        return {n:min(r[key][n] for r in result.values() if n in r[key]) for n in items}
    return {'positive_extrusion_segments':nseg,'minimum_metal_nose_to_bead_mm':minima('metal_nose_to_bead_mm',metal),
            'minimum_socket_frame_to_bead_mm':minima('socket_frame_to_bead_mm',rims),'minimum_RJ_spring_to_bead_mm':minima('latch_to_bead_mm',latch),
            'installed_field_motion_xyz_bounds_mm':play.tolist(),'layer_results':result,
            'panel_first_layer_elephant_foot_compensation_mm':.10,
            'mask_witness_caveat':'At separate PD the side rim is only 0.05 mm past the nominal aperture edge. First-layer compensation can uncover this specific witness; upper PD skin layers (layers 2-4 = 0.40 mm) are recorded separately. The seven Apple rim witnesses have complete programmed mask coverage for their 8 (0.80 mm) or 9 (0.90 mm) mask layers, and the recessed Ø5.00 mm audio collar clears all 26 layers.',
            'scope':'Conservative convex silhouettes per axial deposited layer include closed-panel translation and tilt. Positive coverage denotes bead over the specific mask witness. PETG swell, elephant foot, adhesion, material strength, actual fit and force remain unmeasured.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--slicer',type=Path,default=os.environ.get('PRUSA_SLICER') or shutil.which('prusa-slicer-console'));args=ap.parse_args()
    if args.slicer is None:ap.error("supply --slicer or set PRUSA_SLICER")
    slicer.TMP.mkdir(parents=True,exist_ok=True)
    exe=args.slicer.resolve();cfg,vendor=slicer.config(exe);fine=panel_config(cfg)
    folder=OUT/'print';stls=read(folder/'stl-checks.json');refs=stls['parts']
    digest=lambda p:sha256(p.read_bytes()).hexdigest()
    fh=digest(OUT/'fit-validation.json');ch=digest(OUT/'cad-validation.json')
    assert stls['fit_report_sha256']==fh and stls['cad_report_sha256']==ch
    assert len(refs)==8 and refs[PANEL]['bed_face']['side']=='exterior'
    parts={}
    for n,record in refs.items():
        scan=slicer.slice_one(exe,fine if n==PANEL else cfg,folder/n)
        assert scan['input_sha256']==record['sha256'] and not scan['warnings'],(n,scan)
        parts[n]=scan
    assert parts[PANEL]['bridge_regions']==0 and parts[PANEL]['layers']==26
    paths_report=assess((slicer.TMP/'02-flat-rear-panel.gcode').read_text(encoding='utf8'))
    n='03-monolithic-base.stl';seams={parts[n]['seam_position']:parts[n]}
    for seam in ('aligned','rear'):
        if seam not in seams:seams[seam]=slicer.slice_one(exe,cfg,folder/n,seam)
    assert len(seams)==3 and all(not r['warnings'] and r['input_sha256']==refs[n]['sha256'] for r in seams.values())
    report={'revision':'D2.6','slicer':subprocess.check_output([str(exe),'--help'],encoding='utf8',errors='replace').splitlines()[0],
            'presets':slicer.PRESETS,'scope':'Offline, no printer. Ordinary parts 0.20 mm; panel 0.10 mm INCLUDING first layer (26 layers = 2.60 mm), Classic, 100% Rectilinear. No supports.',
            'panel_layer_height_mm':.1,'panel_first_layer_height_mm':.1,'vendor_ini_sha256':vendor,'panel_config_sha256':digest(fine),
            'parts':parts,'full_base_seam_checks':seams,'extrusion_paths':paths_report,'fit_report_sha256':fh,'cad_report_sha256':ch}
    (folder/'slice-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('8 final STLs;',parts[PANEL]['layers'],'panel layers;',paths_report['positive_extrusion_segments'],'verified extrusion segments')

if __name__=='__main__':main()
