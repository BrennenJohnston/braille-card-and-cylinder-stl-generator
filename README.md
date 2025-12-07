# Braille Business Card & Cylinder STL Generator 🎯

**Create professional, tactile braille business cards and 3D objects with 3D-printable embossing plates**

This web application generates STL files for 3D-printable braille embossing and counter plates. Simply enter your text, and the system automatically translates it to braille and creates the precise 3D models needed for embossing professional business cards or creating cylindrical braille objects.

---

## 1. What You'll Make

| Shape | Components | Purpose |
|-------|------------|---------|
| **Business Cards (Flat)** | Embossing Plate + Counter Plate | Traditional flat business cards with raised braille dots |
| **Cylinders** | Cylinder Shell + Counter Plate | 3D cylindrical objects with curved braille surface |

**Business Card Process**: Place paper between plates → Apply pressure → Get professional braille cards!
**Cylinder Process**: Print cylinder with integrated braille dots for 3D tactile objects!

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

### Web Application (Recommended)
1. **Local dev**: run `python backend.py` and open `http://localhost:5001`
2. **Vercel**: connect repo and deploy; serverless entry is `wsgi.py`
2. **Enter your text** (up to 4 lines)
3. **Select braille grade** (Grade 2 recommended for most users)
4. **Choose shape**: Business card (flat) or cylinder
5. **Click Generate** to create STL files
   - ✨ **New**: Generation happens in your browser (no timeouts!)
   - Automatic fallback to server if needed
6. **Download** and 3D print your files
7. **Test** with actual card stock and adjust if needed

> **⚡ Client-Side Generation**: STL files are now generated in your browser using advanced CSG algorithms. This means no timeout limits, faster iteration, and works perfectly on Vercel's free tier. See [CLIENT_SIDE_CSG_DOCUMENTATION.md](docs/development/CLIENT_SIDE_CSG_DOCUMENTATION.md) for details.

### For Business Cards:
- Print both emboss and counter plates
- Place card stock between plates
- Apply firm, even pressure
- Check results and iterate if needed

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
| 4. **Adjust parameters** using Expert Mode | See table below |
| 5. **Re-print & re-test** | One or two iterations usually nails it |

### 🔄 NEW: Cylinder Shape Feature

**Create 3D cylindrical objects with curved braille surfaces:**

| Parameter | Purpose | Typical Range |
|-----------|---------|---------------|
| **Diameter** | Cylinder width | 20mm - 50mm |
| **Height** | Cylinder length | 30mm - 100mm |
| **Cutout Radius** | Interior polygonal hole | 0mm - 15mm |
| **Seam Offset** | Rotation adjustment | 0° - 360° |

**Use Cases:** Tactile learning tools, decorative objects, cylindrical labels, educational models

Common tweaks:

| Symptom | Try this |
|---------|----------|
| Dots too flat | Increase **Dot Height** or press harder |
| Dots feel sharp | Increase **Apex Rounding** or lower Dot Height |
| Cells crowd | Increase **Cell Advance** or reduce **Dot Diameter** |
| Plates stick together | Increase **Counter Clearance** or add small **Draft** |
| Cylinder text wraps | Reduce diameter or shorten text |

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

## 13. Developer Notes

- Backend: single Flask app in `backend.py` used both locally and on Vercel via `wsgi.py`.
- Frontend: served from `templates/index.html` with static assets in `static/`.
- Translation: browser-side Liblouis via web worker `static/liblouis-worker.js` and tables under `static/liblouis/tables/`.
- Endpoints: `/liblouis/tables`, `/generate_braille_stl`, `/generate_counter_plate_stl`.

### Local development
```bash
pip install -r requirements.txt
python backend.py  # opens http://localhost:5001
```

### Vercel deployment
- Project uses `vercel.json` and `wsgi.py` with `@vercel/python`.
- Install step: `pip install -r requirements_vercel.txt` (minimal set for serverless).
- Static liblouis tables are bundled and loaded on-demand from `static/liblouis/tables/` in a web worker.
- Matplotlib is optional at runtime. In serverless, character markers gracefully fall back when matplotlib isn't present.

### Serverless considerations
- `.vercelignore` excludes heavy directories like `third_party/` and `node_modules/` to keep function size small.
- `backend.py` defers matplotlib imports inside functions to avoid cold-start bloat and missing dependency failures.
- Endpoints exposed: `/`, `/health`, `/liblouis/tables`, `/generate_braille_stl`, `/generate_counter_plate_stl`.

---

## 12. Architecture: Client-Side CSG

### Why Client-Side?

STL generation now happens **in your browser** using the `three-bvh-csg` library:
- ✅ **No timeout limits** - Perfect for Vercel's free tier (no 10-60 second limits)
- ✅ **Fast iteration** - No cold starts or serverless delays
- ✅ **Zero server dependencies** - No need for Blender, OpenSCAD, or manifold3d binaries
- ✅ **Better scalability** - Each user's browser does the work
- ✅ **Automatic fallback** - Falls back to server if browser doesn't support it

### How It Works

```
Browser → Fetch geometry spec (JSON) → CSG Worker → STL file
   ↓ (on error)
   └──→ Server-side generation (fallback)
```

1. **User enters text** → Braille translation (client-side via liblouis)
2. **Click Generate** → Fetch geometry specification from `/geometry_spec` endpoint
3. **Web Worker** builds 3D primitives and performs boolean operations
4. **Export STL** directly in browser
5. **Render preview** and offer download

### Browser Compatibility

- ✅ Chrome 80+, Edge 80+, Firefox 114+, Safari 15+
- ⚠️ Older browsers automatically fall back to server generation
- 📦 Bundle size impact: ~215 KB (60-80 KB gzipped)

### Configuration

Feature flag in `public/index.html`:
```javascript
let useClientSideCSG = true; // Set to false to force server-side
```

### Documentation

- **Full Architecture**: [CLIENT_SIDE_CSG_DOCUMENTATION.md](docs/development/CLIENT_SIDE_CSG_DOCUMENTATION.md)
- **Testing Guide**: [CLIENT_SIDE_CSG_TEST_PLAN.md](docs/development/CLIENT_SIDE_CSG_TEST_PLAN.md)
- **Optional Enhancement**: Client-side manifold3d (WASM) for maximum robustness

---

## 13. References

[1] BANA — Size & Spacing of Braille Characters: https://brailleauthority.org/size-and-spacing-braille-characters
[2] NLS Specification 800 (PDF): https://www.loc.gov/nls/wp-content/uploads/2019/09/Spec800.11October2014.final_.pdf
[3] U.S. Access Board — 2010 ADA Standards: https://www.access-board.gov/aba/guides/chapter-7-signs/
[4] ICC/ANSI A117.1-2003 — Accessible & Usable Buildings & Facilities

---

## 14. Programmer Standardization Protocols

- Code style: PEP 8 for Python. Favor explicit, descriptive names; avoid abbreviations.
- Error handling: Guard clauses and clear messages; never swallow exceptions silently.
- Imports: Standard lib, third-party, local; prefer lazy imports for optional/deployment-heavy deps.
- Logging: Use `print` only for debug during development; convert persistent logs to a proper logger if needed.
- Security: Validate inputs, apply CORS and security headers (see `backend.py`). Limit request sizes.
- API: Return JSON with consistent error formats `{ error: string }` and appropriate HTTP status codes.
- Performance: Prefer vectorized NumPy operations, avoid deep nesting, early returns where possible.
- Dependencies: Keep `requirements_vercel.txt` minimal; add heavier packages only to `requirements.txt` when required locally.
- Assets: Serve static assets from `static/`; avoid runtime reads from `node_modules/` on Vercel.
- Releases: Test `/health` and `/liblouis/tables` after deploy; smoke-test STL generation for both card and cylinder.
