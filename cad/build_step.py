"""
Self-tapping bone marrow needle - native B-rep CAD model (CadQuery / OpenCascade).

Rebuilds every part from the v1 STL generator (reference/build_stl_v1.py) as
true solids with analytic cylinders, planes and helices, and exports:

  step/parts/NN_name.step      one STEP per part, in ASSEMBLY coordinates
  step/00_full_assembly.step   STEP assembly (opens in SolidWorks as .SLDASM)
  stl/NN_name.stl              fine-tessellated STL of each B-rep part

All dimensions in mm. Axis = Z. z = 0 is the bottom face of the housing.
Every part keeps the assembly origin, so inserting a part file with its origin
on the assembly origin puts it in its assembled (at-rest) position.

Run:  pip install cadquery && python build_step.py
"""
import math, os, json
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
TAU = 2 * math.pi
V = cq.Vector

# ------------------------------------------------------------- dimensions
P = dict(
    # cannula (11 G Jamshidi)
    can_od=3.05, can_id=2.39, can_len=101.6,
    thr_pitch=1.0, thr_depth=0.40, thr_len=6.0, thr_lead=1.5, flute_len=3.0,
    # stylet
    sty_d=2.30, trocar_len=2.5,
    # housing / mechanism
    hous_od=38.0, hous_id=32.0, hous_h=100.0,
    ledge_z=18.0, ledge_t=4.0, ledge_bore=12.0,
    slot_z0=49.0, slot_r=17.3, slot_half=0.40,
    shaft_od=10.0, channel_d=4.2, groove_depth=1.2, groove_lead=50.0,
    stroke=30.0, nut_rest_z=80.0, nut_h=14.0,
    gear_r0=8.0, gear_r1=9.5, gear_n=24,
)
H = P['hous_h']; Ro = P['hous_od'] / 2; Ri = P['hous_id'] / 2
SLOT_ANGLES = (math.pi / 2, 3 * math.pi / 2)          # key slots at +Y / -Y


# ------------------------------------------------------------- helpers
def cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)

def ring(ri, ro, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).circle(ro).circle(ri).extrude(z1 - z0)

def sector_sketch(wp, ri, ro, a0, a1):
    """Annular sector (ri may be 0) drawn on workplane wp, closed wire pending."""
    am = (a0 + a1) / 2
    p = lambda r, a: (r * math.cos(a), r * math.sin(a))
    w = wp.moveTo(*p(ri, a0)).lineTo(*p(ro, a0)).threePointArc(p(ro, am), p(ro, a1))
    if ri > 0:
        w = w.lineTo(*p(ri, a1)).threePointArc(p(ri, am), p(ri, a0))
    return w.close()

def sector(ri, ro, a0, a1, z0, z1):
    return sector_sketch(cq.Workplane("XY").workplane(offset=z0), ri, ro, a0, a1).extrude(z1 - z0)

def helical_sector(ri, ro, half, phase0, z0, z1, lead):
    """Sector of half-angle `half` centred on phase0 at z0, swept as a helix of
    the given lead (negative = left-hand) from z0 to z1."""
    twist = math.degrees(TAU * (z1 - z0) / lead)
    return sector_sketch(cq.Workplane("XY").workplane(offset=z0), ri, ro,
                         phase0 - half, phase0 + half).twistExtrude(z1 - z0, twist)

def hex_prism(af, z0, z1, x=0.0, y=0.0):
    # flats normal to X (matches the v1 hexr() profile)
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y)
            .polygon(6, af / math.cos(math.pi / 6)).extrude(z1 - z0))

def groove_phase(z):
    """2-start spiral groove centre angle at height z (left-hand, 50 mm lead)."""
    return -TAU * z / P['groove_lead']


parts = {}

# ======================================================================
# 01 HOUSING
# ======================================================================
lz, lt = P['ledge_z'], P['ledge_t']
housing = ring(Ri, Ro, 0, H).union(ring(P['ledge_bore'] / 2, Ri + 0.01, lz, lz + lt))
for c in SLOT_ANGLES:
    housing = housing.cut(sector(Ri - 0.5, P['slot_r'], c - P['slot_half'], c + P['slot_half'],
                                 P['slot_z0'], H + 0.1))
parts['01_housing'] = housing

# ======================================================================
# 02 BOTTOM PLUG (bearing for the cannula hub)
# ======================================================================
spig_r = 5.0
plug = ring(spig_r + 0.3, Ro, -2, 0).union(ring(spig_r + 0.3, Ri - 0.05, -0.01, 6))
parts['02_bottom_plug'] = plug

# ======================================================================
# 03 CANNULA + RATCHET HUB (one piece)
# ======================================================================
rc_o, rc_i = P['can_od'] / 2, P['can_id'] / 2
tip = -2 - P['can_len']                       # -103.6
pitch, depth = P['thr_pitch'], P['thr_depth']
hub_bot, gear_bot, gear_top = -2.0, 6.2, 14.0
sock = 3.0

# rocker pawl geometry (needed to phase the gear teeth under pawl tip A)
post_xy = (12.2, 0.0)
PAWL_RI, PAWL_RO, PAWL_HALF_W = 1.6, 2.3, 0.5
ARM, GAM, BASE = 3.9, math.radians(44.0), math.radians(65.0)
a1 = math.pi - BASE + GAM; a2 = math.pi + BASE + GAM
tipA = (post_xy[0] + ARM * math.cos(a1), post_xy[1] + ARM * math.sin(a1))
tipB = (post_xy[0] + ARM * math.cos(a2), post_xy[1] + ARM * math.sin(a2))
# tooth valley right under tip A; the extra -0.5 deg seats the flat arm end
# with ~0.01 mm clearance instead of overlapping a straight tooth flank
GEAR_OFF = math.atan2(tipA[1], tipA[0]) - math.radians(0.5)

# body: cannula tube + spigot + 24-tooth symmetric ratchet
g0, g1, gn = P['gear_r0'], P['gear_r1'], P['gear_n']
gear_pts = []
for k in range(gn):
    a = GEAR_OFF + k * TAU / gn
    gear_pts.append((g0 * math.cos(a), g0 * math.sin(a)))
    b = a + TAU / gn / 2
    gear_pts.append((g1 * math.cos(b), g1 * math.sin(b)))
gear = cq.Workplane("XY").workplane(offset=gear_bot).polyline(gear_pts).close().extrude(gear_top - gear_bot)
hub = (cyl(rc_o, tip, hub_bot + 0.01)
       .union(cyl(spig_r, hub_bot, gear_bot + 0.01))
       .union(gear))

# self-tapping buttress thread: right-hand, pitch 1.0, depth 0.40, last 6 mm
z_h0 = math.floor(tip) - 1                    # integer z -> thread phase u = 0 at theta = 0
n_turns = 10
r_base = rc_o - 0.05                          # root sits 0.05 inside the tube for a clean union
prof = [V(r_base, 0, z_h0), V(rc_o, 0, z_h0), V(rc_o + depth, 0, z_h0 + 0.08),
        V(rc_o, 0, z_h0 + 0.75), V(r_base, 0, z_h0 + 0.75)]
helix = cq.Wire.makeHelix(pitch, n_turns * pitch, r_base).moved(cq.Location(V(0, 0, z_h0)))
thread = cq.Solid.sweep(cq.Wire.makePolygon(prof, close=True), [], helix,
                        makeSolid=True, isFrenet=True)
# envelope: tapered lead-in over the first 1.5 mm, thread stops 6 mm up
env = (cq.Workplane("XZ").polyline([(0, tip), (rc_o, tip), (rc_o + depth, tip + P['thr_lead']),
                                     (rc_o + 1.0, tip + P['thr_lead']), (rc_o + 1.0, tip + P['thr_len']),
                                     (0, tip + P['thr_len'])]).close()
       .revolve(360, (0, 0, 0), (0, 1, 0)))
thread = cq.Workplane("XY").add(thread).intersect(env)
for c in (0.0, math.pi):                      # two cutting flutes, first 3 mm
    thread = thread.cut(sector(rc_o - 0.2, rc_o + 1.0, c - 0.45, c + 0.45, tip - 0.1, tip + P['flute_len']))
hub = hub.union(thread)

# through bore + hex socket for the stylet key
hub = hub.cut(cyl(rc_i, tip - 1, gear_top + 1))
hub = hub.cut(hex_prism(3.5, gear_top - sock, gear_top + 1))
parts['03_cannula_hub'] = hub

# ======================================================================
# 04 SPIRAL SHAFT + PAWL CARRIER (one piece)
# ======================================================================
cup_i, cup_o = 14.8, 15.6
disc_bot, disc_top = 14.2, lz - 0.5
sr, ch = P['shaft_od'] / 2, P['channel_d'] / 2
gr_z0, sh_top = 46.0, 100.0
shaft = (ring(cup_i, cup_o, gear_bot, disc_bot + 0.01)
         .union(cyl(cup_o, disc_bot, disc_top))
         .union(cyl(sr, disc_top - 0.01, sh_top)))
for k in (0.0, math.pi):
    shaft = shaft.cut(helical_sector(sr - P['groove_depth'], sr + 0.5, 0.45,
                                     groove_phase(gr_z0) + k, gr_z0, sh_top + 0.5, -P['groove_lead']))
shaft = shaft.union(cyl(1.5, 6.4, disc_bot + 0.6, *post_xy))     # pawl post
shaft = shaft.cut(cyl(ch, gear_bot - 1, sh_top + 1))             # instrument channel
parts['04_spiral_shaft_carrier'] = shaft

# ======================================================================
# 05 REVERSIBLE ROCKER PAWL (shown in the drive position)
# ======================================================================
pz0, pz1 = 6.8, 13.8
pawl = cyl(PAWL_RO, pz0, pz1, *post_xy)
for a in (a1, a2):
    arm = (cq.Workplane("XY").workplane(offset=pz0)
           .center(post_xy[0] + ARM / 2 * math.cos(a), post_xy[1] + ARM / 2 * math.sin(a))
           .transformed(rotate=(0, 0, math.degrees(a)))
           .rect(ARM, 2 * PAWL_HALF_W).extrude(pz1 - pz0))
    pawl = pawl.union(arm)
pawl = pawl.cut(cyl(PAWL_RI, pz0 - 1, pz1 + 1, *post_xy))
parts['05_rocker_pawl'] = pawl

# ======================================================================
# 06 PUSH CAP + DRIVE NUT (one piece, at rest)
# ======================================================================
nz, nh = P['nut_rest_z'], P['nut_h']
plunger_o, plunger_i = 12.0, sr + 0.3
pad_bot = nz + nh + 42; pad_top = pad_bot + 5           # 136 / 141
nut = cyl(Ri - 0.3, nz, nz + nh)
for c in SLOT_ANGLES:                                    # anti-rotation ears in the housing slots
    nut = nut.union(sector(Ri - 1.0, P['slot_r'] - 0.3, c - (P['slot_half'] - 0.07),
                           c + (P['slot_half'] - 0.07), nz, nz + nh))
nut = nut.cut(cyl(sr + 0.25, nz - 1, nz + nh + 1))
for k in (0.0, math.pi):                                 # helical drive pins in the shaft grooves
    nut = nut.union(helical_sector(sr - P['groove_depth'] + 0.2, sr + 0.4, 0.28,
                                   groove_phase(nz) + k, nz, nz + nh, -P['groove_lead']))
cap = (ring(plunger_i, plunger_o, nz + nh - 0.01, pad_bot + 0.01)
       .union(cyl(Ri, pad_bot, pad_top))
       .cut(cyl(2.5, pad_bot - 1, pad_top + 1))
       .cut(cyl(4.5, pad_top - 3, pad_top + 1)))         # seal counterbore 9 x 3
parts['06_push_cap_drive_nut'] = nut.union(cap)

# ======================================================================
# 07 TOP COVER RING (press-fit, keyed, stops the nut at rest)
# ======================================================================
cover = ring(13.0, Ri - 0.05, H - 6, H + 0.01).union(ring(13.0, Ro, H, H + 1.5))
for c in SLOT_ANGLES:
    cover = cover.union(sector(Ri - 0.5, P['slot_r'] - 0.15, c - (P['slot_half'] - 0.05),
                               c + (P['slot_half'] - 0.05), H - 6, H + 0.01))
parts['07_top_cover_ring'] = cover

# ======================================================================
# 08 TOP PORT (clamps the seal; approximate female Luer)
# ======================================================================
pt = pad_top
port = (cq.Workplane("XZ")
        .polyline([(2.1, pt - 1.5), (4.4, pt - 1.5), (4.4, pt), (6.0, pt), (6.0, pt + 1.5),
                   (3.9, pt + 1.5), (3.9, pt + 9.5), (2.3, pt + 9.5), (2.1, pt + 1.5)]).close()
        .revolve(360, (0, 0, 0), (0, 1, 0)))
parts['08_top_port'] = port

# ======================================================================
# 09 STYLET (3-facet trocar point, hex key seats in the hub socket)
# ======================================================================
rs = P['sty_d'] / 2
tro_bot = tip - P['trocar_len']                         # -106.1
knob_z = pt + 9.5 + 15                                  # 165.5
stylet = (cyl(rs, tro_bot, gear_top - sock + 0.01)
          .union(hex_prism(3.3, gear_top - sock, gear_top))
          .union(cyl(rs, gear_top - 0.01, knob_z + 0.01))
          .union(cyl(6.0, knob_z, knob_z + 10)))
# trocar: three flat facets meeting at the apex, apothem = rs at tip + 1.0
fl = P['trocar_len'] + 1.0
hgt = 2 * fl
apo = rs * hgt / fl
tri = [V(2 * apo * math.cos(a), 2 * apo * math.sin(a), tro_bot + hgt)
       for a in (0, TAU / 3, 2 * TAU / 3)]              # vertices at 0/120/240 -> flats at 60/180/300 deg
apex = V(0, 0, tro_bot)
faces = [cq.Face.makeFromWires(cq.Wire.makePolygon(tri, close=True))]
for i in range(3):
    faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon([apex, tri[(i + 1) % 3], tri[i]], close=True)))
pyramid = cq.Solid.makeSolid(cq.Shell.makeShell(faces)).fix()
outside = cyl(rs + 1, tro_bot - 1, tip + 1.0).cut(cq.Workplane("XY").add(pyramid))
stylet = stylet.cut(outside)
parts['09_stylet'] = stylet

# ======================================================================
# 10 SLIDING DEPTH-LOCK BASE (split clamp sleeve + foot + M3 clamp ears)
# ======================================================================
sl_bot, sl_h = -50.0, 100.0
sl_i, sl_o = Ro + 0.25, Ro + 3.0
slit = 0.07
base = sector(sl_i, sl_o, slit, TAU - slit, sl_bot, sl_bot + sl_h)
base = base.union(sector(3.0, 28.0, slit * 0.8, TAU - slit * 0.8, sl_bot, sl_bot + 3))
ear_x, ear_z = sl_o + 2.3, sl_bot + sl_h - 6
for y0, y1 in ((1.4, 7.0), (-7.0, -1.4)):
    ear = (cq.Workplane("XY").box(8.0, y1 - y0, 8.0)
           .edges("|Y").fillet(1.5)
           .translate((ear_x, (y0 + y1) / 2, ear_z)))
    base = base.union(ear)
base = base.cut(cq.Workplane("XZ").workplane(offset=10).center(ear_x, ear_z).circle(1.7).extrude(-20))
base = base.cut(cyl(sl_i, sl_bot + 3, sl_bot + sl_h + 1))   # keep the sleeve bore clear of the ears
parts['10_sliding_base'] = base


# ======================================================================
# EXPORT
# ======================================================================
NAMES = {
    '01_housing': ('Housing', (0.27, 0.58, 0.47)),
    '02_bottom_plug': ('Bottom plug', (0.40, 0.40, 0.38)),
    '03_cannula_hub': ('Cannula + ratchet hub', (0.80, 0.33, 0.18)),
    '04_spiral_shaft_carrier': ('Spiral shaft + pawl carrier', (0.38, 0.36, 0.72)),
    '05_rocker_pawl': ('Rocker pawl', (0.85, 0.62, 0.15)),
    '06_push_cap_drive_nut': ('Push cap + drive nut', (0.58, 0.56, 0.80)),
    '07_top_cover_ring': ('Top cover ring', (0.12, 0.48, 0.36)),
    '08_top_port': ('Top port', (0.90, 0.55, 0.10)),
    '09_stylet': ('Stylet', (0.22, 0.22, 0.22)),
    '10_sliding_base': ('Sliding depth-lock base', (0.55, 0.55, 0.52)),
}

if __name__ == '__main__':
    step_dir = os.path.join(HERE, 'step'); part_dir = os.path.join(step_dir, 'parts')
    stl_dir = os.path.join(HERE, 'stl')
    for d in (part_dir, stl_dir):
        os.makedirs(d, exist_ok=True)

    report = {}
    asm = cq.Assembly(name='self_tapping_needle')
    for key, wp in parts.items():
        solid = wp.val()
        if hasattr(solid, 'Solids') and len(solid.Solids()) == 1:
            solid = solid.Solids()[0]
        label, rgb = NAMES[key]
        report[key] = dict(valid=solid.isValid(), solids=len(wp.solids().vals()),
                           volume_mm3=round(solid.Volume(), 2),
                           bbox=[round(x, 3) for x in (solid.BoundingBox().xmin, solid.BoundingBox().ymin,
                                                         solid.BoundingBox().zmin, solid.BoundingBox().xmax,
                                                         solid.BoundingBox().ymax, solid.BoundingBox().zmax)])
        cq.exporters.export(cq.Workplane().add(solid), os.path.join(part_dir, key + '.step'))
        cq.exporters.export(cq.Workplane().add(solid), os.path.join(stl_dir, key + '.stl'),
                            tolerance=0.01, angularTolerance=0.1)
        asm.add(solid, name=key, color=cq.Color(*rgb, 1.0))
        print(key, report[key])

    asm.save(os.path.join(step_dir, '00_full_assembly.step'), exportType='STEP')
    json.dump(dict(P=P, tip_z=tip, tipA=tipA, tipB=tipB, gear_offset_deg=math.degrees(GEAR_OFF),
                   pad_top=pt, knob_z=knob_z, parts=report),
              open(os.path.join(HERE, 'build_report.json'), 'w'), indent=1)
    print('done')
