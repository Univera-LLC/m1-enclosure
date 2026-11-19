"""Run the D2.6 CAD, fit and slicer gates in a new, isolated directory."""
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CAD = Path("cad/solidcraft-m1")
ACTIVE = CAD / "prototype-d26"
INPUTS = Path(__file__).with_name("cad-inputs.txt")
RAW = {
    "vertices.npy": "765e3b034ecf691ad9558150a73b4f30729d9a225a4e2084afc6c314c51ed514",
    "faces.npy": "19bb513ace65e7eb1a70cc0aa5c7853262734f232e3756eebd2137d08495fc2c",
    "face-component-labels.npy": "96e00a651d4e9bd28f90eb566ec23d77a14e50f82f7ba210d8fd6905e50de862",
}
ASSEMBLY = "3ca388f848672a8f1a5e98765d13c7e39f36b98e1d05b64d1df53faf7ddb1a7a"
LOCK = {"numpy":"2.5.4", "trimesh":"5.2.1", "scipy":"1.18.1", "manifold3d":"3.5.5"}
KITS = ("d2.6-first-fit.zip", "d2.6-cold-fit-kit.zip")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_hash(path, expected):
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f"Missing or incorrect SHA-256: {path}")


def binary(env, names, *installed):
    choice = os.environ.get(env)
    candidates = [shutil.which(choice) or choice] if choice else [
        *(shutil.which(n) for n in names), *installed]
    for candidate in candidates:
        if candidate and (path := Path(candidate).expanduser()).is_file():
            return path.resolve()
    raise FileNotFoundError(f"Install {names[0]} or set {env} to its executable")


def source_files():
    project = json.loads((ROOT/"project.json").read_text(encoding="utf8"))
    if project.get("revision") != "D2.6" or project.get("cad") != ACTIVE.as_posix():
        raise ValueError("CAD build supports D2.6 only; project.json must select D2.6 and " + ACTIVE.as_posix())
    paths = [Path(s) for s in INPUTS.read_text(encoding="utf8").splitlines() if s and not s.startswith("#")]
    for p in paths:
        if p.is_absolute() or ".." in p.parts or not (ROOT/CAD/p).is_file():
            raise ValueError(f"Missing or invalid CAD source in {INPUTS.name}: {p}")
    return paths


def toolchain():
    if sys.version_info[:2] != (3, 13):
        raise ValueError("Use CPython 3.13: uv sync --locked")
    for name, wanted in LOCK.items():
        if metadata.version(name) != wanted:
            raise ValueError(f"Expected {name}=={wanted}; run uv sync --locked")
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    solid = binary("SOLIDCRAFT_CLI", ["solidcraft-cli"], pf/"SolidCraft/solidcraft-cli.exe")
    portable = Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"Programs/PrusaSlicer-2.9.7/prusa-slicer-console.exe"
    slicer = binary("PRUSA_SLICER", ["prusa-slicer-console", "prusa-slicer"], pf/"Prusa3D/PrusaSlicer/prusa-slicer-console.exe", portable)
    scver = subprocess.check_output([str(solid),"--version"], text=True, encoding="utf8").strip()
    psver = subprocess.check_output([str(slicer),"--help"], text=True, encoding="utf8", errors="replace").splitlines()[0]
    if scver != "solidcraft-cli 0.44.1" or not psver.startswith("PrusaSlicer-2.9.7 "):
        raise ValueError(f"D2.6 baseline requires SolidCraft 0.44.1 and PrusaSlicer 2.9.7; found {scver}, {psver}")
    check_hash(slicer.parent/"resources/profiles/Creality.ini","79992570253bcde938819785e9c5fa7226b88f74188b3efa11c6e2d556a74040")
    return solid, slicer, {"python":sys.version.split()[0], **LOCK, "solidcraft":scver,"slicer":psver}


def make_arrays(stl, target):
    # Same exact float32 welding and face-edge connectivity as the historical source analysis.
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    record = np.dtype([("normal","<f4",(3,)),("vectors","<f4",(3,3)),("attribute","<u2")])
    raw = np.ascontiguousarray(np.memmap(stl,dtype=record,mode="r",offset=84)["vectors"]).reshape(-1,3)
    raw[raw == 0] = 0
    _, idx, inverse = np.unique(raw.view("V12").ravel(),return_index=True,return_inverse=True)
    faces = inverse.reshape(-1,3).astype(np.uint32)
    np.save(target/"vertices.npy",raw[idx])
    np.save(target/"faces.npy",faces)
    del raw, idx, inverse, _
    edges = faces[:,[0,1,1,2,2,0]].reshape(-1,2).copy()
    edges.sort(axis=1)
    codes = (edges[:,0].astype(np.uint64)<<32) | edges[:,1]
    order = np.argsort(codes)
    ordered = codes[order]
    joined = ordered[1:] == ordered[:-1]
    left, right = ((s[joined]//3).astype(np.int32) for s in (order[:-1],order[1:]))
    graph = coo_matrix((np.ones(len(left),dtype=np.int8),(left,right)),shape=(len(faces),len(faces))).tocsr()
    _, labels = connected_components(graph,directed=False)
    np.save(target/"face-component-labels.npy",labels)


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    tmp.replace(path)


def verify(out):
    ledger = json.loads((out/"verified.json").read_text(encoding="utf8"))
    base = out/"workspace"/ACTIVE
    required = {*KITS, "cad-validation.json","fit-validation.json","reference-crosscheck.json",
                "print/slice-checks.json","print/stl-checks.json","d26-workbench.sc",
                "d26-printable.step","d26-assembly.step"}
    if ledger["revision"] != "D2.6" or ledger["status"] != "passed" or not required <= set(ledger["sha256"]):
        raise ValueError("No complete D2.6 verification record")
    for name,h in ledger["sha256"].items():
        path = (base/name).resolve()
        if not path.is_relative_to(base.resolve()): raise ValueError("Invalid verification path")
        check_hash(path,h)
    print(f"Verified {len(ledger['sha256'])} output files; {base}",flush=True)


def main():
    if not __debug__ or os.environ.get("PYTHONOPTIMIZE","") not in ("","0"):
        raise ValueError("CAD validation requires Python without -O or PYTHONOPTIMIZE")
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--doctor",action="store_true",help="check tools and source inputs without writing")
    mode.add_argument("--verify",action="store_true",help="rehash a completed --output directory; no CAD tools needed")
    data = ap.add_mutually_exclusive_group()
    data.add_argument("--inputs",type=Path,help="directory containing the three reference arrays")
    data.add_argument("--assembly",type=Path,help="original SnazzyLabs Complete Assembly.STL instead of cached arrays")
    ap.add_argument("--output",type=Path,help="new build directory, or completed directory for --verify")
    a = ap.parse_args()
    if a.verify:
        if a.output is None: ap.error("--verify needs --output")
        verify(a.output.resolve());return
    sources = source_files()
    solid,slicer,versions = toolchain()
    arrays = a.inputs or ROOT/CAD/"source-analysis"
    if (arrays/"source-analysis").is_dir(): arrays = arrays/"source-analysis"
    if a.assembly: check_hash(a.assembly, ASSEMBLY)
    else:
        if not all((arrays/n).is_file() for n in RAW):
            raise FileNotFoundError("Reference arrays are missing. Supply --assembly 'Complete Assembly.STL' from Printables #139893, or --inputs with all three checked arrays; see docs/CAD-BUILD.md.")
        for n,h in RAW.items(): check_hash(arrays/n,h)
    print(f"D2.6: {len(sources)} build inputs; {versions}; original reference verified.",flush=True)
    if a.doctor: return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = (a.output or (ROOT/"build"/f"d26-{stamp}")).resolve()
    if out == ROOT or out.is_relative_to(ROOT/CAD):
        raise ValueError("Choose a new output directory outside the source CAD tree")
    out.mkdir(parents=True,exist_ok=False)
    ws = out/"workspace"; active = ws/ACTIVE
    state = {"revision":"D2.6","status":"running","stages":[],"toolchain":versions}
    save(out/"run.json",state)
    try:
        for rel in sources:
            to = ws/CAD/rel;to.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/CAD/rel,to)
        raw = ws/CAD/"source-analysis";raw.mkdir(parents=True,exist_ok=True)
        if a.assembly: make_arrays(a.assembly,raw)
        else:
            for n in RAW: shutil.copyfile(arrays/n,raw/n)
        for n,h in RAW.items(): check_hash(raw/n,h)
        state["reference_sha256"] = RAW
        env = {**os.environ,"SOLIDCRAFT_CLI":str(solid),"PRUSA_SLICER":str(slicer),"PYTHONUTF8":"1","PYTHONDONTWRITEBYTECODE":"1"}
        # Ignore external source trees or site customizations when running the staged copy.
        env.pop("PYTHONPATH",None)
        stages = [("board","board-study/build_board.py"),("cad","build_d26.py"),("fit","check_d26.py"),("stl","make_print.py"),("slice","check_slices.py"),("references","review_ports.py"),("sections","make_section.py"),("kits","make_print.py","--package")]
        for name, script, *args in stages:
            state["current_stage"] = name; save(out/"run.json",state)
            print(f"[{name}] {script} {' '.join(args)}",flush=True)
            subprocess.run([sys.executable,"-B",str(active/script),*args],cwd=ws,env=env,check=True)
            state["stages"].append(name)
        generated = [p for p in active.rglob("*") if p.is_file() and ".work" not in p.parts
                     and p.suffix in (".json",".stl",".glb",".svg",".sc",".step",".zip")]
        hashes = {p.relative_to(active).as_posix():digest(p) for p in sorted(generated)}
        for n in KITS: check_hash(active/n,hashes[n])
        state.update(status="passed",current_stage=None)
        save(out/"run.json",state)
        save(out/"verified.json",{**state,"sha256":hashes,"physical_fit":"NOT TESTED"})
        verify(out)
    except BaseException as exc:
        state.update(status="failed",error=str(exc));save(out/"run.json",state)
        raise


if __name__ == "__main__":
    try: main()
    except (OSError,ValueError,metadata.PackageNotFoundError,subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
