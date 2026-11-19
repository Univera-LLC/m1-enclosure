"""Verify the published kit without Git, network, CAD applications or a private checkout."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def inside(base, name):
    p = PurePosixPath(name)
    require(name == p.as_posix() and p.parts and not p.is_absolute()
            and not any(x in {".", "..", ".git"} for x in p.parts)
            and ":" not in name and "\\" not in name, f"invalid release path: {name}")
    resolved = (base / name).resolve()
    require(resolved.is_relative_to(base), f"path outside release root: {name}")
    return resolved


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(root):
    project = load(root / "project.json")
    manifest = load(inside(root, project["published_manifest"]))
    rev = manifest["revision"]
    prefix = f"downloads/{rev.lower()}/"
    receipts, companions = manifest["files"], manifest.get("companion_files", {})
    require(receipts.keys().isdisjoint(companions), "duplicate release and companion route")
    records = {**receipts, **companions}
    paths = {}
    for route, entry in records.items():
        inside(root, route)  # Paths for the optional static-site export.
        path = paths[route] = inside(root, entry["source"])
        data = path.read_bytes()
        require(len(data) == entry["bytes"] and hashlib.sha256(data).hexdigest() == entry["sha256"],
                f"published bytes differ: {entry['source']} ({route})")

    first_fit = f"{prefix}{rev.lower()}-first-fit.zip"
    if project["revision"] == rev:
        require(inside(root, project["first_fit"]) == paths[first_fit],
                "active first_fit does not match this release")

    def report(name):
        return load(paths[prefix + name])

    cad, fit = report("cad-validation.json"), report("fit-validation.json")
    stls, slices = report("print/stl-checks.json"), report("print/slice-checks.json")
    require(all(r["revision"] == rev for r in (cad, fit, stls, slices)), "mixed report revisions")
    require(fit["status"] == "passed" and fit["failures"] == [], "failed digital fit")
    require(fit["physical_status"] == manifest["physical_status"], "physical status differs from release")
    for r in (fit, stls, slices):
        require(r["cad_report_sha256"] == records[prefix + "cad-validation.json"]["sha256"],
                "CAD report has changed since validation")
    for r in (stls, slices):
        require(r["fit_report_sha256"] == records[prefix + "fit-validation.json"]["sha256"],
                "fit report has changed since validation")
    printed = {route.rsplit("/", 1)[1] for route in paths if route.startswith(prefix) and route.endswith(".stl")}
    require(len(printed) == 8 and printed == stls["parts"].keys() == slices["parts"].keys(),
            "STL set differs between release and reports")
    for part in printed:
        sha = records[prefix + "print/" + part]["sha256"]
        sliced = slices["parts"][part]
        require(stls["parts"][part]["sha256"] == sha == sliced["input_sha256"] and sliced["warnings"] == [],
                f"slice and STL records differ: {part}")
    for route in paths:
        if route.startswith(prefix) and route.endswith((".step", ".sc")):
            name = route[len(prefix):]
            require(cad["files_sha256"][name] == records[route]["sha256"] and cad["readback"][name],
                    f"CAD readback differs: {name}")
    board = records[f"reference/{rev.lower()}/mac-board-reference.glb"]["sha256"]
    require(board == cad["owner_board_sha256"] == fit["owner_board_sha256"], "board reference differs")
    for kind, ids in (("first-fit", {"01", "02", "06", "07", "08"}),
                      ("cold-fit-kit", {"01", "02", "03", "04", "05"})):
        name = f"{rev.lower()}-{kind}.zip"
        members = {part: prefix + "print/" + part for part in printed if part[:2] in ids}
        require({part[:2] for part in members} == ids and len(members) == len(ids), f"wrong part IDs: {name}")
        members.update({p: prefix + p for p in ("CREDITS.txt", "FIT-FIRST.md")})
        members.update({p: prefix + "print/" + p for p in ("slice-checks.json", "stl-checks.json")})
        with ZipFile(paths[prefix + name]) as kit:
            require(sorted(kit.namelist()) == sorted(members), f"wrong or duplicate ZIP entries: {name}")
            for member, route in members.items():
                require(kit.read(member) == paths[route].read_bytes(), f"kit content differs: {name}/{member}")
    return manifest, paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="source checkout (default: this script's checkout)")
    parser.add_argument("--site-dir", type=Path, help="copy the verified release routes into a NEW directory")
    args = parser.parse_args()
    try:
        manifest, paths = verify(args.root.resolve())
        if args.site_dir:
            dest = args.site_dir.resolve()
            dest.mkdir(parents=True, exist_ok=False)
            for route, path in paths.items():
                target = inside(dest, route)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        print(f"Verified {manifest['revision']}: {len(manifest['files'])} published files, "
              f"{len(manifest.get('companion_files', {}))} companion assets, 8 sliced STL files and both kits; "
              f"Pages {manifest['pages_commit'][:12]}; physical fit: {manifest['physical_status']}.")
    except (OSError, ValueError, KeyError, BadZipFile) as err:
        print(f"Release verification failed: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
