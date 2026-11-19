"""Static contacts, bounded swept volumes and service gauges on the exported D1 assembly."""
import itertools, json, sys
import numpy as np
from build_d1 import *
import check_rear as qa

rect, rod, desk, k, q, md = qa.rect, qa.rod, qa.desk, qa.k, qa.q, qa.md
LIMIT=.002

def wire(points,radius):
    spheres=[md.Manifold.sphere(radius,16).translate(p) for p in points]
    return md.Manifold.batch_boolean([md.Manifold.batch_hull([a,b]) for a,b in zip(spheres,spheres[1:])],md.OpType.Add)

def positive_cover(parts):
    # Every positive box/cylinder in the carrier is bounded individually. Ignoring drilled holes
    # only enlarges its swept volume. Verify independently that the covers contain the exported solids.
    covers={}
    for op in carriage()+gauges():
        p=op["params"]
        if p.get("operation") not in ("join","new"):continue
        n=p.get("body_name") or p["targets"][0]
        if op["command"]=="solid.box":
            lo=np.array(p["corner"]);size=np.array([p[c] for c in ("length","width","height")]);hi=lo+size
        else:raise ValueError("New positive non-box feature requires a bounding rule",op)
        covers.setdefault(n,[]).append((lo,hi))
    for n in NEW_SCREWS[2:]:
        covers[n]=[q.bounds(parts[n])]
    return covers

def run():
    parts=k.load_parts(OUT,FILES); src={n:desk(s) for n,s in k.refs().items()}
    native=json.loads((OUT/"cad-validation.json").read_text())["bodies"]
    check={};fail=[]
    def group(label,pairs):
        count=0;bad={}
        for n,s,m,t in pairs:
            count+=1;vol=k.volume(s,t)
            if vol>LIMIT:bad[n+" / "+m]=vol
        check[label]={"comparisons":count,"unexpected_overlap_mm3":bad}
        if bad:print(label,bad,flush=True);fail.append(label)
    def cross(a,b):return ((n,s,m,t) for n,s in a.items() for m,t in b.items())
    def omit(a,*names):return {n:v for n,v in a.items() if n not in names}
    for n,s in parts.items():
        limits=native[n]["bbox"];assert np.allclose(q.bounds(s),[limits["min"],limits["max"]],atol=.007),n
        assert len([ss for ss in s.decompose() if ss.volume()>.002])==1 and abs(s.volume()-native[n]["volume_mm3"])/s.volume()<.012,n
    # Only these exact five screw/host pairs are allowed to occupy the pilot annulus.
    threadpairs={frozenset((s,FRAME if i<2 else SLED)) for i,s in enumerate(NEW_SCREWS)}
    threads={s:k.volume(parts[s],parts[FRAME if i<2 else SLED]) for i,s in enumerate(NEW_SCREWS)}
    assert all(.2<v<5.2 for v in threads.values()),threads
    group("all distinct native bodies",((n,s,m,t) for (n,s),(m,t) in itertools.combinations(parts.items(),2) if frozenset((n,m)) not in threadpairs))
    group("native bodies vs five retained SOURCE bodies",cross(parts,src))
    hardware={}
    for i,(x,y) in enumerate(c.TRAY_CENTRES):hardware["tray "+str(i)]=desk(rod(x,y,-2.15,3.8,2)+rod(x,y,-.15,5,.3)+rod(x,y,-.15,2,6))
    for i,(x,y) in enumerate(r.HOOD_FIX[:2]):hardware["floor "+str(i)]=desk(rod(x,y,19.8,3.8,2)+rod(x,y,21.8,2,8))
    group("existing tray and front closure screws",cross(hardware,{**parts,**src}))
    everything={**parts,**src,**hardware}
    # Source C5R mating gauges, including actual comparative shoulder locations from C5R.
    old=json.loads((r.v.old.C2/"layout-validation.json").read_text())["assumed_plugs_mm"]
    parent=json.loads((REF/"fit-validation.json").read_text())
    def pdplug(key):
        d=old[key];x,z=d['xz_center'];lo,hi=d['y'];w,h=d['width_height']
        return desk(k.placed(rect([x-w/2,lo,z-h/2],[x+w/2,hi,z+h/2])))
    plugs={n:pdplug(n) for n in ("PD boot","PD neck")}
    x,z=old["RJ45"]["xz_center"];w,h=old["RJ45"]["width_height"];lip=56.45;shoulder=lip+parent['gauged_shoulder_setback_from_lip_mm']['RJ45']
    plugs["RJ boot"]=desk(rect([x-w/2,shoulder,z-h/2],[x+w/2,shoulder+23,z+h/2]))
    plugs["RJ neck"]=desk(rect([x-5.90,lip+.025,z-3.75],[x+5.90,shoulder,z+3.75]))
    group("simultaneous PD and Ethernet plugs",cross(plugs,everything))
    group("adjacent cable plugs",cross({n:s for n,s in plugs.items() if n.startswith("PD")},{n:s for n,s in plugs.items() if n.startswith("RJ")}))
    latch=desk(rect([58,60.65,24.6],[71,80.65,36.6]))
    group("underneath RJ latch/finger with power plugged",cross({"RJ finger":latch},{**everything,"PD boot":plugs["PD boot"],"table":rect([-150,-150,-9],[150,150,0])}))
    air=json.loads((r.C5/"fit-validation.json").read_text())["connected_air_gauges_desk_mm"]
    lanes={f"{n}/{i}":rect(np.minimum(a,b)-.7,np.maximum(a,b)+.7) for n,path in air.items() for i,(a,b) in enumerate(zip(path,path[1:]))}
    group("21 connected convection gauges",cross(lanes,everything))
    covers=positive_cover(parts)
    for n,boxes in covers.items():
        outside=parts[n]-md.Manifold.batch_boolean([rect(lo-1e-5,hi+1e-5) for lo,hi in boxes],md.OpType.Add)
        assert outside.volume()<.002,(n,outside.volume())
    def sweep(label,names,offset,delta,obs):
        d=np.array(delta);off=np.array(offset)
        swept={n:md.Manifold.batch_boolean([rect(lo+off+np.minimum(d,0),hi+off+np.maximum(d,0)) for lo,hi in covers[n]],md.OpType.Add) for n in names}
        group(label,cross(swept,obs))
    modules=[PD,BUCK,SOCKET,*CHIPS,*BACKS]
    sled=[SLED,CAP,*modules,*NEW_SCREWS[2:]]
    obstacles=omit(everything,*sled,*NEW_SCREWS[:2],r.FLOOR,*b.FEET,*r.FOOT_SCREWS,*b.SCREWS,r.ROOF,"floor 0","floor 1")
    sweep("complete cassette service: unplug, open floor, move 4 mm forward",sled,[0,0,0],[0,-4,0],obstacles)
    sweep("complete cassette service: 45 mm down after shifting forward",sled,[0,-4,0],[0,0,-45],obstacles)
    sweep("lift retainer from detached cassette", [CAP],[0,0,0],[0,0,34],{n:parts[n] for n in (SLED,*modules)})
    sweep("lift both boards with cap off on bench",modules,[0,0,0],[0,0,34],{SLED:parts[SLED]})
    # Important contacts: stopping force must come from polymer/not solder. Volumes represent
    # interference after a challenge displacement, NOT actual force, stiffness or physical resistance.
    contact={}
    for host in (SLED,CAP):
        contact["USB against "+host]=k.volume(parts[SOCKET].translate([0,-.40,0]),parts[host])
    contact["PD outward end fence"]=k.volume(parts[PD].translate([0,.55,0]),parts[CAP])
    for n in (PD,BUCK):
        for d in [(.50,0,0),(-.50,0,0),(0,-.55,0),(0,.55,0),(0,0,-.28),(0,0,.70)]:
            vol=parts[n].translate(d);contact[n+str(d)]=k.volume(vol,parts[CAP])+k.volume(vol,parts[SLED])
    assert all(v>.01 for v in contact.values()),contact
    drivers={str(i):rod(x,y,-9,4.0,27.34) for i,(x,y) in enumerate(MOUNTS)}
    group("underfloor tool access, 4 mm shaft, carrier installed",cross(drivers,omit(everything,r.FLOOR,*b.FEET,*NEW_SCREWS[:2],*r.FOOT_SCREWS)))
    captools={str(i):rod(x,y,35.49,4.,26.) for i,(x,y) in enumerate(POSTS)}
    group("cap driver on detached cassette",cross(captools,{n:parts[n] for n in (SLED,CAP,*modules)}))
    # Photo-informed exclusion bands, not measured pad edges. The previous rear
    # jaws sat over the plated rings in the seller's dimensional photograph.
    edge_bands={n:rect([CX-1.50,Y_REAR-5.55,z0],[CX+1.50,Y_REAR-1.45,z1])
                for n,z0,z1 in [("lower ring",PD_LOW-.20,PD_LOW+1.85),("upper ring",PD_HIGH-1.85,PD_HIGH+.20)]}
    group("no jaws on assumed CMTPD mounting-ring bands",cross(edge_bands,{n:parts[n] for n in (SLED,CAP)}))
    # Approaches only, while detached: allow for either long-edge orientation of the mode key.
    yy=Y_REAR-22.6
    approaches={str(i):rect([-104.,yy-2.5,zz-2.5],[-82.4,yy+2.5,zz+2.5])
                for i,zz in enumerate((PD_LOW+3.,PD_HIGH-3.))}
    group("5 mm tool approaches approximate CMTPD key on detached sled",cross(approaches,{n:parts[n] for n in (SLED,CAP,*NEW_SCREWS[2:],*modules)}))
    # Two insulated routing gauges in each corridor; no Mac power connector or wire gauge is implied.
    wires={}
    for i,z in enumerate([19.8,24.3]):
        wires["interboard "+str(i)]=wire([[-83.95,16.1,z],[-84.2,13.,z],[-84.2,9.2,z],[-83.8,6.6,z]],1.15)
    for i,(x,y,z) in enumerate([(-84.15,-21.9,17.15),(-81.55,-22.98,17.45)]):
        wires["outbound "+str(i)]=wire([[x,y,z],[x,-25.8,z],[x,-27.6,z],[x,-30.,16.98],[x,-35.2,16.98]],1.06)
    group("two insulated leads each: interboard and front tie saddle",cross(wires,everything))
    group("wire gauges against one another",((n,s,m,t) for (n,s),(m,t) in itertools.combinations(wires.items(),2)))
    group("wire gauges vs convection gauges",cross(wires,lanes))
    # Rear panel and source tray still assemble independently when cassette is out, C5R's own path.
    pull={n:parts[n] for n in (PANEL,r.SKIN,*r.RIVETS)}
    stationary={FRAME:parts[FRAME],**src,**{n:t for n,t in hardware.items() if n.startswith("tray")}}
    group("rear inlay and port carrier, original sampled seating/removal", ((n,s.translate(d),m,t) for d in [(0,y,-3.6) for y in (66,48,34,22,14,8,4,2,1,0)]+[(0,0,z) for z in (-2.4,-1.2,-.4)] for n,s,m,t in cross(pull,stationary)))
    group("tray approach from underside, carrier out",((n,s.translate([0,0,-z]),FRAME,parts[FRAME]) for n,s in src.items() for z in (40,24,12,3,.5)))
    # The plug-free blank has to come out when its two screws are removed. Test with floor/lid off, carrier and tray installed.
    obs=omit(everything,BLANK,*BLANK_SCREWS,r.FLOOR,r.ROOF,*b.SCREWS,*r.FOOT_SCREWS,"floor 0","floor 1")
    group("blank retracts clear of fascia/bosses, sampled",((BLANK,parts[BLANK].translate([0,d,0]),n,t) for d in (.2,2,5,10) for n,t in obs.items()))
    intake=k.gap(parts[SLED],parts[r.FLOOR])
    report={"date":"2026-11-18","variant":"C5R-D1, mm. Digital only; thread/board contact forces, thermal, RF and PD are not measured.",
            "failures":fail,"comparisons":sum(g["comparisons"] for g in check.values()),"checks":check,"allowed_screw_thread_annuli_mm3":threads,
            "challenge_overlaps_mm3":contact,"bench_wire_gauge_diameters_mm":[2.30,2.12],"power_sled_to_lower_shell_mm":intake,
            "CMTPD_assumed_jaw_spans_from_USB_end_mm":PD_LANDS,"assumed_no_jaw_ring_band_from_USB_end_mm":[1.45,5.55],
            "CMTPD_photo":"https://content2.rozetka.com.ua/goods/images/big/516866400.jpg",
            "Mini560_photo":"https://content2.rozetka.com.ua/goods/images/big/298844425.png",
            "Mini560_assumed_edge_spans_from_rear_mm":BUCK_LANDS,
            "Mini560_choke_side":"4R7 long edge up, populated side out. Single full upper jaw; other upper land is backside-only. 0.70 mm component overhang scenario.",
            "assembly_envelope_mm":np.ptp(np.concatenate([q.bounds(s) for s in parts.values()]),axis=0).round(3).tolist(),
            "tested_service":"4 mm towards front, then 45 mm through open floor. Boards and bar released on detached sled.",
            "not_modelled":"Actual cable bend at solder pads, final harness/OVP, individual package positions, heat, power-on, Mac pinout."}
    c.dump(OUT/"fit-validation.json",report)
    print(report["comparisons"],"comparisons;",fail,"USB contacts",dict(list(contact.items())[:3]),flush=True)
    if fail:raise SystemExit(1)
if __name__=="__main__":run()
