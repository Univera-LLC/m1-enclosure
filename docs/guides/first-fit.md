# First fit: print and check D2.6

Start with the [five-piece first-fit kit](https://univera-llc.github.io/m1-enclosure/downloads/d2.6/d2.6-first-fit.zip). It lets you try the rear panel, power holder and board supports before printing the full base and lid. **Keep the board unpowered throughout.** The D2.6 parts passed digital checks; their fit on a physical board remains unverified.

## 1. Check your printer's scale

Download the [20 mm calibration cube](../../cad/solidcraft-m1/calibration/calibration-cube-20mm.stl) (on GitHub, choose **Download raw file**). Import it in millimetres at 100%. The slicer should show **20 × 20 × 20 mm**. Record the printer, filament and profile you will use for the case. Before printing, note which faces correspond to X, Y and Z, your measuring tool's accuracy, and the error you will accept.

Let the print cool. Measure each axis in three places on the flat faces, away from corners and the widened first layer. If the result is outside your chosen tolerance, check the printer and profile, then repeat the cube. Keep the case at 100%: one cube cannot tell you how a socket or a long panel will fit.

## 2. Print the small kit

Use the supplied orientations, millimetres, 100% scale and no supports. The [verified slice](../../cad/solidcraft-m1/prototype-d26/print/slice-checks.json) used PrusaSlicer 2.9.7, an Ender-3 Pro profile, a 0.4 mm nozzle and Generic PETG.

| Part | Slice settings |
| --- | --- |
| **02** rear panel | The smooth outside face is already on the bed; the pockets face up. Use Classic perimeters, 100% rectilinear infill and **0.10 mm for every layer, including the first**. The checked slice has 26 layers. |
| **01** power holder, **06** board support strip, **07** side guide, **08** lid stop | Use the 0.20 mm Normal profile. The same profile applies to the full base, lid and front blank later. |

## 3. Try the panel, plugs and samples

Use loose cables with their far ends disconnected. Leave the original board and heatsink together.

1. **Panel:** Check for bow before and after placing 02 against the bare board. The connector housings should sit inside their rear pockets, including the silver bridge in the shared USB-A/audio pocket. The audio collar should enter the round opening without rubbing. Pay particular attention to the metal **between the two Thunderbolt sockets**: the two digital board references disagree here. The panel should sit flat without pressure or rocking.
2. **Plugs:** Compare insertion with and without the panel. Try both USB-A plugs together, HDMI, 3.5 mm audio, and both Thunderbolt sockets with a USB-C plug in both orientations. Include your shortest exposed USB-C tip. Check that Ethernet latches **and releases**. Try the separate USB-C power inlet in its holder with a disconnected cable.
3. **Mounts:** Check both board mounting points on strip 06. Try the CMTPD and Mini-560 modules in holder 01. Slide the panel into side guide 07 and check it against lid stop 08. Stop at any interference; record where it touches before filing or changing anything.

## 4. Move to the full case only if the small kit fits

Print **03** base, **04** lid and **05** front blank from the [full D2.6 kit](https://univera-llc.github.io/m1-enclosure/downloads/d2.6/d2.6-cold-fit-kit.zip). Keep 01–04 and samples 06–08 on D2.6; only blank 05 is unchanged from D2.5.

Lower panel 02 into the base guides from above. Lower the board slightly forward of its final position so the audio collar follows the inside groove. Slide the board back into the pockets while it is still above the supports; then lower it onto both supports and fit the two board screws. The CAD path starts **2.10 mm forward** and slides back **0.27 mm above the seated height**. Fit holder 01 with the same sequence. Try lid 04 without force. Leave the antennas out and the power disconnected for this first assembly.

[Report a fit result](https://github.com/Univera-LLC/m1-enclosure/issues/new?template=fit-report.yml) with the part numbers, print setup and what changed with and without the panel. Include units and method for measurements; a photo with a ruler helps if you want to share it. The [original Ukrainian fit sheet](../../cad/solidcraft-m1/prototype-d26/FIT-FIRST.md) ships unchanged in both print kits.
