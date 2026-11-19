"""Audit deposited G-code in the exterior-down panel orientation (bed XY = desk XZ)."""
from math import ceil,dist
import numpy as np

CENTRES={'USB-A 1':(49.90,22.),'USB-A 2':(32.70,22.),'HDMI':(-1.525,22.10),
         'TB1':(-19.05,22.),'TB2':(-33.70,22.),'Audio':(41.30,32.20),
         'Ethernet':(-64.65,23.),'PD IN':(-79.925,22.20)}
# The same independent assumed metal necks used in the fit checks. Audio is
# the whole 7.8-mm sleeve; the Ethernet release tongue also has its own gate.
NECKS={'USB-A 1':(12.,4.5),'USB-A 2':(12.,4.5),'HDMI':(13.80,4.40),
       'TB1':(8.32,2.62),'TB2':(8.32,2.62),'Ethernet':(11.8,7.5),'PD IN':(2.55,8.35)}


def deposited(gcode):
    assert 'M83 ;' in gcode and 'G90 ;' in gcode and '\nM82 ' not in gcode
    layers={}; layer=None; role=''; width=None; pos=(0.,0.); path=[]; widths=[]
    def end_path():
        if path:
            assert len(path)>=4 and dist(path[0],path[-1])<.40,('unclosed exterior toolpath',role,path[:1],path[-1:])
            layer['rings'].append((np.array(path),min(widths),max(widths)))
            path.clear();widths.clear()
    for line in gcode.splitlines():
        if line.startswith(';Z:'):
            end_path();z=float(line[3:]);assert z not in layers
            layer=layers[z]={'rings':[],'segments':[]};role='';continue
        if line.startswith(';TYPE:'):
            end_path();role=line[6:];continue
        if line.startswith(';WIDTH:'):
            width=float(line[7:]);continue
        if layer is not None and line.startswith(('G2 ','G3 ','G91 ')):
            raise ValueError('This verifier requires absolute XY linear moves',line)
        if not line.startswith(('G0 ','G1 ')):continue
        values={s[0]:float(s[1:]) for s in line.partition(';')[0].split()[1:] if s[0] in 'XYE'}
        if 'X' not in values and 'Y' not in values:continue
        nxt=(values.get('X',pos[0]),values.get('Y',pos[1]))
        if layer is not None and values.get('E',0)>0 and dist(pos,nxt)>1.e-9:
            assert width and width>0 and 'Bridge' not in role and 'Support' not in role,role
            layer['segments'].append((*pos,*nxt,width))
            if role=='External perimeter':
                if not path:path.append(pos)
                path.append(nxt);widths.append(width)
            else:end_path()
        else:end_path()
        pos=nxt
    end_path()
    return layers


def inside(x,y,poly):
    a=np.asarray(poly);b=np.roll(a,-1,axis=0);hit=(a[:,1]>y)!=(b[:,1]>y)
    return np.count_nonzero(x<a[hit,0]+(b[hit,0]-a[hit,0])*(y-a[hit,1])/(b[hit,1]-a[hit,1]))%2==1


def rect_clearance(segments,centre,dimensions):
    # Exact 2-D capsule/rectangle test. If centreline and core do not cross,
    # their minimum separation is attained at a line end or a rectangle corner.
    a=segments[:,:2]-centre;d=segments[:,2:4]-segments[:,:2]
    extent=np.asarray(dimensions)/2
    lo=np.zeros(len(a));hi=np.ones(len(a));parallel=np.abs(d)<1.e-12
    valid=np.all(~parallel|(np.abs(a)<=extent),axis=1)
    for k in (0,1):
        mask=~parallel[:,k];p=(-extent[k]-a[mask,k])/d[mask,k];q=(extent[k]-a[mask,k])/d[mask,k]
        lo[mask]=np.maximum(lo[mask],np.minimum(p,q));hi[mask]=np.minimum(hi[mask],np.maximum(p,q))
    distance=np.minimum(np.linalg.norm(np.maximum(np.abs(a)-extent,0),axis=1),
                        np.linalg.norm(np.maximum(np.abs(a+d)-extent,0),axis=1))
    d2=(d*d).sum(axis=1)
    for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        v=extent*[sx,sy]-a;u=np.clip((v*d).sum(axis=1)/d2,0.,1.)
        distance=np.minimum(distance,np.linalg.norm(v-u[:,None]*d,axis=1))
    distance[valid&(lo<=hi)]=0
    return float(np.min(distance-segments[:,4]/2))


def empty_rect(segments,centre,dimensions):return rect_clearance(segments,centre,dimensions)>0


def bottom_at(ring,x):
    a=ring;b=np.roll(a,-1,axis=0);cross=(a[:,0]>x)!=(b[:,0]>x)
    vals=a[cross,1]+(b[cross,1]-a[cross,1])*(x-a[cross,0])/(b[cross,0]-a[cross,0]);assert len(vals)==2,(x,vals)
    return float(vals.min())


def max_distance_to_prior(current,prior,spacing=.002):
    # The real open extrusions are used; a seam is never closed artificially
    # for this measurement. Distance to a polyline is 1-Lipschitz, so adding
    # half the maximum sample spacing also bounds the unsampled segment spans.
    ends=prior[:-1];edges=np.diff(prior,axis=0);sq=(edges**2).sum(axis=1)
    bound=0.
    for a,edge in zip(current[:-1],np.diff(current,axis=0)):
        length=np.linalg.norm(edge);n=max(1,ceil(length/spacing));steps=np.arange(n+1)[:,None]/n
        delta=(a+steps*edge)[:,None,:]-ends
        u=np.clip(np.einsum('ijk,jk->ij',delta,edges)/sq,0.,1.)
        distances=np.linalg.norm(delta-u[:,:,None]*edges,axis=2).min(axis=1)
        bound=max(bound,distances.max()+length/(2*n))
    return float(bound)


def assess_toolpaths(gcode,box):
    X0,_,Z0=box['min'];X1,_,Z1=box['max'];offset=np.array([X0+X1,Z0+Z1])/2
    layers=deposited(gcode);counts={};pd={};skin={};clear={};last=None;lastwidth=None;total=0
    for z,layer in layers.items():
        rings=layer['rings'];assert len(rings)==9,('one outline and exactly eight mouths',z,len(rings))
        outer=max(range(9),key=lambda i:np.ptp(rings[i][0][:,0]));outline=rings[outer][0]
        assert np.ptp(outline[:,0])>160 and np.ptp(outline[:,1])>31,z
        origin=(outline.min(axis=0)+outline.max(axis=0))/2-offset
        # A removable panel with a blind locator must keep the first layers
        # uninterrupted over the pocket. Later the same OUTLINE opens up to
        # the bottom edge; there is no ninth hole and no suspended top skin.
        xc=origin[0]-79.925;bottom=bottom_at(outline,xc+5.)
        assert abs(bottom-bottom_at(outline,xc-5.))<.008,z
        depths=[bottom_at(outline,xc+dx)-bottom for dx in (-2.,0.,2.)]
        assert max(depths)-min(depths)<.012 and abs(depths[1]-(0. if z<=.80 else 3.27))<.02,(z,depths)
        skin[z]=round(depths[1],3)
        assigned={}
        for name,(x,h) in CENTRES.items():
            which=[i for i,(ring,_,_) in enumerate(rings) if i!=outer and inside(*(origin+[x,h]),ring)]
            assert len(which)==1,(z,name,which)
            assigned[name]=which[0]
        counts[z]=len(set(assigned.values()));assert counts[z]==8,(z,assigned)
        segments=np.array(layer['segments']);total+=len(segments)
        for name,dims in NECKS.items():
            assert empty_rect(segments,origin+CENTRES[name],dims),(z,name,'deposited line across metal passage')
        # The sill locator, not the loose upper guides, sets the occupied
        # plate's range. This box is every 2.55 x 8.35 metal neck position
        # together for ±0.075 X and 0...+0.30 Z panel displacement.
        registered=rect_clearance(segments,origin+[-79.925,22.05],(2.70,8.65))
        assert registered>=.10,(z,registered,'located PD metal sweep');clear[z]=round(registered,4)
        assert empty_rect(segments,origin+[-64.65,17.85],(5.8,1.0)),(z,'Ethernet latch key')
        a=segments[:,:2];e=segments[:,2:4]-a;delta=(origin+CENTRES['Audio'])-a
        t=np.clip((delta*e).sum(axis=1)/(e*e).sum(axis=1),0,1)
        assert np.all(np.linalg.norm(delta-t[:,None]*e,axis=1)>3.90+segments[:,4]/2),(z,'audio sleeve')
        ring,lower,upper=rings[assigned['PD IN']];assert abs(upper-lower)<.0001
        entry={'centreline_span_mm':np.ptp(ring,axis=0).round(3).tolist(),'extrusion_width_mm':lower}
        if last is not None:
            drift=max_distance_to_prior(ring,last)
            # The new centreline itself lies within the footprint programmed
            # for the previous bead, including around the real seam and corners.
            assert drift<.20 and drift<lastwidth/2,(z,drift,lastwidth)
            overlap=(lastwidth+lower)/2-drift
            entry.update(max_centreline_approach_bound_mm=round(drift,4),min_projected_bead_overlap_mm=round(overlap,4))
        pd[z]=entry;last=ring;lastwidth=lower
    assert len(layers)==9 and min(layers)==.2 and max(layers)==1.8
    return {'distinct_mouths_by_layer_z_mm':counts,'PD_deposited_rings_by_layer_z_mm':pd,
            'PD_max_centreline_approach_bound_mm':max(e.get('max_centreline_approach_bound_mm',0) for e in pd.values()),
            'PD_min_projected_bead_overlap_mm':min(e['min_projected_bead_overlap_mm'] for e in pd.values() if 'min_projected_bead_overlap_mm' in e),
            'PD_full_registered_neck_clearance_to_programmed_bead_mm_by_layer':clear,
            'blind_locator_inset_of_deposited_bottom_outline_mm_by_layer':skin,'full_finish_skin_layers_over_locator':sum(abs(v)<.02 for v in skin.values()),
            'positive_XY_extrusions_checked':total,'unexpected_core_crossings':0,
            'scope':'Actual programmed XY centreline and slicer bead widths, relative E. Includes the first layer and open seams. Melt shape, layer adhesion and strength have not been measured.'}


def matched_mouths(gcode,box):
    return assess_toolpaths(gcode,box)['distinct_mouths_by_layer_z_mm']
