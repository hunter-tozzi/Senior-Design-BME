"""
Self-tapping bone marrow needle - parametric STL generator (pure NumPy).
All dimensions in millimetres. Clinical sizes follow a standard adult
Jamshidi needle: 11 gauge (3.05 mm OD, 2.39 mm ID) x 4 in (101.6 mm).

Assembly coordinates: z = 0 is the bottom of the housing, +z is up.
Every part is built in place, then exported individually (shifted so it
sits on z = 0) and also as one combined assembly file.
"""
import numpy as np, struct, os, json

OUT = os.path.join(os.path.dirname(__file__), "stl")
os.makedirs(OUT, exist_ok=True)
TAU = 2 * np.pi

# ---------------------------------------------------------------- dimensions
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

# ---------------------------------------------------------------- mesh core
def _fix(v):
    return v

def tube(rows, n=360, solid=False, theta=None):
    """Watertight solid between inner/outer radius surfaces.
    rows: list of (z, rin, rout); rin/rout are numbers or f(th, z).
    Repeated z values make sharp steps. theta=(a,b) makes an open C-shape."""
    closed = theta is None
    th = (np.linspace(0, TAU, n, endpoint=False) if closed
          else np.linspace(theta[0], theta[1], n))
    ev = lambda f, z: (np.full(n, float(f)) if np.isscalar(f) else np.asarray(f(th, z), float))
    m = len(rows)
    O = np.zeros((m, n, 3)); I = np.zeros((m, n, 3))
    for i, (z, ri, ro) in enumerate(rows):
        R = ev(ro, z); O[i] = np.c_[R*np.cos(th), R*np.sin(th), np.full(n, z)]
        if not solid:
            r = ev(ri, z); I[i] = np.c_[r*np.cos(th), r*np.sin(th), np.full(n, z)]
    V = [O.reshape(-1, 3)]
    oi = lambda i, j: i*n + j % n
    off = m*n
    ii = lambda i, j: off + i*n + j % n
    if not solid:
        V.append(I.reshape(-1, 3))
    F = []
    J = n if closed else n-1
    for i in range(m-1):
        for j in range(J):
            a, b, c, d = oi(i, j), oi(i, j+1), oi(i+1, j+1), oi(i+1, j)
            F += [(a, b, c), (a, c, d)]
            if not solid:
                a, b, c, d = ii(i, j), ii(i, j+1), ii(i+1, j+1), ii(i+1, j)
                F += [(a, c, b), (a, d, c)]
    if solid:
        cb = len(np.vstack(V)); ct = cb+1
        V.append(np.array([[0, 0, rows[0][0]], [0, 0, rows[-1][0]]]))
        for j in range(J):
            F.append((cb, oi(0, j+1), oi(0, j)))
            F.append((ct, oi(m-1, j), oi(m-1, j+1)))
    else:
        for j in range(J):
            F += [(ii(0, j), ii(0, j+1), oi(0, j+1)), (ii(0, j), oi(0, j+1), oi(0, j))]
            t = m-1
            F += [(ii(t, j), oi(t, j+1), ii(t, j+1)), (ii(t, j), oi(t, j), oi(t, j+1))]
        if not closed:
            for i in range(m-1):
                F += [(ii(i, 0), oi(i, 0), oi(i+1, 0)), (ii(i, 0), oi(i+1, 0), ii(i+1, 0))]
                k = n-1
                F += [(ii(i, k), oi(i+1, k), oi(i, k)), (ii(i, k), ii(i+1, k), oi(i+1, k))]
    V = np.vstack(V); F = np.array(F)
    if signed_volume(V, F) < 0:
        F = F[:, ::-1]
    return V, F

def signed_volume(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6

def move(mesh, dx=0, dy=0, dz=0, R=None):
    V, F = mesh
    V = V.copy()
    if R is not None:
        V = V @ np.asarray(R).T
    return V + [dx, dy, dz], F

def merge(*meshes):
    Vs, Fs, k = [], [], 0
    for V, F in meshes:
        Vs.append(V); Fs.append(F + k); k += len(V)
    return np.vstack(Vs), np.vstack(Fs)

def zrange(z0, z1, step):
    k = max(1, int(np.ceil((z1-z0)/step)))
    return list(np.linspace(z0, z1, k+1))

def write_stl(path, mesh, name):
    V, F = mesh
    tri = V[F]
    nrm = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    l = np.linalg.norm(nrm, axis=1, keepdims=True); l[l == 0] = 1
    nrm = nrm / l
    with open(path, 'wb') as f:
        f.write(name.encode()[:80].ljust(80, b' '))
        f.write(struct.pack('<I', len(F)))
        rec = np.zeros(len(F), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
        rec['n'] = nrm; rec['v'] = tri
        f.write(rec.tobytes())

# ---------------------------------------------------------------- profiles
def angdiff(a, b):
    return (a - b + np.pi) % TAU - np.pi

def hexr(af):          # polar radius of a hexagon with given across-flats
    return lambda th, z: (af/2) / np.cos(((th + np.pi/6) % (np.pi/3)) - np.pi/6)

def groove_phase(z):   # helix of the shaft grooves / nut pins (left-hand so a push turns the shaft clockwise)
    return -TAU * z / P['groove_lead']

# ---------------------------------------------------------------- parts
parts = {}
H = P['hous_h']; Ro = P['hous_od']/2; Ri = P['hous_id']/2

# 1. HOUSING -------------------------------------------------------------
def hous_in(th, z):
    r = np.full_like(th, Ri)
    if z >= P['slot_z0']:
        for c in (np.pi/2, 3*np.pi/2):
            r = np.where(np.abs(angdiff(th, c)) < P['slot_half'], P['slot_r'], r)
    return r
lz, lt = P['ledge_z'], P['ledge_t']
rows = [(0, Ri, Ro), (lz, Ri, Ro), (lz, P['ledge_bore']/2, Ro), (lz+lt, P['ledge_bore']/2, Ro),
        (lz+lt, Ri, Ro), (P['slot_z0'], Ri, Ro), (P['slot_z0'], hous_in, Ro), (H, hous_in, Ro)]
parts['01_housing'] = tube(rows, n=480)

# 2. BOTTOM PLUG (bearing for the cannula hub) -----------------------------
spig_r = 5.0
parts['02_bottom_plug'] = tube([(-2, spig_r+0.3, Ro), (0, spig_r+0.3, Ro),
                               (0, spig_r+0.3, Ri-0.05), (6, spig_r+0.3, Ri-0.05)], n=240)

# 3. CANNULA + RATCHET HUB (one piece) ------------------------------------
rc_o, rc_i = P['can_od']/2, P['can_id']/2
tip = -2 - P['can_len']                    # working length measured from the plug face
pitch, depth = P['thr_pitch'], P['thr_depth']
def cannula_out(th, z):
    s = z - tip                            # distance up from the tip
    if s > P['thr_len'] + 1e-9:
        return np.full_like(th, rc_o)
    # right-hand helix: phase u in [0,1)
    u = ((z - pitch*th/TAU) / pitch) % 1.0
    # asymmetric (buttress) profile: steep lower face, long sloped upper face
    prof = np.where(u < 0.08, u/0.08, np.where(u < 0.75, 1 - (u-0.08)/0.67, 0.0))
    h = depth * prof
    h = h * np.clip(s / P['thr_lead'], 0, 1)                     # tapered lead-in for self-tapping
    if s < P['flute_len']:                                       # two cutting flutes
        for c in (0.0, np.pi):
            h = np.where(np.abs(angdiff(th, c)) < 0.45, 0.0, h)
    return rc_o + h
g0, g1, gn = P['gear_r0'], P['gear_r1'], P['gear_n']
GEAR_OFF = 0.0
def gear(th, z):
    s = ((th - GEAR_OFF) % (TAU/gn)) / (TAU/gn)
    return g0 + (g1-g0) * (1 - np.abs(2*s - 1))                  # symmetric V teeth (reversible ratchet)
hub_bot, gear_bot, gear_top = -2.0, 6.2, 14.0
sock = 3.0
rows = [(tip, rc_i, cannula_out)]
rows += [(z, rc_i, cannula_out) for z in zrange(tip, tip+P['thr_len']+0.05, 0.02)[1:]]
rows += [(hub_bot, rc_i, rc_o), (hub_bot, rc_i, spig_r), (gear_bot, rc_i, spig_r),
         (gear_bot, rc_i, gear), (gear_top-sock, rc_i, gear), (gear_top-sock, hexr(3.5), gear),
         (gear_top, hexr(3.5), gear)]
hub_rows = rows

# 4. SPIRAL SHAFT + PAWL CARRIER (one piece) --------------------------------
cup_i, cup_o = 14.8, 15.6
disc_bot, disc_top = 14.2, lz - 0.5
sr, ch = P['shaft_od']/2, P['channel_d']/2
gr_z0, sh_top = 46.0, 100.0
def shaft_out(th, z):
    r = np.full_like(th, sr)
    for k in (0, np.pi):
        r = np.where(np.abs(angdiff(th, groove_phase(z) + k)) < 0.45, sr - P['groove_depth'], r)
    return r
rows = [(gear_bot, cup_i, cup_o), (disc_bot, cup_i, cup_o), (disc_bot, ch, cup_o), (disc_top, ch, cup_o),
        (disc_top, ch, sr), (gr_z0, ch, sr)]
rows += [(z, ch, shaft_out) for z in zrange(gr_z0, sh_top, 0.5)]
shaft = tube(rows, n=360)
post_xy = (12.2, 0.0)
post = move(tube([(6.4, 0, 1.5), (disc_bot + 0.6, 0, 1.5)], n=48, solid=True), *post_xy)
parts['04_spiral_shaft_carrier'] = merge(shaft, post)

# 5. REVERSIBLE ROCKER PAWL ---------------------------------------------
# Double-ended rocker on the post. Tip A engages for driving IN; flip the rocker
# (or rotate to the other stop) so tip B engages for backing OUT.
PAWL_RI, PAWL_RO = 1.6, 2.3          # bore on the 1.5 mm post, hub ring
PAWL_HALF_W = 0.5                    # arm half-width (1.0 mm wide arms)
ARM, gam, BASE = 3.9, np.deg2rad(44.0), np.deg2rad(65.0)   # solved: tip seated, 30 deg lean, other end clear
def _bar(th, a, L, h):
    d = angdiff(th, a); c = np.cos(d); s = np.abs(np.sin(d))
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.minimum(np.where(s > 1e-9, h/s, np.inf), np.where(c > 1e-9, L/c, 0))
    return np.where(c > 0, r, 0)
def rocker_shape(gamma, L):
    a1 = np.pi - BASE + gamma; a2 = np.pi + BASE + gamma
    def ro(th, z):
        return np.maximum(PAWL_RO, np.maximum(_bar(th, a1, L, PAWL_HALF_W), _bar(th, a2, L, PAWL_HALF_W)))
    return ro, a1, a2
def tip_r(a, L):
    return np.hypot(post_xy[0] + L*np.cos(a), L*np.sin(a))
_, _a1, _a2 = rocker_shape(gam, ARM)
tipA, tipB = tip_r(_a1, ARM), tip_r(_a2, ARM)
ro_fn, _, _ = rocker_shape(gam, ARM)

_, a1_, _ = rocker_shape(gam, ARM)
tipA_ang = np.arctan2(ARM*np.sin(a1_), post_xy[0] + ARM*np.cos(a1_))
GEAR_OFF = float(tipA_ang)                 # put a tooth valley right under tip A
parts['03_cannula_hub'] = tube(hub_rows, n=240)
parts['05_rocker_pawl'] = move(tube([(6.8, PAWL_RI, ro_fn), (13.8, PAWL_RI, ro_fn)], n=360), *post_xy)

# 6. PUSH CAP + DRIVE NUT (one piece) -------------------------------------
nz = P['nut_rest_z']; nh = P['nut_h']
def nut_in(th, z):
    r = np.full_like(th, sr + 0.25)
    for k in (0, np.pi):
        r = np.where(np.abs(angdiff(th, groove_phase(z) + k)) < 0.28, sr - P['groove_depth'] + 0.2, r)
    return r
def nut_out(th, z):
    r = np.full_like(th, Ri - 0.3)
    for c in (np.pi/2, 3*np.pi/2):
        r = np.where(np.abs(angdiff(th, c)) < P['slot_half'] - 0.07, P['slot_r'] - 0.3, r)
    return r
plunger_o, plunger_i = 12.0, sr + 0.3
pad_bot = nz + nh + 42; pad_top = pad_bot + 5
rows = [(z, nut_in, nut_out) for z in zrange(nz, nz+nh, 0.25)]
rows += [(nz+nh, plunger_i, nut_out), (nz+nh, plunger_i, plunger_o), (pad_bot, plunger_i, plunger_o),
         (pad_bot, 1.25*2, plunger_o), (pad_bot, 2.5, Ri), (pad_bot+2, 2.5, Ri), (pad_bot+2, 4.5, Ri), (pad_top, 4.5, Ri)]
parts['06_push_cap_drive_nut'] = tube(rows, n=360)

# 7. TOP COVER RING (stops the nut, press-fit, keyed in slots) -------------
def ring_out(th, z):
    r = np.full_like(th, Ri - 0.05)
    for c in (np.pi/2, 3*np.pi/2):
        r = np.where(np.abs(angdiff(th, c)) < P['slot_half'] - 0.05, P['slot_r'] - 0.15, r)
    return r
parts['07_top_cover_ring'] = tube([(H-6, 13.0, ring_out), (H, 13.0, ring_out), (H, 13.0, Ro), (H+1.5, 13.0, Ro)], n=480)

# 8. TOP PORT (holds the seal; approximate female Luer) ---------------------
pt = pad_top
luer = lambda th, z: np.full_like(th, 2.1 + 0.2*(z - (pt+1.5))/8.0)
parts['08_top_port'] = tube([(pt-1.5, 2.1, 4.4), (pt, 2.1, 4.4), (pt, 2.1, 6.0), (pt+1.5, 2.1, 6.0),
                            (pt+1.5, 2.1, 3.9), (pt+9.5, luer, 3.9)], n=240)

# 9. STYLET (trocar tip, hex key seats in the hub) --------------------------
rs = P['sty_d']/2
tro_bot = tip - P['trocar_len']
def trocar(th, z):
    f = np.clip((z - tro_bot) / (P['trocar_len'] + 1.0), 0.015, 1.0)
    tri = (rs*f) / np.cos((th % (TAU/3)) - np.pi/3)
    return np.minimum(rs, tri)
knob_z = pt + 9.5 + 15
rows = [(z, 0, trocar) for z in zrange(tro_bot, tip + 1.0, 0.05)]
rows += [(gear_top - sock, 0, rs), (gear_top - sock, 0, hexr(3.3)), (gear_top, 0, hexr(3.3)),
         (gear_top, 0, rs), (knob_z, 0, rs), (knob_z, 0, 6.0), (knob_z + 10, 0, 6.0)]
parts['09_stylet'] = tube(rows, n=180, solid=True)

# 10. SLIDING DEPTH-LOCK BASE (split clamp sleeve + foot) -------------------
sl_bot = -50.0; sl_h = 100.0
sl_i, sl_o = Ro + 0.25, Ro + 3.0
slit = 0.07
sleeve = tube([(sl_bot, sl_i, sl_o), (sl_bot + sl_h, sl_i, sl_o)], n=360, theta=(slit, TAU - slit))
foot = tube([(sl_bot, 3.0, 28.0), (sl_bot + 3, 3.0, 28.0)], n=360, theta=(slit*0.8, TAU - slit*0.8))
def rsq(th, z):
    p = 6.0
    return 4.0 / (np.abs(np.cos(th))**p + np.abs(np.sin(th))**p)**(1/p)
Rzy = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]           # tube axis z -> y
ear_x, ear_z = sl_o + 2.3, sl_bot + sl_h - 6
ear1 = move(tube([(1.4, 1.7, rsq), (7.0, 1.7, rsq)], n=96), R=Rzy)
ear2 = move(tube([(-7.0, 1.7, rsq), (-1.4, 1.7, rsq)], n=96), R=Rzy)
ears = merge(move(ear1, ear_x, 0, ear_z), move(ear2, ear_x, 0, ear_z))
parts['10_sliding_base'] = merge(sleeve, foot, ears)

json.dump(dict(P=P, tip_z=tip, tipA=tipA, tipB=tipB, gamma_deg=float(np.rad2deg(gam)), arm=float(ARM),
               pad_top=pt, knob_z=knob_z), open(os.path.join(OUT, '..', 'dims.json'), 'w'), indent=1)

import pickle
pickle.dump(parts, open(os.path.join(OUT, '..', 'parts.pkl'), 'wb'))

# ---------------------------------------------------------------- export
for name, mesh in parts.items():
    V, F = mesh
    write_stl(os.path.join(OUT, name + '.stl'), move(mesh, dz=-V[:, 2].min()), name)
write_stl(os.path.join(OUT, '00_full_assembly.stl'), merge(*parts.values()), 'assembly')
print('ok', {k: len(v[1]) for k, v in parts.items()})
print('pawl tips r:', round(tipA, 2), round(tipB, 2), 'tilt', round(float(np.rad2deg(gam)), 1), 'arm', round(ARM,2))
