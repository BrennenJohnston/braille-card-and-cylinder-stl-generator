# Project Structure

This document describes the organization of the Braille Card and Cylinder STL Generator codebase.

## 📁 Directory Overview

```
braille-card-and-cylinder-stl-generator/
├── app/                      # Main application package
│   ├── geometry/            # Geometry generation modules
│   ├── api.py               # API route handlers
│   ├── cache.py             # Caching system
│   ├── exporters.py         # STL export functionality
│   ├── geometry_spec.py     # Geometry specification extraction for client-side CSG
│   ├── models.py            # Data models and settings
│   ├── utils.py             # Utility functions
│   └── validation.py        # Input validation
├── docs/                     # Documentation (organized by category)
│   ├── specifications/      # Technical specifications (17 files)
│   ├── deployment/          # Deployment guides and fixes (13 files)
│   ├── development/         # Development guides and notes (13 files)
│   ├── security/            # Security documentation and audit (6 files)
│   └── progress/            # Development progress tracking (18 files)
├── public/                   # Public static HTML (Vercel deployment)
├── scripts/                  # Utility scripts for development and deployment
├── static/                   # Static assets (JS, CSS, fonts, liblouis tables)
├── templates/                # Flask HTML templates
├── tests/                    # Test suite
│   ├── fixtures/            # Test fixtures (golden files)
│   ├── conftest.py          # Pytest configuration
│   ├── test_smoke.py        # Smoke tests
│   └── test_golden.py       # Golden file regression tests
├── third_party/              # Third-party dependencies (liblouis tables)
├── backend.py                # Main Flask application
├── wsgi.py                   # WSGI entry point for Vercel serverless
├── requirements.txt          # Python dependencies (serverless minimal for Vercel)
├── requirements-dev.txt      # Development dependencies
├── package.json              # Node.js dependencies
├── vercel.json               # Vercel deployment configuration
├── pyproject.toml            # Python project metadata
├── .cursorrules              # Cursor AI development rules
└── README.md                 # Main project documentation
```

## 🏗️ Architecture Overview

### Backend (Python/Flask)

**Entry Points:**
- **Local Development**: `backend.py` - Full Flask server with hot reload
- **Production (Vercel)**: `wsgi.py` - Serverless WSGI wrapper

**Application Package (`app/`):**
- **`models.py`**: `CardSettings`, `CylinderParams` - Pydantic data models
- **`validation.py`**: Input validation for braille text and settings
- **`geometry_spec.py`**: Extracts geometry specifications for client-side CSG
- **`api.py`**: Additional API route handlers
- **`cache.py`**: Content-addressable caching system
- **`exporters.py`**: STL file generation and export
- **`utils.py`**: Braille translation, logging, and helper functions

**Geometry Package (`app/geometry/`):**
- **`braille_layout.py`**: Braille cell positioning and markers
- **`dot_shapes.py`**: Dot geometry (cone, hemisphere, rounded)
- **`plates.py`**: Plate base geometry
- **`cylinder.py`**: Cylindrical braille surface generation
- **`booleans.py`**: CSG operations (union, difference) using trimesh

### Frontend (Browser)

**Static Assets (`static/`):**
- **Three.js**: 3D rendering and STL preview
- **three-bvh-csg**: Client-side CSG boolean operations
- **liblouis-worker.js**: Web Worker for braille translation
- **csg-worker.js**: Web Worker for STL generation
- **OrbitControls.js**: 3D camera controls

**HTML Templates:**
- **`templates/index.html`**: Development version (served by Flask)
- **`public/index.html`**: Production version (served by Vercel)

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main UI |
| `/health` | GET | Health check |
| `/liblouis/tables` | GET | List available braille translation tables |
| `/geometry_spec` | POST | Generate geometry specification (JSON) for client-side CSG |
| `/generate_braille_stl` | POST | Generate embossing plate STL (server-side fallback) |
| `/generate_counter_plate_stl` | POST | Generate counter plate STL (server-side fallback) |
| `/lookup_stl` | GET | Check cache for existing STL |

## 📚 Documentation Structure

### `docs/specifications/` (16 files)
Technical specifications for all features:
- UI Interface and settings schema
- Braille text input, translation, and preview
- Surface dimensions and dot adjustments
- Dot shapes and recess indicators
- STL export and caching systems
- Liblouis translation integration

**Key Files:**
- `SPECIFICATIONS_INDEX.md` - Master index of all specifications
- `UI_INTERFACE_CORE_SPECIFICATIONS.md` - UI architecture
- `VERIFICATION_GUIDE.md` - Testing procedures

### `docs/development/` (11 files)
Development guides and implementation notes:
- Client-side CSG implementation
- Manifold3D WASM integration (optional)
- Bug fix documentation
- Development notes and tooling

**Key Files:**
- `CLIENT_SIDE_CSG_DOCUMENTATION.md` - Browser-based STL generation
- `CLIENT_SIDE_CSG_TEST_PLAN.md` - Testing guide

### `docs/deployment/` (13 files)
Deployment guides and production fixes:
- Vercel deployment guides
- Deployment checklists
- Runtime fixes and optimizations

**Key Files:**
- `DEPLOYMENT_CHECKLIST.md` - Pre-release verification
- `VERCEL_DEPLOYMENT.md` - Vercel setup guide

### `docs/security/` (6 files)
Security documentation and configuration:
- Security audit reports and findings
- Environment variable configuration
- Security implementation summary

**Key Files:**
- `ENVIRONMENT_VARIABLES.md` - Production configuration guide
- `SECURITY_IMPLEMENTATION_SUMMARY.md` - Security improvements summary
- `SECURITY_AUDIT_REPORT.md` - Detailed audit findings

### `docs/progress/` (18 files)
Historical development tracking:
- Phase summaries (Phases 0, 1.1, 1.2, 4, 6)
- Refactoring session notes
- Migration checkpoints

## 🔧 Scripts (`scripts/`)

**Active Scripts:**
- **`smoke_test.py`**: Quick health check of core endpoints
- **`pregenerate.py`**: Pre-warm cache with common configurations
- **`git_check.bat`**: Output git status/log to file for debugging
- **`git_push.ps1`**: Automated git stage, commit, and push workflow

**Archived Scripts** (historical reference):
- `build_cylinder_module.py`, `extract_cylinder_functions.py`, `remove_cylinder_funcs.py` - Refactoring utilities
- `replace_prints_with_logging.py` - Code quality utility

See `scripts/README.md` for detailed usage.

## 🧪 Tests (`tests/`)

**Test Files:**
- **`test_smoke.py`**: Basic endpoint smoke tests
- **`test_golden.py`**: Regression tests using golden STL files
- **`conftest.py`**: Pytest configuration and fixtures
- **`generate_golden_fixtures.py`**: Regenerate golden test files

**Fixtures (`tests/fixtures/`):**
- Golden STL files for regression testing
- JSON parameter files for test cases

## 🚀 Deployment

### Local Development
```bash
pip install -r requirements.txt
python backend.py  # Opens http://localhost:5001
```

### Vercel Deployment
- Uses `wsgi.py` as serverless entry point
- Minimal dependencies from `requirements.txt`
- Static assets bundled in deployment
- See `docs/deployment/DEPLOYMENT_CHECKLIST.md`

## 📝 Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project metadata, ruff linting config |
| `vercel.json` | Vercel deployment settings |
| `.vercelignore` | Files excluded from deployment |
| `.gitignore` | Git exclusions |
| `.cursorrules` | Cursor AI development guidelines |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `settings.schema.json` | JSON Schema for settings validation |

## 🔑 Key Dependencies

**Python:**
- `flask` - Web framework
- `trimesh` - 3D mesh operations and STL export
- `numpy` - Numerical operations
- `pydantic` - Data validation
- `shapely` - 2D geometry operations

**JavaScript:**
- `three.js` - 3D rendering
- `three-bvh-csg` - Client-side boolean operations
- `liblouis` - Braille translation

## 📖 Additional Resources

- **Main Documentation**: [README.md](README.md)
- **Documentation Index**: [docs/README.md](docs/README.md)
- **Specifications Index**: [docs/specifications/SPECIFICATIONS_INDEX.md](docs/specifications/SPECIFICATIONS_INDEX.md)
- **Scripts Guide**: [scripts/README.md](scripts/README.md)

---

*This structure follows Python project best practices with clear separation of concerns, comprehensive documentation, and professional organization suitable for open-source release.*

*Last updated: December 2024*
