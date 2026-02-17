# Braille STL Generator

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases/tag/v2.1.0)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-red.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A web app for generating 3D-printable braille. Type your text, pick a braille translation table, and download an STL file you can send straight to your 3D printer.

The goal is to make braille labels and cards accessible to anyone with a 3D printer, without needing to know braille yourself. The app handles translation (via [liblouis](https://liblouis.io/)) and turns it into a ready-to-print 3D model.

## What it does

- Translates text to Grade 1 or Grade 2 braille across 50+ language tables
- Generates STL files for cylindrical braille labels (jars, bottles, containers, etc.)
- All STL generation runs in the browser — nothing gets uploaded
- Shows a 3D preview before you download
- Flat business card plates are temporarily disabled while I rework that feature

## Quick start

### Running locally

```bash
pip install -r requirements.txt
python backend.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser.

### Deploying to Vercel

1. Connect the repo to Vercel
2. Deploy

That's it. No Redis, no blob storage, no API keys to manage. The server just serves static files and a lightweight JSON endpoint — all the heavy geometry work happens in your browser.

You can optionally set `SECRET_KEY` and `PRODUCTION_DOMAIN` as environment variables, but neither is required. See [Environment Variables](docs/security/ENVIRONMENT_VARIABLES.md) if you're curious.

## How to use it

1. Type your text (up to 4 lines)
2. Pick a braille translation table and grade
3. Set your cylinder dimensions — measure your container first
4. Click Generate
5. Download the STL and 3D print it

There's a **Help** button inside the app that walks you through choosing what to include, formatting your text, and measuring containers. For more depth, check the guides below.

## OpenSCAD version

Prefer working offline or want full parametric control? There's a standalone OpenSCAD version of this tool:

[braille-stl-generator-openscad](https://github.com/BrennenJohnston/braille-stl-generator-openscad)

The web app translates automatically; the OpenSCAD version needs you to translate manually (using [Branah.com](https://www.branah.com/braille-translator)), but it works without an internet connection and integrates with existing CAD workflows.

## Project layout

```
app/              Flask backend, geometry specs, validation
public/           Production HTML (served on Vercel)
static/           Frontend JS, CSS, Web Workers, liblouis tables
templates/        Development HTML (served by Flask locally)
tests/            Smoke tests and golden file regression tests
docs/             Guides, technical specs, deployment notes
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for the full breakdown.

## Development

Requires Python 3.12+.

```bash
pip install -r requirements-dev.txt

# Run tests
pytest

# Lint and format
ruff check .
ruff format .
```

Pre-commit hooks are included — run `pre-commit install` to set them up.

## Guides

**Using the app:**

- [Cylinder Guide](docs/guides/CYLINDER_GUIDE.md) — measuring containers, setting parameters, worked examples
- [Business Card Guide](docs/guides/BUSINESS_CARD_TRANSLATION_GUIDE.md) — what to include, formatting tips (flat cards are temporarily disabled)

**Working on the code:**

- [Project Structure](PROJECT_STRUCTURE.md)
- [Specifications Index](docs/specifications/SPECIFICATIONS_INDEX.md)
- [Client-Side CSG](docs/development/CLIENT_SIDE_CSG_DOCUMENTATION.md)
- [Deployment Checklist](docs/deployment/DEPLOYMENT_CHECKLIST.md)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Acknowledgments

This project started from [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator) by Tobi Weinberg. Thanks to Tobi for getting it off the ground.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)

Free for personal, educational, and non-commercial use. Modification and remixing allowed. No commercial use.
