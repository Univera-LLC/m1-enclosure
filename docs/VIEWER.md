# Preview and verify the D2.6 release

From the project root, run `python tools/verify_release.py`. This read-only check uses Python's standard library. It compares file bytes with the published receipt, checks the CAD and slicer report hashes, and opens both kits to compare every member against the individual release files. It does not run CAD or repeat slicing.

The [manifest](../release/d2.6-manifest.json) separates 36 files from the original HTTPS check from 20 accessory assets taken from the same [Pages commit](https://github.com/Dvaderfun/mac-mini-m1-case-prototype/commit/bf7ed6792866e8523eaec3ae2603070908fee04c). `project.json` points to this published receipt even if a later working revision is under development. A passed check establishes digital identity; the recorded physical fit status is **NOT TESTED**.

## Local viewer

```sh
npm ci --prefix cad/solidcraft-m1/viewer
npm --prefix cad/solidcraft-m1/viewer/d26 run preview
```

Open http://127.0.0.1:8000/ in your browser. To use another port, append `-- --port 8001` to the preview command. Stop the server with Ctrl+C. On Windows, use `npm.cmd` if PowerShell blocks the npm script.

The preview rebuilds the UI from its JavaScript, templates, styles and the verified model embedded in the published D2.6 HTML. It writes to `build/d26-viewer/`. The model, 14 downloads, accessory models and posters, and D2.5 archive viewer work offline. Earlier revision pages and old manufacturing downloads open the existing GitHub Pages site and require a connection. The preview only serves specified files and listens on loopback.

## Univera LLC GitHub Pages

The [organization viewer](https://univera-llc.github.io/m1-enclosure/) uses the current UI source with the frozen D2.6 manufacturing files. To prepare the same static site in a **new** directory, install the dependencies above, then run:

```sh
python tools/prepare_pages.py --output build/pages-artifact/m1-enclosure
python -m http.server 8000 --bind 127.0.0.1 --directory build/pages-artifact
```

Open **http://127.0.0.1:8000/m1-enclosure/**. To exercise this exact site, run `node cad/solidcraft-m1/viewer/d26/browser.mjs http://127.0.0.1:8000/m1-enclosure/` in a second terminal after installing a browser as described below.

Packaging verifies the original release receipt, rebuilds the home page, verifies all 14 downloadable files against their SHA-256 hashes, and checks the HTML routes under the same URL prefix as Pages. The D2.5 viewer and accessory models are included. Older archives and D2.5 manufacturing downloads point to their original host. The site carries the current Univera license, source and dependency notices and the machine-readable navigation index. The published ZIPs remain byte-for-byte identical to the original D2.6 release.

The organization site also links to the separate [Redline R2 experiment](https://univera-llc.github.io/m1-enclosure/redline/). The [preview snapshot](../release/redline-r2-site/) contains its self-contained 3D view and three CAD renders. Redline is a visual preview for an unpowered fit prototype; D2.6 remains the revision for the site's print kits.

The [workflow](../.github/workflows/check.yml) tests the actual static artifact on pull requests and branch pushes. Only a successful push or manual run on the organization's `main` branch uploads and deploys it to the `github-pages` environment. The repository's Pages source must be **GitHub Actions**. The raw directory in `release/d2.6-site/` is a set of frozen inputs with their original navigation; use a materialized site for browsing.

## Browser and release checks

```sh
npm --prefix cad/solidcraft-m1/viewer/d26 run check
npm --prefix cad/solidcraft-m1/viewer/d26 run check -- --published
```

The first command checks the rebuilt UI. The second checks the unchanged published HTML and does not run the build. Both start a local server and exercise the saved camera, the exploded rear panel, 16 port probes, the inside view, all 14 downloaded files by hash, and the D2.5 archive viewer. The commands print the path to their screenshots and JSON receipt in a new temporary directory. They do not change historical verification records or deploy anything.

The smoke test uses Microsoft Edge when installed at its standard Windows path, otherwise Playwright Chromium. To install the browser, run `npx playwright install chromium` from `cad/solidcraft-m1/viewer`; on a minimal Linux runner use `npx playwright install --with-deps chromium`. Node dependencies and the browser require an initial download; local verification, builds, and checks then run offline.

For a standalone copy, run `python tools/verify_release.py --site-dir build/d26-site`. The target must not yet exist. This writes the 36 verified routes and 20 companion assets with the original bytes; it is a snapshot of this release, not a mirror of older manufacturing archives. To verify another checkout from an existing installation, pass `--root PATH`. Links inside the frozen `release/d2.6-site/README.md` use the published URL layout; use the local preview or materialize the site before following them.

## Maintainer notes

`npm --prefix cad/solidcraft-m1/viewer/d26 run build` rebuilds the viewer from the frozen D2.6 model; it does not re-run CAD. To see geometry from a new [verified CAD build](CAD-BUILD.md), run these commands from the project root. Replace `build/d26-first` with that build's directory:

```sh
uv run --locked python tools/cad_build.py --verify --output build/d26-first
uv run --locked python cad/solidcraft-m1/viewer/d26/pack_model.py --cad-dir build/d26-first/workspace/cad/solidcraft-m1/prototype-d26 --output build/d26-packed
npm --prefix cad/solidcraft-m1/viewer/d26 run build -- --packed build/d26-packed --cad-dir build/d26-first/workspace/cad/solidcraft-m1/prototype-d26 --output build/d26-first/viewer
npm --prefix cad/solidcraft-m1/viewer/d26 run check -- --engineering build/d26-first/viewer
```

The packer requires a new output directory. It builds the native bodies, cutaways and registered board from the selected CAD; it rechecks native bounds, the eight through profiles and the port probes after reading back its GLB. It reuses the three historical RF reference pieces, the alternative PCB display and 17 cosmetic landmarks from the published model. These are illustrative meshes; their original private inputs are not needed. The output GLB and its fresh `geometry-check.json` stay together. The tool targets the D2.6 part names and fit contract and fails if a new design no longer satisfies them.

Open `build/d26-first/viewer/index.html` to inspect the engineering preview. Both the packer and the engineering UI build require new output directories. The browser smoke reads the candidate's model hash and port probes and checks 14 actual downloads against that build's inputs; STEP, SC and ZIP bytes can legitimately differ from those in the older published snapshot. Screenshots and a JSON receipt go into a new `browser-check-*` directory under the candidate. Static workshop pictures, explanatory text and poster frames still describe the published D2.6; review and update them for a different design before release. Neither the packer nor the UI build updates the published receipt.

Asset provenance and redistribution conditions are in [THIRD_PARTY.md](../THIRD_PARTY.md) and the [original release attribution](../release/d2.6-site/ATTRIBUTION.md).
