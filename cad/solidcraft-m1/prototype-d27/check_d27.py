"""Compare exported D2.7 solids to D2.6 and rerun the affected fit gates."""

from itertools import combinations
import json

import numpy as np

import check_d26 as d26_checks
import check_geometry as q
import check_mount
import check_ports
import check_power
from geometry import d26 as s


def assess(before, p):
    b, power = s.base, s.power
    base, lid, holder = (p[n] for n in (b.BASE, b.LID, power.HOLDER))
    actual, antennas = q.owner(), q.optional()
    board = actual[q.BOARD_LABEL]
    counts = {}

    # All nominal native solids and the reused registered Mac reference fit.
    counts['native pairwise'] = q.free('native', ((i, a, j, c) for (i, a), (j, c) in combinations(p.items(), 2)), .0004)
    counts['Mac, harnesses and historical antenna keepouts'] = q.free('refs', q.cross({**actual, **antennas}, p), .0004)
    limits = np.ptp(np.vstack([q.bounds(solid) for solid in {**p, **actual}.values()]), axis=0)
    assert np.allclose(limits, [170., 119.91, 46.], atol=.015, rtol=0)
    for n, solid in p.items():
        assert len([piece for piece in solid.decompose() if piece.volume() > .0003]) == 1, n

    # At the two existing screw positions, the annular Z14 seat still takes
    # the down-load. There must be no feature above that plane and the top
    # of the blind pilot must be open. The rear anti-tip rests are separate.
    supports = []
    for x, y in b.PCB_AXES:
        region = q.rect([x-3.51, y-3.51, 14.0001], [x+3.51, y+3.51, 15.0])
        assert q.vol(base, region) < .00002
        collar = q.vol(before[b.BASE], region)
        assert collar > 1.
        for dx, dy in [(2.65, 0), (-2.65, 0), (0, 2.65), (0, -2.65)]:
            hits = base.ray_cast([x+dx, y+dy, 16.], [x+dx, y+dy, 12.])
            assert abs(hits[0].position[2] - b.PCB_SEAT) < .003
        pilot = base.ray_cast([x, y, 14.1], [x, y, 8.5])
        assert abs(pilot[0].position[2] - 8.87) < .003
        supports.append({'axis_xy_mm': [x, y], 'top_z_mm': b.PCB_SEAT, 'od_mm': 7.,
                         'pilot_mm': 2.60, 'removed_register_mm3': round(collar, 4)})
    counts['flat ring probes'] = 14

    # Preserve the known insertion path with the panel in its guide. Loose
    # screw play does not become permission to move the board into the panel.
    fixed = {n: p[n] for n in (b.BASE, s.PANEL, b.BLANK, *b.FEET, *b.BLANK_HARDWARE)}
    field = q.field_guard(p[s.PANEL])
    fixed['panel tolerance field'] = field
    board_path = q.travel([[0., -s.FEED, 38.], [0., -s.FEED, s.ALIGN],
                           [0., 0., s.ALIGN], [0., 0., 0.]], actual, fixed)
    counts['board service sweeps'] = sum(map(len, board_path.values()))
    loose_positions = {str(dx): round(q.vol(board.translate([dx, 0., 0.]), field), 5)
                       for dx in (-.45, 0., .45)}
    assert loose_positions['0.0'] < .0004
    counts['loose board offsets'] = len(loose_positions)

    peg_axes = []
    for x, y in power.PEGS:
        y += s.POWER_DY
        clip = q.rect([x-2.50, y-2.50, 8.4001], [x+2.50, y+2.50, 11.0])
        a, c = before[b.BASE] ^ clip, base ^ clip
        assert (a-c).volume() + (c-a).volume() < .0001
        assert abs(q.bounds(c)[1, 2] - 10.95) < .005
        peg_axes.append([x, round(y, 2)])
    counts['unchanged case peg sections'] = len(peg_axes)

    for n in (power.PD, power.BUCK):
        assert q.vol(p[n].translate([0., 0., -.12]), holder) > .4, n
        assert q.vol(p[n].translate([0., 0., .68]), lid) > .15, n
    for dy in (-.48, .48):
        assert q.vol(p[power.BUCK].translate([0., dy, 0.]), holder) > .12, dy
    counts['board edge support and capture challenges'] = 6

    closed = {n: v for n, v in {**p, **actual}.items() if n not in (b.LID, *b.LID_HARDWARE)}
    closed['panel guide travel field'] = q.guide_guard(p[s.PANEL])
    cover_path = q.travel([[0., 0., 0.], [0., 0., 49.]], {b.LID: lid}, closed)
    counts['lid removal sweeps'] = len(cover_path['1'])
    ear = lid ^ q.rect([-83.1, 53., 26.8], [-78.0, 55.62+s.PD_SHIFT, 31.0])
    q.sweep.axial_cover(ear, field, [0., 0., 0.], [0., 0., 49.])
    counts['lid PD ear removal through full field'] = 1

    air = json.loads((s.OLD/'photo-study/board_fins_report.json').read_text(encoding='utf-8'))
    routes = air['d2_1']['updated_gauges_desk_mm']
    assert len(routes) == 21
    lanes = [q.rect(np.minimum(a, c)-.7, np.maximum(a, c)+.7)
             for pts in routes.values() for a, c in zip(pts, pts[1:])]
    counts['convection keepouts'] = q.free('air', q.cross(dict(enumerate(lanes)), {**p, **actual}), .0004)

    detail = {}
    for label, result in [('base', d26_checks.base_checks(p, actual)), ('panel mount', check_mount.assess(p)),
                          ('ports', check_ports.assess(p, actual)), ('power', check_power.assess(p, actual, antennas))]:
        assert not result['failures']
        result['revision'] = 'D2.7'
        detail[label] = result
        counts[label] = result['comparisons']
    detail['board-install'] = {'revision': 'D2.7', 'failures': [], 'comparisons': counts['board service sweeps'],
                               'waypoints_xyz_mm': [[0., -s.FEED, 38.], [0., -s.FEED, s.ALIGN],
                                                    [0., 0., s.ALIGN], [0., 0., 0.]],
                               'continuous_slab_covers': board_path, 'supports': supports,
                               'scope': 'Panel first and held against the rear datums. Align the ports before tightening the screws.'}
    detail['mount'] = detail.pop('panel mount')
    return {'revision': 'D2.7', 'status': 'passed', 'failures': [], 'physical_status': 'NOT TESTED',
            'basis': 'desk mm; +Y rear, +Z up', 'assembled_size_xyz_mm': limits.round(3).tolist(),
            'comparisons': sum(counts.values()), 'checks': counts, 'supports': supports,
            'panel_overlap_mm3_at_loose_board_dx_mm': loose_positions,
            'peg_axes_xy_mm': peg_axes, 'peg_pitch_mm': 45.,
            'pd_fr4_clearance_gauge_xyz_mm': np.ptp(q.bounds(p[power.PD]), axis=0).round(3).tolist(),
            'carrier_volume_before_after_mm3': [round(v.volume(), 3) for v in (before[power.HOLDER], holder)],
            'details': detail}
