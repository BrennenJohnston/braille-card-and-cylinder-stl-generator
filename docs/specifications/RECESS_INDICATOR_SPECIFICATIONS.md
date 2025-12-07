# Recess Indicator Specifications

## Overview

This document provides **strict specifications** for the three types of recessed indicators used in the braille card and cylinder STL generator. These indicators are always **subtracted** (recessed) into both positive (embossing) and negative (counter) plates.

The indicators serve as tactile guides for visually impaired users and must maintain precise orientation and positioning across all generation methods:
- Python backend (`backend.py`)
- Standard CSG Worker (`csg-worker.js` using three-bvh-csg)
- Manifold CSG Worker (`csg-worker-manifold.js` using Manifold WASM)

---

## Coordinate Systems

### Critical Understanding
Different parts of the system use different coordinate systems. **Coordinate mismatches are the primary cause of orientation bugs.**

| Component | Coordinate System | Notes |
|-----------|------------------|-------|
| Python Backend (trimesh) | Z-up | X = width, Y = height, Z = thickness |
| Three.js (csg-worker.js) | Y-up | X = width, Y = height (up), Z = depth |
| Manifold WASM | Z-up | Same as Python, no conversion needed |
| STL File Format | Z-up | Standard CAD convention |

### Conversion Rules

**Three.js (Y-up) to STL (Z-up):**
- For cylinders in `csg-worker.js`: Apply `geometry.rotateX(Math.PI / 2)` at the end
- For cards: No rotation needed (XY plane operations are consistent)

**Manifold (Z-up) to STL (Z-up):**
- No rotation needed - native compatibility

---

## 1. Triangle Marker Indicator

### Purpose
Indicates the END of each braille row (on cards) or serves as the START marker (on cylinders).

### Geometry Specification

```
Shape: Isoceles triangle with VERTICAL base on the LEFT, apex pointing RIGHT

Dimensions (relative to settings.dot_spacing):
- Base Height: 2 × dot_spacing (spans from top to bottom of braille cell)
- Triangle Width: 1 × dot_spacing (horizontal extension to apex)
- Recess Depth: 0.6mm (default)

Vertex Positions (given cell center at x, y):
- Bottom-left vertex: (x - dot_spacing/2, y - dot_spacing)
- Top-left vertex:    (x - dot_spacing/2, y + dot_spacing)
- Apex (right):       (x + dot_spacing/2, y)

Example for dot_spacing = 2.5mm at cell center (10, 20):
- Bottom-left: (8.75, 17.5)
- Top-left:    (8.75, 22.5)
- Apex:        (11.25, 20)
```

### Visual Representation
```
     ▲ y+
     │
  T ─┼─     T = Top-left vertex
  │ \│      B = Bottom-left vertex
  │  ►─ x+  A = Apex vertex
  │ /
  B ─       Arrow points RIGHT (positive X direction)
```

### Position on Cards (Flat Plates)

| Plate Type | Column Position | Cell X Calculation |
|------------|-----------------|-------------------|
| Positive/Embossing | Last column (grid_columns - 1) | `left_margin + (grid_columns-1) × cell_spacing + braille_x_adjust` |
| Counter/Negative | Last column (grid_columns - 1) | Same as positive |

### Position on Cylinders

| Plate Type | Column Position | Angular Position | Special Handling |
|------------|-----------------|-----------------|------------------|
| Positive/Embossing | Column 0 (first) | `apply_seam(start_angle)` = `-start_angle` | Normal orientation |
| Counter/Negative | Column 0 (first) | `apply_seam_mirrored(start_angle)` = `+start_angle` | **rotate_180 = true** |

### Counter Plate Triangle Rotation (CRITICAL)

For counter plates, the triangle must be rotated 180° from its center point to properly align with the embossing plate when paper is pressed between them:

```javascript
// In csg-worker.js and csg-worker-manifold.js
if (rotate_180) {
    // Original vertices: (-size/2, -size), (-size/2, +size), (+size/2, 0)
    // After 180° rotation: (+size/2, +size), (+size/2, -size), (-size/2, 0)
    triangleShape.moveTo(validSize / 2, validSize);    // Rotated bottom-left → top-right
    triangleShape.lineTo(validSize / 2, -validSize);   // Rotated top-left → bottom-right
    triangleShape.lineTo(-validSize / 2, 0);           // Apex now on LEFT
}
```

### Implementation Reference

| File | Function | Lines |
|------|----------|-------|
| `backend.py` | `create_triangle_marker_polygon()` | 366-399 |
| `backend.py` | `create_card_triangle_marker_3d()` (imported) | N/A |
| `app/geometry/braille_layout.py` | `create_card_triangle_marker_3d()` | 216-262 |
| `geometry_spec.py` | `_create_cylinder_marker_spec()` | 776-829 |
| `csg-worker.js` | `createTriangleMarker()` | 619-637 |
| `csg-worker.js` | `createCylinderTriangleMarker()` | 399-476 |
| `csg-worker-manifold.js` | `createCylinderTriangleMarkerManifold()` | 276-364 |

---

## 2. Rectangle Marker Indicator

### Purpose
Fallback indicator for rows where the first character is NOT alphanumeric (symbol, punctuation, or empty). Also used as placeholder on counter plate cylinders.

### Geometry Specification

```
Shape: Vertical rectangle (taller than wide)

Dimensions (relative to settings.dot_spacing):
- Width: 1 × dot_spacing
- Height: 2 × dot_spacing (matches braille cell height)
- Recess Depth: 0.5mm (default)

Center Position (given cell center at x, y):
- Rectangle centered at: (x + dot_spacing/2, y)
- This places it at the RIGHT column of the braille cell

Corner Vertices (given cell center x, y):
- Bottom-left:  (x, y - dot_spacing)
- Bottom-right: (x + dot_spacing, y - dot_spacing)
- Top-right:    (x + dot_spacing, y + dot_spacing)
- Top-left:     (x, y + dot_spacing)

Example for dot_spacing = 2.5mm at cell center (10, 20):
- Bottom-left:  (10, 17.5)
- Bottom-right: (12.5, 17.5)
- Top-right:    (12.5, 22.5)
- Top-left:     (10, 22.5)
```

### Visual Representation
```
     ▲ y+
     │
  ┌──┼──┐   Rectangle is positioned at the RIGHT
  │  │  │   column of the braille cell, NOT centered
  │  │  │   on the cell itself
  │  │  │
  └──┼──┘
     └───► x+
```

### Position on Cards (Flat Plates)

| Plate Type | Column Position | Cell X Calculation |
|------------|-----------------|-------------------|
| Positive/Embossing | First column (column 0) | `left_margin + braille_x_adjust` |
| Counter/Negative | First column (column 0) | Same as positive |

### Position on Cylinders

| Plate Type | Column Position | Angular Position | Notes |
|------------|-----------------|-----------------|-------|
| Positive/Embossing | Column 1 (second) | `apply_seam(start_angle + cell_spacing_angle)` | Only when first char is non-alphanumeric |
| Counter/Negative | Column 1 (second) | `apply_seam_mirrored(start_angle + cell_spacing_angle)` | **ALWAYS rectangle, never character** |

### Counter Plate Always Uses Rectangle (CRITICAL)

On counter plate cylinders, column 1 **always** uses a rectangle placeholder, never a character indicator. This matches the Python backend behavior:

```javascript
// In geometry_spec.py for counter plate cylinders
// Counter plates ALWAYS use rectangle placeholders, not character indicators
marker_spec = _create_cylinder_marker_spec(
    char_col_angle,
    y_local,
    radius,
    settings,
    'rect',  // Always rectangle for counter plate (not character)
    ...
)
```

### Implementation Reference

| File | Function | Lines |
|------|----------|-------|
| `backend.py` | `create_line_marker_polygon()` | 402-425 |
| `app/geometry/braille_layout.py` | `create_line_marker_polygon()` | 55-78 |
| `app/geometry/braille_layout.py` | `create_card_line_end_marker_3d()` | 265-314 |
| `geometry_spec.py` | (specs for markers) | Various |
| `csg-worker.js` | `createRectMarker()` | 609-614 |
| `csg-worker.js` | `createCylinderRectMarker()` | 481-525 |
| `csg-worker-manifold.js` | `createCylinderRectMarkerManifold()` | 369-476 |

---

## 3. Character Marker Indicator

### Purpose
Shows the first alphanumeric character of each row as a tactile indicator, allowing users to identify which row they are on.

### Geometry Specification

```
Shape: Extruded font character (A-Z, 0-9)

Dimensions (fit within braille cell boundary):
- Character Width: 1 × dot_spacing (horizontal/tangential direction)
  (= 2.5mm for default dot_spacing of 2.5mm)
- Character Height: 2 × dot_spacing (vertical/cylinder axis direction)
  (= 5.0mm for default dot_spacing of 2.5mm)
- Recess Depth: 0.5mm (matches rectangle marker depth)

Viewing Orientation (from outer cylinder surface, cylinder axis vertical):
- Width = left-right direction = dot_spacing
- Height = top-bottom direction = 2 × dot_spacing

Center Position (given cell center at x, y):
- Character centered at: (x + dot_spacing/2, y)
- Same position as rectangle marker

Font:
- Primary: "Arial Rounded MT Bold" (tactile-friendly)
- Fallback: "monospace, bold"
- Scaling: Fit character within cell boundary
```

### Rendering Methods

1. **Python Backend**: Uses matplotlib TextPath
2. **Standard CSG Worker**: Uses Three.js TextGeometry with loaded font
3. **Manifold CSG Worker**: Uses 8x8 bitmap font converted to box primitives

### Fallback Behavior

If character rendering fails (no font, non-alphanumeric character, rendering error):
- Falls back to **rectangle marker** with 0.5mm depth

### Position on Cards (Flat Plates)

| Plate Type | Column Position | Condition |
|------------|-----------------|-----------|
| Positive/Embossing | First column (column 0) | Only when `original_lines[row][0].isalnum()` |
| Counter/Negative | First column (column 0) | Same condition |

### Position on Cylinders

| Plate Type | Column Position | Angular Position | Condition |
|------------|-----------------|-----------------|-----------|
| Positive/Embossing | Column 1 (second) | `apply_seam(start_angle + cell_spacing_angle)` | Only when first char is alphanumeric |
| Counter/Negative | **N/A** | **N/A** | **Counter plates use rectangle, NOT character** |

### Implementation Reference

| File | Function | Lines |
|------|----------|-------|
| `backend.py` | `create_character_shape_polygon()` | 428-470 |
| `backend.py` | `create_character_shape_3d()` | 569-645 |
| `backend.py` | `_build_character_polygon()` | 476-563 |
| `app/geometry/braille_layout.py` | `create_character_shape_polygon()` | 171-213 |
| `app/geometry/braille_layout.py` | `create_character_shape_3d()` | 317-393 |
| `geometry_spec.py` | Character marker spec generation | 828-840 |
| `csg-worker.js` | `createCharacterMarker()` | 642-651 |
| `csg-worker.js` | `createCylinderCharacterMarker()` | 530-604 |
| `csg-worker-manifold.js` | `createLetterShapeManifold()` | 566-635 |
| `csg-worker-manifold.js` | `createCylinderCharacterMarkerManifold()` | 985-1065 |

---

## 3.1 Manifold WASM Character Generation (Detailed Specification)

This section provides detailed technical specifications for the Manifold WASM character generation process, enabling future iterations to replicate or modify this architecture correctly.

### Overview

The Manifold WASM process cannot use font rendering libraries (matplotlib, Three.js TextGeometry) because it runs in a Web Worker with only the Manifold 3D library available. Instead, characters are generated using an **8x8 bitmap font converted to box primitives**.

### Bitmap Font Format

```javascript
// Font data structure: FONT8X8_BASIC object
// Each character maps to an array of 8 bytes (one per row)
// Each byte represents one row of pixels (8 bits = 8 columns)
// Bit 0 (LSB) = leftmost pixel, Bit 7 (MSB) = rightmost pixel

'T': [
    0x7E,  // Row 0: .██████. (top bar)
    0x18,  // Row 1: ...██... (stem)
    0x18,  // Row 2: ...██...
    0x18,  // Row 3: ...██...
    0x18,  // Row 4: ...██...
    0x18,  // Row 5: ...██...
    0x18,  // Row 6: ...██...
    0x00   // Row 7: ........ (empty)
]
```

### Supported Characters

- **Letters**: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z
- **Numbers**: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
- **Unsupported characters**: Fall back to rectangle marker

### Font Style

- **Type**: Clean sans-serif geometric font
- **Grid**: 8 rows × 7 effective columns (column 8 typically empty)
- **Stroke Width**: 2 pixels typical
- **Design Principle**: No serifs, no decorative flourishes, uniform stroke widths

### Pixel-to-Box Conversion Algorithm

```
Input: Character, target width, target height, depth
Output: Manifold object (union of box primitives)

1. Look up character in FONT8X8_BASIC dictionary
2. Calculate pixel dimensions:
   - pixelWidth = targetWidth / 7 (7 effective columns)
   - pixelHeight = targetHeight / 8 (8 rows)

3. For each row (0-7) and column (0-6):
   - Check if bit is set: (rowData >> col) & 1
   - If set, create a Manifold box at calculated position

4. CRITICAL - Horizontal Mirroring:
   - posX = +halfWidth - (col + 0.5) × pixelWidth
   - This mirrors the letter so it appears correct when viewed
     from OUTSIDE the cylinder surface
   - Without mirroring, letters appear reversed (like reading
     through glass from behind)

5. Vertical positioning (no mirroring needed):
   - posZ = +halfHeight - (row + 0.5) × pixelHeight
   - Row 0 at top (+Z), Row 7 at bottom (-Z)

6. Union all pixel boxes into single Manifold object
```

### Coordinate System (Manifold Z-up)

```
Letter is created in XZ plane:
- X axis: Width (tangential direction on cylinder)
- Y axis: Depth (radial direction - points outward after rotation)
- Z axis: Height (along cylinder axis)

Origin: Center of character bounding box

After creation:
1. Rotate around Z: (theta - 90°) to align Y with radial direction
2. Translate to cylinder surface position
```

### Cylinder Surface Placement

```javascript
// Theta adjustment (CRITICAL for coordinate system compatibility)
const adjustedTheta = -theta;  // Negate to match Three.js convention

// Rotation to point depth radially outward
const thetaDeg = adjustedTheta * 180 / Math.PI;
letterShape.rotate(0, 0, thetaDeg - 90);

// Radial position (recess into surface)
const radialOffset = cylRadius - depth / 2;

// Final position
posX = radialOffset × cos(adjustedTheta)
posY = radialOffset × sin(adjustedTheta)
posZ = y_local  // Height along cylinder axis
```

### Critical Implementation Notes

1. **Theta Negation**: The theta angle must be negated (`-theta`) to match Three.js coordinate conventions. Without this, characters appear at wrong angular positions.

2. **Horizontal Mirroring**: Letters must be mirrored horizontally during pixel placement because they are viewed from outside the cylinder. The mirroring formula is:
   ```
   posX = +halfWidth - (col + 0.5) × pixelWidth  // Mirrored
   ```
   Not:
   ```
   posX = -halfWidth + (col + 0.5) × pixelWidth  // Non-mirrored (WRONG)
   ```

3. **Depth Direction**: The Y axis becomes the radial (depth) direction after rotation. Positive Y points outward from cylinder center.

4. **Recess Positioning**: For recessed markers, the radial offset is `cylRadius - depth/2` to center the marker geometry at the correct depth below the surface.

### Dimension Calculations

```javascript
// Input from geometry_spec.py
size = dot_spacing × 1.5  // Passed in spec

// Manifold worker calculations
dotSpacing = size / 1.5   // Recover original dot_spacing
charWidth = dotSpacing    // = dot_spacing (fits cell width)
charHeight = 2 × dotSpacing  // = 2 × dot_spacing (fits cell height)
depth = 0.5               // Default recess depth in mm
```

### Error Handling and Fallback

1. If character not in `FONT8X8_BASIC`: Return `null`, caller creates rectangle marker
2. If Manifold operations fail: Catch exception, return rectangle marker with 0.5mm depth
3. If parameters invalid (NaN theta, zero radius): Return `null` immediately

### Testing Verification

To verify correct character rendering:
1. **Symmetrical letters** (A, H, I, M, O, T, U, V, W, X, Y, 0, 1, 8): Should appear identical regardless of mirroring
2. **Asymmetrical letters** (B, C, D, E, F, G, J, K, L, N, P, Q, R, S, Z, 2-7, 9): Verify correct orientation
3. **Letter "B"**: Vertical bar should be on LEFT side when viewing from outside cylinder
4. **Letter "C"**: Opening should face RIGHT when viewing from outside cylinder

---

## Differences Between Embossing Plate and Universal Counter Plate

### CRITICAL: Card Counter Plates Use ONLY Rectangles (Never Character Indicators)

There is an intentional difference between the embossing plate and universal counter plate:

| Aspect | Embossing Plate (Positive) | Universal Counter Plate (Negative) |
|--------|---------------------------|-----------------------------------|
| **Dots** | Only active braille dots (raised) | ALL 6 dots per cell (recessed) |
| **Column 0 Indicator** | Character OR Rectangle (based on first char) | **ALWAYS Rectangle** |
| **Triangle at Last Column** | Yes (recessed) | Yes (recessed) |
| **Recess Depth** | 0.5-0.6mm per indicator type | Unified depth (based on recess_shape) |

### Rationale for Rectangle-Only on Counter Plates

The universal counter plate uses rectangles instead of character indicators because:

1. **Universal Compatibility**: Counter plates are designed to work with ANY embossing plate, regardless of text content
2. **Manufacturing Simplicity**: Consistent rectangle shape is easier to manufacture
3. **Alignment Focus**: The rectangle serves as an alignment guide, not content identification

### Implementation (Consistent Across All Methods)

**Python Backend** (`backend.py` line 1166):
```python
# In create_universal_counter_plate_2d()
# Rectangle at first column (line end marker)
rect = create_line_marker_polygon(x_pos_first, y_pos, params)
indicator_holes.append(rect)
```

**CSG Workers** (`geometry_spec.py` for negative card plates):
```python
# Universal counter plates ALWAYS use rectangle markers at column 0
# (never character indicators) - matches backend.py behavior
spec['markers'].append({'type': 'rect', ...})
```

---

## Column Layout Summary

### Cards (Flat Plates) with Indicators Enabled

**Embossing Plate (Positive):**
```
Column 0:           Character/Rectangle indicator (based on first char of row)
Columns 1 to N-2:   Braille content (shifted by 1)
Column N-1:         Triangle marker (at last cell)

Where N = grid_columns (default 13)
Available braille columns = N - 2 = 11
```

**Universal Counter Plate (Negative):**
```
Column 0:           Rectangle ONLY (never character)
Columns 1 to N-2:   ALL 6 dot recesses per cell (shifted by 1)
Column N-1:         Triangle marker (at last cell)

Where N = grid_columns (default 13)
```

### Cylinders with Indicators Enabled

**Positive/Embossing Plate:**
```
Column 0:           Triangle marker
Column 1:           Character/Rectangle indicator (based on first char)
Columns 2 to N-1:   Braille content (shifted by 2)

Where N = grid_columns
Available braille columns = N - 2
```

**Counter/Negative Plate (CONSISTENT across all methods):**
```
Column 0:           Triangle marker (rotate_180 = true)
Column 1:           Rectangle placeholder (ALWAYS rectangle, not character)
Columns 2 to N-1:   ALL 6 dot recesses per cell

Where N = grid_columns
```

---

## Recess Depth Differences

### Embossing Plate (Positive) Indicator Depths

All indicators on embossing plates are recesses (subtracted from the raised surface):

| Indicator Type | Depth | Notes |
|----------------|-------|-------|
| Triangle Marker | 0.6mm | Standard depth |
| Rectangle Marker | 0.5mm | Standard fallback depth |
| Character Marker | 0.5mm | Matches rectangle marker depth |

### Universal Counter Plate (Negative) Depths

The counter plate uses a **unified recess depth** for ALL features (dots and indicators):

```python
# From backend.py create_universal_counter_plate_2d()
# Recess depth is determined by the recess_shape setting:

if recess_shape == 2:  # Cone
    recess_depth = cone_counter_dot_height  # Default 0.8mm
elif recess_shape == 1:  # Bowl
    recess_depth = counter_dot_depth  # Default 0.6mm
else:  # Hemisphere (recess_shape == 0)
    recess_depth = hemi_counter_dot_base_diameter / 2  # Half the diameter
```

| Recess Shape | Depth Source | Typical Depth |
|--------------|--------------|---------------|
| Cone (2) | `cone_counter_dot_height` | 0.8mm |
| Bowl (1) | `counter_dot_depth` | 0.6mm |
| Hemisphere (0) | `hemi_counter_dot_base_diameter / 2` | ~0.8mm |

**Key Difference**: On counter plates, the triangle and rectangle indicators use the SAME depth as the dot recesses, not their individual depths (0.6mm, 0.5mm).

---

## Cylinder Angular Calculations

### Key Formulas

```python
# From geometry_spec.py

# Grid dimensions
grid_width = (grid_columns - 1) * cell_spacing  # Physical width in mm
grid_angle = grid_width / radius                 # Angular span in radians
start_angle = -grid_angle / 2                    # Center the content

# Per-cell calculations
cell_spacing_angle = cell_spacing / radius       # Angle between cells
dot_spacing_angle = dot_spacing / radius         # Angle between dots in cell

# Angular position for column N
column_angle = start_angle + (N * cell_spacing_angle)
```

### Seam Offset (Polygon Cutout Only)

The `seam_offset_deg` parameter rotates **ONLY the polygon cutout**, not the braille content:

```python
# From geometry_spec.py

seam_offset_rad = math.radians(seam_offset)
if plate_type == 'negative':
    # Counter plate: rotate polygon CLOCKWISE
    cutout_align_theta = seam_offset_rad
else:
    # Embossing plate: rotate polygon COUNTER-CLOCKWISE
    cutout_align_theta = -seam_offset_rad
```

### Angular Direction Functions

```python
def apply_seam(angle: float) -> float:
    """For positive/embossing plate - content flows COUNTER-CLOCKWISE."""
    return -angle

def apply_seam_mirrored(angle: float) -> float:
    """For counter plate - content flows CLOCKWISE (mirrored)."""
    return +angle
```

---

## Radial Positioning (Cylinder Dots and Markers)

### Key Principle

All features (dots, markers) must be positioned at the correct radial distance and oriented to point radially outward.

### Radial Offset Calculation

```javascript
// For recesses (counter plates, all markers)
if (is_recess) {
    if (shape === 'cone') {
        radialOffset = cylRadius - dotHeight / 2;
    } else {
        // Spherical shapes (hemisphere, bowl)
        radialOffset = cylRadius;  // Center at surface
    }
} else {
    // For protrusions (embossing dots)
    radialOffset = cylRadius + dotHeight / 2 + epsilon;
}

// Final 3D position
const posX = radialOffset * Math.cos(theta);
const posZ = radialOffset * Math.sin(theta);  // Z for Three.js, Y for Manifold
const posY = y_local;  // Height along cylinder axis
```

### Orientation Transformations

**For Three.js (Y-up, csg-worker.js):**
```javascript
// Rotate cone frustum to point radially outward
geometry.rotateZ(-Math.PI / 2);  // Align with +X
geometry.rotateY(-theta);         // Point toward radial direction

// For markers (extrusions along depth)
geometry.rotateY(Math.PI / 2 - theta);  // Depth points radially
```

**For Manifold (Z-up, csg-worker-manifold.js):**
```javascript
// Rotate frustum to point radially
dot.rotate(0, 90, 0);            // Z -> X (radial at theta=0)
rotatedDot.rotate(0, 0, thetaDeg);  // Rotate to correct angle

// For markers
marker.rotate(0, 0, thetaDeg - 90);  // Y (depth) points radially
```

---

## Common Orientation Bugs and Solutions

### Bug 1: Triangle Pointing Wrong Direction on Counter Plates

**Symptom**: Triangle apex points right instead of left on counter plate
**Cause**: Missing `rotate_180` flag
**Solution**: Ensure counter plate triangles have `rotate_180: true`

### Bug 2: Markers Not Visible on Cylinder

**Symptom**: Markers appear inside cylinder or float outside
**Cause**: Incorrect radial offset calculation
**Solution**: Verify `radialOffset = cylRadius - depth/2` for recesses

### Bug 3: Dots/Markers at Wrong Angle

**Symptom**: Features appear rotated or at wrong position around cylinder
**Cause**: Sign error in `apply_seam` or `apply_seam_mirrored`
**Solution**:
- Positive plate: `theta = -raw_angle` (counter-clockwise)
- Counter plate: `theta = +raw_angle` (clockwise)

### Bug 4: Cylinder Upside Down in STL

**Symptom**: Cylinder appears inverted when imported to slicer
**Cause**: Missing final rotation in Three.js CSG worker
**Solution**: Apply `geometry.rotateX(Math.PI / 2)` after CSG operations

### Bug 5: Character Indicators Missing on Cylinders

**Symptom**: No character shapes, only rectangles
**Cause**: Font loading failed in CSG worker
**Solution**: Check console for font loading errors, falls back to rectangle

### Bug 6: Counter Plate Recess Depths Don't Match Individual Marker Depths

**Symptom**: Counter plate indicator recesses are shallower/deeper than expected
**Cause**: Counter plate uses unified `recess_depth` for ALL features, not individual marker depths
**Note**: This is intentional behavior - counter plates use consistent depth based on `recess_shape` setting
**No fix needed**: This is by design for manufacturing consistency

---

## Validation Checklist

When implementing or modifying indicator code, verify:

### Triangle Marker
- [ ] Apex points RIGHT on positive plates
- [ ] Apex points LEFT on counter plates (rotate_180 for cylinders)
- [ ] Depth is 0.6mm on embossing plates
- [ ] Depth matches recess_shape setting on counter plates
- [ ] Positioned at correct column (last for cards, first for cylinders)

### Rectangle Marker
- [ ] Width = dot_spacing, Height = 2 × dot_spacing
- [ ] Depth is 0.5mm on embossing plates
- [ ] Depth matches recess_shape setting on counter plates
- [ ] Centered at (x + dot_spacing/2, y)
- [ ] Counter plate cylinders ALWAYS use rectangle at column 1
- [ ] Universal counter plates for CARDS use rectangle ONLY at column 0

### Character Marker
- [ ] Only created when first character is alphanumeric
- [ ] Depth is 0.5mm on embossing plates (matches rectangle)
- [ ] Width = dot_spacing, Height = 2 × dot_spacing (fits within cell)
- [ ] Falls back to rectangle on failure
- [ ] NOT used on counter plate cylinders
- [ ] NOT used on universal counter plates for CARDS
- [ ] **Manifold WASM**: Letters horizontally mirrored for correct outside-cylinder viewing
- [ ] **Manifold WASM**: Asymmetric letters (B, C, D, etc.) appear correctly oriented

### All Markers
- [ ] Always SUBTRACTED (recessed), never added
- [ ] Correct coordinate system transformations applied
- [ ] Final STL is Z-up orientation

### Consistency Checks
- [ ] Python backend output matches CSG worker output for same inputs
- [ ] Embossing and counter plates align when pressed together
- [ ] All features are within the plate boundaries
- [ ] Counter plates have rectangle indicators only (never characters)

---

## Test Cases

### Flat Card Tests

1. **All rows with alphanumeric first character**
   - Expected: Character indicators at column 0, triangles at column N-1

2. **Mixed first characters (some symbols)**
   - Expected: Characters for alphanumeric, rectangles for symbols/empty

3. **Empty rows**
   - Expected: Rectangle at column 0, triangle at column N-1

### Cylinder Tests

1. **Positive plate with text**
   - Expected: Triangles at column 0, characters at column 1, braille at 2+

2. **Counter plate**
   - Expected: Rotated triangles at column 0, rectangles at column 1, recesses at 2+

3. **Verify alignment by visual inspection**
   - Place generated positive and negative STLs together
   - Triangle apexes should point toward each other
   - All features should align when plates are pressed together

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-10-11 | 1.0 | Initial documentation during Phase 0 refactoring |
| 2024-12-06 | 2.0 | Expanded with Manifold WASM implementation details, coordinate system documentation, common bugs |
| 2024-12-06 | 2.1 | Changed character marker depth from 1.0mm to 0.5mm; Added Section 3.1 with detailed Manifold WASM character generation specifications including bitmap font format, pixel-to-box conversion algorithm, horizontal mirroring requirements, and coordinate system details |

---

## Related Documentation

- `CLIENT_SIDE_CSG_DOCUMENTATION.md` - Overall CSG architecture
- `MANIFOLD_WASM_IMPLEMENTATION.md` - Manifold integration for mesh repair
- `MANIFOLD_CYLINDER_FIX.md` - Manifold-based cylinder generation
- `EMBOSSING_PLATE_RECESS_FIX.md` - Fix for embossing plate recesses
- `geometry_spec.py` - Geometry specification extraction (authoritative parameter source)
