# Braille Dot Adjustments Specifications

## Document Purpose

This document provides **comprehensive, in-depth specifications** for all Braille Dot Adjustment controls available in the application UI. It serves as an authoritative reference for future development by documenting:

1. **UI Controls** — The radio dials, input fields, and their intended behaviors
2. **Named Parts of Braille Dots** — Anatomical terminology for each shape component
3. **Parameter Flow** — How UI values propagate through backend, WSGI, CSG workers, and Manifold WASM
4. **Geometric Transformations** — Exact mathematical formulas and calculations

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source
2. `wsgi.py` / `app/models.py` — Configuration and defaults
3. `static/workers/csg-worker.js` — Client-side CSG (three-bvh-csg)
4. `static/workers/csg-worker-manifold.js` — Manifold WASM fallback

---

## Table of Contents

1. [UI Layout: Braille Dot Adjustments Submenu](#1-ui-layout-braille-dot-adjustments-submenu)
2. [Shape Selection Radio Controls](#2-shape-selection-radio-controls)
3. [Embossing Plate: Rounded Shape Parameters](#3-embossing-plate-rounded-shape-parameters)
4. [Embossing Plate: Cone Shape Parameters](#4-embossing-plate-cone-shape-parameters)
5. [Counter Plate: Rounded (Bowl) Shape Parameters](#5-counter-plate-rounded-bowl-shape-parameters)
6. [Counter Plate: Cone Shape Parameters](#6-counter-plate-cone-shape-parameters)
7. [Parameter Flow: UI to Backend](#7-parameter-flow-ui-to-backend)
8. [Geometry Construction Details](#8-geometry-construction-details)
9. [Cross-Implementation Consistency](#9-cross-implementation-consistency)
10. [Default Values Reference](#10-default-values-reference)
11. [Validation and Constraints](#11-validation-and-constraints)
12. [Known Issues and Workarounds](#12-known-issues-and-workarounds)

---

## 1. UI Layout: Braille Dot Adjustments Submenu

### Location in Application

The Braille Dot Adjustments controls are located under:

```
Expert Mode → Braille Dot Adjustments (submenu)
```

This submenu is **collapsed by default** and must be expanded by clicking the toggle button.

### Submenu Structure

The submenu contains **four grouped sections**:

```
┌──────────────────────────────────────────────────────────────────┐
│  ▼ Braille Dot Adjustments                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─ Embossing Braille Dot Dimensions (Rounded Shape) ──────────┐ │
│  │  • Rounded braille dot base diameter (cone base)            │ │
│  │  • Rounded braille dot base height (cone height)            │ │
│  │  • Rounded braille dome diameter (linked to cone flat top)  │ │
│  │  • Rounded braille dot dome height                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Embossing Braille Dot Dimensions (Cone Shape) ─────────────┐ │
│  │  • Dot diameter                                              │ │
│  │  • Dot height                                                │ │
│  │  • Flat hat diameter                                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Counter Braille Recessed Dot Dimensions (Rounded Shape) ───┐ │
│  │  • Bowl Recess Dot Base Diameter                            │ │
│  │  • Bowl Recess Dot Depth                                    │ │
│  │  [Hidden: Hemisphere Recess Dot Base Diameter]              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Counter Braille Recessed Dot Dimensions (Cone Shape) ──────┐ │
│  │  • Dot Base Diameter                                         │ │
│  │  • Dot Height                                                │ │
│  │  • Dot Flat Hat Diameter                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Shape Selection Radio Controls

### Primary Shape Selector: Combined Shape

The primary shape selection is controlled by the **"Braille Dot Shape (Emboss and Counter)"** radio group located in:

```
Expert Mode → Shape Selection → Braille Dot Shape (Emboss and Counter)
```

| UI Option | UI Value | Effect on Emboss Plate | Effect on Counter Plate |
|-----------|----------|------------------------|-------------------------|
| **Rounded** | `'rounded'` | Cone frustum base + spherical cap dome | Bowl (spherical cap) recess |
| **Cone** | `'cone'` | Truncated cone frustum with flat top | Inverted cone frustum recess |

### Hidden Backend Compatibility Radios

Two hidden radio groups maintain backend compatibility:

```html
<!-- Hidden radio buttons for backend compatibility -->
<input type="radio" name="dot_shape" value="rounded" checked>
<input type="radio" name="dot_shape" value="cone">
<input type="radio" name="recess_shape" value="1" checked>  <!-- Bowl -->
<input type="radio" name="recess_shape" value="2">          <!-- Cone -->
```

### Radio Interaction Logic

When the user selects a Combined Shape option:

```javascript
// JavaScript synchronization logic
if (savedCombined === 'rounded') {
    dotShapeRadios.forEach(r => { if (r.value === 'rounded') r.checked = true; });
    recessShapeRadios.forEach(r => { if (r.value === '1') r.checked = true; }); // Bowl
    // use_rounded_dots = 1, recess_shape = 1
} else if (savedCombined === 'cone') {
    dotShapeRadios.forEach(r => { if (r.value === 'cone') r.checked = true; });
    recessShapeRadios.forEach(r => { if (r.value === '2') r.checked = true; }); // Cone
    // use_rounded_dots = 0, recess_shape = 2
}
```

### Backend Parameter Mapping

| UI Combined Shape | `use_rounded_dots` | `recess_shape` | Emboss Shape | Counter Shape |
|-------------------|-------------------|----------------|--------------|---------------|
| `'rounded'` | `1` | `1` (Bowl) | Rounded Dome | Bowl (Spherical Cap) |
| `'cone'` | `0` | `2` (Cone) | Cone Frustum | Inverted Cone Frustum |

---

## 3. Embossing Plate: Rounded Shape Parameters

### Anatomical Parts of a Rounded Dot

```
                    ┌─────────┐
                 .-'         '-.
              .-'               '-.           ← Dome (Spherical Cap)
           .-'                     '-.
          ┌───────────────────────────┐       ← Junction Line (dome_diameter)
         /                             \
        /                               \     ← Frustum Wall (tapered)
       /                                 \
      └───────────────────────────────────┘   ← Base Ring (base_diameter)
      ═══════════════════════════════════════ ← Plate Surface (z = card_thickness)

      │← ─ ─ ─ base_height ─ ─ ─ →│
      │                            │← ─ dome_height ─ →│
      │← ─ ─ ─ ─ ─ total height ─ ─ ─ ─ ─ ─ ─ ─ ─ →│
```

### UI Controls (Rounded Shape)

| UI Label | Input ID | Parameter Name | Default | Min | Max | Step | Unit |
|----------|----------|----------------|---------|-----|-----|------|------|
| Rounded braille dot base diameter (cone base) | `rounded_dot_base_diameter` | `rounded_dot_base_diameter` | 2.0 | 0.5 | 3.0 | 0.1 | mm |
| Rounded braille dot base height (cone height) | `rounded_dot_base_height` | `rounded_dot_base_height` | 0.2 | 0.0 | 2.0 | 0.1 | mm |
| Rounded braille dome diameter (linked to cone flat top) | `rounded_dot_dome_diameter` | `rounded_dot_dome_diameter` | 1.5 | 0.5 | 3.0 | 0.1 | mm |
| Rounded braille dot dome height | `rounded_dot_dome_height` | `rounded_dot_dome_height` | 0.6 | 0.1 | 2.0 | 0.1 | mm |

### Detailed Parameter Descriptions

#### `rounded_dot_base_diameter` (Cone Base Diameter)

**What it controls:** The diameter of the frustum base ring where the dot contacts the plate surface.

**Visual effect:** Larger values create a wider footprint; smaller values create a narrower stem.

**Relationship:** The base diameter must be ≥ dome diameter for proper geometry.

```
Impact on geometry:
  base_radius = rounded_dot_base_diameter / 2
  frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h, sections=48)
```

#### `rounded_dot_base_height` (Frustum Height)

**What it controls:** The vertical height of the conical frustum portion below the dome.

**Visual effect:**
- `0.0` — No frustum; dome sits directly on plate surface
- `0.2` (default) — Short frustum provides smooth transition
- Higher values — Taller stem with dome elevated above plate

**Special case:** When `base_height = 0`, only the dome is generated:

```python
# Python backend (dot_shapes.py)
if base_h > 0:
    frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h, sections=48)
    # Scale top vertices to create taper
    ...
    parts.append(frustum)
# Dome is always added regardless of base_height
```

#### `rounded_dot_dome_diameter` (Dome Base / Junction Diameter)

**What it controls:** The diameter at the junction between the frustum's flat top and the dome's base. This value is also the frustum's top diameter.

**Critical constraint:** This diameter defines where the dome meets the frustum. The dome radius is calculated based on this value and `dome_height`.

**UI Note:** Label states "linked to cone flat top" — this means adjusting this value simultaneously affects:
1. The frustum's top ring diameter (scale factor applied)
2. The dome's base attachment diameter

#### `rounded_dot_dome_height` (Dome Vertical Extent)

**What it controls:** The vertical height of the spherical cap dome above the frustum.

**Critical Formula — Dome Sphere Radius:**

```
R = (r² + h²) / (2h)

Where:
  r = rounded_dot_dome_diameter / 2  (dome base radius)
  h = rounded_dot_dome_height         (dome height)
  R = calculated sphere radius        (R ≥ r always)
```

**Example calculation with defaults:**
```
r = 1.5 / 2 = 0.75 mm
h = 0.6 mm

R = (0.75² + 0.6²) / (2 × 0.6)
R = (0.5625 + 0.36) / 1.2
R = 0.9225 / 1.2
R = 0.76875 mm
```

### Total Height Calculation

```
active_dot_height = rounded_dot_base_height + rounded_dot_dome_height

With defaults: 0.2 + 0.6 = 0.8 mm total height
```

### Backend Implementation (Python)

```python
# From app/geometry/dot_shapes.py

if getattr(settings, 'use_rounded_dots', 0):
    base_diameter = float(getattr(settings, 'rounded_dot_base_diameter', 2.0))
    dome_diameter = float(getattr(settings, 'rounded_dot_dome_diameter', 1.5))
    base_radius = max(0.0, base_diameter / 2.0)
    top_radius = max(0.0, dome_diameter / 2.0)
    base_h = float(getattr(settings, 'rounded_dot_base_height', 0.2))
    dome_h = float(getattr(settings, 'rounded_dot_dome_height', 0.6))

    if base_radius > 0 and base_h >= 0 and dome_h > 0:
        parts = []

        # Build frustum with tapered top
        if base_h > 0:
            frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h, sections=48)
            scale_factor = top_radius / base_radius if base_radius > 1e-9 else 1.0
            top_z = frustum.vertices[:, 2].max()
            is_top = np.isclose(frustum.vertices[:, 2], top_z)
            frustum.vertices[is_top, :2] *= scale_factor
            parts.append(frustum)

        # Spherical cap dome
        R = (top_radius * top_radius + dome_h * dome_h) / (2.0 * dome_h)
        zc = (base_h / 2.0) + (dome_h - R)
        sphere = trimesh.creation.icosphere(radius=R, subdivisions=...)
        sphere.apply_translation([0.0, 0.0, zc])
        parts.append(sphere)

        dot = trimesh.util.concatenate(parts)
        dot.apply_translation([0.0, 0.0, -dome_h / 2.0])
        dot.apply_translation((x, y, z))
```

### CSG Worker Implementation (JavaScript)

```javascript
// From static/workers/csg-worker.js

if (type === 'rounded') {
    const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;

    if (base_height > 0) {
        // Frustum base
        const frustum = createConeFrustum(base_radius, top_radius, base_height, 48);

        // Spherical cap dome
        const dome_R = dome_radius;
        const dome_zc = (base_height / 2.0) + (dome_height - dome_R);
        const dome = createSphericalCap(dome_R, dome_height, 2);
        dome.translate(0, 0, dome_zc);

        // CSG union
        const frustumBrush = new Brush(frustum);
        const domeBrush = new Brush(dome);
        const combinedBrush = evaluator.evaluate(frustumBrush, domeBrush, ADDITION);
        geometry = combinedBrush.geometry;

        geometry.translate(0, 0, -dome_height / 2.0);
        geometry.translate(x, y, z);
    } else {
        // Only dome, no frustum
        const dome = createSphericalCap(dome_radius, dome_height, 2);
        geometry = dome;
        geometry.translate(0, 0, -dome_height / 2.0);
        geometry.translate(x, y, z);
    }
}
```

---

## 4. Embossing Plate: Cone Shape Parameters

### Anatomical Parts of a Cone (Frustum) Dot

```
              ┌─────┐                         ← Flat Top (flat_hat_diameter)
             /       \
            /         \
           /           \                      ← Frustum Wall (linear taper)
          /             \
         /               \
        └─────────────────┘                   ← Base Ring (base_diameter)
        ═════════════════════════════════════ ← Plate Surface (z = card_thickness)

        │← ─ ─ ─ ─ ─ height ─ ─ ─ ─ ─ →│
```

### UI Controls (Cone Shape)

| UI Label | Input ID | Parameter Name | Default | Unit |
|----------|----------|----------------|---------|------|
| Dot diameter | `emboss_dot_base_diameter` | `emboss_dot_base_diameter` | 1.8 | mm |
| Dot height | `emboss_dot_height` | `emboss_dot_height` | 1.0 | mm |
| Flat hat diameter | `emboss_dot_flat_hat` | `emboss_dot_flat_hat` | 0.4 | mm |

### Detailed Parameter Descriptions

#### `emboss_dot_base_diameter` (Base Diameter)

**What it controls:** The diameter at the plate surface where the cone contacts the plate.

**Visual effect:** Larger values create a wider, more stable cone base.

**Relationship to flat hat:** The ratio `flat_hat / base_diameter` determines the taper angle.

#### `emboss_dot_height` (Cone Height)

**What it controls:** The total vertical height from base to flat top.

**Visual effect:** Taller cones provide deeper embossing impressions.

#### `emboss_dot_flat_hat` (Flat Top Diameter)

**What it controls:** The diameter of the flat circular surface at the top of the cone.

**Visual effect:**
- Smaller values (approaching 0) → Sharper pointed tip
- Larger values → Wider, flatter top surface
- Equal to base diameter → Cylinder (no taper)

**Tactile significance:** The flat top diameter affects the feel of the embossed dot when touched.

### Backend Implementation (Python)

```python
# From app/geometry/dot_shapes.py — Default cone frustum path

cylinder = trimesh.creation.cylinder(
    radius=settings.emboss_dot_base_diameter / 2,
    height=settings.emboss_dot_height,
    sections=16
)

if settings.emboss_dot_base_diameter > 0:
    scale_factor = settings.emboss_dot_flat_hat / settings.emboss_dot_base_diameter
    top_surface_z = cylinder.vertices[:, 2].max()
    is_top_vertex = np.isclose(cylinder.vertices[:, 2], top_surface_z)
    cylinder.vertices[is_top_vertex, :2] *= scale_factor

cylinder.apply_translation((x, y, z))
```

### CSG Worker Implementation (JavaScript)

```javascript
// From static/workers/csg-worker.js

function createConeFrustum(baseRadius, topRadius, height, segments = 16) {
    // THREE.CylinderGeometry(topRadius, bottomRadius, height, segments)
    // Note: Three.js CylinderGeometry puts topRadius first!
    const geometry = new THREE.CylinderGeometry(topRadius, baseRadius, height, segments);
    return geometry;
}

// Usage for standard cone:
const { base_radius, top_radius, height } = params;
geometry = createConeFrustum(base_radius, top_radius, height, 16);
geometry.translate(x, y, z);
```

---

## 5. Counter Plate: Rounded (Bowl) Shape Parameters

### Anatomical Parts of a Bowl Recess

```
        ═════════════════════════════════════ ← Plate Surface
        ────────────────────────────────────  ← Opening (bowl_base_diameter)
            ╲                          ╱
              ╲                      ╱
                ╲                  ╱           ← Spherical Arc Wall
                  ╲              ╱
                    ╲──────────╱              ← Bowl Bottom (curved)
                          │
                          └── counter_dot_depth
```

### UI Controls (Bowl Recess)

| UI Label | Input ID | Parameter Name | Default | Min | Max | Step | Unit |
|----------|----------|----------------|---------|-----|-----|------|------|
| Bowl Recess Dot Base Diameter | `bowl_counter_dot_base_diameter` | `bowl_counter_dot_base_diameter` | 1.8 | 0.5 | 5.0 | 0.1 | mm |
| Bowl Recess Dot Depth | `counter_dot_depth` | `counter_dot_depth` | 0.8 | 0.0 | 5.0 | 0.1 | mm |

### Hidden: Hemisphere Controls

The hemisphere option (`recess_shape = 0`) has a hidden input:

```html
<div style="display: none;">
    <label for="hemi_counter_dot_base_diameter">Hemisphere Recess Dot Base Diameter (mm):</label>
    <input type="number" id="hemi_counter_dot_base_diameter" value="1.6" step="0.1" min="0.5" max="5">
</div>
```

**Note:** Hemisphere is not currently exposed in the unified Combined Shape selector. When hemisphere is used, depth equals radius (depth = diameter / 2).

### Detailed Parameter Descriptions

#### `bowl_counter_dot_base_diameter` (Opening Diameter)

**What it controls:** The diameter of the circular opening at the plate surface.

**Visual effect:** Larger values create wider bowl openings that accommodate larger embossed dots.

**Relationship to emboss dots:** Should typically be ≥ the corresponding emboss dot base diameter to provide clearance.

#### `counter_dot_depth` (Bowl Depth)

**What it controls:** The vertical depth of the bowl recess below the plate surface.

**Critical difference from hemisphere:** Unlike hemisphere (where depth = radius), bowl depth is **independently controllable**.

**Constraint:** Clamped to range `[0, card_thickness - epsilon]` to prevent cutting through the plate.

```python
# From app/models.py
self.counter_dot_depth = max(0.0, min(depth, self.card_thickness - self.epsilon_mm))
```

### Critical Formula — Bowl Sphere Radius

To create a spherical cap with:
- Opening radius `a` = `bowl_counter_dot_base_diameter / 2`
- Depth `h` = `counter_dot_depth`

The sphere radius `R` is:

```
R = (a² + h²) / (2h)
```

**Example calculation with defaults:**
```
a = 1.8 / 2 = 0.9 mm (opening radius)
h = 0.8 mm (depth)

R = (0.9² + 0.8²) / (2 × 0.8)
R = (0.81 + 0.64) / 1.6
R = 1.45 / 1.6
R = 0.90625 mm
```

### Backend Implementation (Python)

```python
# From backend.py — build_counter_plate_bowl()

def build_counter_plate_bowl(params: CardSettings) -> trimesh.Trimesh:
    a = float(getattr(params, 'bowl_counter_dot_base_diameter', 1.8)) / 2.0
    h = float(getattr(params, 'counter_dot_depth', 0.8))

    # Calculate sphere radius for specified opening and depth
    R = (a * a + h * h) / (2.0 * h)

    sphere = trimesh.creation.icosphere(
        subdivisions=params.hemisphere_subdivisions,
        radius=R
    )
    # Position sphere center below surface so cap cuts to correct depth
    zc = params.plate_thickness - (R - h)
    sphere.apply_translation((dot_x, dot_y, zc))
```

### CSG Worker Implementation (JavaScript)

```javascript
// From static/workers/csg-worker.js

if (shape === 'bowl') {
    const { bowl_radius, bowl_depth } = params;
    const validBowlRadius = (bowl_radius > 0) ? bowl_radius : 1.5;
    const validBowlDepth = (bowl_depth > 0) ? bowl_depth : 0.8;
    dotHeight = validBowlDepth;

    // Calculate sphere radius
    const sphereR = (validBowlRadius**2 + validBowlDepth**2) / (2.0 * validBowlDepth);

    // Use full sphere for better subtraction (positioned at surface)
    geometry = new THREE.SphereGeometry(sphereR, 16, 16);
}
```

---

## 6. Counter Plate: Cone Shape Parameters

### Anatomical Parts of a Cone Recess

```
        ═════════════════════════════════════ ← Plate Surface
        ────────────────────────────────────  ← Large Opening (base_diameter)
            ╲                          ╱
              ╲                      ╱
                ╲                  ╱           ← Frustum Wall (linear taper inward)
                  ╲              ╱
                    │          │              ← Small Tip (flat_hat_diameter)
                    └──────────┘
                          │
                          └── cone_height
```

### UI Controls (Cone Recess)

| UI Label | Input ID | Parameter Name | Default | Min | Max | Step | Unit |
|----------|----------|----------------|---------|-----|-----|------|------|
| Dot Base Diameter | `cone_counter_dot_base_diameter` | `cone_counter_dot_base_diameter` | 1.6 | 0.1 | 5.0 | 0.1 | mm |
| Dot Height | `cone_counter_dot_height` | `cone_counter_dot_height` | 0.8 | 0.0 | 5.0 | 0.1 | mm |
| Dot Flat Hat Diameter | `cone_counter_dot_flat_hat` | `cone_counter_dot_flat_hat` | 0.4 | 0.0 | 5.0 | 0.1 | mm |

### Detailed Parameter Descriptions

#### `cone_counter_dot_base_diameter` (Large Opening)

**What it controls:** The diameter of the large opening at the plate surface.

**CRITICAL NOTE:** This is the **LARGE** end (at the surface), unlike emboss cones where base is also at surface but recess cones are inverted.

#### `cone_counter_dot_height` (Recess Depth)

**What it controls:** How deep the cone recess extends into the plate material.

#### `cone_counter_dot_flat_hat` (Small Tip)

**What it controls:** The diameter of the small flat bottom inside the plate.

### CRITICAL: Cone Orientation Swap

For cone recesses, the geometry must be **inverted** compared to emboss cones:

```
Emboss Cone:          Counter Cone Recess:
    ┌──┐                  ╲        ╱
   /    \                  ╲      ╱
  /      \                  ╲    ╱
 └────────┘                  └──┘

Base at surface        Large opening at surface
Tip points UP          Tip points DOWN (into material)
```

**Implementation requirement:** When creating cone recess geometry, swap base and top radii:

```javascript
// WRONG (would point outward):
geometry = createConeFrustum(baseRadius, topRadius, height);

// CORRECT (inverted for recess):
geometry = createConeFrustum(topRadius, baseRadius, height);  // Swapped!
```

### Backend Implementation (Python)

```python
# From backend.py — build_counter_plate_cone()

def build_counter_plate_cone(params: CardSettings) -> trimesh.Trimesh:
    base_d = float(getattr(params, 'cone_counter_dot_base_diameter', 1.6))
    hat_d = float(getattr(params, 'cone_counter_dot_flat_hat', 0.4))
    height_h = float(getattr(params, 'cone_counter_dot_height', 0.8))

    base_r = base_d / 2.0
    hat_r = hat_d / 2.0

    # Build inverted frustum geometry
    # Top ring (at z=0, plate surface) has LARGE radius (base_r)
    # Bottom ring (at z=-height, inside plate) has SMALL radius (hat_r)
    angles = np.linspace(0, 2 * np.pi, 17)[:-1]
    cos_angles, sin_angles = np.cos(angles), np.sin(angles)

    top_ring = np.column_stack([base_r * cos_angles, base_r * sin_angles, np.zeros_like(angles)])
    bot_ring = np.column_stack([hat_r * cos_angles, hat_r * sin_angles, -height_h * np.ones_like(angles)])
```

### CSG Worker Implementation (JavaScript)

```javascript
// From static/workers/csg-worker.js — createCylinderDot() for cone recess

if (shape === 'cone') {
    const { base_radius, top_radius, height } = params;
    const validBaseRadius = (base_radius > 0) ? base_radius : 1.0;
    const validTopRadius = (top_radius >= 0) ? top_radius : 0.25;
    const validHeight = (height > 0) ? height : 1.0;
    dotHeight = validHeight;

    // IMPORTANT: Swap base and top radii for recesses!
    // Large opening (base_radius) at surface, small tip (top_radius) inside
    geometry = createConeFrustum(validTopRadius, validBaseRadius, validHeight, 16);
}
```

---

## 7. Parameter Flow: UI to Backend

### Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Combined Shape Radio:  ○ Rounded  ● Cone                                   │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ JavaScript Event Handler                                              │    │
│  │   → Sets hidden dot_shape radio                                       │    │
│  │   → Sets hidden recess_shape radio                                    │    │
│  │   → Persists to localStorage                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
└──────────────────────────────│───────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API REQUEST                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  POST /generate_braille                                                      │
│  {                                                                           │
│    "settings": {                                                             │
│      "dot_shape": "cone",                   // or "rounded"                  │
│      "use_rounded_dots": 0,                 // derived from dot_shape        │
│      "recess_shape": 2,                     // 0=hemi, 1=bowl, 2=cone        │
│      "emboss_dot_base_diameter": 1.8,       // cone shape params             │
│      "emboss_dot_height": 1.0,                                               │
│      "emboss_dot_flat_hat": 0.4,                                             │
│      "rounded_dot_base_diameter": 2.0,      // rounded shape params          │
│      "rounded_dot_base_height": 0.2,                                         │
│      "rounded_dot_dome_diameter": 1.5,                                       │
│      "rounded_dot_dome_height": 0.6,                                         │
│      "bowl_counter_dot_base_diameter": 1.8, // bowl recess params            │
│      "counter_dot_depth": 0.8,                                               │
│      "cone_counter_dot_base_diameter": 1.6, // cone recess params            │
│      "cone_counter_dot_height": 0.8,                                         │
│      "cone_counter_dot_flat_hat": 0.4,                                       │
│      ...                                                                     │
│    },                                                                        │
│    "plate_type": "positive",                // or "negative"                 │
│    "shape_type": "cylinder",                // or "card"                     │
│    ...                                                                       │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (backend.py)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CardSettings.__init__(**kwargs):                                            │
│    │                                                                         │
│    ├─→ Map dot_shape to use_rounded_dots:                                    │
│    │     if dot_shape == 'rounded': use_rounded_dots = 1                     │
│    │     elif dot_shape == 'cone': use_rounded_dots = 0                      │
│    │                                                                         │
│    ├─→ Normalize recess_shape (0=hemi, 1=bowl, 2=cone)                       │
│    │                                                                         │
│    └─→ Calculate derived values:                                             │
│          active_dot_height = base_height + dome_height (if rounded)          │
│          active_dot_height = emboss_dot_height (if cone)                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GEOMETRY GENERATION DECISION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  if plate_type == 'positive':                                                │
│      if use_rounded_dots:                                                    │
│          create_braille_dot() → rounded path (frustum + dome)                │
│      else:                                                                   │
│          create_braille_dot() → cone path (frustum only)                     │
│                                                                              │
│  elif plate_type == 'negative':                                              │
│      if recess_shape == 0:                                                   │
│          build_counter_plate_hemispheres() → hemisphere recesses             │
│      elif recess_shape == 1:                                                 │
│          build_counter_plate_bowl() → bowl (spherical cap) recesses          │
│      elif recess_shape == 2:                                                 │
│          build_counter_plate_cone() → cone frustum recesses                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### UI Input Collection (JavaScript)

```javascript
// From templates/index.html — getSettings() function

function getSettings() {
    return {
        // Shape selection
        use_rounded_dots: (document.querySelector('input[name="dot_shape"]:checked')?.value === 'rounded') ? 1 : 0,

        // Emboss cone parameters
        emboss_dot_base_diameter: document.getElementById('emboss_dot_base_diameter').value,
        emboss_dot_height: document.getElementById('emboss_dot_height').value,
        emboss_dot_flat_hat: document.getElementById('emboss_dot_flat_hat').value,

        // Rounded dome parameters
        rounded_dot_base_diameter: document.getElementById('rounded_dot_base_diameter')?.value || '2.0',
        rounded_dot_base_height: document.getElementById('rounded_dot_base_height')?.value || '0.2',
        rounded_dot_dome_diameter: document.getElementById('rounded_dot_dome_diameter')?.value || '1.5',
        rounded_dot_dome_height: document.getElementById('rounded_dot_dome_height')?.value || '0.6',

        // Bowl recess parameters
        bowl_counter_dot_base_diameter: document.getElementById('bowl_counter_dot_base_diameter')?.value || '1.8',
        counter_dot_depth: document.getElementById('counter_dot_depth')?.value || '0.8',

        // Cone recess parameters
        cone_counter_dot_base_diameter: document.getElementById('cone_counter_dot_base_diameter')?.value || '1.6',
        cone_counter_dot_height: document.getElementById('cone_counter_dot_height')?.value || '0.8',
        cone_counter_dot_flat_hat: document.getElementById('cone_counter_dot_flat_hat')?.value || '0.4',

        // Recess shape selector
        recess_shape: document.querySelector('input[name="recess_shape"]:checked')?.value || '1',

        // ... other parameters
    };
}
```

---

## 8. Geometry Construction Details

### Coordinate System Convention

All implementations use:
- **X-axis**: Width (left-right on card, around circumference on cylinder)
- **Y-axis**: Height (up-down on card, along cylinder axis)
- **Z-axis**: Depth (out of plate surface / radially outward on cylinder)

### Position Reference Points

| Shape Component | Reference Point |
|-----------------|-----------------|
| Dot center | `(x, y)` = cell center position |
| Z position | `z = card_thickness + active_dot_height / 2` |
| Recess center | Depends on shape (see below) |

### Rounded Dot Z-Positioning

```python
# Final Z position for rounded dot center
z = settings.card_thickness + settings.active_dot_height / 2

# Where:
# active_dot_height = rounded_dot_base_height + rounded_dot_dome_height

# The dot mesh is created centered at origin, then:
#   1. Shifted down by dome_height / 2 (to position base at z=0)
#   2. Translated to (x, y, z)
```

### Cone Dot Z-Positioning

```python
# For cone frustum:
# Cylinder is created centered at origin (height spans -h/2 to +h/2)
# Then translated to final position

z = settings.card_thickness + settings.emboss_dot_height / 2
cylinder.apply_translation((x, y, z))
```

### Bowl Recess Sphere Positioning

```python
# For bowl (spherical cap) recess:
# Sphere center positioned below surface

R = (a * a + h * h) / (2.0 * h)  # Sphere radius
zc = params.plate_thickness - (R - h)  # Center Z position

# This positions the sphere so:
#   - Its topmost point is at plate_thickness (surface)
#   - The cap extends h (counter_dot_depth) into the material
```

### Cone Recess Positioning

```python
# For cone recess:
# Frustum top ring at z = plate_thickness
# Frustum bottom ring at z = plate_thickness - height

top_ring_z = params.plate_thickness + epsilon  # Slight overcut for clean boolean
bot_ring_z = params.plate_thickness - cone_counter_dot_height
```

---

## 9. Cross-Implementation Consistency

### Parameter Mapping Table

This table shows how the same logical parameter is named across different parts of the codebase:

| Logical Concept | UI Input ID | CardSettings Attribute | geometry_spec.py Key | CSG Worker params |
|-----------------|-------------|----------------------|---------------------|-------------------|
| Rounded base diameter | `rounded_dot_base_diameter` | `rounded_dot_base_diameter` | `base_radius` × 2 | `base_radius` × 2 |
| Rounded base height | `rounded_dot_base_height` | `rounded_dot_base_height` | `base_height` | `base_height` |
| Rounded dome diameter | `rounded_dot_dome_diameter` | `rounded_dot_dome_diameter` | `top_radius` × 2 | `top_radius` × 2 |
| Rounded dome height | `rounded_dot_dome_height` | `rounded_dot_dome_height` | `dome_height` | `dome_height` |
| Calculated dome sphere R | (derived) | (derived) | `dome_radius` | `dome_radius` |
| Cone base diameter | `emboss_dot_base_diameter` | `emboss_dot_base_diameter` | `base_radius` × 2 | `base_radius` × 2 |
| Cone height | `emboss_dot_height` | `emboss_dot_height` | `height` | `height` |
| Cone flat top diameter | `emboss_dot_flat_hat` | `emboss_dot_flat_hat` | `top_radius` × 2 | `top_radius` × 2 |
| Bowl opening diameter | `bowl_counter_dot_base_diameter` | `bowl_counter_dot_base_diameter` | `bowl_radius` × 2 | `bowl_radius` × 2 |
| Bowl depth | `counter_dot_depth` | `counter_dot_depth` | `bowl_depth` | `bowl_depth` |
| Cone recess opening dia | `cone_counter_dot_base_diameter` | `cone_counter_dot_base_diameter` | `base_radius` × 2 | `base_radius` × 2 |
| Cone recess depth | `cone_counter_dot_height` | `cone_counter_dot_height` | `height` | `height` |
| Cone recess tip diameter | `cone_counter_dot_flat_hat` | `cone_counter_dot_flat_hat` | `top_radius` × 2 | `top_radius` × 2 |

### Spec Type Values

| Spec `type` Value | Description | Used When |
|-------------------|-------------|-----------|
| `'standard'` | Simple cone frustum | Emboss cone, Card-based |
| `'rounded'` | Frustum + dome | Emboss rounded, Bowl/Hemisphere recess |
| `'cylinder_dot'` | Cylinder surface dot | Any dot on cylinder |

### Shape Parameter in Specs

| `params.shape` | Emboss/Counter | Geometry |
|----------------|----------------|----------|
| `'standard'` | Emboss | Cone frustum |
| `'rounded'` | Emboss | Frustum + dome |
| `'hemisphere'` | Counter | Full sphere (positioned for half) |
| `'bowl'` | Counter | Spherical cap (calculated R) |
| `'cone'` | Counter | Inverted frustum |

---

## 10. Default Values Reference

### Complete Default Values Table

From `app/models.py` — CardSettings defaults:

```python
defaults = {
    # Emboss cone parameters
    'emboss_dot_base_diameter': 1.8,    # mm
    'emboss_dot_height': 1.0,            # mm
    'emboss_dot_flat_hat': 0.4,          # mm

    # Rounded dome parameters
    'use_rounded_dots': 0,               # 0=cone, 1=rounded
    'rounded_dot_base_diameter': 2.0,    # mm
    'rounded_dot_dome_diameter': 1.5,    # mm
    'rounded_dot_base_height': 0.2,      # mm
    'rounded_dot_dome_height': 0.6,      # mm

    # Counter plate general
    'recess_shape': 1,                   # 0=hemi, 1=bowl, 2=cone

    # Hemisphere recess
    'hemi_counter_dot_base_diameter': 1.6,  # mm

    # Bowl recess
    'bowl_counter_dot_base_diameter': 1.8,  # mm
    'counter_dot_depth': 0.8,               # mm

    # Cone recess
    'cone_counter_dot_base_diameter': 1.6,  # mm
    'cone_counter_dot_height': 0.8,         # mm
    'cone_counter_dot_flat_hat': 0.4,       # mm

    # Mesh quality
    'hemisphere_subdivisions': 1,
    'cone_segments': 16,
}
```

### UI Input Default Values (from HTML)

```html
<!-- Rounded Shape -->
<input id="rounded_dot_base_diameter" value="2.0" min="0.5" max="3" step="0.1">
<input id="rounded_dot_base_height" value="0.2" min="0" max="2.0" step="0.1">
<input id="rounded_dot_dome_diameter" value="1.5" min="0.5" max="3.0" step="0.1">
<input id="rounded_dot_dome_height" value="0.6" min="0.1" max="2.0" step="0.1">

<!-- Cone Shape -->
<input id="emboss_dot_base_diameter" value="1.8" step="0.1">
<input id="emboss_dot_height" value="1.0" step="0.1">
<input id="emboss_dot_flat_hat" value="0.4" step="0.1">

<!-- Bowl Recess -->
<input id="bowl_counter_dot_base_diameter" value="1.8" min="0.5" max="5" step="0.1">
<input id="counter_dot_depth" value="0.8" min="0" max="5" step="0.1">

<!-- Cone Recess -->
<input id="cone_counter_dot_base_diameter" value="1.6" min="0.1" max="5" step="0.1">
<input id="cone_counter_dot_height" value="0.8" min="0" max="5" step="0.1">
<input id="cone_counter_dot_flat_hat" value="0.4" min="0" max="5" step="0.1">
```

---

## 11. Validation and Constraints

### UI-Level Constraints

| Parameter | Min | Max | Validation |
|-----------|-----|-----|------------|
| `rounded_dot_base_diameter` | 0.5 | 3.0 | HTML `min`/`max` |
| `rounded_dot_base_height` | 0.0 | 2.0 | HTML `min`/`max` |
| `rounded_dot_dome_diameter` | 0.5 | 3.0 | HTML `min`/`max` |
| `rounded_dot_dome_height` | 0.1 | 2.0 | HTML `min`/`max` |
| `bowl_counter_dot_base_diameter` | 0.5 | 5.0 | HTML `min`/`max` |
| `counter_dot_depth` | 0.0 | 5.0 | HTML `min`/`max` |
| `cone_counter_dot_base_diameter` | 0.1 | 5.0 | HTML `min`/`max` |
| `cone_counter_dot_height` | 0.0 | 5.0 | HTML `min`/`max` |
| `cone_counter_dot_flat_hat` | 0.0 | 5.0 | HTML `min`/`max` |

### Backend Validation

```python
# From app/models.py — CardSettings

# Ensure counts are integers
self.grid_columns = int(self.grid_columns)
self.grid_rows = int(self.grid_rows)

# Normalize toggles
self.use_rounded_dots = int(float(kwargs.get('use_rounded_dots', self.use_rounded_dots)))
self.recess_shape = int(float(kwargs.get('recess_shape', getattr(self, 'recess_shape', 1))))

# Clamp depth to safe bounds
depth = float(getattr(self, 'counter_dot_depth', 0.8))
self.counter_dot_depth = max(0.0, min(depth, self.card_thickness - self.epsilon_mm))
```

### CSG Worker Validation

```javascript
// From csg-worker.js — Parameter validation with fallbacks

const validBaseRadius = (base_radius && base_radius > 0) ? base_radius : 1.0;
const validTopRadius = (top_radius && top_radius >= 0) ? top_radius : validBaseRadius;
const validBaseHeight = (base_height && base_height >= 0) ? base_height : 0.2;
const validDomeHeight = (dome_height && dome_height > 0) ? dome_height : 0.6;
const validDomeRadius = (dome_radius && dome_radius > 0) ? dome_radius : Math.max(validTopRadius, 0.5);
```

### Geometric Constraints

1. **Dome diameter ≤ Base diameter** — For proper frustum taper
2. **Dome height > 0** — Required for sphere radius calculation (division by zero)
3. **Depth ≤ Plate thickness** — Prevent cutting through
4. **Cone tip < Opening** — For valid frustum geometry

---

## 12. Known Issues and Workarounds

### Issue 1: Card Cone Recess Inverted Orientation

**Status:** Known, Low Priority

**Symptom:** Card counter plate cone recesses via `/geometry_spec` endpoint may have incorrect orientation (small opening at surface instead of large).

**Affected Code Path:**
- `geometry_spec.py` → `_create_dot_spec()` with `shape_type='cone'` → returns `type: 'standard'`
- CSG workers create frustum without radii swap

**Why Low Priority:** Card counter plates are typically generated server-side using Python `build_counter_plate_cone()` which correctly handles orientation.

**Workaround:** Use server-side generation for card cone recesses.

### Issue 2: Dome-Frustum Junction Visibility

**Symptom:** Visible seam at junction between dome and frustum in rounded dots.

**Cause:** Dome base radius doesn't perfectly match frustum top radius due to floating-point precision.

**Mitigation:** Use higher subdivision counts for smoother meshes.

### Issue 3: Hemisphere Depth Not Independently Controllable

**Note:** This is **by design**, not a bug. Hemisphere depth equals radius.

**User expectation:** Some users expect to control hemisphere depth independently.

**Solution:** Use Bowl shape instead, which allows independent depth control.

### Issue 4: Browser-Specific Number Input Behavior

**Symptom:** `step="0.1"` validation varies across browsers.

**Workaround:** Backend accepts any valid float and clamps to safe ranges.

---

## Appendix A: Quick Reference Card

### Shape Selection Summary

| Combined Shape | Emboss Plate | Counter Plate | `use_rounded_dots` | `recess_shape` |
|----------------|--------------|---------------|-------------------|----------------|
| Rounded | Frustum + Dome | Bowl (Spherical Cap) | `1` | `1` |
| Cone | Cone Frustum | Inverted Cone Frustum | `0` | `2` |

### Key Formulas

```
# Dome sphere radius (for rounded dots and bowl recesses)
R = (r² + h²) / (2h)

# Total rounded dot height
total_height = base_height + dome_height

# Bowl sphere center position
sphere_center_z = plate_thickness - (R - depth)
```

### Parameter Groups Quick Reference

**Rounded Dot (4 params):**
- `rounded_dot_base_diameter` — Cone base at surface
- `rounded_dot_base_height` — Cone frustum height
- `rounded_dot_dome_diameter` — Junction / dome base
- `rounded_dot_dome_height` — Dome height

**Cone Dot (3 params):**
- `emboss_dot_base_diameter` — Base at surface
- `emboss_dot_height` — Total height
- `emboss_dot_flat_hat` — Flat top diameter

**Bowl Recess (2 params):**
- `bowl_counter_dot_base_diameter` — Opening diameter
- `counter_dot_depth` — Recess depth

**Cone Recess (3 params):**
- `cone_counter_dot_base_diameter` — Large opening at surface
- `cone_counter_dot_height` — Recess depth
- `cone_counter_dot_flat_hat` — Small tip inside

---

## Document History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2024-12-06 | 1.0 | AI Assistant | Initial comprehensive specification |

---

## Related Documentation

- `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md` — Shape geometry specifications
- `BRAILLE_SPACING_SPECIFICATIONS.md` — Cell, line, and dot spacing
- `RECESS_INDICATOR_SPECIFICATIONS.md` — Marker shapes (triangles, rectangles, characters)
- `CLIENT_SIDE_CSG_DOCUMENTATION.md` — CSG architecture overview
- `app/models.py` — CardSettings class definition
- `app/geometry/dot_shapes.py` — Python dot creation functions
- `geometry_spec.py` — Geometry specification extraction
