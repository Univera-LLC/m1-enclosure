"""D2.6: seven registered Mac connector noses + real photographed USB-A/audio combo housing, in desk mm (+Y out).

Updated 2026-11-19 from owner's six close-up/profile/underside/ruler photographs:
- USB-A1/A2 black bezels are ~15.60 x 8.55 mm (not 14.20 x 6.55), joined by a
  recessed vertical/horizontal silver metal T-bridge at Y=56.19.
- Audio housing is a ~10.00 x 6.20 mm rectangular black block flush with the
  USB-A bezels (Y=56.45) topped by a metal shield (to Z=35.75, Y=55.99), plus
  a protruding Ø5.00 mm round collar extending +0.59 mm to Y=57.04.
- HDMI bezel updated to ~16.60 x 8.20 mm (Z=17.40..25.60); RJ-45 bezel width
  updated to ~15.84 mm; shared TB1+TB2 rear metal shield modeled to Y=55.11.
"""
from pathlib import Path
import json
if not __debug__:
    raise RuntimeError("D2.6 board checks require Python without -O or PYTHONOPTIMIZE")
import numpy as np

HERE = Path(__file__).resolve().parent
import manifold3d as md

ROOT_Y = 54.05
FLOOR_Y = 54.19
ANG = 96
# axis X/Z | lip Y | outer W,H,R and vertical offset dz from axis | internal W,H
# Status: axis X/Z & lip Y = SOURCE; outer W/H = DOCUMENTED (photo measurements 2026-11-19);
# exact Apple tolerances = ASSUMED (no caliper contact measurements yet).
DATA = {
    'A1':    (49.90, 22.00, 56.45, 15.60, 8.55, .55, +.175, 12.50, 5.12),
    'A2':    (32.70, 22.00, 56.45, 15.60, 8.55, .55, +.175, 12.50, 5.12),
    'HDMI':  (-1.525, 22.10, 56.45, 16.60, 8.20, .55, -.60, 14.38, 4.95),
    'TB1':   (-19.05, 22.00, 56.35, 11.55, 5.40, .60, 0.,    8.40, 2.60),
    'TB2':   (-33.70, 22.00, 56.35, 11.55, 5.40, .60, 0.,    8.40, 2.60),
    'RJ':    (-64.65, 23.00, 56.45, 15.84, 11.60, .55, -.80, 12.40, 7.40),
    'audio': (41.30, 32.20, 56.45, 10.00, 6.20, .40, -.10,   3.55, 3.55),
}
AUDIO_COLLAR_OD = 5.00
AUDIO_COLLAR_TIP_Y = 57.04   # +0.59 mm proud of rectangular black audio face (side profile photo)
T_BRIDGE_Y = 56.19           # -0.26 mm behind USB-A black bezel face (side profile photo)
AUDIO_SHIELD_Y = 55.99       # -0.46 mm behind USB-A black bezel face; reaches Z=35.75
TB_SHIELD_Y = 55.11          # -1.24 mm behind TB black bezel faces (bottom photo)


def rounded(w, h, r):
    if abs(w - h) < 1e-9 and abs(h - 2 * r) < 1e-9:
        return md.CrossSection.circle(r, ANG)
    if abs(h - 2 * r) < 1e-9:
        return md.CrossSection.batch_hull([md.CrossSection.circle(r, ANG).translate([sign * (w / 2 - r), 0]) for sign in (-1, 1)])
    if r == 0:
        return md.CrossSection.square([w, h], True)
    sides = min(ANG, max(12, int(np.ceil(r * 30 / 4)) * 4))
    return md.CrossSection.square([w - 2 * r, h - 2 * r], True).offset(r, md.JoinType.Round, circular_segments=sides)


def outer(n):
    x, z, _, w, h, r, dz, *_ = DATA[n]
    return rounded(w, h, r).translate([x, z + dz])


def bore(n):
    x, z, *_ = DATA[n]
    w, h = DATA[n][-2:]
    dz = DATA[n][6] if n == 'audio' else 0.
    if n.startswith('TB') or n == 'audio':
        p = rounded(w, h, h / 2)
    elif n.startswith('A'):
        p = rounded(w, h, .34)
    elif n == 'HDMI':
        c = 1.12
        p = md.CrossSection([[[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2 - c], [w / 2 - c, h / 2], [-w / 2 + c, h / 2], [-w / 2, h / 2 - c]]])
    else:
        p = rounded(w, h, .38)
        for width, z0, z1 in [(6.70, -4.82, -3.10), (4.08, -5.82, -4.36)]:
            p += rounded(width, z1 - z0, .15).translate([0, (z1 + z0) / 2])
    return p.translate([x, z + dz])


def extrude(p, ya, yb):
    return p.extrude(yb - ya).rotate([90, 0, 0]).translate([0, yb, 0])


def rect(w, h, r, x, z, y0, y1):
    return extrude(rounded(w, h, r).translate([x, z]), y0, y1)


def grouped(name):
    x, z, face, _, _, _, dz, *_ = DATA[name]
    out = outer(name)
    hole = bore(name)
    metal = (.16 if name.startswith('TB') else .23 if name.startswith('A') else .20)
    liner_outer = hole.offset(metal, md.JoinType.Round, circular_segments=ANG)
    front = {}

    def tag(kind, finish, body):
        n = 'oem__ports__' + finish + '__D26_' + name + '_' + kind
        front[n] = body.as_original()

    if name == 'audio':
        # Rectangular black audio housing flush with USB-A bezels, plus protruding Ø5.00 mm collar.
        collar_outer = md.CrossSection.circle(AUDIO_COLLAR_OD / 2, ANG).translate([x, z + dz])
        tag('lip', 'maccomponent', extrude(out - hole, FLOOR_Y, face) + extrude(collar_outer - hole, face - .02, AUDIO_COLLAR_TIP_Y))
        tag('liner', 'macmetal', extrude(liner_outer - hole, FLOOR_Y, face - .15))
        tag('back', 'macinsulator', extrude(out, ROOT_Y, FLOOR_Y))
        # Upper metal shield slightly taller than black housing (Z up to 35.75, Y up to 55.99)
        shield_top = rounded(10.00, 6.75, .35).translate([x, 32.375]) - hole
        tag('shield', 'macmetal', extrude(shield_top, ROOT_Y, AUDIO_SHIELD_Y))
    else:
        tag('lip', 'maccomponent', extrude(out - liner_outer, FLOOR_Y, face))
        tag('liner', 'macmetal' if name != 'RJ' else 'maccomponent', extrude(liner_outer - hole, FLOOR_Y, face - .08))
        tag('back', 'macinsulator', extrude(out, ROOT_Y, FLOOR_Y))

    pads = []
    tiny = .013
    if name.startswith('TB') or name.startswith('A') or name == 'HDMI':
        if name.startswith('TB'):
            w, h, cz, fore = 6.63, .67, z, face - .66
        elif name.startswith('A'):
            w, h, cz, fore = 10.62, 1.46, z + 1.03, face - .66
        else:
            w, h, cz, fore = 10.88, .71, z + .08, face - .72
        tag('tongue', 'maccomponent', rect(w, h, min(.27, h / 2 - .015), x, cz, FLOOR_Y, fore))
        if name.startswith('TB'):
            rows = [(12, .5, +1, 0.), (12, .5, -1, 0.)]
        elif name.startswith('A'):
            rows = [(4, 2.30, -1, 0.), (5, 1.83, -1, -.77)]
        else:
            rows = [(10, .94, +1, 0.), (9, .94, -1, 0.)]
        for count, pitch, side, delta in rows:
            for i in range(count):
                px = x + (i - (count - 1) / 2) * pitch
                y1 = fore - .13 + delta
                y0 = max(FLOOR_Y + .04, y1 - (.57 if name.startswith('A') else .72))
                pads.append(rect(.59 if name.startswith('A') else .20, .047, 0, px, cz + side * (h / 2 + .047 / 2 - tiny), y0, y1))
    elif name == 'RJ':
        for i in range(8):
            cx = x + (i - 3.5) * 1.016
            a = rect(.28, .17, .04, cx, z + 3.67, FLOOR_Y, FLOOR_Y + .16)
            b = rect(.28, .17, .04, cx, z + 2.56, face - .72, face - .60)
            pads.append(md.Manifold.batch_hull([a, b]))
    elif name == 'audio':
        pads.append(rect(.14, .64, .06, x + 1.72, z + dz, FLOOR_Y, face - 1.08))
    if pads:
        tag('contacts', 'maccontact', md.Manifold.batch_boolean(pads, md.OpType.Add))
    return front


def shared_shields():
    """Physical metal bridges photographed between grouped connectors."""
    out = {}
    # Silver T-bridge between A1, A2 and Audio (vertical divider + horizontal shelf)
    v_bar = rounded(1.70, 8.55, .15).translate([41.30, 22.175])
    h_shelf = rounded(10.00, 2.65, .15).translate([41.30, 27.725])
    out['oem__ports__macmetal__D26_usb_audio_t_bridge'] = extrude(v_bar + h_shelf, ROOT_Y, T_BRIDGE_Y).as_original()
    # Shared rear metal shield behind TB1 & TB2 (sits on PCB at Z=17.40, stops at Y=55.11)
    tb_body = rounded(26.10, 7.10, .35).translate([-26.30, 20.95])
    out['oem__ports__macmetal__D26_tb_shared_shield'] = extrude(tb_body, ROOT_Y, TB_SHIELD_Y).as_original()
    return out


def probe_positions(n):
    x, z, y, w, h, r, dz, iw, ih = DATA[n]
    if n == 'audio':
        # Probe on the flat rectangular black audio face outside the Ø5.8/5.9 aperture
        rim = (x + 4.10, z + dz)
        deep = (x, z + dz)
    elif n == 'RJ':
        rim = (x + 7.25, z)
        deep = (x, z - 5.28)
    else:
        rim = (x, z + dz + h / 2 - .25)
        deep = (x, z - ih / 2 + .54)
    tongue = (x, z + (1.03 if n.startswith('A') else .08 if n == 'HDMI' else 0))
    probes = {'rim': rim, 'open_to_back': deep}
    if n not in ('RJ', 'audio'):
        probes['tongue'] = tongue
    return {k: [round(v[0], 4), round(v[1], 4)] for k, v in probes.items()}


def contract():
    def pts(cs):
        return [[[round(x, 6), round(z, 6)] for x, z in loop] for loop in cs.to_polygons()]
    ports = {}
    for n, (x, z, y, w, h, r, dz, iw, ih) in DATA.items():
        row = {
            'axis_xz_mm': [x, z],
            'source_lip_y_mm': y,
            'outer_center_xz_mm': [x, round(z + dz, 4)],
            'outer_profile': 'rounded_rectangle',
            'outer_width_height_radius_mm': [w, h, r],
            'inner_main_width_height_mm': [iw, ih],
            'inner_profile': ('capsule' if n.startswith('TB') else 'upper corner chamfers 1.12 mm' if n == 'HDMI'
                              else 'rectangle plus two-step lower latch channel' if n == 'RJ'
                              else 'circle' if n == 'audio' else 'rounded rectangle R0.34'),
            'outer_loops_xz_mm': pts(outer(n)),
            'inner_loops_xz_mm': pts(bore(n)),
            'clear_geometry_depth_to_partial_study_back_mm': round(y - FLOOR_Y, 3),
            'mesh_names': list(grouped(n)),
            'front_ray_probes_xz_mm': probe_positions(n),
        }
        if n == 'audio':
            row['protruding_collar_od_mm'] = AUDIO_COLLAR_OD
            row['protruding_collar_tip_y_mm'] = AUDIO_COLLAR_TIP_Y
            row['protruding_collar_center_xz_mm'] = [x, round(z + dz, 4)]
        ports[n] = row
    return {
        'revision': 'D2.6',
        'units': 'desk millimetres; right-handed, +Y towards cable, +Z up; loops CCW viewed in the X,Z plane',
        'source_reference': 'SnazzyLabs SOURCE 20 registered envelope updated with 2026-11-19 owner macro/ruler/side/underside photographs.',
        'status': {
            'SOURCE': 'port axes, PCB mounting rings and heatsink/board datums retained from registered SOURCE 20.',
            'DOCUMENTED': '2026-11-19 owner photos (2.54 mm PCB ruler, dead-flat side profile, 3/4 macro, underside & marked D2.5 orange print) document 15.6x8.55 USB-A bezels, silver T-bridge (Y=56.19), 10.0x6.2 rectangular audio block + protruding Ø5.00 collar (+0.59 mm to Y=57.04), 16.6x8.2 HDMI, 15.84 RJ-45, and shared TB rear shield.',
            'ASSUMED': 'corner radii, internal bore/tongue shapes, and exact tolerances between photographic scale and caliper measurements.',
            'MEASURED': 'none by caliper yet; 2.54 mm PCB ruler photo gives ~±0.15 mm visual scale on audio housing and collar.'
        },
        'rear_common_body_max_y_mm': ROOT_Y,
        'model_back_wall_y_mm': FLOOR_Y,
        'shared_bridges': {
            'usb_audio_t_bridge_y_mm': T_BRIDGE_Y,
            'audio_shield_y_mm': AUDIO_SHIELD_Y,
            'tb_shared_shield_y_mm': TB_SHIELD_Y,
        },
        'ports': ports,
    }


if __name__ == '__main__':
    (HERE / 'port-contract.json').write_text(json.dumps(contract(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
