# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-02-16

Documentation overhaul. Rewrote all project docs to remove AI-generated language and match the tone of a small, single-maintainer open-source project.

### Changed
- Rewrote README, CONTRIBUTING, SECURITY, CHANGELOG, PROJECT_STRUCTURE, and RELEASING
- Rewrote all docs in docs/security/, docs/deployment/, and docs/development/
- Trimmed ENVIRONMENT_VARIABLES.md, KNOWN_ISSUES.md, and the specifications index
- Cleaned up "comprehensive", "robust", and other AI patterns across specification files
- Cut MAJOR_FEATURE_IMPLEMENTATION_SOP from 1000+ lines to a practical 70-line checklist
- Updated bug report template and GitHub repository metadata

### Removed
- docs/development/IMPLEMENTATION_PROCESS_ANALYSIS.md (530-line AI self-review with no value for contributors)

---

## [2.0.0] - 2026-01-06

Major architecture change: removed all external service dependencies. The server is now a minimal Flask app that serves geometry specs — all STL generation happens in the browser.

### Why v2.0.0

- Removed Upstash Redis (free tier archives after 14 days of inactivity, breaking the app)
- Removed Vercel Blob storage (no longer needed)
- Moved all STL generation to client-side Web Workers
- Server now only needs Flask and Flask-CORS

### Added
- Python 3.13 support
- Health check loop in CI for stable Lighthouse audits
- Updated all GitHub Actions, npm, and pip packages to latest stable versions

### Changed
- Default braille dot shape is now cone (better print quality and tactile feel)
- Server only provides geometry specs; all CSG operations run client-side
- GitHub Actions updated to checkout@v6, setup-python@v6, setup-node@v6
- three-mesh-bvh updated to 0.9.4

### Removed
- Upstash Redis dependency
- Vercel Blob storage dependency
- Server-side STL generation
- Flask-Limiter (Vercel handles DDoS protection)
- requests library (was only used for blob upload)

### Fixed
- CI pipeline PORT variable for Flask server
- Replaced fixed sleep with health check loop in CI

---

## [1.3.0] - 2025-12-09

GitHub community infrastructure and license change.

### Changed
- License changed from MIT to PolyForm Noncommercial 1.0.0

### Added
- GitHub Actions CI (testing, linting, Lighthouse accessibility audits, W3C validation)
- Issue and PR templates
- Dependabot for pip and npm
- SECURITY.md, CODE_OF_CONDUCT.md
- lighthouserc.json, package.json, .vercelignore

### Fixed
- Various CI configuration issues (manifold3d deps, FLASK_ENV, ruff version sync, requirements filename, html5validator version)
- Reduced Vercel serverless function size under 250 MB limit

### Removed
- AI tool-specific plan files

---

## [1.2.0] - 2024-12-08

Documentation release.

### Added
- LICENSE (PolyForm Noncommercial 1.0.0)
- CHANGELOG.md
- CONTRIBUTING.md

### Changed
- README updated with badges and new sections
- .gitignore updated with OpenSCAD exclusion

---

## [1.1.0] - 2024-12-08

- Mobile compatibility improvements (lazy WASM loading)
- Dead code cleanup (~680 lines removed)
- WCAG 2.1 Level AA compliance verified

---

## [1.0.0] - 2024-09-27

First stable release.

### Features
- Braille text translation via liblouis (Grade 1 and Grade 2, 50+ language tables)
- Flat business card plates and cylindrical objects
- Real-time 3D preview with Three.js
- Client-side STL generation with three-bvh-csg and Manifold WASM
- Configurable dimensions, dot parameters, and embossing plate options
- Responsive UI with dark mode and WCAG 2.1 AA accessibility
- Vercel deployment with Flask backend

### Acknowledgments

Thanks to Tobi Weinberg for kick-starting the project. Based on [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator).

---

## [Unreleased]

### Planned
- Additional language support
- Custom dot shape options
- Batch processing
- OpenSCAD export option

[2.1.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v2.1.0
[2.0.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v2.0.0
[1.3.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.3.0
[1.2.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.2.0
[1.1.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.1.0
[1.0.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.0.0
[Unreleased]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/compare/v2.1.0...HEAD
