"""Shared cable gauges and combined D2.1 rear report on the exported meshes."""
import json

import rear
import check_d1 as d

LIMIT = .002
rect, rod, desk, k, q = d.rect, d.rod, d.desk, d.k, d.q


def cable_gauges():
    # These are exactly the OLD full rectangular boots at their original start
    # planes. Do not move the shoulders back to get a successful clearance.
    specs = json.loads((d.r.v.old.C2/'layout-validation.json').read_text())['assumed_plugs_mm']
    gauges = {}
    for name, spec in specs.items():
        x,z = spec['xz_center']; y0,y1 = spec['y']
        if 'diameter' in spec:
            body = rod(x,0,0,spec['diameter'],y1-y0).rotate([-90,0,0]).translate([0,y0,z])
        else:
            w,h = spec['width_height']
            body = rect([x-w/2,y0,z-h/2], [x+w/2,y1,z+h/2])
            if name.startswith('PD '):
                body = k.placed(body)
        gauges[name] = desk(body)
    return gauges


def assess(parts,src):
    from check_mount_d21 import assess as check_mount
    from check_ports_d21 import assess as check_ports
    mount,ports=check_mount(parts,src),check_ports(parts,src)
    assert not mount['failures'] and not ports['failures']
    return {'revision':'D2.1','failures':[], 'comparisons':mount['comparisons']+ports['comparisons'],
            'mount':mount,'ports':ports,'physical_status':'NOT TESTED'}


if __name__=='__main__':
    from build_d2 import OUT,FILES,SOURCE_IDS,dump
    parts=k.load_parts(OUT,FILES)
    src={n:desk(s) for n,s in k.refs().items() if int(n.split('_')[-1]) in SOURCE_IDS}
    result=assess(parts,src)
    dump(OUT/'rear-fit.json',result)
    print('D2.1 rear: mount',result['mount']['comparisons'],'ports',result['ports']['comparisons'])
