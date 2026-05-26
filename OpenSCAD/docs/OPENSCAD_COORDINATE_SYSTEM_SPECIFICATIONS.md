# OpenSCAD Braille Generator - Coordinate System and Geometry Specifications

## Version History
| Date | Version | Changes |
|------|---------|---------|
| 2024-12-09 | 1.0 | Initial specification document |

---

## 1. OpenSCAD Coordinate System

### 1.1 Global Coordinate System

OpenSCAD uses a **right-handed Z-up coordinate system**:

```
        Z (up)
        |
        |
        |_______ Y
       /
      /
     X
```

| Axis | Direction | Braille Context |
|------|-----------|-----------------|
| X | Right | Around cylinder circumference (angular) |
| Y | Forward | Height along cylinder axis |
| Z | Up | Radial outward from cylinder center |

### 1.2 Cylinder Orientation

The cylinder is generated with its axis along Z, then positioned upright for printing:

```openscad
// Cylinder with axis along Z (height = cylinder_height_mm)
cylinder(h = cylinder_height_mm, r = cylinder_diameter_mm / 2, center = true);

// After translate([0, 0, cylinder_height_mm/2]):
// - Cylinder base at Z=0
// - Cylinder top at Z=cylinder_height_mm
// - Cylinder axis along Z
```

**IMPORTANT:** In the context of dot placement on cylinder surfaces:
- The cylinder's Z-axis corresponds to the "height" direction
- Dots are placed radially outward in the XY-plane
- Angular position θ determines X,Y coordinates: `(r*cos(θ), r*sin(θ))`

---

## 2. Braille Dot Geometry Construction

### 2.1 Rounded Dot Structure

The rounded dot consists of two parts:

```
                    ┌───────┐
                   /  DOME   \     ← Spherical cap (dome_height)
                  /           \
                 └─────────────┘   ← Dome base = Frustum top
                /               \
               /    FRUSTUM      \  ← Conical frustum (base_height)
              /                   \
             └─────────────────────┘ ← Frustum base (base_diameter)
```

### 2.2 Geometry Construction (Card Surface - Base at Z=0)

For **cards**, the dot is built with its base at Z=0:

```openscad
// Frustum: spans z=0 to z=base_height
translate([0, 0, base_height / 2])
cylinder(h = base_height, r1 = base_radius, r2 = top_radius, center = true);

// Dome: base at z=base_height, top at z=base_height+dome_height
// (spherical cap positioned at top of frustum)
```

**Geometry bounds:** `z ∈ [0, base_height + dome_height]`

### 2.3 Geometry Construction (Cylinder Surface - Centered at Origin)

For **cylinders**, the dot must be centered at Z=0 for correct radial positioning:

```openscad
// Total height
total_height = base_height + dome_height;

// Create centered geometry
translate([0, 0, -total_height / 2]) {
    // Same frustum + dome construction as cards
    // This translation centers the combined geometry at Z=0
}
```

**Geometry bounds after centering:** `z ∈ [-total_height/2, +total_height/2]`

---

## 3. Cylinder Surface Positioning

### 3.1 The Rotation-Translation Sequence

To place a dot on the cylinder surface:

```openscad
translate([radialOffset * cos(θ), radialOffset * sin(θ), height_position])
rotate([0, 90, θ])
centered_dot();
```

The order of transformations in OpenSCAD is **right-to-left** (innermost first):
1. `centered_dot()` - Create dot geometry centered at origin, axis along +Z
2. `rotate([0, 90, θ])` - Rotate to point radially outward at angle θ
3. `translate(...)` - Move to position on cylinder surface

### 3.2 Understanding `rotate([0, 90, θ])`

OpenSCAD applies rotations around the **original (global) axes** in order X, Y, Z:

| Step | Rotation | Effect on +Z axis |
|------|----------|-------------------|
| 1 | 0° around X | No change |
| 2 | 90° around Y | +Z → +X (dot now points along +X) |
| 3 | θ° around Z | +X → (cos(θ), sin(θ), 0) (radial direction) |

**Result:** The dot's original +Z axis now points in the radial direction at angle θ.

### 3.3 Point Transformation Analysis

For a centered dot with geometry spanning `z ∈ [-h/2, +h/2]`:

| Original Point | After rotate([0, 90, θ]) | After translate to (R·cos(θ), R·sin(θ), z_pos) |
|----------------|--------------------------|------------------------------------------------|
| (0, 0, -h/2) | (-h/2·cos(θ), -h/2·sin(θ), 0) | ((R - h/2)·cos(θ), (R - h/2)·sin(θ), z_pos) |
| (0, 0, 0) | (0, 0, 0) | (R·cos(θ), R·sin(θ), z_pos) |
| (0, 0, +h/2) | (+h/2·cos(θ), +h/2·sin(θ), 0) | ((R + h/2)·cos(θ), (R + h/2)·sin(θ), z_pos) |

Where `R = radialOffset` and `h = total_height`.

### 3.4 Radial Offset Formula for Protrusions

For a **centered** dot to sit flush with the cylinder surface:

```
radialOffset = cylRadius + total_height / 2
```

**Verification:**
- Dot base (at z = -h/2 originally) → radial distance = R - h/2 = cylRadius ✓ (flush with surface)
- Dot top (at z = +h/2 originally) → radial distance = R + h/2 = cylRadius + h ✓ (extends outward)

### 3.5 CRITICAL: Why Centering is Required

If the dot is **NOT** centered (base at z=0, top at z=h):

| Original Point | After rotate | After translate to (R·cos(θ), R·sin(θ), z_pos) |
|----------------|--------------|------------------------------------------------|
| (0, 0, 0) [base] | (0, 0, 0) | (R·cos(θ), R·sin(θ), z_pos) |
| (0, 0, h) [top] | (h·cos(θ), h·sin(θ), 0) | ((R + h)·cos(θ), (R + h)·sin(θ), z_pos) |

With `R = cylRadius + h/2`:
- Base at radial distance = R = cylRadius + h/2 ❌ (GAP of h/2 from surface!)
- Top at radial distance = R + h = cylRadius + 3h/2 ❌

**This is why the "stable" version had floating dots!**

---

## 4. Comparison with Other Coordinate Systems

### 4.1 Python Backend (trimesh) - Z-up

```python
# Frustum created centered at origin: z ∈ [-base_h/2, +base_h/2]
frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h)

# Dome positioned at top of frustum
# Combined geometry: z ∈ [-base_h/2, base_h/2 + dome_h]

# Center offset correction:
# Geometric center is at z = dome_h / 2
# Translation by [0, 0, -dome_h / 2] centers at origin
dot.apply_translation([0.0, 0.0, -dome_h / 2.0])
```

### 4.2 Three.js CSG Worker - Y-up

```javascript
// Three.js uses Y-up, so "height" direction is Y
// Frustum: y ∈ [-base_h/2, +base_h/2] (CylinderGeometry is centered)
// Dome positioned at y = base_h/2
// Combined: y ∈ [-base_h/2, base_h/2 + dome_h]

// Center correction:
geometry.translate(0, -validDomeHeight / 2, 0);

// For cylinder surface:
geometry.rotateZ(-Math.PI / 2);  // Y-axis → X-axis
geometry.rotateY(-theta);         // Orient radially
```

### 4.3 OpenSCAD - Z-up (Different Construction)

```openscad
// OpenSCAD frustum with center=true is centered
// But we translate it up to start at z=0:
translate([0, 0, base_height / 2])
cylinder(h = base_height, center = true);
// Result: z ∈ [0, base_height]

// Combined geometry: z ∈ [0, base_height + dome_height]
// Geometric center at z = (base_height + dome_height) / 2

// To center at z=0:
translate([0, 0, -(base_height + dome_height) / 2])
```

**KEY DIFFERENCE:** OpenSCAD's construction starts at z=0, not centered like Python/Three.js. Therefore, the centering translation must be `-(total_height / 2)`, not `-(dome_height / 2)`.

---

## 5. Dome Orientation

### 5.1 Correct Dome Orientation

The dome (spherical cap) must point **outward** from the cylinder surface:

```
  Cylinder       Dot (correct)
  Surface
    |            ┌───┐
    |           /DOME \   ← Dome faces outward
    |__________|_______|
              FRUSTUM
```

### 5.2 How Rotation Affects Dome Position

After `rotate([0, 90, θ])`:
- Original +Z (where dome points) → radial outward direction
- Original -Z (frustum base) → radial inward direction

For a centered dot:
- Dome (at +z side) ends up at outer edge (correct ✓)
- Frustum base (at -z side) ends up at cylinder surface (correct ✓)

---

## 6. Complete Cylinder Dot Placement Algorithm

### 6.1 Pseudocode

```
For each braille dot on cylinder surface:
    1. Calculate angular position θ (radians)
    2. Calculate height position z_pos along cylinder axis
    3. Calculate total dot height: h = base_height + dome_height
    4. Calculate radial offset: R = cylRadius + h/2
    5. Create centered dot geometry (z ∈ [-h/2, +h/2])
    6. Rotate: rotate([0, 90, θ * 180/π])
    7. Translate: translate([R*cos(θ), R*sin(θ), z_pos])
```

### 6.2 OpenSCAD Implementation

```openscad
module braille_dot_centered_cylinder() {
    total_height = rounded_dot_base_height + rounded_dot_dome_height;
    
    // Center the geometry at origin
    translate([0, 0, -total_height / 2]) {
        union() {
            // Frustum: z = 0 to z = base_height
            translate([0, 0, rounded_dot_base_height / 2])
            cylinder(
                h = rounded_dot_base_height,
                r1 = rounded_dot_base_diameter / 2,
                r2 = rounded_dot_dome_diameter / 2,
                center = true
            );
            // Dome: z = base_height to z = base_height + dome_height
            // (spherical cap or scaled sphere)
        }
    }
}

// Placement on cylinder:
theta_deg = angle_rad * 180 / PI + seam_offset_degrees;
radial_offset = radius + active_emboss_height / 2;

translate([radial_offset * cos(theta_deg), radial_offset * sin(theta_deg), z_position])
rotate([0, 90, theta_deg])
braille_dot_centered_cylinder();
```

---

## 7. Validation Checklist

### 7.1 Visual Verification

- [ ] Dot base touches cylinder outer surface (no gap)
- [ ] Dome points radially outward (not inward)
- [ ] Dots maintain correct position at various cylinder diameters
- [ ] Dot height extends outward from surface

### 7.2 Numerical Verification

For a dot with:
- `base_height = 0.2mm`
- `dome_height = 0.6mm`
- `total_height = 0.8mm`
- `cylinder_radius = 15mm`

Expected:
- `radialOffset = 15 + 0.4 = 15.4mm`
- Dot base at radial distance: `15.4 - 0.4 = 15.0mm` (cylinder surface ✓)
- Dot top at radial distance: `15.4 + 0.4 = 15.8mm` (0.8mm above surface ✓)

---

## 8. Cone Dot Handling

### 8.1 Cone Dots Are Already Centered

When using `center = true` with OpenSCAD's `cylinder()`:

```openscad
cylinder(h = height, r1 = base_r, r2 = top_r, center = true);
// Geometry: z ∈ [-height/2, +height/2] ✓ Already centered
```

No additional centering translation is needed for cone dots.

### 8.2 Comparison Table

| Dot Type | Original Bounds | Centering Translation | Final Bounds |
|----------|-----------------|----------------------|--------------|
| Cone | [-h/2, +h/2] | None needed | [-h/2, +h/2] |
| Rounded | [0, base_h + dome_h] | `-(base_h + dome_h) / 2` | [-total_h/2, +total_h/2] |

---

## 9. Related Documentation

- `README.md` - Overview and usage
- `Braille_Card_And_Cylinder_STL_Generator.scad` - Main OpenSCAD implementation
- `PARAMETER_MAPPING.md` - OpenSCAD to web UI parameter correspondence

Note: This document includes some historical comparison notes to the Python/Three.js implementation used by the web app. The web app source/specs are not present in this OpenSCAD-only branch.

---

## 10. Known Issues and Solutions

### Issue 1: Floating Rounded Dots (FIXED)

**Symptom:** Gap between dot base and cylinder surface.

**Cause:** Using card-style dot (base at z=0) with cylinder positioning formula without centering.

**Solution:** Use centered dot geometry for cylinder placement with `translate([0, 0, -total_height/2])`.

### Issue 2: Inverted Dome Orientation (FIXED)

**Symptom:** Dome points inward toward cylinder center.

**Cause:** Incorrect centering translation using Python/JS formula instead of OpenSCAD-specific formula.

**Solution:** The centering translation must be `-(base_height + dome_height) / 2`, not `-(dome_height / 2)`.

### Issue 3: Truncated Dome / Wrong Sphere Center (FIXED)

**Symptom:** Dome appears flat-topped instead of smoothly curved; small gap persists.

**Cause:** When using spherical cap geometry, the sphere center formula was incorrect:
- **Wrong:** `center_z = base_height + (R_sphere - dome_height)`
- **Correct:** `center_z = base_height + dome_height - R_sphere`

The wrong formula places the sphere center too high, causing the sphere apex to extend beyond the clipping region.

**Solution:** Use correct spherical cap formula matching Python backend:
```openscad
// Calculate sphere radius for spherical cap
_dome_r = dome_diameter / 2;
_R_sphere = (_dome_r² + dome_height²) / (2 * dome_height);

// Sphere center positioned so cap base = dome_diameter, apex at correct height
_center_z = base_height + dome_height - _R_sphere;

intersection() {
    translate([0, 0, _center_z])
    sphere(r = _R_sphere);
    // Clip to only show cap above z = base_height
    translate([0, 0, base_height + _R_sphere])
    cube([_R_sphere * 4, _R_sphere * 4, _R_sphere * 2], center = true);
}
```

**Verification (with defaults: dome_diameter=1.5mm, dome_height=0.6mm):**
- R_sphere = (0.75² + 0.6²) / (2 × 0.6) = 0.76875mm
- center_z = 0.2 + 0.6 - 0.76875 = 0.03125mm
- At z = 0.2 (joint): sphere radius = sqrt(R² - (0.2 - 0.03125)²) = sqrt(0.591 - 0.0285) = 0.75mm ✓
- This exactly matches dome_diameter/2 = 0.75mm → seamless joint!

### Issue 4: Mismatched Frustum/Dome Junction (FIXED)

**Symptom:** Dome diameter doesn't match frustum top diameter; visible seam or step at the joint.

**Cause:** Using scaled sphere approach instead of proper spherical cap. A scaled sphere creates an ellipsoid where the equator radius doesn't match the intended dome base.

**Solution:** Use proper spherical cap formula (see Issue 3). The formula `R = (r² + h²) / (2h)` ensures that the sphere cross-section at the cap base has exactly radius `r = dome_diameter/2`, creating a perfect match with the frustum top.

