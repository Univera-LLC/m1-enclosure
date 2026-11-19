"""D2.2 rear closure. Desk mm. The sheet drops from above in two wall-end slots.

The two fixed grooves are inside continuations of the existing rounded
sidewalls. The plain lid has one short flat rim above the sheet: no key,
spring, top groove, panel fastener or stop that must release sideways.
"""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"prototype-d2"))
import base

BASE,LID,PANEL=base.BASE,base.LID,"D22_FLAT_IO_PLATE"
INNER,FACE,SILL,ZTOP=57.35,59.15,8.70,41.20
X0,X1=-89.10,74.10
G_IN,G_OUT=57.17,59.47       # .18 / .32; the assumed PD shell already reaches Y57.09
LEFT_ROOT,RIGHT_ROOT=X0-.32,X1+.32
LEFT_LIP,RIGHT_LIP=X0+2.00,X1-2.00
TOP=base.WALL_TOP
ENTRY=.48                     # local top chamfer; printed by removing material
ROOF=41.50                    # normal flat lid rim, .30 nominal upward freedom
TRAVEL=36.0                   # panel bottom Z44.70, 1.10 above the fixed walls
LOCATOR_X=-79.925             # under the commercial PD shell, not across the full plate
SEATED_X_PLAY=.075            # short local 6.00/6.15 fit; side guides keep their .32 each way
WIDE_FROM_LIFT=1.50           # above this rise the entire .32 mm guide play is available
COUPONS={
    "side-guide":([-92.54,47.40,5.95],[-73.50,60.55,43.62]),
    "lid-stop":([-92.54,47.40,40.95],[-73.50,60.55,46.05]),
}


def sidewalls():
    a=[]
    for left in (True,False):
        side="left" if left else "right"
        name="D22_"+side.upper()+"_WALL_END"
        # Re-use the identical vertical 4.5 mm corner of the stock shell;
        # trim its excess on the inside and forward. No overhanging rail.
        x0,x1=(-92.50,-72.00) if left else (57.,77.50)
        lip,root=(LEFT_LIP,LEFT_ROOT) if left else (RIGHT_LIP,RIGHT_ROOT)
        a+=base.rounded_blank(name,x0,31.0,8.27,x1,60.5,TOP,4.5,
                              side+" rear return on the original case corner radius")
        a.extend([
            base.block(name,"cut",x0-.2,30.8,8.15,x1+.2,54.24,TOP+.2,
                       "Start just inside the existing end of the sidewall"),
            base.block(name,"cut",lip if left else x0-.2,54.0,8.15,x1+.2 if left else lip,60.75,TOP+.2,
                       "End of the short two millimetre front and rear lips"),
            base.block(name,"cut",root if left else lip-.2,G_IN,SILL,lip+.2 if left else root,G_OUT,TOP+.2,
                       "Open vertical panel groove; plain bottom land"),
            base.cmd("solid.chamfer",body=name,
                     edges=[[(root+lip)*.5,G_IN,TOP],[(root+lip)*.5,G_OUT,TOP],[root,(G_IN+G_OUT)*.5,TOP]],
                     distance=ENTRY,name="Three-sided entry lead for dropping in the flat panel"),
            base.combine(BASE,name,"join")])
    return a


def pd_centring_land():
    # A 45-degree crown admits the original broad guide play. Vertical
    # working flanks below it keep the seated X position constant for the
    # full .30 mm lid play. The matching recess is open from below/inboard
    # but leaves the outside face intact. This is not a hook or a latch.
    contour=[(-3.,8.55),(3.,8.55),(3.,10.70),(2.05,11.65),(-2.05,11.65),(-3.,10.70)]
    pts=[[LOCATOR_X+x,-z] for x,z in contour]
    a=[base.cmd("sketch.create",plane="XZ",offset=56.85,name="Local Mac PD centring land section")]
    for p,q in zip(pts,pts[1:]+pts[:1]):
        a.append(base.cmd("sketch.line",points=[p,q]))
    return a+[base.cmd("sketch.finish"),
              base.cmd("solid.extrude",targets=[BASE],operation="join",distance=1.23,
                       name="Lower self-centring land under PD; straight sides below tapered nose")]


def operations():
    return sidewalls()+[
        base.block(BASE,"join",-88.23,55.32,8.26,73.23,60.41,SILL,
                   "One continuous sill supports the sheet; no lower track or sliding rebate"),
        base.block(LID,"join",LEFT_LIP+.32,56.98,ROOF,RIGHT_LIP-.32,59.49,43.73,
                   "Flat face of the lid rim retains the sheet without a groove or key")]+pd_centring_land()
