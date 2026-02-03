# Verification Guide - Phase 0 & Phase 1.1

This guide helps you verify that the refactoring work so far is solid and the application still works perfectly.

## Quick Verification (2 minutes)

```bash
# 1. Run all tests
python -m pytest tests/ -v

# Expected: 13 tests passing in ~5 seconds
```

If all tests pass, the core functionality is intact! ✓

## Full Local Verification (5 minutes)

### 1. Start the Application

```bash
python backend.py
```

Expected output:
```
 * Running on http://127.0.0.1:5001
```

### 2. Test in Browser

Open http://localhost:5001 in your browser.

**Verify:**
- ✓ Page loads
- ✓ UI displays correctly
- ✓ Can enter text
- ✓ Can generate STL (try "Hello")
- ✓ 3D preview shows up
- ✓ Can download STL file

### 3. Test Endpoints with curl (Optional)

```bash
# Health check
curl http://localhost:5001/health

# Expected: {"status": "ok"}

# Get geometry specification (v2.0.0 - STL generation is client-side only)
curl -X POST http://localhost:5001/geometry_spec \
  -H "Content-Type: application/json" \
  -d "{\"lines\": [\"⠁\", \"\", \"\", \"\"], \"plate_type\": \"positive\", \"shape_type\": \"card\", \"grade\": \"g1\", \"settings\": {\"card_width\": 85, \"card_height\": 55}}"

# Expected: JSON geometry specification (client sends this to CSG worker for STL generation)

# Note: The deprecated /generate_braille_stl endpoint returns 410 Gone
```

### 4. Verify Test Files

```bash
# Check test structure
dir tests\
# Should see: test_smoke.py, test_golden.py, conftest.py, fixtures\

# Check app structure
dir app\
# Should see: __init__.py, models.py, api.py, exporters.py, utils.py, geometry\, geometry_spec.py, validation.py

dir app\geometry\
# Should see: Multiple .py files for geometry operations
```

## Code Quality Checks

```bash
# Check linting (should show 40 known issues, all documented)
python -m ruff check . --output-format=concise

# Format code (should show files already formatted)
python -m ruff format . --check

# Type checking (optional - will have many warnings, that's expected for now)
# python -m mypy backend.py
```

## What Changed vs. Original

### ✅ Improvements
- **Testing:** 13 automated tests (0 → 13)
- **Code Quality:** 408 linting issues fixed
- **Documentation:** Multiple new docs (this guide, summaries, etc.)
- **Structure:** New `app/` package with modular design
- **Developer Tools:** pre-commit hooks, ruff, mypy, pytest configured

### ⚠️ No Behavior Changes
- All endpoints work identically
- All STL generation produces same results (verified by golden tests)
- Performance unchanged
- No new features or bug fixes (intentionally - that comes later)

## Troubleshooting

### Tests Fail
```bash
# Get detailed error
python -m pytest tests/test_smoke.py -v --tb=long

# Common fixes:
# - Ensure all dependencies installed: pip install -r requirements.txt
# - Ensure pytest installed: pip install pytest
```

### Application Won't Start
```bash
# Check if port 5001 is in use
netstat -ano | findstr :5001

# Try a different port
# Edit backend.py line ~4188: app.run(debug=True, port=5002)
```

### Import Errors
```bash
# Ensure you're in project root
cd C:\Users\WATAP\Documents\github\braille-card-and-cylinder-stl-generator

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

## Success Criteria Checklist

- [ ] All 13 tests pass
- [ ] Application starts without errors
- [ ] Web UI loads and is functional
- [ ] Can generate a simple STL file
- [ ] STL file opens in 3D viewer (Blender, MeshLab, etc.)
- [ ] `app/` package imports work: `python -c "import app; import app.models; import app.utils"`
- [ ] No errors in terminal when running tests

## Performance Baseline

For future comparison, record these numbers:

```bash
# Time the test suite
python -m pytest tests/ -v

# Note the time - should be ~5 seconds
```

```bash
# Generate a small card and note the time
# (Backend will print "Created positive plate with X braille dots...")
# Typical: <1 second for small cards, 2-5 seconds for full cards
```

## What's Safe to Commit

Currently: **Everything is safe to commit locally**

However, per your instructions, **do not push to GitHub yet** as all changes are locally testable.

When ready:
```bash
# Stage changes
git add .

# Commit
git commit -m "Phase 0 & 1.1: Add testing infrastructure and app package structure"

# DO NOT push yet - wait for Vercel-specific changes
# git push origin refactor/phase-0-safety-net
```

## Next Phase Preview

**Phase 1.2** will:
- Extract ~50-100 functions from `backend.py`
- Move them into `app/` modules
- Keep all tests passing
- No behavior changes
- Estimated time: 2-4 hours of careful work

The application will continue to work throughout!

---

## Questions or Issues?

If anything doesn't work as expected:
1. Check this guide's troubleshooting section
2. Re-run the specific failing test with `-v` for details
3. The original `backend.py` is still intact - nothing has been removed yet
4. All changes are reversible with `git checkout backend.py`

**Everything should work perfectly!** If it doesn't, we can fix it before moving on.
