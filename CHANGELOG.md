# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-06

### 🎯 Zero-Maintenance Stable Release

This major release represents the most stable and reliable version of the Braille STL Generator, optimized for zero-maintenance deployment.

### Changed
- **Default Braille Dot Shape** — Changed default to Cone shape for improved print quality and readability
- **Simplified Architecture** — Removed external dependencies for zero-maintenance operation

### Removed
- **Upstash Redis** — Removed Redis caching dependency (no longer required)
- **Vercel Blob Storage** — Removed blob storage dependency (no longer required)

### Fixed
- **Documentation** — Comprehensive cleanup and refresh for public release

---

## [1.3.0] - 2025-12-09

### 🏛️ Community Infrastructure & License Update

This release establishes GitHub community standards and changes to a noncommercial license.

### Changed
- **LICENSE** — Changed from MIT to PolyForm Noncommercial License 1.0.0 (no commercial use permitted)
- **Dependencies** — Synchronized `requirements.txt` and `requirements-dev.txt` with dev dependencies

### Added
- **GitHub Actions CI** — Automated testing, linting, Lighthouse accessibility audits, and W3C HTML validation
- **Issue Templates** — Bug report and feature request templates
- **Pull Request Template** — Standardized PR description format
- **Dependabot** — Automated dependency updates for pip and npm
- **SECURITY.md** — Security policy with vulnerability reporting guidelines
- **CODE_OF_CONDUCT.md** — Contributor Covenant Code of Conduct v2.0
- **lighthouserc.json** — Lighthouse CI configuration for accessibility testing
- **package.json** — Node.js configuration for Lighthouse CI
- **.vercelignore** — Exclude unnecessary files from Vercel deployments

### Fixed
- **CI** — Lighthouse CI configuration for accessibility audits
- **CI** — Added `manifold3d` and `scipy` to dev dependencies for STL generation tests
- **CI** — Set `FLASK_ENV=development` for pytest runs
- **CI** — Synchronized ruff version between pre-commit and CI workflow
- **CI** — Corrected requirements filename reference
- **CI** — Use specific version tag for html5validator-action
- **Vercel** — Reduced serverless function size under 250 MB limit

### Removed
- Removed AI tool-specific plan files and references from repository

---

## [1.2.0] - 2024-12-08

### 📚 Documentation Release

This release adds industry-standard documentation to the project.

### Added
- **LICENSE** — PolyForm Noncommercial License 1.0.0 (no commercial use permitted)
- **CHANGELOG.md** — Release history following Keep a Changelog format
- **CONTRIBUTING.md** — Comprehensive contribution guidelines

### Changed
- **README.md** — Added version/license/Python/accessibility badges
- **README.md** — Added Contributing, Changelog, and License sections
- **.gitignore** — Added OpenSCAD/ directory exclusion

---

## [1.1.0] - 2024-12-08

### Features & Fixes
- Mobile compatibility improvements (lazy WASM loading)
- Dead code cleanup (~680 lines removed)
- ADA Accessibility Validation SOP
- WCAG 2.1 Level AA compliance verified

---

## [1.0.0] - 2024-09-27

### 🎉 First Stable Release

This marks the first stable release of the Braille STL Generator, a web application
for generating 3D-printable STL files for braille embossing plates and cylinders.

### Features

#### Core Functionality
- **Braille Text Translation** — Automatic translation using liblouis with support for Grade 1 and Grade 2 braille
- **Multi-Language Support** — 50+ translation tables for various languages and braille codes
- **Dual Shape Support** — Generate flat business card plates or cylindrical objects
- **Real-Time 3D Preview** — Interactive Three.js visualization before download
- **STL Export** — Download ready-to-print 3D models

#### Client-Side Generation
- **Browser-Based CSG** — STL generation runs entirely in the browser using three-bvh-csg
- **Manifold WASM Integration** — High-performance cylinder generation via WebAssembly
- **Lazy WASM Loading** — Improved mobile compatibility with on-demand module loading
- **Server Fallback** — Automatic fallback to server-side generation when needed

#### Customization Options
- **Configurable Dimensions** — Adjust card/cylinder size, thickness, and margins
- **Braille Dot Parameters** — Fine-tune dot height, diameter, and spacing
- **Embossing Plates** — Generate both positive and negative plates for embossing
- **Recess Indicators** — Optional visual markers for plate orientation

#### User Interface
- **Responsive Design** — Works on desktop and mobile devices
- **Dark Mode Support** — Automatic theme based on system preference
- **Accessible Interface** — WCAG 2.1 Level AA compliant
- **Translation Preview** — Real-time braille preview before generation

### Technical Highlights

- **Python 3.12** — Modern Python with full type hints
- **Flask Backend** — Lightweight web framework
- **Vercel Deployment** — Production-ready serverless deployment
- **Comprehensive Testing** — pytest suite with smoke and golden tests
- **Pre-commit Hooks** — Automated code quality with ruff
- **Security Hardened** — Rate limiting, input validation, CSP headers

### Documentation

- Complete API documentation
- Technical specifications for all subsystems
- Deployment guides for Vercel
- Security documentation and environment variable reference
- ADA Accessibility Validation SOP

### Acknowledgments

Thanks to **Tobi Weinberg** for kick-starting the project.

Based on [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator).

---

## [Unreleased]

### Planned
- Additional language support
- Custom dot shape options
- Batch processing
- OpenSCAD export option

[2.0.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v2.0.0
[1.3.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.3.0
[1.2.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.2.0
[1.1.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.1.0
[1.0.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.0.0
[Unreleased]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/compare/v2.0.0...HEAD
