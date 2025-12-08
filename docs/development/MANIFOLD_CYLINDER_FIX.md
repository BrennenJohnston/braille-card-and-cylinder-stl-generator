# Manifold Cylinder Fix - Zero Non-Manifold Edges

> **STATUS: ✅ IMPLEMENTED (2024-12-08)**
> The Manifold worker has been fully integrated into the frontend. Cylinder generation now automatically uses the Manifold worker, guaranteeing zero non-manifold edges.

## Problem

The original implementation used `three-bvh-csg` for all CSG operations, then attempted to "repair" the resulting mesh using Manifold's constructor. This approach failed because:

1. **Manifold constructor ≠ mesh repair**: `new Manifold(mesh)` doesn't repair non-manifold geometry - it constructs from triangle soup and may fail or produce garbage if input is broken.

2. **Cylinder geometry is complex**: Boolean operations on curved surfaces (cylinder + hundreds of curved recesses) create many edge cases:
   - Coplanar face intersections
   - T-junctions where edges don't meet cleanly
   - Tiny sliver triangles from near-tangent subtractions

3. **Counter plates are worst**: The counter plate had 47,158 non-manifold edges (vs 1,715 for embossing) because subtracting bowl/hemisphere recesses creates the most edge cases.

## Solution

Created a dedicated Manifold CSG worker (`csg-worker-manifold.js`) that uses **Manifold primitives for the entire boolean pipeline**:

1. **Manifold primitives**: Uses `Manifold.cylinder()`, `Manifold.sphere()`, `Manifold.cube()` etc.
2. **Native boolean operations**: Uses Manifold's `.add()`, `.subtract()` methods
3. **Guaranteed manifold output**: Manifold's boolean operations maintain manifold properties throughout

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (index.html)                    │
│                                                              │
│  ┌──────────────────┐        ┌───────────────────────────┐  │
│  │ shape_type=card  │───────▶│ csg-worker.js            │  │
│  │                  │        │ (three-bvh-csg)          │  │
│  └──────────────────┘        │ Fast, ~200KB             │  │
│                              └───────────────────────────┘  │
│                                                              │
│  ┌──────────────────┐        ┌───────────────────────────┐  │
│  │ shape_type=      │───────▶│ csg-worker-manifold.js   │  │
│  │ cylinder         │        │ (Manifold WASM)          │  │
│  └──────────────────┘        │ Guaranteed manifold,     │  │
│                              │ ~2.5MB WASM              │  │
│                              └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Files Changed

### New Files
- `static/workers/csg-worker-manifold.js` - Manifold-based CSG worker

### Modified Files (2024-12-08 Integration)
- `public/index.html` - Added Manifold worker initialization and routing logic
- `templates/index.html` - Added Manifold worker initialization and routing logic

### Key Changes in Frontend
1. Added `manifoldWorker`, `manifoldWorkerReady`, `manifoldRequestId`, `pendingManifoldRequests` variables
2. Added Manifold worker initialization in `window.onload` (30-second timeout for WASM loading)
3. Updated `generateSTLClientSide()` to select worker based on `shapeType`:
   - `cylinder` → Manifold worker (guaranteed manifold)
   - `card` → Standard three-bvh-csg worker (faster)

## How It Works

1. **Worker Selection**: When generating STL, the frontend checks `spec.shape_type`:
   - `cylinder` → Uses Manifold worker (REQUIRED - no fallback)
   - `card` → Uses standard three-bvh-csg worker

2. **No Fallback**: If Manifold worker fails to load (CDN issue, timeout), cylinder generation will display an error message asking the user to refresh. There is NO fallback to the standard worker for cylinders because it produces non-manifold edges.

3. **Coordinate System**: Manifold uses Z-up natively, matching the STL/CAD convention

## Expected Console Output

### Successful Cylinder Generation (Manifold)
```
Manifold CSG Worker: WASM loaded from https://cdn.jsdelivr.net/npm/manifold-3d@2.5.1/manifold.js
Manifold CSG Worker: Initialization complete
Using Manifold CSG worker for cylinder generation
Manifold CSG Worker: Processing cylinder negative with 500 dots and 2 markers
Manifold CSG Worker: Created cylinder shell with polygon cutout
Manifold CSG Worker: Created 500/500 dots successfully
Manifold CSG Worker: Generated mesh with 125000 triangles
Manifold CSG Worker: Generation complete
Manifold CSG generation successful
```

### Successful Card Generation (Standard)
```
Using Standard CSG worker for card generation
CSG Worker: Processing card positive with 100 dots and 1 markers
Client-side CSG generation successful
```

## Testing

1. Open browser DevTools console
2. Generate a cylinder STL (embossing or counter plate)
3. Verify console shows "Using Manifold CSG worker for cylinder generation"
4. Download the STL and verify in a slicer:
   - **PrusaSlicer**: Should show no repair notifications
   - **Meshmixer**: Analysis → Inspector should show 0 errors
   - **Online**: viewstl.com or makeprintable.com

## Performance Notes

| Aspect | Standard Worker | Manifold Worker |
|--------|-----------------|-----------------|
| Bundle size | ~200KB | ~2.5MB WASM |
| First load | Instant | +2-3 seconds |
| Processing | Fast | Slightly slower |
| Manifold guarantee | No | Yes |
| Best for | Flat cards | Cylinders |

## Rollback

To disable Manifold worker and use only standard worker:

```javascript
// In public/index.html, change:
initManifoldWorker();

// To:
// initManifoldWorker(); // Disabled - use standard worker for all
```

## Why Not Use Manifold for Everything?

While Manifold could handle flat cards too, the standard three-bvh-csg worker is:
- Much faster for simpler geometry
- Smaller bundle size (no WASM)
- Already produces acceptable results for flat cards

The hybrid approach gives the best of both worlds: fast flat card generation and guaranteed manifold cylinders.
