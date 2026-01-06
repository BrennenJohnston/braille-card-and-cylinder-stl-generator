# Braille STL Generator

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-red.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![WCAG 2.1 AA](https://img.shields.io/badge/WCAG-2.1%20AA-green.svg)](https://www.w3.org/WAI/WCAG21/quickref/)

A web application that generates 3D-printable STL files for braille embossing plates and cylinders. Enter text, translate to braille, and export ready-to-print 3D models.

## Features

- **Automatic Braille Translation** — Powered by liblouis with support for Grade 1 and Grade 2 braille
- **Multiple Output Shapes** — Business card plates (flat) and cylindrical objects
- **Client-Side Generation** — STL files generated in-browser for fast iteration
- **Real-Time Preview** — 3D visualization before download
- **Configurable Parameters** — Adjust dot dimensions, spacing, and surface settings

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python backend.py
```

Open http://localhost:5001 in your browser.

### Production Deployment (Vercel)

1. Connect repository to Vercel
2. **(Optional)** Configure environment variables:
   - `SECRET_KEY` — Session key (optional for stateless backend)
   - `PRODUCTION_DOMAIN` — Your Vercel domain for CORS
   - See [Environment Variables](docs/security/ENVIRONMENT_VARIABLES.md) for details
3. Deploy

**Note:** No Redis, Blob storage, or external services required! The application works out of the box on Vercel.

## Usage

1. Enter text (up to 4 lines)
2. Select braille translation table and grade
3. Choose shape type (card or cylinder)
4. Configure dimensions and dot parameters as needed
5. Click Generate to create STL files
6. Download and 3D print

## Project Structure

```
├── app/                  # Application package
│   ├── geometry/         # 3D geometry generation
│   ├── geometry_spec.py  # Geometry specification extraction
│   ├── models.py         # Data models (dataclass/Enum)
│   ├── validation.py     # Input validation
│   └── utils.py          # Utility functions
├── docs/                 # Documentation
│   ├── specifications/   # Technical specifications
│   ├── deployment/       # Deployment guides
│   ├── development/      # Development guides
│   └── security/         # Security documentation
├── public/               # Public HTML files
├── static/               # Frontend assets (workers, libraries)
├── tests/                # Test suite
├── backend.py            # Flask application (minimal backend)
└── wsgi.py               # Vercel entry point
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed architecture.

## API Endpoints

**Active Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main UI |
| `/health` | GET | Health check |
| `/liblouis/tables` | GET | List braille translation tables |
| `/geometry_spec` | POST | Get geometry specification (for client-side CSG) |
| `/static/<path>` | GET | Serve static files (workers, libraries, tables) |

**Deprecated Endpoints (return 410 Gone):**

| Endpoint | Method | Status |
|----------|--------|--------|
| `/generate_braille_stl` | POST | ~~Removed 2026-01-05~~ (use client-side generation) |
| `/generate_counter_plate_stl` | POST | ~~Removed 2026-01-05~~ (use client-side generation) |
| `/lookup_stl` | GET | ~~Removed 2026-01-05~~ (cache removed) |
| `/debug/blob_upload` | GET | ~~Removed 2026-01-05~~ (blob storage removed) |

**Architecture Note:** Server-side STL generation has been removed to eliminate Redis and Blob storage dependencies. All STL generation now happens client-side using Web Workers (BVH-CSG for cards, Manifold WASM for cylinders). See [CODEBASE_AUDIT_AND_RENOVATION_PLAN.md](docs/development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md) for details.

## Development

### Requirements

- Python 3.12+
- Node.js (for frontend dependencies)

### Running Tests

```bash
# Install dev/test dependencies
pip install -r requirements-dev.txt

pytest
```

### Code Quality

```bash
# Install dev/test dependencies (includes ruff)
pip install -r requirements-dev.txt

# Linting and formatting
ruff check .
ruff format .
```

The project uses pre-commit hooks for consistent code quality.

## Documentation

- [Project Structure](PROJECT_STRUCTURE.md) — Architecture overview
- [Specifications Index](docs/specifications/SPECIFICATIONS_INDEX.md) — Technical specifications
- [Deployment Checklist](docs/deployment/DEPLOYMENT_CHECKLIST.md) — Production deployment guide
- [Environment Variables](docs/security/ENVIRONMENT_VARIABLES.md) — Configuration reference
- [Client-Side CSG](docs/development/CLIENT_SIDE_CSG_DOCUMENTATION.md) — Browser-based generation

## Technology Stack

**Backend (Minimal):**
- Flask — Web framework (serves static files and JSON geometry specs)
- Python Standard Library — All computation uses stdlib only

**Frontend (Client-Side Generation):**
- Three.js — 3D rendering and visualization
- three-bvh-csg — Client-side CSG for cards
- Manifold WASM — Client-side CSG for cylinders
- liblouis — Braille translation (WebAssembly)
- Web Workers — Background STL generation

**Development Only:**
- NumPy, Trimesh, Shapely — Optional server-side generation (local dev)
- Manifold3D — Optional local boolean operations

## Acknowledgments

Thanks to **Tobi Weinberg** for kick-starting the project.

Originally based on [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator).

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history and version changes.

## License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**.

- ✅ Free for personal, educational, and non-commercial use
- ✅ Modification and remixing allowed
- ❌ **No commercial use permitted**

See the [LICENSE](LICENSE) file for full terms.
