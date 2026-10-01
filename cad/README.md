# Self-tapping bone marrow needle: CAD model (STEP, SolidWorks-ready)

Native solid model of the 11 G × 4 in self-tapping needle: 10 parts, assembled in the at-rest position.
These are true B-rep solids with real cylinders, planes and helices, not faceted meshes. In SolidWorks you can
select faces, use concentric mates, measure, section and run Interference Detection on them.

| File | What it is |
|---|---|
| `step/00_full_assembly.step` | **Open this one.** STEP assembly with 10 named, colored components in their assembled positions. |
| `step/parts/NN_*.step` | One STEP per part. Each keeps the assembly origin, so a part inserted at the origin lands in its assembled spot. |
| `stl/NN_*.stl` | STL exported from the solids (0.01 mm chord tolerance), for 3D printing. |
| `build_step.py` | Parametric source (CadQuery). Edit a dimension in `P` and re-run to regenerate everything. |
| `build_report.json` | Volume, bounding box and validity of every part from the last build. |
| `solidworks/AddNeedleMates.bas` | SolidWorks macro that adds all motion mates to the opened assembly (see *Simulating*). |
| `animation/needle_mechanism.mp4` (`.gif`) | 20 s animation of six push strokes, rendered from the CAD geometry by `animate.py`. |
| `preview.png`, `handle_preview.png` | Rendered check views: full assembly, cut-away, thread tip, ratchet and pawl, spiral shaft in nut, handle. |

Units are **mm**. The needle axis is the **Z axis**, and z = 0 is the bottom face of the housing. SolidWorks uses Y-up
by default, so after opening the assembly the needle will lie horizontally. Use *View › Modify › Orientation* (or
rotate it) to view it vertically.

## Opening in SolidWorks

1. **File › Open**, set the file type to *STEP AP203/214/242 (\*.step;\*.stp)* and pick `step/00_full_assembly.step`.
2. If SolidWorks asks, choose **Assembly** as the template and **Millimeters** as the units.
3. SolidWorks creates an `.SLDASM` plus 10 `.SLDPRT` files, one per component. Click **Save All** and save them to a folder of your choice.
4. If *Import Diagnostics* offers to run, you can say yes, but there should be nothing to repair: every body was checked as valid closed geometry.

Each `.SLDPRT` is an *Imported1* body, so there is no feature tree to edit. You can still add new features on top
(cuts, fillets, holes, text). To change a base dimension, edit `build_step.py` and re-export (see below).

## Verified fit

- Every part is a single valid solid.
- Volumes match the original STL generator within 0.1% for 7 of the 10 parts. The housing is larger only because of the new handle. The cannula hub is 1% lower because its
  ratchet teeth now have straight flanks. The sliding base is 2.7% lower because the old STL counted the volume where
  the foot, sleeve and ears overlap twice.
- **Pairwise interference check over all 45 part pairs: zero overlap.** The ratchet phase was trimmed by 0.5° so the
  pawl tip seats in a tooth valley with about 0.01 mm clearance instead of digging into a flank.

## Simulating the mechanism in SolidWorks

A STEP file stores part positions but cannot store mates, and only SolidWorks can write `.SLDASM`. The macro
`solidworks/AddNeedleMates.bas` therefore adds the mates inside SolidWorks. The parts are already in place, so
nothing moves when the mates are added.

### 1. Add the mates (one-time, about 1 minute)

1. Open `step/00_full_assembly.step` as described above.
2. **Tools › Macro › New…** and save it anywhere, for example as `AddNeedleMates.swp`. The VBA editor opens.
3. In the VBA editor, use **File › Import File…** and pick `solidworks/AddNeedleMates.bas`. Alternatively, paste its contents into the module.
4. Put the cursor inside `Sub main()` and press **F5**. A message box lists every mate as OK or FAIL.
5. **File › Save As** › *Assembly (\*.sldasm)*. This is your working simulation file.

| Mates the macro adds | Effect |
|---|---|
| Housing, bottom plug, cover ring and sliding base set to **Fixed** | Static frame |
| Hub: concentric in the plug bore, plus Front-plane coincident | Cannula spins in place |
| Shaft: concentric in the ledge bore, plus Front-plane coincident | Spiral shaft spins in place |
| Pawl: concentric on the post (rotation locked), plus Front-plane coincident | Pawl rides on the carrier in the drive position |
| Cap: concentric (rotation locked) and **limit distance 28–58 mm** from nut to ledge | Cap slides a 30 mm stroke and cannot turn |
| **Screw** nut ↔ shaft, 50 mm per revolution | Pushing the cap turns the shaft 0.6 rev |
| **Gear 1:1** shaft ↔ hub | Shaft turns the cannula (drive stroke) |
| Port: concentric and coincident in the cap counterbore | Port rides with the cap |
| Stylet: concentric (rotation locked) in the hub bore, hex key seated | Stylet turns with the cannula |

**Direction check (do this once).** Drag the push cap down with the mouse. Seen from the top, the purple shaft must
turn **clockwise**, with the nut pins following the spiral grooves. If the pins cut across the grooves instead, go
to *Mates*, right-click **Spiral drive (nut-shaft)** › Edit Feature and toggle **Reverse**. The orange hub must turn the
same way as the shaft, so the pawl tip stays in its tooth gap. If it turns the other way, toggle **Reverse** on
**Ratchet drive (shaft-hub)**.

The macro finds each face by its geometry (cylinder radius and axis, or plane height). It could not be run here
because SolidWorks wasn't available, so it is untested. If a mate reports FAIL, add that mate by hand using the table
above; every face it needs is named there.

### 2. Run the push stroke

- **Quick check:** drag the thumb pad. The cap slides, the shaft and cannula turn, and the stroke stops at 30 mm.
- **Animation:** open the **Motion Study 1** tab and set the study type to *Animation* (or *Basic Motion*). Add a
  **Linear Motor** on the top face of the thumb pad, direction down, type **Distance**, 30 mm, from 0 s over 1 s.
  Then **Calculate** and **Play**. The cannula turns 0.6 rev, which is 0.6 mm of thread advance per push.
  Add *Interference Detection* or a section view to watch the pins in the grooves.
- **True one-way ratchet with spring return:** this needs the *SOLIDWORKS Motion* add-in and a *Motion Analysis* study.
  1. Suppress the gear mate.
  2. Add **Contact** between the pawl and the cannula hub.
  3. Add a **Linear Spring** between the ledge top and the nut bottom (free length 65 mm; use the rate of the spring you buy).
  4. Add a small **Torsion Spring** on the pawl.

  The cap then springs back and the pawl clicks over the teeth, so the cannula stays where the push left it.

## Animation

`animation/needle_mechanism.mp4` shows six push strokes rendered from this model:

| Panel | Shows |
|---|---|
| Left | Half-section of the whole device, with the return spring drawn in. |
| Middle | Top view of the ratchet and pawl. |
| Right | The threaded tip in a section of bone: 3 mm cortex over marrow. |
| Bottom | Charts of cap travel and needle advance. |

The kinematics come straight from the geometry:

- **Push:** the cap travels 30 mm and the 50 mm left-hand spiral turns the shaft −216°, clockwise seen from the top.
- **Return:** the pawl rocks out over the teeth and the cannula holds its position.
- **Slack:** 216° is not a whole number of 15° teeth. After the first stroke, each push takes up 6° of slack before
  the pawl engages, so steady-state advance is 210° per push, or 0.58 mm with the 1.0 mm-pitch thread.
- **Total:** six pushes give 3.52 mm of advance, enough to cross a 3 mm cortex.

To re-render after changing the model, run `xvfb-run -a python animate.py` (about 4 minutes; needs `vtk` and `ffmpeg`).

## Finger-grip handle

The housing has a syringe-style handle at the top: two wings along ±X, 104 mm tip to tip, 22 mm wide and 12 mm
thick, with Ø24 finger scallops (2 mm deep) on the underside and 2 mm rounded edges. Hook your index and middle
fingers under the wings and press the cap with your thumb. The grip span from the wing underside to the top of the
thumb pad is 53 mm at rest and 23 mm at the end of the stroke.

- The wings are part of the housing, not the press-fit cover ring, so finger pull goes straight into the housing wall.
- They sit at ±X, clear of the internal key slots (±Y) and of the cap, which stops 6 mm above them.
- The wings now limit how far the sliding base can ride up. The maximum exposed needle length goes from about 99 mm to about 92 mm (range now about 14–92 mm).
- All handle sizes are in the `HANDLE` dict in `build_step.py`. Set `HANDLE = None` to build the plain housing.
- See `handle_preview.png`.

## Parts to buy (not modeled)

- Compression spring: OD ≤ 15, ID ≥ 10.5, free length about 65 mm, compressing to ≤ 28 mm.
- Light pawl spring (small torsion spring or elastic band).
- Silicone slit disc Ø9 × 1.5 to fit in the cap counterbore.
- M3 × 20 screw and nut for the base clamp.
- Rubber pad Ø56 for the foot.

## Regenerating

```
pip install cadquery
python build_step.py
```

Building takes about 15 s. All dimensions live in the `P` dictionary and the per-part sections of `build_step.py`.
The original mesh generator and its build sheet are kept in `../reference/` for comparison.
