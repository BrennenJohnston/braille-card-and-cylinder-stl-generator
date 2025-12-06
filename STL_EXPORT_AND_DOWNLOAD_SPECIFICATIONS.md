# STL Export and Download Core Specifications

## Document Purpose

This document provides **comprehensive, in-depth specifications** for the STL export and download system in the Braille Card and Cylinder STL Generator application. It serves as an authoritative reference for future development by documenting:

1. **Generation Architecture** — Client-side CSG (primary) vs. server-side (fallback) generation
2. **Geometry Specification Format** — JSON structure sent to CSG workers
3. **CSG Worker System** — Web Worker communication, processing, and error handling
4. **STL Export Format** — Binary STL format details and file naming conventions
5. **Download Button State Machine** — Generate/Download state transitions
6. **Fallback Mechanisms** — Automatic fallback from client to server
7. **Counter Plate Caching** — Server-side cache for negative plates
8. **Server Endpoints** — `/geometry_spec` and `/generate_braille_stl` APIs

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source for server-side logic
2. `geometry_spec.py` — Geometry specification extraction
3. `static/workers/csg-worker.js` — Client-side CSG (three-bvh-csg)
4. `static/workers/csg-worker-manifold.js` — Manifold WASM fallback/alternative
5. `templates/index.html` / `public/index.html` — Frontend orchestration

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Generation Strategy Selection](#2-generation-strategy-selection)
3. [Geometry Specification Format](#3-geometry-specification-format)
4. [CSG Worker System](#4-csg-worker-system)
5. [Manifold WASM Integration](#5-manifold-wasm-integration)
6. [STL Binary Export Format](#6-stl-binary-export-format)
7. [File Naming Conventions](#7-file-naming-conventions)
8. [Download Button State Machine](#8-download-button-state-machine)
9. [Fallback Mechanisms](#9-fallback-mechanisms)
10. [Counter Plate Caching](#10-counter-plate-caching)
11. [Server Endpoints](#11-server-endpoints)
12. [Error Handling](#12-error-handling)
13. [Performance Characteristics](#13-performance-characteristics)
14. [Cross-Implementation Consistency](#14-cross-implementation-consistency)

---

## 1. Architecture Overview

### Design Philosophy

The STL generation system follows a **client-first architecture** where:

1. **Primary path:** Client-side CSG using Web Workers
2. **Fallback path:** Server-side generation via Flask API
3. **Counter plates:** Server-side with caching to Vercel Blob storage

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER CLICKS "GENERATE STL"                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND ORCHESTRATION (index.html)                       │
│                                                                              │
│  1. Translate text to braille Unicode (via liblouis worker)                 │
│  2. Collect all form settings                                               │
│  3. Determine generation path based on:                                     │
│     - useClientSideCSG flag                                                 │
│     - Worker availability                                                   │
│     - Plate type (positive vs negative)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼───────┐                   ┌───────▼───────┐
            │ Client-Side   │                   │ Server-Side   │
            │ CSG Path      │                   │ Fallback Path │
            └───────┬───────┘                   └───────┬───────┘
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────┐     ┌───────────────────────────────────────┐
│   POST /geometry_spec          │     │   POST /generate_braille_stl          │
│   - Returns JSON spec          │     │   - Returns STL binary                │
│   - Lightweight computation    │     │   - Full server-side generation       │
│   - No boolean operations      │     │   - Used for counter plate cache      │
└───────────────┬───────────────┘     └───────────────────┬───────────────────┘
                │                                         │
                ▼                                         │
┌───────────────────────────────┐                        │
│   CSG WORKER (Web Worker)      │                        │
│   - Receives JSON spec         │                        │
│   - Creates 3D primitives      │                        │
│   - Performs boolean ops       │                        │
│   - Exports to STL binary      │                        │
│   - Optional: Manifold repair  │                        │
└───────────────┬───────────────┘                        │
                │                                         │
                └─────────────────┬───────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STL BINARY RECEIVED                                       │
│                                                                              │
│  1. Create Blob URL from ArrayBuffer                                        │
│  2. Load into Three.js scene for preview                                    │
│  3. Set download link href                                                  │
│  4. Transition button to "Download STL" state                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `index.html` | Orchestration, state management, user interaction |
| `csg-worker.js` | Primary CSG operations using three-bvh-csg |
| `csg-worker-manifold.js` | Alternative CSG using Manifold WASM |
| `geometry_spec.py` | Extract JSON spec from braille data |
| `backend.py` | Server-side generation, caching, API endpoints |

---

## 2. Generation Strategy Selection

### Decision Logic

```javascript
// From templates/index.html
async function generateSTL() {
    const plateType = getSelectedPlateType();  // 'positive' or 'negative'

    // Counter plates always use server (for caching)
    if (plateType === 'negative') {
        return await generateServerSide();
    }

    // Positive plates try client-side first
    if (useClientSideCSG && workerReady) {
        try {
            return await generateClientSide();
        } catch (error) {
            console.warn('Client-side failed, falling back to server:', error);
            return await generateServerSide();
        }
    }

    // Direct server generation if client-side disabled
    return await generateServerSide();
}
```

### Strategy Matrix

| Plate Type | useClientSideCSG | Worker Ready | Strategy |
|------------|-----------------|--------------|----------|
| Positive | true | true | Client-side CSG |
| Positive | true | false | Server fallback |
| Positive | false | any | Server direct |
| Negative | any | any | Server (cached) |

### Feature Flag

```javascript
// Global flag to enable/disable client-side CSG
let useClientSideCSG = true;  // Set to false to force server-side

// Can be toggled via browser console:
// useClientSideCSG = false;
```

---

## 3. Geometry Specification Format

### Overview

The `/geometry_spec` endpoint returns a JSON object describing all geometric primitives needed to construct the STL file. This separates the "what to build" (server calculation) from "how to build it" (client CSG operations).

### Card (Flat Plate) Specification

```json
{
    "shape_type": "card",
    "plate_type": "positive",
    "plate": {
        "width": 90.0,
        "height": 52.0,
        "thickness": 2.0,
        "center_x": 45.0,
        "center_y": 26.0,
        "center_z": 1.0
    },
    "dots": [
        {
            "type": "standard",
            "x": 10.5,
            "y": 42.0,
            "z": 2.0,
            "params": {
                "shape": "standard",
                "base_radius": 0.9,
                "top_radius": 0.2,
                "height": 1.0
            }
        },
        {
            "type": "rounded",
            "x": 17.0,
            "y": 42.0,
            "z": 2.0,
            "params": {
                "shape": "rounded",
                "base_radius": 1.0,
                "top_radius": 0.75,
                "base_height": 0.2,
                "dome_height": 0.6,
                "dome_radius": 0.76875
            }
        }
    ],
    "markers": [
        {
            "type": "triangle",
            "x": 83.5,
            "y": 42.0,
            "z": 2.0,
            "size": 2.5,
            "depth": 0.6
        },
        {
            "type": "rect",
            "x": 5.75,
            "y": 42.0,
            "z": 2.0,
            "width": 2.5,
            "height": 5.0,
            "depth": 0.5
        },
        {
            "type": "char",
            "x": 5.75,
            "y": 32.0,
            "z": 2.0,
            "char": "J",
            "size": 3.75,
            "depth": 0.5
        }
    ]
}
```

### Cylinder Specification

```json
{
    "shape_type": "cylinder",
    "plate_type": "positive",
    "cylinder": {
        "radius": 15.375,
        "height": 52.0,
        "thickness": 2.0,
        "polygon_points": [
            {"x": 13.464, "y": 0.0},
            {"x": 11.648, "y": 6.732},
            {"x": 6.732, "y": 11.648}
        ]
    },
    "dots": [
        {
            "type": "cylinder_dot",
            "x": 15.0,
            "y": 26.0,
            "z": 0.0,
            "theta": 0.15,
            "radius": 15.375,
            "is_recess": false,
            "params": {
                "shape": "standard",
                "base_radius": 0.9,
                "top_radius": 0.2,
                "height": 1.0
            }
        }
    ],
    "markers": [
        {
            "type": "cylinder_triangle",
            "theta": -0.5,
            "y": 42.0,
            "radius": 15.375,
            "size": 2.5,
            "depth": 0.6,
            "rotate_180": false
        }
    ]
}
```

### Specification Field Reference

#### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `shape_type` | `"card"` \| `"cylinder"` | Output geometry type |
| `plate_type` | `"positive"` \| `"negative"` | Embossing or counter plate |
| `plate` | object | Card plate dimensions (cards only) |
| `cylinder` | object | Cylinder dimensions (cylinders only) |
| `dots` | array | Braille dot specifications |
| `markers` | array | Indicator marker specifications |

#### Plate Fields (Cards)

| Field | Type | Description |
|-------|------|-------------|
| `width` | float | Card width in mm |
| `height` | float | Card height in mm |
| `thickness` | float | Card thickness in mm |
| `center_x` | float | X-center for positioning |
| `center_y` | float | Y-center for positioning |
| `center_z` | float | Z-center for positioning |

#### Cylinder Fields

| Field | Type | Description |
|-------|------|-------------|
| `radius` | float | Cylinder outer radius in mm |
| `height` | float | Cylinder height in mm |
| `thickness` | float | Wall thickness (when no polygon) |
| `polygon_points` | array | Array of {x, y} vertices for inner cutout |

#### Dot Types

| Type | Usage | Key Params |
|------|-------|------------|
| `standard` | Card emboss cone | `base_radius`, `top_radius`, `height` |
| `rounded` | Card emboss dome | `base_radius`, `top_radius`, `base_height`, `dome_height`, `dome_radius` |
| `cylinder_dot` | All cylinder dots | `theta`, `radius`, `is_recess`, `params.shape` |

#### Marker Types

| Type | Usage | Key Params |
|------|-------|------------|
| `triangle` | Card row-end marker | `size`, `depth` |
| `rect` | Card fallback/counter marker | `width`, `height`, `depth` |
| `char` | Card character indicator | `char`, `size`, `depth` |
| `cylinder_triangle` | Cylinder row marker | `theta`, `size`, `depth`, `rotate_180` |
| `cylinder_rect` | Cylinder fallback marker | `theta`, `size`, `depth` |
| `cylinder_char` | Cylinder character marker | `theta`, `char`, `size`, `depth` |

---

## 4. CSG Worker System

### Worker Initialization

**Source:** `templates/index.html`

```javascript
// Initialize CSG worker
let csgWorker = null;
let workerReady = false;

function initCSGWorker() {
    try {
        csgWorker = new Worker('/static/workers/csg-worker.js', { type: 'module' });

        csgWorker.onmessage = function(e) {
            if (e.data.type === 'ready') {
                workerReady = true;
                console.log('CSG Worker initialized and ready');
            } else if (e.data.type === 'result') {
                handleWorkerResult(e.data);
            } else if (e.data.type === 'error') {
                handleWorkerError(e.data);
            }
        };

        csgWorker.onerror = function(error) {
            console.error('CSG Worker error:', error);
            workerReady = false;
        };
    } catch (error) {
        console.warn('Failed to initialize CSG worker:', error);
        workerReady = false;
    }
}
```

### Worker Message Protocol

#### Request Message

```javascript
{
    type: 'generate',
    id: 1702345678901,           // Unique request ID (timestamp)
    spec: { ... },               // Geometry specification object
    useManifold: false           // Optional: use Manifold for repair
}
```

#### Success Response

```javascript
{
    type: 'result',
    id: 1702345678901,           // Matches request ID
    stlData: ArrayBuffer,        // Binary STL data
    geometry: BufferGeometry,    // Three.js geometry for preview
    stats: {
        dots: 97,
        markers: 8,
        vertices: 15420,
        triangles: 5140,
        time_ms: 12450
    }
}
```

#### Error Response

```javascript
{
    type: 'error',
    id: 1702345678901,
    error: 'CSG operation failed: ...',
    details: { ... }
}
```

### Worker Internal Architecture

**Source:** `static/workers/csg-worker.js`

```javascript
// Worker initialization
importScripts(...);  // Load Three.js, three-bvh-csg

self.onmessage = async function(e) {
    const { type, id, spec, useManifold } = e.data;

    if (type === 'generate') {
        try {
            console.log(`CSG Worker: Starting generation for request ${id}`);

            // 1. Create base geometry (plate or cylinder shell)
            let geometry = createBaseGeometry(spec);

            // 2. Process all dots (union or subtraction)
            for (const dot of spec.dots) {
                const dotGeom = createDotGeometry(dot, spec);
                geometry = performBoolean(geometry, dotGeom, dot.is_recess);
            }

            // 3. Process all markers (always subtraction)
            for (const marker of spec.markers) {
                const markerGeom = createMarkerGeometry(marker, spec);
                geometry = performBoolean(geometry, markerGeom, true);
            }

            // 4. Optional: Manifold repair
            if (useManifold && manifoldReady) {
                geometry = repairGeometryWithManifold(geometry);
            }

            // 5. Export to STL
            const stlData = exportToSTL(geometry);

            self.postMessage({
                type: 'result',
                id: id,
                stlData: stlData,
                geometry: geometry.toJSON(),
                stats: collectStats(spec, geometry)
            });

        } catch (error) {
            self.postMessage({
                type: 'error',
                id: id,
                error: error.message
            });
        }
    }
};

// Notify main thread that worker is ready
self.postMessage({ type: 'ready' });
```

### Boolean Operations

```javascript
// Using three-bvh-csg
import { Evaluator, Brush, ADDITION, SUBTRACTION } from 'three-bvh-csg';

const evaluator = new Evaluator();

function performBoolean(baseGeom, toolGeom, isSubtraction) {
    const baseBrush = new Brush(baseGeom);
    const toolBrush = new Brush(toolGeom);

    const operation = isSubtraction ? SUBTRACTION : ADDITION;
    const resultBrush = evaluator.evaluate(baseBrush, toolBrush, operation);

    return resultBrush.geometry;
}
```

---

## 5. Manifold WASM Integration

### Purpose

Manifold 3D WASM provides mesh repair capabilities to fix non-manifold edges that can occur during CSG operations.

### Initialization

**Source:** `static/workers/csg-worker.js` (lines 81-106)

```javascript
let ManifoldModule = null;
let manifoldReady = false;

async function initManifold() {
    const cdnUrls = [
        'https://cdn.jsdelivr.net/npm/manifold-3d@2.5.1/manifold.js',
        'https://unpkg.com/manifold-3d@2.5.1/manifold.js'
    ];

    for (const url of cdnUrls) {
        try {
            importScripts(url);
            ManifoldModule = await Module();
            manifoldReady = true;
            console.log('CSG Worker: Manifold3D WASM loaded from', url);
            return;
        } catch (error) {
            console.warn('Failed to load Manifold from', url);
        }
    }

    console.log('CSG Worker: Manifold3D not available, mesh repair disabled');
}
```

### Repair Function

```javascript
function repairGeometryWithManifold(geometry) {
    if (!manifoldReady || !ManifoldModule) {
        return geometry;  // Pass through if not available
    }

    try {
        // Convert Three.js BufferGeometry to Manifold mesh format
        const positions = geometry.attributes.position.array;
        const indices = geometry.index ? geometry.index.array : null;

        // Create Manifold mesh (automatically repairs during construction)
        const mesh = new ManifoldModule.Mesh({
            numProp: 3,
            vertProperties: Array.from(positions),
            triVerts: indices ? Array.from(indices) : undefined
        });

        const manifold = new ManifoldModule.Manifold(mesh);

        // Extract repaired mesh
        const repairedMesh = manifold.getMesh();

        // Convert back to Three.js
        const repairedGeometry = new THREE.BufferGeometry();
        // ... conversion logic ...

        // Clean up Manifold objects
        manifold.delete();
        mesh.delete();

        console.log('CSG Worker: Mesh repaired with Manifold3D');
        return repairedGeometry;

    } catch (error) {
        console.warn('CSG Worker: Manifold repair failed:', error);
        return geometry;  // Return original if repair fails
    }
}
```

### Usage in Generation Pipeline

```javascript
// In worker message handler
let geometry = processGeometrySpec(spec);

// Apply Manifold repair if requested and available
if (useManifold !== false) {
    geometry = repairGeometryWithManifold(geometry);
}

const stlData = exportToSTL(geometry);
```

---

## 6. STL Binary Export Format

### STL Binary Structure

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER (80 bytes)                                           │
│  - Arbitrary text, often empty or application name           │
├──────────────────────────────────────────────────────────────┤
│  TRIANGLE COUNT (4 bytes, uint32 little-endian)              │
│  - Number of triangular facets in the mesh                   │
├──────────────────────────────────────────────────────────────┤
│  TRIANGLE 1 (50 bytes)                                       │
│  ├─ Normal vector (12 bytes: 3 × float32)                    │
│  ├─ Vertex 1 (12 bytes: 3 × float32)                         │
│  ├─ Vertex 2 (12 bytes: 3 × float32)                         │
│  ├─ Vertex 3 (12 bytes: 3 × float32)                         │
│  └─ Attribute byte count (2 bytes, typically 0)              │
├──────────────────────────────────────────────────────────────┤
│  TRIANGLE 2 (50 bytes)                                       │
│  ... repeats for each triangle ...                           │
└──────────────────────────────────────────────────────────────┘
```

### Export Implementation

**Source:** `static/examples/STLExporter.js`

```javascript
class STLExporter {
    parse(geometry, options = {}) {
        // Ensure we have a non-indexed geometry
        let geom = geometry;
        if (geometry.index !== null) {
            geom = geometry.toNonIndexed();
        }

        const positions = geom.attributes.position.array;
        const normals = geom.attributes.normal ? geom.attributes.normal.array : null;

        const triangleCount = positions.length / 9;
        const bufferLength = 80 + 4 + (triangleCount * 50);
        const buffer = new ArrayBuffer(bufferLength);
        const dataView = new DataView(buffer);

        // Write header (80 bytes)
        // Typically left as zeros or contains metadata

        // Write triangle count (uint32, little-endian)
        dataView.setUint32(80, triangleCount, true);

        let offset = 84;
        for (let i = 0; i < triangleCount; i++) {
            const idx = i * 9;

            // Normal vector
            // ... calculate from vertices if not provided ...

            // Write normal (3 × float32)
            dataView.setFloat32(offset + 0, nx, true);
            dataView.setFloat32(offset + 4, ny, true);
            dataView.setFloat32(offset + 8, nz, true);

            // Write vertex 1
            dataView.setFloat32(offset + 12, positions[idx + 0], true);
            dataView.setFloat32(offset + 16, positions[idx + 1], true);
            dataView.setFloat32(offset + 20, positions[idx + 2], true);

            // Write vertex 2
            dataView.setFloat32(offset + 24, positions[idx + 3], true);
            dataView.setFloat32(offset + 28, positions[idx + 4], true);
            dataView.setFloat32(offset + 32, positions[idx + 5], true);

            // Write vertex 3
            dataView.setFloat32(offset + 36, positions[idx + 6], true);
            dataView.setFloat32(offset + 40, positions[idx + 7], true);
            dataView.setFloat32(offset + 44, positions[idx + 8], true);

            // Attribute byte count (always 0)
            dataView.setUint16(offset + 48, 0, true);

            offset += 50;
        }

        return buffer;
    }
}
```

### Coordinate System

**CRITICAL:** The final STL must use Z-up orientation (standard CAD convention):

| Axis | Direction |
|------|-----------|
| X | Width (left-right) |
| Y | Depth (front-back) |
| Z | Height (up-down) |

**Three.js uses Y-up internally.** For cylinders, a rotation is applied:

```javascript
// In csg-worker.js
if (isCylinder) {
    finalGeometry.rotateX(Math.PI / 2);  // Y-up → Z-up
    console.log('CSG Worker: Rotated cylinder to Z-up orientation');
}
```

---

## 7. File Naming Conventions

### Naming Pattern

```
braille_[content]_[shape]_[plate].stl
```

### Components

| Component | Values | Example |
|-----------|--------|---------|
| `braille` | Fixed prefix | `braille_` |
| `content` | Sanitized first line | `john_smith` |
| `shape` | `card` or `cylinder` | `card` |
| `plate` | `emboss` or `counter` | `emboss` |

### Sanitization Rules

```javascript
function sanitizeFilename(text) {
    return text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')  // Replace non-alphanumeric with underscore
        .replace(/^_+|_+$/g, '')       // Trim leading/trailing underscores
        .substring(0, 30);              // Limit length
}

function generateFilename(lines, shapeType, plateType) {
    const content = sanitizeFilename(lines[0] || 'untitled');
    const shape = shapeType === 'cylinder' ? 'cylinder' : 'card';
    const plate = plateType === 'negative' ? 'counter' : 'emboss';

    return `braille_${content}_${shape}_${plate}.stl`;
}
```

### Examples

| First Line | Shape | Plate | Filename |
|------------|-------|-------|----------|
| "John Smith" | card | positive | `braille_john_smith_card_emboss.stl` |
| "Hello World!" | cylinder | positive | `braille_hello_world_cylinder_emboss.stl` |
| "" (empty) | card | negative | `braille_untitled_card_counter.stl` |
| "123 Main St." | cylinder | negative | `braille_123_main_st_cylinder_counter.stl` |

---

## 8. Download Button State Machine

### States

| State | Button Text | CSS Class | Enabled | Action |
|-------|-------------|-----------|---------|--------|
| **Generate** | "Generate STL" | `generate-state` | Yes | Start generation |
| **Generating** | "Generating..." | `generating-state` | No | — |
| **Download** | "Download STL" | `download-state` | Yes | Download file |
| **Error** | "Generate STL" | `generate-state` | Yes | Retry |

### State Transitions

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                        ┌───────────────┐                              │
│  ┌─────────────────────►  GENERATE     │◄────────────────────────────┐│
│  │                     │               │                              ││
│  │                     └───────┬───────┘                              ││
│  │                             │                                      ││
│  │                     [User clicks]                                  ││
│  │                             │                                      ││
│  │                             ▼                                      ││
│  │                     ┌───────────────┐                              ││
│  │                     │  GENERATING   │                              ││
│  │                     │  (disabled)   │                              ││
│  │                     └───────┬───────┘                              ││
│  │                             │                                      ││
│  │              ┌──────────────┴──────────────┐                       ││
│  │              │                             │                       ││
│  │       [Success]                      [Error]                       ││
│  │              │                             │                       ││
│  │              ▼                             └───────────────────────┘│
│  │      ┌───────────────┐                                             │
│  │      │   DOWNLOAD    │                                             │
│  │      │               │                                             │
│  │      └───────┬───────┘                                             │
│  │              │                                                     │
│  │       [User clicks                                                 │
│  │        Download]                                                   │
│  │              │                                                     │
│  │              ▼                                                     │
│  │      File downloaded                                               │
│  │              │                                                     │
│  │       [Any input                                                   │
│  │        changes]                                                    │
│  │              │                                                     │
│  └──────────────┘                                                     │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Implementation

```javascript
const actionBtn = document.getElementById('action-btn');

function resetToGenerateState() {
    actionBtn.textContent = 'Generate STL';
    actionBtn.className = 'generate-state';
    actionBtn.setAttribute('data-state', 'generate');
    actionBtn.setAttribute('aria-label', 'Generate STL file from entered text');
    actionBtn.disabled = false;
    actionBtn.style.opacity = '1';
}

function setToGeneratingState() {
    actionBtn.textContent = 'Generating...';
    actionBtn.className = 'generating-state';
    actionBtn.setAttribute('data-state', 'generating');
    actionBtn.setAttribute('aria-label', 'STL file is being generated');
    actionBtn.disabled = true;
    actionBtn.style.opacity = '0.6';
}

function setToDownloadState() {
    actionBtn.textContent = 'Download STL';
    actionBtn.className = 'download-state';
    actionBtn.setAttribute('data-state', 'download');
    actionBtn.setAttribute('aria-label', 'Download generated STL file');
    actionBtn.disabled = false;
    actionBtn.style.opacity = '1';
}

// Any input change resets to Generate state
document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('input', resetToGenerateState);
});
```

### High Contrast Button Colors

| State | Background | Text | Border |
|-------|------------|------|--------|
| Generate | `#0201fe` (Blue) | `#fdfe00` (Yellow) | `2px solid #fdfe00` |
| Generating | `#666666` (Gray) | `#cccccc` (Light Gray) | `2px solid #999999` |
| Download | `#02fe05` (Green) | `#000000` (Black) | `2px solid #000000` |

---

## 9. Fallback Mechanisms

### Fallback Triggers

| Trigger | Cause | Action |
|---------|-------|--------|
| Worker initialization fails | Browser doesn't support module workers | Server-side generation |
| `/geometry_spec` fails | Network error, server error | Server-side generation |
| CSG worker throws error | Boolean operation failure | Server-side generation |
| Worker timeout (2 min) | Very complex model | Server-side generation |
| Counter plate requested | Caching requirement | Server-side generation |

### Fallback Implementation

```javascript
async function generateSTL() {
    const plateType = getSelectedPlateType();

    // Counter plates always use server (for caching)
    if (plateType === 'negative') {
        return await generateServerSide();
    }

    // Try client-side first
    if (useClientSideCSG && workerReady) {
        try {
            // Set timeout for client-side generation
            const timeout = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Worker timeout')), 120000)
            );

            const result = await Promise.race([
                generateClientSide(),
                timeout
            ]);

            return result;

        } catch (error) {
            console.warn('Client-side generation failed:', error);
            console.log('Falling back to server-side generation');

            // Optionally disable client-side for future requests
            // useClientSideCSG = false;
        }
    }

    // Server fallback
    return await generateServerSide();
}
```

### User Notification

```javascript
function showFallbackNotification() {
    const notice = document.createElement('div');
    notice.className = 'fallback-notice';
    notice.textContent = 'Using server-side generation...';
    notice.setAttribute('role', 'status');
    notice.setAttribute('aria-live', 'polite');
    document.body.appendChild(notice);
    setTimeout(() => notice.remove(), 3000);
}
```

---

## 10. Counter Plate Caching

### Cache Strategy

Counter plates (negative) are deterministic based on grid settings only, not text content. This enables aggressive caching:

1. **Cache Key:** Hash of grid settings (rows, columns, spacing, dot shape)
2. **Storage:** Vercel Blob storage
3. **Response:** Redirect to cached Blob URL

### Cache Key Generation

**Source:** `backend.py`

```python
def compute_counter_plate_cache_key(params: CardSettings, shape_type: str, cylinder_params: dict = None) -> str:
    """Generate a deterministic cache key for counter plate geometry."""

    key_parts = [
        f'shape:{shape_type}',
        f'rows:{params.grid_rows}',
        f'cols:{params.grid_columns}',
        f'cell_spacing:{params.cell_spacing}',
        f'line_spacing:{params.line_spacing}',
        f'dot_spacing:{params.dot_spacing}',
        f'recess_shape:{params.recess_shape}',
    ]

    if shape_type == 'cylinder' and cylinder_params:
        key_parts.extend([
            f'diameter:{cylinder_params.get("diameter_mm", 30.75)}',
            f'height:{cylinder_params.get("height_mm", 52)}',
            f'polygon_radius:{cylinder_params.get("polygonal_cutout_radius_mm", 13)}',
            f'polygon_sides:{cylinder_params.get("polygonal_cutout_sides", 12)}',
        ])

    key_string = '|'.join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]
```

### Cache Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    POST /generate_braille_stl (negative plate)              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  Compute cache key   │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  Check Blob storage  │
                           └──────────┬───────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              [Cache HIT]                         [Cache MISS]
                    │                                   │
                    ▼                                   ▼
           ┌───────────────┐                   ┌───────────────┐
           │  Return 302   │                   │  Generate STL │
           │  Redirect to  │                   │  Upload to    │
           │  Blob URL     │                   │  Blob storage │
           └───────────────┘                   └───────┬───────┘
                                                       │
                                                       ▼
                                               ┌───────────────┐
                                               │  Return 302   │
                                               │  Redirect to  │
                                               │  Blob URL     │
                                               └───────────────┘
```

### Cache Headers

```python
# Response for cached counter plate
return redirect(blob_url, code=302)

# Cache control on Blob URL (set by Vercel Blob)
# Cache-Control: public, max-age=31536000, immutable
```

---

## 11. Server Endpoints

### POST /geometry_spec

**Purpose:** Extract geometry specification without performing boolean operations.

**Request:**

```json
{
    "lines": ["⠚⠕⠓⠝", "⠎⠍⠊⠞⠓"],
    "original_lines": ["John", "Smith"],
    "placement_mode": "manual",
    "plate_type": "positive",
    "shape_type": "card",
    "settings": {
        "grid_columns": 13,
        "grid_rows": 4,
        "cell_spacing": 6.5,
        "line_spacing": 10.0,
        "dot_spacing": 2.5
    }
}
```

**Response (200 OK):**

```json
{
    "shape_type": "card",
    "plate_type": "positive",
    "plate": { ... },
    "dots": [ ... ],
    "markers": [ ... ]
}
```

**Response (400 Bad Request):**

```json
{
    "error": "Validation error message"
}
```

### POST /generate_braille_stl

**Purpose:** Full server-side STL generation (used for fallback and counter plates).

**Request:**

```json
{
    "lines": ["⠚⠕⠓⠝", "⠎⠍⠊⠞⠓"],
    "original_lines": ["John", "Smith"],
    "placement_mode": "manual",
    "plate_type": "positive",
    "shape_type": "card",
    "settings": { ... },
    "cylinder_params": { ... }
}
```

**Response (200 OK):**

```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="braille_john_card_emboss.stl"

[Binary STL data]
```

**Response (302 Redirect - Cached counter plate):**

```
Location: https://[blob-url]/counter_plate_[hash].stl
```

**Response (500 Error):**

```json
{
    "error": "Generation failed: [error message]"
}
```

---

## 12. Error Handling

### Error Categories

| Category | Source | Handling |
|----------|--------|----------|
| Validation Error | Invalid input | Display message, stay in Generate state |
| Network Error | Fetch failed | Retry or show error |
| Worker Error | CSG operation failed | Fallback to server |
| Server Error | Backend exception | Display error message |
| Timeout | Operation took too long | Fallback to server |

### User-Facing Error Messages

```javascript
const errorMessages = {
    'validation': 'Please check your input. ',
    'network': 'Network error. Please check your connection and try again.',
    'worker': 'Client-side generation failed. Trying server...',
    'server': 'Server error. Please try again later.',
    'timeout': 'Generation is taking too long. Please try a simpler design.',
    'unknown': 'An unexpected error occurred. Please refresh and try again.'
};

function showError(type, details = '') {
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');

    errorText.textContent = errorMessages[type] + details;
    errorDiv.style.display = 'flex';

    // Announce to screen readers
    errorDiv.setAttribute('role', 'alert');
}
```

### Error Recovery

```javascript
async function handleGenerationError(error, fallbackToServer = true) {
    console.error('Generation error:', error);

    if (fallbackToServer && error.type !== 'validation') {
        showError('worker');
        try {
            return await generateServerSide();
        } catch (serverError) {
            showError('server', serverError.message);
            resetToGenerateState();
            return null;
        }
    }

    showError(error.type || 'unknown', error.message);
    resetToGenerateState();
    return null;
}
```

---

## 13. Performance Characteristics

### Client-Side Generation Times

| Model Size | Dots | Markers | Typical Time | Memory Usage |
|------------|------|---------|--------------|--------------|
| Small | 10-30 | 4-8 | 2-5 seconds | ~50-100 MB |
| Medium | 50-100 | 8-12 | 5-15 seconds | ~100-200 MB |
| Large | 150-250 | 12-16 | 15-30 seconds | ~200-350 MB |
| Very Large | 300+ | 16+ | 30-60 seconds | ~350-500 MB |

### Server-Side Generation Times

| Model Size | Time (Cold Start) | Time (Warm) |
|------------|-------------------|-------------|
| Small | 5-10 seconds | 2-3 seconds |
| Medium | 10-20 seconds | 5-10 seconds |
| Large | 20-40 seconds | 10-20 seconds |
| Very Large | May timeout | 20-40 seconds |

### Bundle Sizes

| Component | Size (minified) | Size (gzipped) |
|-----------|-----------------|----------------|
| three.module.js | ~650 KB | ~150 KB |
| three-bvh-csg | ~120 KB | ~35 KB |
| three-mesh-bvh | ~95 KB | ~25 KB |
| STLExporter | ~5 KB | ~2 KB |
| csg-worker.js | ~50 KB | ~15 KB |
| **Total** | **~920 KB** | **~227 KB** |

### Manifold WASM (Optional)

| Component | Size | Notes |
|-----------|------|-------|
| manifold.js | ~2.5 MB | Loaded from CDN |
| WASM module | ~1.5 MB | Part of above |
| Runtime memory | ~10-20 MB | During repair |

---

## 14. Cross-Implementation Consistency

### Geometry Spec Consistency

All generation methods must produce geometrically identical results:

| Aspect | geometry_spec.py | csg-worker.js | backend.py |
|--------|-----------------|---------------|------------|
| Plate center | `(w/2, h/2, t/2)` | Same | Same |
| Dot positions | `dot_positions` array | Same | Same |
| Angular direction | `apply_seam()` | Same | Same |
| Counter plate: all dots | Yes | Yes | Yes |
| Counter plate: rect only | Yes | Yes | Yes |

### Verification Tests

```python
# Verify client and server produce identical geometry
def test_geometry_consistency():
    # Generate via geometry_spec
    spec = extract_card_geometry_spec(lines, settings, ...)

    # Generate server-side
    server_stl = generate_braille_stl(lines, settings, ...)

    # Send spec to worker, get client-side STL
    client_stl = worker.generate(spec)

    # Compare vertex counts (should be similar)
    assert abs(count_vertices(server_stl) - count_vertices(client_stl)) < 100

    # Compare bounding boxes (should be identical)
    assert bounding_box(server_stl) == bounding_box(client_stl)
```

### Known Differences

| Aspect | Client-Side | Server-Side | Impact |
|--------|-------------|-------------|--------|
| Triangle count | May vary | May vary | None (mesh equivalence) |
| Vertex order | May differ | May differ | None |
| Normal calculation | Auto | Auto | None |
| Manifold repair | Optional | Not applied | Mesh quality |

---

## Appendix A: Worker File Locations

| File | Path | Purpose |
|------|------|---------|
| CSG Worker | `static/workers/csg-worker.js` | Primary CSG operations |
| Manifold Worker | `static/workers/csg-worker-manifold.js` | Alternative with Manifold |
| Three.js | `static/three.module.js` | 3D library |
| BVH CSG | `static/vendor/three-bvh-csg/index.module.js` | Boolean operations |
| Mesh BVH | `static/vendor/three-mesh-bvh/index.module.js` | BVH acceleration |
| STL Exporter | `static/examples/STLExporter.js` | Binary export |

---

## Appendix B: Troubleshooting Guide

### STL Won't Generate

1. Check browser console for errors
2. Verify worker initialized: `console.log(workerReady)`
3. Try disabling client-side: `useClientSideCSG = false`
4. Check network tab for `/geometry_spec` failures

### Generated STL is Invalid

1. Import into slicer, check for errors
2. Try with Manifold repair enabled
3. Compare with server-generated version
4. Check for non-manifold edges

### Generation is Slow

1. Check model complexity (dot count)
2. Close other browser tabs
3. Try server-side for large models
4. Check browser memory usage

### Worker Fails to Initialize

1. Check browser supports module workers (Chrome 80+, Firefox 114+, Safari 15+)
2. Verify all files exist in `/static/`
3. Check for CORS errors
4. Try hard refresh (Ctrl+Shift+R)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-06 | Initial specification document |

---

## Related Specifications

- [UI_INTERFACE_CORE_SPECIFICATIONS.md](./UI_INTERFACE_CORE_SPECIFICATIONS.md) — Button styling and states
- [BRAILLE_DOT_SHAPE_SPECIFICATIONS.md](./BRAILLE_DOT_SHAPE_SPECIFICATIONS.md) — Dot geometry details
- [RECESS_INDICATOR_SPECIFICATIONS.md](./RECESS_INDICATOR_SPECIFICATIONS.md) — Marker specifications
- [BRAILLE_SPACING_SPECIFICATIONS.md](./BRAILLE_SPACING_SPECIFICATIONS.md) — Layout calculations
- [LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md](./LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md) — Translation system
