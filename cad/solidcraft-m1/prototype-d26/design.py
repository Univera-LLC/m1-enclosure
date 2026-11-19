"""D2.6 rear panel & thickened rear wall (+0.60 mm). Desk mm, +Y towards the cable, +Z up.

Based on 2026-11-19 owner print feedback (D2.5 ~2 mm bow at USB-A/audio + paper-thin
0.20 mm membrane vs Apple's ~1.0 mm OEM pocket wall) and 8 owner photographs:
- Thickens the flat rear panel outward by +0.60 mm (FIELD 2.00 -> 2.60 mm, perimeter
  1.80 -> 2.40 mm, FACE 56.76 -> 57.36 mm, REAR 57.81 -> 58.41 mm; case depth
  119.31 -> 119.91 mm; exterior stays 100% flat on bed with zero supports).
- Pocket front walls ("стінка там де паз") become 4x stronger:
  * 0.80 mm at USB-A1, USB-A2, HDMI, RJ-45, and Audio (8x 0.10 or 4x 0.20 mm layers)
  * 0.90 mm at TB1 & TB2 (total TB setback 1.01 mm, matching Apple's ~1.0 mm OEM wall)
  * 0.40 mm at separate PD IN (CMTPD shifted +0.40 mm to PD_FACE=56.80 so short
    0.65 mm USB-C power plugs still seat with positive clearance).
- Unified deep inverted-T pocket (floor Y=56.56 mm) clears real ~15.6x8.55 USB-A bezels,
  recessed silver T-bridge (Y=56.19), ~10.0x6.2 rectangular audio block (Y=56.45), and
  upper audio shield (Z=35.75).
- Audio aperture enlarged to Ø5.90 at (41.30, 32.10) so the protruding Ø5.00 mm collar
  (Y=57.04) sits cleanly 0.32 mm recessed inside the hole (just like OEM Mac mini M1).
- Shallow top entry relief track above audio (floor Y=55.26, leaves 2.10 mm solid wall)
  clears the protruding collar during panel-first vertical board drop.
- Widened/deepened internal blind pockets for HDMI, RJ-45, and shared TB1+TB2 shield.

All printable dimensions below are design assumptions for the cold fit.
"""
import importlib.util
import json
import sys
if not __debug__:
    raise RuntimeError("D2.6 geometry checks require Python without -O or PYTHONOPTIMIZE")
from pathlib import Path

OUT=Path(__file__).resolve().parent;CAD=OUT.parent;D23=CAD/'prototype-d23';OLD=CAD/'prototype-d2'
spec=importlib.util.spec_from_file_location('d23_native_parameters',D23/'design.py')
prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
sys.path.insert(0,str(OUT))
d1,base,power,prior=prev.d1,prev.base,prev.power,prev.prior
cmd,cyl,block,combine=d1.cmd,d1.cyl,d1.block,base.combine
PANEL='D26_PROFILED_IO_PLATE';INSERT='D24_PD_DIELECTRIC_TONGUE'
D=.36          # shift of inboard wedge / upper-guide datums from D2.4
T_ADD=.60      # outward panel & rear-frame thickening (+0.60 mm -> 0.80/0.90 mm pocket walls)
PD_SHIFT=.40   # outward shift of CMTPD saddle & stops so PD wall doubles to 0.40 mm while keeping 0.56 mm setback
FACE=round(56.76+T_ADD,3)          # 57.36
INNER=54.96;FIELD_IN=54.76;COMMON_IN=55.56
REAR=round(57.81+T_ADD,3)          # 58.41 (keeps 1.05 mm outer groove cheek!)
SKIN_IN=FIELD_IN
PD_FACE=round(56.40+PD_SHIFT,3)    # 56.80
SILL=8.70;ZTOP=41.20;ROOF=41.40;X0,X1=-89.10,74.10
G_IN,G_OUT=54.74,FACE              # 54.74..57.36 (2.62 mm groove for 2.40 mm edge -> same 0.22 mm clearance)
DX=.075;LIFT=.20;POCKET_RADIAL=.55
POWER_DY=round(-.69+PD_SHIFT,3)    # -0.29
FEED=2.10;ALIGN=.27
PD_X,PD_Z=-79.925,22.20
EAR_GAP=.10
FILES={**prev.FILES,'panel':[PANEL],'socket_insert':[INSERT]}
PLASTICS=[base.BASE,base.LID,PANEL,power.HOLDER,base.BLANK]
NAMES=sum((list(v) for v in FILES.values()),[])
COUPONS={'side-guide':([-92.54,48.0,5.95],[-73.50,round(57.94+T_ADD,3),43.62]),
         'lid-stop':([-92.54,48.0,40.95],[-73.50,round(57.94+T_ADD,3),46.05])}
WEDGES=[(-85.82,3.14,.075),(69.50,4.20,.45)]
CONTRACT=OUT/'board-study/port-contract.json'
FASCIA_CONTRACT=OUT/'fascia-contract.json'

def mouths():return json.loads(CONTRACT.read_text(encoding='utf8'))['ports']

def capsule(name,x,z,w,h,ya,yb,title):
    """A native box and two exact semicircles; horizontal or vertical in XZ."""
    r=min(w,h)/2;hx=max(0.,w/2-r);hz=max(0.,h/2-r)
    return [block(name,'new',x-(hx or r),ya,z-(hz or r),x+(hx or r),yb,z+(hz or r),title+' straight section'),
            cyl(name,'join',[x-hx,ya,z-hz],2*r,yb-ya,title+' first end','Y'),
            cyl(name,'join',[x+hx,ya,z+hz],2*r,yb-ya,title+' second end','Y')]

def capsule_cut(x,z,w,h,ya,yb,title):
    return capsule('D26_CAPSULE_TOOL',x,z,w,h,ya,yb,title)+[combine(PANEL,'D26_CAPSULE_TOOL','cut')]

def short_cant(n):
    if n.startswith('TB'):return .90
    if n=='PD':return .40
    return .80

def entrances():
    return {
        'A1':{'profile':'rounded_rectangle','width':13.12,'height':5.76,'radius':.52},
        'A2':{'profile':'rounded_rectangle','width':13.12,'height':5.76,'radius':.52},
        'HDMI':{'profile':'upper_chamfers','width':15.04,'height':5.60,'chamfer_xz':1.30},
        'TB1':{'profile':'horizontal_capsule','width':9.10,'height':3.30},
        'TB2':{'profile':'horizontal_capsule','width':9.10,'height':3.30},
        'RJ':{'profile':'rectangle_with_lower_latch_relief','width':13.20,'main_z':[17.96,27.12],'main_radius':.52,
              'latch_width':7.25,'latch_z':[16.75,18.60],'latch_radius':.32},
        # Ø5.90 at (41.30, 32.10) clears the protruding Ø5.00 mm audio collar (Y=57.04),
        # which now sits 0.32 mm recessed inside the 0.80 mm wall (matching OEM Mac mini M1).
        'audio':{'profile':'circle','diameter':5.90,'offset_z_mm':-.10},
        'PD':{'profile':'vertical_capsule','width':3.05,'height':8.87,'offset_z_mm':-.10},
    }

# D2.6 interior blind pockets (desk X0, X1, Z0, Z1, corner R, floor Y):
# Pocket floors stay at Y=56.56 (0.11 mm air ahead of 56.45 bezels) -> 0.80 mm front wall!
DEEP_POCKETS={
    'USB_A_BAR':(24.20,58.40,16.80,27.60,.70,56.56),
    'AUDIO_STEM':(35.30,47.30,26.40,36.60,.70,56.56),
    'HDMI':(-10.45,7.40,16.80,26.30,.70,56.56),
    'RJ':(-73.15,-56.15,15.85,28.85,.70,56.56),
}
GROUP_POCKETS={'TB1+TB2':(-40.35,-12.40,16.90,26.00,.72)}
# Top-entry relief track above audio stem (floor Y=55.26, leaves 2.10 mm solid wall)
# so the protruding Ø5.00 mm audio collar (Y=57.04) clears the top rail during vertical drop.
AUDIO_ENTRY_TRACK=(38.10,44.50,36.00,41.35,.40,55.26)

def facade_contract():
    rows={};mac=mouths()
    for n,prof in entrances().items():
        p=mac.get(n);x,z=p['axis_xz_mm'] if p else (PD_X,PD_Z);lip=p['source_lip_y_mm'] if p else PD_FACE
        out=p['outer_width_height_radius_mm'] if p else [3.25,8.94,1.625]
        bx,bz=p['outer_center_xz_mm'] if p else [PD_X,PD_Z]
        row={'axis_xz_mm':[x,z],'front_center_xz_mm':[x,round(z+prof.get('offset_z_mm',0.),3)],
             'front_profile':prof,'outer_frame_center_xz_mm':[bx,bz],'outer_frame_wh_radius_mm':out,
             'exterior_y_mm':FACE,'registered_lip_y_mm':lip,'lip_behind_exterior_mm':round(FACE-lip,3),
             'local_face_land_thickness_mm':short_cant(n),'interior_pocket_floor_y_mm':round(FACE-short_cant(n),3),
             'air_between_frame_and_land_mm':round(FACE-short_cant(n)-lip,3),
             'individual_frame_rebate_clearance_per_side_mm':POCKET_RADIAL}
        if p and 'protruding_collar_tip_y_mm' in p:
            row['protruding_collar_od_mm']=p['protruding_collar_od_mm']
            row['protruding_collar_tip_y_mm']=p['protruding_collar_tip_y_mm']
            row['collar_recess_behind_exterior_mm']=round(FACE-p['protruding_collar_tip_y_mm'],3)
        rows[n]=row
    return {'revision':'D2.6','units':'desk mm; +Y out to cable; +Z up','ports':rows,
            'main_field_mm':round(FACE-FIELD_IN,3),'rail_edge_mm':round(FACE-INNER,3),
            'outward_thickening_from_d25_mm':T_ADD,'pd_outward_shift_from_d25_mm':PD_SHIFT,
            'inside_deep_pockets_x0_x1_z0_z1_r_floor_mm':DEEP_POCKETS,
            'inside_group_pockets_x0_x1_z0_z1_r_mm':GROUP_POCKETS,'inside_group_pocket_floor_y_mm':COMMON_IN,
            'audio_collar_vertical_entry_track_x0_x1_z0_z1_r_floor_mm':AUDIO_ENTRY_TRACK,
            'print':'Flat exterior on bed, zero supports; 0.10 mm layers (26 layers: 8 layers = 0.80 mm at ordinary ports, 9 layers = 0.90 mm at TB, 4 layers = 0.40 mm at PD) or 0.20 mm standard profile.',
            'statuses':{'SOURCE':'Apple port registration from retained SnazzyLabs board as preserved in nearby port-contract.json.',
                        'DOCUMENTED':'2026-11-19 owner macro, side-profile, 2.54 mm PCB ruler, underside, marked D2.5 orange print, and Apple OEM ~4 mm / ~1 mm fascia thickness comparison photos.',
                        'ASSUMED':'All numerical fascia dimensions, real mouth-to-SOURCE alignment, CMTPD and printer tolerances.',
                        'MEASURED':'Owner reported ~2 mm bow on D2.5 print and ~4 mm overall / ~1 mm pocket wall on Apple OEM fascia; no caliper contact measurements on D2.6 print yet.'}}

def yz(host,pts,xa,xb,op,title):
    # SolidCraft 0.44.1 requires distinct sketch names at the two wedge stations.
    title = f"{title} (X={xa:g} mm)"
    a=[cmd('sketch.create',plane='YZ',offset=xa,name=title+' section')]
    a.extend(cmd('sketch.line',points=[p,q]) for p,q in zip(pts,pts[1:]+pts[:1]))
    return a+[cmd('sketch.finish'),cmd('solid.extrude',operation=op,targets=[host],distance=xb-xa,name=title)]

def round_cut(host,x,z,w,h,r,y0,y1,title):
    return d1.r.rounded(host,(x-w/2,x+w/2,y0,y1,z-h/2,z+h/2),r,'cut',title)

def panel():
    a=d1.b.rounded_xz(PANEL,X0,X1,INNER,FACE,SILL,ZTOP,.70,'new','One flat exterior; 2.40 mm locating perimeter')
    a+=[block(PANEL,'join',X0+3.40,FIELD_IN,12.36,X1-3.40,INNER+.04,38.9,'2.60 mm field; full supporting ribs remain between deep pockets')]
    y0=FIELD_IN-.15;y1=FACE+.15
    for n,row in facade_contract()['ports'].items():
        x,z=row['front_center_xz_mm'];q=row['front_profile'];kind=q['profile'];w=q.get('width');h=q.get('height')
        if kind=='circle':a+=[cyl(PANEL,'cut',[x,y0,z],q['diameter'],y1-y0,'Audio round collar passage through outer face','Y')]
        elif 'capsule' in kind:a+=capsule_cut(x,z,w,h,y0,y1,n+' metal-tip capsule through outer face')
        elif kind=='upper_chamfers':
            c=q['chamfer_xz'];xl=x-w/2;xh=x+w/2;zl=z-h/2;zh=z+h/2
            a+=prev.prism(PANEL,[(xl,zl),(xh,zl),(xh,zh-c),(xh-c,zh),(xl+c,zh),(xl,zh-c)],y0,y1,'cut','HDMI two upper polarizing corners')
        elif kind=='rectangle_with_lower_latch_relief':
            for label,r,width,(za,zb) in [('main',q['main_radius'],w,q['main_z']),('latch',q['latch_radius'],q['latch_width'],q['latch_z'])]:
                a+=round_cut(PANEL,x,(za+zb)/2,width,zb-za,r,y0,y1,'8P8C '+label+' clearance towards desk')
        else:a+=round_cut(PANEL,x,z,w,h,q['radius'],y0,y1,n+' Type-A nose through outer face')
        bx,bz=row['outer_frame_center_xz_mm'];ow,oh,orr=row['outer_frame_wh_radius_mm'];stop=row['interior_pocket_floor_y_mm'];e=POCKET_RADIAL
        if n=='PD':a+=capsule_cut(bx,bz,ow+2*e,oh+2*e,y0,stop,'Commercial CMTPD blind metal-body seat; 0.40 mm outer wall')
        elif n.startswith('TB'):a+=round_cut(PANEL,bx,bz,ow+2*e,oh+2*e,orr+e,y0,stop,n+' blind seat for wide flange; 0.90 mm outer wall')
    for title,(xa,xb,za,zb,r,stop) in DEEP_POCKETS.items():
        a+=round_cut(PANEL,(xa+xb)/2,(za+zb)/2,xb-xa,zb-za,r,y0,stop,'D2.6 deep blind seat '+title+'; 0.80 mm outer wall')
    for title,(xa,xb,za,zb,r) in GROUP_POCKETS.items():
        a+=round_cut(PANEL,(xa+xb)/2,(za+zb)/2,xb-xa,zb-za,r,y0,COMMON_IN,'Inside shared '+title+' rear shield relief; 1.80 mm outer wall')
    xa,xb,za,zb,r,stop=AUDIO_ENTRY_TRACK
    a+=round_cut(PANEL,(xa+xb)/2,(za+zb)/2,xb-xa,zb-za,r,y0,stop,'Audio collar vertical board-drop entry relief; 2.10 mm outer wall')
    # PD reliefs track PD_SHIFT (+0.40 mm) while outer walls become +0.20 mm thicker than D2.5!
    a+=round_cut(PANEL,-76.96,22.24,3.26,18.08,.26,y0,round(55.95+PD_SHIFT,3),'Only FR4/solder relief; 1.01 mm outer wall')
    a+=round_cut(PANEL,-80.69,13.03,4.86,10.10,.32,y0,round(55.87+PD_SHIFT,3),'PD saddle footprint; 1.09 mm outer wall')
    a+=round_cut(PANEL,-79.17,34.20,1.55,15.32,.20,y0,round(55.55+PD_SHIFT,3),'Upper metal-ear service track, open to top; 1.41 mm outer wall')
    # Shallow vertical relief for shifted PD inboard root & vertical sled-drop nose (Y=54.66..54.87); leaves 2.16 mm solid outer wall.
    a+=round_cut(PANEL,PD_X,33.075,3.75,16.55,.20,y0,55.20,'PD inboard root & nose vertical entry channel; 2.16 mm outer wall')
    # Inboard lower cams & upper guide seats stay at D=0.36 (unchanged!).
    for x,w,clear in WEDGES:
        path=[[53.94,8.48],[55.364,8.48],[54.708,11.76],[53.94,11.76]]
        a+=yz(PANEL,[[y+D,z] for y,z in path],x-w/2-clear,x+w/2+clear,'cut','Hidden lower cam pocket, flat exterior untouched')
        a.append(block(PANEL,'cut',x-1.42,53.94+D,38.64,x+1.42,55.21+D,41.35,'Open upper guide seat; only two small faces to fit on coupon'))
    return a

def shift_y(ops,dy):
    for op in ops:
        p=op['params'];pt=p['corner'] if op['command']=='solid.box' else p['base']
        pt[1]+=dy
    return ops

def shared_power():return shift_y(power.operations(),POWER_DY)

def peg_and_register():
    a=[]
    stations=[(x,y,14.,1.90,1.87,'Mac') for x,y in base.PCB_AXES]
    stations += [(x,y+POWER_DY,8.40,2.40,2.39,'saddle') for x,y in power.PEGS]
    for i,(x,y,z,r,cr,tag) in enumerate(stations):
        cutter='D24_APPROACH_TOOL_'+str(i)
        a.extend([block(cutter,'new',x-r-.08,y-r-.08,z+.20,x+r+.08,y+r+.08,z+(1.0 if tag=='Mac' else 2.72),'Remove only material above full seated register'),
                  cyl(cutter,'cut',[x,y-FEED,z+.14],2*cr,3.0,'Keep tall supported forward sector for horizontal feed'),
                  combine(base.BASE,cutter,'cut')])
    return a

def trim_round():
    a=[]
    for n in (base.BASE,base.LID):
        a.append(block(n,'cut',-94,REAR,5.,79.,61.,47.,'Trim obsolete deep rear shelf; face is 1.05 mm inside rear corner'))
        for i,(x,xa,xb) in enumerate([(-88.,-93.0,-88.),(73.,73.,78.)]):
            tool='D24_REAR_CORNER'
            a.extend([block(tool,'new',xa,REAR-4.5,5.,xb,REAR+.1,47.,'Matching rear corner continuation'),
                      cyl(tool,'cut',[x,REAR-4.5,4.9],9.0,42.3,'Retain existing 4.5 mm plan corner radius'),combine(n,tool,'cut')])
    return a

def mount():
    import mount_d22 as old
    a=old.sidewalls()
    for op in a:
        p=op['params'];n=p.get('name','')
        if n=='Open vertical panel groove; plain bottom land':p['corner'][1]=G_IN;p['width']=G_OUT-G_IN
        if n=='Three-sided entry lead for dropping in the flat panel':
            for e in p['edges']:
                y=e[1];e[1]=G_IN if abs(y-old.G_IN)<.001 else G_OUT if abs(y-old.G_OUT)<.001 else (G_IN+G_OUT)/2
    a+=[block(base.BASE,'join',-88.23,55.88+D,8.25,73.23,REAR,SILL,'Continuous hard lower ledge even in the PD bay'),
        block(base.BASE,'join',-73.9,54.23+D,8.25,73.23,REAR,SILL,'Full lower shelf carrying both anti-fore/aft cams'),
        block(base.LID,'join',X0+2.36,54.53+D,ROOF,X1-2.36,REAR,43.73,'0.20 mm above seated panel')]
    for x,w,clear in WEDGES:
        a.append(block(base.BASE,'join',x-w/2-.08,54.04+D,8.25,x+w/2+.08,56.02+D,SILL,'Support lower cam all the way to bed'))
        a+=yz(base.BASE,[[y+D,z] for y,z in [[54.08,8.57],[55.346,8.57],[54.72,11.70],[54.08,11.70]]],x-w/2,x+w/2,'join','Inboard 1:5 cam bears against solid outboard end datums')
        a+=yz(base.LID,[[y+D,z] for y,z in [[54.48,39.05],[54.67,39.05],[55.13,39.51],[55.13,43.84],[54.48,43.84]]],
              x-1.10,x+1.10,'join','Chamfered inward top pad bounds pitch; 0.08 horizontal clearance and open vertical entry')
    return a+trim_round()

def power_nose():
    s=power.SOCKET;dy=PD_SHIFT
    a=[block(s,'cut',-82.2,53.84+dy,16.50,-78.0,57.2+dy,27.76,'Replace simplified solid front with hollow metal receptacle')]
    a+=capsule('D24_PD_TUBE',PD_X,PD_Z,3.25,8.94,53.80+dy,PD_FACE,'Assumed commercial metal tube at D2.6 physical station')
    a+=[combine(s,'D24_PD_TUBE','join')]
    a+=capsule('D24_PD_BORE',PD_X,PD_Z,2.62,8.44,54.04+dy,PD_FACE+.08,'Open receptacle entrance')
    a+=[combine(s,'D24_PD_BORE','cut')]
    a+=capsule(INSERT,PD_X,PD_Z,.66,6.55,54.04+dy,PD_FACE-.60,'Insulating tongue rooted in actual blind metal pocket')
    return a

def retain():
    before=prev.metal_retention();dy=PD_SHIFT
    a=shift_y([op for op in before if op['params']['name'] not in ('Lid-backed outside support behind the PD mouth','Upper axial stop on the top exposed ear; 0.40 above plain shell')],POWER_DY-prev.POWER_DY)
    lower,=[op['params'] for op in a if op['params']['name'].startswith('Lower axial stop outside shell')]
    lower['corner'][1]-=.18-EAR_GAP;lower['width']+=.18-EAR_GAP
    # Upper load column stays inboard of FIELD_IN (Y_max=54.56) while bridge & inboard root track PD_SHIFT outside plated ring (X<-79.00).
    a.append(block(base.LID,'join',-81.63,53.42+dy,27.62,-79.22,54.56,43.87,'Upper load column inboard of field and beside plated ring; full wall above socket'))
    a.append(block(base.LID,'join',-81.40,52.79+dy,31.65,-79.62,54.56,43.70,'Tie long upper ear column to broad pre-existing shell keeper, wholly above ring reserve'))
    a.append(block(base.LID,'join',-80.70,54.26,27.66,-79.22,54.76,30.43,'Bridge from upper load column to shifted inboard root; wholly left of plated ring (X<-79.00)'))
    a.append(block(base.LID,'join',-80.70,54.26+dy,27.66,-78.69,54.47+dy,30.43,'Inboard root behind plated ring, passes vertically through shallow panel channel'))
    a+=yz(base.LID,[[54.21+dy,27.65],[55.23+dy,27.65],[55.23+dy,28.46],[54.30+dy,30.42],[54.21+dy,30.42]],-79.65,-78.69,'join','Bed-supported taper for vertically removable narrow ear reaction')
    a.append(block(base.LID,'join',-79.65,54.51+dy+EAR_GAP,27.07,-78.69,55.23+dy,27.84,'Upper metal-ear stop only; 0.40 mm above closed smooth shell'))
    for ya,yb in [(42.52+dy,43.53+dy),(48.65+dy,49.66+dy)]:
        a.append(block(base.LID,'join',-84.92,ya,25.55,-83.05,yb,43.83,'Metal load via saddle pillar to case; no laminate or solder bearing'))
    a.append(block(base.LID,'join',-84.92,42.52+dy,27.65,-83.05,49.66+dy,43.83,'One broad axial fork over unloaded saddle; only short locating teeth project'))
    return a

def shared():return [('Inherited structural chassis, mounting axes and ventilation',base.operations()),('Unified commercial power position (+0.40 mm for thicker rear wall)',shared_power())]
def groups():return shared()+[('Eight profiled throat openings, 0.80/0.90/0.40 mm walls, unified inverted-T USB-A/audio pocket and widened reliefs',panel()),('Two positively located lower wedge seats and +0.60 mm deepened rear guide datums',mount()),('Full lower registers with taller approach sectors',peg_and_register()),('Hollow commercial PD mouth and tongue at +0.40 mm station',power_nose()),('Independent metal / saddle reactions',retain())]
