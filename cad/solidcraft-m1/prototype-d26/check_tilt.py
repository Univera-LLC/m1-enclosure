"""Certify the closed-panel motion bound at every masked opening on the actual D2.6 guides."""
from pathlib import Path
import importlib.util
import itertools
import sys
import numpy as np
import design as s

def assess(parts):
    path=s.OUT.parent/'prototype-d24/board-study/check_panel_tilt.py'
    sys.path.insert(0,str(path.parent))
    try:
        spec=importlib.util.spec_from_file_location('rigid_support_planes',path)
        calc=importlib.util.module_from_spec(spec);spec.loader.exec_module(calc)
    finally: sys.path.remove(str(path.parent))
    from build_d26 import dump,digest
    # Inboard guide/cam/pad datums sit at dy=s.D (0.36); panel outer face extends to FACE=57.36.
    dy=s.D
    panel,base,lid=[parts[n].translate([0,-dy,0]) for n in (s.PANEL,s.base.BASE,s.base.LID)]
    rows,obs=calc.measurements(panel,base,lid)
    env=calc.Envelope(rows)
    proof=calc.finite_faces(env,obs,base,lid)
    probes={n:np.asarray([p for ring in q['outer_loops_xz_mm'] for p in ring])
            for n,q in s.mouths().items()}
    probes['PD']=np.array([[-81.55,17.73],[-78.30,26.67]])
    per={}
    for n,ring in probes.items():
        a,b=ring.min(axis=0)-.8,ring.max(axis=0)+.8
        v=np.asarray([env.at([x,y-dy,z]) for x,y,z in itertools.product((a[0],b[0]),(s.FIELD_IN-.01,s.FACE+.01),(a[1],b[1]))])
        per[n]=[np.floor(v[:,0].min(axis=0)*1.e5)/1.e5,np.ceil(v[:,1].max(axis=0)*1.e5)/1.e5]
    union=np.stack([np.min([p[0] for p in per.values()],axis=0),np.max([p[1] for p in per.values()],axis=0)])
    proposed=np.array([[-.125,-.085,-.002],[.125,.002,.204]])
    assert np.all(union[0]>=proposed[0]) and np.all(union[1]<=proposed[1]),(union,proposed)
    for group in obs.values():
        for row in group:row['p_mm'][1]=round(row['p_mm'][1]+dy,6)
    report={'revision':'D2.6','source':'actual exported panel, base and lid; fresh half-space measurements and finite-triangle checks',
            'scope':'Closed seated rigid panel and engaged datums; hold both upper corners against outside guides when lid is open. No rigidity/warp measurement.',
            'geometry_sha256':{n:digest(s.OUT/'geometry'/(n+'.glb')) for n in ('panel','base','lid')},
            'station_measurements_and_halfspaces':obs,'finite_support_triangles':proof,
            'per_port_excursion_xyz_mm':{n:np.asarray(p).tolist() for n,p in per.items()},
            'summary':{'all_port_fields_within_guard':True,'actual_union_xyz_mm':union.tolist(),'guard_xyz_mm':proposed.tolist(),
                       'verified_contact_faces':proof['planes_verified_over_entire_projected_excursion']}}
    dump(s.OUT/'board-study/panel-tilt-validation.json',report)
    return report
