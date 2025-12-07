# Client-Side CSG Architecture Documentation

## Overview

This application now uses **client-side CSG (Constructive Solid Geometry)** as the primary method for generating braille STL files. The boolean operations (unions and subtractions) are performed in the browser using `three-bvh-csg`, with automatic fallback to server-side generation when needed.

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
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  public/index.html (Main App)                          │ │
│  │  - Collects user input                                 │ │
│  │  - Translates text to braille via liblouis            │ │
│  │  - Requests geometry spec from server                 │ │
│  │  - Sends spec to CSG Worker                           │ │
│  │  - Receives STL, renders preview, offers download     │ │
│  └─────────────┬──────────────────────────────────────────┘ │
│                │                                             │
│         ┌──────▼──────┐            ┌──────────────────┐    │
│         │ CSG Worker  │            │  Three.js        │    │
│         │  (Module)   │◄───────────┤  STLExporter     │    │
│         │             │            │  three-bvh-csg   │    │
│         │ Builds 3D   │            │  three-mesh-bvh  │    │
│         │ primitives  │            └──────────────────┘    │
│         │ Performs    │                                     │
│         │ CSG ops     │                                     │
│         │ Exports STL │                                     │
│         └──────┬──────┘                                     │
│                │                                             │
└────────────────┼─────────────────────────────────────────────┘
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
         │  │  POST /generate_braille_stl (FALLBACK)   │  │
         │  │  - Full server-side generation           │  │
         │  │  - Used when client-side fails           │  │
         │  └──────────────────────────────────────────┘  │
         └────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Braille translation (client-side liblouis)
2. **Translated text + settings** → POST /geometry_spec → **JSON spec**
3. **JSON spec** → CSG Worker → **STL ArrayBuffer + Geometry**
4. **STL** → Blob URL → Three.js preview + download link
5. **On error** → Fallback to POST /generate_braille_stl

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
- `public/index.html` - Added CSG worker initialization and fallback logic

## Configuration

### Feature Flag

In `public/index.html` (around line 2417):

```javascript
let useClientSideCSG = true; // Set to false to force server-side generation
```

To **disable client-side CSG** and always use server:
```javascript
let useClientSideCSG = false;
```

### Automatic Fallback Triggers

Client-side CSG automatically falls back to server when:
1. Web Workers not supported by browser
2. Worker initialization fails
3. Module worker imports fail (Safari < 15, older browsers)
4. `/geometry_spec` fetch fails or returns error
5. CSG worker throws error during generation
6. Worker timeout (2 minute limit)

### Manual Server-Side Generation

Users can force server-side generation by:
1. Setting `useClientSideCSG = false` in browser console
2. Refreshing the page after Worker error (auto-disables on error)

## Browser Compatibility

### Fully Supported (Client-Side CSG)
- ✅ Chrome 80+ (Desktop & Android)
- ✅ Edge 80+
- ✅ Firefox 114+ (Module workers stable)
- ✅ Safari 15+ (Module workers supported)

### Fallback to Server (Automatic)
- Safari < 15 (no module workers)
- Firefox < 114 (module worker bugs)
- IE 11, older mobile browsers
- Any browser with JavaScript disabled

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

### Server Fallback
- Vercel Hobby timeout: 10 seconds
- With Fluid Compute: 60-300 seconds
- Medium models: Often hit timeout on Hobby
- Counter plates: Usually cached, instant via CDN

## Debugging

### Enable Debug Logging

Browser console:
```javascript
// Check worker status
console.log('Worker ready:', workerReady);
console.log('Use client-side:', useClientSideCSG);

// Force server fallback
useClientSideCSG = false;
```

### Console Messages

**Successful client-side generation:**
```
CSG Worker initialized and ready
Attempting client-side CSG generation...
Geometry spec received: {...}
Client-side CSG generation successful
Using client-side generated STL
```

**Fallback to server:**
```
Client-side CSG failed: [error message]
Using server-side STL generation
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
- Try server fallback to compare
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

See the `optional-manifold-worker` todo for adding client-side manifold3d as an additional option:
- Add manifold-3d WASM files to `static/vendor/`
- Create `static/workers/csg-worker-manifold.js`
- Add runtime toggle: three-bvh-csg → manifold3d → server fallback
- ~2-3 MB additional bundle, maximum robustness

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
3. Try smaller model
4. Use server fallback for large models

### Worker Not Initializing
1. Check browser version (need module worker support)
2. Check CORS errors in console
3. Verify files exist in `static/vendor/` and `static/workers/`
4. Try hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
