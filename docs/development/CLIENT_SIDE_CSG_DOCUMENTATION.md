# Client-Side CSG Architecture Documentation

## Overview

This application uses **client-side CSG (Constructive Solid Geometry)** as the **exclusive method** for generating braille STL files. A **dual-worker architecture** is employed:

- **Standard Worker** (`csg-worker.js`): Uses `three-bvh-csg` for flat cards - fast but may produce non-manifold edges on complex geometry
- **Manifold Worker** (`csg-worker-manifold.js`): Uses Manifold WASM for cylinders - guarantees watertight/manifold output

> **BUG FIX (2024-12-08):** Prior to this fix, the CSG worker existed but was never integrated into the frontend. The code incorrectly went directly to the server-side `/generate_braille_stl` endpoint. This has been corrected - the frontend now properly initializes the CSG worker and uses client-side generation exclusively. Server-side fallback has been intentionally disabled to ensure the correct generation path is always used.

> **MANIFOLD INTEGRATION (2024-12-08):** The Manifold worker (`csg-worker-manifold.js`) existed but was never integrated. This has been fixed - cylinder generation now automatically uses the Manifold worker, guaranteeing zero non-manifold edges. See `MANIFOLD_CYLINDER_FIX.md` for details.

## Why Client-Side CSG?

### Vercel Hobby Tier Compatibility
- **No timeout limits**: Vercel Hobby has 10-60 second limits on serverless functions
- **No cold start delays**: Processing happens immediately in the browser
- **No external dependencies**: Doesn't require Blender, OpenSCAD, or manifold3d binaries on the server
- **Reduced server load**: Server only provides geometry specifications, not full STL files
- **Better scalability**: Each client does their own rendering work

### Performance
- **Fast enough**: Typical braille card (50-100 dots) generates in 5-15 seconds
- **Predictable**: No variability from serverless cold starts or function reuse
- **Progressive**: User sees progress in browser console

### Bundle Size
- **Minimal impact**: Adds ~215-295 KB minified (~60-80 KB gzipped)
- **Cacheable**: Client downloads libraries once, reuses across sessions
- **Already have Three.js**: Most dependencies are the existing three.module.js

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  public/index.html (Main App)                              │ │
│  │  - Collects user input                                     │ │
│  │  - Translates text to braille via liblouis                │ │
│  │  - Requests geometry spec from server                     │ │
│  │  - Selects worker based on shape_type                     │ │
│  │  - Receives STL, renders preview, offers download         │ │
│  └─────────────┬──────────────────────────────────────────────┘ │
│                │                                                 │
│       ┌────────┴────────┐                                       │
│       │  Worker Select  │                                       │
│       │  (shape_type)   │                                       │
│       └────────┬────────┘                                       │
│          ┌─────┴─────┐                                          │
│          │           │                                          │
│          ▼           ▼                                          │
│  ┌───────────────┐  ┌────────────────────┐                     │
│  │ csg-worker.js │  │ csg-worker-        │                     │
│  │ (cards)       │  │ manifold.js        │                     │
│  │               │  │ (cylinders)        │                     │
│  │ three-bvh-csg │  │ Manifold WASM      │                     │
│  │ Fast, ~200KB  │  │ Watertight, ~2.5MB │                     │
│  └───────┬───────┘  └─────────┬──────────┘                     │
│          │                    │                                 │
│          └────────┬───────────┘                                 │
│                   ▼                                             │
│           ┌──────────────┐                                      │
│           │  STL Binary  │                                      │
│           │  + Geometry  │                                      │
│           └──────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                 │
         ┌───────▼────────────────────────────────────────┐
         │  Vercel Backend (Python Flask)                 │
         │  ┌──────────────────────────────────────────┐  │
         │  │  POST /geometry_spec                     │  │
         │  │  - Receives braille text + settings      │  │
         │  │  - Computes dot positions                │  │
         │  │  - Returns JSON spec (no booleans)       │  │
         │  └──────────────────────────────────────────┘  │
         │  ┌──────────────────────────────────────────┐  │
         │  │  POST /generate_braille_stl (DISABLED)   │  │
         │  │  - Server-side fallback REMOVED          │  │
         │  │  - Endpoint exists but not used by UI    │  │
         │  └──────────────────────────────────────────┘  │
         └────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Braille translation (client-side liblouis)
2. **Translated text + settings** → POST /geometry_spec → **JSON spec**
3. **JSON spec** → CSG Worker → **STL ArrayBuffer + Geometry**
4. **STL** → Blob URL → Three.js preview + download link
5. **On error** → Display error message (NO server fallback)

### Geometry Spec Format

The `/geometry_spec` endpoint returns JSON describing primitives:

```json
{
  "shape_type": "card",
  "plate_type": "positive",
  "plate": {
    "width": 85.0,
    "height": 54.0,
    "thickness": 2.0,
    "center_x": 42.5,
    "center_y": 27.0,
    "center_z": 1.0
  },
  "dots": [
    {
      "type": "standard",
      "x": 10.0,
      "y": 40.0,
      "z": 2.0,
      "params": {
        "base_radius": 0.75,
        "top_radius": 0.5,
        "height": 0.5
      }
    },
    {
      "type": "rounded",
      "x": 15.0,
      "y": 40.0,
      "z": 2.0,
      "params": {
        "base_radius": 1.0,
        "top_radius": 0.75,
        "base_height": 0.2,
        "dome_height": 0.6,
        "dome_radius": 1.2
      }
    }
  ],
  "markers": [
    {
      "type": "triangle",
      "x": 5.0,
      "y": 40.0,
      "z": 2.0,
      "size": 2.5,
      "depth": 0.5
    },
    {
      "type": "rect",
      "x": 7.0,
      "y": 40.0,
      "z": 2.0,
      "width": 2.5,
      "height": 5.0,
      "depth": 0.5
    }
  ]
}
```

## Files Added/Modified

### New Files
- `static/vendor/three-bvh-csg/index.module.js` - CSG library (vendored from npm)
- `static/vendor/three-bvh-csg/index.module.js.map` - Source map
- `static/vendor/three-mesh-bvh/index.module.js` - BVH library (vendored from npm)
- `static/vendor/three-mesh-bvh/index.module.js.map` - Source map
- `static/examples/STLExporter.js` - STL exporter from three.js
- `static/workers/csg-worker.js` - Web Worker for CSG operations
- `app/geometry_spec.py` - Geometry spec extraction logic
- `CLIENT_SIDE_CSG_DOCUMENTATION.md` - This file
- `CLIENT_SIDE_CSG_TEST_PLAN.md` - Testing guide

### Modified Files
- `backend.py` - Added `/geometry_spec` endpoint
- `public/index.html` - Added CSG worker initialization (no fallback between workers)

## Configuration

### No Fallback Mode (Current Implementation)

As of the 2024-12-08 bug fix, client-side CSG is the **exclusive** STL generation method. There is no automatic fallback to server-side generation. This ensures:

1. The correct generation path is always used
2. Bugs in the client-side path are surfaced immediately (not hidden by fallback)
3. Consistent behavior across all users and browsers

### Error Conditions

If CSG generation fails, users will see an error message. Common causes:
1. Web Workers not supported by browser
2. Worker initialization fails
3. Module worker imports fail (Safari < 15, older browsers)
4. `/geometry_spec` fetch fails or returns error
5. CSG worker throws error during generation
6. Worker timeout (2 minute limit)

### Browser Requirements

For STL generation to work, the browser must support:
- ES6 Modules
- Module Workers (`new Worker(url, { type: 'module' })`)
- Modern JavaScript (async/await, Promises)

**Supported browsers**: Chrome 80+, Edge 80+, Firefox 114+, Safari 15+

## Browser Compatibility

### Fully Supported (Client-Side CSG)
- ✅ Chrome 80+ (Desktop & Android)
- ✅ Edge 80+
- ✅ Firefox 114+ (Module workers stable)
- ✅ Safari 15+ (Module workers supported)

### Not Supported (Will Show Error)
- ❌ Safari < 15 (no module workers)
- ❌ Firefox < 114 (module worker bugs)
- ❌ IE 11, older mobile browsers
- ❌ Any browser with JavaScript disabled

> **Note:** Server-side fallback has been intentionally disabled. Users on unsupported browsers will see an error message asking them to use a modern browser.

## Performance Characteristics

### Client-Side CSG
| Model Size | Dots | Time (typical) | Browser Load |
|------------|------|----------------|--------------|
| Small      | 10-20 | 2-5 seconds   | Low |
| Medium     | 50-100 | 5-15 seconds  | Medium |
| Large      | 200-300 | 15-45 seconds | High |
| Very Large | 500+ | 45-120 seconds | Very High (may fail) |

### Memory Usage
- Small models: ~50-100 MB
- Medium models: ~100-200 MB
- Large models: ~200-500 MB
- **Browser limit**: ~500 MB - 2 GB depending on browser/device

### Server Fallback (DISABLED)
Server-side fallback has been intentionally disabled as of 2024-12-08.
- The `/generate_braille_stl` endpoint still exists but is not used by the frontend
- All STL generation uses client-side CSG exclusively
- This ensures consistent behavior and surfaces bugs immediately

## Debugging

### Enable Debug Logging

Browser console:
```javascript
// Check worker status
console.log('CSG Worker ready:', csgWorkerReady);

// Check if worker object exists
console.log('CSG Worker:', csgWorker);
```

### Console Messages

**Successful initialization:**
```
Initializing CSG worker...
CSG Worker file is accessible
CSG Worker initialized and ready
CSG Worker ready for client-side STL generation
```

**Successful generation:**
```
Starting client-side CSG generation...
Fetching geometry specification from /geometry_spec...
Received geometry specification: {...}
Geometry spec contains: X dots, Y markers
Sending geometry spec to CSG worker...
CSG Worker completed successfully
Client-side CSG generation complete: filename.stl
```

**On error (no fallback):**
```
Client-side CSG generation failed: [error message]
STL generation failed: [error message]
```

### Common Issues

**Worker fails to initialize:**
- Check browser supports module workers
- Check CORS (all files served from same origin)
- Check files exist: `/static/workers/csg-worker.js`, `/static/vendor/...`

**Geometry spec fails:**
- Check backend endpoint is running: `POST /geometry_spec`
- Check request payload matches expected format
- Check backend logs for Python errors

**CSG operation fails:**
- Check browser memory (Task Manager / Activity Monitor)
- Try smaller model
- Check browser console for detailed error

**Generated STL is invalid:**
- Check watertightness in slicer
- For cylinders, verify Manifold worker initialized successfully
- Report geometry edge cases

## Deployment to Vercel

### No Special Configuration Required

The client-side approach works out-of-the-box on Vercel Hobby:
- Static files in `static/` are served via CDN
- `/geometry_spec` endpoint is a lightweight serverless function
- No WASM configuration needed (pure JS)
- No file tracing configuration needed

### Existing Vercel Config

`vercel.json` remains unchanged:
```json
{
  "version": 2,
  "builds": [
    { "src": "public/index.html", "use": "@vercel/static" },
    { "src": "wsgi.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "^/$", "dest": "/public/index.html" },
    { "src": "^/index.html$", "dest": "/public/index.html" },
    { "src": "/(.*)", "dest": "/wsgi.py" }
  ]
}
```

### Cache Behavior

**Counter plates** (negative) continue to use Vercel Blob caching:
- First request: generates and uploads to Blob storage
- Subsequent requests: redirect to cached Blob URL
- Client-side generation doesn't interfere with this

**Positive plates** are not cached (text-dependent)

## Maintenance

### Updating three-bvh-csg

```bash
npm install three-bvh-csg@latest three-mesh-bvh@latest
Copy-Item node_modules\three-bvh-csg\build\index.module.js static\vendor\three-bvh-csg\ -Force
Copy-Item node_modules\three-mesh-bvh\build\index.module.js static\vendor\three-mesh-bvh\ -Force
```

### Updating Three.js

When updating `static/three.module.js`, also update `static/examples/STLExporter.js`:
```bash
Copy-Item node_modules\three\examples\jsm\exporters\STLExporter.js static\examples\ -Force
```

## Comparison to Alternatives

### vs. Server-Side manifold3d
| Factor | Client-Side three-bvh-csg | Server manifold3d |
|--------|---------------------------|-------------------|
| Vercel Hobby timeout | ✅ No limit | ❌ 10-60 seconds |
| Performance | ~10-30s typical | ~5-15s typical |
| Robustness | Good for clean geometry | Excellent (guaranteed manifold) |
| Setup complexity | ✅ None | ❌ Wheel availability, dependencies |
| Memory | Browser limit (~500MB-2GB) | Serverless limit (2GB) |
| Cost | ✅ Free (client CPU) | Vercel function time charges |

### vs. Client-Side manifold3d (WASM)
| Factor | three-bvh-csg | manifold3d |
|--------|---------------|------------|
| Bundle size | ~215 KB | ~2-3 MB |
| Browser support | ✅ Excellent | Good (WASM required) |
| Memory management | ✅ Automatic (GC) | ❌ Manual (`delete()` calls) |
| Performance | Good | ✅ Excellent |
| Setup | ✅ Simple | Complex (WASM config) |

## Future Enhancements (Optional)

**COMPLETED (2024-12-08):** The Manifold worker has been fully integrated:
- Manifold WASM loads from CDN (`manifold-3d@2.5.1`)
- `static/workers/csg-worker-manifold.js` handles cylinder generation
- **No fallback**: Cylinders MUST use Manifold worker; cards use standard worker
- See `MANIFOLD_CYLINDER_FIX.md` for details

## Support & Troubleshooting

### User Can't Generate STL
1. Check browser console for errors
2. Try with `useClientSideCSG = false` in console
3. Refresh page and retry
4. Check internet connection (for spec fetch)
5. Try smaller model

### STL is Invalid
1. Open in slicer, check for errors
2. Compare with server-generated version
3. Report geometry edge case

### Slow Performance
1. Check browser task manager (memory usage)
2. Close other tabs
3. Try smaller model (reduce text length or line count)
4. Refresh page and ensure workers initialize properly

### Worker Not Initializing
1. Check browser version (need module worker support)
2. Check CORS errors in console
3. Verify files exist in `static/vendor/` and `static/workers/`
4. Try hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
