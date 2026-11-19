import itertools, math
import numpy as np
import design as s
from check_geometry import *

def assess(p):
    panel,base,lid=p[s.PANEL],p[s.base.BASE],p[s.base.LID]
    fixed={s.base.BASE:base,s.base.BLANK:p[s.base.BLANK],**{n:p[n] for n in (*s.base.BLANK_HARDWARE,*s.base.FEET)}}
    dy=s.D  # inboard lower wedges and upper guide pads remain at D=0.36
    path=[[0.,-.14,36.],[0.,-.14,.80],[0.,0.,0.]];checks={};react={}
    gross=rect([s.X0,s.INNER-.14,s.SILL],[s.X1,s.FACE,s.ZTOP+36.])
    inner=rect([s.X0+3.40,s.FIELD_IN-.14,12.36],[s.X1-3.40,s.FACE,38.9+36.])
    gross+=inner
    windows={str(i):rect([x-w/2-.09,53.98+dy,s.SILL],[x+w/2+.09,55.46+dy,11.79]) for i,(x,w,_) in enumerate(s.WEDGES)}
    elsewhere=base-md.Manifold.batch_boolean(list(windows.values()),md.OpType.Add)
    assert (panel-gross).volume()<.00002
    for n,t in fixed.items():
        v=vol(gross,elsewhere if n==s.base.BASE else t); assert v<.00006,(n,v)
        checks['enclosing swept field and edge slabs / '+n]=v
    for label,region in windows.items():
        wedge=base^region
        for i,(a,b) in enumerate(zip(path,path[1:])):
            tiny=md.Manifold.cube([.000002]*3,True)
            segment=md.Manifold.batch_hull([tiny.translate((-np.array(v)).tolist()) for v in (a,b)])
            v=vol(panel,wedge.minkowski_sum(segment)); assert v<.00007,(label,i,v)
            checks['inverse continuous cam '+label+'/'+str(i+1)]=v
    for x in (-88.32,73.31):
        ys=shell_at_xz(base,x,24.);assert np.isclose(ys,s.G_OUT,atol=.003).any() and min(abs(v - s.G_IN) for v in ys if v<s.G_OUT-.15)<.024,(x,ys)
    contacts=[]
    for x,w,slack in s.WEDGES:
        for z in (9.1,10.20,11.15):
            yy=55.32+dy-.20*(z-8.70)
            assert np.isclose(shell_at_xz(base,x,z),yy,atol=.003).any(),(x,z,yy,shell_at_xz(base,x,z))
            assert np.isclose(shell_at_xz(panel,x,z),yy,atol=.003).any()
        assert np.isclose(shell_at_xz(lid,x,40.05),55.13+dy,atol=.003).any() and np.isclose(shell_at_xz(panel,x,40.05),55.21+dy,atol=.003).any()
        contacts.append({'x_mm':x,'upper_y_gap_mm':.08,'lower_y_gap_seated_mm':0.,'lower_y_gap_at_max_lift_mm':.04})
    for desc,mv,host in [('outward', [0,.10,0],base),('inward at bottom',[0,-.10,0],base),('lift above cap',[0,0,.30],lid),('downward',[0,0,-.10],base),
                             ('left lower locator',[-.19,0,0],base),('right lower locator',[.19,0,0],base)]:
        v=vol(panel.translate(mv),host);assert v>.001,(desc,v);react[desc]=v
    gg=guide_guard(panel)
    for n,v in [('case',base),('lid',lid)]:
        assert vol(gg,v)<.0002,(n,vol(gg,v))
    guide_stations=shell_at_xz(base,-88.32,24.)
    guide_inner=max(v for v in guide_stations if v<s.G_OUT-.15)
    dx=s.WEDGES[1][0]-s.WEDGES[0][0];dz=40.05-9.10
    yaw=math.degrees(math.atan(.08/dx));pitch=math.degrees(math.atan(.08/dz));roll=math.degrees(math.atan(.20/dx))
    assert yaw<.031 and pitch<.150 and roll<.075
    from check_tilt import assess as verify_tilt
    tilt=verify_tilt(p)
    return {'tilt_report':tilt['summary'],'revision':'D2.6','comparisons':len(checks)+6+6+4+2,'failures':[],'waypoints_xyz_mm':path,'continuous_travel':checks,
            'positive_stop_challenge_mm3':react,'locked_translation_bounds_xyz_mm':PLAY.tolist(),'linked_lower_limit':'0 <= Z <= 0.20; -0.20*Z <= Y <= 0; fitted lower X +/-0.075.',
            'upper_and_lower_seats':contacts,'field_motion_conservative_xyz_mm':[[-.125,-.085,-.002],[.125,.002,.204]],
            'rigid_tilt_geometric_bounds_deg':{'yaw':round(yaw,4),'pitch':round(pitch,4),'roll':round(roll,4)},
            'station_probe_z_mm':[9.1,40.05],'side_guide_width_mm':round(s.G_OUT-guide_inner,4),'nominal_groove_cut_width_mm':round(s.G_OUT-s.G_IN,4),'drop_mm':36.,
            'scope':'Rigid small-angle geometry, extreme local field excursions conservatively included in connector and service checks. Print error, flex/warp, force and actual clearance unmeasured.'}
