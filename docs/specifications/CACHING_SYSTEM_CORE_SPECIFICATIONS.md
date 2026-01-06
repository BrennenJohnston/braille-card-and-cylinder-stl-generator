# Caching System Core Specifications

---

## ⚠️ DEPRECATION NOTICE (2026-01-05)

**This caching system has been REMOVED from the application.**

### Why It Was Removed

1. **Root Cause of Deployment Failures:** Upstash Redis archives free-tier databases after 14 days of inactivity, causing `redis.exceptions.ConnectionError` on ALL requests (Error 16: Device or resource busy).

2. **Server-Side Generation Not Available on Vercel:** The `/generate_braille_stl` and `/generate_counter_plate_stl` endpoints cannot work on Vercel because `manifold3d` requires native binaries not available in Vercel's Python runtime.

3. **Client-Side Generation is Sufficient:** The application's client-side CSG system (BVH-CSG for cards, Manifold WASM for cylinders) generates STL files quickly enough that caching is unnecessary.

4. **Zero Maintenance Architecture:** Removing Redis and Blob storage eliminates all external service dependencies, creating a deployment that cannot fail due to inactivity.

### Current Architecture (2026-01-05)

**Minimal Backend + Client-Side Generation:**
- Flask backend provides lightweight JSON geometry specifications (`/geometry_spec`)
- No Redis, no Blob storage, no rate limiting infrastructure
- All STL generation happens client-side using Web Workers
- Zero external service dependencies
- No 14-day inactivity failure mode

**For implementation details, see:**
- [Codebase Audit and Renovation Plan](../development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md)

### What Was Removed

- `app/cache.py` - Deleted (caching logic no longer needed)
- Redis integration removed from `backend.py`
- Blob storage integration removed from `backend.py`
- Flask-Limiter removed entirely

### Document Status

**This document is ARCHIVED for historical reference only.** The caching system described below is no longer implemented in the application.

---

## Historical Document Purpose (Pre-2026-01-05)

This document provides **comprehensive, in-depth specifications** for the caching system that **was** used to enable efficient STL generation and delivery on serverless platforms (Vercel). It serves as an historical reference by documenting:

1. **Architecture Overview** — Content-addressable caching with Vercel Blob storage
2. **Cache Key Generation** — Deterministic hashing for geometry-based cache lookups
3. **Redis Integration** — URL mapping and cache metadata storage
4. **Vercel Blob Storage** — STL file upload, retrieval, and public URL management
5. **Counter Plate Caching Strategy** — Why and how counter plates are aggressively cached
6. **Cache Flow Diagrams** — Complete request/response flows for cache hits and misses
7. **Environment Configuration** — Required environment variables and their purposes

**Note:** The original source files for the caching system have been removed. This document serves as historical reference only.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Cache Key Generation](#2-cache-key-generation)
3. [Redis Integration](#3-redis-integration)
4. [Vercel Blob Storage](#4-vercel-blob-storage)
5. [Counter Plate Caching Strategy](#5-counter-plate-caching-strategy)
6. [Cache Flow: Request Lifecycle](#6-cache-flow-request-lifecycle)
7. [Environment Variables](#7-environment-variables)
8. [API Endpoints with Caching](#8-api-endpoints-with-caching)
9. [Cache Invalidation and TTL](#9-cache-invalidation-and-ttl)
10. [Error Handling and Fallbacks](#10-error-handling-and-fallbacks)
11. [Performance Characteristics](#11-performance-characteristics)
12. [Implementation Details](#12-implementation-details)

---

## 1. Architecture Overview

### Design Philosophy

The caching system implements **content-addressable storage** where:

1. **Cache keys are deterministic** — Same geometry parameters always produce same key
2. **Counter plates are heavily cached** — Universal counter plates depend only on grid settings
3. **Positive plates use client-side generation** — No caching needed for emboss plates
4. **Two-tier storage** — Redis for URL lookups, Vercel Blob for actual STL files

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       REQUEST: Generate Counter Plate                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CACHE KEY GENERATION                                │
│  • Normalize settings (round floats, convert strings to numbers)            │
│  • Select geometry-affecting parameters only                                │
│  • Generate canonical JSON representation                                   │
│  • Compute SHA-256 hash (32-char hex)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            REDIS LOOKUP                                      │
│  • Query: GET "blob-url:{cache_key}"                                        │
│  • Returns: Blob URL string or empty                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              [URL Found]                          [URL Not Found]
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────┐     ┌─────────────────────────────────────┐
│   VERIFY BLOB EXISTS           │     │   GENERATE STL                     │
│   • HTTP HEAD request          │     │   • Create trimesh geometry        │
│   • Fallback: Range GET        │     │   • Export to binary STL           │
│   • Check 2xx status           │     └───────────────┬─────────────────────┘
└──────────────┬────────────────┘                     │
               │                                       ▼
         [Blob Exists]                    ┌───────────────────────────────────┐
               │                          │   UPLOAD TO VERCEL BLOB            │
               │                          │   • PUT with deterministic path    │
               │                          │   • Set public access              │
               │                          │   • Return public URL              │
               │                          └───────────────┬───────────────────┘
               │                                          │
               │                                          ▼
               │                          ┌───────────────────────────────────┐
               │                          │   STORE URL IN REDIS               │
               │                          │   • SET "blob-url:{key}" = URL     │
               │                          │   • TTL = 31536000 (1 year)        │
               │                          └───────────────┬───────────────────┘
               │                                          │
               └──────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RETURN 302 REDIRECT TO BLOB URL                         │
│  Location: https://{store}.public.blob.vercel-storage.com/stl/{key}.stl    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Benefits

|| Benefit | Impact |
||---------|--------|
|| **Content-Addressable** | Identical geometry = automatic deduplication |
|| **Serverless-Friendly** | No local filesystem, no server state |
|| **Global CDN** | Vercel Blob uses edge network for fast delivery |
|| **Cost Efficient** | Counter plates generated once, served many times |
|| **Scalable** | Redis lookups are O(1), independent of file size |

---

## 2. Cache Key Generation

### Purpose

Cache keys uniquely identify geometry configurations. The same settings must **always** produce the same cache key for proper deduplication.

### Key Generation Algorithm

**Source:** `app/cache.py` (lines 77-80)

```python
def compute_cache_key(payload: dict) -> str:
    """Compute a stable SHA-256 key from request payload for content-addressable caching."""
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

### Canonical JSON Generation

**Source:** `app/cache.py` (lines 69-74)

```python
def _canonical_json(obj):
    """Convert object to canonical JSON string for stable hashing."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(',', ':'))
    except Exception:
        return str(obj)
```

**Critical Rules:**
- `sort_keys=True` — Ensures key order doesn't affect hash
- `separators=(',', ':')` — No whitespace, deterministic formatting
- All floating-point numbers normalized to 5 decimals
- Near-integers converted to integers (`1.0` → `1`)

### Number Normalization

**Source:** `app/cache.py` (lines 83-104)

```python
def _normalize_number(value):
    """Normalize numbers and numeric strings to a stable JSON-friendly form.
    - Convert numeric strings to float
    - Round floats to 5 decimals
    - Convert near-integers to int to avoid 1 vs 1.0 mismatches
    """
    try:
        if isinstance(value, str):
            value = float(value)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int,)):
            return value
        if isinstance(value, float):
            rounded = round(value, 5)
            if abs(rounded - round(rounded)) < 1e-9:
                return int(round(rounded))
            return rounded
    except Exception:
        pass
    return value
```

**Examples:**

| Input | Normalized Output | Reason |
|-------|------------------|--------|
| `"2.5"` | `2.5` | String → float |
| `6.5000001` | `6.5` | Rounded to 5 decimals |
| `1.0` | `1` | Near-integer → int |
| `True` | `1` | Bool → int |
| `"90"` | `90` | String → int |

### Settings Normalization for Cache Keys

**Source:** `app/cache.py` (lines 107-152)

```python
def _normalize_settings_for_cache(settings) -> dict:
    """Return a normalized dict of geometry-affecting settings for cache keys."""
    # Only include fields that change output geometry
    fields = {
        # Card geometry
        'card_width': settings.card_width,
        'card_height': settings.card_height,
        'card_thickness': settings.card_thickness,
        # Grid
        'grid_columns': settings.grid_columns,
        'grid_rows': settings.grid_rows,
        'cell_spacing': settings.cell_spacing,
        'line_spacing': settings.line_spacing,
        'dot_spacing': settings.dot_spacing,
        # Offsets
        'braille_x_adjust': settings.braille_x_adjust,
        'braille_y_adjust': settings.braille_y_adjust,
        # Recess/dot shapes
        'recess_shape': int(getattr(settings, 'recess_shape', 1)),
        'hemisphere_subdivisions': int(getattr(settings, 'hemisphere_subdivisions', 2)),
        'cone_segments': int(getattr(settings, 'cone_segments', 16)),
        # Emboss dot params
        'emboss_dot_base_diameter': getattr(settings, 'emboss_dot_base_diameter', None),
        'emboss_dot_height': getattr(settings, 'emboss_dot_height', None),
        'emboss_dot_flat_hat': getattr(settings, 'emboss_dot_flat_hat', None),
        # Counter plate specific
        'hemi_counter_dot_base_diameter': getattr(settings, 'hemi_counter_dot_base_diameter', ...),
        'bowl_counter_dot_base_diameter': getattr(settings, 'bowl_counter_dot_base_diameter', ...),
        'counter_dot_depth': getattr(settings, 'counter_dot_depth', None),
        'cone_counter_dot_base_diameter': getattr(settings, 'cone_counter_dot_base_diameter', ...),
        'cone_counter_dot_flat_hat': getattr(settings, 'cone_counter_dot_flat_hat', None),
        'cone_counter_dot_height': getattr(settings, 'cone_counter_dot_height', None),
        # Indicator shapes flag
        'indicator_shapes': int(getattr(settings, 'indicator_shapes', 1)),
    }
    # Normalize numeric values
    norm = {}
    for k, v in fields.items():
        norm[k] = _normalize_number(v)
    return norm
```

**Important:** Only geometry-affecting parameters are included. Non-geometry fields (like text content, language tables) are **excluded** for counter plates.

### Cylinder Parameters Normalization

**Source:** `app/cache.py` (lines 155-163)

```python
def _normalize_cylinder_params_for_cache(cylinder_params: dict) -> dict:
    """Normalize cylinder parameters for cache key generation."""
    if not isinstance(cylinder_params, dict):
        return {}
    keys = ['diameter_mm', 'height_mm', 'polygonal_cutout_radius_mm',
            'polygonal_cutout_sides', 'seam_offset_deg']
    out = {}
    for k in keys:
        out[k] = _normalize_number(cylinder_params.get(k))
    return out
```

### Cache Key Example

**Input Settings:**
```json
{
  "grid_columns": "13",
  "grid_rows": "4",
  "cell_spacing": "6.50000",
  "line_spacing": 10.0,
  "dot_spacing": "2.5",
  "recess_shape": "1"
}
```

**Normalized Payload:**
```json
{
  "grid_columns": 13,
  "grid_rows": 4,
  "cell_spacing": 6.5,
  "line_spacing": 10,
  "dot_spacing": 2.5,
  "recess_shape": 1
}
```

**Cache Key:** `a7b3c9d1e2f4... (SHA-256 hex, 64 chars)`

---

## 3. Redis Integration

### Purpose

Redis provides **fast O(1) lookups** to map cache keys to Vercel Blob URLs without querying the Blob API directly.

### Redis Client Initialization

**Source:** `app/cache.py` (lines 28-43)

```python
def _get_redis_client():
    """Get or create Redis client singleton."""
    global _redis_client_singleton
    if _redis_client_singleton is not None:
        return _redis_client_singleton
    if _redis_mod is None:
        return None
    try:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            return None
        # from_url handles rediss:// and ssl automatically
        _redis_client_singleton = _redis_mod.from_url(redis_url, decode_responses=True)
        return _redis_client_singleton
    except Exception:
        return None
```

**Initialization Pattern:**
- Singleton pattern for connection reuse
- Lazy initialization (only when first accessed)
- SSL/TLS support via `rediss://` URL scheme
- `decode_responses=True` for string values (not bytes)

### Redis Operations

#### Get Cached URL

**Source:** `app/cache.py` (lines 46-54)

```python
def _blob_url_cache_get(cache_key: str) -> str:
    """Get cached blob URL from Redis."""
    try:
        r = _get_redis_client()
        if not r:
            return ''
        return r.get(f'blob-url:{cache_key}') or ''
    except Exception:
        return ''
```

**Key Format:** `blob-url:{cache_key}`

**Example:**
```
Key: blob-url:a7b3c9d1e2f4567890abcdef123456
Value: https://abc123xyz.public.blob.vercel-storage.com/stl/a7b3c9d1.stl
```

#### Set Cached URL

**Source:** `app/cache.py` (lines 57-66)

```python
def _blob_url_cache_set(cache_key: str, url: str) -> None:
    """Set cached blob URL in Redis with TTL."""
    try:
        r = _get_redis_client()
        if not r:
            return
        ttl = int(os.environ.get('BLOB_URL_TTL_SEC', '31536000'))
        r.setex(f'blob-url:{cache_key}', ttl, url)
    except Exception:
        return
```

**TTL Default:** 31536000 seconds (1 year)

**Rationale:** Blob URLs are stable and immutable; long TTL reduces Redis storage needs while maintaining cache effectiveness.

### Redis Key Namespace

All cache keys are prefixed with `blob-url:` to:
- Avoid collisions with other application data
- Enable bulk operations (e.g., `KEYS blob-url:*`)
- Support future multi-tenant scenarios

---

## 4. Vercel Blob Storage

### Overview

Vercel Blob provides **immutable object storage** with global CDN distribution. STL files are uploaded once and served from edge locations worldwide.

### Public URL Format

**Source:** `app/cache.py` (lines 172-178)

```python
def _build_blob_public_url(cache_key: str) -> str:
    """Build the public URL for a blob given its cache key."""
    base = _blob_public_base_url().rstrip('/')
    if not base:
        return ''
    # namespace STLs under /stl/
    return f'{base}/stl/{cache_key}.stl'
```

**URL Structure:**
```
https://{store_id}.public.blob.vercel-storage.com/stl/{cache_key}.stl
```

**Components:**
- `{store_id}` — Vercel Blob store identifier (from environment)
- `/stl/` — Namespace for STL files (organizational)
- `{cache_key}.stl` — Deterministic filename based on cache key

### Blob Existence Check

**Source:** `app/cache.py` (lines 181-204)

```python
def _blob_check_exists(public_url: str) -> bool:
    """Return True if the blob appears to exist and is retrievable.

    Some CDNs/storage frontends may not support HEAD consistently or may
    require following redirects. Fall back to a minimal Range GET.
    """
    if not public_url or requests is None:
        return False
    # First try HEAD and follow redirects
    try:
        resp = requests.head(public_url, timeout=4, allow_redirects=True)
        if 200 <= resp.status_code < 300:
            return True
    except Exception:
        pass
    # Fallback: minimal GET with a 1-byte range
    try:
        headers = {'Range': 'bytes=0-0'}
        resp = requests.get(public_url, headers=headers, timeout=6, stream=True, allow_redirects=True)
        with contextlib.suppress(Exception):
            resp.close()
        return resp.status_code in (200, 206)
    except Exception:
        return False
```

**Two-Stage Verification:**
1. **HEAD request** (preferred) — Fast, minimal data transfer
2. **Range GET** (fallback) — Fetches only 1 byte to verify existence

### Blob Upload

**Source:** `app/cache.py` (lines 207-292)

```python
def _blob_upload(cache_key: str, stl_bytes: bytes, logger=None) -> str:
    """Upload STL to Vercel Blob via REST if configured. Returns public URL or empty string."""
    if requests is None:
        return ''

    token = os.environ.get('BLOB_STORE_WRITE_TOKEN') or os.environ.get('BLOB_READ_WRITE_TOKEN')
    if not token:
        return ''

    pathname = f'stl/{cache_key}.stl'

    # First, try deterministic PUT to the exact pathname (no suffix)
    try:
        direct_base = os.environ.get('BLOB_DIRECT_UPLOAD_URL', 'https://blob.vercel-storage.com')
        put_url = f'{direct_base.rstrip("/")}/{pathname}'
        headers = {
            'Authorization': f'Bearer {token}',
            'x-vercel-blob-access': 'public',
            'x-vercel-blobs-access': 'public',
            'x-vercel-blob-add-random-suffix': '0',  # CRITICAL: no random suffix
            'x-vercel-blobs-add-random-suffix': '0',
            'content-type': 'application/octet-stream',
        }

        store_id = os.environ.get('BLOB_STORE_ID')
        if store_id:
            headers['x-vercel-store-id'] = store_id

        max_age = os.environ.get('BLOB_CACHE_MAX_AGE')
        if max_age:
            headers['x-vercel-cache-control-max-age'] = str(max_age)

        resp = requests.put(put_url, data=stl_bytes, headers=headers, timeout=30)

        if 200 <= resp.status_code < 300 or resp.status_code == 409:
            # 409 Conflict = file already exists (OK for content-addressable storage)
            try:
                j = resp.json()
                url_from_api = j.get('url') or ''
                if url_from_api:
                    return url_from_api
            except Exception:
                pass
            # Fallback to constructed public URL
            return _build_blob_public_url(cache_key)
```

### Upload Request Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `Authorization` | `Bearer {token}` | Authentication |
| `x-vercel-blob-access` | `public` | Make blob publicly accessible |
| `x-vercel-blob-add-random-suffix` | `0` | **Disable** random suffix (critical for deterministic URLs) |
| `x-vercel-store-id` | `{store_id}` | Target specific Blob store |
| `x-vercel-cache-control-max-age` | `{max_age}` | Set CDN cache duration |
| `content-type` | `application/octet-stream` | Binary STL data |

**Critical:** `x-vercel-blob-add-random-suffix: 0` ensures the filename remains exactly `stl/{cache_key}.stl` without random suffixes, enabling content-addressable storage.

### Two-Stage Upload Strategy

1. **Primary:** PUT to direct URL with deterministic path
2. **Fallback:** POST to base URL with `x-vercel-filename` header

Both methods disable random suffixes to ensure deterministic filenames.

---

## 5. Counter Plate Caching Strategy

### Why Counter Plates Are Cached

**Key Insight:** Universal counter plates are **completely deterministic** based on grid settings alone:

- **Grid dimensions** — rows, columns, spacing
- **Dot shape** — hemisphere, bowl, or cone parameters
- **Surface dimensions** — plate/cylinder size
- **No text dependency** — Counter plates have ALL dots regardless of text

**Contrast with Positive Plates:**
- Positive plates depend on **text content** (which dots are raised)
- Every different text produces a different geometry
- Caching positive plates would have low hit rate
- Client-side generation is fast enough for positive plates

### Cache Hit Rate Expectations

| Scenario | Expected Hit Rate | Reasoning |
|----------|------------------|-----------|
| **Default settings** | 90-95% | Most users don't change expert mode settings |
| **Common variations** | 60-80% | A few common size/spacing presets |
| **Custom settings** | 10-30% | Unique configurations generate and cache |

### What Makes Counter Plates Universal

**Source:** `backend.py` counter plate generation

```python
# Counter plates generate ALL 6 dots for ALL cells (not text-dependent)
for row_num in range(settings.grid_rows):
    for col_num in range(settings.grid_columns):
        for dot_idx in range(6):  # Always all 6 dots
            # Create recess for this dot
            dot_mesh = create_counter_dot(...)
            meshes.append(dot_mesh)
```

**Text-Independence:** The `lines` and `original_lines` parameters are **ignored** for counter plates.

---

## 6. Cache Flow: Request Lifecycle

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                POST /generate_braille_stl (plate_type: negative)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. EXTRACT PARAMETERS                                                       │
│     settings_data = data.get('settings', {})                                │
│     shape_type = data.get('shape_type', 'card')                             │
│     cylinder_params = data.get('cylinder_params', {})                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. GENERATE CACHE KEY                                                       │
│     settings_normalized = _normalize_settings_for_cache(settings)           │
│     cylinder_normalized = _normalize_cylinder_params_for_cache(params)      │
│     payload = {'shape': shape_type, 'settings': settings_normalized, ...}   │
│     cache_key = compute_cache_key(payload)  # SHA-256 hash                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. CHECK REDIS CACHE                                                        │
│     blob_url = _blob_url_cache_get(cache_key)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
          [URL Found in Redis]              [URL Not Found in Redis]
                    │                                   │
                    ▼                                   │
┌────────────────────────────────────┐                 │
│  4a. VERIFY BLOB EXISTS             │                 │
│      exists = _blob_check_exists()  │                 │
└────────────┬───────────────────────┘                 │
             │                                          │
       [Blob Exists]  [Blob Missing]                    │
             │              │                           │
             │              └───────────────────────────┘
             │                                          │
             │                                          ▼
             │              ┌────────────────────────────────────────────────┐
             │              │  4b. GENERATE STL                              │
             │              │      settings = CardSettings(**settings_data)  │
             │              │      if shape_type == 'cylinder':              │
             │              │          mesh = generate_cylinder_counter()    │
             │              │      else:                                     │
             │              │          mesh = generate_card_counter()        │
             │              │      stl_bytes = mesh.export('stl')            │
             │              └───────────────┬────────────────────────────────┘
             │                              │
             │                              ▼
             │              ┌────────────────────────────────────────────────┐
             │              │  5. UPLOAD TO VERCEL BLOB                      │
             │              │     url = _blob_upload(cache_key, stl_bytes)   │
             │              └───────────────┬────────────────────────────────┘
             │                              │
             │                              ▼
             │              ┌────────────────────────────────────────────────┐
             │              │  6. STORE URL IN REDIS                         │
             │              │     _blob_url_cache_set(cache_key, url)        │
             │              └───────────────┬────────────────────────────────┘
             │                              │
             └──────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  7. RETURN 302 REDIRECT                                                      │
│     return redirect(blob_url, code=302)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cache Hit Flow (Fast Path)

**Total Time:** ~100-200ms

```
1. Redis lookup: ~10-20ms
2. Blob existence check: ~50-100ms (HEAD request to CDN)
3. 302 redirect response: ~5-10ms
```

### Cache Miss Flow (Slow Path)

**Total Time:** ~5-20 seconds (depending on complexity)

```
1. Redis lookup: ~10-20ms (cache miss)
2. Generate STL: ~3-15 seconds (mesh creation, boolean ops)
3. Upload to Blob: ~500ms-2s (network transfer)
4. Store in Redis: ~10-20ms
5. 302 redirect response: ~5-10ms
```

### Optimization: Concurrent First-Time Requests

**Potential Issue:** Multiple users requesting same counter plate simultaneously could trigger multiple generations.

**Mitigation Strategy (Not Currently Implemented):**
- Use Redis SETNX for distributed locking
- First request generates, others wait
- Timeout and retry mechanism

**Current Behavior:** Last-write-wins (acceptable for immutable content)

---

## 7. Environment Variables

### Required Variables

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `BLOB_READ_WRITE_TOKEN` | Authentication for Vercel Blob API | `vercel_blob_rw_...` |
| `BLOB_PUBLIC_BASE_URL` | Base URL for public blob access | `https://abc123.public.blob.vercel-storage.com` |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `REDIS_URL` | Redis connection string | (none - caching disabled) |
| `BLOB_URL_TTL_SEC` | Redis cache TTL | `31536000` (1 year) |
| `BLOB_STORE_ID` | Specific Blob store ID | (auto-detected) |
| `BLOB_DIRECT_UPLOAD_URL` | Blob API endpoint | `https://blob.vercel-storage.com` |
| `BLOB_CACHE_MAX_AGE` | CDN cache duration | (Vercel default) |

### Fallback Behavior Without Environment Variables

| Missing Variable | Behavior |
|-----------------|----------|
| No `REDIS_URL` | Redis operations return empty/None, Blob URL still checked directly |
| No `BLOB_READ_WRITE_TOKEN` | No Blob uploads, falls back to direct STL response |
| No `BLOB_PUBLIC_BASE_URL` | Cannot construct public URLs, falls back to direct response |

**Graceful Degradation:** The application works without any cache variables; it just generates STL files on-demand without caching.

---

## 8. API Endpoints with Caching

### POST /generate_braille_stl

**Caching Behavior:**

| Plate Type | Caching | Response Type |
|------------|---------|---------------|
| `positive` | **No** | Direct STL download (200 OK) |
| `negative` | **Yes** | 302 redirect to Blob URL |

**Implementation in backend.py:**

```python
@app.route('/generate_braille_stl', methods=['POST'])
def generate_braille_stl():
    data = request.get_json()
    plate_type = data.get('plate_type', 'positive')

    # Counter plates use caching
    if plate_type == 'negative':
        # Try cache
        cache_key = compute_cache_key(...)
        blob_url = _blob_url_cache_get(cache_key)

        if blob_url and _blob_check_exists(blob_url):
            logger.info(f'Cache HIT for counter plate, key={cache_key}')
            return redirect(blob_url, code=302)

        # Generate and upload
        stl_bytes = generate_counter_plate(...)
        blob_url = _blob_upload(cache_key, stl_bytes, logger)

        if blob_url:
            _blob_url_cache_set(cache_key, blob_url)
            return redirect(blob_url, code=302)

    # Positive plates or fallback: direct response
    stl_bytes = generate_positive_plate(...)
    return send_file(io.BytesIO(stl_bytes), mimetype='model/stl', ...)
```

### GET /lookup_stl (Dedicated Cache Lookup)

**Purpose:** Check cache without generating STL

**Source:** `backend.py` (lines 134-209)

```python
@app.route('/lookup_stl', methods=['GET'])
@limiter.limit('60 per minute')
def lookup_stl_redirect():
    """Return cached negative plate location (302 redirect or JSON) if available."""

    # Parse query parameters
    shape_type = request.args.get('shape_type', 'card')
    settings_json = request.args.get('settings', '')
    cylinder_json = request.args.get('cylinder_params', '')
    format_type = request.args.get('format', 'redirect')

    # Generate cache key
    settings = CardSettings(**json.loads(settings_json))
    cache_key = compute_cache_key(...)

    # Check cache
    blob_url = _blob_url_cache_get(cache_key)

    if blob_url and _blob_check_exists(blob_url):
        if format_type == 'json':
            return jsonify({'url': blob_url, 'cache_key': cache_key})
        else:
            return redirect(blob_url, code=302)

    return jsonify({'error': 'Not cached'}), 404
```

**Response Formats:**

**302 Redirect (default):**
```
HTTP/1.1 302 Found
Location: https://abc.public.blob.vercel-storage.com/stl/{key}.stl
```

**JSON Response (`format=json`):**
```json
{
  "url": "https://abc.public.blob.vercel-storage.com/stl/{key}.stl",
  "cache_key": "a7b3c9d1e2f4567890abcdef12345678"
}
```

**Cache Miss:**
```json
{
  "error": "Not cached"
}
```
Status: 404 Not Found

---

## 9. Cache Invalidation and TTL

### Cache Lifetime Strategy

**Principle:** Counter plates are **immutable** — same settings always produce byte-identical STL files.

**TTL Values:**

| Storage | TTL | Rationale |
|---------|-----|-----------|
| **Redis URL Mapping** | 1 year (31536000s) | Long-lived, stable URLs |
| **Vercel Blob Storage** | Permanent | Immutable content-addressed storage |
| **CDN Cache** | Configurable | Set via `x-vercel-cache-control-max-age` |

### When Caching Breaks Down

**Cache invalidation is needed when:**

1. **Bug fixes in geometry generation** — Old cached STLs have bugs
2. **Floating-point precision changes** — Python version, library updates
3. **Boolean operation algorithm changes** — Different mesh triangulation

**Invalidation Methods:**

| Method | Scope | Implementation |
|--------|-------|----------------|
| **Change cache key format** | Global | Modify `_normalize_settings_for_cache()` to include version field |
| **Clear Redis keys** | Global | `redis-cli KEYS blob-url:* | xargs redis-cli DEL` |
| **Delete Blob files** | Per-file | Use Vercel Blob API or dashboard |
| **Ignore old cache** | Automatic | Blob existence check fails → regenerate |

### Cache Version Field (Recommended Addition)

**Not currently implemented, but recommended:**

```python
def _normalize_settings_for_cache(settings) -> dict:
    fields = {
        'cache_version': 2,  # Increment when geometry algorithm changes
        'card_width': settings.card_width,
        # ... other fields
    }
```

---

## 10. Error Handling and Fallbacks

### Redis Connection Failures

**Behavior:** Graceful degradation, caching disabled

```python
def _get_redis_client():
    try:
        # ... connection logic
        return client
    except Exception:
        return None  # No error raised, caching just doesn't work
```

**Impact:**
- All Redis operations return empty/None
- Blob URL is still checked via HTTP
- Slightly increased latency (no Redis fast path)
- Regeneration on every request

### Blob Upload Failures

**Behavior:** Falls back to direct STL response

```python
blob_url = _blob_upload(cache_key, stl_bytes, logger)

if blob_url:
    _blob_url_cache_set(cache_key, blob_url)
    return redirect(blob_url, code=302)
else:
    # Blob upload failed, serve directly
    logger.warning('Blob upload failed, serving STL directly')
    return send_file(io.BytesIO(stl_bytes), mimetype='model/stl', ...)
```

**Impact:**
- Request completes successfully
- No caching benefit (future requests regenerate)
- Increased server load

### Blob Existence Check Failures

**Behavior:** Regenerate STL

```python
if blob_url and _blob_check_exists(blob_url):
    return redirect(blob_url, code=302)
else:
    # URL cached but blob missing (orphaned Redis entry)
    logger.warning(f'Cached URL exists in Redis but blob not found: {blob_url}')
    # Fall through to regeneration
```

**Impact:**
- Orphaned Redis entries are ignored
- Blob is regenerated and re-uploaded
- Redis entry is updated with new URL

### Network Timeout Handling

All external requests have timeouts:

| Operation | Timeout | Fallback |
|-----------|---------|----------|
| Redis operations | Implicit (library default ~30s) | Return None |
| Blob HEAD check | 4 seconds | Try Range GET |
| Blob Range GET check | 6 seconds | Return False |
| Blob upload (PUT) | 30 seconds | Try POST fallback |
| Blob upload (POST) | 30 seconds | Serve direct STL |

---

## 11. Performance Characteristics

### Cache Performance Metrics

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Redis GET | 5-20ms | Local: ~5ms, Remote: ~10-20ms |
| Redis SET | 5-20ms | Same as GET |
| Blob HEAD check | 50-150ms | Depends on CDN location |
| Blob upload | 500ms-3s | Depends on STL size (1-10MB) |
| Generate counter plate | 3-15s | Depends on grid size |

### Cache Hit Savings

**Example: 4-row × 13-column counter plate**

| Path | Time | Breakdown |
|------|------|-----------|
| **Cache Hit** | ~150ms | Redis (20ms) + Blob check (100ms) + Redirect (30ms) |
| **Cache Miss** | ~8s | Redis miss (20ms) + Generate (6s) + Upload (1.5s) + Redis store (20ms) + Redirect (30ms) |
| **Savings** | **~7.85s** (98% reduction) | — |

### Memory Usage

| Component | Memory | Lifecycle |
|-----------|--------|-----------|
| Redis client | ~5-10 MB | Singleton, persistent |
| Blob upload buffer | ~1-10 MB | Per-request, garbage collected |
| Mesh generation | ~50-200 MB | Per-generation, garbage collected |

---

## 12. Implementation Details

### Backend Integration Points

**File:** `backend.py`

**Counter plate generation functions:**

| Function | Shape | Lines |
|----------|-------|-------|
| `generate_card_counter_plate()` | Card | Various |
| `generate_cylinder_counter_plate()` | Cylinder | Various |

Both functions:
1. Accept `CardSettings` and optionally `CylinderParams`
2. Generate mesh with ALL dots (text-independent)
3. Export to STL bytes
4. Return bytes for caching

### Cache Module Functions

**File:** `app/cache.py`

| Function | Purpose | Returns |
|----------|---------|---------|
| `compute_cache_key(payload)` | Generate SHA-256 hash | `str` (hex) |
| `_normalize_settings_for_cache(settings)` | Extract geometry params | `dict` |
| `_normalize_cylinder_params_for_cache(params)` | Normalize cylinder params | `dict` |
| `_blob_url_cache_get(key)` | Redis GET | `str` (URL or empty) |
| `_blob_url_cache_set(key, url)` | Redis SETEX | `None` |
| `_blob_upload(key, bytes)` | Upload to Blob | `str` (URL or empty) |
| `_blob_check_exists(url)` | Verify blob exists | `bool` |
| `_build_blob_public_url(key)` | Construct URL | `str` |

### Importing Cache Functions

```python
# In backend.py
from app.cache import (
    _blob_check_exists,
    _blob_public_base_url,
    _blob_upload,
    _blob_url_cache_get,
    _blob_url_cache_set,
    _build_blob_public_url,
    _normalize_cylinder_params_for_cache,
    _normalize_settings_for_cache,
    compute_cache_key,
)
```

---

## 13. Deployment Considerations

### Local Development

**Without Redis/Blob configured:**
- All cache operations no-op gracefully
- STL files served directly (200 OK)
- Full functionality preserved

**With Redis/Blob configured:**
- Can test caching behavior locally
- Useful for performance testing
- Use Vercel Blob dev store

### Vercel Production

**Environment variables set via Vercel dashboard:**
- `REDIS_URL` — From Upstash Redis or similar
- `BLOB_READ_WRITE_TOKEN` — From Vercel Blob storage
- `BLOB_PUBLIC_BASE_URL` — Auto-configured by Vercel

**Vercel Blob Limits (Hobby tier):**
- **Storage:** 100 GB total
- **Bandwidth:** Unlimited (served via CDN)
- **File size:** Up to 500 MB per file (STLs are typically 1-10 MB)

### Redis Recommendations

**Provider Options:**
1. **Upstash Redis** (recommended for Vercel)
   - Serverless-native
   - Global replication
   - Hobby tier: 10K commands/day free

2. **Redis Labs**
   - More features
   - Requires VPN/IP whitelist for security

3. **Redis Cloud**
   - Managed service
   - Pay-as-you-go

**Connection String Format:**
```
redis://default:{password}@{host}:{port}
rediss://default:{password}@{host}:{port}  # SSL/TLS
```

---

## 14. Monitoring and Observability

### Logging

**Cache Operations Logged:**

```python
# Cache hit
logger.info(f'Cache HIT for counter plate, key={cache_key[:8]}...')

# Cache miss
logger.info(f'Cache MISS for counter plate, generating, key={cache_key[:8]}...')

# Blob upload success
logger.info(f'Blob upload OK for key={cache_key[:8]}..., url={blob_url}')

# Blob upload failure
logger.warning(f'Blob upload failed status={status} body={body}')

# Blob check failure
logger.warning(f'Cached URL exists in Redis but blob not found: {blob_url}')
```

### Metrics to Monitor

| Metric | Source | Threshold |
|--------|--------|-----------|
| **Cache hit rate** | Application logs | Target: >80% |
| **Redis connection errors** | Exception logs | Target: <1% |
| **Blob upload failures** | Warning logs | Target: <5% |
| **Average response time** | Vercel analytics | Target: <1s (hit), <10s (miss) |

### Debug Endpoint (Optional)

**Not currently implemented, but recommended:**

```python
@app.route('/debug/cache_stats', methods=['GET'])
def cache_stats():
    """Return cache statistics for monitoring."""
    redis_client = _get_redis_client()

    if not redis_client:
        return jsonify({'error': 'Redis not configured'})

    # Get all blob-url keys
    keys = redis_client.keys('blob-url:*')

    return jsonify({
        'total_cached_items': len(keys),
        'redis_connected': True,
        'sample_keys': keys[:10]  # First 10 for inspection
    })
```

---

## 15. Security Considerations

### Public Blob Access

**Design Choice:** All cached STL files are **publicly accessible**.

**Rationale:**
- Counter plates contain no user-specific content
- Geometry is deterministic and non-sensitive
- Public access enables CDN caching

**Risk Mitigation:**
- No personally identifiable information in counter plates
- Blob URLs are not enumerable (random store IDs)
- Cache keys are hashed (not guessable)

### Redis Security

**Best Practices:**
- Use `rediss://` (TLS) for production
- Rotate Redis passwords periodically
- Use Vercel environment variables (encrypted at rest)
- Limit Redis access to serverless functions only

### Blob Token Security

**Critical:**
- `BLOB_READ_WRITE_TOKEN` grants full access to Blob storage
- Never expose in client-side code
- Store in Vercel environment variables (encrypted)
- Rotate if compromised

---

## 16. Testing and Verification

### Unit Tests

**Test: Cache Key Stability**
```python
def test_cache_key_stability():
    settings1 = CardSettings(grid_columns=13, grid_rows=4, cell_spacing=6.5)
    settings2 = CardSettings(grid_columns="13", grid_rows="4", cell_spacing="6.50")

    key1 = compute_cache_key(_normalize_settings_for_cache(settings1))
    key2 = compute_cache_key(_normalize_settings_for_cache(settings2))

    assert key1 == key2, "Different representations should produce same cache key"
```

**Test: Number Normalization**
```python
def test_number_normalization():
    assert _normalize_number("2.5") == 2.5
    assert _normalize_number(1.0) == 1
    assert _normalize_number(1.00001) == 1
    assert _normalize_number(2.5000000001) == 2.5
```

### Integration Tests

**Test: Cache Round-Trip**
```python
async def test_cache_round_trip():
    # First request (cache miss)
    resp1 = await client.post('/generate_braille_stl', json={
        'plate_type': 'negative',
        'settings': {'grid_columns': 13, ...}
    })
    assert resp1.status_code == 302
    blob_url1 = resp1.headers['Location']

    # Second request (cache hit)
    resp2 = await client.post('/generate_braille_stl', json={
        'plate_type': 'negative',
        'settings': {'grid_columns': 13, ...}
    })
    assert resp2.status_code == 302
    blob_url2 = resp2.headers['Location']

    assert blob_url1 == blob_url2, "Same settings should return same blob URL"
```

### Manual Verification

1. **Generate counter plate** with default settings
2. **Check logs** for cache miss message
3. **Generate again** with same settings
4. **Check logs** for cache hit message
5. **Verify response time** — Second request should be <1s

---

## 17. Future Enhancements

### Potential Improvements

| Enhancement | Benefit | Complexity |
|-------------|---------|------------|
| **Distributed lock for concurrent requests** | Prevent duplicate generations | Medium |
| **Cache version field** | Easier invalidation | Low |
| **Positive plate caching** | Reduce repeated text generations | High (text hash needed) |
| **Preemptive cache warming** | Faster first-time user experience | Medium |
| **Cache analytics endpoint** | Better monitoring | Low |
| **Blob cleanup job** | Reduce storage costs | Medium |

### Not Recommended

| Anti-Pattern | Why Avoid |
|--------------|-----------|
| **Cache positive plates by text** | Low hit rate, storage bloat |
| **Aggressive TTL** | Unnecessary (immutable content) |
| **Local filesystem cache** | Not serverless-compatible |
| **In-memory cache** | Lost on function cold start |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-06 | Initial comprehensive specification document |

---

## Related Specifications

- [STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md](./STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md) — Generation and download system
- [SURFACE_DIMENSIONS_SPECIFICATIONS.md](./SURFACE_DIMENSIONS_SPECIFICATIONS.md) — Parameters that affect cache keys
- [BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md](./BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md) — Dot parameters in cache keys
- [BRAILLE_SPACING_SPECIFICATIONS.md](./BRAILLE_SPACING_SPECIFICATIONS.md) — Spacing parameters in cache keys

---

## Appendix A: Complete Cache Key Example

### Input Request

```json
{
  "plate_type": "negative",
  "shape_type": "cylinder",
  "settings": {
    "grid_columns": "13",
    "grid_rows": "4",
    "cell_spacing": "6.50",
    "line_spacing": "10.0",
    "dot_spacing": "2.5",
    "recess_shape": "1",
    "card_width": 90,
    "card_height": 52,
    "card_thickness": "2.0",
    "bowl_counter_dot_base_diameter": "1.8",
    "counter_dot_depth": "0.8"
  },
  "cylinder_params": {
    "diameter_mm": "30.75",
    "height_mm": "52",
    "polygonal_cutout_radius_mm": "13",
    "polygonal_cutout_sides": "12",
    "seam_offset_deg": "355"
  }
}
```

### Normalized Payload

```json
{
  "shape_type": "cylinder",
  "settings": {
    "card_width": 90,
    "card_height": 52,
    "card_thickness": 2,
    "grid_columns": 13,
    "grid_rows": 4,
    "cell_spacing": 6.5,
    "line_spacing": 10,
    "dot_spacing": 2.5,
    "braille_x_adjust": 0,
    "braille_y_adjust": 0,
    "recess_shape": 1,
    "hemisphere_subdivisions": 2,
    "cone_segments": 16,
    "bowl_counter_dot_base_diameter": 1.8,
    "counter_dot_depth": 0.8,
    "indicator_shapes": 1
  },
  "cylinder_params": {
    "diameter_mm": 30.75,
    "height_mm": 52,
    "polygonal_cutout_radius_mm": 13,
    "polygonal_cutout_sides": 12,
    "seam_offset_deg": 355
  }
}
```

### Canonical JSON

```
{"cylinder_params":{"diameter_mm":30.75,"height_mm":52,"polygonal_cutout_radius_mm":13,"polygonal_cutout_sides":12,"seam_offset_deg":355},"settings":{"bowl_counter_dot_base_diameter":1.8,"braille_x_adjust":0,"braille_y_adjust":0,"card_height":52,"card_thickness":2,"card_width":90,"cell_spacing":6.5,"cone_segments":16,"counter_dot_depth":0.8,"dot_spacing":2.5,"grid_columns":13,"grid_rows":4,"hemisphere_subdivisions":2,"indicator_shapes":1,"line_spacing":10,"recess_shape":1},"shape_type":"cylinder"}
```

### Cache Key (SHA-256)

```
7e8f9a0b1c2d3e4f5g6h7i8j9k0l1m2n  (first 32 chars of 64-char hash)
```

### Blob URL

```
https://abc123xyz.public.blob.vercel-storage.com/stl/7e8f9a0b1c2d3e4f5g6h7i8j9k0l1m2n.stl
```

### Redis Entry

```
Key:   blob-url:7e8f9a0b1c2d3e4f5g6h7i8j9k0l1m2n
Value: https://abc123xyz.public.blob.vercel-storage.com/stl/7e8f9a0b1c2d3e4f5g6h7i8j9k0l1m2n.stl
TTL:   31536000 seconds (1 year)
```

---

## Appendix B: Troubleshooting Guide

### Cache Not Working (Always Regenerating)

**Symptoms:**
- Every request takes 5-10 seconds
- Logs show "Cache MISS" repeatedly for same settings

**Possible Causes:**

1. **Redis not configured**
   - Check: `REDIS_URL` environment variable set
   - Verify: Redis is accessible from serverless function
   - Test: Connect with redis-cli

2. **Settings normalization inconsistent**
   - Check: Input settings use consistent types (string vs number)
   - Verify: Floating-point precision (should round to 5 decimals)
   - Test: Log normalized payload before hashing

3. **Blob uploads failing**
   - Check: `BLOB_READ_WRITE_TOKEN` is valid
   - Verify: Token has write permissions
   - Check logs: Look for "Blob upload failed" warnings

### Cache Returning 404 for Existing Keys

**Symptoms:**
- Redis contains URL
- Blob check returns False
- Request regenerates STL

**Possible Causes:**

1. **Blob was deleted**
   - Solution: Regeneration will re-upload

2. **Blob URL format changed**
   - Solution: Clear Redis keys, regenerate

3. **Network timeout**
   - Solution: Increase timeout in `_blob_check_exists()`

### Redis Connection Errors

**Symptoms:**
- Logs show Redis connection exceptions
- Caching completely disabled

**Possible Causes:**

1. **Invalid Redis URL**
   - Check: URL format `redis://user:pass@host:port`
   - Verify: Credentials are correct

2. **Network access blocked**
   - Check: Firewall rules allow Vercel → Redis
   - Verify: IP whitelist includes Vercel IPs

3. **Redis server down**
   - Check: Redis provider status page
   - Verify: Can connect from other client

---

## Appendix C: Cache Key Determinism Verification

### Verification Script

```python
def verify_cache_key_determinism():
    """Verify that cache keys are deterministic and stable."""

    # Same settings in different formats
    settings_variants = [
        {'grid_columns': 13, 'grid_rows': 4, 'cell_spacing': 6.5},
        {'grid_columns': '13', 'grid_rows': '4', 'cell_spacing': '6.5'},
        {'grid_columns': 13.0, 'grid_rows': 4.0, 'cell_spacing': 6.50000},
    ]

    keys = []
    for variant in settings_variants:
        settings = CardSettings(**variant)
        normalized = _normalize_settings_for_cache(settings)
        key = compute_cache_key({'settings': normalized, 'shape_type': 'card'})
        keys.append(key)
        print(f'Variant: {variant}')
        print(f'Normalized: {normalized}')
        print(f'Cache key: {key}')
        print()

    # All keys should be identical
    assert len(set(keys)) == 1, "All variants should produce the same cache key"
    print("✅ Cache key determinism verified")
```

---

*Document Version: 1.0*
*Last Updated: 2024-12-06*
*Source Priority (historical; caching removed 2026-01-05): app/cache.py (deleted) > backend.py (caching removed) > app/models.py > wsgi.py*
