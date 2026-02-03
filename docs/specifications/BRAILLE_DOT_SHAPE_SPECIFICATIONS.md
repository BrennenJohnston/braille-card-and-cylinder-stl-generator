# Braille Dot Shape Selection Specifications

## Overview

This document provides **strict specifications** for the Braille Dot Shape selection menu, covering both embossing (positive) and counter (negative) plate operations. The specifications define the exact parameters, geometry formulas, and behavioral differences between shape options.

The authoritative implementations (in order of correctness) are:
1. **Python backend** (`backend.py`, `app/geometry/dot_shapes.py`)
2. **WSGI/API layer** (`wsgi.py`, `app/models.py`)
3. **Standard CSG Worker** (`static/workers/csg-worker.js` using three-bvh-csg)
4. **Manifold WASM Worker** (`static/workers/csg-worker-manifold.js`)

---

## 1. Shape Selection Overview

### Embossing Plate (Positive) Dot Shapes

The embossing plate supports **two dot shape options** for raised braille dots:

| Shape Option | UI Value | Internal Flag | Description |
|--------------|----------|---------------|-------------|
| **Cone (Standard)** | `'cone'` | `use_rounded_dots = 0` | Truncated cone frustum (default) |
| **Rounded (Dome)** | `'rounded'` | `use_rounded_dots = 1` | Cone frustum base + spherical cap dome |

### Counter Plate (Negative/Universal) Recess Shapes

The counter plate supports **three recess shape options** for subtracted dots:

| Shape Option | UI Value | Internal Flag | Description |
|--------------|----------|---------------|-------------|
| **Hemisphere** | `0` | `recess_shape = 0` | Full hemisphere centered at surface |
| **Bowl** | `1` | `recess_shape = 1` | Spherical cap with independent depth (default) |
| **Cone** | `2` | `recess_shape = 2` | Inverted truncated cone frustum |

---

## 2. Embossing Plate: Cone (Standard) Shape

### Description

The default cone shape creates a **truncated cone frustum** (cone with flat top) for each braille dot. This is the industry-standard shape for embossing plate dots.

### Geometry Construction

```
Shape: Cone Frustum (truncated cone)
Profile: Circular base tapering to smaller circular flat top

Parameters:
- emboss_dot_base_diameter: Base diameter at plate surface (default: 1.8mm)
- emboss_dot_flat_hat: Flat top diameter (default: 0.4mm)
- emboss_dot_height: Total height from base to flat top (default: 1.0mm)
```

### Visual Cross-Section

```
     ┌────┐  ← Flat top (emboss_dot_flat_hat / 2)
    /      \
   /        \
  /          \
 /            \
└──────────────┘  ← Base at surface (emboss_dot_base_diameter / 2)
```

### Implementation: Python Backend (`app/geometry/dot_shapes.py`)

```python
# Default cone frustum path
cylinder = trimesh.creation.cylinder(
    radius=settings.emboss_dot_base_diameter / 2,
    height=settings.emboss_dot_height,
    sections=16
)

# Scale top surface to create frustum
if settings.emboss_dot_base_diameter > 0:
    scale_factor = settings.emboss_dot_flat_hat / settings.emboss_dot_base_diameter
    top_surface_z = cylinder.vertices[:, 2].max()
    is_top_vertex = np.isclose(cylinder.vertices[:, 2], top_surface_z)
    cylinder.vertices[is_top_vertex, :2] *= scale_factor

cylinder.apply_translation((x, y, z))
```

### Implementation: CSG Worker (`csg-worker.js`)

```javascript
function createConeFrustum(baseRadius, topRadius, height, segments = 16) {
    const geometry = new THREE.CylinderGeometry(topRadius, baseRadius, height, segments);
    return geometry;
}

// In createCylinderDot() for shape === 'standard':
const { base_radius, top_radius, height } = params;
geometry = createConeFrustum(baseRadius, topRadius, height, 16);
```

### Implementation: Manifold WASM (`csg-worker-manifold.js`)

```javascript
function createManifoldFrustum(baseRadius, topRadius, height, segments = 24) {
    // Manifold.cylinder creates along Z-axis, centered at origin
    // radiusLow is at -height/2, radiusHigh is at +height/2
    return Manifold.cylinder(height, baseRadius, topRadius, segments, true);
}

// Standard frustum for positive embossing:
dot = createManifoldFrustum(baseRadius, topRadius, height, 24);
```

### Default Parameter Values

| Parameter | Default Value | Source |
|-----------|--------------|--------|
| `emboss_dot_base_diameter` | 1.8mm | `app/models.py` |
| `emboss_dot_flat_hat` | 0.4mm | `app/models.py` |
| `emboss_dot_height` | 1.0mm | `app/models.py` |

### Geometry Specification Format (`geometry_spec.py`)

```python
{
    'type': 'standard',  # or 'cylinder_dot' for cylinders
    'x': x,
    'y': y,
    'z': z,
    'params': {
        'shape': 'standard',
        'base_radius': emboss_dot_base_diameter / 2,
        'top_radius': emboss_dot_flat_hat / 2,
        'height': emboss_dot_height,
    }
}
```

---

## 3. Embossing Plate: Rounded (Dome) Shape

### Description

The rounded shape creates a **cone frustum base with spherical cap dome** for a more tactile-friendly braille dot. The dome provides a smoother surface compared to the flat top of standard cones.

### Geometry Construction

```
Shape: Cone Frustum Base + Spherical Cap Dome
Profile: Tapered base with smooth dome top

Parameters:
- rounded_dot_base_diameter: Cone base diameter at surface (default: 2.0mm)
- rounded_dot_dome_diameter: Cone flat top / dome base diameter (default: 1.5mm)
- rounded_dot_base_height: Cone frustum height (default: 0.2mm)
- rounded_dot_dome_height: Dome height above cone flat top (default: 0.6mm)
```

### Visual Cross-Section

```
                     .-"""-.
                   .'       '.        ← Dome top (outermost point)
                  /           \
                 /             \      ↑ dome_height (0.4mm default)
                /               \     ↓ Distance from junction to dome top
               ┌─────────────────┐    ← Junction: dome_diameter / 2 (smaller)
              /                   \
             /                     \  ↑ base_height (0.4mm default)
            /                       \ ↓ Distance from surface to junction
           └─────────────────────────┘← Base at surface: base_diameter / 2 (larger)
    ════════════════════════════════════  ← CYLINDER SURFACE (radius = cylRadius)
```

**Geometry stacks upward from cylinder surface:**
1. **Base** (widest point) sits flush on cylinder surface
2. **Frustum** tapers inward as it rises `base_height` mm
3. **Junction** where frustum meets dome (narrower than base)
4. **Dome** rises `dome_height` mm from junction to rounded top

### Critical Formula: Dome Sphere Radius

The dome is a spherical cap. To achieve a dome of height `h` with a base radius `r`, the sphere radius `R` is calculated as:

```
R = (r² + h²) / (2h)

Where:
- r = rounded_dot_dome_diameter / 2 (dome base radius)
- h = rounded_dot_dome_height (dome height)
- R = calculated sphere radius for the cap
```

### Implementation: Python Backend (`app/geometry/dot_shapes.py`)

```python
if getattr(settings, 'use_rounded_dots', 0):
    base_diameter = float(getattr(settings, 'rounded_dot_base_diameter', 2.0))
    dome_diameter = float(getattr(settings, 'rounded_dot_dome_diameter', 1.5))
    base_radius = base_diameter / 2.0
    top_radius = dome_diameter / 2.0
    base_h = float(getattr(settings, 'rounded_dot_base_height', 0.2))
    dome_h = float(getattr(settings, 'rounded_dot_dome_height', 0.6))

    # Build cone frustum base
    if base_h > 0:
        frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h, sections=48)
        # Scale top vertices to create taper
        scale_factor = top_radius / base_radius if base_radius > 0 else 1.0
        top_z = frustum.vertices[:, 2].max()
        is_top = np.isclose(frustum.vertices[:, 2], top_z)
        frustum.vertices[is_top, :2] *= scale_factor
        parts.append(frustum)

    # Calculate sphere radius for dome
    R = (top_radius**2 + dome_h**2) / (2.0 * dome_h)
    zc = (base_h / 2.0) + (dome_h - R)  # Center position

    sphere = trimesh.creation.icosphere(radius=R, subdivisions=3)
    sphere.apply_translation([0.0, 0.0, zc])
    parts.append(sphere)

    # Combine and translate
    dot = trimesh.util.concatenate(parts)
    dot.apply_translation([0.0, 0.0, -dome_h / 2.0])
    dot.apply_translation((x, y, z))
```

### Implementation: CSG Worker (`csg-worker.js`)

```javascript
if (shape === 'rounded') {
    const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;

    // Create cone frustum base
    if (base_height > 0) {
        const frustum = createConeFrustum(base_radius, top_radius, base_height, 48);

        // Create spherical cap dome
        const dome_R = dome_radius;
        const dome_zc = (base_height / 2.0) + (dome_height - dome_R);
        const dome = createSphericalCap(dome_R, dome_height, 2);
        dome.translate(0, 0, dome_zc);

        // CSG union
        const frustumBrush = new Brush(frustum);
        const domeBrush = new Brush(dome);
        const combinedBrush = evaluator.evaluate(frustumBrush, domeBrush, ADDITION);
        geometry = combinedBrush.geometry;
    }
}
```

### Implementation: Manifold WASM (`csg-worker-manifold.js`)

```javascript
if (shape === 'rounded') {
    const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;
    dotHeight = base_height + dome_height;

    if (base_height > 0) {
        // Create frustum base
        const frustum = createManifoldFrustum(base_radius, top_radius, base_height, 24);
        const positionedFrustum = frustum.translate([0, 0, base_height / 2]);
        frustum.delete();

        // Create dome
        const dome = createSphericalCap(dome_radius, dome_height, 24);
        const positionedDome = dome.translate([0, 0, base_height]);
        dome.delete();

        // Union frustum and dome
        dot = positionedFrustum.add(positionedDome);
        positionedFrustum.delete();
        positionedDome.delete();
    }
}
```

### Default Parameter Values

| Parameter | Default Value | Source |
|-----------|--------------|--------|
| `rounded_dot_base_diameter` | 2.0mm | `app/models.py` |
| `rounded_dot_dome_diameter` | 1.5mm | `app/models.py` |
| `rounded_dot_base_height` | 0.2mm | `app/models.py` |
| `rounded_dot_dome_height` | 0.6mm | `app/models.py` |

### Geometry Specification Format (`geometry_spec.py`)

```python
{
    'type': 'rounded',  # or 'cylinder_dot' with shape='rounded' for cylinders
    'x': x,
    'y': y,
    'z': z,
    'params': {
        'shape': 'rounded',
        'base_radius': rounded_dot_base_diameter / 2,
        'top_radius': rounded_dot_dome_diameter / 2,
        'base_height': rounded_dot_base_height,
        'dome_height': rounded_dot_dome_height,
        'dome_radius': R,  # Calculated sphere radius
    }
}
```

### Dome Radius Calculation Verification

```
Given default values:
- dome_diameter = 1.5mm → r = 0.75mm
- dome_height = 0.6mm → h = 0.6mm

R = (0.75² + 0.6²) / (2 × 0.6)
R = (0.5625 + 0.36) / 1.2
R = 0.9225 / 1.2
R = 0.76875mm
```

---

## 4. Counter Plate: Hemisphere Recess Shape

### Description

The hemisphere recess creates a **perfect hemispherical indentation** in the counter plate surface. The hemisphere radius equals the specified counter dot diameter.

### Geometry Construction

```
Shape: Hemisphere (half-sphere)
Profile: Circular opening with perfect hemispherical depression

Parameters:
- hemi_counter_dot_base_diameter: Opening diameter at surface (default: 1.6mm)
```

### Visual Cross-Section

```
────────────────────  ← Plate surface
    ╲            ╱    ← Opening (hemi_counter_dot_base_diameter)
      ╲        ╱
        ╲    ╱
          ╲╱          ← Bottom (hemisphere radius below surface)
```

### Critical Implementation Detail

For boolean subtraction reliability, a **full sphere** is created and positioned so its equator coincides with the plate surface. The portion above the surface is implicitly discarded during subtraction.

```
Sphere positioning:
- Center Z = plate_thickness (for cards)
- Center Z = cylinder_radius (for cylinders)
- Only the lower hemisphere actually subtracts material
```

### Implementation: Python Backend (`backend.py`)

```python
def build_counter_plate_hemispheres(params: CardSettings) -> trimesh.Trimesh:
    # Calculate hemisphere radius
    counter_base = float(getattr(params, 'hemi_counter_dot_base_diameter', 1.6))
    hemisphere_radius = counter_base / 2

    # Create icosphere at each dot position
    sphere = trimesh.creation.icosphere(
        subdivisions=params.hemisphere_subdivisions,
        radius=hemisphere_radius
    )
    # Position sphere equator at top surface
    z_pos = params.plate_thickness
    sphere.apply_translation((dot_x, dot_y, z_pos))
```

### Implementation: CSG Worker (`csg-worker.js`)

```javascript
if (shape === 'hemisphere') {
    const { recess_radius } = params;
    const validRecessRadius = (recess_radius > 0) ? recess_radius : 1.0;
    dotHeight = validRecessRadius;
    // Use full sphere for better subtraction overlap
    geometry = new THREE.SphereGeometry(validRecessRadius, 16, 16);
}
```

### Implementation: Manifold WASM (`csg-worker-manifold.js`)

```javascript
if (shape === 'hemisphere') {
    const recessRadius = (params.recess_radius > 0) ? params.recess_radius : 1.0;
    dotHeight = recessRadius;
    // Full sphere for better subtraction
    dot = createManifoldSphere(recessRadius, 24);
}
```

### Default Parameter Values

| Parameter | Default Value | Source |
|-----------|--------------|--------|
| `hemi_counter_dot_base_diameter` | 1.6mm | `app/models.py` |
| `recess_shape` | 0 | When hemisphere selected |

### Geometry Specification Format (`geometry_spec.py`)

```python
{
    'type': 'cylinder_dot',
    'x': x,
    'y': y,
    'z': z,
    'theta': theta,
    'radius': cylinder_radius,
    'is_recess': True,
    'params': {
        'shape': 'hemisphere',
        'recess_radius': hemi_counter_dot_base_diameter / 2,
    }
}
```

### Radial Positioning on Cylinders

For hemispheres on cylinders, the sphere is centered exactly at the cylinder surface:

```javascript
// Hemisphere radial offset
radialOffset = cylRadius;  // Center at surface
```

---

## 5. Counter Plate: Bowl (Spherical Cap) Recess Shape

### Description

The bowl recess creates a **spherical cap with independently controlled depth**. Unlike the hemisphere, the bowl allows specifying both the opening diameter AND the recess depth independently.

### Geometry Construction

```
Shape: Spherical Cap (bowl)
Profile: Circular opening with controlled-depth spherical depression

Parameters:
- bowl_counter_dot_base_diameter: Opening diameter at surface (default: 1.8mm)
- counter_dot_depth: Recess depth (default: 0.8mm)
```

### Visual Cross-Section

```
─────────────────────  ← Plate surface
    ╲              ╱   ← Opening (bowl_counter_dot_base_diameter)
      ╲          ╱
        ╲──────╱       ← Spherical arc
              │
              └── counter_dot_depth
```

### Critical Formula: Bowl Sphere Radius

To create a bowl with opening radius `a` and depth `h`, the sphere radius `R` is:

```
R = (a² + h²) / (2h)

Where:
- a = bowl_counter_dot_base_diameter / 2 (opening radius)
- h = counter_dot_depth (bowl depth)
- R = calculated sphere radius
```

### Implementation: Python Backend (`backend.py`)

```python
def build_counter_plate_bowl(params: CardSettings) -> trimesh.Trimesh:
    # Get bowl parameters
    a = float(getattr(params, 'bowl_counter_dot_base_diameter', 1.6)) / 2.0
    h = float(getattr(params, 'counter_dot_depth', 0.6))

    # Calculate sphere radius
    R = (a * a + h * h) / (2.0 * h)

    # Create sphere and position
    sphere = trimesh.creation.icosphere(
        subdivisions=params.hemisphere_subdivisions,
        radius=R
    )
    # Place center below surface: z = plate_thickness - (R - h)
    zc = params.plate_thickness - (R - h)
    sphere.apply_translation((dot_x, dot_y, zc))
```

### Implementation: CSG Worker (`csg-worker.js`)

```javascript
if (shape === 'bowl') {
    const { bowl_radius, bowl_depth } = params;
    const validBowlRadius = (bowl_radius > 0) ? bowl_radius : 1.5;
    const validBowlDepth = (bowl_depth > 0) ? bowl_depth : 0.8;
    dotHeight = validBowlDepth;

    // Calculate sphere radius
    const sphereR = (validBowlRadius**2 + validBowlDepth**2) / (2.0 * validBowlDepth);

    // Use full sphere for better subtraction
    geometry = new THREE.SphereGeometry(sphereR, 16, 16);
}
```

### Implementation: Manifold WASM (`csg-worker-manifold.js`)

```javascript
if (shape === 'bowl') {
    const bowlRadius = (params.bowl_radius > 0) ? params.bowl_radius : 1.5;
    const bowlDepth = (params.bowl_depth > 0) ? params.bowl_depth : 0.8;
    dotHeight = bowlDepth;

    // Calculate sphere radius for bowl
    const sphereR = (bowlRadius**2 + bowlDepth**2) / (2.0 * bowlDepth);
    dot = createManifoldSphere(sphereR, 24);
}
```

### Default Parameter Values

| Parameter | Default Value | Source |
|-----------|--------------|--------|
| `bowl_counter_dot_base_diameter` | 1.8mm | `app/models.py` |
| `counter_dot_depth` | 0.8mm | `app/models.py` |
| `recess_shape` | 1 | Default counter plate shape |

### Geometry Specification Format (`geometry_spec.py`)

```python
{
    'type': 'cylinder_dot',
    'x': x,
    'y': y,
    'z': z,
    'theta': theta,
    'radius': cylinder_radius,
    'is_recess': True,
    'params': {
        'shape': 'bowl',
        'bowl_radius': bowl_counter_dot_base_diameter / 2,
        'bowl_depth': counter_dot_depth,
    }
}
```

### Radial Positioning on Cylinders

For bowl recesses on cylinders, the sphere is centered at the cylinder surface (same as hemisphere):

```javascript
// Bowl radial offset
radialOffset = cylRadius;  // Center at surface
```

### Bowl Sphere Radius Verification

```
Given default values:
- bowl_base_diameter = 1.8mm → a = 0.9mm
- counter_dot_depth = 0.8mm → h = 0.8mm

R = (0.9² + 0.8²) / (2 × 0.8)
R = (0.81 + 0.64) / 1.6
R = 1.45 / 1.6
R = 0.90625mm
```

---

## 6. Counter Plate: Cone Recess Shape

### Description

The cone recess creates an **inverted truncated cone frustum** in the counter plate. The large opening is at the surface, and the smaller flat tip points inward.

### Geometry Construction

```
Shape: Inverted Cone Frustum
Profile: Large circular opening tapering to smaller flat bottom

Parameters:
- cone_counter_dot_base_diameter: Opening diameter at surface (default: 1.6mm)
- cone_counter_dot_flat_hat: Flat tip diameter at bottom (default: 0.4mm)
- cone_counter_dot_height: Recess depth (default: 0.8mm)
```

### Visual Cross-Section

```
─────────────────────  ← Plate surface
    ╲              ╱   ← Opening (cone_counter_dot_base_diameter)
      ╲          ╱
        ╲      ╱
          ╲  ╱
           ││          ← Flat tip (cone_counter_dot_flat_hat)
           └── cone_counter_dot_height
```

### CRITICAL: Cone Orientation Swap

For cone recesses, the base and top radii must be **swapped** compared to protrusions:
- **Large opening** (base_radius) at the surface
- **Small tip** (top_radius) pointing into the material

```javascript
// For recesses, create frustum with radii swapped:
// Small radius at bottom, large radius at top (surface)
geometry = createConeFrustum(topRadius, baseRadius, height, 16);  // Swapped!
```

### Implementation: Python Backend (`backend.py`)

```python
def build_counter_plate_cone(params: CardSettings) -> trimesh.Trimesh:
    base_d = float(getattr(params, 'cone_counter_dot_base_diameter', 1.6))
    hat_d = float(getattr(params, 'cone_counter_dot_flat_hat', 0.4))
    height_h = float(getattr(params, 'cone_counter_dot_height', 0.8))

    base_r = base_d / 2.0
    hat_r = hat_d / 2.0

    # Create cone frustum geometry
    # Top ring (at z=0, which becomes plate surface) has LARGE radius
    # Bottom ring (at z=-height, inside plate) has SMALL radius
    top_ring = np.column_stack([base_r * cos_angles, base_r * sin_angles, np.zeros_like(angles)])
    bot_ring = np.column_stack([hat_r * cos_angles, hat_r * sin_angles, -height_h * np.ones_like(angles)])

    frustum = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    # Position with top cap slightly above surface for robust boolean
    frustum.apply_translation((dot_x, dot_y, params.plate_thickness + overcut_z))
```

### Implementation: CSG Worker (`csg-worker.js`)

```javascript
if (shape === 'cone') {
    const { base_radius, top_radius, height } = params;

    // IMPORTANT: Swap base and top radii for recesses
    // createConeFrustum puts second param at +Y, which becomes radial outward after rotations
    geometry = createConeFrustum(top_radius, base_radius, height, 16);  // Swapped!
}
```

### Implementation: Manifold WASM (`csg-worker-manifold.js`)

```javascript
if (shape === 'cone') {
    const { base_radius, top_radius, height } = params;
    dotHeight = height;

    // Swap radii for recess: large at top (surface), small at bottom (inside)
    dot = createManifoldFrustum(top_radius, base_radius, height, 24);  // Swapped!
}
```

### Default Parameter Values

| Parameter | Default Value | Source |
|-----------|--------------|--------|
| `cone_counter_dot_base_diameter` | 1.6mm | `app/models.py` |
| `cone_counter_dot_flat_hat` | 0.4mm | `app/models.py` |
| `cone_counter_dot_height` | 0.8mm | `app/models.py` |
| `recess_shape` | 2 | When cone selected |

### Geometry Specification Format (`geometry_spec.py`)

```python
{
    'type': 'cylinder_dot',
    'x': x,
    'y': y,
    'z': z,
    'theta': theta,
    'radius': cylinder_radius,
    'is_recess': True,
    'params': {
        'shape': 'cone',
        'base_radius': cone_counter_dot_base_diameter / 2,  # Large opening
        'top_radius': cone_counter_dot_flat_hat / 2,        # Small tip
        'height': cone_counter_dot_height,
    }
}
```

### Radial Positioning on Cylinders

For cone recesses on cylinders, special positioning is required to place the large opening at the surface:

```javascript
// Cone radial offset - position so base lands at surface
if (shape === 'cone') {
    radialOffset = cylRadius - dotHeight / 2;
}
```

---

## 7. Cylinder-Specific Positioning Rules

### Radial Offset Calculations

| Shape Type | Plate Type | Radial Offset Formula |
|------------|------------|----------------------|
| Standard/Rounded | Embossing | `cylRadius + dotHeight/2` |
| Hemisphere | Counter | `cylRadius` |
| Bowl | Counter | `cylRadius` |
| Cone | Counter | `cylRadius - dotHeight/2` |

### Orientation Rotations

All non-spherical shapes must be rotated to point radially outward on the cylinder surface.

**Three.js (Y-up coordinate system):**
```javascript
// For cone frustums:
geometry.rotateZ(-Math.PI / 2);  // Align with +X
geometry.rotateY(-theta);         // Point toward radial direction
```

**Manifold (Z-up coordinate system):**
```javascript
// CRITICAL: Negate theta to match Three.js convention
const adjustedTheta = -theta;

// Rotate to point radially:
dot.rotate(0, 90, 0);           // Z -> X
dot.rotate(0, 0, thetaDeg);     // Rotate to angle
```

### Position Calculation

```javascript
// Final 3D position on cylinder surface
const posX = radialOffset * Math.cos(theta);  // Or adjustedTheta for Manifold
const posY = y_local;                          // Height along cylinder axis
const posZ = radialOffset * Math.sin(theta);  // Or adjustedTheta for Manifold
```

---

## 8. API Parameter Mapping

### Shape Selection Parameter Flow

**Embossing Plate Dot Shape:**
```
UI: dot_shape = 'cone' | 'rounded'
    ↓
API: use_rounded_dots = 0 (cone) | 1 (rounded)
    ↓
Backend: settings.use_rounded_dots
    ↓
CSG Worker: spec.params.shape = 'standard' | 'rounded'
```

**Counter Plate Recess Shape:**
```
UI: recess_shape = 0 | 1 | 2
    ↓
API: recess_shape = 0 (hemisphere) | 1 (bowl) | 2 (cone)
    ↓
Backend: settings.recess_shape
    ↓
CSG Worker: spec.params.shape = 'hemisphere' | 'bowl' | 'cone'
```

### Models.py Parameter Processing

```python
# Map dot_shape to use_rounded_dots
try:
    dot_shape = kwargs.get('dot_shape', 'rounded')
    if dot_shape == 'rounded':
        self.use_rounded_dots = 1
    elif dot_shape == 'cone':
        self.use_rounded_dots = 0
except Exception:
    pass  # Keep existing use_rounded_dots value

# Normalize recess_shape (0=hemi, 1=bowl, 2=cone)
try:
    self.recess_shape = int(float(kwargs.get('recess_shape', 1)))
except Exception:
    self.recess_shape = 1
```

---

## 9. Parameter Default Summary Table

### Embossing Plate Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_rounded_dots` | 0 | Shape selector (0=cone, 1=rounded) |
| `emboss_dot_base_diameter` | 1.8mm | Cone base diameter |
| `emboss_dot_flat_hat` | 0.4mm | Cone top diameter |
| `emboss_dot_height` | 1.0mm | Cone height |
| `rounded_dot_base_diameter` | 2.0mm | Rounded base diameter |
| `rounded_dot_dome_diameter` | 1.5mm | Dome base diameter |
| `rounded_dot_base_height` | 0.2mm | Frustum base height |
| `rounded_dot_dome_height` | 0.6mm | Dome height |

### Counter Plate Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `recess_shape` | 1 | Shape selector (0=hemi, 1=bowl, 2=cone) |
| `hemi_counter_dot_base_diameter` | 1.6mm | Hemisphere diameter |
| `bowl_counter_dot_base_diameter` | 1.8mm | Bowl opening diameter |
| `counter_dot_depth` | 0.8mm | Bowl/general depth |
| `cone_counter_dot_base_diameter` | 1.6mm | Cone opening diameter |
| `cone_counter_dot_flat_hat` | 0.4mm | Cone tip diameter |
| `cone_counter_dot_height` | 0.8mm | Cone depth |

---

## 10. Validation Checklist

### Embossing Plate Cone (Standard) Shape
- [ ] `emboss_dot_base_diameter` correctly sets base width
- [ ] `emboss_dot_flat_hat` correctly sets flat top width
- [ ] `emboss_dot_height` correctly sets total height
- [ ] Frustum tapers from base to top (not inverted)
- [ ] Dot positioned with base at plate surface

### Embossing Plate Rounded Shape
- [ ] `rounded_dot_base_diameter` sets cone base width
- [ ] `rounded_dot_dome_diameter` sets junction diameter
- [ ] `rounded_dot_base_height` sets cone height
- [ ] `rounded_dot_dome_height` sets dome height
- [ ] Dome sphere radius calculated correctly: `R = (r² + h²) / (2h)`
- [ ] Dome smoothly joins cone at junction diameter

### Counter Plate Hemisphere
- [ ] `hemi_counter_dot_base_diameter` sets opening diameter
- [ ] Full sphere positioned with equator at surface
- [ ] Recess depth equals radius

### Counter Plate Bowl
- [ ] `bowl_counter_dot_base_diameter` sets opening diameter
- [ ] `counter_dot_depth` independently controls depth
- [ ] Sphere radius calculated correctly: `R = (a² + h²) / (2h)`
- [ ] Opening matches specified diameter

### Counter Plate Cone
- [ ] `cone_counter_dot_base_diameter` sets large opening
- [ ] `cone_counter_dot_flat_hat` sets small tip
- [ ] `cone_counter_dot_height` sets depth
- [ ] **Radii swapped** for correct orientation (large at surface)
- [ ] Cone points inward (not outward)

### Cylinder Positioning
- [ ] Standard/Rounded dots: `radialOffset = cylRadius + dotHeight/2`
- [ ] Hemisphere/Bowl: `radialOffset = cylRadius`
- [ ] Cone: `radialOffset = cylRadius - dotHeight/2`
- [ ] Non-spherical shapes rotated to point radially
- [ ] Manifold uses `adjustedTheta = -theta`

---

## 11. Common Bugs and Solutions

### Bug 1: Cone Recess Points Outward Instead of Inward

**Symptom:** Cone recess has small opening at surface, large tip inside
**Cause:** Base and top radii not swapped for recess
**Solution:** Swap radii in frustum creation:
```javascript
// WRONG: Same as protrusion
geometry = createConeFrustum(baseRadius, topRadius, height);

// CORRECT: Swapped for recess
geometry = createConeFrustum(topRadius, baseRadius, height);
```

### Bug 2: Bowl Opening Diameter Doesn't Match Parameter

**Symptom:** Bowl opening is smaller or larger than expected
**Cause:** Sphere radius calculated incorrectly
**Solution:** Verify formula: `R = (a² + h²) / (2h)` where `a` is opening radius

### Bug 3: Dots Float Above/Sink Below Cylinder Surface

**Symptom:** Dots not properly tangent to cylinder
**Cause:** Incorrect radial offset for shape type
**Solution:** Use shape-specific radial offset formulas

### Bug 4: Hemisphere Depth Doesn't Match Diameter

**Symptom:** Hemisphere appears too shallow or too deep
**Note:** This is **expected behavior** - hemisphere depth equals radius
**If adjustable depth needed:** Use bowl shape instead

### Bug 5: Rounded Dot Has Sharp Edge at Junction

**Symptom:** Visible seam between cone base and dome
**Cause:** Dome base radius doesn't match cone top radius
**Solution:** Ensure `rounded_dot_dome_diameter` equals the cone top diameter

### Bug 6: Card Cone Recess Has Inverted Orientation (KNOWN ISSUE)

**Symptom:** Card counter plate cone recesses have small opening at surface, large void inside (inverted)
**Cause:** `geometry_spec.py` creates `type: 'standard'` specs for card cone recesses without marking them as recesses. The CSG workers (`csg-worker.js` and `csg-worker-manifold.js`) then create the frustum directly without swapping radii.

**Affected Code Paths:**
- `geometry_spec.py` → `_create_dot_spec()` with `shape_type='cone'` → returns `type: 'standard'`
- `csg-worker.js` → `createBrailleDot()` → creates frustum without radii swap
- `csg-worker-manifold.js` → card dot creation → creates frustum without radii swap

**Comparison with Working Implementations:**
- **Cylinder cone recesses**: Correctly handled in `createCylinderDot()` with radii swap
- **Python backend**: `build_counter_plate_cone()` correctly builds inverted frustum geometry

**Impact Assessment:** LOW
- Card counter plates with cone recesses are rarely used (most use hemisphere or bowl)
- Cylinder cone recesses work correctly
- (Note: Server-side generation was removed in v2.0.0; all generation is now client-side)

**Potential Fix:**
Either:
1. Add `is_recess: True` flag to card cone dot specs in `geometry_spec.py`
2. Modify CSG workers to swap radii for `type: 'standard'` when plate_type is 'negative'
3. Use a different `type` value (e.g., `'cone_recess'`) to distinguish from protrusions

### Bug 7: Cylinder Rounded Dot Positioning Inconsistency (FIXED & VERIFIED - Dec 2024)

**Symptom:** Rounded braille dots on cylinders appear to float away from the cylinder surface when the cylinder diameter is adjusted. The dots do not properly follow the radial line and maintain tangency with the cylinder surface.

**Root Cause:** Inconsistent centering behavior between Python backend (`app/geometry/dot_shapes.py`) and CSG worker (`static/workers/csg-worker.js`).

**Technical Details:**
- **Python Backend** (`dot_shapes.py` lines 65-68): After creating the combined frustum+dome geometry, centers the dot by translating by `[0.0, 0.0, -dome_h / 2.0]`
- **CSG Worker** (original code): Used `recenterGeometryAlongY()` which computed the bounding box of the combined geometry and centered based on that, potentially producing a different offset
- **Issue**: The CSG worker's bounding box-based centering could produce a slightly different center point than the Python backend's explicit `-dome_h / 2.0` translation, especially when the CSG union operation between frustum and dome affected the geometry bounds

**Affected Code Path:**
- `static/workers/csg-worker.js` → `createCylinderDot()` → `shape === 'rounded'` branch → geometry centering

**Fix Applied (December 2024):**
Modified `csg-worker.js` line 284-285 to use explicit height calculation and centering that matches the Python backend:

```javascript
// OLD (buggy):
const roundedHeight = recenterGeometryAlongY(geometry);
dotHeight = roundedHeight > 0 ? roundedHeight : (validBaseHeight + validDomeHeight);

// NEW (fixed):
dotHeight = validBaseHeight + validDomeHeight;
geometry.translate(0, -validDomeHeight / 2, 0);
```

**Impact:** HIGH - Affects all client-side generated cylinder embossing plates with rounded dots

**Resolution Status:** FIXED
- Client-side CSG worker now uses identical centering logic to Python backend
- Dots now properly maintain contact with cylinder surface across all diameter values
- Coordinate system consistency ensures dots follow radial lines correctly

**Note (December 2024):** This bug existed in TWO separate worker files:
1. `static/workers/csg-worker.js` - Three.js/three-bvh-csg worker (used for cards)
2. `static/workers/csg-worker-manifold.js` - Manifold3D worker (used for cylinders)

Both required the same fix: after creating the combined frustum+dome geometry, translate by `-dotHeight/2` along the dot's axis to center it at the origin. This ensures that when positioned at `radialOffset = cylRadius + dotHeight/2`, the inner edge lands exactly at `cylRadius` (flush with the cylinder surface).

**Centering Logic Explanation (December 2024 Clarification):**

The rounded dot geometry (frustum + dome) is constructed as follows:
1. **Frustum**: Created centered at origin, spans Y from `-base_h/2` to `+base_h/2`
2. **Dome (spherical cap)**: Positioned so its base is at `Y = base_h/2` (top of frustum)
3. **Combined geometry**: Spans from `Y = -base_h/2` (frustum bottom) to `Y = base_h/2 + dome_h` (dome top)

The geometric center of this combined shape is at:
```
center_Y = (-base_h/2 + base_h/2 + dome_h) / 2 = dome_h / 2
```

To center the geometry at Y=0, we translate by `-dome_h/2`:
```
After translation:
  - Bottom: -base_h/2 - dome_h/2
  - Top: base_h/2 + dome_h - dome_h/2 = base_h/2 + dome_h/2
  - New center: 0
  - Total height: base_h + dome_h = dotHeight
```

The centered geometry now spans `[-dotHeight/2, +dotHeight/2]` along the Y-axis.

**Radial Positioning Formula:**

After rotation to orient radially, the dot is translated to:
```javascript
radialOffset = cylRadius + dotHeight / 2;
posX = radialOffset * cos(theta);
posZ = radialOffset * sin(theta);
```

This places:
- **Inner edge (frustum base)** at: `radialOffset - dotHeight/2 = cylRadius` (flush with surface)
- **Outer edge (dome top)** at: `radialOffset + dotHeight/2 = cylRadius + dotHeight`

**Validation:**
To validate the fix:
1. Generate a cylinder with rounded dots using client-side CSG
2. Adjust cylinder diameter from 30.75mm to various values (20mm, 40mm, 60mm, etc.)
3. Verify dots remain flush with cylinder outer surface at all diameters
4. Compare client-side generated STL with server-side generated STL for consistency
5. Check browser console for debug logs showing `cylRadius`, `dotHeight`, and `radialOffset` values

**Debug Logging (Added December 2024):**

The CSG worker now includes debug logging for rounded dots:
```javascript
console.log(`CSG Worker: Rounded dot positioning: cylRadius=${cylRadius}, dotHeight=${dotHeight}, radialOffset=${radialOffset}`);
console.log(`CSG Worker: Expected dot base at radius ${radialOffset - dotHeight/2}, top at ${radialOffset + dotHeight/2}`);
```

Use these logs to verify that:
- `cylRadius` matches the cylinder shell radius
- `dotHeight = base_height + dome_height`
- `radialOffset = cylRadius + dotHeight/2`
- The expected dot base equals `cylRadius` (should be flush with surface)

---

## 12. Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-06 | 1.0 | Initial specification document |
| 2024-12-06 | 1.1 | Added Bug 6: Card cone recess inverted orientation (discovered during cross-check) |
| 2024-12-07 | 1.2 | Extended Bug 7 documentation with detailed centering logic and debug logging information |
| 2024-12-07 | 1.3 | Fixed Bug 7 in csg-worker-manifold.js (Manifold CSG worker for cylinders) - added centering translation |
| 2024-12-07 | 1.4 | Bug 7 fix VERIFIED by user testing - rounded dots now correctly positioned flush with cylinder surface |

---

## 13. Related Documentation

- `BRAILLE_SPACING_SPECIFICATIONS.md` - Braille cell and row layout specifications
- `RECESS_INDICATOR_SPECIFICATIONS.md` - Triangle, rectangle, character marker specifications
- `CLIENT_SIDE_CSG_DOCUMENTATION.md` - Overall CSG architecture
- `geometry_spec.py` - Authoritative geometry specification extraction
- `app/models.py` - Parameter defaults and validation
