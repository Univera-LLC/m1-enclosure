"""Actual loaded sled travel, metal positive stops, copper/solder reserves and hidden PD pocket."""
import itertools
import numpy as np
import design as s
from check_geometry import *

def assess(p,actual,rf):
    q=s.power; base,lid,sled,plate,metal,fr4=[p[n] for n in (s.base.BASE,s.base.LID,q.HOLDER,s.PANEL,q.SOCKET,q.PD)]
    dy=s.PD_SHIFT
    parts={n:p[n] for n in (q.HOLDER,*q.MODULES,s.INSERT)};electronics={n:v for n,v in parts.items() if n!=q.HOLDER}
    fixed={n:v for n,v in {**p,**actual,**rf}.items() if n not in parts and n not in (s.base.LID,*s.base.LID_HARDWARE)}
    fixed['Panel field including upper angular reserve']=field_guard(plate)
    poses=[[0.,-s.FEED,49.],[0.,-s.FEED,s.ALIGN],[0.,0.,s.ALIGN],[0.,0.,0.]]
    travel_checks=travel(poses,parts,fixed);checks={};react={}
    checks['loaded sled continuous service']=sum(map(len,travel_checks.values()))
    checks['no static contact: power items / chassis, fascia, lid']=free('power installed',cross(electronics,{'base':base,'lid':lid,'saddle':sled,'fascia field':fixed['Panel field including upper angular reserve']}))
    def hit(name,mover,target,mv,minv=.001):
        v=vol(mover.translate(mv),target);assert v>minv,(name,v)
        react[name]=v;return v
    hit('insertion load: metal rear face / plastic shoe',metal,sled,[0,-.30,0],.10)
    hit('outside side metal shoe',metal,sled,[-.42,0,0])
    hit('lower metal shell support',metal,sled,[0,0,-.36])
    hit('upper metal stop',metal,lid,[0,0,.47])
    ref=metal^rect([-79.251,52.77+dy,17.0],[-78.699,54.52+dy,17.729])
    ref+=metal^rect([-79.251,52.77+dy,26.671],[-78.699,54.52+dy,27.30])
    assert len([a for a in ref.decompose() if a.volume()>.001])==2
    ear={}
    for label,obj,lo,hi in [('upper',lid,26.90,27.23),('lower',sled,17.16,17.69)]:
        guard=obj^rect([-81.72,54.58+dy,lo],[-78.31,55.51+dy,hi])
        gap=round(float(bounds(guard)[0,1]-bounds(ref)[1,1]),5)
        assert abs(gap-.10)<.001 and guard.volume()>.050 and vol(ref.translate([0,.095,0]),guard)<.00002,(label,gap)
        bearing=hit('withdrawal on assumed '+label+' metal ear',ref,guard,[0,.22,0],.009)
        assert vol((metal-ref).translate([0,.22,0]),guard)<.00003
        ear[label]=round(bearing/.12,4)
    population={n:p[n] for n in (*q.CHIPS,*q.BACKS)}
    checks['solder and FR4 are still clear when metal ears first restrain withdrawal despite full panel field motion']=free('first withdrawal',cross({n:v.translate([0,.10,0]) for n,v in {q.PD:fr4,**population}.items()},
                    {'sled':sled,'lid':lid,'fascia':fixed['Panel field including upper angular reserve']}))
    onset={n:qa.k.gap(p[n].translate([0,.10,0]),fixed['Panel field including upper angular reserve'],1.0) for n in (q.PD,q.BACKS[0])}
    assert min(onset.values())>.02,onset
    checks['PCB and parts remain free on first metal insertion reaction']=free('insertion',cross({n:v.translate([0,-.30,0]) for n,v in {q.PD:fr4,**population}.items()},{'sled':sled,'lid':lid,'fascia':plate}))
    for movement in [-.32,.32]:
        clip=rect([-85.3,42.35+dy,25.56],[-82.98,49.80+dy,27.11])
        hit('loaded sled axial reaction in plastic / '+str(movement),sled^clip,lid^clip,[0,movement,0],.12)
    hit('existing broad plastics restrain sled lift before laminate loading',sled,lid,[0,0,.36],.20)
    checks['electronic parts remain free at first vertical keeper']=free('first vertical',cross({n:v.translate([0,0,.32]) for n,v in electronics.items()},{'lid':lid}))
    ring={label:rect([-79.,50.80+s.POWER_DY,zlow],[-76.,54.90+s.POWER_DY,zhigh]) for label,zlow,zhigh in [('lower plated ring reserve',13.50,15.55),('upper plated ring reserve',28.85,30.90)]}
    checks['photo-derived plated-ring exclusions']=free('rings',cross(ring,{'sled':sled,'lid':lid,'panel':plate}))
    pegs=[]
    for x,y in q.PEGS:
        y+=s.POWER_DY
        one=base^rect([x-2.55,y-2.55,8.401],[x+2.55,y+2.55,11.02]);tall=one^rect([x-2.55,y-2.55,8.61],[x+2.55,y+2.55,11.02])
        assert abs(bounds(one)[1,2]-10.95)<.005 and tall.volume()>6.
        pegs.append({'axis_xy_mm':[x,y],'full_360_deg_height_mm':.20,'high_sector_height_mm':2.55,'tall_sector_mm3':round(tall.volume(),3)})
    # Behind the separate power socket, probe actual thickened walls (all +0.20..+0.60 mm thicker than D2.5!).
    representatives={'FR4 and backside solder':([-76.12,22.20],1.01),'floor-supported saddle foot':([-80.65,13.15],1.09),
                     'narrow upper ear service track':([-79.20,36.40],1.41),'unrelieved beside PD':([-82.55,22.20],2.60)}
    witnesses={}
    for name,(xz,want) in representatives.items():
        y=shell_at_xz(plate,*xz);assert len(y)==2 and abs(y[1]-y[0]-want)<.006,(name,xz,y)
        witnesses[name]={'probe_xz_mm':xz,'surface_y_mm':y,'wall_thickness_mm':round(y[1]-y[0],4)}
    leads={}
    for i,z in enumerate([19.8,24.3]):leads[str(i)]=qa.wire([[-83.95,16.1,z],[-84.2,13.,z],[-84.2,9.2,z],[-83.8,6.6,z]],1.15).translate([0,s.POWER_DY,0])
    for i,(x,y,z) in enumerate([(-84.15,-21.9,17.15),(-81.55,-22.98,17.45)]):
        leads[str(i+2)]=qa.wire([[x,y,z],[x,-25.8,z],[x,-27.6,z],[x,-30.,16.98],[x,-35.2,16.98]],1.06).translate([0,s.POWER_DY,0])
    checks['Four insulated leads in corridors vs all actual installed items']=free('leads',cross(leads,{**p,**actual,**rf}))
    checks['Insulated leads are separate']=free('wires',((a,v,b,w) for (a,v),(b,w) in itertools.combinations(leads.items(),2)))
    floor=base.slice(7.20);bed=sled.slice(8.41);floor_area=free_area=0.
    for x in [-86.8,-81.3,-75.8]:
        window=md.CrossSection.square([3.2,50]).translate([x-1.6,-18.]);open_area=window-floor
        floor_area+=open_area.area();free_area+=(open_area-bed).area()
    assert free_area/floor_area>.66
    return {'revision':'D2.6','failures':[],'comparisons':sum(checks.values())+len(react)+7,'checks':checks,'waypoints_xyz_mm':poses,
            'continuous_slab_covers':travel_checks,'floor_pegs':pegs,'printed_power_parts':1,'hardware':'No power screws. Release both leads and disconnect before removal.',
            'challenge_overlaps_mm3':react,'metal_ear_conditional':{'exposed_contact_area_mm2':ear,'nominal_gap_mm':gap,'physical_status':'Only tab presence is visible; accessible metal height above solder is ASSUMED. No positive withdrawal reaction for a smooth tabless shell.'},
            'local_PD_reliefs':{'exported_panel_wall_witnesses':witnesses,'clearance_at_first_ear_reaction_full_panel_field_mm':onset,
                   'load_path':'Insertion: metal back into shoe. Withdrawal: two conditional metal ears. Both directions also meet a broad plastic sled pillar/closed-lid stops. The blind relief is a cosmetic clearance and is not designed as the cable thrust stop.'},
            'installed_power_floor':{'nominal_open_mm2':round(floor_area,3),'open_after_fit_mm2':round(free_area,3),'open_fraction':round(free_area/floor_area,4)},
            'service':'With lid open, hold both upper corners of the installed panel on their rear datum. Sled enters level with both modules installed from outside, 2.10 mm forward; feed at Z+0.27, seat and fit lid; reverse to remove. Mac and screws can stay.'}
