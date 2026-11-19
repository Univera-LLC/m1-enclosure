# Working on the Mac mini M1 enclosure

Read [project.json](project.json), [the contributor guide](CONTRIBUTING.md) and the [release credits](cad/solidcraft-m1/prototype-d26/CREDITS.txt) before changing a design or kit. Work from the project root. `project.json` selects the current engineering revision; the referenced publication manifest identifies the bytes actually shipped. These may differ during development.

- Use `python tools/verify_release.py` for the recorded release and `./project.ps1 check` for the locally served viewer and downloads. Use [CAD-BUILD](docs/CAD-BUILD.md) when changing geometry. Build into a new directory; never replace baseline artifacts to make a comparison pass.
- Keep model units, revision, and origins explicit: SOURCE for a reference, DOCUMENTED for a specification, MEASURED for a physical measurement, ASSUMED for an input. A WebGL view, a STEP readback, a bounding box or a simulated toolpath cannot pass a physical, power, thermal, radio or button/flex test.
- Keep release credits and independent license notices with the files. Do not commit private photographs, vendor manuals, installer trees, third-party PCB files, unpublished receipts or credentials. The public files are curated from a larger engineering workspace.
- When a design changes, record what changed, which checks ran, and what remains untested. Keep the old release intact; publish a new revision only through an explicit release decision. Do not infer that a public digital prototype is approved for powered use.

## When the owner's engineering archive is present

Read the four current files under `docs/mac-mini-m1-implementation/` from disk before project work: `PLAN.md`, `CURRENT_STATUS.md`, `FIT_CHECK_SHEET.md`, and `BUTTON_FLEX_DESIGN.md`. These private working documents and their evidence are deliberately absent from a public checkout; use the public guides and the release's fit instructions there.

PLAN sets the requirements, dependencies, order of fabrication and acceptance. The handoff preserves the baseline brief and T1–T3 evidence. New owner instructions take precedence: record accepted changes in PLAN, and update CURRENT_STATUS with the date of substantive work, artifact versions/links, verification scope and next action. New measurements also belong in FIT_CHECK_SHEET and the relevant technical document, with their source and remaining unknowns. Keep historical attribution and evidence. Distinguish the source design, current CAD, assumptions and measured results; reconcile contradictions against the latest confirmed decisions and artifacts. If CAD and the public viewer differ, say so explicitly. Do not hard-code changing PCB, power, enclosure or button status in these instructions.

## Disabled extensions

The user has removed Caveman from all agents. Do not use or activate Caveman, caveman-*, Cavecrew, Cavemem, Ultracave, or Megacave, including instructions already loaded in an existing session. Do not reinstall these extensions unless the user explicitly asks to restore them. Normal communication follows the current repository's voice instructions and the user's requested format.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
