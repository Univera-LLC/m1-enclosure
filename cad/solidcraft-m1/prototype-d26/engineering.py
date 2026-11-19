"""Load actual D2.6 exports and bound translations of nonconvex native solids."""
import importlib.util
import itertools
import sys
import numpy as np
import trimesh as tm
import design as s
import check_d1 as qa
from build_d26 import BOARD
sys.path.insert(0,str(s.OUT/'board-study'))
from build_board import registered_body
sys.path.insert(0,str(s.OUT))

spec=importlib.util.spec_from_file_location('d23_continuous_translations',s.D23/'check_board_insertion.py')
sweep=importlib.util.module_from_spec(spec);spec.loader.exec_module(sweep)
md,rect,vol,bounds=qa.md,qa.rect,qa.k.volume,qa.q.bounds
PLAY=np.array([[-s.DX,-.04,0.],[s.DX,0.,s.LIFT]])
BOARD_LABEL='Registered owner Mac, 23 crests and seven photographed connector fronts'

def parts():return qa.k.load_parts(s.OUT,s.FILES)
def optional():return {n:qa.desk(v) for n,v in qa.k.refs().items() if n in ('SOURCE_11','SOURCE_13','SOURCE_14')}
def owner():
    transform=np.array([[1000,0,0,0],[0,0,-1000,0],[0,1000,0,0],[0,0,0,1]])
    sc=tm.load_scene(BOARD,process=False);out={BOARD_LABEL:registered_body()}
    for n in sc.graph.nodes_geometry:
        if '__loom__' in n:
            pose,k=sc.graph[n];m=sc.geometry[k].copy();m.apply_transform(transform@pose);out[n]=qa.k.qa.solid(m)
    assert len(out)==3
    return out

def guide_guard(panel):
    cell=md.Manifold.hull_points([[x,y,z] for x in (-s.DX,s.DX) for y,z in [(0.,0.),(-.04,.20),(0.,.20)]])
    g=panel.minkowski_sum(cell);assert (panel-g).volume()<.00002
    return g

def field_guard(panel):
    cell=rect([-.125,-.085,-.002],[.125,.002,.204])
    return panel.minkowski_sum(cell)

def cross(a,b):return ((i,p,j,q) for i,p in a.items() for j,q in b.items())

def free(label,pairs,tol=.00015):
    n=0;hits={}
    for i,p,j,q in pairs:
        overlap=vol(p,q);n+=1
        if overlap>tol:hits[i+' / '+j]=overlap
    assert not hits,(label,hits)
    return n

def travel(poses,mobile,fixed):
    phases={}
    for i,(a,b) in enumerate(zip(poses,poses[1:])):
        group={}
        for n,p,k,q in cross(mobile,fixed):
            try:result=sweep.axial_cover(p,q,a,b)
            except AssertionError as e:raise AssertionError(('travel phase '+str(i+1),n,k,*e.args)) from e
            group[n+' / '+k]=result
        phases[str(i+1)]=group
    return phases

def shell_at_xz(p,x,z):
    return [round(float(h.position[1]),4) for h in p.ray_cast([x,53,z],[x,58.,z])]
