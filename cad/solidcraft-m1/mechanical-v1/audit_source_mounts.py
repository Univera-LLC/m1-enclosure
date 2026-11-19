"""Check proposed shell supports against every triangle of retained SOURCE meshes.

This numerical mesh/AABB check is independent of SolidCraft's native boolean
check, which explicitly leaves imported meshes unchecked. It is not a fit test.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
HERE = OUT.parent
EPS = 1e-4  # mm; discard float32 noise and touching faces, not physical tolerance.
SOURCE_IDS = (20, 25, 11, 13, 14)
SOURCE_TRANSFORM = [77.709897965, 110.123044968, 56.498825073]
cover = json.loads((HERE / "native-bottom-v0/source-and-parameters.json").read_text())
# Cover axis 2 belongs to removed source bracket 9; it is NOT a tray anchor.
TRAY_CENTRES = [cover["normalised_centres_xy"][i] for i in (0, 2, 3)]
BOTTOM_CENTRES = [(-48., -50.5), (48., -50.5), (-68., 62.), (68., 62.)]
SHEET_CENTRES = [(-20., -42.), (-20., 52.), (50., -42.), (50., 52.)]
FOOT_CENTRES = [(-66.8, -46.8), (66.8, -46.8), (-48., 61.2), (48., 61.2)]


def sources():
    vertices = np.load(HERE / "source-analysis/vertices.npy", mmap_mode="r")
    faces = np.load(HERE / "source-analysis/faces.npy", mmap_mode="r")
    labels = np.load(HERE / "source-analysis/face-component-labels.npy", mmap_mode="r")
    result = {}
    for ident in SOURCE_IDS:
        selected = faces[np.flatnonzero(labels == ident)]
        raw = np.asarray(vertices[selected], dtype=np.float64)
        triangles = np.stack((raw[:, :, 0] - SOURCE_TRANSFORM[0],
                              SOURCE_TRANSFORM[1] - raw[:, :, 2],
                              raw[:, :, 1] - SOURCE_TRANSFORM[2]), axis=2)
        result[ident] = triangles
    return result


def support_boxes(tray_z=3.15, lug_t=3., web_h=4., boss_h=7.4):
    # Boxes overlap the existing shell walls, so joins have a real connection.
    result = []
    for i, (x, y) in enumerate(TRAY_CENTRES):
        lo_x, hi_x = (-77.5, x + 4.5) if x < 0 else (x - 4.5, 77.5)
        result.append((f"Tray lug {i+1}", [lo_x, y-4.5, tray_z-lug_t],
                       [hi_x, y+4.5, tray_z]))
        lo_x, hi_x = (-77.5, -73.2) if x < 0 else (73.2, 77.5)
        result.append((f"Outboard web {i+1}", [lo_x, y-4.5, tray_z],
                       [hi_x, y+4.5, tray_z+web_h]))
    for i, (x, y) in enumerate(BOTTOM_CENTRES):
        if y < 0:
            lo, hi = [x-5, -57.5, 0], [x+5, y+5, boss_h]
        elif x < 0:
            lo, hi = [-77.5, y-4.5, 0], [x+5, y+4.5, boss_h]
        else:
            lo, hi = [x-5, y-4.5, 0], [77.5, y+4.5, boss_h]
        result.append((f"Bottom boss {i+1}", lo, hi))
    return result


def triangle_box_hits(triangles, lo, hi):
    """Triangle/box SAT (13 axes), counting interior intersection only."""
    lo, hi = np.asarray(lo), np.asarray(hi)
    candidates = (np.all(triangles.max(axis=1) > lo + EPS, axis=1)
                  & np.all(triangles.min(axis=1) < hi - EPS, axis=1))
    indices = np.flatnonzero(candidates)
    if not len(indices):
        return []
    v = triangles[indices] - (lo + hi) / 2
    half = (hi - lo) / 2
    edges = np.roll(v, -1, axis=1) - v
    axes = [np.cross(edges[:, 0], edges[:, 1])]
    axes += [np.cross(edges[:, e], axis) for e in range(3) for axis in np.eye(3)]
    hits = np.ones(len(v), dtype=bool)
    for axis in axes:
        norm = np.linalg.norm(axis, axis=1)
        projection = np.einsum("nvi,ni->nv", v, axis)
        radius = np.abs(axis) @ half
        active = norm > 1e-12
        hits &= ~active | ((projection.min(axis=1) < radius - EPS*norm)
                           & (projection.max(axis=1) > -radius + EPS*norm))
    return indices[hits].tolist()


def inside_source(triangles, point):
    """Vertical ray parity, deduplicating triangulated planar-face crossings."""
    point = np.asarray(point, dtype=float) + [1.37e-7, 2.19e-7, 0]
    mask = (np.all(triangles[:, :, :2].min(axis=1) <= point[:2], axis=1)
            & np.all(triangles[:, :, :2].max(axis=1) >= point[:2], axis=1)
            & (triangles[:, :, 2].max(axis=1) > point[2] + EPS))
    t = triangles[mask]
    if not len(t):
        return False
    a, b = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    delta = point[:2] - t[:, 0, :2]
    det = a[:, 0]*b[:, 1] - a[:, 1]*b[:, 0]
    active = np.abs(det) > 1e-12
    a, b, delta, det, t = a[active], b[active], delta[active], det[active], t[active]
    u = (delta[:, 0]*b[:, 1] - delta[:, 1]*b[:, 0]) / det
    v = (a[:, 0]*delta[:, 1] - a[:, 1]*delta[:, 0]) / det
    z = t[:, 0, 2] + u*a[:, 2] + v*b[:, 2]
    valid = (u >= -1e-10) & (v >= -1e-10) & (u+v <= 1+1e-10) & (z > point[2]+EPS)
    crossings = np.unique(np.round(z[valid], 5))
    return bool(len(crossings) % 2)


def audit(boxes=None, exclude_pairs=()):
    meshes = sources()
    result = {"status": "SOURCE MESH NUMERICAL CHECK ONLY", "epsilon_mm": EPS,
              "method": "All-triangle/AABB SAT plus ray containment; touching is allowed",
              "source_ids": list(SOURCE_IDS), "checks": [], "source_anchors": [],
              "intentional_exclusions": []}
    for name, lo, hi in support_boxes() if boxes is None else boxes:
        for ident, triangles in meshes.items():
            if (name, ident) in exclude_pairs:
                result["intentional_exclusions"].append({"part": name, "component_id": ident,
                    "reason": "ASSUMED insert envelope inside its source plastic host; heat fit not verified"})
                continue
            hits = triangle_box_hits(triangles, lo, hi)
            enclosed = inside_source(triangles, (np.array(lo)+hi)/2) if not hits else False
            check = {"support": name, "component_id": ident, "bounds_mm": [lo, hi],
                     "interior_triangle_hits": len(hits), "box_center_inside": enclosed,
                     "result": "FAIL" if hits or enclosed else "PASS"}
            result["checks"].append(check)
    tray = meshes[25]
    for x, y in TRAY_CENTRES:
        mask = np.all(np.linalg.norm(tray[:, :, :2] - [x, y], axis=2) < 4.6, axis=1)
        local = tray[mask]
        tips = local[np.all(np.abs(local[:, :, 2]-3.15) < EPS, axis=1)]
        area = np.linalg.norm(np.cross(tips[:, 1]-tips[:, 0], tips[:, 2]-tips[:, 0]), axis=1).sum()/2
        assert area > 20, (x, y, area)
        result["source_anchors"].append({"xy_mm": [x, y], "tip_plane_z_mm": 3.15,
                                          "tip_annulus_area_mm2": float(area), "status": "SOURCE"})
    result["source_sha256"] = {
        str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (HERE/"source-analysis/vertices.npy", HERE/"source-analysis/faces.npy",
                     HERE/"source-analysis/face-component-labels.npy")}
    result["pass"] = all(c["result"] == "PASS" for c in result["checks"])
    return result


if __name__ == "__main__":
    result = audit()
    OUT.mkdir(exist_ok=True)
    (OUT/"source-mount-audit.json").write_text(json.dumps(result, indent=2)+"\n")
    failures = [c for c in result["checks"] if c["result"] == "FAIL"]
    print(json.dumps({"checks": len(result["checks"]), "failures": failures,
                      "anchors": result["source_anchors"]}, indent=2))
    assert result["pass"], "Fix the proposed supports before building native CAD"
