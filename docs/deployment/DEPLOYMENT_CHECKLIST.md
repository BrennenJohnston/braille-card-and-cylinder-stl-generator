# Deployment Checklist - Braille Card Generator v2.0.0

> **Zero-Maintenance Architecture:** v2.0.0 requires no external services. Deploy once, run forever.

## Architecture Overview

| Component | v1.x | v2.0.0 |
|-----------|------|--------|
| External Services | Redis + Blob Storage | **None** |
| STL Generation | Server-side | **100% Client-side** |
| Server Dependencies | ~15 packages | **2 packages** (Flask, Flask-CORS) |
| Required Secrets | 5+ | **None** (all optional) |

## Pre-Deployment Checklist

### Security Measures (Built-In)

- [x] Input validation and sanitization (100KB request limit)
- [x] Security headers (CSP, XSS protection, etc.)
- [x] Path traversal protection
- [x] Error handling that doesn't expose sensitive information
- [x] Minimal server attack surface (only serves JSON specs and static files)
- [x] No secrets required (Vercel handles DDoS protection)

### Environment Variables

All environment variables are **optional** in v2.0.0:

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | No | Flask session key (not used in stateless backend) |
| `FLASK_ENV` | No | Set to `production` for production mode |
| `PRODUCTION_DOMAIN` | No | Custom domain for CORS (Vercel domains allowed by default) |
| `LOG_LEVEL` | No | Logging verbosity (default: INFO) |

**Generate a secret key (if needed):**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### CORS Configuration

CORS is configured automatically:
- Vercel preview/production domains are allowed
- Custom domain via `PRODUCTION_DOMAIN` environment variable
- No code changes needed

## Deployment Steps (Vercel)

### 1. Connect Repository
1. Push code to GitHub
2. Connect repository to Vercel
3. Select framework preset: **Other**

### 2. Configure Build
Vercel auto-detects Python from `requirements.txt`:
- Install Command: `pip install -r requirements.txt`
- Build Command: (none)
- Output Directory: (none)

### 3. Deploy
Click Deploy. No environment variables required!

**Optional:** Add `PRODUCTION_DOMAIN` if using a custom domain.

## Post-Deployment Testing

### Functionality Tests
- [ ] Generate embossing plate STL (card shape)
- [ ] Generate counter plate STL (card shape)
- [ ] Generate embossing cylinder STL
- [ ] Generate counter cylinder STL
- [ ] Test braille translation preview
- [ ] Test multiple languages
- [ ] Test expert mode parameters
- [ ] Test accessibility features (keyboard navigation, screen reader)
- [ ] Test mobile responsiveness

### Security Tests
- [ ] Attempt XSS injection in text inputs
- [ ] Try malformed JSON requests
- [ ] Test file path traversal attempts
- [ ] Verify error handling doesn't leak info
- [ ] Test with very large inputs (should reject > 100KB)
- [ ] Check security headers at [securityheaders.com](https://securityheaders.com)

### Performance Tests
- [ ] STL generation time (client-side, typically < 5s)
- [ ] Frontend load time (target: < 3s on desktop)
- [ ] Mobile performance (test on actual devices)
- [ ] Manifold WASM loading (first load ~2-3s)

## Endpoints

### Active Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main UI |
| `/health` | GET | Health check |
| `/liblouis/tables` | GET | List braille translation tables |
| `/geometry_spec` | POST | Get geometry specification (JSON) |
| `/static/<path>` | GET | Serve static files |

### Deprecated Endpoints (Return 410 Gone)

| Endpoint | Removed |
|----------|---------|
| `/generate_braille_stl` | 2026-01-05 (use client-side generation) |
| `/generate_counter_plate_stl` | 2026-01-05 (use client-side generation) |
| `/lookup_stl` | 2026-01-05 (cache removed) |

## Monitoring

### Key Metrics
- Health endpoint response time (`/health`)
- Translation table loading (`/liblouis/tables`)
- Geometry spec response time (`/geometry_spec`)

### What You Don't Need to Monitor
- Redis/cache health (removed)
- Blob storage quotas (removed)
- Server-side STL generation times (removed)
- Rate limiting (handled by Vercel)

## Troubleshooting

### Common Issues

**"Manifold worker not available" on mobile:**
- This is expected on first load. WASM loads lazily.
- User can refresh if timeout occurs.

**STL generation fails:**
- Check browser console for JavaScript errors
- Verify WASM is loading from CDN
- Try a different browser

**Translation preview empty:**
- Check liblouis tables are serving
- Verify `/liblouis/tables` returns JSON

### Getting Help

1. Check [Known Issues](../KNOWN_ISSUES.md)
2. Check browser console for errors
3. Open GitHub issue with reproduction steps

## Rollback

To rollback to a previous deployment on Vercel:
1. Go to Deployments tab
2. Click on previous deployment
3. Click "Promote to Production"

## Final Checklist

- [ ] Deployment successful (no build errors)
- [ ] Health check responds (`/health`)
- [ ] Main UI loads
- [ ] Card STL generation works
- [ ] Cylinder STL generation works
- [ ] Braille translation works
- [ ] Mobile tested
- [ ] Accessibility tested

**✅ Ready for Public Use!**

---

*Last updated: 2026-02-02*
*Architecture: v2.0.0 Zero-Maintenance*
