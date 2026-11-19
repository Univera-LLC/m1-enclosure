# Enclosure Lab

**A printable enclosure study for Mac mini (M1, 2020) · Univera LLC**

![Exploded CAD rendering of the D2.6 enclosure. The vented lid lifts above the base; the removable rear panel is highlighted in orange.](docs/assets/d26-enclosure.jpg)

Keep the original logic board and heatsink. Print the parts around them. D2.6 is a **170 × 119.91 × 46 mm** enclosure with a removable lid, a separate USB-C power inlet and an eight-opening rear panel. The small first-fit kit lets you check the hardest part—the fit around your own sockets and plugs—before committing to the whole case.

**[Explore the 3D model](https://univera-llc.github.io/m1-enclosure/)** &nbsp;·&nbsp; **[Download the first-fit kit · ZIP](https://univera-llc.github.io/m1-enclosure/downloads/d2.6/d2.6-first-fit.zip)** &nbsp;·&nbsp; **[Open the editable CAD](cad/solidcraft-m1/prototype-d26/d26-workbench.sc)**

[View the model offline](docs/VIEWER.md#local-viewer)

**Current status:** D2.6 passed digital geometry and slicing checks. The printed D2.6 parts have **not** been accepted on a physical board. This release is for an **unpowered fit check**. Power, button operation, passive cooling and wireless performance remain unverified.

## Print the small kit first

1. **Unzip the [first-fit kit](cad/solidcraft-m1/prototype-d26/d2.6-first-fit.zip).** It contains a power holder (**01**), rear panel (**02**) and three little pieces (**06–08**) that stand in for the board supports, side guide and lid stop. Leave the full base and lid for later.
2. **Print the supplied STL orientations at 100%, in millimetres.** The checked Ender 3 Pro setup uses PETG, a 0.4 mm nozzle and no supports. Use **0.10 mm for every layer of the panel**, including the first. Its smooth outside face is already on the bed. The holder and samples use 0.20 mm layers.
3. **Try the parts without power.** Set the panel against the bare board. It should sit flat without pressing on the metal between the two Thunderbolt sockets. Compare each plug with and without the panel; try both USB-A plugs together and check that the Ethernet latch releases. Check the holder, guides and board supports before printing the [five-part case](cad/solidcraft-m1/prototype-d26/d2.6-cold-fit-kit.zip).

[Full fit procedure (Ukrainian)](cad/solidcraft-m1/prototype-d26/FIT-FIRST.md) · [How to report a fit result](CONTRIBUTING.md#report-a-fit-result)

## Why this panel looks different

The first D2.5 panel bowed near the USB-A ports and audio jack. Here is the back of its D2.6 replacement, the side you can’t see once the board is installed:

![Inside face of panel 02. From left to right, the modeled face walls are 0.40 mm at the USB-C power opening, 0.90 mm at Thunderbolt and 0.80 mm at the shared USB-A and audio pocket.](docs/assets/d26-detail-views.jpg)

The outer face moved **0.60 mm** outward. A shared T-shaped recess now clears the USB-A and audio housings in the photo-registered model while leaving **0.80 mm** of plastic in front of them. The Thunderbolt region deserves its own fit check: two digital references disagree about the common metal shield. [Compare D2.5 and D2.6](cad/solidcraft-m1/prototype-d26/d25-vs-d26-usb-audio-comparison.svg) or [read the numerical comparison](cad/solidcraft-m1/prototype-d26/reference-crosscheck.json).

## Choose a file

| To… | Open |
| --- | --- |
| Print the entire case after the first fit | [D2.6 full STL kit](cad/solidcraft-m1/prototype-d26/d2.6-cold-fit-kit.zip). Keep 01–04 and samples 06–08 from the same revision. |
| Modify the design in CAD | [SolidCraft workbench](cad/solidcraft-m1/prototype-d26/d26-workbench.sc) · [printable parts STEP](cad/solidcraft-m1/prototype-d26/d26-printable.step) · [mechanical assembly STEP](cad/solidcraft-m1/prototype-d26/d26-assembly.step) |
| Inspect the board and heatsink | [Board reference · GLB](cad/solidcraft-m1/prototype-d26/board-study/mac-board-reference.glb). The STEP files contain mechanical solids; the board mesh is in the GLB and native workbench. |
| Reproduce a change | [CAD toolchain](docs/CAD-BUILD.md) · [viewer and browser checks](docs/VIEWER.md) · [contributor guide](CONTRIBUTING.md) |

To compare the files in your checkout with the published release, run `python tools/verify_release.py`. No CAD software is required for that check. For scripts and other tools: [current revision and paths](project.json) · [published file hashes](release/d2.6-manifest.json) · [plain-text index](llms.txt).

## Use and attribution

You can print your own case, adapt the design and share it free of charge under the [noncommercial project license](LICENSE). **Selling kits or cases, paid printing (even at cost) and other commercial uses require separate prior written permission from Univera LLC.** The logic-board and other third-party references retain their own [attribution and license terms](THIRD_PARTY.md).

Mac and Mac mini are trademarks of Apple Inc. Their use here identifies the intended hardware. Enclosure Lab is an independent project and is not affiliated with, sponsored by or endorsed by Apple.
