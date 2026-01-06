# Scripts Directory

Utility scripts for development and testing of the Braille Card and Cylinder STL Generator.

## 🔧 Active Scripts

### `smoke_test.py`
**Purpose**: Quick health check of core endpoints

**Usage**:
```bash
python scripts/smoke_test.py
```

**What it tests**:
- `/health` endpoint
- `/liblouis/tables` endpoint
- Returns status codes and basic response validation

**When to use**: Before deployment or after major changes to verify basic functionality.

---

### `git_check.bat`
**Purpose**: Check git status and output to a file for debugging

**Usage**:
```batch
scripts\git_check.bat
```

**What it does**:
- Outputs git status, recent log, and branch info to `git_results.txt`

**When to use**: Debugging git state when terminal output is unreliable.

---

### `git_push.ps1`
**Purpose**: Automated git stage, commit, and push workflow

**Usage**:
```powershell
.\scripts\git_push.ps1
```

**What it does**:
- Shows current git status
- Stages all changes (`git add -A`)
- Commits with auto-generated message if there are staged changes
- Pushes to remote origin

**When to use**: Quick commits during development. Use manual commits for important changes.

---

## 🧪 Running Tests

For comprehensive testing, use the test suite in the `tests/` directory:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_smoke.py
pytest tests/test_golden.py

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## 📝 Adding New Scripts

When adding utility scripts:

1. Place them in this `scripts/` directory
2. Add appropriate docstrings and comments
3. Update this README with usage instructions
4. Consider if the script should be:
   - A permanent utility (document here)
   - A one-time refactoring tool (delete after use)
   - Part of the test suite (move to `tests/`)

---

*Last updated: January 2026*
