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

Use **SOURCE** for geometry taken from a reference; **DOCUMENTED** for a specification or drawing; **MEASURED** for a physical measurement; and **ASSUMED** for an unverified input. Record a CAD or slicer result as calculated, with its input revision. A successful slice does not establish printed fit, electrical behavior or temperature.

## Add a public file

Put new public Markdown guides in `docs/guides/`. Use relative links to files in the public checkout so the guide also works in a fork. Private engineering notes, owner photos and vendor manuals stay out of this directory.

If a new file is missing from `git status`, run `git check-ignore -v -- path/to/the/file` to find the matching rule. Existing tracked files still show edits even when a rule would hide a new file at that path.

For a new CAD revision, add a narrow exception in [.gitignore](.gitignore) for the revision directory, keep its contents ignored by default, and allow only the reviewed source paths. Confirm that each input can be redistributed; list files needed to rebuild in [cad-inputs.txt](tools/cad-inputs.txt). Do not force-add a historical directory. Stage the intended paths, review `git diff --cached --name-only`, and run `python tools/check_public_tree.py` to verify the public file list and guide links.

## Rights in new contributions

You keep ownership of your original contribution. For a new contribution that you intend us to publish or merge, we ask for two permissions: make that contribution available to the public under the [project’s noncommercial license](LICENSE), and give **Univera LLC a separate commercial license**. The second permission allows Univera to use your contribution in products it sells and to authorize manufacturers, distributors and customers. Public recipients do not receive that commercial grant.

To agree, include the following in your pull request or other written submission. Identify any exceptions or third-party content separately, with its source, notices and terms. We can agree on different terms in writing before accepting the contribution.

> For my original contribution in this submission, I agree to the Univera Noncommercial Project License and grant Univera LLC a nonexclusive, worldwide, perpetual, royalty-free license, irrevocable to the extent permitted by law, to use, reproduce, modify, publish, distribute, manufacture, have manufactured, sell and sublicense my contribution, including commercially. I own the rights I am granting or am authorized by their holder to grant them. I have identified any third-party material and applicable terms separately.

This is permission to use your work, not an assignment of ownership or a patent or trademark license. You can license your own contribution elsewhere; that does not grant rights in anyone else’s underlying case design. The grant does not cover third-party material, earlier submissions or unrelated work. A fork, issue, bug report, fit measurement or silence does not give Univera additional commercial rights. If we want to reuse previously contributed work beyond its existing terms, we must obtain permission from its rights holder.

## Report a fit result

Start with the [D2.6 first-fit kit](cad/solidcraft-m1/prototype-d26/d2.6-first-fit.zip) on an unpowered board. A useful report can be short:

- **Setup:** revision, part numbers, printer, material, nozzle size, first and subsequent layer heights, orientation, and whether supports were enabled.
- **Observation:** exact location, whether the part sat freely, and any difference with and without the panel. Identify the plug or cable where relevant.
- **Evidence:** measured value, units and measuring method, or a description if no measurement was taken. A detail photo with a scale is useful if you own it and intend to publish it.

For D2.6, the shared Thunderbolt shield and the USB-A/audio area are especially useful checks. The [fit sheet](cad/solidcraft-m1/prototype-d26/FIT-FIRST.md) lists the rest. Do not include private owner photographs or republish supplier files; cite the source instead.
