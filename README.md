# Braille STL Generator

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/owner/braille-card-and-cylinder-stl-generator/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
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
2. Configure required environment variables (see [Environment Variables](docs/security/ENVIRONMENT_VARIABLES.md))
3. Deploy

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
│   ├── models.py         # Data models (Pydantic)
│   ├── validation.py     # Input validation
│   └── cache.py          # Caching system
├── docs/                 # Documentation
│   ├── specifications/   # Technical specifications
│   ├── deployment/       # Deployment guides
│   ├── development/      # Development guides
│   └── security/         # Security documentation
├── static/               # Frontend assets
├── tests/                # Test suite
├── backend.py            # Flask application
└── wsgi.py               # Vercel entry point
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed architecture.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main UI |
| `/health` | GET | Health check |
| `/liblouis/tables` | GET | List braille translation tables |
| `/geometry_spec` | POST | Get geometry specification (for client-side CSG) |
| `/generate_braille_stl` | POST | Generate embossing plate (server fallback) |
| `/generate_counter_plate_stl` | POST | Generate counter plate (server fallback) |

## Development

### Requirements

- Python 3.12+
- Node.js (for frontend dependencies)

### Running Tests

```bash
pytest
```

### Code Quality

```bash
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

**Backend:**
- Flask — Web framework
- Trimesh — 3D mesh operations
- NumPy/SciPy — Numerical computing
- Shapely — 2D geometry

**Frontend:**
- Three.js — 3D rendering
- three-bvh-csg — Client-side boolean operations
- liblouis — Braille translation (WebAssembly)

## Acknowledgments

Thanks to **Tobi Weinberg** for kick-starting the project.

Originally based on [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator).

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history and version changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
