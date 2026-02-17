# Release Process

## Versioning

This project uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **Major** — breaking changes (API structure, removed features)
- **Minor** — new features, non-breaking enhancements
- **Patch** — bug fixes, dependency updates, docs

Version is tracked in `package.json` and `pyproject.toml`. Keep them in sync.

## Before releasing

### Run tests

```bash
pytest tests/ -v
ruff check .
ruff format --check .
```

### Run Lighthouse

```bash
python backend.py &
lighthouse http://localhost:5001 --only-categories=accessibility
```

Target: 100/100 accessibility score.

### Manual smoke test

- [ ] App loads in browser
- [ ] Enter text, verify braille translation
- [ ] Generate cylinder STL (embossing and counter)
- [ ] Download STL files
- [ ] 3D preview renders
- [ ] Test on mobile

### Security check

- [ ] No secrets in committed code
- [ ] `pip-audit` and `npm audit` clean

## Release steps

1. Update version in `package.json` and `pyproject.toml`
2. Add a section to `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format
3. Commit, tag, and push:

```bash
git add package.json pyproject.toml CHANGELOG.md
git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```

4. Create a GitHub Release from the tag, using the changelog section as the description
5. Vercel deploys automatically on push — verify the production site works

## Hotfixes

For critical bugs in production:

1. Branch from the latest tag: `git checkout -b hotfix/issue-123 vX.Y.Z`
2. Fix with minimal changes
3. Run tests, bump patch version, update changelog
4. Merge to main, tag, deploy

## Rollback

In the Vercel dashboard, find the previous deployment and click "Promote to Production." Don't force-push or delete tags.

## Release history

See [CHANGELOG.md](../CHANGELOG.md).
