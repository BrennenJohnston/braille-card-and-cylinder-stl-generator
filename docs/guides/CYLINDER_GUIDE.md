# Cylinder Braille Guide

This guide helps you create braille labels for cylindrical surfaces using the Braille STL Generator.

## First: Decide What to Include

> **The most important decision:** Braille takes far more space than print. You cannot include everything — you must prioritize.

Before measuring your container or adjusting settings, answer this question:

**"What is the minimum information someone needs to identify this item or contact me?"**

### Space Reality

A typical cylinder (75mm diameter) fits approximately **4 rows with 13-14 cells each**. This is much less than you might expect.

### Content Priority (BANA Guidelines)

| Information | Priority | Guidance |
|-------------|----------|----------|
| **Primary identifier** | Essential | What this item IS (e.g., "Cinnamon", "Jane Smith") |
| **One contact method** | Essential | Phone OR email — pick one |
| Organization | High | Include only if it identifies you; omit if in email |
| Secondary details | Low | Usually omit — won't fit |

### If It Doesn't Fit

1. **Disable capitalization** — Saves ~1 cell per capital (default in this app)
2. **Abbreviate** — "Nat" for National, "Lib" for Library
3. **Remove redundant info** — If organization is in email, omit it
4. **Simplify** — "J. Smith" instead of "Jane Smith"

---

## Common Use Cases

Braille cylinders are commonly used for:

- **Container labels:** Spice jars, medicine bottles, storage containers
- **Identification:** Water bottles, travel mugs, personal items
- **Educational tools:** Learning aids, classroom materials

## Cylinder Parameters

| Parameter | What It Controls |
|-----------|------------------|
| Outer Diameter | The diameter of the object you're labeling (in mm) |
| Cylinder Height | How tall the braille surface will be |
| Wall Thickness | Thickness of the cylinder wall |
| Polygon Cutout | Number of flat sides for the inner shape |
| Seam Offset | Rotates where the seam (gap) appears |

## Measuring Your Container

### Outer Diameter

1. Wrap a piece of string or flexible tape around the container at the widest point where the label will go
2. Mark where the string meets itself
3. Measure the length of the string
4. Divide by π (3.14159) to get the diameter

**Example:** String length of 235mm ÷ 3.14159 = 74.8mm diameter

### Height

1. Measure the flat area where braille will go
2. Leave margin at top and bottom for fit
3. Consider how many rows of braille you need

## Text Capacity

The number of braille cells that fit depends on your cylinder's circumference:

- Standard braille cell width is ~2.5mm (with spacing)
- Cell spacing is typically 6.5mm center-to-center

| Diameter (mm) | Circumference (mm) | Approximate Cells per Row |
|---------------|-------------------|---------------------------|
| 50 | 157 | ~9 |
| 75 | 236 | ~13-14 |
| 100 | 314 | ~18 |
| 125 | 393 | ~22 |

**Note:** 2 cells are reserved for start/end indicators when Indicator Shapes is enabled.

## Key Parameters Explained

### Polygon Cutout

The inner surface of the cylinder uses flat faces (a polygon) rather than a true curve. This makes the STL file smaller and more compatible with 3D printers.

- **Lower numbers (e.g., 12-24):** Visible flat faces, smaller file size
- **Higher numbers (e.g., 48-64):** Smoother curve, larger file size
- **Recommendation:** 32-48 provides a good balance

### Seam Offset

Cylinders have a "seam" — a gap where the cylinder opens. The seam offset rotates where this gap appears.

- **Default:** Seam appears at one side
- **Adjust:** Rotate so the seam doesn't interrupt your text
- **Tip:** Place the seam at the back or between words

### Wall Thickness

- **Thinner (1.5-2mm):** Lighter, flexible, less material
- **Thicker (2.5-3mm):** Sturdier, better for larger cylinders
- **Recommendation:** 2mm for most applications

## Tips for Best Results

### Print Orientation

- Print cylinders **standing upright** for best dot quality
- Layer lines will be horizontal, matching how the cylinder will be read

### Test Fit

- Print a small section first to verify the diameter matches your container
- Adjust diameter slightly if the fit is too tight or too loose

### Seam Placement

- Rotate the seam to the back
- If text wraps around completely, place seam between words

### Material Considerations

- PLA works well for most applications
- PETG for containers that may get wet
- Consider food-safe filament for kitchen containers

## Using the Application

### Quick Start

1. Type your text under **Enter Text for Braille Translation**
2. Set **Placement Mode** to **Auto Placement**
3. Click **Show Expert Mode**, then click **Preview Braille Translation**
4. In **Surface Dimensions**, adjust diameter and height for your container
5. Click **Generate STL**, review the 3D preview, then **Download STL**
6. Switch to **Universal Counter Plate** and download again

### Capitalized Letters Toggle

The **Capitalized Letters** toggle controls how capitals are handled:

- **Disabled (default):** Text is automatically converted to lowercase. You can type normally — capitals are converted for you.
- **Enabled:** Capital letters are preserved, adding indicator cells.

**Why disable capitals?** Saves approximately 1 braille cell per capital letter.

### Recommended Settings for Cylinders

| Setting | Typical Value | Notes |
|---------|--------------|-------|
| Placement Mode | Auto Placement | Handles wrapping automatically |
| Capitalized Letters | Disabled | Saves space (default) |
| Language | English (UEB) — uncontracted | Clearest for labels |
| Indicator Shapes | On | Helps find row start/end |

### Expert Mode Settings

Access these by clicking **Show Expert Mode**:

| Submenu | Key Settings |
|---------|--------------|
| Shape Selection | Output shape (cylinder), dot shape (cone/rounded) |
| Braille Spacing | Cells per row, number of rows, spacing |
| Surface Dimensions | Diameter, height, wall thickness, polygon sides |

## Troubleshooting

### Cylinder Doesn't Fit Container

- Verify your diameter measurement
- Remember diameter = circumference ÷ π
- Print a test ring first

### Text Too Long for Row

- Reduce text length or use abbreviations
- Increase cylinder diameter if container allows
- Use multiple rows instead

### Seam Interrupts Text

- Adjust **Seam Offset** in Expert Mode → Surface Dimensions
- Rotate until seam appears in a natural break point

### Dots Too Large/Small After Printing

- Adjust dot parameters in Expert Mode → Braille Dot Adjustments
- This is printer-specific calibration

## Worked Examples

These examples show **what to type** into the application for common cylinder use cases.

### Example 1: Spice Jar Label

**Goal:** Label a spice jar (diameter ~55mm) so it can be identified by touch.

**Container measurement:** Circumference ~173mm ÷ π ≈ 55mm diameter → approximately 9-10 cells per row.

**Decision:** A single word is all that's needed — just the spice name.

**What to type:**
```
cinnamon
```

**Settings:**
| Setting | Value |
|---------|-------|
| Outer Diameter | 55mm |
| Placement Mode | Auto Placement |
| Capitalized Letters | Disabled |

**Result:** 1 row, fits easily. For longer spice names (e.g., "cardamom"), abbreviate if needed.

---

### Example 2: Medicine Bottle

**Goal:** Label a prescription bottle (diameter ~40mm) with drug name and dosage.

**Container measurement:** Circumference ~126mm ÷ π ≈ 40mm diameter → approximately 9 cells per row.

**Decision:** Two key pieces — medication name and dosage. The small circumference means the name may wrap to a second row.

**What to type:**
```
amoxicillin
500mg
```

**Settings:**
| Setting | Value |
|---------|-------|
| Outer Diameter | 40mm |
| Placement Mode | Auto Placement |
| Capitalized Letters | Disabled |

**Result:** 2-3 rows. "amoxicillin" wraps because it exceeds 9 cells per row. For a very small bottle, abbreviate to "amox 500mg" on one line.

---

### Example 3: Water Bottle ID Tag

**Goal:** Identify a personal water bottle (diameter ~75mm) at a shared workplace.

**Container measurement:** Circumference ~235mm ÷ π ≈ 75mm diameter → approximately 13-14 cells per row.

**Decision:** Name plus one contact method. Omit organization — not needed to identify a personal item.

**What to type:**
```
j. smith
555.867.5309
```

**Settings:**
| Setting | Value |
|---------|-------|
| Outer Diameter | 75mm |
| Placement Mode | Auto Placement |
| Capitalized Letters | Disabled |

**Result:** 2 rows on a 75mm cylinder. Using initial "J." instead of full first name saves cells. Phone formatted with periods per BANA guidance.

---

### Notes on These Examples

- **Capitalized Letters disabled (default):** The app converts text to lowercase automatically.
- **Grade 1 uncontracted:** These examples assume Grade 1 (uncontracted) braille, which is clearest for labels.
- **Measure first, then type:** Always measure your container and check the text capacity table above before entering text.

---

## Resources & Credits

### Official Standards

- [BANA Position Statements and Fact Sheets](https://www.brailleauthority.org/bana-position-statements-and-fact-sheets) — includes the official Business Cards Fact Sheet
- [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters) — primary reference for cylinder dot dimensions and spacing
- [BANA Braille Signage Guidelines](https://www.brailleauthority.org/braille-signage-guidelines)
- [The Rules of Unified English Braille (ICEB)](https://iceb.org/ueb.html)

### Related Guides

- [BUSINESS_CARD_TRANSLATION_GUIDE.md](BUSINESS_CARD_TRANSLATION_GUIDE.md) — Guidance for flat cards (when re-enabled)

### Acknowledgments

Cylinder guidance follows [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters). Content selection guidance adapted from the [*Business Cards Fact Sheet*](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf) (approved March 2024).

Braille translation powered by [liblouis](https://liblouis.io/).

---

*Document Version: 1.1*
*Last Updated: February 2026*
