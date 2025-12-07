# Braille Spacing and Generation Specifications

## Overview

This document provides **strict specifications** for braille dot, cell, and row generation in the braille card and cylinder STL generator. These specifications establish rigid rules that bind the process of how braille content is generated for both embossing plates (positive) and universal counter plates (negative).

The authoritative implementations are:
- Python backend (`backend.py`)
- Geometry specification (`geometry_spec.py`)
- Standard CSG Worker (`csg-worker.js` using three-bvh-csg)
- Manifold CSG Worker (`csg-worker-manifold.js` using Manifold WASM)

---

## 1. Braille Dot Numbering Standard

### Standard 6-Dot Braille Cell Layout

Braille dots are numbered according to the international standard:

```
Left Column    Right Column
    ┌───┬───┐
    │ 1 │ 4 │   ← Top Row (row_off_idx = 0)
    ├───┼───┤
    │ 2 │ 5 │   ← Middle Row (row_off_idx = 1)
    ├───┼───┤
    │ 3 │ 6 │   ← Bottom Row (row_off_idx = 2)
    └───┴───┘
```

### Internal Dot Index Mapping

The code uses a 0-based index (0-5) to reference dots, with the following mapping:

| Dot Number | Internal Index | Position |
|------------|---------------|----------|
| Dot 1 | Index 0 | Top-Left |
| Dot 2 | Index 1 | Middle-Left |
| Dot 3 | Index 2 | Bottom-Left |
| Dot 4 | Index 3 | Top-Right |
| Dot 5 | Index 4 | Middle-Right |
| Dot 6 | Index 5 | Bottom-Right |

### Code Implementation (AUTHORITATIVE)

```python
# From backend.py and geometry_spec.py
dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
# Format: [row_off_idx, col_off_idx] for each dot index 0-5
# row_off_idx: 0=top, 1=middle, 2=bottom
# col_off_idx: 0=left, 1=right
```

---

## 2. Braille Cell Geometry

### Cell Dimensions

Braille cells are defined by the following spacing parameters (all in millimeters):

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `dot_spacing` | 2.5mm | Distance between dots within a cell (both horizontal and vertical) |
| `cell_spacing` | 6.5mm | Distance between cell centers (horizontal) |
| `line_spacing` | 10.0mm | Distance between row centers (vertical) |

### Dot Position Offsets

Dots are positioned relative to the **cell center** using these offsets:

```python
# From backend.py and geometry_spec.py
dot_col_offsets = [-dot_spacing / 2, dot_spacing / 2]
# Index 0: Left column offset = -1.25mm (for default 2.5mm dot_spacing)
# Index 1: Right column offset = +1.25mm

dot_row_offsets = [dot_spacing, 0, -dot_spacing]
# Index 0: Top row offset = +2.5mm
# Index 1: Middle row offset = 0mm (at cell center)
# Index 2: Bottom row offset = -2.5mm
```

### Visual Representation of Cell Geometry

```
Cell Center at (x, y)
        ▲ y+
        │
   ●────┼────●    Dot 1 at (x-1.25, y+2.5), Dot 4 at (x+1.25, y+2.5)
        │
   ●────┼────●    Dot 2 at (x-1.25, y+0.0), Dot 5 at (x+1.25, y+0.0)
        │
   ●────┼────●    Dot 3 at (x-1.25, y-2.5), Dot 6 at (x+1.25, y-2.5)
        │
        └────────► x+
```

### Dot Position Formula

For a cell centered at `(x, y)` and dot index `i`:

```python
row_off_idx, col_off_idx = dot_positions[i]
dot_x = x + dot_col_offsets[col_off_idx]
dot_y = y + dot_row_offsets[row_off_idx]
```

---

## 3. Braille Row Layout

### Card (Flat Plate) Row Layout

Rows are positioned from **top to bottom** of the card, with the first row at the top:

```python
y_pos = card_height - top_margin - (row_num * line_spacing) + braille_y_adjust
```

### Cylinder Row Layout

For cylinders, rows are positioned vertically along the cylinder's Z-axis (height):

```python
# Calculate vertical centering
braille_content_height = (grid_rows - 1) * line_spacing + 2 * dot_spacing
space_above = (height - braille_content_height) / 2.0
first_row_center_y = height - space_above - dot_spacing

# Row position
y_pos = first_row_center_y - (row_num * line_spacing) + braille_y_adjust
y_local = y_pos - (height / 2.0)  # Relative to cylinder center
```

---

## 4. Angular Direction Rules for Cylinders

### CRITICAL: Mirroring Behavior

The embossing plate and counter plate use **opposite angular directions** to ensure proper alignment when paper is pressed between them.

### Angular Direction Functions (AUTHORITATIVE)

```python
# From geometry_spec.py

def apply_seam(angle: float) -> float:
    """For embossing plate - content flows COUNTER-CLOCKWISE when viewed from above."""
    return -angle

def apply_seam_mirrored(angle: float) -> float:
    """For counter plate - content flows CLOCKWISE when viewed from above."""
    return +angle  # Note: positive, not negative
```

### Visual Explanation

```
View from ABOVE the cylinder:

EMBOSSING PLATE (Positive)           COUNTER PLATE (Negative)
Content flows COUNTER-CLOCKWISE      Content flows CLOCKWISE

        ↑ 0°                                ↑ 0°
        │                                   │
   ←────┼────→                         ←────┼────→
  270° ─│─ 90°                        90° ─│─ 270°
        │                                   │
        ↓ 180°                              ↓ 180°

   Text: "ABC"                         Text: "CBA" (mirrored)
   A at -angle                         A at +angle
   B at center                         B at center
   C at +angle                         C at -angle
```

### When Paper is Pressed Between Plates

When the embossing plate's braille at angle θ is pressed, it creates a raised dot on the paper. The counter plate's corresponding recess at angle θ (mirrored) receives that raised dot, ensuring perfect alignment.

---

## 5. Column Layout Specifications

### Card Column Layout (with Indicators Enabled)

```
Column 0:           Character/Rectangle indicator
Columns 1 to N-2:   Braille content (N-2 characters maximum)
Column N-1:         Triangle marker

N = grid_columns (default 13)
Available braille columns = N - 2 = 11
```

**Column Position Formula:**
```python
x_pos = left_margin + (col_num * cell_spacing) + braille_x_adjust
```

### Cylinder Column Layout (with Indicators Enabled)

**Embossing Plate (Positive):**
```
Column 0:           Triangle marker at apply_seam(start_angle)
Column 1:           Character/Rectangle indicator at apply_seam(start_angle + cell_spacing_angle)
Columns 2 to N-1:   Braille content at apply_seam(start_angle + col * cell_spacing_angle)

N = grid_columns
Available braille columns = N - 2
```

**Counter Plate (Negative):**
```
Column 0:           Triangle marker at apply_seam_mirrored(start_angle) with rotate_180=true
Column 1:           Rectangle ONLY at apply_seam_mirrored(start_angle + cell_spacing_angle)
Columns 2 to N-1:   ALL 6 dots at apply_seam_mirrored(start_angle + col * cell_spacing_angle)

N = grid_columns
Note: Counter plates ALWAYS use rectangle, never character indicators at column 1
```

### Angular Calculations for Cylinders

```python
# Grid angular span
grid_width = (grid_columns - 1) * cell_spacing  # Physical width in mm
grid_angle = grid_width / radius                 # Angular span in radians
start_angle = -grid_angle / 2                    # Center content on cylinder

# Per-cell angular spacing
cell_spacing_angle = cell_spacing / radius       # Radians between cell centers
dot_spacing_angle = dot_spacing / radius         # Radians between dots in a cell

# Angular position for column N
column_angle = start_angle + (N * cell_spacing_angle)

# Cylinder dot angular offsets (analogous to dot_col_offsets for cards)
dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
```

---

## 6. Embossing Plate vs Counter Plate: Key Differences

### Summary Table

| Aspect | Embossing Plate (Positive) | Universal Counter Plate (Negative) |
|--------|---------------------------|-----------------------------------|
| **Dot Generation** | Only active dots (from braille text) | ALL 6 dots for ALL cells |
| **Dot Operation** | ADD (protrusions) | SUBTRACT (recesses) |
| **Angular Direction** | `apply_seam(angle)` = `-angle` | `apply_seam_mirrored(angle)` = `+angle` |
| **Content Flow** | Counter-clockwise (viewed from above) | Clockwise (viewed from above) |
| **Column 1 Indicator** | Character OR Rectangle (based on text) | ALWAYS Rectangle |
| **Triangle Rotation** | Normal (`rotate_180=false`) | 180° rotated (`rotate_180=true`) |
| **Dot Shapes** | Standard, Rounded | Hemisphere, Bowl, Cone |

### Why This Mirroring Works

When you place paper between an embossing plate and counter plate:

1. **Embossing plate braille** at angular position θ pushes the paper
2. **Counter plate recess** at angular position θ (mirrored direction) receives the pushed paper
3. Because the directions are opposite, the positions **align perfectly** when the plates face each other

**Analogy:** Think of looking at text through a mirror. The text appears reversed, but if you fold the paper to meet the mirror, the text and its reflection align.

---

## 7. Braille Character Encoding

### Unicode Braille Block

Braille characters are encoded in the Unicode block U+2800 to U+28FF:

```python
# From app/utils.py braille_to_dots()
def braille_to_dots(braille_char: str) -> list:
    code_point = ord(braille_char)

    # Must be in braille Unicode block
    if code_point < 0x2800 or code_point > 0x28FF:
        return [0, 0, 0, 0, 0, 0]  # Not a braille character

    # Extract dot pattern (code_point - 0x2800 gives bit pattern)
    dot_pattern = code_point - 0x2800

    # Bit 0 = Dot 1, Bit 1 = Dot 2, ..., Bit 5 = Dot 6
    dots = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        dots[i] = (dot_pattern >> i) & 1

    return dots
```

### Dot Bit Mapping

| Bit Position | Dot Number | Binary Value |
|--------------|------------|--------------|
| Bit 0 | Dot 1 | 0x01 |
| Bit 1 | Dot 2 | 0x02 |
| Bit 2 | Dot 3 | 0x04 |
| Bit 3 | Dot 4 | 0x08 |
| Bit 4 | Dot 5 | 0x10 |
| Bit 5 | Dot 6 | 0x20 |

**Example:** The letter "A" in Grade 1 braille is dot 1 only = Unicode U+2801

---

## 8. Dot Shape Specifications

### Embossing Plate Dots (Protrusions)

**Standard Cone Frustum:**
```python
{
    'base_radius': emboss_dot_base_diameter / 2,  # Default: 0.8mm
    'top_radius': emboss_dot_flat_hat / 2,        # Default: 0.25mm
    'height': emboss_dot_height                    # Default: 0.5mm
}
```

**Rounded Dot (when use_rounded_dots=1):**
```python
{
    'base_radius': rounded_dot_base_diameter / 2,  # Default: 1.0mm
    'top_radius': rounded_dot_dome_diameter / 2,   # Default: 0.75mm
    'base_height': rounded_dot_base_height,        # Default: 0.2mm
    'dome_height': rounded_dot_dome_height,        # Default: 0.6mm
    'dome_radius': (top_radius² + dome_height²) / (2 * dome_height)
}
```

### Counter Plate Dots (Recesses)

**Hemisphere (recess_shape=0):**
```python
{
    'shape': 'hemisphere',
    'recess_radius': hemi_counter_dot_base_diameter / 2  # Default: 0.8mm
}
```

**Bowl (recess_shape=1):**
```python
{
    'shape': 'bowl',
    'bowl_radius': bowl_counter_dot_base_diameter / 2,  # Default: 0.9mm
    'bowl_depth': counter_dot_depth                      # Default: 0.8mm
}
```

**Cone (recess_shape=2):**
```python
{
    'shape': 'cone',
    'base_radius': cone_counter_dot_base_diameter / 2,  # Large opening: 0.8mm
    'top_radius': cone_counter_dot_flat_hat / 2,        # Small tip: 0.2mm
    'height': cone_counter_dot_height                    # Default: 0.8mm
}
# Note: For recesses, base_radius is the OPENING at the surface
```

---

## 9. Cylinder Surface Positioning

### Radial Position Calculation

```javascript
// For PROTRUSIONS (embossing plate dots)
radialOffset = cylRadius + dotHeight / 2 + epsilon;

// For RECESSES (counter plate dots)
if (shape === 'cone') {
    radialOffset = cylRadius - dotHeight / 2;
} else {  // hemisphere, bowl
    radialOffset = cylRadius;  // Center at surface
}

// 3D position on cylinder surface
posX = radialOffset * Math.cos(theta);
posY = y_local;  // Height along cylinder axis
posZ = radialOffset * Math.sin(theta);  // For Three.js Y-up
```

### Orientation on Cylinder Surface

All non-spherical shapes must be rotated to point radially outward:

```javascript
// Three.js (Y-up coordinate system)
geometry.rotateZ(-Math.PI / 2);  // Align with +X
geometry.rotateY(-theta);         // Point toward radial direction

// Manifold (Z-up coordinate system)
dot.rotate(0, 90, 0);            // Z -> X
rotatedDot.rotate(0, 0, thetaDeg);  // Rotate to correct angle
```

---

## 10. Coordinate Systems

### Coordinate System Summary

| Component | System | Axis Meaning |
|-----------|--------|--------------|
| Python Backend (trimesh) | Z-up | X=width, Y=height, Z=thickness |
| Three.js (csg-worker.js) | Y-up | X=width, Y=height(up), Z=depth |
| Manifold WASM | Z-up | Same as Python |
| STL File Format | Z-up | Standard CAD convention |

### Critical Transformations

**Three.js cylinders must be rotated before STL export:**
```javascript
// At end of CSG operations in csg-worker.js
if (isCylinder) {
    finalGeometry.rotateX(Math.PI / 2);
}
```

**Manifold cylinders are natively Z-up - no rotation needed.**

### CRITICAL: Manifold Theta Negation

Due to coordinate system differences, theta must be **negated** in the Manifold worker to match Three.js output:

**Why this is needed:**
- Three.js (Y-up) after `rotateX(π/2)` produces: `(cos(θ), -sin(θ), height)`
- Manifold (Z-up) natively produces: `(cos(θ), sin(θ), height)`
- The Y component has **opposite signs**, causing content to appear in reverse order

**The fix - negate theta in Manifold worker:**
```javascript
// In csg-worker-manifold.js - for ALL cylinder positioning functions
const adjustedTheta = -theta;

// Use adjustedTheta for all position and rotation calculations
const posX = radialOffset * Math.cos(adjustedTheta);
const posY = radialOffset * Math.sin(adjustedTheta);
const posZ = height;

// For rotations around Z-axis
const thetaDeg = adjustedTheta * 180 / Math.PI;
```

**Additional fix for triangle markers - invert rotate_180:**
```javascript
// In createCylinderTriangleMarkerManifold() ONLY
// The theta negation also flips the rotation direction, which would
// swap the triangle orientation. Invert rotate_180 to compensate.
const adjustedRotate180 = !rotate_180;

// Use adjustedRotate180 for triangle vertex selection
if (adjustedRotate180) {
    // Apex points left
} else {
    // Apex points right
}
```

**Functions that require theta negation:**
- `createCylinderDotManifold()`
- `createCylinderTriangleMarkerManifold()` (also requires `rotate_180` inversion)
- `createCylinderRectMarkerManifold()`
- `createCylinderCharacterMarkerManifold()` (inherits from rect)

---

## 11. Validation Checklist

### Dot Generation
- [ ] `dot_positions` array maps correctly: `[[0,0], [1,0], [2,0], [0,1], [1,1], [2,1]]`
- [ ] `dot_col_offsets` = `[-dot_spacing/2, dot_spacing/2]`
- [ ] `dot_row_offsets` = `[dot_spacing, 0, -dot_spacing]`
- [ ] Embossing plate: only active dots from `braille_to_dots()` result
- [ ] Counter plate: ALL 6 dots for ALL cells

### Angular Direction
- [ ] Embossing plate uses `apply_seam(angle)` = `-angle`
- [ ] Counter plate uses `apply_seam_mirrored(angle)` = `+angle`
- [ ] Content flows counter-clockwise on embossing plate
- [ ] Content flows clockwise on counter plate (mirror image)

### Column Layout
- [ ] Triangle at column 0 for both plate types
- [ ] Character/Rectangle at column 1 for embossing plate
- [ ] Rectangle ONLY at column 1 for counter plate (never character)
- [ ] Braille content starts at column 2 when indicators enabled

### Coordinate Transformations
- [ ] Three.js cylinders rotated +90° around X before export
- [ ] Manifold cylinders exported without rotation (native Z-up)
- [ ] **Manifold worker uses `adjustedTheta = -theta` for all cylinder positioning**
- [ ] **Manifold triangle marker uses `adjustedRotate180 = !rotate_180`**
- [ ] Dots/markers positioned at correct radial offset
- [ ] Non-spherical shapes rotated to point radially outward

---

## 12. Common Bugs and Solutions

### Bug 1: Braille Content Appears Mirrored on Counter Plate

**Symptom**: Text reads left-to-right when it should read right-to-left (or vice versa)

**Cause**: Using `apply_seam()` instead of `apply_seam_mirrored()` for counter plate

**Solution**: Ensure counter plates use `apply_seam_mirrored(angle)` = `+angle`

### Bug 2: Plates Don't Align When Pressed Together

**Symptom**: Embossing dots don't fit into counter plate recesses

**Cause**: Same angular direction used for both plates

**Solution**:
- Embossing: `theta = -raw_angle`
- Counter: `theta = +raw_angle`

### Bug 3: Dots Appear at Wrong Positions in Cell

**Symptom**: Dots 1-3 appear on right, dots 4-6 appear on left

**Cause**: `dot_col_offsets` indices swapped

**Solution**: Verify `dot_col_offsets = [-dot_spacing/2, +dot_spacing/2]`
- Index 0 = left column (negative offset)
- Index 1 = right column (positive offset)

### Bug 4: Row Spacing Wrong on Cylinders

**Symptom**: Rows overlap or are too far apart

**Cause**: Using `line_spacing` in radians instead of mm

**Solution**: Row offsets use linear mm values, not angular values:
```python
dot_row_offsets = [dot_spacing, 0, -dot_spacing]  # mm, not radians
y_local + dot_row_offsets[row_off_idx]  # Simple addition in mm
```

### Bug 5: Column Spacing Wrong on Cylinders

**Symptom**: Cells overlap or are too far apart around cylinder

**Cause**: Using mm instead of radians for angular offset

**Solution**: Column offsets use angular values for cylinders:
```python
dot_spacing_angle = dot_spacing / radius  # Convert mm to radians
dot_col_angle_offsets = [-dot_spacing_angle/2, dot_spacing_angle/2]
```

### Bug 6: Braille Cells in Reverse Order on Manifold WASM Cylinders

**Symptom**: Both embossing plate and counter plate cylinders have braille cells appearing in reverse angular order when generated by the Manifold worker

**Cause**: Coordinate system mismatch between Three.js and Manifold:
- Three.js (Y-up) after `rotateX(π/2)` produces: `(cos(θ), -sin(θ), height)`
- Manifold (Z-up) natively produces: `(cos(θ), +sin(θ), height)`
- The positive vs negative sin(θ) flips the angular direction

**Solution**: Negate theta at the start of all Manifold cylinder positioning functions:
```javascript
// In createCylinderDotManifold, createCylinderTriangleMarkerManifold,
// createCylinderRectMarkerManifold
const adjustedTheta = -theta;

// Use adjustedTheta for ALL position and rotation calculations
const posX = radialOffset * Math.cos(adjustedTheta);
const posY = radialOffset * Math.sin(adjustedTheta);  // Now matches Three.js
```

**Additional fix for triangle orientation**: The theta negation also flips the rotation around Z, which swaps triangle orientations. In `createCylinderTriangleMarkerManifold`, also invert `rotate_180`:
```javascript
const adjustedRotate180 = !rotate_180;
// Use adjustedRotate180 for triangle vertex selection
```

**Important**: These fixes were applied to `csg-worker-manifold.js` on 2024-12-06. If this bug reappears, verify:
1. `adjustedTheta = -theta` is applied in all four cylinder positioning functions
2. `adjustedRotate180 = !rotate_180` is applied in the triangle marker function

---

## 13. Test Cases

### Unit Test: Dot Position Calculation

```python
# Given: cell center at (10, 20), dot_spacing = 2.5mm
# Expected positions:
# Dot 1 (index 0): (10 - 1.25, 20 + 2.5) = (8.75, 22.5)
# Dot 2 (index 1): (10 - 1.25, 20 + 0.0) = (8.75, 20.0)
# Dot 3 (index 2): (10 - 1.25, 20 - 2.5) = (8.75, 17.5)
# Dot 4 (index 3): (10 + 1.25, 20 + 2.5) = (11.25, 22.5)
# Dot 5 (index 4): (10 + 1.25, 20 + 0.0) = (11.25, 20.0)
# Dot 6 (index 5): (10 + 1.25, 20 - 2.5) = (11.25, 17.5)
```

### Integration Test: Angular Mirroring

```
Test: Generate embossing and counter plate cylinders for text "AB"

Expected Angular Positions (radius=30mm, cell_spacing=6.5mm):
- cell_spacing_angle = 6.5 / 30 = 0.2167 radians

Embossing Plate:
- "A" at column 2, angle = apply_seam(start_angle + 2*cell_spacing_angle)
- "B" at column 3, angle = apply_seam(start_angle + 3*cell_spacing_angle)

Counter Plate:
- Cell 2 recesses at angle = apply_seam_mirrored(start_angle + 2*cell_spacing_angle)
- Cell 3 recesses at angle = apply_seam_mirrored(start_angle + 3*cell_spacing_angle)

Verification: When plates face each other:
- "A" dots at -θ should align with recesses at +θ
- "B" dots at -θ' should align with recesses at +θ'
```

### Visual Alignment Test

1. Generate embossing plate cylinder STL
2. Generate counter plate cylinder STL
3. Import both into 3D viewer
4. Position counter plate inside embossing plate (concentric)
5. Verify: All recesses align with corresponding raised dots
6. Verify: Triangle markers point toward each other

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-06 | 1.0 | Initial specification based on working backend.py and csg-worker implementations |
| 2024-12-06 | 1.1 | Added Manifold theta negation fix (Bug 6) to correct reverse cell order on cylinders |
| 2024-12-06 | 1.2 | Added triangle rotate_180 inversion fix to correct swapped triangle orientations |

---

## Related Documentation

- `RECESS_INDICATOR_SPECIFICATIONS.md` - Triangle, Rectangle, and Character marker specifications
- `CLIENT_SIDE_CSG_DOCUMENTATION.md` - Overall CSG architecture
- `geometry_spec.py` - Authoritative geometry specification extraction
- `app/utils.py` - Braille character to dots conversion
