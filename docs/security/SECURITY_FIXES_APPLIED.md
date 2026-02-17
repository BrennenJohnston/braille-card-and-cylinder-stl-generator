# Security Fixes Applied

**Date:** December 7, 2025

> **Note:** This document covers fixes applied to the pre-2026 architecture. Many of the systems referenced here (Redis, Blob storage, rate limiting, server-side STL generation) were removed in v2.0.0 (January 2026). The fixes are documented here for historical reference.
>
> For current configuration, see [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).

## Summary

14 issues were identified in the security audit and fixed:

| Severity | Count | Key fixes |
|----------|-------|-----------|
| Critical | 1 | CORS misconfiguration — now uses environment variables |
| High | 3 | SECRET_KEY enforcement, XSS fix (innerHTML to textContent), Redis TLS |
| Medium | 6 | Subprocess hardening, request size limits, rate limiting, CSP, security headers, debug endpoint |
| Low | 4 | Filename sanitization, static file headers, Redis password redaction, input validation |

## Files modified

- `backend.py` — 15 security improvements (~200 lines)
- `public/index.html` — XSS fix (textContent)
- `app/cache.py` — Redis TLS + password redaction (removed in v2.0.0)
- `app/validation.py` — Added `validate_original_lines()`
- `wsgi.py` — Subprocess restricted to dev mode

## Post-v2.0.0 hardening (January 2026)

Additional fixes applied after the architecture change:

- **Worker message validation** — All three Web Workers now validate message types and required fields
- **innerHTML XSS prevention** — Translation error display uses safe DOM building
- **Path traversal hardening** — Static file handler rejects `..`, absolute paths, and null bytes
- **CSP update** — Added `wasm-unsafe-eval` for modern browsers alongside `unsafe-eval` fallback
- **Template deprecation** — `templates/index.html` has a deprecation notice pointing to `public/index.html`

## Full details

See [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) for the complete findings from the original audit.
