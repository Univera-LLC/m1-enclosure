import numpy as np
import design as s
from check_geometry import *

def assess(p,actual):
    base=p[s.base.BASE];panel=p[s.PANEL];board=actual[BOARD_LABEL]
    fixed={n:p[n] for n in (s.base.BASE,s.PANEL,s.base.BLANK,*s.base.FEET,*s.base.BLANK_HARDWARE)}
    fixed['Panel field: full lateral, vertical, depth and angular reserve']=field_guard(panel)
    poses=[[0.,-s.FEED,38.],[0.,-s.FEED,s.ALIGN],[0.,0.,s.ALIGN],[0.,0.,0.]]
    records=travel(poses,actual,fixed)
    guides=[]
    for x,y in s.base.PCB_AXES:
        ring=base^rect([x-2.1,y-2.1,14.001],[x+2.1,y+2.1,14.85])
        upper=base^rect([x-2.1,y-2.1,14.201],[x+2.1,y+2.1,14.85])
        assert abs(bounds(ring)[1,2]-14.70)<.003 and upper.volume()>.25
        yr=[v.position[2] for v in base.ray_cast([x+1.72,y,12.],[x+1.72,y,15.])]
        assert abs(max(yr)-14.20)<.003
        assert vol(board.translate([0,-s.FEED,0]),ring)>.1
        for move in [(-.45,0,0),(.45,0,0),(0,-.45,0),(0,.45,0)]:
            assert vol(board.translate(move),ring)>.015,(x,move,vol(board.translate(move),ring))
        guides.append({'axis_xy_mm':[x,y],'bearing_underside_mm':14.,'complete_360_deg_register_top_mm':14.20,'tall_forward_sector_top_mm':14.70,
                       'clearance_over_complete_register_during_horizontal_feed_mm':round(s.ALIGN-.20,3),'tall_sector_volume_above_full_ring_mm3':round(upper.volume(),4)})
    wrong=vol(board.translate([0,-s.FEED,0]),base);assert wrong>.4
    return {'revision':'D2.6','failures':[],'comparisons':sum(map(len,records.values()))+14,'waypoints_xyz_mm':poses,'continuous_slab_covers':records,
            'board_supports':guides,'counterexample_slide_without_lifting_overlap_mm3':wrong,'moving':list(actual),'fixed':list(fixed),
            'scope':'Panel first; with lid off, hold both upper corners straight against the fixed outer guide faces. Drop level 2.10 mm forward, horizontal feed at +0.27, settle 0.27; only then fit both screws. Checks include the full closed-case field-motion reserve, not arbitrary lean of an unsupported open panel. Lid, power saddle and antennas absent. No part is rotated.'}
