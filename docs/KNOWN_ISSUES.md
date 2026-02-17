# Known Issues

No major issues are currently tracked.

## Resolved (historical)

These issues existed in v1.x and were resolved by removing the systems entirely in v2.0.0:

1. **Vercel Blob storage caching** — Blob caching for counter plate STLs didn't work reliably. Resolved by removing Blob storage and moving to client-side generation.

2. **Upstash Redis inactivity failures** — Free tier archives databases after 14 days of inactivity, causing all requests to fail. Resolved by removing Redis entirely.

3. **Server-side STL generation on Vercel** — manifold3d requires native binaries not available in Vercel's Python runtime. Resolved by moving all generation to client-side (three-bvh-csg for cards, Manifold WASM for cylinders).

## Reporting issues

Check [GitHub Issues](https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/issues) first, then open a new issue with steps to reproduce, browser/OS info, and any console errors.
