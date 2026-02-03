# Archived Deployment Documentation

> **Note:** The documents in this folder are **historical artifacts** from v1.x development. They describe issues and fixes for systems that have been **removed** in v2.0.0.

## Why These Are Archived

v2.0.0 introduced a **zero-maintenance architecture** that eliminated:
- Server-side STL generation
- Redis caching
- Vercel Blob storage
- Rate limiting (Flask-Limiter)
- Complex dependencies (shapely, manifold3d on server)

These documents describe fixes for problems that no longer exist.

## Archived Documents

| Document | Original Issue | Why Obsolete |
|----------|---------------|--------------|
| `VERCEL_BOOLEAN_BACKEND_FIX.md` | Server-side boolean operations failing | Server-side generation removed |
| `VERCEL_COUNTER_PLATE_BUG_FIX.md` | Server-side counter plate generation | Server-side generation removed |
| `VERCEL_RUNTIME_FIX.md` | Default shape type bug | Fixed long ago |
| `DEPLOYMENT_FIX_SUMMARY.md` | Shapely build errors | Shapely dependency removed |
| `VERCEL_DEPLOYMENT_FIX.md` | Various v1.x dependencies | Dependencies changed |
| `VERCEL_PREVIEW_DEPLOYMENT_NOTE.md` | mapbox_earcut module issues | Module replaced/removed |

## Current Documentation

For v2.0.0 deployment guidance, see:
- [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) — Primary deployment guide
- [VERCEL_DEPLOYMENT.md](../VERCEL_DEPLOYMENT.md) — Vercel-specific setup

---

*Archived: 2026-02-02*
