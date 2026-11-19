# Contributing

There are two useful ways to contribute: make an engineering change that can be checked against the D2.6 reference, or report what a printed part does on a real board. Keep those kinds of evidence separate. The published D2.6 files remain a reference for both.

## Work from a checkout

Run commands from the project root. To verify the frozen files, use the standard-library verifier; it does not require SolidCraft, a printer or a browser:

```sh
python tools/verify_release.py
```

For engineering tasks, use PowerShell 7. Start with `doctor` to see which parts of the toolchain are available:

```powershell
./project.ps1 doctor
npm ci --prefix cad/solidcraft-m1/viewer
./project.ps1 check
```

The browser check uses an installed Edge or Playwright Chromium; the [viewer guide](docs/VIEWER.md) gives the Chromium install command. Consult the [CAD build guide](docs/CAD-BUILD.md) before running `./project.ps1 build` and the [viewer guide](docs/VIEWER.md) for `./project.ps1 viewer`. Some operations require an installed CAD application or separately obtained source assets. The released STL, STEP and viewer files can be inspected without rebuilding the source models.

## Submit an engineering change

1. Identify the revision, affected parts, and the observation that motivates the change. For a port or mounting change, record the coordinate basis, units, and whether a figure came from a reference model, a specification, a measurement or an assumption.
2. Make the smallest coherent change. If a panel change also affects the base, lid or holder, name the matching parts. Give a changed printable design its own revision; keep the recorded D2.6 files intact.
3. Report the commands you ran, what they verified and what remains open. For a geometry change, include a comparable before/after view or a dimensional result. For a viewer change, check the relevant interaction as well as the rendered page.

The public Git tree is a selection from a larger engineering workspace. If a build needs a new CAD input, list it in [cad-inputs.txt](tools/cad-inputs.txt), confirm it can be redistributed, and add that specific path to Git. Do not force-add a whole historical directory. Use `python tools/check_public_tree.py` to check the staged file list and links before you submit.

Use **SOURCE** for geometry taken from a reference; **DOCUMENTED** for a specification or drawing; **MEASURED** for a physical measurement; and **ASSUMED** for an unverified input. Record a CAD or slicer result as calculated, with its input revision. A successful slice does not establish printed fit, electrical behavior or temperature.

## Report a fit result

Start with the [D2.6 first-fit kit](cad/solidcraft-m1/prototype-d26/d2.6-first-fit.zip) on an unpowered board. A useful report can be short:

- **Setup:** revision, part numbers, printer, material, nozzle size, first and subsequent layer heights, orientation, and whether supports were enabled.
- **Observation:** exact location, whether the part sat freely, and any difference with and without the panel. Identify the plug or cable where relevant.
- **Evidence:** measured value, units and measuring method, or a description if no measurement was taken. A detail photo with a scale is useful if you own it and intend to publish it.

For D2.6, the shared Thunderbolt shield and the USB-A/audio area are especially useful checks. The [fit sheet](cad/solidcraft-m1/prototype-d26/FIT-FIRST.md) lists the rest. Do not include private owner photographs or republish supplier files; cite the source instead.
