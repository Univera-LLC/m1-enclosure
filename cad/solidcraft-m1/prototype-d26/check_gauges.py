"""Independent cable envelopes in desk XZ, not exported from the panel sketches.

Widths, lengths and evidence: docs/mac-mini-m1-implementation/CONNECTOR_REFERENCES.md.
Profiles are centered; physical misregistration and the mated shoulder clearance are separate.
"""
from pathlib import Path
import numpy as np

OUT=Path(__file__).resolve().parent
import manifold3d as md

NOSES={'A1':(12.10,4.60,'rect'),'A2':(12.10,4.60,'rect'),
       'HDMI':(13.94,4.49,'hdmi'),'TB1':(8.28,2.43,'capsule'),'TB2':(8.28,2.43,'capsule'),
       'RJ':(11.80,6.75,'rect'),'audio':(3.55,3.55,'round'),'PD':(2.43,8.28,'capsule')}
# USB-A (2.67) and HDMI (2.00) are documented mated-pair specs.
# TB1/TB2 (1.20) matches Apple OEM ~1.0 mm wall class; PD (0.65) stays compatible with
# standard short USB-C power plugs thanks to +0.40 mm CMTPD shift; audio (0.55) clears
# the 0.32 mm collar recess; RJ (1.20) represents wide strain-relief boot setback.
SHOULDERS={'A1':(16.,8.,2.67),'A2':(16.,8.,2.67),'HDMI':(21.,11.,2.),
           'TB1':(12.85,7.,1.20),'TB2':(12.85,7.,1.20),'RJ':(16.8,15.,1.20),
           'audio':(11.40,11.40,.55),'PD':(7.,12.85,.65)}
SOURCES={'A1':'USB 2.0 Fig 6-9; 6-7 and USB 3.1 Legacy 5-27 mated shoulder (DOCUMENTED).',
         'A2':'USB 2.0 Fig 6-9; 6-7 and USB 3.1 Legacy 5-27 mated shoulder (DOCUMENTED).',
         'HDMI':'HDMI 1.3 Figs 4-2 / 4-3; outer W/H and mated shoulder (DOCUMENTED). Chamfer gauge 0.72 mm cuts the two desk-upper corners (modeled).',
         'TB1':'USB Type-C 2.5 Fig 3-3 metal maximum and straight overmold maximum (DOCUMENTED). Apple OEM fascia has ~1.0 mm wall ahead of TB bezel (owner photo 2026-11-19).',
         'TB2':'USB Type-C 2.5 Fig 3-3 metal maximum and straight overmold maximum (DOCUMENTED). Apple OEM fascia has ~1.0 mm wall ahead of TB bezel (owner photo 2026-11-19).',
         'PD':'USB Type-C 2.5 Fig 3-3 rotated 90 degrees. CMTPD shifted +0.40 mm so 0.56 mm setback keeps 0.65 mm cable scenario clear.',
         'RJ':'FCC 47 CFR 68.500 Fig (c)(2)(ii): 11.684 x 6.604 body REF; example 11.80 x 6.75. No universal cable boot or release finger envelope.',
         'audio':'Same Sky SP-3530 first shaft max 3.55, first collar max 9.1 (DOCUMENTED). Protruding Ø5.00 Apple collar sits 0.32 mm recessed behind 0.80 mm wall.'}

def section(w,h,kind):
    if kind=='round': return md.CrossSection.circle(w/2,96)
    if kind=='capsule':
        r=min(w,h)/2
        centers=[(a*(w-2*r)/2,a*(h-2*r)/2) for a in (-1,1)]
        return md.CrossSection.batch_hull([md.CrossSection.circle(r,96).translate(c) for c in centers])
    if kind=='hdmi':
        a,b,c=w/2,h/2,.72
        return md.CrossSection([[[-a,-b],[a,-b],[a,b-c],[a-c,b],[-a+c,b],[-a,b-c]]])
    return md.CrossSection.square([w,h],True)

def nose(n,at):
    return section(*NOSES[n]).translate(at)

def shoulder(n,at):
    w,h,_=SHOULDERS[n]
    return section(w,h,'round' if n=='audio' else 'rect').translate(at)

def extrusion(cs,y0,y1):
    return cs.extrude(y1-y0).rotate([90,0,0]).translate([0,y1,0])

def negative_play_convex(cs,play):
    return md.CrossSection.batch_hull([cs.translate([-dx,-dz]) for dx in play[:,0] for dz in play[:,2]])

def rj_spring(x,lip):
    def segment(y,z0,z1,w):
        return md.Manifold.cube([w,.02,z1-z0]).translate([x-w/2,y,z0])
    sections=[segment(lip+d,lo,hi,6.18) for d,lo,hi in [(-.36,18.52,19.22),(.21,18.36,19.10),(1.60,17.45,19.),(7.45,13.18,17.96)]]
    central=md.Manifold.batch_boolean([md.Manifold.batch_hull([a,b]) for a,b in zip(sections,sections[1:])],md.OpType.Add)
    narrow=md.Manifold.batch_hull([segment(lip-.35,17.56,18.40,3.38),segment(lip+.30,17.48,18.50,3.38)])
    return {'central latch':central,'terminal latch':narrow}
