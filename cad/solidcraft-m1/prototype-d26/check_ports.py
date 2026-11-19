"""Measure the mask, internal pocket, protruding audio collar, and real openings independently on exported D2.6 solids."""
import itertools
import numpy as np
import design as s
from check_geometry import *
from check_gauges import NOSES,SHOULDERS,SOURCES,nose,shoulder,section,extrusion,negative_play_convex,rj_spring
import check_ports_d21 as geom

PLAY_FIELD=np.array([[-.125,-.085,-.002],[.125,.002,.204]])
EXPECTED={'A1':(13.12,5.76),'A2':(13.12,5.76),'HDMI':(15.04,5.60),'TB1':(9.10,3.30),'TB2':(9.10,3.30),
          'audio':(5.90,5.90),'RJ':(13.20,10.37),'PD':(3.05,8.87)}
PORT_PROFILE={'A1':'rounded rectangle','A2':'rounded rectangle','HDMI':'two desk-upper chamfers','TB1':'capsule','TB2':'capsule',
              'audio':'circle (clears protruding Ø5.00 collar)','RJ':'wide body, narrower lower latch passage','PD':'vertical capsule'}
MASK_DELTA={'A1':(7.10,0),'A2':(7.10,0),'HDMI':(7.90,0),'TB1':(0,2.25),'TB2':(0,2.25),
            'audio':(4.10,0),'RJ':(7.25,0),'PD':(1.575,0)}
FIELD_PROBE={'A1':(49.9,29.0),'A2':(32.7,29.0),'HDMI':(-1.525,28.0),'TB1':(-19.05,27.5),
             'TB2':(-33.70,27.5),'audio':(49.50,32.20),'RJ':(-64.65,30.50),'PD':(-83.8,22.20)}

def beam(part,xz):
    x,z=xz
    return sorted([float(h.position[1]) for h in part.ray_cast([x,62.,z],[x,53.5,z])],reverse=True)

def contains(cs,x,z):
    tiny=md.CrossSection.square([.02,.02],True).translate([x,z])
    return (tiny-cs).area()<.000005

def verify_profile(n,hole,loop,at):
    sz=np.ptp(loop,axis=0)
    assert np.allclose(sz,EXPECTED[n],atol=.012,rtol=0),(n,sz,EXPECTED[n])
    x,z=at;w,h=sz
    if n.startswith('TB') or n in ('audio','PD'):
        center=(np.asarray(at)+[0.,-.10]).tolist() if n=='PD' else at
        target=section(*EXPECTED[n],'round' if n=='audio' else 'capsule').translate(center)
        assert abs(hole.area()/target.area()-1)<.012 and (target-hole.offset(.045)).area()+(hole-target.offset(.045)).area()<.001,(n,hole.area(),target.area())
    elif n=='HDMI':
        for side in (-1,1):
            assert not contains(hole,x+side*(w/2-.25),z+h/2-.25)
            assert contains(hole,x+side*(w/2-.25),z-h/2+.25)
            assert contains(hole,x+side*(w/2-.78),z+h/2-.78)
    elif n=='RJ':
        assert contains(hole,x,z-5.95) and not contains(hole,x-5.0,z-5.95)
        assert contains(hole,x-5.0,z-4.50) and contains(hole,x+5.0,z+3.50)
    else:
        assert .97*w*h<hole.area()<w*h, (n,hole.area(),w*h)

def assess(p,actual):
    panel=p[s.PANEL];board=actual[BOARD_LABEL];metal=p[s.power.SOCKET];field=field_guard(panel)
    native={**p,**actual};contract=s.mouths();checks={};results={};metals={};bodies={};bad={};poses={}
    face=round(float(bounds(panel)[1,1]),5)
    exposed=panel.rotate([90,0,0]).slice(face-.035);loops=geom.loops(exposed)
    assert len(exposed.to_polygons())==9 and abs(face-s.FACE)<.002,(face,s.FACE)
    for n in NOSES:
        if n=='PD':
            at=np.array([s.PD_X,s.PD_Z]);lip=float(bounds(metal)[1,1]);seat_y=lip;port=metal+p[s.INSERT]
            outer=section(3.25,8.94,'capsule').translate(at);bore=section(2.62,8.44,'capsule').translate(at)
            deep=at+[1.02,0.]
        else:
            dat=contract[n]
            at=np.asarray(dat.get('protruding_collar_center_xz_mm',dat['axis_xz_mm']))
            lip=dat['source_lip_y_mm'];seat_y=dat.get('protruding_collar_tip_y_mm',lip);port=board
            outer=md.CrossSection(dat['outer_loops_xz_mm']);bore=md.CrossSection(dat['inner_loops_xz_mm'])
            deep=np.asarray(dat['front_ray_probes_xz_mm']['open_to_back'])
        x,z=at;mask=at+MASK_DELTA[n];field_pt=FIELD_PROBE[n]
        ray=beam(panel,mask);behind=beam(port,mask);open_board=beam(port,deep);land=beam(panel,field_pt)
        assert len(ray)==2 and abs(ray[0]-face)<.002 and abs(behind[0]-lip)<.004,(n,mask,ray,behind)
        assert not beam(panel,deep) and len(open_board) and lip-open_board[0]>1.2,(n,deep,open_board)
        skin=ray[0]-ray[1];air=ray[1]-behind[0]
        assert abs(skin-s.short_cant(n))<.004,(n,skin,s.short_cant(n))
        assert air+PLAY_FIELD[0,1]>.01,(n,air)
        assert len(land)==2 and abs(land[0]-land[1]-(s.FACE-s.FIELD_IN))<.004,(n,field_pt,land)
        xy=loops[n]*[1.,-1.];hole=md.CrossSection([xy])
        verify_profile(n,hole,xy,at.tolist())
        outside=round((hole-outer).area(),5)
        lower=max(0.,np.min(outer.to_polygons()[0][:,1])-np.min(xy[:,1]))
        if n=='PD':
            assert .02<outside<.10 and .056<lower<.07,(n,outside,lower)
        else:assert outside<.002 and lower<.002,(n,outside,lower)
        assert (outer-hole).area()>.3
        flange=outer-bore
        hidden=(flange-hole).area()/flange.area()
        if n.startswith('TB'):assert hidden>.74,(n,hidden)
        ns=nose(n,at);swept=negative_play_convex(ns,PLAY_FIELD)
        assert (ns-bore).area()<.0002,(n,'modeled entrance',(ns-bore).area())
        assert (swept-hole).area()<.0001,(n,'metal against moving mask',(swept-hole).area())
        xz_clear=geom.gap(swept.to_polygons()[0],xy)
        assert xz_clear>(.10 if n=='PD' else .025),(n,xz_clear)
        # For audio, also verify the protruding Ø5.00 mm collar clears the Ø5.90 hole across full panel play.
        collar_clear=None
        if n=='audio':
            collar_cs=section(dat['protruding_collar_od_mm'],dat['protruding_collar_od_mm'],'round').translate(at)
            swept_collar=negative_play_convex(collar_cs,PLAY_FIELD)
            assert (swept_collar-hole).area()<.0001,('audio collar against moving mask',(swept_collar-hole).area())
            collar_clear=round(geom.gap(swept_collar.to_polygons()[0],xy),4)
            assert collar_clear>.15,('audio collar clearance too small',collar_clear)
        bw,bh,L=SHOULDERS[n];sc=shoulder(n,at)
        req=round(face-seat_y+PLAY_FIELD[1,1],4)
        metals[n]=extrusion(ns,lip-.30,seat_y+L)
        bodies[n]=extrusion(sc,seat_y+L,seat_y+L+25.)
        assert L>req and (sc-hole).area()>1.,(n,L,req)
        # All 8 ports (including audio collar at Y=57.04 behind FACE=57.36) hit the panel if shoulder is at L=0.
        bad[n]=round(vol(extrusion(sc,seat_y,face+.04),panel),5)
        assert bad[n]>.009,(n,bad[n])
        flag='DOCUMENTED mated pair; registered flange datum assumed' if n in ('A1','A2','HDMI') else 'illustrative compatible cable only'
        poses[n]=(at,seat_y)
        row_out={'axis_xz_mm':at.tolist(),'socket_lip_y_mm':round(behind[0],4),'plug_shoulder_seat_y_mm':round(seat_y,4),
            'face_y_mm':face,'signed_face_minus_lip_mm':round(face-lip,4),
            'face_to_lip_with_locked_panel_range_mm':[round(face-lip+d,4) for d in PLAY_FIELD[:,1]],
            'aperture_xz_span_mm':np.round(np.ptp(xy,axis=0),4).tolist(),'aperture_outline_xz_mm':np.round(xy,4).tolist(),'aperture_profile':PORT_PROFILE[n],
            'masked_bezel_probe_xz_mm':np.round(mask,4).tolist(),'mask_back_y_mm':round(ray[1],4),'mask_skin_thickness_mm':round(skin,4),
            'nominal_axial_gap_mask_to_bezel_mm':round(air,4),'mask_to_bezel_axial_gap_conservative_min_mm':round(air+PLAY_FIELD[0,1],4),
            'field_witness_xz_mm':field_pt,'field_thickness_mm':round(land[0]-land[1],4),
            'exposed_entrance_probe_xz_mm':np.round(deep,4).tolist(),'exposed_entrance_board_hit_y_mm':round(open_board[0],4),
            'fraction_of_projected_surround_hidden_nominal':round(hidden,4),'outer_bezel_xz_span_mm':np.round(np.ptp(outer.to_polygons()[0],axis=0),4).tolist(),
            'aperture_center_xz_mm':(at+[0.,-.10]).tolist() if n=='PD' else at.tolist(),
            'aperture_area_outside_nominal_frame_outline_mm2':outside,'aperture_below_nominal_frame_mm':round(float(lower),4),
            'metal_nose_xz_mm':list(NOSES[n][:2]),'nose_to_aperture_XZ_gap_after_rigid_movement_mm':round(xz_clear,4),
            'modeled_shoulder_xz_mm':[bw,bh],'modeled_L_from_socket_seat_mm':L,'shoulder_scenario_status':flag,
            'required_mated_L_for_positive_shoulder_to_fascia_clearance_mm':req,'scenario_shoulder_axial_clearance_mm':round(L-req,4),
            'counterexample_wide_shoulder_at_seat_overlap_mm3':bad[n],'cable_evidence':SOURCES[n]}
        if collar_clear is not None:
            row_out['protruding_collar_od_mm']=dat['protruding_collar_od_mm']
            row_out['protruding_collar_tip_y_mm']=dat['protruding_collar_tip_y_mm']
            row_out['collar_recess_behind_exterior_mm']=round(face-dat['protruding_collar_tip_y_mm'],4)
            row_out['collar_to_aperture_XZ_gap_after_rigid_movement_mm']=collar_clear
        results[n]=row_out
    checks['Centered metal noses cover 0.30 mm of the actual shallow entrance and extend through the entire printed mask']=free('noses',cross(metals,native))
    checks['Noses against all allowed local panel poses']=free('nose / field',cross(metals,{'panel':field}))
    checks['Supported example shoulder stations against all installed bodies and full rigid panel play']=free('shoulders',cross(bodies,{**native,'full panel motion':field}))
    occupied={**{n+' metal':v for n,v in metals.items()},**{n+' body':v for n,v in bodies.items()}}
    checks['Eight distinct cables occupied simultaneously at tabulated shoulder stations']=free('adjacent',((n,a,m,b) for (n,a),(m,b) in itertools.combinations(occupied.items(),2) if n.split()[0]!=m.split()[0]))
    # Photographed board (including USB-A bezels, silver T-bridge, rectangular audio block,
    # protruding Ø5.00 collar, audio shield, HDMI, RJ, shared TB shield) vs full panel motion field!
    checks['Photographed board connectors & bridges against full rigid panel motion field']=free('board / panel field',[('board',board,'panel field',field)])
    # Also cross-check against raw SnazzyLabs SOURCE_20 envelope on USB-A/Audio, HDMI, and RJ zones.
    src20=qa.desk(qa.k.refs()['SOURCE_20'])
    src_zones={
        'SOURCE_20 USB-A + Audio zone':src20^rect([20.,54.0,15.],[62.,60.,40.]),
        'SOURCE_20 HDMI zone':src20^rect([-12.,54.0,15.],[10.,60.,30.]),
        'SOURCE_20 RJ-45 zone':src20^rect([-75.,54.0,14.],[-54.,60.,31.]),
    }
    src_overlaps={k:round(vol(v,panel),6) for k,v in src_zones.items()}
    assert all(ov<.0005 for ov in src_overlaps.values()),('SOURCE_20 zone interference',src_overlaps)
    checks['Raw SOURCE_20 USB-A/Audio, HDMI, and RJ zones vs D2.6 panel']=len(src_overlaps)
    scenarios={}
    for n,L in [('TB1',1.20),('TB2',.85),('PD',.65),('PD',.45),('audio',.55),('audio',.10)]:
        at,seat_y=poses[n];label=f'{n} / L {L:.2f}'
        sc=section(9.1,9.1,'round').translate(at) if n=='audio' else shoulder(n,at)
        body=extrusion(sc,seat_y+L,seat_y+L+20.)
        gap=round(L-results[n]['required_mated_L_for_positive_shoulder_to_fascia_clearance_mm'],4)
        v=round(vol(body,field),6)
        assert (v<.00015 and gap>0) or (v>.00015 and gap<0),(n,L,v,gap)
        scenarios[label]={'setback_from_socket_seat_mm':L,'worst_axial_clearance_mm':gap,'overlap_with_fascia_field_mm3':v,
                          'result':'clear in CAD' if gap>0 else 'blocked by printed mask in this scenario'}
    x=poses['RJ'][0][0];lip=poses['RJ'][1];latch=rj_spring(x,lip)
    latch['outside press tab']=rect([-71.,lip+1.65,11.9],[-58.,78.,15.46])
    latch['outside finger']=rect([-71.,lip+2.35,3.4],[-58.,78.,15.4])
    relieved=bodies['RJ']-rect([-68.,lip+.95,15.31],[-61.3,lip+9.45,20.03])
    desk=rect([-130,-130,-5],[130,130,0]);others={n:b for n,b in bodies.items() if n!='RJ'}
    checks['RJ central latch, narrow nose, independent external press tab and finger with PD inserted and a relieved boot']=free('latch',cross(latch,{**native,**others,'moving mask':field,'relieved boot':relieved,'desk':desk}))
    webs={a+'/'+b:round(geom.gap(loops[a],loops[b]),4) for a,b in itertools.combinations(loops,2)}
    return {'revision':'D2.6','comparisons':sum(checks.values()),'failures':[],'ports':results,'checks':checks,'face_y_mm':face,'facade_through_holes':8,
            'field_motion_conservative_xyz_mm':PLAY_FIELD.tolist(),'minimum_web_mm':min(webs.values()),'webs_face_mm':webs,
            'raw_source20_zone_overlaps_mm3':src_overlaps,
            'large_HDMI_to_TB1_shoulder_gap_mm':qa.k.gap(bodies['HDMI'],bodies['TB1'],2.),'illustrative_short_shoulder_scenarios':scenarios,
            'RJ_release':{'central_spring_width_mm':6.18,'terminal_width_mm':3.38,'finger_width_mm':13.,'relieved_boot_required':True},
            'scope':'Actual thickened 2.60 mm cable-side mask (0.80/0.90/0.40 mm pocket walls), unified USB-A/audio T-pocket, recessed Ø5.00 audio collar passage, and photographed board reference. Positive computed clearance excludes printer/board tolerances. FDM and cold assembly remain physical gates.'}
