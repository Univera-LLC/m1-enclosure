"""D2 FDM monocoque and opening lid, drawn directly in D1 desk coordinates (mm).

The two board datums are the Apple housing-mount rings in SOURCE 20, not
SnazzyLabs' three tray posts or the four screw holes at the heatsink corners.
The metal assembly and all positions/ground contacts still need a cold fit.
"""
from pathlib import Path
import math
import sys

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / "prototype-d1"))
import build_d1 as d

box, cyl, cmd, block = d.box, d.cyl, d.cmd, d.block
BASE, LID, BLANK = "D2_MONO_BASE", "D2_TOP_COVER", "D2_FRONT_BLANK"
LID_HARDWARE = [f"D2_LID_FIXING_{i}" for i in range(1, 5)]
PCB_HARDWARE = [f"D2_BOARD_FIXING_{i}" for i in range(1, 3)]
BLANK_HARDWARE = ["D2_BLANK_FIXING_LOW", "D2_BLANK_FIXING_HIGH"]
FEET = [f"D2_ADHESIVE_FOOT_{i}" for i in range(1, 5)]
FILES = {"base": [BASE], "lid": [LID], "blank": [BLANK], "feet": FEET,
         "lid_screws": LID_HARDWARE, "pcb_screws": PCB_HARDWARE,
         "blank_screws": BLANK_HARDWARE}

EXTENTS_XY = (-92.5, 77.5, -61.5, 60.5)
BED_Z, FLOOR_TOP, WALL_TOP, LID_TOP = 6.0, 8.4, 43.6, 46.0
PCB_AXES = [(-52.00, -34.35), (47.95, -34.35)]
PCB_SEAT, PCB_BEARING, PCB_BORE = 14.0, 17.4, 4.40  # SOURCE model, not physical
PCB_LOCATOR_OD = 3.80
LID_AXES = [(-62.0, -55.0), (62.0, -55.0), (-87.65, 51.9), (72.50, 51.9)]
FOOT_AXES = [(62.0, -45.0), (-75.0, -44.0), (52.0, 47.0), (-72.0, 46.0)]
ANTI_TIP = [(-55.0, 28.85), (22.0, 28.85)]
MAIN_LANES = [-x for x in d.b.AX]
POWER_LANES = [-x for x in d.b.PD_X]
FLOOR_POWER_SPANS = {
    -75.8: [(-16.0, -12.25), (-5.75, 3.2), (6.0, 30.0)],
    -81.3: [(-16.0, -12.25), (-5.75, 3.2), (6.0, 30.0)],
    -86.8: list(d.b.PD_SPANS),
}
# Preserve a solid lid directly over the PD retainer vanes. The exterior
# (x=-86.8) bank keeps the full original power-bay convection route.
LID_POWER_SPANS = {
    -75.8: [(-11.4, -1.55), (6.0, 18.0), (25.5, 30.0)],
    -81.3: [(-11.4, -1.55), (6.0, 18.0), (25.5, 30.0)],
    -86.8: list(d.b.PD_SPANS),
}


def combine(host, tool, op):
    return cmd("solid.combine", target=host, tools=[tool], operation=op, keep_tools=False)


def rounded_blank(n, x0, y0, z0, x1, y1, z1, radius, title):
    return d.v.roundbox(n, [x0,y0,z0], [x1-x0,y1-y0,z1-z0], radius, title)


def rounded_slots(n, plan, z, end, title):
    # All profiles in a bank are disjoint and pass through the same skin.
    a = [cmd("sketch.create", plane="XY", offset=z, name=title+" profiles")]
    for x, lo, hi, w in plan:
        a.append(cmd("sketch.slot.overall", p0=[x,lo], p1=[x,hi], width=w))
    return a + [cmd("sketch.finish"), cmd("solid.extrude", operation="cut",
                targets=[n], distance=end-z, name=title)]


def polygon_prism(host, points, z0, z1, op, label):
    a = [cmd("sketch.create", plane="XY", offset=z0, name=label+" section")]
    for p,q in zip(points, points[1:]+points[:1]):
        a.append(cmd("sketch.line", points=[p,q]))
    return a + [cmd("sketch.finish"), cmd("solid.extrude", operation=op, targets=[host],
                distance=z1-z0, name=label)]


def tab_guide(x,y,angle,length,width,seat,label):
    # U-guide with open ends, aligned with the SOURCE folded tab; no snap fit,
    # metal fastener, ground contact, or contact with the board is implied.
    rad = math.radians(angle)
    ex,ey = (math.cos(rad),math.sin(rad)), (-math.sin(rad),math.cos(rad))
    def corners(l,w):
        return [[x+i*l/2*ex[0]+j*w/2*ey[0], y+i*l/2*ex[1]+j*w/2*ey[1]]
                for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
    h = seat+1.35
    return (polygon_prism(BASE,corners(length,width),FLOOR_TOP-.10,h,"join",label+" block")+
            polygon_prism(BASE,corners(length+.50,1.48),seat,h+.15,"cut",label+" loose slot"))


def shell():
    a = rounded_blank(BASE,-92.5,-61.5,BED_Z,77.5,60.5,WALL_TOP,4.5,
                      "Single upright FDM blank: floor and fixed walls")
    a += rounded_blank("D2_CAVITY",-90.1,-59.1,FLOOR_TOP,75.1,64.1,44.2,2.1,
                       "2.4 mm skin; inner front corner radius")
    a += [combine(BASE,"D2_CAVITY","cut"),
          block(BASE,"cut",-94.,54.5,FLOOR_TOP,79.,62.,44.2,
                "Open rear for horizontal service cassette and fixed rails")]
    a += rounded_blank(LID,-92.5,-61.5,WALL_TOP,77.5,60.5,LID_TOP,4.5,
                       "Independent removable top; flat printed face")
    a += [cmd("solid.chamfer",body=LID,edges=[[0.,-61.5,LID_TOP]],distance=.45,
              name="Soft outside lid rim; broad print face stays planar")]
    lower = [(x,*d.b.IN_SPAN,d.b.IN_W) for x in MAIN_LANES]
    lower += [(x,lo,hi,d.b.PD_W) for x in POWER_LANES for lo,hi in FLOOR_POWER_SPANS[x]]
    upper = [(x,lo,hi,d.b.VENT_W) for x in MAIN_LANES for lo,hi in d.b.ROOF_SPANS]
    upper += [(x,lo,hi,d.b.PD_W) for x in POWER_LANES for lo,hi in LID_POWER_SPANS[x]]
    a += rounded_slots(BASE,lower,BED_Z-.12,FLOOR_TOP+.12,"Open floor intake banks")
    a += rounded_slots(LID,upper,WALL_TOP-.12,LID_TOP+.12,"Open lid exhaust banks")
    for i in range(0,10,2):
        x0,x1 = sorted((MAIN_LANES[i],MAIN_LANES[i+1]))
        a += d.b.rounded_xz("D2_NOSE_CUT",x0-2.38,x1+2.38,-61.7,-58.8,9.10,13.45,
                            1.55,"new","Low front intake with bridgeable roof")
        a.append(combine(BASE,"D2_NOSE_CUT","cut"))
    # Rubber is a separate, nonprinted accessory. No molded feet lifting the
    # large floor off the build plate, no screws passing through the bottom.
    for (x,y),n in zip(FOOT_AXES,FEET):
        a.extend([cyl(n,"new",[x,y,0.0],12.0,BED_Z,"Adhesive elastomer foot on planar underside; no bridged pockets"),
                  d.c.fil(n,[[x+6,y,0.0]],.50)])
    return a


def board_seats():
    a = []
    for (x,y),n in zip(PCB_AXES,PCB_HARDWARE):
        a.extend([cyl(BASE,"join",[x,y,FLOOR_TOP-.12],8.6,2.0,"Wide integral boss foot"),
                  cyl(BASE,"join",[x,y,FLOOR_TOP+1.70],7.0,PCB_SEAT-FLOOR_TOP-1.70,
                      "Direct dielectric annular land at SOURCE underside Z14"),
                  cyl(BASE,"join",[x,y,PCB_SEAT-.08],PCB_LOCATOR_OD,.78,
                      "Short registering shoulder inside SOURCE 4.4 mm bore"),
                  cyl(BASE,"cut",[x,y,8.87],2.60,6.01,"Blind top pilot; size to test on printed plastic"),
                  cyl(n,"new",[x,y,9.4],2.42,5.36,"M3 x 8 scenario; thread MINOR diameter gauge"),
                  cyl(n,"join",[x,y,14.72],3.0,2.68,"Clearance shank above plastic register"),
                  cyl(n,"join",[x,y,PCB_BEARING],6.0,1.80,
                      "Broad head bears on SOURCE ring, independent of heatsink screws"),
                  cyl(n,"cut",[x,y,18.35],2.20,1.0,"Driver socket gauge, not torque specification")])
    # Both actual mounts lie on the front edge; these stops catch deflection
    # under rear port loading. Nominal 0.30 air to the rear SOURCE ear. Open
    # centre well is deliberately larger than its SOURCE hole. No fixing here.
    for x,y in ANTI_TIP:
        a += [cyl(BASE,"join",[x,y,FLOOR_TOP-.1],6.7,16.10-FLOOR_TOP+.1,
                  "Unthreaded rear anti-tip support; 0.30 mm nominal air"),
              cyl(BASE,"cut",[x,y,10.6],4.65,5.65,"Relieve all central rear-ear hardware")]
    return a


def lid_attachment():
    a=[]
    for i,((x,y),n) in enumerate(zip(LID_AXES,LID_HARDWARE)):
        if i<2:
            a.append(block(BASE,"join",x-3.5,-59.32,8.31,x+3.5,-51.55,43.6,
                     "Front lid socket merged into fixed front wall"))
        elif i==2:
            a.append(block(BASE,"join",-90.55,y-2.50,8.31,-85.05,y+2.50,43.6,
                     "Rear lid socket on outside power wall"))
        else:
            a.append(block(BASE,"join",69.95,y-2.50,8.31,75.45,y+2.50,43.6,
                     "Narrow right side wall socket clears folded SOURCE antenna"))
        a.extend([cyl(BASE,"cut",[x,y,34.30],2.60,9.48,"M3 plastic-forming pilot in fixed wall"),
                  cyl(LID,"cut",[x,y,43.45],3.35,2.75,"Independent top screw clearance"),
                  cmd("solid.chamfer",body=LID,edges=[[x+1.675,y,LID_TOP]],distance=1.35,
                      name="90 degree countersink for flush removable lid screw"),
                  cyl(n,"new",[x,y,44.510],5.50,1.485,"Flush head, broad-end diameter 5.50"),
                  cmd("solid.chamfer",body=n,edges=[[x+2.75,y,44.510]],distance=1.26,
                      name="Matching countersunk head bearing surface"),
                  cyl(n,"join",[x,y,43.655],3.0,.90,"Unthreaded shank at lid"),
                  cyl(n,"join",[x,y,37.995],2.42,5.68,"M3 x 8 countersunk screw; thread root gauge"),
                  cyl(n,"cut",[x,y,45.215],1.90,.90,"Driver socket gauge")])
    for x in (-37.0,24.0):
        a.append(block(LID,"join",x,-58.65,41.55,x+13,-57.15,43.70,
                 "Front register: 0.45 clearance, two mm vertical engagement"))
    for left,right in [(-89.65,-88.15),(73.15,74.65)]:
        a.append(block(LID,"join",left,-22.0,41.55,right,-10.0,43.70,
                 "Side register: lid locates before screws are fitted"))
    return a


def antenna_saddles():
    # Positional cold-fit rests, not substitutes for the native electrical
    # bonds/coax/retention. The disk support stays forward of the SOURCE PCB
    # lower outline so it does not obstruct vertical insertion of the board.
    a=[block(BASE,"join",42.5,-47.55,8.32,53.3,-45.15,24.30,
             "Round antenna dielectric rest outside board insertion outline"),
       block(BASE,"join",43.7,-50.14,8.32,52.2,-48.84,25.65,
             "Outboard front limit of removable round antenna"),
       block(BASE,"join",43.7,-49.25,8.32,52.2,-47.20,24.30,
             "Buttress of round antenna front rest")]
    # #13 has its original board-side fixing; the free rear tab is supported.
    a+=tab_guide(58.60,50.985,2.9,3.65,4.30,13.05,"Antenna 13 free rear tab")
    a+=tab_guide(-66.05,-28.0,117.7,6.00,4.60,13.05,"Antenna 14 folded tab")
    return a


def front_blank():
    x=-81.5
    # Through button provision and removable D1 external shape. One continuous
    # backing web replaces cantilevered horizontal standoffs for upright FDM.
    a=[block(BASE,"join",-87.85,-59.32,8.32,-75.15,-53.44,35.92,
             "Floor-supported button landing with room for a later service board"),
       cyl(BASE,"cut",[x,-61.67,25.20],10.70,8.43,
           "Through provision for the removable blank or later verified switch","Y"),
       block(BLANK,"new",-85.75,-53.44,14.95,-77.25,-51.64,35.45,
             "D1-compatible removable blank face on stock datums"),
       cyl(BLANK,"join",[x,-59.65,25.20],7.80,6.35,"Blank stem; cannot actuate a switch","Y"),
       cyl(BLANK,"join",[x,-61.36,25.20],10.10,1.90,"Solid cap recessed 0.14 from front","Y"),
       cmd("solid.chamfer",body=BLANK,edges=[[x+5.05,-59.46,25.20]],distance=1.05,
           name="45 degree rise from stem to cap in flange-down print orientation")]
    for z,n in zip([17.5,32.9],BLANK_HARDWARE):
        a += [cyl(BASE,"cut",[x,-58.60,z],1.70,5.28,"Blind M2 plastic-forming pilot","Y"),
              cyl(BLANK,"cut",[x,-53.54,z],2.45,2.05,"Inside M2 clearance","Y"),
              cyl(n,"new",[x,-57.64,z],1.54,4.25,"M2 x 6 scenario, minor-diameter polymer threads","Y"),
              cyl(n,"join",[x,-53.41,z],2.00,1.78,"Clearance shank through plate","Y"),
              cyl(n,"join",[x,-51.64,z],3.80,1.64,"Driver head accessible with lid and holder removed","Y"),
              cyl(n,"cut",[x,-50.72,z],1.62,.85,"Inside-facing driver socket gauge","Y")]
    return a


def operations():
    return shell()+board_seats()+lid_attachment()+antenna_saddles()+front_blank()
