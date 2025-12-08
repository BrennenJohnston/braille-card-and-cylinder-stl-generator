# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2024-12-08

### 📚 Documentation Release

This release adds industry-standard documentation to the project.

### Added
- **LICENSE** — MIT License file
- **CHANGELOG.md** — Release history following Keep a Changelog format
- **CONTRIBUTING.md** — Comprehensive contribution guidelines

### Changed
- **README.md** — Added version/license/Python/accessibility badges
- **README.md** — Added Contributing, Changelog, and License sections
- **.gitignore** — Added OpenSCAD/ directory exclusion

---

## [1.0.0] - 2024-12-08

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

[1.0.1]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.0.1
[1.0.0]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v1.0.0
[Unreleased]: https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/compare/v1.0.1...HEAD
