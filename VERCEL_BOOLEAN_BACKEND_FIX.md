# Vercel Boolean Backend Fix

## Problem

When deployed to Vercel, the application was attempting server-side boolean operations (unions and subtractions) using `manifold3d` and `trimesh`, which are not available on Vercel's serverless platform. This caused:

- 500 Internal Server Errors
- Hundreds of "No backends available for boolean operations!" errors in logs
- Failed STL generation for both positive and negative plates

## Root Cause

The server-side STL generation endpoints (`/generate_braille_stl` and `/generate_counter_plate_stl`) were trying to perform 3D boolean operations even when:
1. `manifold3d` Python package is not installed (requires native binaries)
2. `trimesh` boolean backends (Blender, OpenSCAD) are not available on serverless

This contradicted the **new client-side CSG architecture** which was designed specifically to avoid this problem.

## Solution

### Backend Changes (`backend.py`)

Added boolean backend availability checks to both STL generation endpoints:

```python
from app.geometry.booleans import has_boolean_backend

if not has_boolean_backend():
    return jsonify({
        'error': 'Server-side STL generation requires a modern browser with JavaScript enabled. '
                 'This server does not have 3D boolean operation backends available. '
                 'Please ensure JavaScript is enabled in your browser to use client-side geometry processing.',
        'error_code': 'NO_BOOLEAN_BACKEND',
        'suggestion': 'Use a modern browser (Chrome 80+, Firefox 114+, Safari 15+, or Edge 80+) with JavaScript enabled. '
                      'The application will automatically generate STL files in your browser.'
    }), 503
```

**Affected Endpoints:**
- `POST /generate_braille_stl` - Now returns 503 if no boolean backend
- `POST /generate_counter_plate_stl` - Now returns 503 if no boolean backend

### Frontend Changes (`public/index.html`)

Enhanced error handling to detect `NO_BOOLEAN_BACKEND` error code:

```javascript
if (errorCode === 'NO_BOOLEAN_BACKEND') {
    if (!useClientSideCSG || !workerReady) {
        msg = 'Server cannot generate STL files and client-side generation is not available. Please use a modern browser...';
    } else {
        msg = 'Client-side generation failed and server cannot generate STL files. Please refresh the page and try again.';
    }
}
```

## Architecture Flow (Corrected)

### On Vercel Deployment

```
User clicks "Generate"
  ↓
Frontend attempts client-side CSG
  ├─→ Success: STL generated in browser ✓
  │   └─→ No server boolean operations
  │
  └─→ Failure/Timeout
      ├─→ Falls back to server
      │   └─→ Server checks: has_boolean_backend()?
      │       ├─→ No (on Vercel): Returns 503 + error code
      │       │   └─→ User sees: "Please use modern browser"
      │       │
      │       └─→ Yes (local dev): Generates on server ✓
```

### Expected Behavior on Vercel

1. **Client-side generation works** → User gets STL file (no server involvement)
2. **Client-side fails** → Server returns clear error message (no crash)
3. **User has old browser** → Gets helpful error directing to use modern browser

## What Changed

### Commit 1: `88f8a0a` - Client-Side CSG Implementation
- Added three-bvh-csg libraries
- Created CSG Web Worker
- Added `/geometry_spec` endpoint
- Implemented fallback logic

### Commit 2: `f22f3f2` - Boolean Backend Fix (THIS FIX)
- Prevents server from attempting boolean ops on Vercel
- Returns 503 with clear error code instead of 500
- Enhanced frontend error messages
- Ensures client-side CSG is the primary path

## Testing the Fix

### On Vercel (After Deploy)

1. **Modern Browser (Chrome, Firefox, Safari 15+, Edge)**
   - ✅ Should work: Client-side CSG generates STL
   - ✅ No server errors in logs
   - ✅ Fast generation (no timeouts)

2. **Old Browser or JavaScript Disabled**
   - ✅ Should show clear error: "Please use modern browser with JavaScript"
   - ✅ No 500 errors
   - ✅ No boolean operation attempts in logs

### On Local Development

1. **With manifold3d installed**
   - ✅ Client-side CSG works (primary)
   - ✅ Server fallback works (if client fails)
   - ✅ Both paths functional

2. **Without manifold3d installed**
   - ✅ Client-side CSG works (primary)
   - ⚠️ Server fallback returns 503 error
   - ✅ User gets helpful message

## Verifying the Fix

### Check Logs for Success

**Before fix** (errors):
```
[error] pairwise union failed: No backends available for boolean operations!
[error] pairwise union failed: No backends available for boolean operations!
[error] pairwise union failed: No backends available for boolean operations!
... (hundreds of these)
```

**After fix** (success):
```
[info] CSG Worker initialized and ready
[info] Attempting client-side CSG generation...
[info] Geometry spec received: {...}
[info] Client-side CSG generation successful
```

**After fix** (if client fails):
```
[info] 127.0.0.1 - - [DATE] "POST /generate_braille_stl HTTP/1.1" 503 -
[info] Returned NO_BOOLEAN_BACKEND error to client
```

### Browser Console Check

1. Open browser console (F12)
2. Look for: `"CSG Worker initialized and ready"`
3. Generate STL
4. Look for: `"Attempting client-side CSG generation..."`
5. Should see: `"Client-side CSG generation successful"`

## Troubleshooting

### If Client-Side CSG Fails

**Symptoms:**
- "Client-side generation failed" error
- Falls back to server
- Server returns 503 error

**Possible Causes:**
1. **Worker not loading** - Check Network tab for `/static/workers/csg-worker.js`
2. **Library not loading** - Check for `/static/vendor/three-bvh-csg/` files
3. **Browser compatibility** - Verify Module Worker support
4. **CORS issues** - Check all files served from same origin

**Fix:**
1. Clear browser cache (Ctrl+Shift+R / Cmd+Shift+R)
2. Check browser console for specific errors
3. Verify files exist on server
4. Try different browser

### If You See 503 Errors

**This is expected behavior on Vercel when:**
- Client-side CSG fails
- JavaScript is disabled
- Browser doesn't support Module Workers

**This is the CORRECT behavior** - it prevents server crashes and guides users to use client-side generation.

## Configuration

### Force Server-Side Generation (Not Recommended on Vercel)

In `public/index.html` (line ~2417):
```javascript
let useClientSideCSG = false; // Forces server-side
```

⚠️ **Do not use on Vercel** - will always fail with 503 error.

### Allow Server-Side on Local Dev

Ensure `manifold3d` is installed:
```bash
pip install manifold3d
```

Or rely on trimesh with Blender/OpenSCAD installed.

## Summary

✅ **Fixed**: Server no longer attempts boolean operations on Vercel without backends
✅ **Fixed**: Clear error messages instead of cryptic 500 errors
✅ **Improved**: Users get helpful guidance for browser requirements
✅ **Ensured**: Client-side CSG is the primary (and only viable) path on Vercel

**Result**: Application now works correctly on Vercel's free tier without boolean backend dependencies.
