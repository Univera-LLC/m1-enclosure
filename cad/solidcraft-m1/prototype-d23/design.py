"""D2.3 engineering dimensions in desk millimetres. Front-of-plug clearance is +Y.

SOURCE: Mac grouped shell datums. DOCUMENTED: standard drawing envelope classes.
All parts, locator fits and the unmeasured CMTPD metal ears are design hypotheses.
"""
from pathlib import Path
import sys

OUT=Path(__file__).resolve().parent;CAD=OUT.parent;D22=CAD/'prototype-d22';OLD=CAD/'prototype-d2'
sys.path.insert(0,str(D22))
import build_d22 as prior
sys.path.insert(0,str(OUT))
base,power,d1=prior.base,prior.power,prior.d1
cmd,box,cyl,block=d1.cmd,d1.box,d1.cyl,d1.block
PANEL='D23_SHALLOW_IO_PLATE';FACE,INNER,DOCK=57.95,56.15,56.75
SILL,ZTOP=8.70,41.20;X0,X1=-89.10,74.10
G_IN,G_OUT=55.97,58.12;PD_X=-79.925;POWER_DY=-.60;ROOF=41.50
FILES={**prior.FILES,'panel':[PANEL]};NAMES=sum((list(g) for g in FILES.values()),[])
PLASTICS=[base.BASE,base.LID,PANEL,power.HOLDER,base.BLANK]
COUPONS={'side-guide':([-92.54,47.40,5.95],[-73.50,60.55,43.62]),'lid-stop':([-92.54,47.40,40.95],[-73.50,60.55,46.05])}
MOUTHS={'A1':(49.90,21.85,16.36,9.10,.20),'A2':(32.70,21.85,16.36,9.10,.20),
        'TB1':(-19.05,21.85,13.45,8.60,.90),'TB2':(-33.70,21.85,13.45,8.60,.90),
        'PD':(PD_X,22.05,7.90,14.00,.65)}
# Backs of the four distinct, unmodified SOURCE assemblies. A combined shield
# needs a socket dock on the INSIDE, never an open shared exterior port window.
DOCKS={'USB-A pair + audio':(24.12,58.60,16.65,37.42),'TB dual shield':(-40.05,-12.55,16.62,26.1),
       'HDMI shield':(-10.52,7.52,16.62,27.12),'RJ shield':(-73.18,-56.42,15.70,29.74)}


def soft(n,x0,x1,z0,z1,r,label,ya=INNER-.2,yb=FACE+.2):
    return d1.r.rounded(n,(x0,x1,ya,yb,z0,z1),r,'cut',label)


def prism(host,xz,ya,yb,op,label):
    pts=[[x,-z] for x,z in xz]
    out=[cmd('sketch.create',plane='XZ',offset=ya,name=label+' profile')]
    out.extend(cmd('sketch.line',points=[a,b]) for a,b in zip(pts,pts[1:]+pts[:1]))
    return out+[cmd('sketch.finish'),cmd('solid.extrude',targets=[host],operation=op,distance=yb-ya,name=label)]


def plate():
    ops=d1.b.rounded_xz(PANEL,X0,X1,INNER,FACE,SILL,ZTOP,.70,'new','D2.3 / exterior lies flat on print bed')
    for n,(x,z,w,h,r) in MOUTHS.items():ops+=soft(PANEL,x-w/2,x+w/2,z-h/2,z+h/2,r,n+' / rectangular overmould with softened corners')
    x,z,w,h,clip=-1.525,22.00,17.6,8.2,1.30
    lo=x-w/2;hi=x+w/2;bottom=z-h/2;top=z+h/2
    ops+=prism(PANEL,[(lo,bottom),(hi,bottom),(hi,top-clip),(hi-clip,top),(lo+clip,top),(lo,top-clip)],INNER-.2,FACE+.2,'cut','HDMI / two upper polarizing corners')
    ops+=[cyl(PANEL,'cut',[41.30,INNER-.20,32.32],10.25,FACE-INNER+.40,'Audio / cylindrical flange passage','Y')]
    for lim in [(-72.13,-57.17,18.22,28.05,.65,'RJ45 / contact field'),(-69.24,-60.06,15.85,20.20,.55,'RJ45 / release key toward desk')]:
        ops+=soft(PANEL,*lim)
    for name,(x0,x1,z0,z1) in DOCKS.items():ops+=soft(PANEL,x0,x1,z0,z1,.48,'Inside only / receive '+name,INNER-.20,DOCK)
    ops+=soft(PANEL,-82.10,-75.35,13.18,31.62,.45,'Inside only / clear raised PD shell, board ends and backside solder',INNER-.20,DOCK)
    female=[(-3.835,8.45),(3.835,8.45),(3.835,8.70),(3.075,9.46),(3.075,11.97),(-3.075,11.97),(-3.075,9.46),(-3.835,8.70)]
    return ops+prism(PANEL,[(PD_X+x,z) for x,z in female],INNER-.21,FACE-.79,'cut','Hidden lower locator / flat outside remains intact')


def mount():
    # Same pair of open-top vertical rails, one local locator, flat lid capture.
    # Only the front/back stations of the grooves and their captures change.
    import mount_d22 as old
    ops=old.sidewalls()
    for entry in ops:
        p=entry['params']
        if p.get('name')=='Open vertical panel groove; plain bottom land':
            assert abs(p['corner'][1]-old.G_IN)<.001;p['corner'][1]=G_IN;p['width']=G_OUT-G_IN
        if p.get('name')=='Three-sided entry lead for dropping in the flat panel':
            for edge in p['edges']:
                y=edge[1];edge[1]=G_IN if abs(y-old.G_IN)<.001 else G_OUT if abs(y-old.G_OUT)<.001 else (G_IN+G_OUT)/2
    ops+= [block(base.BASE,'join',-88.23,55.82,8.26,73.23,60.41,SILL,'Continuous support for the panel lower edge'),
           block(base.LID,'join',X0+2.32,55.78,ROOF,X1-2.32,58.29,43.73,'Plain lid edge stops upward travel')]
    positive=[(-3.,8.55),(3.,8.55),(3.,10.70),(2.05,11.65),(-2.05,11.65),(-3.,10.70)]
    return ops+prism(base.BASE,[(PD_X+x,z) for x,z in positive],55.65,56.88,'join','Sill locator / two straight flanks beneath lead-in')


def shared_power():
    # Shift all power datums together, including the pegs integral to the base
    # and retainers integral to the lid. The Mac, its supports and vents stay put.
    ops=power.operations()
    for entry in ops:
        p=entry['params'];feature=entry['command'];assert feature in ('solid.box','solid.cylinder')
        p['corner' if feature=='solid.box' else 'base'][1]+=POWER_DY
    return ops


def metal_retention():
    # The seller's top and bottom photographs show metal hold-down ears. Their
    # projection and free metal height above solder are NOT specified. These
    # explicitly conditional datum solids are part of the commercial shell,
    # not part of the plug path or solder. Never imply the plain box has ears.
    s=power.SOCKET;h=power.HOLDER
    ops=[block(s,'join',-79.25,52.88,17.18,-78.70,54.60,17.80,'ASSUMED exposed lower shell ear / vendor photo; must measure'),
         block(s,'join',-79.25,52.88,26.60,-78.70,54.60,27.22,'ASSUMED exposed upper shell ear / vendor photo; must measure'),
         block(h,'join',-82.78,52.20,8.40,-79.20,55.59,16.94,'Load column beside lower plated ring; keep reserve clear'),
         block(h,'join',-82.78,54.38,8.40,-78.72,55.59,16.94,'Wider foot behind ring reserve, supported continuously from bed'),
         block(h,'join',-81.68,54.78,16.80,-78.74,55.59,17.64,'Lower axial stop outside shell and above any specified solder; never ahead of the port'),
         block(base.LID,'join',-81.62,54.64,27.47,-78.74,55.59,43.88,'Lid-backed outside support behind the PD mouth'),
         block(base.LID,'join',-81.42,54.78,27.07,-78.69,55.59,27.60,'Upper axial stop on the top exposed ear; 0.40 above plain shell')]
    return ops


def groups():return [('Original monocoque, Mac seats and blank',base.operations()),('Shifted coupled commercial module system',shared_power()),
                    ('Shallow exterior and four inside docking rebates',plate()),('Two vertical end rails and blind locator',mount()),
                    ('Two rearward metal-ear withdrawal stops',metal_retention())]
