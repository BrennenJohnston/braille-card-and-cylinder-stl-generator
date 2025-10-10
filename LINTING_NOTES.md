# Linting Notes

## Phase 0.2 Status

✅ **Completed:**
- Installed ruff, mypy, pytest, pre-commit
- Fixed 430 auto-fixable linting issues
- All smoke tests pass
- Pre-commit hooks installed

## Remaining Linting Issues (40)

These will be addressed during the refactoring phases:

### Style Suggestions (SIM105) - 8 instances
**Issue:** `try-except-pass` patterns could use `contextlib.suppress()`
**Decision:** Will refactor during Phase 4.1 (Logging & Error Handling)
**Locations:** backend.py lines 299, 431, 455, 3968, 3993, 4143, 4166

### Unused Variables (F841) - 6 instances
**Issue:** Variables assigned but never used
**Decision:** Will remove during Phase 3 (Geometry De-duplication)
**Variables:** `base_height`, `line_height`, `circumference`, `row_height`, `rows_on_cylinder`

### Type Comparison (E721) - 1 instance
**Issue:** Line 627 uses `==` for type comparison instead of `isinstance()`
**Decision:** Will fix during Phase 2 (Typed Models & Validation)

### Exception Handling (B904) - 1 instance
**Issue:** Line 632 raises exception without `from`
**Decision:** Will fix during Phase 4.2 (Consistent API Errors)

### Unnecessary getattr (B009) - 7 instances
**Issue:** Using getattr with constant attribute values
**Decision:** Will simplify during Phase 3 (Geometry De-duplication)

### Whitespace in Docstrings (W293, W291) - 17 instances
**Issue:** Blank lines with whitespace in docstrings
**Decision:** Low priority, can be cleaned up in final pass

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
