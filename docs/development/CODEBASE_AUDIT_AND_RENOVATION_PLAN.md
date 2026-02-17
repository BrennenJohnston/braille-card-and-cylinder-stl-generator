# Codebase Audit and Renovation Plan

**Created:** 2026-01-05
**Updated:** 2026-01-05
**Purpose:** Comprehensive audit of the Braille STL Generator architecture and renovation plan to remove external dependencies and create a robust, low-maintenance deployment.

**Status:** ✅ **COMPLETED** - Implementation finished

> **Note (2026-01-05):** This plan has been fully implemented. All Redis/Blob storage dependencies have been removed, deprecated endpoints return 410 Gone, and the `app/cache.py` file has been deleted. The application now uses a minimal backend + client-side generation architecture with zero external service dependencies.

---

## Executive Summary

### Root Cause of Deployment Failure

The Vercel deployment is failing due to an **archived Upstash Redis database**. Upstash archives free-tier databases after 14 days of inactivity, causing `redis.exceptions.ConnectionError` on every request.

### Key Finding

**The application already has a fully functional client-side STL generation system.** The Redis and Blob storage systems are legacy components that are no longer necessary for the core functionality. Removing them will:

1. Eliminate the 14-day inactivity failure mode
2. Reduce server-side complexity
3. Remove all external service dependencies
4. Create a zero-maintenance deployment

---

## Part 1: Detailed Logic Map

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BROWSER (Client)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌────────────────────┐    ┌─────────────────────┐  │
│  │  public/         │    │  static/           │    │  Web Workers        │  │
│  │  index.html      │───▶│  liblouis-worker.js│    │                     │  │
│  │                  │    │  (Translation)     │    │  csg-worker.js      │  │
│  │  - Text Input    │    │                    │    │  (Cards - BVH-CSG)  │  │
│  │  - Settings UI   │    │  + liblouis tables │    │                     │  │
│  │  - 3D Preview    │    │  + WASM binaries   │    │  csg-worker-        │  │
│  │  - Download      │    │                    │    │  manifold.js        │  │
│  │                  │    └────────────────────┘    │  (Cylinders-WASM)   │  │
│  └────────┬─────────┘                              └──────────┬──────────┘  │
│           │                                                   │             │
│           │  1. User enters text                             │             │
│           │  2. liblouis translates to braille              │             │
│           │  3. Request /geometry_spec (lightweight JSON)    │             │
│           ▼                                                   │             │
│  ┌──────────────────────────────────────────────────────────┐│             │
│  │  Geometry Spec JSON (from server)                        ││             │
│  │  - Plate dimensions                                      ││             │
│  │  - Dot positions (x, y, z, theta for cylinders)         ││             │
│  │  - Marker positions                                      ││             │
│  │  - Shape parameters                                      ││             │
│  └──────────────────────────────────────────────────────────┘│             │
│           │                                                   │             │
│           │  4. Send spec to CSG worker                      │             │
│           └──────────────────────────────────────────────────▶│             │
│                                                               │             │
│                  5. CSG worker creates 3D mesh               │             │
│                  6. Exports binary STL                       │             │
│                  7. Returns to main thread                   │             │
│                                    │                          │             │
│                                    ▼                          │             │
│                           ┌──────────────────┐               │             │
│                           │  Blob URL        │               │             │
│                           │  Three.js Preview│               │             │
│                           │  Download Link   │               │             │
│                           └──────────────────┘               │             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                      ┌─────────────▼─────────────┐
                      │   Vercel Backend (Flask)   │
                      │                            │
                      │  POST /geometry_spec       │◀── CRITICAL ENDPOINT
                      │  - Receives braille+settings│
                      │  - Computes dot positions  │
                      │  - Returns JSON spec       │
                      │  - NO boolean operations   │
                      │  - NO STL generation       │
                      │  - Fast & lightweight      │
                      │                            │
                      │  GET /liblouis/tables      │◀── Returns available tables
                      │  GET /health               │◀── Health check
                      │  GET /                     │◀── Serves index.html
                      │  GET /static/*             │◀── Serves static files
                      │                            │
                      │  ═══════════════════════   │
                      │  LEGACY (TO BE REMOVED):   │
                      │  ───────────────────────   │
                      │  POST /generate_braille_stl│◀── Uses Redis (broken)
                      │  POST /generate_counter_*  │◀── Uses Redis (broken)
                      │  GET /lookup_stl           │◀── Uses Redis (broken)
                      │  GET /debug/blob_upload    │◀── Debug endpoint
                      │                            │
                      │  UNUSED INTEGRATIONS:      │
                      │  - Upstash Redis           │◀── ARCHIVED (broken)
                      │  - Vercel Blob Storage     │◀── Optional caching
                      │  - Flask-Limiter + Redis   │◀── Fails on archived Redis
                      └────────────────────────────┘
```

### 1.2 Request Flow (Current Working Path)

```
User Input → liblouis Worker → Braille Unicode
                                    │
                                    ▼
                          POST /geometry_spec
                                    │
                                    ▼
                          JSON Geometry Spec
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
               shape_type='card'           shape_type='cylinder'
                    │                               │
                    ▼                               ▼
            csg-worker.js               csg-worker-manifold.js
            (three-bvh-csg)                  (Manifold WASM)
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                          Binary STL + Preview Data
                                    │
                                    ▼
                          Three.js 3D Preview
                          + Download Link
```

### 1.3 Request Flow (Broken Legacy Path - Why It Fails)

```
User Input → liblouis Worker → Braille Unicode
                                    │
                                    ▼
                      POST /generate_braille_stl
                                    │
                      ┌─────────────▼─────────────┐
                      │  Flask-Limiter Rate Check  │
                      │  storage_uri = REDIS_URL   │
                      │           │                │
                      │           ▼                │
                      │  ┌──────────────────────┐ │
                      │  │ Connect to Redis     │ │
                      │  │ enormous-caribou-    │ │
                      │  │ 11905.upstash.io     │ │
                      │  └──────────┬───────────┘ │
                      │             │             │
                      │             ▼             │
                      │  ╔════════════════════╗   │
                      │  ║  CONNECTION ERROR  ║   │
                      │  ║  Error 16: Device  ║   │
                      │  ║  or resource busy  ║   │
                      │  ╚════════════════════╝   │
                      │             │             │
                      │             ▼             │
                      │   500 Internal Server     │
                      │   Error                   │
                      └───────────────────────────┘
```

### 1.4 File Structure Map

```
braille-card-and-cylinder-stl-generator/
├── backend.py                 # Main Flask app (1415 lines)
│   ├── Flask app setup        # Lines 75-169
│   ├── Rate limiter (Redis)   # Lines 147-169 ← PROBLEM
│   ├── Security headers       # Lines 349-395
│   ├── Static file serving    # Lines 503-560
│   ├── /geometry_spec         # Lines 1136-1211 ← WORKING
│   ├── /generate_braille_stl  # Lines 725-1133 ← BROKEN (Redis)
│   └── /generate_counter_*    # Lines 1214-1410 ← BROKEN (Redis)
│
├── wsgi.py                    # Vercel entry point
│   └── manifold3d check       # Lines 35-58 (correctly shows NOT available)
│
├── app/
│   ├── cache.py               # Redis/Blob integration (TO BE REMOVED)
│   ├── geometry_spec.py       # Geometry spec extraction (KEEP)
│   ├── models.py              # Data models (dataclass/Enum) (KEEP)
│   ├── validation.py          # Input validation (KEEP)
│   ├── utils.py               # Utility functions (KEEP)
│   ├── exporters.py           # STL export utilities (KEEP)
│   └── geometry/              # Geometry generation (KEEP)
│       ├── booleans.py        # Boolean backend check
│       ├── braille_layout.py  # Braille layout calculations
│       ├── cylinder.py        # Cylinder generation
│       ├── dot_shapes.py      # Dot shape geometry
│       └── plates.py          # Plate generation
│
├── public/
│   └── index.html             # Main frontend (WORKING)
│
├── static/
│   ├── liblouis-worker.js     # Braille translation worker
│   ├── liblouis/              # liblouis tables
│   ├── workers/
│   │   ├── csg-worker.js          # Card CSG (three-bvh-csg)
│   │   └── csg-worker-manifold.js # Cylinder CSG (Manifold WASM)
│   ├── vendor/                # Vendored libraries
│   └── examples/              # STL exporter
│
├── requirements.txt           # Python dependencies
│   ├── flask, flask-cors      # Core web framework
│   ├── Flask-Limiter          # Rate limiting
│   ├── redis                  # ← REMOVE
│   ├── requests               # ← OPTIONAL (only for blob)
│   ├── numpy, trimesh         # Geometry processing
│   └── shapely, mapbox_earcut # 2D geometry
│
└── vercel.json                # Vercel configuration
```

---

## Part 2: Vercel Deployment Report

### 2.1 Runtime Log Analysis

From the Vercel Runtime Logs (`logs_result.csv`):

**Error Pattern (Every Request):**
```
redis.exceptions.ConnectionError: Error 16 connecting to
enormous-caribou-11905.upstash.io:6379. Device or resource busy.
```

**Root Cause Chain:**
1. `REDIS_URL` environment variable is set to archived Upstash database
2. Flask-Limiter uses `storage_uri=redis_url` (line 148 of backend.py)
3. Every request triggers rate limit check → Redis connection attempt
4. Connection fails → 500 Internal Server Error

**Secondary Observations:**
- `manifold3d IMPORT FAILED (ImportError): No module named 'manifold3d'` — Expected behavior (Vercel doesn't have manifold3d)
- `PRODUCTION_DOMAIN environment variable is NOT set!` — CORS warning
- Boolean backend correctly reports "NOT available"

### 2.2 Environment Variables

| Variable | Status | Purpose |
|----------|--------|---------|
| `REDIS_URL` | SET (broken) | Points to archived Upstash Redis |
| `SECRET_KEY` | ? | Flask session key |
| `PRODUCTION_DOMAIN` | NOT SET | CORS configuration |
| `BLOB_STORE_WRITE_TOKEN` | ? | Vercel Blob upload |
| `BLOB_PUBLIC_BASE_URL` | ? | Blob CDN URL |
| `FLASK_ENV` | ? | Development/production mode |

### 2.3 Why Server-Side STL Generation Would Never Work on Vercel

Even if Redis was working, the `/generate_braille_stl` and `/generate_counter_plate_stl` endpoints would still fail because:

1. **`manifold3d` is not installed** — The package requires native binaries that aren't available on Vercel's Python runtime
2. **`has_boolean_backend()` returns `False`** — The code already returns 503 error before attempting generation
3. **Vercel function timeout** — Even with dependencies, complex STL generation would exceed the 10-60 second limit

**The server-side endpoints are dead code on Vercel.** They exist only for local development.

---

## Part 3: Similar Open-Source Projects

### 3.1 Project Comparison Matrix

| Project | Purpose | Client-Side? | Dependencies | Maintenance |
|---------|---------|--------------|--------------|-------------|
| **This Project** | Braille STL for 3D printing | ✅ Yes (CSG workers) | Redis, Flask, Vercel | High (Redis timeout) |
| **Liblouis** | Braille translation | ✅ WASM available | None | Low (well-maintained) |
| **Three.js + three-bvh-csg** | Browser 3D + CSG | ✅ Pure client | None | Very Low |
| **Manifold3D** | Mesh booleans | ✅ WASM available | CDN load | Very Low |
| **OpenSCAD** | 3D modeling | ❌ Server-side | OpenSCAD binary | High |
| **TouchSee/Treatstock** | Braille labels | ❌ Server-side | Server infrastructure | High (commercial) |
| **BrailleRap** | Hardware embosser | ❌ Hardware-focused | Hardware | High |

### 3.2 Best Practices from Similar Projects

**From Static Site Generators (GitHub Pages, Netlify):**
- Zero server dependencies = zero maintenance
- CDN-served static files with infinite scaling
- All computation happens in browser

**From Browser-Based CAD Tools (OpenJSCAD, CascadeStudio):**
- Web Workers for heavy computation
- WASM for performance-critical code
- Progressive loading of large assets

**From Production Three.js Applications:**
- Lazy loading of WASM modules
- Graceful degradation for older browsers
- No server-side rendering needed

---

## Part 4: Renovation Plan

### 4.1 Strategy: "Static-First" Architecture

Transform the application from a Flask+Redis deployment to a **static web application** with a minimal API backend.

**Before (Current):**
```
┌─────────────────────────────────────────────────┐
│                 Vercel                           │
│  ┌──────────────────────────────────────────┐   │
│  │  Flask App (Python)                      │   │
│  │  + Redis (Upstash)                       │   │
│  │  + Blob Storage                          │   │
│  │  + Rate Limiting                         │   │
│  │  + STL Generation (broken)               │   │
│  │  + Geometry Spec                         │   │
│  │  + Static Files                          │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**After (Renovated):**
```
┌─────────────────────────────────────────────────┐
│                 Vercel                           │
│  ┌──────────────────────────────────────────┐   │
│  │  Static Files (CDN Edge)                 │   │
│  │  - public/index.html                     │   │
│  │  - static/workers/*.js                   │   │
│  │  - static/liblouis/*                     │   │
│  │  - static/vendor/*                       │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Flask API (Minimal, Stateless)          │   │
│  │  - GET /liblouis/tables                  │   │
│  │  - POST /geometry_spec                   │   │
│  │  - GET /health                           │   │
│  │  (No Redis, No Blob, No Rate Limits)     │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 4.2 Implementation Phases

#### Phase 1: Emergency Fix (Immediate)
**Goal:** Restore deployment functionality within 1 hour

1. **Remove/Unset `REDIS_URL` environment variable from Vercel**
   - This will make Flask-Limiter fall back to `memory://` storage
   - Rate limiting will still work (per-instance, not global)

2. **Verify `/geometry_spec` endpoint works**
   - This is the only endpoint the frontend actually uses
   - Should work immediately after Redis URL is removed

#### Phase 2: Code Cleanup (Short-term)
**Goal:** Remove all dead/broken code

**Files to Modify:**

1. **`backend.py`** — Remove Redis dependencies:
   - Remove imports from `app.cache`
   - Remove blob cache logic from `/generate_braille_stl`
   - Remove blob cache logic from `/generate_counter_plate_stl`
   - Keep these endpoints for local development but mark as dev-only
   - Remove `/lookup_stl` endpoint
   - Remove `/debug/blob_upload` endpoint

2. **`app/cache.py`** — ✅ DELETED:
   - This entire module was for Redis/Blob integration
   - Has been removed from the codebase

3. **`requirements.txt`** — Simplify dependencies:
   ```
   # Remove these:
   redis==5.0.7
   requests==2.32.3  # Only needed for Blob upload

   # Keep these:
   flask==2.3.3
   flask-cors==4.0.0
   Flask-Limiter==3.8.0  # Works without Redis (uses memory)
   numpy==1.26.4
   trimesh==4.5.3
   shapely==2.0.6
   mapbox_earcut==1.0.2
   ```

#### Phase 3: Architecture Hardening (Medium-term)
**Goal:** Make the application truly low-maintenance

1. **Remove Flask-Limiter dependency entirely**
   - For a client-side app, rate limiting on `/geometry_spec` is unnecessary
   - The endpoint just returns JSON with calculated positions
   - Vercel's edge network provides DDoS protection

2. **Consider static-only deployment**
   - Move `/liblouis/tables` to a static JSON file
   - Move `/geometry_spec` logic to client-side JavaScript
   - This would eliminate the Flask backend entirely

3. **Add offline support**
   - Service Worker for offline functionality
   - Cache liblouis tables in IndexedDB
   - Full PWA capabilities

#### Phase 4: Optional Enhancements (Long-term)
**Goal:** Improve user experience

1. **Precomputed liblouis table metadata**
   - Generate `tables.json` at build time
   - Serve statically instead of scanning at runtime

2. **Client-side geometry spec calculation**
   - Port `app/geometry_spec.py` to JavaScript
   - Eliminates need for backend entirely
   - Pure static deployment possible

3. **Progressive Web App features**
   - Installable on mobile devices
   - Offline-capable
   - Push notifications for updates

4. **Vercel Edge Middleware for Rate Limiting** (if extra protection desired)
   - Runs at edge before Python function
   - No Redis required
   - Simple in-memory or Vercel KV-backed

   **Implementation:**
   ```javascript
   // middleware.js at project root
   import { NextResponse } from 'next/server';

   const rateLimit = new Map();

   export function middleware(request) {
     if (request.nextUrl.pathname === '/geometry_spec') {
       const ip = request.ip ?? 'unknown';
       const now = Date.now();
       const windowMs = 60 * 1000;
       const maxRequests = 10;

       const requests = (rateLimit.get(ip) || []).filter(t => now - t < windowMs);
       if (requests.length >= maxRequests) {
         return new NextResponse(
           JSON.stringify({ error: 'Rate limit exceeded' }),
           { status: 429, headers: { 'Content-Type': 'application/json' } }
         );
       }
       requests.push(now);
       rateLimit.set(ip, requests);
     }
     return NextResponse.next();
   }

   export const config = {
     matcher: ['/geometry_spec'],
   };
   ```

   **When to implement:** Only if abuse patterns observed in Vercel logs. Default Vercel protections are likely sufficient.

---

## Part 5: Recommended Implementation

### 5.1 Immediate Action (Fix Broken Deployment)

**Step 1: Remove REDIS_URL from Vercel Environment Variables**

1. Go to Vercel Dashboard → Project Settings → Environment Variables
2. Delete or unset `REDIS_URL`
3. Redeploy

This single change will:
- Make Flask-Limiter use memory storage (per-instance, which is fine for this use case)
- Eliminate all Redis connection errors
- Restore `/geometry_spec` endpoint functionality
- Restore the entire application

**Step 2: Verify Deployment**

1. Visit the deployed URL
2. Enter text in the input field
3. Click "Generate"
4. Verify STL downloads correctly

### 5.2 Recommended Code Changes

**Minimal Fix (backend.py lines 147-148):**

```python
# Before:
redis_url = os.environ.get('REDIS_URL')
storage_uri = redis_url if redis_url else 'memory://'

# After (force memory storage, ignore REDIS_URL):
storage_uri = 'memory://'  # Redis removed - using in-memory rate limiting
```

This ensures the app works even if someone accidentally sets `REDIS_URL`.

### 5.3 Environment Variables to Set

| Variable | Value | Purpose |
|----------|-------|---------|
| `SECRET_KEY` | (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) | Flask session security |
| `PRODUCTION_DOMAIN` | Your Vercel domain (e.g., `https://your-app.vercel.app`) | CORS configuration |
| `FLASK_ENV` | `production` | Disable debug mode |

**Variables to REMOVE:**
- `REDIS_URL` — Causes connection failures
- `BLOB_STORE_WRITE_TOKEN` — Not needed for client-side generation
- `BLOB_PUBLIC_BASE_URL` — Not needed
- `BLOB_READ_WRITE_TOKEN` — Not needed
- `BLOB_DIRECT_UPLOAD_URL` — Not needed
- `BLOB_API_BASE_URL` — Not needed

---

## Part 6: Pros and Cons

### 6.1 Removing Redis (Recommended)

**Pros:**
- ✅ Eliminates 14-day inactivity failure mode
- ✅ Removes external service dependency
- ✅ Simplifies deployment (no environment variables needed)
- ✅ Reduces code complexity
- ✅ No cost for external services
- ✅ Faster startup (no Redis connection)

**Cons:**
- ⚠️ Rate limiting becomes per-instance instead of global
  - *Mitigation: Vercel's edge protection handles abuse*
- ⚠️ No cached counter plates across users
  - *Mitigation: Counter plates generate in <15 seconds client-side*

### 6.2 Moving to Fully Static Deployment

**Pros:**
- ✅ Zero maintenance (no server code to break)
- ✅ Infinite scaling (CDN edge)
- ✅ Faster load times
- ✅ Can host on GitHub Pages, Netlify, any static host
- ✅ No function invocation costs

**Cons:**
- ⚠️ Requires porting `/geometry_spec` to JavaScript
  - *Effort: ~2-4 hours for experienced developer*
- ⚠️ Larger initial download (liblouis tables)
  - *Mitigation: Lazy load tables on demand*

### 6.3 Keeping Server-Side Generation (Not Recommended)

**Pros:**
- ✅ Works in older browsers without Web Workers
- ✅ Could support very large models

**Cons:**
- ❌ Requires `manifold3d` which isn't available on Vercel
- ❌ Would require alternative hosting (AWS, DigitalOcean)
- ❌ Higher hosting costs
- ❌ More maintenance burden
- ❌ Function timeout limits

---

## Part 7: Implementation Checklist

### Immediate (Today)

- [ ] Remove `REDIS_URL` from Vercel environment variables
- [ ] Verify deployment works after removal
- [ ] Test STL generation end-to-end

### Short-term (This Week)

- [ ] Update `backend.py` to force `memory://` storage
- [ ] Remove unused imports from `app.cache`
- [ ] Remove `/lookup_stl` endpoint
- [ ] Remove `/debug/blob_upload` endpoint
- [ ] Update `requirements.txt` to remove `redis` and `requests`
- [ ] Set `SECRET_KEY` and `PRODUCTION_DOMAIN` in Vercel

### Medium-term (This Month)

- [ ] Remove Flask-Limiter entirely (optional)
- [ ] Generate static `tables.json` for liblouis tables
- [ ] Archive or delete `app/cache.py`
- [ ] Update documentation to reflect new architecture
- [ ] Add health check monitoring

### Long-term (Future)

- [ ] Consider porting `/geometry_spec` to client-side JavaScript
- [ ] Add Service Worker for offline support
- [ ] Implement PWA features

---

## Appendix A: Runtime Log Errors

### Error 1: Redis Connection Failure

```
File "/var/task/backend.py", line 827, in _blob_url_cache_get
    mapped_url = _blob_url_cache_get(early_cache_key)
  File "/var/task/app/cache.py", line 75, in _blob_url_cache_get
    rc = _get_redis_client()
  ...
redis.exceptions.ConnectionError: Error 16 connecting to
enormous-caribou-11905.upstash.io:6379. Device or resource busy.
```

**Cause:** Upstash Redis database archived after 14 days of inactivity.

### Error 2: manifold3d Not Available

```
manifold3d IMPORT FAILED (ImportError): No module named 'manifold3d'
manifold3d package is not installed
Boolean backend status: manifold3d=NOT available
```

**Cause:** Expected behavior. `manifold3d` requires native binaries not available on Vercel's Python runtime. This is why client-side CSG was implemented.

### Error 3: CORS Warning

```
CORS: PRODUCTION_DOMAIN environment variable is NOT set!
```

**Cause:** Missing environment variable. Should be set to production domain.

---

## Appendix B: Files to Archive/Delete

> **Note:** These files have been deleted as part of the cleanup.

| File | Status | Reason |
|------|--------|--------|
| `app/cache.py` | ✅ Deleted | Redis/Blob integration no longer needed |
| `Vercel Runtime Logs/` | ✅ Deleted | Diagnostic files, not needed in repo |

These endpoints can be removed from `backend.py`:

| Endpoint | Lines | Reason |
|----------|-------|--------|
| `/lookup_stl` | 187-258 | Redis-dependent, unused by frontend |
| `/debug/blob_upload` | 264-345 | Debug endpoint, dev-only |
| Blob cache logic in `/generate_braille_stl` | 801-841, 927-1130 | Redis-dependent |
| Blob cache logic in `/generate_counter_plate_stl` | 1257-1380 | Redis-dependent |

---

## Appendix C: Testing Checklist

After implementing fixes, verify:

1. **Basic Functionality**
   - [ ] Homepage loads (`/`)
   - [ ] Health check returns ok (`/health`)
   - [ ] Liblouis tables load (`/liblouis/tables`)

2. **Card Generation**
   - [ ] Enter text in Manual mode
   - [ ] Click Generate
   - [ ] 3D preview appears
   - [ ] Download button works
   - [ ] STL file is valid (open in slicer)

3. **Cylinder Generation**
   - [ ] Switch to Cylinder shape
   - [ ] Enter text
   - [ ] Generate and download
   - [ ] Verify manifold output (no mesh errors)

4. **Counter Plate Generation**
   - [ ] Switch to Counter Plate type
   - [ ] Generate for both Card and Cylinder
   - [ ] Verify recesses are correct shape

5. **Edge Cases**
   - [ ] Empty input shows appropriate error
   - [ ] Very long text handles gracefully
   - [ ] Multiple rapid clicks don't cause issues
   - [ ] Works on Chrome, Firefox, Safari, Edge

---

## Document History

| Date | Changes |
|------|---------|
| 2026-01-05 | Initial document created with complete audit and renovation plan |
| 2026-01-05 | Validated and consolidated with implementation plan; confirmed dependency analysis |
| 2026-01-05 | **Final validation**: Fixed pydantic claim (NOT used); added pyproject.toml note |

---

## Validation Notes (2026-01-05)

This audit has been **validated and consolidated** with the implementation plan. Key validations performed:

1. ✅ **Dependency Analysis Confirmed:**
   - `app/geometry_spec.py` uses ONLY standard library (no numpy/trimesh/shapely)
   - Heavy dependencies are ONLY used by server-side STL generation (which doesn't work on Vercel)
   - Minimal backend requires ONLY: Flask, flask-cors (models use stdlib dataclass/Enum, NOT pydantic)

2. ✅ **Strategic Decisions Finalized:**
   - Flask-Limiter: Remove entirely (rate limiting unnecessary for lightweight JSON endpoint)
   - Server-side endpoints: Replace with 410 Gone responses (backward compatibility)
   - Static serving: Keep Python-served routes (liblouis include resolution issues)

3. ✅ **Implementation Plan Ready:**
   - Detailed line numbers for backend.py changes documented
   - Specific requirements.txt removals identified
   - Testing checklist created
   - Risk assessment completed

**Implementation details:** See `backend.py` (deprecated endpoints), `requirements.txt` (minimal Vercel deps), and `requirements-dev.txt` (local dev/test deps).

### Final Validation Corrections (2026-01-05)

| Original Claim | Correction | Evidence |
|----------------|------------|----------|
| Minimal backend needs pydantic | **Pydantic is NOT used** | `app/models.py` uses `dataclass` + `Enum` from stdlib |
| Only requirements.txt listed | Added `pyproject.toml` deps | scipy, matplotlib, manifold3d also need consideration |

### Additional Files Verified

| File | Dependencies | Vercel-Safe? |
|------|-------------|--------------|
| `app/geometry_spec.py` | stdlib only | ✅ Yes |
| `app/models.py` | stdlib only (dataclass, enum) | ✅ Yes |
| `app/utils.py` | stdlib only (logging, os) | ✅ Yes |
| `app/validation.py` | stdlib only (typing) | ✅ Yes |
| `app/cache.py` | redis, requests | ❌ Remove |
| `app/geometry/plates.py` | numpy, trimesh, shapely | ❌ Not for Vercel |
| `app/geometry/cylinder.py` | numpy, trimesh, shapely | ❌ Not for Vercel |

---

*This document serves as the master audit for the Braille STL Generator renovation. The consolidated implementation plan provides actionable steps with specific line numbers and code changes.*
