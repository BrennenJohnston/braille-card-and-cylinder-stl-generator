# STL Export and Download Core Specifications

## Document Purpose

This document provides **comprehensive, in-depth specifications** for the STL export and download system in the Braille Card and Cylinder STL Generator application. It serves as an authoritative reference for future development by documenting:

1. **Generation Architecture** — Client-side CSG (exclusive method, no fallback)
2. **Geometry Specification Format** — JSON structure sent to CSG workers
3. **CSG Worker System** — Web Worker communication, processing, and error handling
4. **STL Export Format** — Binary STL format details and file naming conventions
5. **Download Button State Machine** — Generate/Download state transitions
6. **Error Handling** — No automatic fallback; errors displayed to user
7. **Server Endpoints** — `/geometry_spec` API (primary), `/generate_braille_stl` (legacy, unused)

> **BUG FIX (2024-12-08):** Prior to this fix, the CSG worker existed but was never integrated into the frontend. The frontend incorrectly called `/generate_braille_stl` directly. This has been corrected - the frontend now properly uses client-side CSG exclusively via `/geometry_spec` → CSG Worker. Server-side fallback has been intentionally disabled.

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source for server-side logic
2. `geometry_spec.py` — Geometry specification extraction
3. `static/workers/csg-worker.js` — Client-side CSG for cards (three-bvh-csg)
4. `static/workers/csg-worker-manifold.js` — Client-side CSG for cylinders (Manifold WASM, guarantees manifold output)
5. `templates/index.html` / `public/index.html` — Frontend orchestration with dual worker selection

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

The STL generation system follows a **client-only architecture** where:

1. **Exclusive path:** Client-side CSG using Web Workers
2. **No fallback:** Server-side generation is disabled (endpoint exists but unused)
3. **All plate types:** Both positive and negative plates generated client-side

> **Updated 2024-12-08:** Server-side fallback has been intentionally disabled to ensure consistent behavior and surface bugs immediately.

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
│  3. Call generateSTLClientSide() - NO FALLBACK                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │ Client-Side     │
                            │ CSG Path ONLY   │
                            └────────┬────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────┐
                   │   POST /geometry_spec          │
                   │   - Returns JSON spec          │
                   │   - Lightweight computation    │
                   │   - No boolean operations      │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │   CSG WORKER (Web Worker)      │
                   │   - Receives JSON spec         │
                   │   - Creates 3D primitives      │
                   │   - Performs boolean ops       │
                   │   - Exports to STL binary      │
                   │   - Optional: Manifold repair  │
                   └───────────────┬───────────────┘
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

                    ┌─────────────────────────────────────┐
                    │   ON ERROR: Display error message   │
                    │   (NO automatic server fallback)    │
                    └─────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `index.html` | Orchestration, CSG worker init, state management |
| `csg-worker.js` | Exclusive CSG operations using three-bvh-csg |
| `geometry_spec.py` | Extract JSON spec from braille data |
| `backend.py` | `/geometry_spec` endpoint (primary); `/generate_braille_stl` exists but unused |

---

## 2. Generation Strategy Selection

### Decision Logic (Updated 2024-12-08)

```javascript
// From templates/index.html - NO FALLBACK
// All STL generation uses client-side CSG exclusively

// On form submit, after braille translation:
try {
    const stlData = await generateSTLClientSide({
        lines: translatedLines,
        originalLines: originalForIndicators,
        placementMode: placementMode,
        plateType: plateType,
        shapeType: shapeType,
        cylinderParams: cylinderParams,
        perLineLanguageTables: perLineLanguageTables,
        settings: settings
    });
    // Success: create blob, show preview, enable download
} catch (csgError) {
    // Error: show error message to user (NO server fallback)
    errorText.textContent = 'STL generation failed: ' + csgError.message;
}
```

### Strategy Matrix (Simplified)

| Plate Type | Worker Ready | Strategy |
|------------|--------------|----------|
| Positive | true | Client-side CSG |
| Positive | false | **Error** (no fallback) |
| Negative | true | Client-side CSG |
| Negative | false | **Error** (no fallback) |

### No Feature Flag

Server-side fallback has been intentionally disabled. There is no feature flag to toggle between methods. This ensures:
- Consistent behavior across all users
- Bugs are surfaced immediately (not hidden by fallback)
- The correct generation path is always used

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

### Embossing Plate Naming Pattern

```
Embossing_Plate_[first_word].stl
```

The embossing plate filename uses the **first word** from the text input field (Line 1 is prioritized, then other lines as fallback).

### Counter Plate Naming Pattern

```
Universal_Counter_Plate_[counter].stl
```

Counter plates use a **session-based sequential counter** that increments with each download. The counter resets when the page is refreshed.

### Counter Limits

| Aspect | Value | Rationale |
|--------|-------|-----------|
| Initial Value | 1 | First download starts at 1 |
| Maximum Value | 999 | Reasonable limit for single session |
| Overflow Behavior | Wraps to 1 | Prevents excessively long filenames |
| Persistence | Session only | Resets on page refresh |

### Components

| Plate Type | Component | Description | Example |
|------------|-----------|-------------|---------|
| Embossing | `Embossing_Plate_` | Fixed prefix | `Embossing_Plate_` |
| Embossing | `first_word` | First word from text input, sanitized | `brennen` |
| Counter | `Universal_Counter_Plate_` | Fixed prefix | `Universal_Counter_Plate_` |
| Counter | `counter` | Sequential download number (1-999) | `1`, `2`, `42` |

### First Word Extraction

The first word is extracted from the first non-empty line of text input:

```javascript
function extractFirstWord(text) {
    // Split by whitespace and get the first word
    const words = text.trim().split(/\s+/);
    return words[0] || '';
}
```

### Sanitization Rules

```javascript
function sanitizeFilename(text) {
    return text
        .replace(/[^\w\s-]/g, '')      // Remove special characters
        .replace(/[-\s]+/g, '_')       // Replace spaces/hyphens with underscore
        .replace(/^_+|_+$/g, '')       // Trim leading/trailing underscores
        .substring(0, 30);              // Limit length
}

function generateEmbossingFilename(lines) {
    // Find first non-empty line
    for (const line of lines) {
        if (line.trim()) {
            // Extract first word and sanitize
            const firstWord = line.trim().split(/\s+/)[0];
            const sanitized = sanitizeFilename(firstWord);
            if (sanitized) {
                return `Embossing_Plate_${sanitized}.stl`;
            }
        }
    }
    // Fallback if no text
    return 'Embossing_Plate_untitled.stl';
}

// Session-based counter for counter plate downloads
let counterPlateDownloadCounter = 0;
const COUNTER_PLATE_MAX = 999;

function generateCounterFilename() {
    // Increment counter (wraps at max)
    counterPlateDownloadCounter = (counterPlateDownloadCounter % COUNTER_PLATE_MAX) + 1;
    return `Universal_Counter_Plate_${counterPlateDownloadCounter}.stl`;
}
```

### Examples

#### Embossing Plates

| Text Input | First Word | Filename |
|------------|------------|----------|
| "brennen johnston watap@uw.edu" | brennen | `Embossing_Plate_brennen.stl` |
| "John Smith" | John | `Embossing_Plate_John.stl` |
| "Hello World!" | Hello | `Embossing_Plate_Hello.stl` |
| "" (empty) | — | `Embossing_Plate_untitled.stl` |
| "123 Main St." | 123 | `Embossing_Plate_123.stl` |

#### Counter Plates

| Download # | Filename |
|------------|----------|
| 1st download | `Universal_Counter_Plate_1.stl` |
| 2nd download | `Universal_Counter_Plate_2.stl` |
| 42nd download | `Universal_Counter_Plate_42.stl` |
| 999th download | `Universal_Counter_Plate_999.stl` |
| 1000th download | `Universal_Counter_Plate_1.stl` (wraps) |

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

## 9. Fallback Mechanisms (DISABLED)

> **Updated 2024-12-08:** Server-side fallback has been intentionally disabled. All errors are surfaced to the user.

### Error Conditions (No Fallback)

| Condition | Cause | Action |
|-----------|-------|--------|
| Worker initialization fails | Browser doesn't support module workers | **Show error message** |
| `/geometry_spec` fails | Network error, server error | **Show error message** |
| CSG worker throws error | Boolean operation failure | **Show error message** |
| Worker timeout (2 min) | Very complex model | **Show error message** |

### Rationale for Disabling Fallback

1. **Bug Discovery:** The original fallback hid a critical bug where the CSG worker was never integrated
2. **Consistency:** All users get the same behavior regardless of edge cases
3. **Debugging:** Errors are immediately visible, not silently handled
4. **Simplicity:** Single code path is easier to maintain and test

### Error Handling Implementation

```javascript
// From templates/index.html - NO FALLBACK
try {
    const stlData = await generateSTLClientSide({...});
    // Success path
} catch (csgError) {
    log.error('Client-side CSG generation failed:', csgError);

    // Show error - NO FALLBACK TO SERVER
    errorText.textContent = 'STL generation failed: ' + csgError.message;
    errorDiv.style.display = 'flex';
    errorDiv.className = 'error-message';

    // Re-enable button and reset to generate state
    resetToGenerateState();
}
```

### Legacy Endpoints (Still Available)

The `/generate_braille_stl` endpoint still exists in `backend.py` but is **not called by the frontend**. It may be useful for:
- Direct API testing
- Future integrations
- Emergency manual generation (via curl/Postman)

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

**Purpose:** Full server-side STL generation (LEGACY - endpoint exists but is NOT used by frontend).

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
| Network Error | Fetch failed | Display error, allow retry |
| Worker Error | CSG operation failed | Display error message (NO fallback) |
| Server Error | Backend exception | Display error message |
| Timeout | Operation took too long | Display error message (NO fallback) |

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
// NO FALLBACK - errors are displayed to the user
async function handleGenerationError(error) {
    console.error('Generation error:', error);

    // Show error message - NO fallback to server or alternative worker
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
| Standard CSG Worker | `static/workers/csg-worker.js` | CSG for flat cards (three-bvh-csg) |
| Manifold CSG Worker | `static/workers/csg-worker-manifold.js` | CSG for cylinders (Manifold WASM, guarantees manifold) |
| Three.js | `static/three.module.js` | 3D library |
| BVH CSG | `static/vendor/three-bvh-csg/index.module.js` | Boolean operations for standard worker |
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
| 1.1 | 2024-12-08 | **BUG FIX:** CSG worker integration. Frontend now properly initializes CSG worker and uses client-side generation exclusively. Server-side fallback disabled. Updated Sections 1, 2, and 9. |
| 1.2 | 2024-12-08 | **BUG FIX:** Manifold worker integration. Cylinders now use `csg-worker-manifold.js` for guaranteed manifold output. Added dual-worker architecture with automatic shape-based routing. |
| 1.3 | 2024-12-08 | **NO FALLBACK ENFORCEMENT:** Removed fallback from Manifold to standard worker for cylinders. Cylinder generation now requires Manifold worker; displays error if unavailable. Updated Sections 9 and 12. |

---

## Related Specifications

- [UI_INTERFACE_CORE_SPECIFICATIONS.md](./UI_INTERFACE_CORE_SPECIFICATIONS.md) — Button styling and states
- [BRAILLE_DOT_SHAPE_SPECIFICATIONS.md](./BRAILLE_DOT_SHAPE_SPECIFICATIONS.md) — Dot geometry details
- [RECESS_INDICATOR_SPECIFICATIONS.md](./RECESS_INDICATOR_SPECIFICATIONS.md) — Marker specifications
- [BRAILLE_SPACING_SPECIFICATIONS.md](./BRAILLE_SPACING_SPECIFICATIONS.md) — Layout calculations
- [LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md](./LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md) — Translation system
