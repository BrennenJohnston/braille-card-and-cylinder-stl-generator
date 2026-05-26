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

### `fetch_bana_business_cards.py`
**Purpose**: Download and rasterize the BANA *Business Cards Fact Sheet* (approved March 2024) into `docs/guides/_bana_source/` so the verified-source transcription at `docs/guides/_bana_business_cards_verified_source.md` can be audited page-by-page.

**Usage**:
```bash
pip install pypdfium2 Pillow
python scripts/fetch_bana_business_cards.py
```

**When to use**: Once per BANA revision. If BANA publishes a revised Fact Sheet, re-run this script, update the verified-source file from the new pages, and then propagate changes to `docs/guides/BUSINESS_CARD_TRANSLATION_GUIDE.md`, `templates/index.html`, and `public/index.html`.

The companion script `_extract_bana_text.py` (prefixed with `_` because it is internal to the BANA-source pipeline) pairs each NABA-ASCII-encoded line in the PDF text layer with its Unicode braille (U+2800–U+28FF) equivalent for cross-checking against the rendered page images.

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
