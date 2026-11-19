"""Compare printed panel STLs with both board references in the same desk datum."""
import json
from hashlib import sha256
from pathlib import Path
import trimesh
from check_geometry import qa, rect, owner, BOARD_LABEL

HERE=Path(__file__).resolve().parent
def load_panel(folder):
    cad=json.loads((folder/'cad-validation.json').read_text(encoding='utf8'))
    bbox=cad['bodies'][cad['groups']['panel'][0]]['bbox']
    stl=folder/'print/02-flat-rear-panel.stl'
    solid=qa.k.qa.solid(trimesh.load_mesh(stl,process=False))
    return solid.translate([bbox['min'][0],bbox['min'][2],-bbox['max'][1]]).rotate([90,0,0])
def volume(solid):
    return round(max(0.,float(solid.volume())),5)
def run():
    old=HERE.with_name('prototype-d25')
    revised=load_panel(HERE);previous=load_panel(old)
    registered=owner()[BOARD_LABEL];raw=qa.desk(qa.k.refs()['SOURCE_20'])
    intersection=revised^raw
    zones={n:volume(intersection^rect([x0,53,14],[x1,60,40])) for n,x0,x1 in
           [('TB1 + TB2',-44,-11),('USB-A + audio',20,62),('HDMI',-11,9),('RJ',-76,-54)]}
    inputs=[HERE/'print/02-flat-rear-panel.stl',old/'print/02-flat-rear-panel.stl',HERE/'board-study/mac-board-reference.glb',HERE/'board-study/registered-board.stl']
    inputs += [HERE.parent/'source-analysis'/name for name in ('vertices.npy','faces.npy','face-component-labels.npy')]
    return {'revision':'D2.6','units':'desk mm; intersection volumes in mm3',
            'registered_board_overlap_mm3':{'D2.5':volume(previous^registered),'D2.6':volume(revised^registered)},
            'raw_SOURCE_20_total_overlap_mm3':volume(intersection),'raw_SOURCE_20_zone_overlap_mm3':zones,
            'raw_SOURCE_20_overlap_bounds_mm':list(intersection.bounding_box()) if not intersection.is_empty() else None,
            'scope':'The original SnazzyLabs SOURCE_20 places more material in front of the TB pair than the photo-based D2.6 board. This is a disagreement between models, not an observed collision on the owner board. Check the shared TB shield in a cold fit before printing the full enclosure.',
            'physical_fit':'NOT TESTED','inputs_sha256':{p.relative_to(HERE.parent).as_posix():sha256(p.read_bytes()).hexdigest() for p in inputs}}
if __name__=='__main__':
    result=run()
    (HERE/'reference-crosscheck.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(result['registered_board_overlap_mm3'],result['raw_SOURCE_20_zone_overlap_mm3'])
