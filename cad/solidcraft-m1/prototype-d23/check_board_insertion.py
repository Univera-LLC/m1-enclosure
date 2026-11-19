"""Panel-first D2.3 assembly: continuous board travel, in desk coordinates (mm)."""
import numpy as np
import manifold3d as md

# Relative to the fully seated Mac model, +Y points towards the cable ports.
# The short horizontal feed occurs with the two integral registering lips below the PCB.
APPROACH_Y = -2.0
ALIGN_Z = 1.0
OPEN_Z = 38.0
TOL_VOLUME = .00002


def bounds(solid):
    return np.asarray(solid.bounding_box()).reshape(2, 3)


def block(lo, hi):
    return md.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())


def axial_cover(mobile, fixed, start, end):
    """Prove the whole translation by projecting closed slabs, including both endpoints.

    Express each move along positive local Z (reverse the path if necessary).
    Every point of material in a slab, during the whole move, lies inside the
    extrusion of that slab's complete XY projection. A broad cover that hits a
    fixed obstacle is subdivided; it can never certify clearance by missing an
    intermediate pose. Inside a true penetration the smallest cover also fails.
    """
    a,b=np.asarray(start,float),np.asarray(end,float)
    axes=np.flatnonzero(np.abs(a-b)>.000001); assert len(axes)==1
    axis=axes[0]; assert axis in (1,2)
    if b[axis]<a[axis]: a,b=b,a
    step=float(b[axis]-a[axis])
    shape=mobile.translate(a.tolist())
    if axis==1:
        shape=shape.rotate([90,0,0])
        fixed=fixed.rotate([90,0,0])
    limits=bounds(shape); mob_min,mob_max=limits
    target_lo,target_hi=bounds(fixed)
    high=mob_max.copy(); high[2]+=step
    if np.any(np.minimum(high,target_hi)-np.maximum(mob_min,target_lo)<=.000001):
        return dict(slabs=0,overlap_bound_mm3=0.)
    # Subtract the reach of the whole move before clipping the original mesh;
    # all moving material that could ever touch fixed is retained.
    lo=np.maximum(mob_min,target_lo-[0.,0.,step])-.001
    hi=np.minimum(mob_max,target_hi)+.001
    source=shape ^ block(lo,hi)
    if source.is_empty():return dict(slabs=0,overlap_bound_mm3=0.)
    lo2,hi2=bounds(source); xy0,xy1=lo2[:2]-.002,hi2[:2]+.002
    # Clip the static geometry, too. Eight dense radiator sections should not
    # be intersected with unrelated geometry on the far side of the case.
    fixed=fixed ^ block(lo2-.002,hi2+[.002,.002,step+.002])
    if fixed.is_empty():return dict(slabs=0,overlap_bound_mm3=0.)
    mesh=source.to_mesh64()
    elevations=np.asarray(mesh.vert_properties)[np.asarray(mesh.tri_verts),2]
    # Register support-contact planes exactly (e.g. the underside of the
    # board ring). Spanning such a plane with a coarse slab could report a
    # penetration into the base even for a true face-to-face landing.
    flat=elevations[np.ptp(elevations,axis=1)<1.e-9,0]
    knots=np.unique(flat[(flat>lo2[2]+.000001)&(flat<hi2[2]-.000001)])
    intervals=[(lo2[2],hi2[2])]
    leaf=0; residual=0.
    while intervals:
        z0,z1=intervals.pop(); h=z1-z0
        if h<1e-8:continue
        slab=source ^ block(np.r_[xy0,z0],np.r_[xy1,z1])
        if slab.is_empty():continue
        footprint=slab.project()
        if footprint.is_empty():continue
        approx=footprint.extrude(h+step).translate([0.,0.,z0])
        possible=approx ^ fixed
        overlap=max(0.,float(possible.volume()))
        if overlap>1.e-9:
            # An upper slab boundary can contain an exactly coplanar support
            # face of zero volume. Bound the *opposite* sweep as well: any
            # colliding material must start in the inverse extrusion of the
            # projected possible-contact region. This preserves that intentional
            # face contact without artificially thickening the board below it.
            inverse=0.
            for patch in possible.decompose():
                if patch.is_empty():continue
                zlo,zhi=bounds(patch)[:,2]
                witness=patch.project().extrude(zhi-zlo+step).translate([0.,0.,zlo-step])
                inverse+=max(0.,float((slab^witness).volume()))
            overlap=min(overlap,inverse)
        if overlap<1.e-9 or h<=.003:
            leaf+=1;residual+=overlap
            if residual>TOL_VOLUME:
                raise AssertionError((axis,a.tolist(),b.tolist(),'possible collision in continuous travel',
                                      round(residual,7),bounds(possible).round(4).tolist()))
        else:
            mid=(z0+z1)/2
            candidates=knots[(knots>z0+1.e-6)&(knots<z1-1.e-6)]
            if len(candidates):mid=candidates[np.argmin(np.abs(candidates-mid))]
            intervals.extend([(z0,mid),(mid,z1)])
    return dict(slabs=leaf,overlap_bound_mm3=round(residual,9))


def assess(parts,actual):
    """Board screws, lid with its screws, and power saddle are removed."""
    panel_name,=[n for n in parts if n.endswith('_IO_PLATE')]
    fixed={n:s for n,s in parts.items() if 'MONO_BASE' in n or 'BLANK' in n or 'ADHESIVE_FOOT' in n or n==panel_name}
    assert len([n for n in fixed if 'MONO_BASE' in n])==1
    assert len(actual)==3 and any('23 crests' in n for n in actual)
    pos=[[0.,APPROACH_Y,OPEN_Z],[0.,APPROACH_Y,ALIGN_Z],[0.,0.,ALIGN_Z],[0.,0.,0.]]
    open_clearance=round(min(bounds(s)[0,2] for s in actual.values())+OPEN_Z-max(bounds(s)[1,2] for s in fixed.values()),4)
    assert open_clearance>1
    # A single nonconvex union of every allowed *seated* panel pose. A board
    # path that clears this shape clears each combination of guide play,
    # including all intermediate positions. No possibly moving counters/PCB
    # are allowed to carry the plate with them.
    play_bounds=np.array([[-.075,-.18,0.],[.075,.17,.30]])
    panel_guard=parts[panel_name].minkowski_sum(block(*play_bounds))
    assert panel_guard.volume()>parts[panel_name].volume() and (parts[panel_name]-panel_guard).volume()<TOL_VOLUME
    fixed['Panel with full locator and guide translation']=panel_guard
    for n,part in actual.items():
        for k,target in fixed.items():
            assert (part^target).volume()<=TOL_VOLUME,(n,k,'assembled')
    base=next(s for n,s in fixed.items() if 'MONO_BASE' in n)
    board=next(s for n,s in actual.items() if '23 crests' in n)
    # A real wrong-order challenge: a forward slide with the PCB still
    # resting on the two locating shoulders must collide. Read the heights
    # from the exported mounting surfaces, independent of builder settings.
    unlifted=(board.translate([0.,APPROACH_Y,0.])^base).volume()
    assert unlifted>1.,unlifted
    rings=[]
    for x,y in [(-52.,-34.35),(47.95,-34.35)]:
        lip=base.ray_cast([x+1.70,y,30.],[x+1.70,y,5.])[0].position[2]
        underside=board.ray_cast([x+2.65,y,5.],[x+2.65,y,30.])[0].position[2]
        gap=underside+ALIGN_Z-lip
        assert .28<gap<.32,gap
        rings.append({'axis_xy_mm':[x,y],'lip_z_mm':round(lip,4),'board_underside_z_mm':round(underside,4),
                      'vertical_clearance_during_feed_mm':round(gap,4)})
    phases={}
    for name,a,b in zip(('drop_forward_of_ports','feed_ports_towards_panel','seat_two_board_rings'),pos,pos[1:]):
        verdicts={}
        for n,moving in actual.items():
            for k,target in fixed.items():
                try: verdicts[n+' / '+k]=axial_cover(moving,target,a,b)
                except AssertionError as e:raise AssertionError((name,n,k,*e.args)) from e
        phases[name]=verdicts
    return {'revision':'D2.3','failures':[],'comparisons':sum(len(v) for v in phases.values()),
            'basis':'desk mm; +Y to rear, +Z up; poses relative to fully seated board; same path in reverse for removal',
            'waypoints_xyz_mm':pos,'open_start_clearance_above_highest_fixed_part_mm':open_clearance,
            'board_supports':rings,'counterexample_slide_without_lifting_overlap_mm3':round(unlifted,5),
            'seated_panel_full_translation_bounds_xyz_mm':play_bounds.tolist(),
            'fixed_parts':list(fixed),'moving_board_and_harness':list(actual),'continuous_slab_covers':phases,
            'volume_bound_tolerance_mm3_per_pair':TOL_VOLUME,
            'scope':'Seated panel, nominal and entire XYZ guide/locator play; unpowered, antennas, lid, its fasteners, board screws and power saddle removed. CAD surfaces from board GLB and local harness estimate; no solder/coax/force/warp or physical seating established.'}
