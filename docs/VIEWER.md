# Preview and verify the enclosure release

From the project root, run `python tools/verify_release.py`. It checks the active [D2.7 receipt](../release/d2.7-manifest.json), including the frozen viewer page, CAD readback, STL and slicing hashes, and the contents of both print kits. It uses Python's standard library and does not run CAD. For the previous release, run `python tools/verify_release.py --manifest release/d2.6-manifest.json`. Both releases are digital prototypes for unpowered fitting; passing these checks does not establish physical fit.

## Local viewer

```sh
npm ci --prefix cad/solidcraft-m1/viewer
./project.ps1 viewer
```

Open http://127.0.0.1:8000/. To choose a different port, run `npm --prefix cad/solidcraft-m1/viewer/d26 run preview -- --port 8001`. Stop with Ctrl+C. On Windows, use `npm.cmd` if PowerShell blocks the npm script.

The D2.7 and D2.6 viewers share the UI source in `viewer/d26/`; `project.json` selects the CAD and publication receipt. D2.7 has its own model evidence and fallback images. The local server listens on loopback and serves the built site. The D2.6 and D2.5 viewers, current downloads, and accessory atlas work offline once the dependencies are installed. Older manufacturing archives link to the original Pages site.

Open **Порівняння** in the D2.7 tab bar, or go to http://127.0.0.1:8000/compare/. **3D поруч** opens with both cases aligned on one grid. Drag to orbit; use the wheel, pinch or the zoom buttons to change scale. Each object's rulers follow its visible edges, with numbers in centimetres and ticks at 1 mm. D2.7 shows the shell and visible hardware from the released atlas; Mac mini uses the DatSketch model scaled to Apple's published dimensions. The A4 paper uses the official President.gov.ua portrait. The page includes the source credits and identifies approximate sizes. **Креслення** gives four fixed projections and also opens automatically if WebGL is unavailable.

## Univera LLC GitHub Pages

The [organization home](https://univera-llc.github.io/m1-enclosure/) shows D2.7. The [D2.6 archive](https://univera-llc.github.io/m1-enclosure/d2.6/) retains the earlier scene and versioned downloads. The [Redline R2 experiment](https://univera-llc.github.io/m1-enclosure/redline/) is a separate visual preview.

To stage the same site in a **new** directory and test the Pages URL prefix:

```sh
python tools/prepare_pages.py --output build/pages-artifact/m1-enclosure
python -m http.server 8000 --bind 127.0.0.1 --directory build/pages-artifact
```

Open **http://127.0.0.1:8000/m1-enclosure/**. With the server running, check it with `node cad/solidcraft-m1/viewer/d26/browser.mjs http://127.0.0.1:8000/m1-enclosure/`.

Packaging verifies both receipts and checks that the rebuilt D2.7 page matches the frozen release page. It then adds the comparison tab and its linked page to the site artifact. It verifies all 14 D2.7 downloads, all 14 D2.6 download routes, and links from the comparison, D2.5, accessory and Redline pages. The archive page relocates D2.6's links; its CAD and print downloads keep the original bytes. The site includes licensing, source notices and the plain-text index.

The [workflow](../.github/workflows/check.yml) tests the actual static artifact on pull requests and pushes. Only a successful run on the organization's `main` branch deploys to `github-pages`. The repository's Pages source is **GitHub Actions**.

## Browser and geometry checks

Use `./project.ps1 check` to verify the model hash, saved camera, rear-panel motion, 16 port probes, the base and carrier views, archive navigation and all current downloads. It also checks free orbit, zoom and reset, both 3D case envelopes, projected sizes, the rulers next to each object, the A4 portrait, object selection and the narrow screen layout. The check writes screenshots and a JSON receipt to a new temporary directory. It does not deploy.

The smoke test uses Microsoft Edge when installed at its standard Windows path, otherwise Playwright Chromium. Install Chromium with `npx playwright install chromium` from `cad/solidcraft-m1/viewer` (use `--with-deps` on a minimal Linux runner).

For an engineering preview, start with a [verified CAD build](CAD-BUILD.md) such as `build/d27-first` and run:

```sh
uv run --locked python cad/solidcraft-m1/viewer/d26/pack_model.py --cad-dir build/d27-first --output build/d27-packed
node cad/solidcraft-m1/viewer/d26/build.mjs --packed build/d27-packed --cad-dir build/d27-first --output build/d27-engineering-viewer
node cad/solidcraft-m1/viewer/d26/browser.mjs --engineering build/d27-engineering-viewer
```

The packer checks the native mesh and CAD report hashes, reopens the packed GLB, and verifies the eight through-profiles and port probes. The board and the shared rear panel retain their D2.6 basis. The three historical RF meshes, the alternative PCB display and small component illustrations are reference geometry. Engineering previews use the published stills unless they are rendered again from the candidate.

To regenerate stills, build with `--draft --packed … --cad-dir … --output …` and run `node cad/solidcraft-m1/viewer/d26/browser.mjs --posters SITE OUT` with that draft directory and a new image directory. Rendered site files should match the release model in `geometry-check.json`.
