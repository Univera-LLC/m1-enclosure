"""Independent checks on the eight D2.1 port profiles as exported, in desk mm."""
import itertools
import numpy as np

import rear
import check_rear_d2 as old

d,md,k,q,rect = old.d,old.d.md,old.k,old.q,old.rect
CENTRES={'A1':(49.90,22.),'A2':(32.70,22.),'HDMI':(-1.525,22.10),'TB1':(-19.05,22.),
         'TB2':(-33.70,22.),'audio':(41.30,32.20),'RJ':(-64.65,23.),'PD':(-79.925,22.20)}
GAUGE_NAME={'A1':'USB-A 1','A2':'USB-A 2','HDMI':'HDMI','TB1':'TB1','TB2':'TB2',
            'audio':'Audio','RJ':'RJ45','PD':'PD boot'}
LIMIT=.002


def pin(poly,x,y):
    a=np.asarray(poly); b=np.roll(a,-1,axis=0); mask=(a[:,1]>y)!=(b[:,1]>y)
    return bool(np.count_nonzero(x < a[mask,0]+(b[mask,0]-a[mask,0])*(y-a[mask,1])/(b[mask,1]-a[mask,1]))%2)


def loops(section):
    # Slice is in [desk X,-desk Z]. A negative winding is an actual hole.
    shapes={}
    for vertices in section.to_polygons():
        a=np.asarray(vertices); n=np.roll(a,-1,axis=0)
        if (a[:,0]*n[:,1]-a[:,1]*n[:,0]).sum()>=0: continue
        centres=[name for name,(x,z) in CENTRES.items() if pin(a,x,-z)]
        if not centres: continue  # an engraved legend counter, outside all eight sockets
        assert len(centres)==1 and centres[0] not in shapes,centres
        shapes[centres[0]]=a
    assert shapes.keys()==CENTRES.keys(),set(CENTRES)-set(shapes)
    return shapes


def gap(a,b):
    # Distinct rings; their closest polygon edges meet an endpoint of at
    # least one of the two segments. Check both directions, not just vertices.
    def directed(v,e):
        seg=np.roll(e,-1,axis=0)-e; delta=v[:,None,:]-e[None,:,:]
        t=np.clip(np.einsum('ijk,jk->ij',delta,seg)/np.maximum((seg*seg).sum(axis=1),1.e-16),0,1)
        return np.linalg.norm(delta-t[:,:,None]*seg[None,:,:],axis=-1).min()
    return float(min(directed(a,b),directed(b,a)))


def swept_profile(name,w,h,r,y0,y1):
    x,z=CENTRES[name]
    if name=='audio': return d.rod(x,0,0,w,y1-y0).rotate([-90,0,0]).translate([0,y0,z])
    if name=='HDMI' and r:
        pts=[(-w/2,-h/2),(w/2,-h/2),(w/2,h/2-r),(w/2-r,h/2),(-w/2+r,h/2),(-w/2,h/2-r)]
        section=md.CrossSection([pts])
    elif r:
        section=md.CrossSection.square([w-2*r,h-2*r],True).offset(r,md.JoinType.Round,circular_segments=96)
    else: section=md.CrossSection.square([w,h],True)
    return section.extrude(y1-y0).rotate([90,0,0]).translate([x,y1,z])


def assess(parts,src):
    p=parts[rear.PANEL]; pcb=src['SOURCE_20']; obstacles={**parts,**src}
    comparisons={}
    def check(label,pairs):
        bad={}; count=0
        for n,s,m,t in pairs:
            count+=1; v=k.volume(s,t)
            if v>LIMIT:bad[n+' / '+m]=v
        if bad:raise ValueError(label,bad)
        comparisons[label]=count
    def cross(sources,fixed):return ((n,s,m,t) for n,s in sources.items() for m,t in fixed.items())

    # Separate datum evidence: only TB2 has an actual pocket in the author's
    # merged SOURCE block. The seven shaped passages are inherited DESIGN
    # from the independent D1 inlay; no physical connector scan is inferred.
    lips={}
    for n,(x,z) in CENTRES.items():
        if n=='PD':lips[n]=57.09;continue  # ASSUMED D1 commercial shell
        field=pcb^rect([x-2,55,z-2],[x+2,57,z+2]);assert field.volume()>.5,n
        yl=float(q.bounds(field)[1,1]); assert abs(yl-(56.35 if n.startswith('TB') else 56.45))<.006,(n,yl)
        lips[n]=round(yl,3)
    previous=k.load_parts(d.OUT,{'inlay':[d.r.SKIN]})[d.r.SKIN]
    historical=loops(previous.rotate([90,0,0]).project())
    # Restrict the proof of the profile sections to the port field. Side entry
    # ends and the independent base track's lower rebate may legitimately vary.
    field=(p^rect([-84.64,56.5,12.50],[60.35,60.0,36.76])).rotate([90,0,0])
    m=field.to_mesh64(); verts=np.asarray(m.vert_properties)[:,:3]; levels=np.unique(np.round(verts[:,2],5))
    assert abs(levels[0]-57.35)<.003 and abs(levels[-1]-59.15)<.003
    tris=verts[np.asarray(m.tri_verts)]; normals=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]); mag=np.linalg.norm(normals,axis=1)
    nz=np.abs(normals[:,2])/np.maximum(mag,1e-16)
    assert np.all((nz<.001)|(nz>.999)),'Nonparallel port wall: interval slices alone would not prove continuous shape.'
    cuts=[field.slice((a+b)/2) for a,b in zip(levels,levels[1:])]; rings=[loops(s) for s in cuts]
    assert len(cuts[0].to_polygons())==9  # one piece plus eight distinct through apertures
    gained=[round((b-a).area(),6) for a,b in zip(cuts,cuts[1:])];assert max(gained,default=0)<.002
    def webb(r):return {a+'/'+b:round(gap(r[a],r[b]),3) for a,b in itertools.combinations(r,2)}
    inside,outside=rings[0],rings[-1]; lower,upper=webb(inside),webb(outside)
    assert min(lower.values())>3.50 and min(upper.values())>2.10,(lower,upper)
    sizes={}; original_diff={}
    for n in CENTRES:
        sizes[n]={'inner_xz_span':np.ptp(inside[n],axis=0).round(3).tolist(),
                  'outer_xz_span':np.ptp(outside[n],axis=0).round(3).tolist()}
        if n=='PD':continue
        a=md.CrossSection([inside[n][::-1]]);b=md.CrossSection([historical[n][::-1]])
        original_diff[n]=round((a-b).area()+(b-a).area(),5)
        assert original_diff[n]<.22,(n,original_diff[n]) # two independent polygon tessellations
    # Both desk-upper HDMI edges are clipped; both lower corners remain full.
    for poly in (inside['HDMI'],outside['HDMI']):
        lo,hi=poly.min(axis=0),poly.max(axis=0); edges=np.roll(poly,-1,axis=0)-poly
        nxt=np.roll(edges,1,axis=0)
        assert np.count_nonzero(np.abs(edges[:,0]*nxt[:,1]-edges[:,1]*nxt[:,0])>.0001)==6
        for x in (lo[0]+.25,hi[0]-.25):assert not pin(poly,x,lo[1]+.25) and pin(poly,x,hi[1]-.25)
    # Verify the two levels of the stepped RJ, using the key width change.
    assert pin(inside['RJ'],-64.65,-17.30) and not pin(inside['RJ'],-70.0,-17.30)

    full=old.cable_gauges(); wide={n:full[key] for n,key in GAUGE_NAME.items()}
    # Selection-independent worst shoulder, and individually defined slim
    # profile scenarios. The slim dimensions are hypothetical, not cable SKUs.
    slim_specs={'A1':(14.40,6.80,.75),'A2':(14.40,6.80,.75),'HDMI':(16.0,6.55,1.54),
                'TB1':(10.10,4.48,2.21),'TB2':(10.10,4.48,2.21),'RJ':(13.66,8.64,.60)}
    slim={n:swept_profile(n,*v,55.0,84.0) for n,v in slim_specs.items()}
    slim.update({n:wide[n] for n in ('audio','PD')})
    neck={'A1':(12.,4.5,0),'A2':(12.,4.5,0),'HDMI':(13.80,4.40,0),'TB1':(8.32,2.62,0),
          'TB2':(8.32,2.62,0),'audio':(3.5,0,0),'RJ':(11.8,7.5,0),'PD':(2.55,8.35,0)}
    old_hits={n:k.volume(s,p) for n,s in wide.items()}
    assert all(v>.1 for n,v in old_hits.items() if n!='PD') and old_hits['PD']<=LIMIT
    distances={n:{} for n in CENTRES}; placed_for_finger=None
    for family,shapes in [('wide',wide),('slim',slim)]:
        for play in (0.,.30):
            installed=p.translate([0,play,0]); all_here={**obstacles,rear.PANEL:installed}; placed={}
            for n,boot in shapes.items():
                from_y=q.bounds(boot)[0,1]; span=boot.translate([0,55.0-from_y,0]); hit=span^installed
                assert hit.volume()>.02,(n,family)
                contact=float(q.bounds(hit)[1,1])
                expected={'audio':58.15,'PD':58.43}.get(n,59.15 if family=='wide' else 58.35)
                assert abs(contact-expected-play)<.007,(n,family,contact,expected)
                shoulder=contact+.30; tag=family+('_aft_rail_limit' if play else '_nominal')
                distances[n][tag]=round(shoulder-lips[n],3)
                placed[n+' shoulder']=boot.translate([0,shoulder-from_y,0])
                placed[n+' neck']=swept_profile(n,*neck[n],lips[n]+.025,shoulder)
            key=family+', '+('panel at aft limit' if play else 'nominal panel')
            check(key+': eight necks and shoulders vs installed bodies',cross(placed,all_here))
            check(key+': plugs against other ports',((n,s,m,t) for (n,s),(m,t) in itertools.combinations(placed.items(),2) if n.split()[0]!=m.split()[0]))
            if family=='wide' and play:placed_for_finger=placed

    # Tab narrows to fit through the profiled key. Beyond the plate the large
    # 13-mm rectangular corridor starts at the aft face plus 0.30. Record the
    # old conservative from-Y58.50 tab intersection separately, do not pass it.
    def slice_tab(y,low,high):return rect([-67.55,y,low],[-61.75,y+.025,high])
    tab=md.Manifold.batch_hull([slice_tab(56.48,18.55,19.70),slice_tab(59.48,17.34,19.30)])
    tab+=md.Manifold.batch_hull([slice_tab(59.48,17.34,19.30),slice_tab(65.2,13.0,18.1)])
    latch={'narrow spring through key':tab,'wide tab beyond face':rect([-71,59.75,12.0],[-58,86,15.50]),
           'finger on external tab':rect([-71,60.65,3.4],[-58,80.65,15.4])}
    old_tab=rect([-71,58.50,12],[-58,86,15.50]); old_tab_hit=k.volume(old_tab,p); assert old_tab_hit>.1
    check('RJ latch path, finger, desk and all other occupied ports at aft limit',
          cross(latch,{**obstacles,rear.PANEL:p.translate([0,.30,0]),
                       'desk':rect([-150,-150,-4],[150,150,0]),
                       **{n:s for n,s in placed_for_finger.items() if not n.startswith('RJ ')}}))
    shell=rect([-81.55,49.74,17.73],[-78.30,57.09,26.67]);assert k.volume(shell,p)<=LIMIT
    bearing={}
    for key,x0,x1 in [('left',-81.55,-81.15),('right',-78.70,-78.30)]:
        patch=p^rect([x0,57.34,17.72],[x1,58.44,26.68]);bearing[key]=k.volume(shell.translate([0,.39,0]),patch)
        assert bearing[key]>.12 and k.volume(shell.translate([0,.69,0]),patch.translate([0,.30,0]))>.12
    bed=p.rotate([90,0,0]); footprint=bed.slice(57.351).area(); projected=bed.project().area()
    assert footprint>4000 and footprint/projected>.97,(footprint,projected)
    return {'scope':'Desk mm, exported geometry only. No measured Mac, cable, engagement depth or printing force.',
            'failures':[],'comparisons':sum(comparisons.values()),'checks':comparisons,'source_socket_lips_y_mm':lips,
            'provenance':'SOURCE 20 provides the face datums; most socket fronts are closed in the author mesh. The seven native aperture profiles were independently compared with the D1 inlay; D1/D2 commercial PD shell and plug dimensions are ASSUMED.',
            'individual_port_sizes_mm':sizes,'D1_native_through_section_symmetric_differences_mm2':original_diff,
            'thin_web_inner_mm':min(lower.values()),'thin_web_exterior_mm':min(upper.values()),
            'widths_at_the_exterior_mm':{s:upper.get(s,upper.get('/'.join(reversed(s.split('/'))))) for s in ('A1/A2','HDMI/TB1','TB1/TB2','RJ/PD')},
            'seated_socket_lip_to_shoulder_required_mm_includes_0.30_clearance':distances,
            'slim_hypotheses_W_H_cornerR_or_HDMI_clip_mm':slim_specs,'original_full_shoulder_overlap_mm3_at_D2_planes':old_hits,
            'RJ_release':{'old_13mm_tab_at_y58.50_intersection_mm3':old_tab_hit,'accepted_13mm_tab_start_y_at_aft_panel_mm':59.75,
                          'tapered_tab_width_through_key_mm':5.8,'finger_gauge_start_y_mm':60.65},
            'PD_shell_bearing_challenge_at_0.39mm_mm3':bearing,
            'FDM_geometry':{'n_independent_through_ports':8,'n_independent_exterior_mouths':8,
                            'intact_profiles_in_each_port_field_section':[len(r) for r in rings],
                            'initial_bed_contact_mm2':round(footprint,2),'projected_mm2':round(projected,2),
                            'unsupported_area_in_port_field_between_sections_mm2':gained}}
