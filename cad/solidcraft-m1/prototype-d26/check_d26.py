"""Run D2.6 manufacturing/assembly gates on the exact re-imported revision."""
import itertools,json
import numpy as np
import design as s
from build_d26 import dump,digest,operations_hash,features,BOARD
from check_geometry import *
import check_mount,check_board_insertion,check_ports,check_power

def base_checks(p,act):
    b=s.base;pf=p[b.BASE];lid=p[b.LID];board=act[BOARD_LABEL];tests={};loads={};vents={}
    for i,(x,y) in enumerate(b.PCB_AXES):
        vertical=board.ray_cast([x+2.65,y,12.],[x+2.65,y,30.]);assert np.allclose([j.position[2] for j in vertical],[14.,17.4],atol=.003)
        assert abs(pf.ray_cast([x+2.65,y,20],[x+2.65,y,10])[0].position[2]-14.)<.003
        down=vol(board.translate([0,0,-.04]),pf^qa.rod(x,y,12.8,8.4,2.0));up=vol(board.translate([0,0,.12]),p[b.PCB_HARDWARE[i]])
        assert .7<down<1.2 and up>1.;loads[str(i+1)]={'down_0_04_mm3':down,'up_0_12_against_screw_mm3':up}
    for x,y in b.ANTI_TIP:
        xy=[x+.6,y+2.82];a=pf.ray_cast([*xy,17.7],[*xy,9.0])[0].position[2];u=board.ray_cast([*xy,9.0],[*xy,17.7])[0].position[2]
        assert abs(u-a-.30)<.006
    c={n:q for n,q in p.items() if n not in b.LID_HARDWARE}
    tests['lid screw access']=free('lid access',cross({str(i):qa.rod(x,y,46.02,4.,18.) for i,(x,y) in enumerate(b.LID_AXES)}, {**c,**act}))
    tests['Mac screw access after seating board']=free('PCB access',cross({str(i):qa.rod(x,y,19.22,4.,38.) for i,(x,y) in enumerate(b.PCB_AXES)},
                       {**act,b.BASE:pf,s.PANEL:p[s.PANEL],b.BLANK:p[b.BLANK]}))
    for name,host,z,w,lanes in [('floor',pf,7.35,b.d.b.IN_W,[(x,*b.d.b.IN_SPAN) for x in b.MAIN_LANES]),('lid',lid,45.,b.d.b.VENT_W,[(x,a,c) for x in b.MAIN_LANES for a,c in b.d.b.ROOF_SPANS])]:
        cut=host.slice(z);areas=sum((md.CrossSection.square([w+.12,hi-lo+.12],center=True).translate([x,(lo+hi)/2])-cut).area() for x,lo,hi in lanes)
        nom=sum((hi-lo-w)*w+np.pi*(w/2)**2 for x,lo,hi in lanes);assert abs(areas/nom-1)<.015;vents[name]=round(areas,2)
    return {'revision':'D2.6','comparisons':sum(tests.values())+10,'failures':[],'source_board_axes_xy_mm':b.PCB_AXES,'ring_load_challenges':loads,
            'unthreaded_anti_tip_gap_mm':.30,'vent_areas_mm2':vents,'checks':tests,'scope':'Registered board and unchanged two mounting axes; the profiled top of each locating collar is confirmed in the separate insertion report.'}

def _run():
    native=json.loads((s.OUT/'cad-validation.json').read_text())
    assert native['revision']=='D2.6'
    assert native['owner_registered_stl_sha256']==digest(s.OUT/'board-study/registered-board.stl')
    assert native['fascia_contract_sha256']==digest(s.FASCIA_CONTRACT)
    assert native['operations_sha256']==operations_hash(features())
    assert native['port_contract_sha256']==digest(s.CONTRACT) and native['owner_board_sha256']==digest(BOARD)
    assert all(digest(s.OUT/f)==sh for f,sh in native['files_sha256'].items())
    p=parts();act=owner();rf=optional();alln={**p,**act};checks={};sub={}
    def check(name,pairs):checks[name]=free(name,pairs,.0004)
    report={'revision':'D2.6','status':'running','checks':checks,'specialized':sub,'failures':[],'cad_report_sha256':digest(s.OUT/'cad-validation.json'),
            'fascia_contract_sha256':digest(s.FASCIA_CONTRACT),'panel_glb_sha256':digest(s.OUT/'geometry/panel.glb'),
            'owner_board_sha256':digest(BOARD),'fitted_antenna_references':0,'physical_status':'NOT TESTED'}
    dest=s.OUT/'fit-validation.json'
    try:
        for n,obj in p.items():
            val=native['bodies'][n]
            assert np.allclose(bounds(obj),[val['bbox'][k] for k in ('min','max')],atol=.010,rtol=0),(n,bounds(obj),val['bbox'])
            assert abs(obj.volume()/val['volume_mm3']-1)<.013 and len([c for c in obj.decompose() if c.volume()>.0003])==1,n
        check('All 25 physical native bodies',((a,pa,b,pb) for (a,pa),(b,pb) in itertools.combinations(p.items(),2)))
        check('Registered photographed Mac and both local harnesses against all native exports',cross(act,p))
        check('Three detached historical antenna candidates measured separately vs all native exports',cross(rf,p))
        fixed={n:v for n,v in alln.items() if n not in (s.base.LID,*s.base.LID_HARDWARE)}
        lid=p[s.base.LID]
        clearance_targets={**fixed,'all admitted parallel panel poses':guide_guard(p[s.PANEL])}
        lid_sweeps={}
        for n,v in clearance_targets.items():
            try: lid_sweeps[n]=sweep.axial_cover(lid,v,[0,0,0],[0,0,49.])
            except AssertionError as e: raise AssertionError(('lid lift',n,*e.args)) from e
        ear=lid^rect([-83.1,53.,26.80],[-78.0,55.62+s.PD_SHIFT,31.0])
        lid_sweeps['PD toe releases through narrow internal track; conservative local angular field']=sweep.axial_cover(ear,field_guard(p[s.PANEL]),[0,0,0],[0,0,49.])
        checks['Closed lid releases vertically from assembled panel, sockets and chassis']=len(lid_sweeps)
        air=json.loads((s.OLD/'photo-study/board_fins_report.json').read_text())['d2_1']['updated_gauges_desk_mm']
        assert len(air)==21;lanes={f'{n}/{i}':rect(np.minimum(a,b)-.7,np.maximum(a,b)+.7) for n,pts in air.items() for i,(a,b) in enumerate(zip(pts,pts[1:]))}
        check('21 adapted convection channels vs current installed bodies',cross(lanes,alln))
        dimensions=np.ptp(np.vstack([bounds(t) for t in alln.values()]),axis=0).round(3).tolist()
        # Assembly envelope grows by +0.60 mm rear thickening: 170.00 x 119.91 x 46.00 (still 2.09 mm shorter than D2.1/D2.2).
        assert np.allclose(dimensions,[170.,119.91,46.],atol=.015),dimensions
        report['assembly_xyz_mm']=dimensions
        for name,fn in [('mount',lambda:check_mount.assess(p)),('board-install',lambda:check_board_insertion.assess(p,act)),('ports',lambda:check_ports.assess(p,act)),('base',lambda:base_checks(p,act)),('power',lambda:check_power.assess(p,act,rf))]:
            result=fn();assert not result['failures']
            result['cad_report_sha256']=report['cad_report_sha256'];result['panel_glb_sha256']=report['panel_glb_sha256']
            dump(s.OUT/(name+'-fit.json'),result);sub[name]=result['comparisons']
    except Exception as e:
        report['status']='failed';report['failures']=[repr(e)];dump(dest,report);raise
    report.update(status='passed',comparisons=sum(checks.values()),total_with_specialized_comparisons=sum(checks.values())+sum(sub.values()),adapted_air_gauges=21)
    dump(dest,report);print(dimensions,sub,report['total_with_specialized_comparisons'],'passed')

def run():
    # Invalidate an earlier success even if input hashing or reference loading fails.
    dest = s.OUT/'fit-validation.json'
    attempt = {'revision':'D2.6','status':'running','physical_status':'NOT TESTED'}
    dump(dest,attempt)
    try:
        _run()
    except Exception as exc:
        if json.loads(dest.read_text(encoding='utf8'))['status'] != 'failed':
            dump(dest,{**attempt,'status':'failed','failures':[repr(exc)]})
        raise

if __name__=='__main__':run()
