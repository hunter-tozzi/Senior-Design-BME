# Self-tapping bone marrow needle — part files and SolidWorks build sheet

All dimensions in **mm**. Sized to a standard adult **Jamshidi 11 G × 4 in** needle (cannula OD 3.05, ID 2.39, working length 101.6).
Axis = Z. Datum z = 0 is the bottom face of the housing. Every STL keeps its assembly X/Y position and is shifted so its lowest point is z = 0; `00_full_assembly.stl` has all parts in their assembled positions.

## Opening the STLs in SolidWorks
File › Open › file type *Mesh Files (*.stl)* › **Options**: Import as *Solid body*, units *Millimeters*.
They open as faceted solids: good for checking size, fit and appearance, but round faces are made of flat facets, so concentric mates and feature edits won't work cleanly. For a fully operating assembly, model each part natively from the table below (about 15–30 min per part) and use the STL as an overlay to check against.

## How it works (one push stroke)
Push cap down 30 mm → drive nut (keyed in housing slots, cannot rotate) forces the 2-start spiral shaft to turn 0.6 rev clockwise (seen from top) → carrier on the shaft drives the rocker pawl → pawl turns the ratchet hub and cannula → right-hand buttress threads advance 0.6 mm into cortex. Spring returns the cap; shaft turns back but the pawl clicks over the teeth, so the cannula stays put. About 5–8 pushes cross a 3–5 mm cortex.

## Part dimensions

| # | Part | Key dimensions |
|---|---|---|
| 01 | Housing | Tube OD 38 / ID 32 × 100 tall. Spring ledge z 18–22, bore Ø12. Two key slots 180° apart (at ±Y), z 49 → top, cut to R 17.3, angular width ±0.40 rad (~13.5 mm chord). |
| 02 | Bottom plug | Flange Ø38 × 2 (z −2…0) + press-fit body Ø31.9 × 6 (z 0…6). Bore Ø10.6 (hub bearing). |
| 03 | Cannula + ratchet hub (one piece) | Cannula OD 3.05 / ID 2.39, tip at z −103.6 (101.6 below plug face). Spigot Ø10.0, z −2…6.2. Ratchet gear z 6.2…14.0: 24 symmetric V teeth, root Ø16, tip Ø19. Bore Ø2.39 through. Hex socket 3.5 AF × 3 deep at top (stylet key). **Threads:** last 6.0 mm, right-hand, pitch 1.0, depth 0.40 (major Ø3.85). Buttress profile per pitch: lower flank rises in 0.08 (near-flat, faces tip, cuts going in), upper flank slopes back down over 0.67 (glides out), root flat 0.25. Tapered lead-in over first 1.5 mm. Two cutting flutes 180° apart, ±0.45 rad wide, first 3.0 mm. |
| 04 | Spiral shaft + pawl carrier | Carrier cup ID 29.6 / OD 31.2, z 6.2…14.2. Disc Ø31.2, z 14.2…17.5 (bears on ledge underside). Shaft Ø10.0 to z 100. Through bore Ø4.2 (instrument channel). Two helical grooves (2-start), depth 1.2, width ±0.45 rad, **lead 50 mm left-hand**, z 46…100. Pawl post Ø3.0 at (X 12.2, Y 0), hangs from disc to z 6.4. |
| 05 | Rocker pawl | Bore Ø3.2 on post, hub ring Ø4.6, thickness 7 (z 6.8…13.8). Two arms 1.0 wide, reaching 3.9 mm from pivot, each 65° either side of the line to the gear center. Drive position: rotated 44°, tip A seated at R 8.67 in a tooth valley, arm B clear (R ≥ 13.2). Reverse position: rotate 88° to the other stop. |
| 06 | Push cap + drive nut (one piece) | Nut z 80…94 (at rest): OD 31.4 with two ears to R 17.0 riding in the housing slots; bore Ø10.5 with two helical pins (to R 4.0, ±0.28 rad) on the same 50 mm LH lead. Plunger OD 24 / ID 10.6 up to z 136. Thumb pad Ø32 × 5 (z 136…141): bore Ø5.0, counterbore Ø9.0 × 3 deep for the seal. |
| 07 | Top cover ring | Press-fit OD 31.9 with keys into the slots, ID 26, z 94…100, lip Ø38 × 1.5 on top. Stops the nut at rest. |
| 08 | Top port | Spigot Ø8.8 × 1.5 (into counterbore, clamps seal), flange Ø12 × 1.5, boss Ø7.8 × 8 with bore Ø4.2 → Ø4.6 (approx. female Luer; glue in a commercial Luer fitting for real use). |
| 09 | Stylet | Rod Ø2.30. 3-facet trocar point extends 2.5 past cannula tip. Hex key 3.3 AF × 3 seats in the hub socket so the stylet turns with the cannula. Knob Ø12 × 10. Overall ≈ 281 mm. |
| 10 | Sliding depth-lock base | Split sleeve ID 38.5 / OD 44 × 100, slit ~2 mm. Foot Ø56 × 3, bore Ø6. Two clamp ears with Ø3.4 hole for an M3 screw near the top. Exposed needle below foot adjustable ≈ 14–99 mm (thin to large patients). |

## Buy, don't print
- Compression spring: OD ≤ 15, ID ≥ 10.5, free length ~65, must compress to ≤ 28 (30 mm travel).
- Light pawl spring (small torsion spring or elastic) to hold tip A against the teeth.
- Silicone slit disk Ø9 × 1.5 (or a Luer-activated needleless valve).
- M3 × 20 screw + nut for the base clamp; rubber/silicone pad Ø56 for the foot.
- For a working needle: stainless 11 G tube and Ø2.3 rod, machined threads. Printed cannula/stylet are display-only at true scale; print at 3–5× scale for a demo of the tip.

## Mates for a working motion study
1. Housing **Fixed**. Everything else **Concentric** to the housing axis (pawl: concentric to the post).
2. Plug flange top **Coincident** with housing bottom.
3. Hub gear bottom **Distance 0.2** above plug top; hub **Concentric** in plug bore (free to rotate).
4. Carrier disc top **Distance 0.5** below ledge underside.
5. Nut: **Slot/Parallel** mate between an ear face and slot wall (no rotation) + **Distance** limit mate 0…30 for the stroke.
6. **Screw mate** nut ↔ shaft: 50 mm per revolution, left-hand. This drives the shaft from the push without needing groove contact.
7. Shaft ↔ hub: for a simple animation use a **Gear mate 1:1** (push stroke only). For true one-way action use *Motion Analysis* (SolidWorks Motion add-in) with **Contact** between pawl and gear teeth and a torsion spring on the pawl.
8. Spring: Motion Analysis **Linear Spring** between ledge top and nut bottom.
9. Optional: **Screw mate** cannula ↔ a bone block, 1.0 mm/rev right-hand, to show the needle advancing per stroke.

## Known v1 simplifications
- Reverse is set by rotating the pawl to its other stop; the external in/out selector collar still needs to be designed.
- Depth marks on the housing are not modeled (add as a sketch-text cut).
- Clearances (0.2–0.4 mm) suit SLA/resin printing; open them up ~0.1 mm for FDM.
