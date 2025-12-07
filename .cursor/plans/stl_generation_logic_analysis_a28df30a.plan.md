---
name: STL Generation Logic Analysis
overview: A comprehensive analysis of all STL generation logic branches, fallback mechanisms, and their functioning status in the Braille Card and Cylinder STL Generator.
todos: []
---

# STL Generation Logic Architecture Analysis

## Executive Summary

This document analyzes all implemented logic branches and fallback mechanisms for generating STL files in the Braille Card and Cylinder STL Generator application. The system uses a **client-first architecture** with server-side fallbacks.

---

## 1. High-Level Generation Strategy

### Primary Decision Tree

```
User Request → Shape Type? → Plate Type? → Generation Path
                   │              │
                   ├─ Card        ├─ Positive (emboss)  → Client-side CSG (primary)
                   │              │                      → Server-side (fallback)
                   │              └─ Negative (counter) → Server-side (cached)
                   │
                   └─ Cylinder    ├─ Positive (emboss)  → Client-side CSG (primary)
                                  │                      → Server-side (fallback)
                                  └─ Negative (counter) → Server-side (cached)
```

### Strategy Matrix (from `templates/index.html`)

| Plate Type | Client CSG Flag | Worker Ready | Generation Path |

|------------|-----------------|--------------|-----------------|

| Positive   | true            | true         | Client-side CSG |

| Positive   | true            | false        | Server fallback |

| Positive   | false           | any          | Server direct   |

| Negative   | any             | any          | Server (cached) |

---

## 2. Client-Side Generation Path

### Status: FUNCTIONAL

**Files:** `static/workers/csg-worker.js`, `app/geometry_spec.py`

### Architecture

1. Frontend requests geometry specification from `/geometry_spec` endpoint
2. Server extracts dot/marker positions WITHOUT performing boolean operations
3. JSON spec sent to Web Worker
4. Worker performs CSG using `three-bvh-csg` library
5. Optional Manifold3D WASM repair for non-manifold edges
6. Binary STL exported and returned

### Reasoning

- **Offloads computation** from server to client browser
- **Reduces server costs** on Vercel serverless (no expensive boolean ops)
- **Eliminates dependency** on server-side boolean backends (manifold3d, blender, openscad)
- **Better UX** with progress feedback and local processing

### Key Functions

- `extract_card_geometry_spec()` - Card specification extraction
- `extract_cylinder_geometry_spec()` - Cylinder specification extraction
- `processGeometrySpec()` (JS) - Client-side CSG orchestration
- `repairGeometryWithManifold()` (JS) - Optional mesh repair

### Dot Types Handled

| Type | Plate | Shape | Implementation |

|------|-------|-------|----------------|

| `standard` | Positive | Cone frustum | `createConeFrustum()` |

| `rounded` | Positive | Cone + spherical cap | CSG union of frustum + dome |

| `hemisphere` | Negative | Full sphere | `SphereGeometry` (positioned for half-cut) |

| `bowl` | Negative | Spherical cap | Computed sphere radius for depth |

| `cone` | Negative | Cone frustum (inverted) | Swapped radii for recess |

### Marker Types Handled

- `triangle` / `cylinder_triangle` - Row end indicators
- `rect` / `cylinder_rect` - Rectangular placeholders
- `character` / `cylinder_character` - Alphanumeric indicators (font-based or fallback box)

---

## 3. Server-Side Generation Path

### Status: FUNCTIONAL (with environment dependencies)

**Files:** `backend.py`, `app/geometry/cylinder.py`, `app/geometry/booleans.py`

### Environment Detection

```python
def has_boolean_backend() -> bool:
    # Returns True if manifold3d is importable
    # Trimesh default requires blender/openscad (not on serverless)
    return _check_manifold_available()
```

### Boolean Engine Fallback Chain (`app/geometry/booleans.py`)

| Priority | Engine | Availability | Notes |

|----------|--------|--------------|-------|

| 1 | `manifold` | When manifold3d installed | Preferred, pure Python wheel |

| 2 | `trimesh-default` | With blender/openscad | Not available on serverless |

| 3 | Pairwise fallback | Always | Individual binary operations |

| 4 | Concatenate | Always | Non-boolean last resort |

### Card Positive Plate Generation (`create_positive_plate_mesh`)

**Status:** FUNCTIONAL

1. Create base box (card dimensions)
2. For each braille character, create raised dots
3. Add row indicators (character shapes or rectangles)
4. Add triangle markers at row ends
5. Marker recesses created via 2D Shapely operations (serverless-compatible)

### Card Negative Plate Generation

**Multiple implementations with different approaches:**

#### 3a. `create_simple_negative_plate()`

**Status:** LEGACY - superseded

- Creates holes only for actual text content positions
- Falls back to `create_universal_counter_plate_fallback()` if no holes created

#### 3b. `create_universal_counter_plate_fallback()`

**Status:** LEGACY - 2D flat-bottom holes

- Creates circular holes at ALL dot positions
- Uses 2D Shapely boolean then extrusion
- Produces flat-bottomed recesses (not ideal for finger feel)

#### 3c. `create_universal_counter_plate_2d()`

**Status:** FUNCTIONAL - serverless-compatible

- Layered extrusion approach (no 3D booleans)
- Bottom layer: solid slab
- Top layer: slab with holes
- Includes indicator shapes (rectangles + triangles)

#### 3d. `build_counter_plate_hemispheres()`

**Status:** FUNCTIONAL - requires manifold3d

- True hemispherical recesses using icospheres
- Hemisphere radius = counter_dot_base_diameter / 2
- Sphere center positioned at z = TH - r + ε
- Subtracts all spheres in batch operation

#### 3e. `build_counter_plate_bowl()`

**Status:** FUNCTIONAL - requires manifold3d

- Spherical cap (bowl) recesses with independent depth control
- Computes sphere radius R from opening radius a and depth h: R = (a² + h²) / (2h)
- Falls back to hemispheres if depth ≤ 0

#### 3f. `build_counter_plate_cone()`

**Status:** FUNCTIONAL - requires manifold3d

- Conical frustum recesses
- Parameters: base diameter, flat hat diameter, height
- Optimized with configurable segments (8-32)

### Cylinder Positive Plate (`generate_cylinder_stl`)

**Status:** FUNCTIONAL

1. Create cylinder shell (optional N-gon polygon cutout)
2. Map braille cells to cylindrical coordinates
3. Create dots with radial orientation on outer surface
4. Add triangle markers at column 0
5. Add character indicators at column 1
6. Union dots, subtract markers

### Cylinder Negative Plate (`generate_cylinder_counter_plate`)

**Status:** FUNCTIONAL (requires manifold3d for best results)

1. Create cylinder shell with mirrored polygon cutout
2. Create recesses at ALL dot positions (mirrored angular direction)
3. Recess shape selection: hemisphere, bowl, or cone
4. Subtract all recesses and markers

---

## 4. Fallback Mechanisms

### 4.1 Client → Server Fallback

**Triggers:**

- Worker initialization fails (browser compatibility)
- `/geometry_spec` endpoint fails
- CSG worker throws error
- Worker timeout (2 minutes)
- Counter plate requested (for caching benefits)

**Implementation:**

```javascript
if (useClientSideCSG && workerReady) {
    try { return await generateClientSide(); }
    catch { return await generateServerSide(); }
}
return await generateServerSide();
```

### 4.2 Boolean Engine Fallback

**Location:** `app/geometry/booleans.py`

```
mesh_union/mesh_difference:
  1. Try preferred engine
  2. Try manifold (if available)
  3. Try trimesh default
  4. Pairwise binary tree fallback
  5. Concatenate (non-boolean, last resort)
```

### 4.3 Counter Plate Generation Fallback

**Location:** `backend.py` lines 2199-2224

```
if plate_type == 'negative':
    if recess_shape == 1:  → build_counter_plate_bowl()
    elif recess_shape == 0: → build_counter_plate_hemispheres()
    elif recess_shape == 2: → build_counter_plate_cone()
    else:                   → build_counter_plate_bowl() (default)
```

If any 3D boolean approach fails:

- Surface 500 error to indicate deployment/runtime issue
- No silent fallback to 2D (would mask problems)

### 4.4 Cylinder Shell Fallback

**Location:** `app/geometry/cylinder.py` `create_cylinder_shell()`

```
if 2D extrusion fails:
    return solid cylinder (no cutout)
```

### 4.5 Character Shape Fallback

When font loading or TextPath fails:

- Card: Falls back to `create_card_line_end_marker_3d()` (rectangle)
- Cylinder: Falls back to `create_cylinder_line_end_marker()` (rectangle)
- Client: Falls back to `BoxGeometry` approximation

### 4.6 Blob Cache Fallback

**Location:** `backend.py` `/generate_braille_stl` endpoint

1. Check Redis URL cache mapping first
2. Check Vercel Blob public URL exists
3. If cache hit → 302 redirect to blob URL
4. If cache miss → Generate, upload to blob, return/redirect

---

## 5. Recess Shape Options (Counter Plates)

| recess_shape | Name | Implementation | Best For |

|--------------|------|----------------|----------|

| 0 | Hemisphere | Full sphere subtraction | Maximum finger feel |

| 1 | Bowl | Spherical cap (adjustable depth) | Balanced (default) |

| 2 | Cone | Frustum subtraction | Sharp tactile definition |

---

## 6. Environment-Specific Behavior

### Local Development

- Full Flask server with hot reload
- All boolean backends available if installed
- manifold3d provides best results

### Vercel Serverless

- No blender/openscad available
- manifold3d may not be available (glibc compatibility)
- Client-side CSG is preferred path
- 2D operations for fallback

### Boolean Backend Detection

```python
def has_boolean_backend():
    if os.environ.get('FORCE_CLIENT_CSG'): return False
    return _check_manifold_available()
```

---

## 7. Complete Status Summary Table

| Method | Location | Status | Environment | Reasoning |

|--------|----------|--------|-------------|-----------|

| **CLIENT-SIDE CSG** | `csg-worker.js` | **FUNCTIONAL** | All browsers (Chrome 80+, FF 114+) | Offload computation, reduce server costs, no backend dependencies |

| **Manifold WASM Repair** | `csg-worker.js` | **OPTIONAL** | CDN-dependent | Fix non-manifold edges from CSG operations |

| **Card Positive Plate** | `create_positive_plate_mesh()` | **FUNCTIONAL** | All | Primary emboss plate generation |

| **Card Counter - 2D Holes** | `create_simple_negative_plate()` | **LEGACY** | Serverless | Basic flat-bottomed holes, superseded |

| **Card Counter - Universal 2D** | `create_universal_counter_plate_2d()` | **FUNCTIONAL** | Serverless | Layered extrusion, no 3D booleans needed |

| **Card Counter - Hemisphere** | `build_counter_plate_hemispheres()` | **FUNCTIONAL** | Local + manifold3d | True spherical recesses for best finger feel |

| **Card Counter - Bowl** | `build_counter_plate_bowl()` | **FUNCTIONAL** | Local + manifold3d | Adjustable depth spherical caps (DEFAULT) |

| **Card Counter - Cone** | `build_counter_plate_cone()` | **FUNCTIONAL** | Local + manifold3d | Sharp tactile definition |

| **Cylinder Positive** | `generate_cylinder_stl()` | **FUNCTIONAL** | Local + manifold3d | Cylindrical braille surfaces |

| **Cylinder Counter** | `generate_cylinder_counter_plate()` | **FUNCTIONAL** | Local + manifold3d | Mirrored recesses for cylinder |

| **Boolean Fallback Chain** | `mesh_union/difference()` | **FUNCTIONAL** | All | Graceful degradation through engine options |

| **Blob Cache** | `/lookup_stl`, `/generate_braille_stl` | **FUNCTIONAL** | Vercel only | Reduce redundant counter plate generation |

---

## 8. Detailed Reasoning for Each Implementation

### 8.1 Why Client-Side CSG?

- **Problem:** Server-side boolean operations require manifold3d or blender/openscad
- **Vercel Limitation:** Serverless functions cannot install system binaries
- **Solution:** Move CSG to browser using three-bvh-csg Web Worker
- **Benefit:** Works everywhere, no server dependencies, better user feedback

### 8.2 Why Multiple Counter Plate Implementations?

- **Historical Evolution:** Started with 2D holes, evolved to 3D shapes
- **2D (flat holes):** Works on serverless but produces inferior tactile feedback
- **3D (hemisphere/bowl/cone):** Better finger feel but requires manifold3d
- **Current Strategy:** Use 3D when available, surface error if not (don't silently degrade)

### 8.3 Why Three Recess Shapes?

- **Hemisphere (shape=0):** Maximum sphere radius = base diameter / 2
- **Bowl (shape=1, DEFAULT):** Independent control of opening diameter AND depth
- **Cone (shape=2):** Sharp edges, different tactile sensation, optimized performance

### 8.4 Why Counter Plates Always Use Server?

- **Caching Opportunity:** Counter plates don't depend on text content
- **Same Parameters = Same STL:** Can cache by settings hash alone
- **Vercel Blob Storage:** Serve cached STLs via CDN redirect (302)

### 8.5 Why Manifold3D vs Other Engines?

- **manifold3d:** Pure Python wheel, no system dependencies
- **blender/openscad:** Require binary installation (impossible on serverless)
- **trimesh default:** Tries to use available engine but often fails on serverless

### 8.6 Why Geometry Spec Extraction?

- **Separation of Concerns:** Server calculates positions, client performs CSG
- **Lightweight Server Call:** No heavy computation, just JSON coordinates
- **Enables Parallelism:** Client can start CSG immediately upon spec receipt

---

## 9. Identified Issues / Considerations

1. **Server generation without manifold3d** returns 503 error directing users to use client-side CSG
2. **Counter plates always use server** for caching benefits, requiring boolean backend
3. **Mesh validation** attempts healing for non-watertight or inconsistent winding
4. **Character markers** have font loading dependencies with CDN fallbacks
5. **Cylinder polygon cutout** can fail if shape computation produces empty geometry
6. **Client-side rounded dots** use CSG union which is slower than single mesh
7. **Bowl fallback to hemisphere** when depth ≤ 0 (edge case)

---

## 10. Generation Flow Diagrams

### 10.1 Positive Plate (Emboss) Flow

```
Request → Client CSG Available?
          ├─ YES → GET /geometry_spec → Web Worker CSG → STL Binary
          └─ NO  → POST /generate_braille_stl → Server CSG → STL Binary
                                                    │
                                                    └─ manifold3d available?
                                                       ├─ YES → 3D boolean union
                                                       └─ NO  → 503 Error
```

### 10.2 Negative Plate (Counter) Flow

```
Request → POST /generate_braille_stl
              │
              ├─ Early Cache Check → HIT → 302 Redirect to Blob URL
              │
              └─ MISS → Generate based on recess_shape:
                        ├─ 0: build_counter_plate_hemispheres()
                        ├─ 1: build_counter_plate_bowl() [DEFAULT]
                        └─ 2: build_counter_plate_cone()
                        │
                        └─ Upload to Blob → Return STL / 302 Redirect
```

---

## 11. Files Reference

| File | Primary Responsibility |

|------|----------------------|

| `backend.py` | Server endpoints, card generation, counter plates |

| `app/geometry_spec.py` | JSON specification extraction for client CSG |

| `app/geometry/cylinder.py` | Cylinder generation (positive and negative) |

| `app/geometry/booleans.py` | Boolean operation abstraction with fallbacks |

| `app/geometry/dot_shapes.py` | Braille dot creation |

| `app/geometry/braille_layout.py` | Marker creation |

| `static/workers/csg-worker.js` | Client-side CSG worker |

| `static/workers/csg-worker-manifold.js` | Manifold CSG worker for cylinders (active) |

| `templates/index.html` | Frontend orchestration |

| `app/cache.py` | Blob cache operations |

---

## 12. Testing Recommendations

To verify each path is working:

1. **Client-side CSG:** Open browser console, check for "CSG Worker: All modules loaded successfully"
2. **Server 3D booleans:** Check server logs for "manifold3d is available"
3. **Counter plate cache:** Check response headers for `X-Blob-Cache: hit`
4. **Fallback chain:** Set `FORCE_CLIENT_CSG=1` env var to test server rejection path
