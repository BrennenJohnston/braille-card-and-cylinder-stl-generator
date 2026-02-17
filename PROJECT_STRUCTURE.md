# Project Structure

## Directory overview

```
braille-card-and-cylinder-stl-generator/
├── app/                      Main application package
│   ├── geometry/             Geometry generation (dots, plates, cylinders)
│   ├── api.py                API route handlers
│   ├── exporters.py          STL export (dev mode)
│   ├── geometry_spec.py      Geometry spec extraction for client-side CSG
│   ├── models.py             Data models and settings
│   ├── utils.py              Braille translation and helpers
│   └── validation.py         Input validation
├── docs/                     Documentation
│   ├── specifications/       Technical specs (17 files)
│   ├── deployment/           Deployment guides
│   ├── development/          Dev notes and implementation guides
│   ├── guides/               User-facing guides (cylinder, business card)
│   └── security/             Security docs and audit reports
├── public/                   Production HTML (served on Vercel)
├── scripts/                  Utility scripts
├── static/                   Frontend JS, CSS, Web Workers, liblouis tables
├── templates/                Dev HTML (served by Flask locally)
├── tests/                    Test suite
│   ├── fixtures/             Golden STL files for regression tests
│   ├── test_smoke.py         Endpoint smoke tests
│   └── test_golden.py        Golden file regression tests
├── third_party/              Vendored liblouis tables
├── backend.py                Flask app entry point
├── wsgi.py                   Vercel serverless entry point
├── requirements.txt          Production dependencies (Flask only)
├── requirements-dev.txt      Dev dependencies (numpy, trimesh, pytest, etc.)
├── settings.schema.json      JSON Schema for settings validation
└── vercel.json               Vercel deployment config
```

## How it works

The project uses a **client-side generation** architecture:

1. The browser sends text and settings to the server
2. The server translates the text (via liblouis) and returns a JSON geometry spec
3. The browser runs CSG boolean operations to build the 3D model
4. The STL file is generated and downloaded entirely in the browser

The server is minimal — just Flask serving static files and one JSON endpoint. All the heavy computation happens client-side using Web Workers.

### Backend

- **`backend.py`** — Flask server for local development
- **`wsgi.py`** — Serverless wrapper for Vercel
- **`app/models.py`** — `CardSettings` and `CylinderParams` data models
- **`app/geometry_spec.py`** — Builds the JSON geometry spec that the browser uses
- **`app/geometry/`** — Dot shapes, plate geometry, cylinder geometry, CSG operations (used in dev/test)

### Frontend

- **`static/workers/csg-worker.js`** — Web Worker using three-bvh-csg for flat cards
- **`static/workers/csg-worker-manifold.js`** — Web Worker using Manifold WASM for cylinders
- **`static/liblouis-worker.js`** — Web Worker for braille translation
- **Three.js** — 3D preview rendering
- **`public/index.html`** — Production build (served by Vercel)
- **`templates/index.html`** — Dev build (served by Flask)

These two HTML files must stay in sync.

### API endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve the UI |
| `/health` | GET | Health check |
| `/liblouis/tables` | GET | List braille translation tables |
| `/geometry_spec` | POST | Return geometry spec JSON for client-side CSG |

Old server-side STL endpoints (`/generate_braille_stl`, `/generate_counter_plate_stl`, `/lookup_stl`) return 410 Gone.

## Dependencies

**Production** (what Vercel installs):
- Flask, Flask-CORS

**Development** (what you install locally):
- numpy, trimesh, shapely — 3D geometry operations
- pytest, ruff, mypy — testing and linting

**Client-side**:
- Three.js — 3D rendering
- three-bvh-csg — CSG for flat cards
- Manifold WASM — CSG for cylinders (loaded from CDN)
- liblouis — braille translation (WASM)

## Configuration files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python metadata, ruff config |
| `vercel.json` | Vercel deployment settings |
| `settings.schema.json` | JSON Schema for settings validation |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff) |
