# Braille Business Card Embossing Plates — Beginner’s Guide

Create tactile, readable braille on ordinary business-card paper with just a 3-D printer, a clamp, and a few minutes in the free program **OpenSCAD**.  This guide walks you—*even if you have never 3-D printed before*—through designing, printing, and using custom braille Emboss & Counter plates.

---

## 1. What You’ll Make

| Part | Purpose |
|------|---------|
| **Emboss Plate** (raised dots) | Pushes the braille dots *out* of the paper |
| **Counter Plate** (matching recesses) | Supports the paper so dots keep their shape |

Press a card between the two plates and you have braille you can feel and read.

> Vocabulary for experts: Emboss = male/positive, Counter = female/negative.

---

## 2. Things You Need

| Item                         | Notes |
|------------------------------|-------|
| Computer (Win/Mac/Linux)     | Install **OpenSCAD** (free) & your favourite slicer (Cura, PrusaSlicer, etc.) |
| 3-D printer                  | 0.4 mm nozzle, PLA or PETG filament recommended |
| Clamp / small arbor press    | To squeeze the plates together (even a hand-screw clamp works) |
| Business-card paper          | Use the exact card stock you plan to distribute |
| Digital calipers *(optional)*| Helpful for measuring dot size after your first test |

---

## 3. 5-Minute Quick-Start

1. **Open** `Braille Business Card STL Generator.scad` in OpenSCAD.
2. **View → Customizer**  ➜ fill in your text *in English*.
   - Keep **Grade** set to **Grade 2 (contracted)** unless you have a special reason.
   - Leave all sizes *as-is* for your very first test.
3. **Design → Render (F6)** → **File → Export → STL**.
4. Slice & print both plates flat on the bed.
5. Place a single card between plates & clamp firmly for a few seconds.
6. Feel / measure the dots.  Happy? Great!  Need tweaks?  See Section 7.

> **Tip** Always test with the same paper thickness you’ll use later.  Paper controls the final dot height more than the plastic settings do.

---

## 4. Video Tutorial

A short screen-recording + live demo will be published here:
`👉 [YouTube link – coming soon]`

The video covers:
1. Opening the design & entering text
2. Selecting Grade 2 vs 1
3. Exporting STL, slicing, printing
4. Assembling the full tool
5. Embossing a card & inspecting results

---

## 5. Understanding Grade 1 vs Grade 2

*Regulatory guidance in the US, UK, and elsewhere says use **Grade 2** for English braille by default.*  Grade 1 (uncontracted) is normally reserved for:
- Education / literacy teaching
- Short labels where contractions could confuse
- Situations prescribed by local regulations

Therefore the Customizer defaults to **Grade 2**.

---

## 6. Why the Default Sizes?  (Dots, Spacing & Sources)

The design aims to **shape the *paper* dots** so they land near widely-accepted targets for paper embossing.

Recommended on-paper dimensions (Specification 800 §3.2):

| Parameter                                             | Target |
|-------------------------------------------------------|--------|
| Dot height                                            | 0.019 in (0.48 mm) |
| Dot base diameter                                     | 0.057 in (1.44 mm) |
| Dot-to-dot distance *within a cell* (horiz/vert)      | 0.092 in (2.34 mm) |
| Cell-to-cell distance (centre-to-centre)               | 0.245 in (6.20 mm) |
| Line spacing (centre-to-centre of nearest dots)       | 0.400 in (10.16 mm) |

Sources & further reading:
- Braille Authority of North America — *Size and Spacing of Braille Characters* [1]
- NLS, Library of Congress — *Specification 800: Braille Books & Pamphlets* [2]
- ICC/ANSI A117.1-2003 (Accessible & Usable Buildings) pp. 151–163
- U.S. Access Board — ABA & ADA Accessibility Guidelines (Chapter 7 Signs)

> *Important* Because card stock varies, *your* embossed dots may be slightly larger or smaller.  That’s normal—start with defaults, then adjust.

---

## 7. Test → Measure → Adjust (Recommended Workflow)

| Step | What to do |
|------|------------|
| 1. Print a **small test plate** | One or two words is enough |
| 2. **Emboss** a single card | Even, firm pressure |
| 3. **Inspect** | Feel the dots; use calipers if available |
| 4. **Adjust parameters** in the Customizer | See table below |
| 5. **Re-print & re-test** | One or two iterations usually nails it |

Common tweaks:

| Symptom | Try this |
|---------|----------|
| Dots too flat | Increase **Dot Height** or press harder |
| Dots feel sharp | Increase **Apex Rounding** or lower Dot Height |
| Cells crowd | Increase **Cell Advance** or reduce **Dot Diameter** |
| Plates stick together | Increase **Counter Clearance** or add small **Draft** |

---

## 8. Printing Tips

- **Material** PLA is fine; PETG is tougher.  Use 3–4 perimeters and 40 % infill for stiffness.
- **Orientation** Print plates *flat* on the bed, embossed surface facing *up*.
- **Quality** A slower outer-wall speed (≲ 30 mm/s) produces smoother dots.

---

## 9. Safety & Handling

- Keep fingers clear of the clamp/press.
- Emboss with controlled force; over-pressing can tear paper or squash dots.

---

## 10. File-Naming & On-Part Labels (Optional but Handy)

Example STL names:
- `BRL_EmbossPlate_Raised_UEB-G2_88x51mm_Dot0p6.stl`
- `BRL_CounterPlate_Recessed_Universal_88x51mm.stl`

Engraved rim labels avoid mix-ups: **EMBOSS (RAISED) — MIRRORED** vs **COUNTER (RECESSED)**.

---

## 11. Acknowledgments

Huge thanks to **Tobi Weinberg** for kick-starting the project and introducing me to Cursor AI.  Without Tobi’s time, effort, and encouragement this program would not exist.

Attribution: This project was originally based on
[tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator/tree/main) and further evolved from my earlier variant
[BrennenJohnston/braile-card-generator](https://github.com/BrennenJohnston/braile-card-generator/blob/brennen-dev/README.md) (branch `brennen-dev`).

---

## 12. References

[1] BANA — Size & Spacing of Braille Characters: https://brailleauthority.org/size-and-spacing-braille-characters  
[2] NLS Specification 800 (PDF): https://www.loc.gov/nls/wp-content/uploads/2019/09/Spec800.11October2014.final_.pdf  
[3] U.S. Access Board — 2010 ADA Standards: https://www.access-board.gov/aba/guides/chapter-7-signs/  
[4] ICC/ANSI A117.1-2003 — Accessible & Usable Buildings & Facilities

