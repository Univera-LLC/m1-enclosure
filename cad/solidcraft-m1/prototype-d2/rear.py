"""Shared rear datum, aperture cutter and recessed PD mark. Desk mm, +X to open."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'prototype-d1'))
import build_d1 as d1

PANEL = 'D2_SLIDING_IO_PLATE'
INNER, FACE = 57.35, 59.15
X0, X1 = -88.15, 74.20
Z0, Z1 = 8.70, 41.20
PD_PAD_L, PD_PAD_R, PD_PAD_END = -81.40, -78.45, 58.43
KEY_C = -72.00
block, cyl, cmd = d1.block, d1.cyl, d1.cmd


def rounded(target, x0, x1, z0, z1, radius, label, y0=None, y1=None):
    """A constant-radius through aperture in XZ. Fillet the cutter first."""
    return d1.r.rounded(target, (x0, x1, INNER-.20 if y0 is None else y0,
                                 FACE+.20 if y1 is None else y1, z0, z1),
                        radius, 'cut', label)


def legend():
    # Readable looking at the rear (+Y): screen right corresponds to -X.
    # Strokes >=0.80; 0.40-deep pockets opening into the last two 0.20 layers.
    def stroke(u, z, w, h):
        x = -73.40-u
        return block(PANEL, 'cut', x-w, FACE-.40, 31.50+z,
                     x, FACE+.12, 31.50+z+h, 'PD IN / recessed finish mark')
    strokes = [(0,0,.80,3.80), (.66,3.00,1.63,.80), (.66,1.55,1.63,.80), (2.02,1.72,.80,1.87),
               (3.55,0,.80,3.80), (4.21,3.00,1.49,.80), (4.21,0,1.49,.80), (5.41,.40,.80,3.00),
               (7.85,0,.80,3.80), (9.42,0,.80,3.80), (11.76,0,.80,3.80)]
    ops = [stroke(*s) for s in strokes]
    # Two overlapping short steps join the strokes of N; the entire mark stays
    # printable with a 0.4-mm nozzle and has no external graphic dependency.
    for i in range(4):
        ops.append(stroke(9.95+i*.43, 2.53-i*.55, .91, .91))
    return ops


# The original two upright guide blocks and shared port windows are archived
# in history/d2-732a632.zip. D2.1 uses rear_plate_d21 and rear_mount_d21.
