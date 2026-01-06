# Vercel Optimization Roadmap

⚠️ **ARCHITECTURE UPDATE (2026-01-05):** Phases 3 and 4 (Redis/Blob caching) have been **DEPRECATED and REMOVED** from the application. The application now uses client-side CSG generation exclusively, eliminating all external service dependencies. This document is maintained for historical reference.

---

## Current Architecture (2026-01-05)

**Minimal Backend + Client-Side Generation:**
- Flask backend provides lightweight JSON geometry specifications (`/geometry_spec`)
- No Redis, no Blob storage, no rate limiting infrastructure needed
- All STL generation happens client-side using Web Workers (BVH-CSG for cards, Manifold WASM for cylinders)
- Zero external service dependencies = zero maintenance overhead
- No 14-day inactivity failure mode

**For implementation details, see:**
- [Codebase Audit and Renovation Plan](../development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md)

---

## Historical Roadmap (Pre-2026-01-05)

This roadmap outlines performance and cost optimization steps that were implemented for deploying the Braille Card and Cylinder STL Generator on Vercel with server-side generation and caching infrastructure.

## Phase 1: Static Asset Optimization (Immediate Impact)

### 1.1 Configure Static File Serving
**Status: SKIPPED**
- Update `vercel.json` to serve static assets directly from Vercel's CDN
- Add static routes for `/static/**` and `/favicon.ico`
- Benefits: Reduces function invocations, faster asset delivery

Reason:
- Interferes with liblouis table include resolution on Vercel; translation fails to find `unicode.dis` and UEB tables.
Action:
- Serve all assets via Python for reliability; revisit later with a verified mapping fix.

### 1.2 Update CSP Headers
**Status: COMPLETE**
- Add `worker-src 'self' blob:;` to Content Security Policy in backend.py
- Ensures web workers (liblouis) function properly with enhanced security

## Phase 2: Function Optimization

### 2.1 Memory and Timeout Configuration
**Status: SKIPPED**
Reason:
- The `functions` property is not supported with `builds` in vercel.json for this project preset.
Action:
- Rely on default limits or set memory/timeouts via Vercel dashboard if needed.
- Set function memory to 1024MB (sweet spot for Python + trimesh)
- Set maxDuration to 30s for complex STL generation
- Add to `vercel.json`:

```json
"functions": {
  "wsgi.py": {
    "memory": 1024,
    "maxDuration": 30
  }
}
```

### 2.2 Response Caching Headers
**Status: COMPLETE**
- Add Cache-Control headers to STL responses
- Implement ETags for browser caching
- Code changes in `backend.py`:
  - `Cache-Control: public, max-age=3600, stale-while-revalidate=86400`
  - Strong ETag computed from SHA-256 of STL bytes
  - Return `304 Not Modified` when client `If-None-Match` matches

## Phase 3: Persistent Caching

### 3.1 Content-Addressable STL Cache
**Status: ~~COMPLETE~~ → DEPRECATED (2026-01-05)**

⚠️ **REMOVED:** Blob storage caching has been removed from the application.

**Reason for Removal:**
- Server-side STL generation does not work on Vercel (no manifold3d binaries)
- Client-side generation is fast enough that caching is unnecessary
- Eliminates external service dependency and associated costs
- Removes complexity from deployment and maintenance

**Historical Implementation:**
- Research available Vercel Blob SDKs for Python (e.g. REST API vs `vercel_blob`)
- Select approach for server-side blob interactions
- Implement Vercel Blob storage for generated STLs
- Cache key based on request parameters hash
- Redirect to cached STLs when available
- Environment variable: `BLOB_STORE_WRITE_TOKEN`

Policy:
- Blob caching is ENABLED for Universal Counter Plate generation (plate_type "negative") for BOTH shapes: `card` and `cylinder`.
- Blob caching is DISABLED for Embossing plate generation (plate_type "positive") for BOTH shapes: `card` and `cylinder`.
- Counter plate cache keys exclude user text and grade; embossing plate responses are never persisted to blob.

Implementation:
1. Check cache before generation (only when `plate_type` is `negative`)
2. Store generated STLs in Blob storage (only when `plate_type` is `negative`)
3. Return 302 redirect to cached URL (only when `plate_type` is `negative`)

## Phase 4: Rate Limiting

### 4.1 Remove In-Memory Rate Limiting
**Status: ~~COMPLETE~~ → DEPRECATED (2026-01-05)**

⚠️ **REMOVED:** Flask-Limiter and all rate limiting infrastructure have been removed.

**Reason for Removal:**
- `/geometry_spec` endpoint is lightweight (returns JSON only, no heavy computation)
- Vercel provides DDoS protection at the edge network level
- Rate limiting on a JSON-only endpoint is unnecessary overhead
- Eliminates Redis dependency that caused 14-day inactivity failures

**Historical Implementation:**
- Replace defaultdict-based limiter with Flask-Limiter
- Configure shared storage via Redis when available
- Preserve memory:// fallback for development

### 4.2 Integrate Upstash Redis
**Status: ~~COMPLETE~~ → DEPRECATED (2026-01-05)**

⚠️ **REMOVED:** Upstash Redis integration has been removed.

**Reason for Removal:**
- Upstash free tier archives databases after 14 days of inactivity
- Archived databases cause `redis.exceptions.ConnectionError` on ALL requests
- This was the root cause of deployment failures (Error 16: Device or resource busy)
- Client-side generation eliminates need for distributed rate limiting

**Historical Setup:**
1. Create Upstash Redis database (free tier)
2. Add `REDIS_URL` to Vercel environment variables
3. Deploy with redis and flask-limiter dependencies

## Phase 5: Edge Optimization (Optional)

### 5.1 Move Static HTML to Edge
**Status: COMPLETE**
- Route `/` and `/index.html` to static `templates/index.html` via Vercel configuration
- Keep Python backend focused on API endpoints
- Prepares for optional Edge middleware enhancements

### 5.2 Parameter Validation at Edge
**Status: SKIPPED**
- Not applicable for this Flask-only project without Next.js Edge Middleware.
- Validation is handled in `backend.py` before processing.

## Phase 6: Advanced Caching (Optional)

### 6.1 CDN Integration
**Status: COMPLETE**
- Blob uploads set long-lived Cache-Control metadata (immutable, content-addressed)
- Redirect responses include CDN-Cache-Control for edge caching
- Added GET lookup endpoint and frontend GET-first flow for negative plates

### 6.2 Pregeneration Strategy
**Status: ~~COMPLETE~~ → DEPRECATED (2026-01-05)**
- The `scripts/pregenerate.py` helper was removed when Redis/Blob caching was removed.
- Client-side generation does not require cache pre-warming.

## Phase 7: Monitoring and Analytics

### 7.1 Performance Monitoring
**Status: COMPLETE**
- X-Compute-Time and X-Cache response headers added for STL endpoints and lookup
- Track function execution times and cache outcomes via response headers and logs
- Optional: enable Vercel Analytics

### 7.2 Cost Optimization Tracking
**Status: COMPLETE**
- Structured JSON logs added for uploads vs origin sends (size, compute_ms)
- Use Vercel logs/analytics to monitor invocations and bandwidth
- Track Redis and Blob usage via provider dashboards

## Implementation Checklist

- [ ] Phase 1.1: Configure static file serving in vercel.json (skipped)
- [x] Phase 1.2: Update CSP headers for web workers
- [ ] Phase 2.1: Set function memory and timeout limits (skipped)
- [x] Phase 2.2: Add cache headers to STL responses
- [x] Phase 3.1: Implement Vercel Blob caching
- [x] Phase 4.1: Remove in-memory rate limiting
- [x] Phase 4.2: Integrate Upstash Redis
- [x] Phase 5.1: Move HTML to Edge (optional)
- [ ] Phase 5.2: Edge validation (optional) (skipped)
- [x] Phase 6.1: CDN integration (metadata)
- [x] Phase 6.2: Pregeneration (optional)
- [x] Phase 7.1: Enable monitoring (headers/logs)
- [x] Phase 7.2: Track costs

## Environment Variables Required

### Current Architecture (2026-01-05)

**Optional (recommended for production):**

1. **SECRET_KEY** (Flask)
   - Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Used for: Flask session security (optional for stateless backend)

2. **PRODUCTION_DOMAIN** (CORS)
   - Format: `https://your-domain.vercel.app`
   - Used for: CORS origin validation

3. **FLASK_ENV** (Environment)
   - Value: `production` or `development`
   - Used for: Debug mode control

**Note:** No Redis, Blob storage, or other external service credentials required!

---

### Historical Architecture (Pre-2026-01-05) - DEPRECATED

~~1. **BLOB_STORE_WRITE_TOKEN** (Vercel Blob)~~
   - **REMOVED** - Blob storage no longer used
   - Get from: Vercel Dashboard → Storage → Create Blob Store
   - Used for: Caching generated STL files

~~2. **REDIS_URL** (Upstash Redis)~~
   - **REMOVED** - Causes deployment failures when database archives
   - Get from: Upstash Console → Create Database → Connection String
   - Format: `rediss://default:<password>@<host>:<port>`
   - Used for: Rate limiting

3. **SECRET_KEY** (Flask)
   - Still optional but recommended
   - Generate: Random string for session security
   - Used for: Flask session management

## Testing Guide

### Verify Static Asset Serving
```bash
curl -I https://your-app.vercel.app/static/three.module.js
# Should return from CDN, not function
```

### Verify Rate Limiting
```powershell
# Send 11 requests rapidly
for ($i=1; $i -le 11; $i++) {
  $code = curl.exe -s -o NUL -w "%{http_code}" `
    -X POST -H "Content-Type: application/json" `
    -d '{"lines":["⠁"],"plate_type":"positive","grade":"g2","settings":{}}' `
    "https://your-app.vercel.app/generate_braille_stl"
  Write-Host "$i -> $code"
  Start-Sleep -Milliseconds 200
}
# Expect: 10x 200/302, then 429
```

### Verify Caching
1. Generate an STL with specific parameters
2. Note response time
3. Repeat with same parameters
4. Second request should be faster (cache hit)

## Cost Savings

Expected monthly savings:
- Static asset serving: -70% function invocations
- STL caching: -50% compute time for repeated requests
- Edge caching: -30% bandwidth costs
- Total estimate: 40-60% cost reduction

## Next Steps

With Phases 1-4 complete, the application has:
- Optimized static asset delivery
- Efficient memory allocation
- Browser and CDN caching
- Persistent STL storage
- Global rate limiting

Optional phases (5-7) can be implemented based on:
- Traffic patterns
- Cost analysis
- Performance requirements

For production deployment:
1. Update CORS origins in backend.py
2. Set all environment variables
3. Enable Vercel Analytics
4. Monitor first week of metrics
5. Adjust rate limits based on usage
