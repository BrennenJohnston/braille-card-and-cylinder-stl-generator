# Release Process

This document describes the release process for the Braille STL Generator.

## Versioning Scheme

This project follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

| Version Bump | When to Use | Examples |
|--------------|-------------|----------|
| **MAJOR** | Breaking changes to API, geometry output, or workflow | Changing JSON spec structure, removing features |
| **MINOR** | New features, non-breaking enhancements | New language support, UI improvements |
| **PATCH** | Bug fixes, documentation, security patches | Fixing geometry bugs, updating dependencies |

## Current Version

Version is tracked in two places (keep synchronized):
- `package.json` → `"version": "X.Y.Z"`
- `pyproject.toml` → `version = "X.Y.Z"`

## Release Cadence

- **Patch releases**: As needed for bug fixes and security updates
- **Minor releases**: When significant features are complete
- **Major releases**: Rare, only for breaking changes

## Pre-Release Checklist

Before creating a release, verify:

### 1. Tests Pass

```bash
# Python tests
pytest tests/ -v

# Golden fixture tests (geometry regression)
pytest tests/test_golden.py -v

# Smoke tests
pytest tests/test_smoke.py -v
```

### 2. Linting Clean

```bash
# Python linting
ruff check .
ruff format --check .

# Type checking (optional but recommended)
mypy app/
```

### 3. Accessibility Validation

```bash
# Start server
python backend.py &

# Run Lighthouse (requires npm install -g lighthouse)
lighthouse http://localhost:5001 --only-categories=accessibility
```

Target: **100/100** accessibility score

### 4. Manual Smoke Test

- [ ] Load application in browser
- [ ] Enter braille text, verify translation
- [ ] Generate card STL (positive and negative)
- [ ] Generate cylinder STL (positive and negative)
- [ ] Download STL files
- [ ] Verify 3D preview renders correctly
- [ ] Test on mobile device

### 5. Security Check

- [ ] No secrets in committed code
- [ ] Dependencies are up to date (`pip-audit`, `npm audit`)
- [ ] CSP headers are intact

## Release Steps

### 1. Update Version Numbers

```bash
# Edit both files to new version
# package.json: "version": "X.Y.Z"
# pyproject.toml: version = "X.Y.Z"
```

### 2. Update CHANGELOG.md

Add a new section at the top following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Changed behavior description

### Fixed
- Bug fix description

### Removed
- Removed feature description
```

### 3. Commit and Tag

```bash
git add package.json pyproject.toml CHANGELOG.md
git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```

### 4. Create GitHub Release

1. Go to [Releases](https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/releases)
2. Click "Draft a new release"
3. Select the tag you just created
4. Copy the CHANGELOG section as the release description
5. Publish release

### 5. Verify Deployment

After pushing, Vercel automatically deploys. Verify:
- [ ] Production site is accessible
- [ ] Basic functionality works
- [ ] No console errors

## API Stability

### Stable APIs (do not break without major version)

| API | Stability | Notes |
|-----|-----------|-------|
| `/geometry_spec` endpoint | **Stable** | JSON structure must not change |
| Worker message format | **Stable** | `{ type, spec, requestId }` structure |
| STL output format | **Stable** | Binary STL, Z-up orientation |

### Internal APIs (may change in minor versions)

| API | Stability | Notes |
|-----|-----------|-------|
| Python module imports | Internal | `app.geometry.*` structure may change |
| CSS class names | Internal | May change for styling updates |
| HTML element IDs | Internal | May change in refactors |

## Hotfix Process

For critical bugs in production:

1. Create branch from latest tag: `git checkout -b hotfix/issue-123 vX.Y.Z`
2. Fix the issue with minimal changes
3. Run tests
4. Bump patch version
5. Update CHANGELOG
6. Merge to main, tag, and deploy

## Rollback Process

If a release causes issues:

1. Identify the last known good version
2. In Vercel dashboard, redeploy that version
3. Create hotfix branch to address the issue
4. Do NOT force-push or delete tags

---

## Release History

See [CHANGELOG.md](../CHANGELOG.md) for complete release history.

| Version | Date | Highlights |
|---------|------|------------|
| v2.0.0 | 2026-01-06 | Zero-maintenance stable release |
| v1.3.0 | 2025-12-09 | Community infrastructure |
| v1.2.0 | 2024-12-08 | Documentation release |
| v1.1.0 | 2024-12-08 | Mobile compatibility |
| v1.0.0 | 2024-09-27 | First stable release |

---

*Last updated: 2026-01-28*
