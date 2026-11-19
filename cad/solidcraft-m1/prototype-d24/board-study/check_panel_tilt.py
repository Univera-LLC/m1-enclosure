"""Rigid-body rocking at the front: independent exported-triangle / support-plane check.

Model the continuous seated branch: both installed panel ends remain in their
grooves; when closed both cams and lid pads remain engaged. No elastic
deflection, friction, manufacturing or assumed press-fit is used.
"""
from pathlib import Path
import itertools
import json
import sys
import numpy as np
from scipy.optimize import linprog
from scipy.spatial.transform import Rotation
import trimesh as tm
from build_board import HERE, sha, registered_body, manifold_from, md

REV=HERE.parent; P=REV/'geometry'
C=np.array([-8.16,55.40,24.95])
TO_DESK=np.array([[1000.,0,0,0],[0,0,-1000.,0],[0,1000.,0,0],[0,0,0,1]])


def read_solids(group):
    sc=tm.load_scene(P/(group+'.glb'),process=False);result={}
    for n in sc.graph.nodes_geometry:
        pose,k=sc.graph[n];m=sc.geometry[k].copy();m.apply_transform(TO_DESK@pose)
        result[n]=manifold_from(m.triangles)
    return result


def samp(m,ax,v,p0,p1):
    p=list(v);q=list(v);p[ax]=p0;q[ax]=p1
    return [float(h.position[ax]) for h in m.ray_cast(p,q)]


def check_near(m,ax,pt,t,a=3.0):
    matches=samp(m,ax,pt,t-a,t+a)
    assert len(matches) and min(abs(s-t) for s in matches)<.00006,(pt,ax,t,matches)


def measurements(panel,base,lid):
    # Each inequality is n·(p'-p)<=gap. Use points well within the overlapping
    # contact faces, not at the edges. Read each surface independently.
    rows=[];obs={}
    def add(tag,pt,n,gap):
        rows.append((np.array(pt),np.array(n),gap))
        obs.setdefault(tag,[]).append({'p_mm':pt,'normal':n,'free_mm':round(gap,5)})
    for x in (-88.32,73.31):
        for z in (9.10,10.0,38.50):
            probe=[x,55.5,z];by=samp(base,1,probe,53,58);py=samp(panel,1,probe,53,58)
            yl=min(py);yu=max(py);near1=min(by,key=lambda v:abs(v-yl)); near2=min(by,key=lambda v:abs(v-yu))
            assert abs(near2-yu)<.00006 and .18<yl-near1<.25
            add('outboard groove planes',[x,yu,z],[0,1,0],max(near2-yu,0.))
            add('inboard groove planes',[x,yl,z],[0,-1,0],yl-near1)
    for x in (-85.82,69.50):
        YY=[]
        for z in (9.6,11.0):
            pp=[x,55.,z]; b=max(samp(base,1,pp,53.,56.)); y=min(samp(panel,1,pp,53.8,56.8))
            assert abs(y-b)<.00006
            YY.append((z,y,b))
        slope=-(YY[1][2]-YY[0][2])/(YY[1][0]-YY[0][0]);assert abs(slope-.20)<.00004
        for z,y,b in YY:add('two Y/Z ramps at the base',[x,y,z],[0,-1,-slope],max(y-b,0.))
        for z in (40.05,40.80):
            pt=[x,55.2,z]; sy=min(samp(panel,1,pt,54.5,56.8));by=max(samp(lid,1,pt,54.4,56.1))
            assert abs(sy-by-.080)<.00004
            # Upper stop face must remain engaged throughout the computed local
            # X/Z excursions. Check an actual 0.5 × 0.5 mm footprint around it.
            for dx,dz in itertools.product((-.25,0,.25),(-.25,0,.25)):
                check_near(lid,1,[x+dx,by,z+dz],by)
            add('inner upper faces of closed lid',[x,sy,z],[0,-1,0],sy-by)
        for y in (55.85,56.13):
            pt=[x,y,9.];lo=min(samp(panel,2,pt,8,13)); bot=max(samp(base,2,pt,7,11))
            hi=max(samp(panel,2,pt,38.4,42.8)); roof=min(samp(lid,2,pt,40.61,42.8))
            assert abs(lo-bot)<.00006 and abs(roof-hi-.20)<.00006
            add('horizontal sill',[x,y,lo],[0,0,-1],max(lo-bot,0.))
            add('horizontal closed lid',[x,y,hi],[0,0,1],roof-hi)
    # On either side of the two small upper cutouts the full thickness of
    # the panel, not just the outboard half at the pad, is below the lid.
    # These four witnessed roof points enclose every socket in plan.
    for x,y in itertools.product((-84.00,71.13),(54.67,56.29)):
        pt=[x,y,41.];hi=max(samp(panel,2,pt,39.6,42.8));roof=min(samp(lid,2,pt,40.61,42.8))
        assert abs(roof-hi-.20)<.00006
        add('horizontal closed lid on either side of upper slots',[x,y,hi],[0,0,1],roof-hi)
    x=-85.82;y=54.68;z=10.2;pt=[x,y,z]
    bb=samp(base,0,pt,x-3.3,x+3.3); pp=samp(panel,0,pt,x-2.9,x+2.9)
    l,r=min(bb),max(bb);pl=min(pp,key=lambda v:abs(v-l));pr=min(pp,key=lambda v:abs(v-r))
    assert abs(l-pl-.075)<.00006 and abs(pr-r-.075)<.00006
    add('lower X pocket left',[pl,y,z],[1,0,0],l-pl)
    add('lower X pocket right',[pr,y,z],[-1,0,0],pr-r)
    return rows,obs


def jac(p):
    x,y,z=np.asarray(p)-C
    return np.column_stack((np.eye(3),np.array([[0,z,-y],[-z,0,x],[y,-x,0]])))


class Envelope:
    def __init__(self,rows):
        self.A=np.asarray([n@jac(p) for p,n,g in rows])
        self.rows=rows;self.trace=[]
        # Rodrigues: exact displacement = t + w × (p-C) + E(p), with
        # w = axis*sin(theta) and |E(p)| <= |p-C|*(1-cos(theta)).
        # Bound the connected nominal branch: if it cannot reach 1 degree
        # from below it cannot leave the starting attitude cell continuously.
        theta=np.radians(1.)
        for _ in range(12):
            self.theta=theta
            self.lims=np.array([g+self.err(p)*np.linalg.norm(n)+.000015 for p,n,g in rows])
            w=[]
            for i in range(3):
                obj=np.eye(6)[3+i];w.append(max(self.max(obj),self.max(-obj)))
            nxt=np.arcsin(np.linalg.norm(w))
            self.trace.append([round(float(np.degrees(theta)),8),round(float(np.degrees(nxt)),8)])
            assert nxt<theta+.00000001
            if theta-nxt<.000000015:break
            theta=nxt
        self.angular=np.degrees(np.arcsin(w))
    def err(self,p):return np.linalg.norm(np.asarray(p)-C)*(1.-np.cos(self.theta))
    def max(self,obj):
        v=linprog(-obj,A_ub=self.A,b_ub=self.lims,bounds=[(None,None)]*6,method='highs')
        assert v.success,v.message
        return -v.fun
    def at(self,p):
        J=jac(p);e=self.err(p)
        return np.array([[-self.max(-j)-e for j in J],[self.max(j)+e for j in J]])


def rigid(m,rx,dy,dz):
    # Exact transform about the lower outside edge, no linearization.
    O=np.array([0,56.4,8.7]);r=Rotation.from_euler('x',rx,degrees=True).as_matrix()
    return m.transform(np.column_stack((r,O-r@O + [0,dy,dz])))


def finite_faces(env,obs,base,lid):
    # A plane inequality only applies while the moving witness lies over
    # actual fixed material. Prove each whole projected displacement box
    # lies in the union of the exported, correctly oriented planar triangles.
    # This also closes the continuation argument: before a seated panel could
    # escape an engaged face, it would have to reach its footprint boundary.
    meshes={}
    for tag,m in [('base',base),('lid',lid)]:
        f=m.to_mesh64();t=np.asarray(f.vert_properties)[:,:3][np.asarray(f.tri_verts)]
        norms=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);meshes[tag]=(t,norms)
    proved=0;unused=0.;cache={}
    for desc,measurements_solid in obs.items():
        kind='lid' if 'lid' in desc else 'base'
        t,norms=meshes[kind]
        for row in measurements_solid:
            p=np.asarray(row['p_mm']);n=np.asarray(row['normal']);level=n@p+row['free_mm'];drop=np.argmax(abs(n));axes=np.array([i for i in range(3) if i!=drop])
            key=(kind,str(n.round(4)),round(level,4))
            if key not in cache:
                flat=(np.max(np.abs(t@n-level),axis=1)<.00012)&(norms@n < -1.e-9)
                projected=np.take(t[flat],axes,axis=2)
                assert len(projected)>0,(desc,n,level)
                a=projected[:,1]-projected[:,0];b=projected[:,2]-projected[:,0]
                rev=a[:,0]*b[:,1]-a[:,1]*b[:,0]<0
                projected[rev]=projected[rev,::-1]
                cache[key]=md.CrossSection(list(projected))
            dif=env.at(p);lo=p[axes]+dif[0,axes]-.001;hi=p[axes]+dif[1,axes]+.001
            test=md.CrossSection.square(hi-lo).translate(lo)-cache[key]
            miss=test.area();assert miss<.0000005,(desc,row,miss,lo,hi)
            unused=max(unused,miss);proved+=1
    return {'planes_verified_over_entire_projected_excursion':proved,'max_uncovered_area_mm2':round(unused,8),'extra_footprint_margin_mm':.001}


def run():
    panel=next(iter(read_solids('panel').values()));base=next(iter(read_solids('base').values()));lid=next(iter(read_solids('lid').values()))
    rows,obs=measurements(panel,base,lid);env=Envelope(rows)
    allports=json.loads((HERE/'port-contract.json').read_text(encoding='utf-8'))['ports']
    boxes={n:np.array([a for ring in q['outer_loops_xz_mm'] for a in ring]) for n,q in allports.items()}
    boxes['PD']=np.asarray([[-79.925-1.625,22.20-4.47],[-79.925+1.625,22.20+4.47]])
    per={};per_exact={}
    for n,ps in boxes.items():
        # Bounding rectangles include every point of all curved contours, at
        # any depth through the 1.80 mm plate. An affine functional reaches
        # its extreme at a corner, and the Euclidean error bound is convex.
        a=ps.min(axis=0)-.38;b=ps.max(axis=0)+.38
        vals=[env.at([x,y,z]) for x,y,z in itertools.product((a[0],b[0]),(54.60,56.40),(a[1],b[1]))]
        rr=np.array([np.min([v[0] for v in vals],axis=0),np.max([v[1] for v in vals],axis=0)])
        per_exact[n]=rr
        per[n]=(np.stack([np.floor(rr[0]*1e4),np.ceil(rr[1]*1e4)])/1e4).tolist()
    whole=np.stack((np.min([v[0] for v in per_exact.values()],axis=0),np.max([v[1] for v in per_exact.values()],axis=0)))
    # Also check footprints at which guide planes enter the LP. Upper pads
    # were sampled with a 0.25 mm margin in both X and Z.
    for row in obs['inner upper faces of closed lid']:
        mov=env.at(row['p_mm']);assert np.max(np.abs(mov[:,[0,2]]))<.25
    face_check=finite_faces(env,obs,base,lid)
    fixed={'base':base,'lid':lid,'Mac':registered_body()}
    for name in ('socket','socket_insert','saddle','boards','population'):
        fixed.update(read_solids(name))
    pd_face=max(solid.bounding_box()[4] for solid in read_solids('socket').values());assert abs(pd_face-56.40)<.00005
    axial={}
    for n,(a,b) in per.items():
        lip=pd_face if n=='PD' else allports[n]['source_lip_y_mm'];nom=56.40-lip
        axial[n]=[round(nom+a[1],4),round(nom+b[1],4)]
    example={}
    for label,rx,dy,dz in [('nominal',0,0,0),('closed nonzero pitch',.11,-.001,.105),('loose until lid fitted',.34,-.0008,.175),('0.22 mm full-groove pitch challenge',float(np.degrees(np.arcsin(.22/(41.2-8.7)))),0,.18)]:
        candidate=rigid(panel,rx,dy,dz)
        hits={n:round(max(0.,(candidate^part).volume()),6) for n,part in fixed.items()}
        if label in ('nominal','closed nonzero pitch'):assert max(hits.values())<.00002,(label,hits)
        elif label=='loose until lid fitted':assert hits['lid']>.001 and max(v for n,v in hits.items() if n!='lid')<.00002,(label,hits)
        else:assert hits['lid']>.001,(label,hits)
        example[label]={'pitch_deg':round(rx,6),'add_Y_Z_mm':[dy,dz],'upper_edge_outside_face_delta_Y_mm':round(dy-(41.2-8.7)*np.sin(np.radians(rx)),6),'intersection_volume_mm3':hits}
    expected=np.array([[-.125,-.085,-.002],[.125,.002,.202]])
    contained=bool((whole[0]>=expected[0]).all() and (whole[1]<=expected[1]).all())
    out={'revision':'D2.4','method':'Exact rigid signed-distance enclosure for planes on the engaged seated branch (linear programming + Rodrigues remainder); whole exported solids for finite-angle witnesses.',
         'assumptions':'Rigid base/lid/plate, fully installed lid on its datum, seated and both groove ends plus wedges engaged. Free panel outside its guides is a different state. Print tolerance, warpage, force, friction and deflection not measured.',
         'geometry_sha256':{n:sha(P/(n+'.glb')) for n in ('base','panel','lid','socket','socket_insert','saddle','boards','population')},
         'station_measurements_and_halfspaces':obs,'finite_support_triangles':face_check,'angle_refinement_degree_in_and_out':env.trace,
         'max_abs_axis_times_sine_angle_deg_small_rigid_bound':env.angular.round(6).tolist(),
         'guard_offered_xyz_mm':expected.tolist(),'all_port_rectangle_excursions_in_guard':contained,'per_port_rectangular_aperture_excursion_xyz_mm':per,
         'facade_y_minus_lip_y_range_mm_positive_if_lip_is_recessed':axial,
         'union_excursion_xyz_mm':(np.stack([np.floor(whole[0]*1e5),np.ceil(whole[1]*1e5)])/1e5).tolist(),'exact_pose_witnesses':example}
    (HERE/'panel-tilt-validation.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print('actual port fields',out['union_excursion_xyz_mm'],'within prior guard?',contained,'witnesses',{n: v['intersection_volume_mm3']['lid'] for n,v in example.items()})


if __name__=='__main__':run()
