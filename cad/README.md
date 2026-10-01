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
| `preview.png` | Rendered check views: cut-away assembly, thread tip, ratchet and pawl, spiral shaft in nut. |

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
- Volumes match the original STL generator within 0.1% for 8 of the 10 parts. The cannula hub is 1% lower because its
  ratchet teeth now have straight flanks. The sliding base is 2.7% lower because the old STL counted the volume where
  the foot, sleeve and ears overlap twice.
- **Pairwise interference check over all 45 part pairs: zero overlap.** The ratchet phase was trimmed by 0.5° so the
  pawl tip seats in a tooth valley with about 0.01 mm clearance instead of digging into a flank.

## Adding mates for a motion study

A STEP file stores part positions but cannot store SolidWorks mates. Your components arrive already in place, so
adding mates does not move anything. In the FeatureManager, right-click each component and choose **Float**
(keep `01_housing` **Fixed**), then add:

| # | Mate | Pick |
|---|---|---|
| 1 | Concentric | `02_bottom_plug` bore Ø10.6 ↔ `01_housing` outer Ø38 face |
| 2 | Coincident | top face of the plug flange ↔ bottom face of the housing (z = 0) |
| 3 | Concentric | `03_cannula_hub` spigot Ø10 ↔ plug bore Ø10.6 (hub is free to rotate) |
| 4 | Distance 0.2 | bottom face of the ratchet gear ↔ top face of the plug |
| 5 | Concentric | `04_spiral_shaft_carrier` shaft Ø10 ↔ housing ledge bore Ø12 |
| 6 | Distance 0.5 | top face of the carrier disc ↔ underside of the housing ledge |
| 7 | Concentric | `05_rocker_pawl` bore Ø3.2 ↔ pawl post Ø3.0 on the carrier |
| 8 | Distance 0.4 | top face of the pawl ↔ underside of the carrier disc |
| 9 | Concentric | `06_push_cap_drive_nut` plunger OD Ø24 ↔ housing outer face |
| 10 | Coincident | side face of a nut ear ↔ matching side wall of the housing key slot (stops rotation) |
| 11 | Limit distance 28–58 | bottom face of the nut ↔ top face of the housing ledge (58 = at rest, 28 = fully pushed, giving the 30 mm stroke) |
| 12 | **Screw** | nut ↔ shaft, 50 mm/rev, **reverse direction** for left-hand. Drives the shaft from the push. |
| 13 | Concentric + Coincident | `07_top_cover_ring` ↔ housing bore; underside of the lip ↔ housing top face, plus Coincident between a key side and a slot wall |
| 14 | Concentric + Coincident | `08_top_port` spigot Ø8.8 ↔ cap counterbore Ø9; port flange underside ↔ top face of the thumb pad |
| 15 | Concentric + Coincident | `09_stylet` rod ↔ cannula bore; a hex flat on the stylet key ↔ a hex flat in the hub socket; bottom face of the hex key ↔ socket floor |
| 16 | Concentric | `10_sliding_base` sleeve bore ↔ housing outer face (leave the axial position free, or add a Distance to set exposed needle length) |

To drive the cannula during the push stroke, add a **Gear mate 1:1** between the shaft and the hub for a quick animation.
For true one-way ratchet action, use *SolidWorks Motion* with **Contact** between the pawl and the gear teeth, a
torsion spring on the pawl, and a **Linear Spring** between the ledge top and the nut bottom.

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
