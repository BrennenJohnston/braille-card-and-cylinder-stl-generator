# Known Issues

This document tracks known issues in the Braille Card and Cylinder STL Generator.

---

## Active Issues

*No major issues are currently tracked.*

---

## Resolved Issues (Historical Reference)

### 1. Vercel Blob Storage Caching - RESOLVED (Removed)

**Status:** ✅ Resolved - Feature Removed
**Resolution Date:** 2026-01-05

**Original Issue:** Vercel Blob storage caching for counter plate STL files was not functioning correctly.

**Resolution:** The entire caching system (Redis + Blob storage) was removed from the application. The application now uses a minimal backend + client-side generation architecture where all STL files are generated in the browser. This eliminates the complexity and potential failure modes of external service dependencies.

See: `docs/specifications/CACHING_SYSTEM_CORE_SPECIFICATIONS.md` for historical details.

---

### 2. Upstash Redis Inactivity Failures - RESOLVED (Removed)

**Status:** ✅ Resolved - Feature Removed
**Resolution Date:** 2026-01-05

**Original Issue:** Upstash Redis free tier archives databases after 14 days of inactivity, causing all requests to fail with `redis.exceptions.ConnectionError`.

**Resolution:** Redis dependency was completely removed. The application no longer requires any external services.

---

### 3. Server-Side STL Generation on Vercel - RESOLVED (Removed)

**Status:** ✅ Resolved - Feature Removed
**Resolution Date:** 2026-01-05

**Original Issue:** The `manifold3d` library requires native binaries that aren't available in Vercel's Python runtime, preventing server-side STL generation.

**Resolution:** Server-side STL generation was replaced with client-side generation using:
- **BVH-CSG** for flat card shapes (via three-bvh-csg)
- **Manifold WASM** for cylinder shapes (loaded from CDN)

The server now only provides lightweight JSON geometry specifications via the `/geometry_spec` endpoint.

---

## Reporting New Issues

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/your-username/braille-card-and-cylinder-stl-generator/issues) for existing reports
2. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Browser and OS information
   - Console error messages (if any)

---

*Last updated: 2026-01-05*
