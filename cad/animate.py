"""
Render an animation of the self-tapping needle mechanism from the CAD model.

Kinematics (all from build_step.py geometry):
  * push cap + drive nut slide down d = 0..30 mm (keyed, no rotation)
  * spiral shaft turns alpha = -360 * d / 50 deg (50 mm left-hand lead -> clockwise seen from the top)
  * ratchet: the pawl on the carrier drives the hub only clockwise. Teeth are 15 deg apart,
    so after the first stroke each push first takes up 6 deg of slack (216 mod 15) and then
    drives 210 deg. On the spring return the pawl rocks out over the teeth and the hub stays put.
  * the whole device advances 1.0 mm per cannula revolution (right-hand thread, pitch 1.0)

Run:  xvfb-run -a python animate.py      (needs cadquery, vtk, pillow, matplotlib, ffmpeg)
Output: animation/needle_mechanism.mp4 (+ .gif)
"""
import math, os, shutil, subprocess, sys
import numpy as np
import vtk
from vtk.util import numpy_support as nps
from PIL import Image, ImageDraw, ImageFont
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_step as B

OUT = os.path.join(HERE, 'animation')
FRAMES = os.path.join(OUT, 'frames')
FPS = 20
N_STROKES = 6
T_PUSH, T_HOLD, T_RET, T_GAP = 1.4, 0.3, 1.0, 0.3
T_INTRO, T_OUTRO = 1.0, 1.5
STROKE = B.P['stroke']
LEAD = B.P['groove_lead']
PITCH = B.P['thr_pitch']
TOOTH = 360.0 / B.P['gear_n']
CORTEX = 3.0                     # modeled cortical thickness, mm
W, H = 1920, 1080
C_SCALE = 8.5                    # half-height of the bone close-up, mm

FONT = font_manager.findfont('DejaVu Sans')
FONT_B = font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans', weight='bold'))
def font(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, sz)


# ---------------------------------------------------------------- kinematics
def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)

def timeline():
    """Per-frame (t, cap travel d, stroke index, phase)."""
    seq = [(T_INTRO, 'rest', None)]
    for k in range(N_STROKES):
        seq += [(T_PUSH, 'push', k), (T_HOLD, 'hold', k), (T_RET, 'return', k), (T_GAP, 'rest', k)]
    seq += [(T_OUTRO, 'rest', N_STROKES - 1)]
    out, t0 = [], 0.0
    for dur, ph, k in seq:
        n = int(round(dur * FPS))
        for i in range(n):
            u = (i + 1) / n
            d = {'push': STROKE * smooth(u), 'hold': STROKE, 'return': STROKE * (1 - smooth(u)), 'rest': 0.0}[ph]
            out.append((t0 + (i + 1) / FPS, d, k, ph))
        t0 += n / FPS
    return out

# gear polygon in the hub frame
G0, G1, GOFF = B.P['gear_r0'], B.P['gear_r1'], math.degrees(B.GEAR_OFF)
def gear_r(theta_deg):
    u = (theta_deg - GOFF) % TOOTH
    if u < TOOTH / 2:
        a0, r0, a1, r1 = 0.0, G0, TOOTH / 2, G1
    else:
        a0, r0, a1, r1 = TOOTH / 2, G1, TOOTH, G0
    A = np.array([r0 * math.cos(math.radians(a0)), r0 * math.sin(math.radians(a0))])
    Bv = np.array([r1 * math.cos(math.radians(a1)), r1 * math.sin(math.radians(a1))])
    d = np.array([math.cos(math.radians(u)), math.sin(math.radians(u))])
    e = Bv - A
    return (A[0] * e[1] - A[1] * e[0]) / (d[0] * e[1] - d[1] * e[0])

PX, PY = B.post_xy
def pawl_tip_pts(phi_deg):
    a = B.a1 + math.radians(phi_deg)
    e = np.array([math.cos(a), math.sin(a)]); n = np.array([-e[1], e[0]])
    c = np.array([PX, PY]) + B.ARM * e
    return [c + s * B.PAWL_HALF_W * n for s in np.linspace(-1, 1, 7)]

def pawl_phi(rho_deg):
    """Smallest lift (phi <= 0, deg) that keeps the pawl tip outside the teeth."""
    R = math.radians(rho_deg)
    rot = np.array([[math.cos(R), -math.sin(R)], [math.sin(R), math.cos(R)]])
    for phi in np.arange(0.0, -45.0, -0.1):
        ok = True
        for p in pawl_tip_pts(phi):
            q = rot @ p
            if np.hypot(*q) < gear_r(math.degrees(math.atan2(q[1], q[0]))) + 0.003:
                ok = False; break
        if ok:
            return phi
    return -45.0

def kinematics(tl):
    beta, prev_rho, states = 0.0, 0.0, []
    for t, d, k, ph in tl:
        alpha = -360.0 * d / LEAD
        v = TOOTH * math.floor(prev_rho / TOOTH + 1e-9)
        driving = False
        if alpha - beta < v - 1e-9:
            beta = alpha - v; driving = True
        rho = alpha - beta
        prev_rho = rho
        adv = -beta / 360.0 * PITCH
        states.append(dict(t=t, d=d, k=k, ph=ph, alpha=alpha, beta=beta, rho=rho,
                           phi=pawl_phi(rho), adv=adv, driving=driving))
    return states


# ---------------------------------------------------------------- VTK helpers
def to_polydata(shape, tol, ang=0.2):
    verts, tris = shape.tessellate(tol, ang)
    pts = np.array([[v.x, v.y, v.z] for v in verts], dtype=np.float64)
    tri = np.asarray(tris, dtype=np.int64)
    cells = np.hstack([np.full((len(tri), 1), 3, np.int64), tri]).ravel()
    pd = vtk.vtkPolyData()
    p = vtk.vtkPoints(); p.SetData(nps.numpy_to_vtk(pts, deep=True)); pd.SetPoints(p)
    ca = vtk.vtkCellArray()
    ca.SetCells(len(tri), nps.numpy_to_vtkIdTypeArray(cells, deep=True)); pd.SetPolys(ca)
    nf = vtk.vtkPolyDataNormals(); nf.SetInputData(pd); nf.SetFeatureAngle(40); nf.SplittingOn()
    nf.ConsistencyOff(); nf.AutoOrientNormalsOff(); nf.Update()
    return nf.GetOutput()

def box_pd(x0, x1, y0, y1, z0, z1):
    c = vtk.vtkCubeSource(); c.SetBounds(x0, x1, y0, y1, z0, z1); c.Update()
    return c.GetOutput()

def make_actor(pd, rgb, clip=None, spec=0.25):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    if clip is not None:
        m.AddClippingPlane(clip)
    a = vtk.vtkActor(); a.SetMapper(m)
    pr = a.GetProperty(); pr.SetColor(*rgb); pr.SetSpecular(spec); pr.SetSpecularPower(30)
    pr.SetAmbient(0.12); pr.SetDiffuse(0.85)
    bp = vtk.vtkProperty(); bp.SetColor(*[c * 0.55 for c in rgb]); bp.SetAmbient(0.35); bp.SetDiffuse(0.5)
    a.SetBackfaceProperty(bp)
    return a

def place(actor, rot_deg=0.0, dz=0.0, pawl_phi_deg=None, carrier_deg=0.0):
    t = vtk.vtkTransform(); t.PostMultiply()
    if pawl_phi_deg is not None:
        t.Translate(-PX, -PY, 0); t.RotateZ(pawl_phi_deg); t.Translate(PX, PY, 0); t.RotateZ(carrier_deg)
    else:
        t.RotateZ(rot_deg)
    t.Translate(0, 0, dz)
    actor.SetUserTransform(t)

def spring_pd(z0, z1, coils=9.0, rm=6.4, rw=0.75):
    n = int(coils * 48)
    s = np.linspace(0, 1, n)
    ang = 2 * math.pi * coils * s
    zz = z0 + rw + (z1 - z0 - 2 * rw) * s
    pts = np.c_[rm * np.cos(ang), rm * np.sin(ang), zz]
    vp = vtk.vtkPoints(); vp.SetData(nps.numpy_to_vtk(pts, deep=True))
    line = vtk.vtkPolyLine(); line.GetPointIds().SetNumberOfIds(n)
    for i in range(n):
        line.GetPointIds().SetId(i, i)
    ca = vtk.vtkCellArray(); ca.InsertNextCell(line)
    pd = vtk.vtkPolyData(); pd.SetPoints(vp); pd.SetLines(ca)
    tube = vtk.vtkTubeFilter(); tube.SetInputData(pd); tube.SetRadius(rw); tube.SetNumberOfSides(14)
    tube.CappingOn(); tube.Update()
    return tube.GetOutput()

class View:
    def __init__(self, w, h, bg=(1, 1, 1)):
        self.rw = vtk.vtkRenderWindow(); self.rw.SetOffScreenRendering(1); self.rw.SetSize(w, h)
        self.rw.SetMultiSamples(8)
        self.ren = vtk.vtkRenderer(); self.ren.SetBackground(*bg); self.rw.AddRenderer(self.ren)
        self.w2i = vtk.vtkWindowToImageFilter(); self.w2i.SetInput(self.rw)
    def image(self):
        self.rw.Render(); self.w2i.Modified(); self.w2i.Update()
        img = self.w2i.GetOutput()
        w, h, _ = img.GetDimensions()
        arr = nps.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, -1)[::-1, :, :3]
        return Image.fromarray(np.ascontiguousarray(arr))


# ---------------------------------------------------------------- scene
def build_scene():
    print('tessellating ...')
    tol = {'03_cannula_hub': 0.01, '05_rocker_pawl': 0.01, '09_stylet': 0.02}
    pds = {k: to_polydata(w.val(), tol.get(k, 0.04)) for k, w in B.parts.items()}
    col = {k: v[1] for k, v in B.NAMES.items()}
    ROT_HUB = ('03_cannula_hub', '09_stylet')
    MOVE_CAP = ('06_push_cap_drive_nut', '08_top_port')

    # A: full device, half section of the outer parts (keep y >= 0)
    A = View(560, 930)
    clipA = vtk.vtkPlane(); clipA.SetOrigin(0, 0, 0); clipA.SetNormal(0, 1, 0)
    outer = ('01_housing', '02_bottom_plug', '06_push_cap_drive_nut', '07_top_cover_ring', '08_top_port', '10_sliding_base')
    actA = {k: make_actor(pds[k], col[k], clipA if k in outer else None) for k in pds}
    for a in actA.values():
        A.ren.AddActor(a)
    springA = make_actor(spring_pd(22, 80), (0.72, 0.72, 0.76), clipA, spec=0.6)
    A.ren.AddActor(springA)
    cam = A.ren.GetActiveCamera(); cam.ParallelProjectionOn()
    cam.SetFocalPoint(0, 0, 33); cam.SetPosition(-260, -560, 170); cam.SetViewUp(0, 0, 1)
    cam.SetParallelScale(142)
    A.ren.ResetCameraClippingRange()

    # B: ratchet top view (keep z <= 13.9 in the device frame)
    Bv = View(680, 560)
    clipB = vtk.vtkPlane(); clipB.SetNormal(0, 0, -1)
    keepB = ('01_housing', '02_bottom_plug', '03_cannula_hub', '04_spiral_shaft_carrier', '05_rocker_pawl', '09_stylet')
    actB = {k: make_actor(pds[k], col[k], clipB) for k in keepB}
    for a in actB.values():
        Bv.ren.AddActor(a)
    cam = Bv.ren.GetActiveCamera(); cam.ParallelProjectionOn()
    cam.SetFocalPoint(0, 0, 0); cam.SetPosition(0, 0, 300); cam.SetViewUp(0, 1, 0); cam.SetParallelScale(16.8)

    # C: threaded tip entering bone (half block behind the needle axis)
    C = View(680, 560)
    tip = B.tip
    S = tip                                     # bone surface at the cannula tip at t = 0
    cortex = make_actor(box_pd(-14, 14, 0, 9, S - CORTEX, S), (0.93, 0.86, 0.70), spec=0.05)
    marrow = make_actor(box_pd(-14, 14, 0, 9, S - 16, S - CORTEX), (0.70, 0.30, 0.28), spec=0.05)
    for a in (cortex, marrow):
        C.ren.AddActor(a)
    keepC = ('03_cannula_hub', '09_stylet')
    actC = {k: make_actor(pds[k], col[k]) for k in keepC}
    for a in actC.values():
        C.ren.AddActor(a)
    cam = C.ren.GetActiveCamera(); cam.ParallelProjectionOn()
    cam.SetFocalPoint(0, 0, S - 1.5); cam.SetPosition(-70, -330, S - 1.5); cam.SetViewUp(0, 0, 1)
    cam.SetParallelScale(C_SCALE)
    C.ren.ResetCameraClippingRange()

    for v in (A, Bv, C):
        lk = vtk.vtkLightKit(); lk.AddLightsToRenderer(v.ren)

    def update(st):
        dz = -st['adv']
        for acts in (actA, actB, actC):
            for k, a in acts.items():
                if k in ROT_HUB:
                    place(a, st['beta'], dz)
                elif k == '04_spiral_shaft_carrier':
                    place(a, st['alpha'], dz)
                elif k == '05_rocker_pawl':
                    place(a, dz=dz, pawl_phi_deg=st['phi'], carrier_deg=st['alpha'])
                elif k in MOVE_CAP:
                    place(a, 0, dz - st['d'])
                else:
                    place(a, 0, dz)
        springA.GetMapper().SetInputData(spring_pd(22 + dz, 80 - st['d'] + dz))
        clipB.SetOrigin(0, 0, 14.05 + dz)
        A.ren.ResetCameraClippingRange(); C.ren.ResetCameraClippingRange()
        return A.image(), Bv.image(), C.image()

    return update


# ---------------------------------------------------------------- charts
def chart(states, i, w=1360, h=330):
    t = np.array([s['t'] for s in states]); d = np.array([s['d'] for s in states])
    adv = np.array([s['adv'] for s in states])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(w / 100, h / 100), dpi=100)
    for ax in (a1, a2):
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(labelsize=10); ax.set_xlabel('time (s)', fontsize=10)
        ax.set_xlim(0, t[-1])
        ax.axvline(t[i], color='#444', lw=1)
    a1.plot(t, d, color='#8f8bcc', lw=1.2, alpha=0.35)
    a1.plot(t[:i + 1], d[:i + 1], color='#5b55b0', lw=2)
    a1.set_ylim(31, -1); a1.set_ylabel('cap pushed down (mm)', fontsize=10)
    a1.set_title('Push cap travel: 30 mm stroke, spring return', fontsize=11, loc='left')
    a2.plot(t, adv, color='#d08060', lw=1.2, alpha=0.35)
    a2.plot(t[:i + 1], adv[:i + 1], color='#c0502a', lw=2)
    a2.axhline(CORTEX, color='#b49a60', ls='--', lw=1.2)
    a2.text(0.2, CORTEX + 0.08, f'cortex {CORTEX:.0f} mm (model)', fontsize=9, color='#8a7440')
    a2.set_ylim(0, max(adv[-1], CORTEX) * 1.15); a2.set_ylabel('needle advance (mm)', fontsize=10)
    a2.set_title('Cannula thread advance: 1.0 mm per revolution', fontsize=11, loc='left')
    fig.tight_layout(pad=0.8)
    fig.canvas.draw()
    img = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
    plt.close(fig)
    return img


# ---------------------------------------------------------------- compose
def compose(st, imgs, ch):
    A, Bimg, C = imgs
    canvas = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(canvas)
    dr.rectangle([0, 0, W, 64], fill=(36, 40, 56))
    dr.text((20, 14), 'Self-tapping bone marrow needle: push-to-advance mechanism', font=font(28, True), fill='white')
    k = st['k']
    phase = {'push': 'PUSH', 'hold': 'PUSH', 'return': 'SPRING RETURN', 'rest': 'REST'}[st['ph']]
    stroke_txt = f'Stroke {k + 1} of {N_STROKES}  ·  {phase}' if k is not None else 'At rest'
    dr.text((W - 20, 18), stroke_txt, font=font(24, True), fill=(255, 210, 120), anchor='ra')

    canvas.paste(A, (0, 150)); canvas.paste(Bimg, (560, 150)); canvas.paste(C, (1240, 150))
    canvas.paste(ch, (560, 750))
    dr.line([(560, 70), (560, H)], fill=(220, 220, 225), width=2)
    dr.line([(1240, 70), (1240, 745)], fill=(220, 220, 225), width=2)
    dr.line([(560, 747), (W, 747)], fill=(220, 220, 225), width=2)

    t1, t2 = font(20, True), font(16)
    dr.text((16, 80), 'Whole device, half section', font=t1, fill=(30, 30, 30))
    dr.text((16, 106), f"cap {st['d']:5.1f} mm down", font=t2, fill=(70, 70, 70))
    dr.text((16, 128), f"spiral shaft {st['alpha']:7.1f}°", font=t2, fill=(70, 70, 70))
    dr.text((16, 150), 'thumb on the cap · fingers under the handle wings', font=font(14), fill=(110, 110, 110))

    dr.text((576, 80), 'Ratchet and pawl (top view)', font=t1, fill=(30, 30, 30))
    if st['ph'] in ('push', 'hold'):
        pawl = 'pawl DRIVING the cannula' if st['driving'] else ('pawl seated' if st['ph'] == 'hold' else 'taking up slack')
    elif st['ph'] == 'return':
        pawl = 'pawl clicking over teeth: cannula stays put'
    else:
        slack = st['rho'] % TOOTH
        pawl = 'pawl seated in tooth gap' if min(slack, TOOTH - slack) < 0.05 else \
            f"pawl resting on a tooth flank ({slack:.0f}° slack before it drives)"
    dr.text((576, 106), pawl, font=t2, fill=(150, 70, 30) if 'DRIVING' in pawl else (70, 70, 70))
    dr.text((576, 128), f"cannula {st['beta']:7.1f}°  ({-st['beta'] / 360:.2f} rev)", font=t2, fill=(70, 70, 70))
    dr.text((576, 722), 'clockwise from the top = drives the right-hand thread in', font=font(14), fill=(110, 110, 110))

    dr.text((1256, 80), 'Threaded tip in bone (section)', font=t1, fill=(30, 30, 30))
    dr.text((1256, 106), f"advance {st['adv']:.2f} mm", font=t2, fill=(70, 70, 70))
    status = 'through the cortex into marrow' if st['adv'] >= CORTEX else 'tapping into cortical bone'
    dr.text((1256, 128), status, font=t2, fill=(150, 40, 40) if st['adv'] >= CORTEX else (70, 70, 70))
    pxmm = 560 / (2 * C_SCALE)
    x0, y0 = 1880 - int(2 * pxmm), 668
    dr.rectangle([x0, y0, 1880, y0 + 5], fill='white')
    dr.text((x0 + pxmm, y0 + 9), '2 mm', font=font(15, True), fill='white', anchor='ma')
    dr.text((1256, 722), 'stylet trocar leads · threads pull the needle in', font=font(14), fill=(110, 110, 110))
    return canvas


def main():
    tl = timeline()
    states = kinematics(tl)
    print(f'{len(states)} frames; final advance {states[-1]["adv"]:.2f} mm, cannula {states[-1]["beta"]:.0f} deg')
    update = build_scene()
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)
    only = int(os.environ.get('ONLY_FRAME', '-1'))
    for i, st in enumerate(states):
        if only >= 0 and i != only:
            continue
        frame = compose(st, update(st), chart(states, i))
        frame.save(os.path.join(FRAMES, f'f{i:04d}.png'))
        if i % 40 == 0:
            print('frame', i)
    if only >= 0:
        return
    mp4 = os.path.join(OUT, 'needle_mechanism.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(FRAMES, 'f%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-movflags', '+faststart', mp4], check=True)
    gif = os.path.join(OUT, 'needle_mechanism.gif')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(FRAMES, 'f%04d.png'),
                    '-vf', 'fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer',
                    gif], check=True)
    shutil.rmtree(FRAMES)
    print('wrote', mp4, gif)


if __name__ == '__main__':
    main()
