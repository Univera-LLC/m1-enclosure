"""D2 power: one bed-down print; two locating pegs and the closed case lid retain it.

Desk mm. Only the two board outlines and the buck's overall 5.4-mm stack are
documented by the sellers. Shell position, laminate, solder, land widths, gaps,
peg fit and all hardware interfaces are cold-fit scenarios, not measurements.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "prototype-d1"))
import build_d1 as d1

BASE, LID = "D2_MONO_BASE", "D2_TOP_COVER"
SADDLE = HOLDER = "D2_POWER_SADDLE"
PD, BUCK, SOCKET = "D2_CMTPD_FR4_GAUGE", "D2_MINI560_FR4_GAUGE", "D2_USB_C_SHELL_GAUGE"
CHIPS = ["D2_CMTPD_POPULATION_GAUGE", "D2_MINI560_POPULATION_GAUGE"]
BACKS = ["D2_CMTPD_SOLDER_GAUGE", "D2_MINI560_SOLDER_GAUGE"]
MODULES = [PD, BUCK, SOCKET, *CHIPS, *BACKS]
HARDWARE = []  # No fasteners for boards or holder. An ordinary 2.5-mm tie secures insulated leads only.
FILES = {"saddle":[SADDLE], "boards":[PD, BUCK], "population":[*CHIPS, *BACKS], "socket":[SOCKET]}

Z_FLOOR, Z_BED, LID_ROOT = 8.40, 11.15, 43.93
CX, SLOT = d1.CX, 2.20
LIP = .72                      # Only these short lands touch the cut edge of the laminate.
UP_GAP, HOLDER_GAP = .55, .25  # Plastic seats first; shell has .40, then FR4 .55 mm travel.
PEG_D, BORE_D, PEG_H = 4.80, 5.40, 2.55
PEGS = [(-79.10,-9.0), (-79.10,36.0)]
SLOT_EXTRA = 1.40              # Rounded second hole takes up length/shrinkage along Y only.
BED_X = (-83.75,-74.45)
BED_Y = (-33.6,53.65)
# Open both sides directly to the base's inner power-intake slots. A 3.83-mm
# continuous spine plus the full-width lands carry the loads; no thin perimeter
# surrounds an air window. All three openings are normal to the printer bed.
VENT_SPANS = [(-4.85,.55),(5.82,19.78),(23.87,30.05)]
VENT_WEB = (-80.38,-76.55)
FRONT_STOP = (-79.85,-26.65,-75.05,-23.05,25.90)
REAR_STOP = (-85.40,44.80,-82.86,49.05,27.10)
SHELL_PALM = (-83.93,50.30,-79.25,53.65)  # Above and below metal, clear of the assumed plated rings.

block, cyl = d1.block, d1.cyl


def module_gauges():
    """Reuse the actual D1 parameterised module geometry, including its worst-case envelopes."""
    names = dict(zip([d1.PD,d1.BUCK,d1.SOCKET,*d1.CHIPS,*d1.BACKS], MODULES))
    ops = d1.gauges()
    for op in ops:
        p = op['params']
        if 'body_name' in p: p['body_name'] = names[p['body_name']]
        if 'targets' in p: p['targets'] = [names[n] for n in p['targets']]
    return ops


def seating():
    ops = [block(SADDLE,'new',BED_X[0],BED_Y[0],Z_FLOOR,BED_X[1],BED_Y[1],Z_BED,
                 'Broad uninterrupted bed; prints in its installed orientation')]
    for low,high in VENT_SPANS:
        for x0,x1 in [(BED_X[0]-.10,VENT_WEB[0]),(VENT_WEB[1],BED_X[1]+.10)]:
            ops += [block(SADDLE,'cut',x0,low,Z_FLOOR-.10,x1,high,Z_BED+.10,
                          'Open-sided intake relief; full support under all edge lands')]
    for i,(x,y) in enumerate(PEGS):
        ops += [cyl(BASE,'join',[x,y,Z_FLOOR-.09],PEG_D,PEG_H+.09,
                    'Integral round floor locator; no screw, thread, nut or metal insert')]
        if i == 0:
            ops += [cyl(SADDLE,'cut',[x,y,Z_FLOOR-.12],BORE_D,Z_BED-Z_FLOOR+.24,
                        'Round locating hole fixes transverse and longitudinal position')]
        else:
            r,dy = BORE_D/2,SLOT_EXTRA/2
            ops += [block(SADDLE,'cut',x-r,y-dy,Z_FLOOR-.12,x+r,y+dy,Z_BED+.12,
                          'Longitudinal relief between semicircular ends of second locating hole')]
            for ey in (y-dy,y+dy):
                ops += [cyl(SADDLE,'cut',[x,ey,Z_FLOOR-.12],BORE_D,Z_BED-Z_FLOOR+.24,
                            'Rounded end: second locator restrains yaw without forcing hole pitch')]
    # Four local islands, not continuous edge channels: the hot face, terminal pads and
    # the centre of the CMTPD long edge remain open. Short lips grow directly from a broad foot.
    for rear,lands,lo,hi,buck in [(d1.Y_REAR,d1.PD_LANDS,d1.PD_LOW,d1.PD_HIGH,False),
                                  (d1.Y_B,d1.BUCK_LANDS,d1.B_LOW,d1.B_HIGH,True)]:
        for a,b in lands:
            y0,y1 = rear-b,rear-a
            ops += [block(SADDLE,'join',-81.50,y0,Z_BED-.10,-74.45,y1,lo+LIP,'Buttressed bare-edge seat'),
                    block(SADDLE,'cut',CX-SLOT/2,y0-.05,lo,CX+SLOT/2,y1+.05,lo+LIP+.12,'Flat laminate datum with 0.30 mm face clearance')]
            # In lid print orientation the broad root is on the bed side and the narrow
            # toes grow last. Only on the unobstructed side can a jaw descend past FR4.
            mid=(y0+y1)/2
            ops += [block(LID,'join',-80.50,mid-2.50,33.10,-74.70,mid+2.50,LID_ROOT,'Broad lid root, independent of module preload')]
            back_only = buck and a > 7
            ops += [block(LID,'join',CX-.22 if back_only else -80.50,y0,hi-.24,-74.70,y1,33.23,
                          'Backside-only stop at the 4R7 land' if back_only else 'Short lid keeper at confirmed-by-fit-only FR4 land'),
                    block(LID,'cut',CX-SLOT/2,y0-.04,hi-.34,CX+SLOT/2,y1+.04,hi+UP_GAP,
                          'Stop lies above FR4; tightening lid screws never preloads laminate in nominal CAD')]
    return ops


def stops_and_leads():
    ops=[]
    # These posts carry removing/inverting the *holder* into the closed lid. Neither
    # the screw load nor a moving holder needs to bear on a component or PCB for this.
    ops += [block(SADDLE,'join',-80.10,-27.20,Z_BED-.10,-74.70,-22.65,FRONT_STOP[-1],
                  'Front compression pillar, directly above the flat bed'),
            block(SADDLE,'join',CX-.64,-23.0,Z_BED-.10,CX+.64,d1.Y_F-.33,24.80,
                  'Buck front abutment: only the centre of the laminate end face'),
            block(SADDLE,'join',-85.55,43.90,Z_FLOOR,-82.60,49.14,Z_BED,
                  'Broad foot under the USB thrust buttress'),
            block(SADDLE,'join',-84.40,49.09,Z_FLOOR,-82.60,53.65,Z_BED,
                  'Foot under shell cradle, stepped clear of the rear corner lid support'),
            block(SADDLE,'join',-85.55,44.42,Z_BED-.10,-82.73,49.14,REAR_STOP[-1],
                  'Full-height buttress outside component face; direct path to bed and locating pegs')]
    for x0,y0,x1,y1,z in (FRONT_STOP,REAR_STOP):
        ops += [block(LID,'join',x0,y0,z+HOLDER_GAP,x1,y1,LID_ROOT,
                      'Plastic-to-plastic travel stop for the saddle; no retained hardware')]
    # The short end fences bear on the laminate core, not the power pads on either face.
    # The CMTPD rear end has 1.0 mm to the panel: the metal face bearings engage first.
    for y0,y1,lo in [(d1.Y_B+.33,d1.Y_B+2.85,d1.B_LOW),(d1.Y_PD-2.85,d1.Y_PD-.33,d1.PD_LOW)]:
        ops += [block(SADDLE,'join',-80.2,y0,Z_BED-.10,-76.65,y1,lo-.12,'Fully backed base below a laminate-end fence'),
                block(SADDLE,'join',CX-.65,y0,lo-.24,CX+.65,y1,lo+2.65,'Short backed end stop; closed lid supplies upper capture')]
    # A continuous shoe replaces the two thin D1 fingers. Its narrow axial land is
    # the measured-by-fit gap between the shell shoulder and the seller-photo parts;
    # it is joined along its full height to a deep outside buttress and to the bed.
    ops += [block(SADDLE,'join',-82.90,48.19,Z_BED-.10,-78.65,49.48,26.98,'Metal-only thrust face, backed full height at side and below; leave room for the module to move aft'),
            block(SADDLE,'join',-84.0,49.48,Z_BED-.10,-79.25,53.65,17.46,'Lower shell shelf, 0.27 mm below metal; outside plated-ring reserve'),
            block(SADDLE,'join',-84.20,49.34,11.04,-81.85,53.65,24.78,'Outside lateral shell shoe, 0.30 mm from metal'),
            block(LID,'join',SHELL_PALM[0],SHELL_PALM[1],27.07,SHELL_PALM[2],SHELL_PALM[3],LID_ROOT,
                  'Upper metal-shell support only; no tie on socket or solder')]
    # One straight tunnel printed above a full bed. The roof bridges only its 3.25-mm
    # width in Y. A tie can be threaded with the main floor still present.
    ops += [block(SADDLE,'join',-85.65,-33.60,Z_FLOOR,-80.0,-26.08,15.72,'Cradle for insulated output leads, away from pads'),
            block(SADDLE,'cut',-85.80,-31.50,12.10,-79.85,-28.25,14.10,'3.25 x 2.0 mm transverse tunnel for an ordinary 2.5 mm wire tie')]
    return ops


def operations():
    return seating()+stops_and_leads()+module_gauges()
