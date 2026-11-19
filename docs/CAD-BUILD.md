# Rebuild the CAD and print kits

The build reads the [pinned source list](../tools/cad-inputs.txt) and writes into a **new directory**. It first rebuilds the D2.6 reference, then builds D2.7 with flat board supports and a revised carrier. It neither publishes nor sends G-code to a printer. A digital pass does not establish physical fit, electrical safety, cooling or RF performance.

## Install the pinned tools

The tested platform is 64-bit Windows. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), [SolidCraft](https://docs.solidcraft.io/) with its headless CLI **0.44.1**, and [PrusaSlicer 2.9.7](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.7) with its original bundled `resources/profiles/Creality.ini`. In PowerShell at the project root:

```powershell
uv sync --locked
# Set these only if the corresponding CLI is not in PATH or a standard install directory.
$env:SOLIDCRAFT_CLI = 'C:\Program Files\SolidCraft\solidcraft-cli.exe'
$env:PRUSA_SLICER = 'C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe'
```

[uv.lock](../uv.lock) pins NumPy, SciPy, trimesh and manifold3d for CPython 3.13. The runner checks the CAD CLI, the slicer version and the vendor profile hash. The case uses the Ender‑3 Pro 0.4 mm nozzle and Generic PETG presets; the panel uses 0.10 mm layers. Python optimization (`-O`, `PYTHONOPTIMIZE`) is refused because it suppresses geometry assertions.

## Supply the external board reference and build

Obtain **Complete Assembly.STL** from SnazzyLabs’ [Shrink the M1 Mac mini!, Printables #139893](https://www.printables.com/model/139893-shrink-the-m1-mac-mini). Extract the original binary STL. The expected SHA-256 is `3ca388f848672a8f1a5e98765d13c7e39f36b98e1d05b64d1df53faf7ddb1a7a`. The original belongs to its author under the terms on the source page; it is not bundled here. See the [geometry credits](../cad/solidcraft-m1/prototype-d26/CREDITS.txt). No other source STL, photos, Apple manuals or KiCad project are required.

```powershell
$assembly = 'D:\reference\Complete Assembly.STL'
uv run --locked python tools/cad_build.py --doctor --assembly $assembly
uv run --locked python tools/cad_build.py --assembly $assembly --output build/d26-first
uv run --locked python tools/cad_build.py --verify --output build/d26-first
uv run --locked python cad/solidcraft-m1/prototype-d27/build_d27.py --baseline build/d26-first --output build/d27-first
```

For the full D2.7 build, install the [viewer dependencies](VIEWER.md) and run `./project.ps1 build -Assembly $assembly -OutputPath build/d27-complete`. It writes the D2.6 reference under `baseline/`, the D2.7 model, reports and print kits under `cad/`, and a browser preview under `viewer/`. It writes `candidate.json` after the native and browser checks pass. The Python commands above can reuse a verified baseline without repeating that stage. D2.7 build directories must be under `build/`.

The tool welds exact float32 source vertices and labels faces connected by shared edges. It checks all three resulting array hashes before building. To reuse the arrays from that run, use `--inputs build/d26-first/workspace/cad/solidcraft-m1/source-analysis` in place of `--assembly` and choose a new `--output`. An existing engineering workspace can use its original `cad/solidcraft-m1/source-analysis` directory; this is the default if neither argument is given. The public source checkout needs the author's STL or these verified arrays to perform a full rebuild.

Windows portable option: extract the official `PrusaSlicer-2.9.7.zip` (SHA-256 `5d4f395aeb6c344b300e0e1be37a0e1931622b642c3c3085eb19cdae211bc008`) under `%LOCALAPPDATA%\Programs`. The runner discovers the versioned folder there; no PATH change or administrator privileges are required.

| Required local reference cache | SHA-256 |
| --- | --- |
| vertices.npy | `765e3b034ecf691ad9558150a73b4f30729d9a225a4e2084afc6c314c51ed514` |
| faces.npy | `19bb513ace65e7eb1a70cc0aa5c7853262734f232e3756eebd2137d08495fc2c` |
| face-component-labels.npy | `96e00a651d4e9bd28f90eb566ec23d77a14e50f82f7ba210d8fd6905e50de862` |

## Read the result

`build/d26-first/run.json` records each stage. A successful run also writes `verified.json`, the output SHA-256 ledger used by `--verify`. A failed run has no verified ledger. Inspect its stage and error, fix the cause and run in a **new** directory. This preserves earlier verified outputs. Work on the source under `cad/solidcraft-m1/`; staged files are copies.

The D2.7 build places `d27-workbench.sc`, two STEP files, eight STL files, the two kits, `fit-validation.json` and `verified.json` in its output directory. It checks the flat supports, two power pegs, loaded carrier travel and assembly clearances. It slices the five changed files and reuses the D2.6 slice results for byte-identical 02, 05 and 07. The physical procedure is in [FIT-FIRST.md](../cad/solidcraft-m1/prototype-d27/FIT-FIRST.md).

The D2.6 reference artifacts are under `build/d26-first/workspace/cad/solidcraft-m1/prototype-d26/`. The frozen D2.6 design has 341 CAD operations, 5,023 fit comparisons and 26 panel layers. Its original raw board model and photo-registered board disagree around the common Thunderbolt shield. The crosscheck reports both; it also applies to the identical D2.7 panel.

You can inspect two D2.6 reports without installing CAD tools. The [board connector dimensions](../cad/solidcraft-m1/prototype-d26/board-study/port-contract.json) give the axes and outlines of the seven original board sockets and distinguish source geometry, photo estimates and assumptions. The [base fit report](../cad/solidcraft-m1/prototype-d26/base-fit.json) details the 118 digital base comparisons, including screw access and support on the two board mounting rings.

`tools/cad_build.py` always builds the D2.6 reference and compares its eight STL files to the D2.6 receipt. `--verify` also checks a previous D2.6 output independently of [the site's active revision](../project.json).

**Compatibility with the published D2.6 release:** SolidCraft 0.44.1 rejects duplicate sketch names during a clean build. The builder now includes the X station in the names of the YZ sections and their extrusions. This changes 14 display-name fields in the 454 submitted commands; removing only those suffixes reproduces the archived command hash exactly. The corrected operation SHA-256 starts with `285da3c3`; the published release report retains `994b76eb`. No command coordinates, sizes, operations or materials changed.

**Reproduction evidence (2026-11-19):** Starting from the author’s original STL, the clean build regenerated all eight print STLs byte-for-byte, reopened both STEP files and the native assembly, passed 5,023 digital fit comparisons and reproduced 51,795 checked panel extrusion segments. The two reference models still give 0 and 37.48917 mm³ of interference at the shared Thunderbolt shield; physical acceptance remains open.

The baseline ledger records the D2.6 manifest hash, comparison result and a fingerprint of the staged source files. The D2.7 packer checks the generated model and report hashes against its own CAD ledger. To verify the published downloads instead of a new build, use `python tools/verify_release.py`.

The stage verifies native readbacks and part geometry, STL validity and slicer outputs. STEP or SC metadata and ZIP timestamps may differ between builds. Compare the operation hash (accounting for the known label change), native body bounds/volumes, STL meshes, slicer metrics and reference crosscheck rather than expecting identical bytes for every container. The scratch G-code, raw arrays, intermediate SC cache and working directory are local and do not belong in a public source or Pages commit.
