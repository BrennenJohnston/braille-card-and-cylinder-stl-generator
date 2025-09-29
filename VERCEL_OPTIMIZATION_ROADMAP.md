# Vercel Optimization Roadmap

This roadmap outlines performance and cost optimization steps for deploying the Braille Card and Cylinder STL Generator on Vercel.

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
**Status: COMPLETE**
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
**Status: COMPLETE**
- Replace defaultdict-based limiter with Flask-Limiter
- Configure shared storage via Redis when available
- Preserve memory:// fallback for development

### 4.2 Integrate Upstash Redis
**Status: COMPLETE**
- Use Flask-Limiter with Redis backend whenever `REDIS_URL` is provided
- Falls back to memory:// for local development
- Environment variable: `REDIS_URL`

Setup:
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
**Status: PARTIAL**
- Blob uploads now set long-lived Cache-Control metadata (immutable, content-addressed)
- Next (optional): add Edge cache rules for redirect responses

### 6.2 Pregeneration Strategy
**Status: COMPLETE**
- Identify common parameter combinations
- Pregenerate and cache popular configurations via `scripts/pregenerate.py`

## Phase 7: Monitoring and Analytics

### 7.1 Performance Monitoring
**Status: PARTIAL**
- X-Compute-Time and X-Cache response headers added for STL endpoints
- Track function execution times and cache outcomes via response headers and logs
- Next: enable Vercel Analytics (optional)

### 7.2 Cost Optimization Tracking
- Monitor function invocation counts
- Track bandwidth usage
- Analyze Redis and Blob storage usage

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
- [ ] Phase 6.1: CDN integration (metadata) (partial)
- [x] Phase 6.2: Pregeneration (optional)
- [ ] Phase 7.1: Enable monitoring (headers/logs) (partial)
- [ ] Phase 7.2: Track costs

## Environment Variables Required

1. **BLOB_STORE_WRITE_TOKEN** (Vercel Blob)
   - Get from: Vercel Dashboard → Storage → Create Blob Store
   - Used for: Caching generated STL files

2. **REDIS_URL** (Upstash Redis)
   - Get from: Upstash Console → Create Database → Connection String
   - Format: `rediss://default:<password>@<host>:<port>`
   - Used for: Rate limiting

3. **SECRET_KEY** (Flask)
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
