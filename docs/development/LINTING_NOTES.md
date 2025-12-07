# Linting Notes

## Current Status (After Phase 1.2 & 2.1)

✅ **Completed:**
- Installed ruff, mypy, pytest, pre-commit
- Fixed 430+ auto-fixable linting issues
- Migrated 1,872 lines to app/ package
- All smoke tests pass
- Pre-commit hooks installed

## Remaining Linting Issues (9)

Down from 97 errors to just 9! Major cleanup achieved.

### False Positives / Type Checking Issues (F821) - 5 instances
**Issue:** `CardSettings` undefined in app/geometry/cylinder.py (lines 227, 329, 420, 543, 819)
**Reason:** Using `from __future__ import annotations` with TYPE_CHECKING guard
**Status:** Code works perfectly, tests pass - ruff doesn't recognize this pattern
**Decision:** Safe to ignore - will be fixed when we add proper .pyi stub files (Phase 10+)

### Test Script Imports (E402) - 2 instances
**Issue:** Module imports after sys.path manipulation in test scripts
**Locations:** scripts/smoke_test.py, tests/generate_golden_fixtures.py
**Status:** Expected and necessary - imports must come after sys.path setup
**Decision:** Safe to ignore - test/script pattern

### Type Comparison (E721) - 1 instance
**Issue:** backend.py line 415 uses `==` for type comparison
**Decision:** Will fix in Phase 5 (Input Validation refactor)

### Exception Handling (B904) - 1 instance
**Issue:** backend.py line 420 raises exception without `from`
**Decision:** Will fix in Phase 4.2 (Consistent API Errors)

**All remaining issues are documented and will be addressed in future phases.**

## Running Linting Tools

```bash
# Check linting issues
python -m ruff check .

# Auto-fix issues
python -m ruff check . --fix

# Format code
python -m ruff format .

# Run tests
python -m pytest -q

# Type checking (when implemented)
python -m mypy .
```

## Pre-commit Hooks

Pre-commit hooks are installed and will run automatically on commit to:
- Fix trailing whitespace
- Fix end-of-file
- Check YAML/JSON syntax
- Run ruff linting and formatting
