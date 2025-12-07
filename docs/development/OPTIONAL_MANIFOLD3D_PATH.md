# Optional: Client-Side manifold3d Path

This document outlines how to add client-side manifold3d (WASM) as an additional CSG engine for maximum robustness, at the cost of a larger bundle size (~2-3 MB).

## Why Add manifold3d?

### Advantages Over three-bvh-csg
- **Guaranteed manifold output**: Always produces watertight meshes
- **Better edge case handling**: More robust for complex geometry
- **Numerical precision**: Better handling of floating-point edge cases
- **Proven reliability**: Used in production CAD applications

### Trade-offs
- **Bundle size**: Adds ~2-3 MB (vs ~200 KB for three-bvh-csg)
- **WASM overhead**: Initial load time, memory management complexity
- **Manual memory management**: Requires `.delete()` calls on Manifold objects
- **Setup complexity**: WASM file path configuration needed

## Implementation Plan

### 1. Install and Vendor manifold3d

```bash
npm install manifold-3d
```

Copy WASM files to static:
```bash
# PowerShell
New-Item -ItemType Directory -Force -Path static\vendor\manifold-3d
Copy-Item node_modules\manifold-3d\manifold.js static\vendor\manifold-3d\ -Force
Copy-Item node_modules\manifold-3d\manifold.wasm static\vendor\manifold-3d\ -Force
```

### 2. Create manifold3d Worker

Create `static/workers/csg-worker-manifold.js`:

```javascript
/**
 * CSG Worker using manifold3d (WASM) for maximum robustness
 */

import Module from '/static/vendor/manifold-3d/manifold.js';

let wasm = null;
let Manifold = null;

// Initialize WASM module
async function initManifold() {
    if (wasm) return;

    wasm = await Module({
        locateFile: (path) => {
            if (path.endsWith('.wasm')) {
                return '/static/vendor/manifold-3d/manifold.wasm';
            }
            return path;
        }
    });

    wasm.setup();
    Manifold = wasm.Manifold;
}

// Create braille dot using manifold primitives
function createBrailleDot(spec) {
    const { x, y, z, type, params } = spec;

    if (type === 'rounded') {
        const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;

        // Create frustum base
        let dot = null;
        if (base_height > 0) {
            dot = Manifold.cylinder(base_height, base_radius, top_radius, 48);
        }

        // Create spherical cap dome
        const sphere = Manifold.sphere(dome_radius, 64);
        const cutHeight = dome_radius - dome_height;
        const box = Manifold.cube([dome_radius * 3, dome_radius * 3, dome_radius * 3], true);
        box = box.translate([0, 0, -(dome_radius - cutHeight)]);
        const cap = sphere.subtract(box);

        // Union base and dome
        if (dot) {
            cap = cap.translate([0, 0, base_height / 2]);
            dot = dot.union(cap);
        } else {
            dot = cap;
        }

        // Translate to position
        dot = dot.translate([x, y, z]);
        return dot;

    } else {
        // Standard frustum
        const { base_radius, top_radius, height } = params;
        const dot = Manifold.cylinder(height, base_radius, top_radius, 16);
        return dot.translate([x, y, z]);
    }
}

// Process geometry spec
async function processGeometrySpec(spec) {
    await initManifold();

    const { shape_type, plate, dots, markers } = spec;

    try {
        // Create base
        let base;
        if (shape_type === 'cylinder') {
            // Cylinder implementation
            const { radius, height, thickness } = spec.cylinder;
            const outer = Manifold.cylinder(height, radius, radius, 64);
            const inner = Manifold.cylinder(height + 0.1, radius - thickness, radius - thickness, 64);
            base = outer.subtract(inner);
        } else {
            // Card plate
            const { width, height, thickness } = plate;
            base = Manifold.cube([width, height, thickness], false);
        }

        // Create all cutouts
        const cutoutManifolds = [];

        // Add dots
        if (dots && dots.length > 0) {
            for (const dotSpec of dots) {
                const dot = createBrailleDot(dotSpec);
                cutoutManifolds.push(dot);
            }
        }

        // Add markers
        if (markers && markers.length > 0) {
            for (const markerSpec of markers) {
                let marker;
                if (markerSpec.type === 'rect') {
                    const { x, y, z, width, height, depth } = markerSpec;
                    marker = Manifold.cube([width, height, depth], true);
                    marker = marker.translate([x, y, z]);
                } else if (markerSpec.type === 'triangle') {
                    // Simplified as box for now
                    const { x, y, z, size, depth } = markerSpec;
                    marker = Manifold.cube([size, size, depth], true);
                    marker = marker.translate([x, y, z]);
                }
                if (marker) cutoutManifolds.push(marker);
            }
        }

        // Batch union cutouts
        let allCutouts = cutoutManifolds[0];
        for (let i = 1; i < cutoutManifolds.length; i++) {
            allCutouts = allCutouts.union(cutoutManifolds[i]);
        }

        // Subtract from base
        const result = base.subtract(allCutouts);

        // Export to mesh
        const mesh = result.getMesh();

        // Extract geometry data
        const numTri = mesh.numTri;
        const positions = new Float32Array(numTri * 9);
        const normals = new Float32Array(numTri * 9);

        for (let i = 0; i < numTri; i++) {
            const tri = mesh.triVerts(i);
            for (let j = 0; j < 3; j++) {
                const vert = tri[j];
                positions[i * 9 + j * 3] = vert[0];
                positions[i * 9 + j * 3 + 1] = vert[1];
                positions[i * 9 + j * 3 + 2] = vert[2];
            }

            const normal = mesh.triNormal(i);
            for (let j = 0; j < 3; j++) {
                normals[i * 9 + j * 3] = normal[0];
                normals[i * 9 + j * 3 + 1] = normal[1];
                normals[i * 9 + j * 3 + 2] = normal[2];
            }
        }

        // Clean up manifold objects
        result.delete();
        allCutouts.delete();
        base.delete();
        cutoutManifolds.forEach(m => m.delete());

        // Export to STL (implement binary STL export)
        const stlData = exportToSTL(positions, normals);

        return { positions, normals, stl: stlData };

    } catch (error) {
        throw new Error(`manifold3d processing failed: ${error.message}`);
    }
}

function exportToSTL(positions, normals) {
    const numTri = positions.length / 9;
    const bufferLength = 80 + 4 + numTri * 50;
    const buffer = new ArrayBuffer(bufferLength);
    const view = new DataView(buffer);

    // Skip 80-byte header
    let offset = 80;

    // Write triangle count
    view.setUint32(offset, numTri, true);
    offset += 4;

    // Write triangles
    for (let i = 0; i < numTri; i++) {
        // Normal
        view.setFloat32(offset, normals[i * 9], true); offset += 4;
        view.setFloat32(offset, normals[i * 9 + 1], true); offset += 4;
        view.setFloat32(offset, normals[i * 9 + 2], true); offset += 4;

        // Vertices
        for (let j = 0; j < 3; j++) {
            view.setFloat32(offset, positions[i * 9 + j * 3], true); offset += 4;
            view.setFloat32(offset, positions[i * 9 + j * 3 + 1], true); offset += 4;
            view.setFloat32(offset, positions[i * 9 + j * 3 + 2], true); offset += 4;
        }

        // Attribute byte count (unused)
        view.setUint16(offset, 0, true); offset += 2;
    }

    return buffer;
}

// Message handler
self.onmessage = async function(event) {
    const { type, spec, requestId } = event.data;

    try {
        if (type === 'generate') {
            const result = await processGeometrySpec(spec);

            self.postMessage({
                type: 'success',
                requestId: requestId,
                geometry: {
                    positions: result.positions,
                    normals: result.normals,
                    indices: null
                },
                stl: result.stl
            }, [result.positions.buffer, result.normals.buffer, result.stl]);

        } else if (type === 'ping') {
            self.postMessage({ type: 'pong', requestId: requestId });
        }

    } catch (error) {
        self.postMessage({
            type: 'error',
            requestId: requestId,
            error: error.message,
            stack: error.stack
        });
    }
};

self.postMessage({ type: 'ready' });
```

### 3. Update Frontend to Support Both Engines

In `public/index.html`, add engine selection:

```javascript
// CSG Engine selection
let csgEngine = 'three-bvh-csg'; // or 'manifold3d'
let csgWorkerManifold = null;

// Initialize manifold worker
function initManifoldWorker() {
    if (csgWorkerManifold) return;

    try {
        csgWorkerManifold = new Worker('/static/workers/csg-worker-manifold.js', { type: 'module' });

        csgWorkerManifold.onmessage = function(event) {
            const { type } = event.data;
            if (type === 'ready') {
                log.info('Manifold CSG Worker initialized');
            }
        };

        csgWorkerManifold.onerror = function(error) {
            log.error('Manifold Worker error:', error);
            csgEngine = 'three-bvh-csg'; // Fall back
        };

    } catch (error) {
        log.warn('Failed to initialize Manifold Worker:', error);
        csgEngine = 'three-bvh-csg';
    }
}

// Select worker based on engine
function getActiveWorker() {
    if (csgEngine === 'manifold3d' && csgWorkerManifold) {
        return csgWorkerManifold;
    }
    return csgWorker; // default three-bvh-csg
}

// Initialize both workers
if (typeof Worker !== 'undefined') {
    initCSGWorker();
    initManifoldWorker();
}
```

### 4. Add UI Toggle (Optional)

Add a setting to switch engines:

```html
<div class="setting-row">
    <label for="csg-engine">CSG Engine:</label>
    <select id="csg-engine">
        <option value="three-bvh-csg">three-bvh-csg (Fast, 200 KB)</option>
        <option value="manifold3d">manifold3d (Robust, 2 MB)</option>
    </select>
</div>
```

```javascript
document.getElementById('csg-engine').addEventListener('change', (e) => {
    csgEngine = e.target.value;
    log.info('Switched to CSG engine:', csgEngine);
});
```

### 5. Cascade Fallback Strategy

Recommended fallback order:
1. **manifold3d** (if selected and available) - Maximum robustness
2. **three-bvh-csg** - Fast and lightweight
3. **Server** - Final fallback

Update `tryClientSideCSG` to try both engines:

```javascript
async function tryClientSideCSG(requestData) {
    // Try preferred engine first
    let worker = getActiveWorker();
    let engineName = csgEngine;

    try {
        return await generateWithWorker(worker, requestData);
    } catch (error) {
        log.warn(`${engineName} failed, trying fallback...`);

        // Try other engine
        if (engineName === 'manifold3d' && workerReady) {
            try {
                return await generateWithWorker(csgWorker, requestData);
            } catch (e) {
                log.warn('three-bvh-csg also failed, falling back to server');
            }
        }
    }

    return null; // Fall back to server
}
```

## Testing Checklist

- [ ] WASM file loads correctly (check Network tab)
- [ ] manifold3d worker initializes
- [ ] Can generate simple models with manifold engine
- [ ] Fallback to three-bvh-csg works
- [ ] Fallback to server works
- [ ] STL output is watertight (test in slicer)
- [ ] Memory is properly released (no leaks)
- [ ] Bundle size is acceptable for your use case

## Bundle Size Impact

| Component | Size (uncompressed) | Size (gzipped) |
|-----------|---------------------|----------------|
| manifold.js | ~200 KB | ~60 KB |
| manifold.wasm | ~2.5 MB | ~800 KB |
| **Total** | **~2.7 MB** | **~860 KB** |

## When to Use manifold3d

- **Critical applications**: Medical devices, safety equipment
- **Complex geometry**: Many intersections, edge cases
- **Guaranteed output**: Need watertight meshes for manufacturing
- **Professional use**: CAD export, production workflows

## When to Use three-bvh-csg

- **Personal projects**: Business cards, prototypes
- **Fast iteration**: Quick design changes
- **Mobile devices**: Limited bandwidth/memory
- **Hobbyist use**: 3D printing experiments

## Maintenance Notes

- Update manifold3d: `npm install manifold-3d@latest`
- Check for memory leaks: Monitor browser memory usage
- WASM caching: Vercel serves .wasm with correct MIME type automatically
- Security: WASM files should be served from same origin (CORS)
