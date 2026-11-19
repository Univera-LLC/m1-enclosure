"""D2.7 cold-fit CAD delta. Desk mm, +Y rear, +Z up; built on the D2.6 source."""

import design as d26

base, power, d1 = d26.base, d26.power, d26.d1
block, cyl = d26.block, d26.cyl
PD_LENGTH_ALLOWANCE = 2.0  # 43 mm trial envelope; the seller specifies 41 mm.
Z0, BED = power.Z_FLOOR, power.Z_BED


def chassis():
    ops = base.operations()
    flat = [op for op in ops if op['params'].get('name') !=
            'Short registering shoulder inside SOURCE 4.4 mm bore']
    assert len(ops) - len(flat) == 2
    return flat


def carrier():
    h = power.HOLDER
    # A straight web replaces the wide plate and its six vent cutouts. All
    # new feet start on the print bed, including the wider pads at the pins.
    ops = [block(h, 'new', -80.65, -33.60, Z0, -77.35, 53.65, BED,
                 'Narrow continuous carrier spine'),
           block(h, 'join', power.BED_X[0], 43.25, Z0,
                 power.BED_X[1], 53.65, BED, 'Pad under the USB-C shoe')]
    for i, (x, y) in enumerate(power.PEGS):
        ops.append(cyl(h, 'join', [x, y, Z0], 9.0, BED-Z0,
                       f'Carrier bearing pad at existing peg {i+1}'))

    # Keep the two case pegs and the round / slotted mating holes, exactly.
    ops += [op for op in power.seating() if op['params'].get('name') in {
        'Integral round floor locator; no screw, thread, nut or metal insert',
        'Round locating hole fixes transverse and longitudinal position',
        'Longitudinal relief between semicircular ends of second locating hole',
        'Rounded end: second locator restrains yaw without forcing hole pitch',
    }]
    for label, y, low, lands in [('PD', d1.Y_REAR, d1.PD_LOW, d1.PD_LANDS),
                                 ('Mini560', d1.Y_B, d1.B_LOW, d1.BUCK_LANDS)]:
        for i, (a, b) in enumerate(lands):
            y0, y1 = y-b, y-a
            ops += [block(h, 'join', -80.65, y0, Z0, -75.50, y1,
                          low + power.LIP, f'{label} edge seat {i+1}'),
                    block(h, 'cut', power.CX-power.SLOT/2, y0-.05, low,
                          power.CX+power.SLOT/2, y1+.05, low+power.LIP+.12,
                          f'{label} open 2.2 mm groove {i+1}')]

    # Two low end fences capture only the Mini560 laminate. The PD metal shoe
    # fixes its station, so the PD tail can accept a longer board without a stop.
    for i, (y0, y1) in enumerate([(-23.0, d1.Y_F-.33), (d1.Y_B+.33, d1.Y_B+2.10)]):
        ops += [block(h, 'join', -79.02, y0, Z0, -76.75, y1, d1.B_LOW-.12,
                      f'Mini560 end foot {i+1}'),
                block(h, 'join', power.CX-.64, y0, d1.B_LOW-.24,
                      power.CX+.64, y1, d1.B_LOW+2.65, f'Mini560 end fence {i+1}')]

    # Keep the USB shell load path and the existing tunnel for insulated leads.
    # Remove the front pillar, both old carrier travel stops and the PD end fence.
    keep = {
        'Broad foot under the USB thrust buttress',
        'Foot under shell cradle, stepped clear of the rear corner lid support',
        'Full-height buttress outside component face; direct path to bed and locating pegs',
        'Metal-only thrust face, backed full height at side and below; leave room for the module to move aft',
        'Lower shell shelf, 0.27 mm below metal; outside plated-ring reserve',
        'Outside lateral shell shoe, 0.30 mm from metal',
        'Upper metal-shell support only; no tie on socket or solder',
        'Cradle for insulated output leads, away from pads',
        '3.25 x 2.0 mm transverse tunnel for an ordinary 2.5 mm wire tie',
    }
    load_path = [op for op in power.stops_and_leads() if op['params'].get('name') in keep]
    assert len(load_path) == len(keep)
    # The wider pad couples the narrow spine to both shell uprights.
    ops += load_path

    # One overhead tab per board, clear of the board face and of the 4R7
    # inductor on the Mini560. Both contact FR4 only after free upward travel.
    for label, mid, top in [('PD', d1.Y_REAR-34.55, d1.PD_HIGH),
                            ('Mini560', (d1.Y_B+d1.Y_F)/2, d1.B_HIGH)]:
        ops += [block(base.LID, 'join', -79.50, mid-1.50, top+1.20,
                      -77.11, mid+1.50, power.LID_ROOT, f'{label} keeper root in solid roof strip'),
                block(base.LID, 'join', -77.98, mid-1.50, top+power.UP_GAP,
                      -77.11, mid+1.50, top+1.34, f'{label} keeper over bare top edge')]
    return d26.shift_y(ops, d26.POWER_DY)


def modules():
    ops = power.module_gauges()
    extended = 0
    for op in ops:
        p = op['params']; name = p.get('body_name')
        if name in (power.PD, power.CHIPS[0], power.BACKS[0]):
            p['corner'][1] -= PD_LENGTH_ALLOWANCE
            p['width'] += PD_LENGTH_ALLOWANCE
            extended += 1
    assert extended == 3
    return d26.shift_y(ops, d26.POWER_DY)


def groups():
    peg_registers = d26.peg_and_register()[6:]
    assert len(peg_registers) == 6  # Two peg profiles only, no Mac collars.
    stops = d26.retain()
    fork, = [op['params'] for op in stops if op['params'].get('name', '').startswith('One broad axial fork')]
    # One fork now provides the axial *and* upward reaction of the carrier.
    fork['corner'][2] -= .30
    fork['height'] += .30
    return [
        ('D2.6 chassis with flat Mac seating rings', chassis()),
        ('Two-pin carrier and PCB clearance gauges', carrier() + modules()),
        ('D2.6 rear panel and guides', d26.panel() + d26.mount()),
        ('Two unchanged power peg profiles', peg_registers),
        ('D2.6 USB-C axis and shell-only loads', d26.power_nose() + stops),
    ]
