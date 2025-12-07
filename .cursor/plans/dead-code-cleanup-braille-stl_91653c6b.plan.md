---
name: dead-code-cleanup-braille-stl
overview: Validate existing logic/roadmap docs, then safely de-duplicate and remove unused STL-generation code while preserving current behavior and tests.
todos:
  - id: preflight-checks
    content: Run pre-flight verification commands to ensure clean starting state.
    status: pending
  - id: unify-backend-imports
    content: Switch backend to import plate generators from app.geometry.plates and use them in routes.
    status: pending
  - id: remove-backend-duplicates
    content: Delete duplicated card plate functions from backend.py (retain geometry module as source of truth).
    status: pending
  - id: drop-cylinder-2d
    content: Remove create_cylinder_counter_plate_2d() from app/geometry/cylinder.py; ensure no references remain.
    status: pending
  - id: prune-backend-helper
    content: Remove unused _is_serverless_env() from backend.py and app/geometry/cylinder.py (neither is referenced).
    status: pending
  - id: utils-deprecation
    content: Remove unused allow_serverless_booleans() from app/utils.py.
    status: pending
  - id: scripts-hygiene
    content: Archive or remove legacy refactor scripts not used in CI or dev workflows.
    status: pending
  - id: run-tests
    content: Run smoke and golden tests before/after and compare results; spot-check API outputs.
    status: pending
  - id: final-verification
    content: Run verification grep commands to confirm all dead code removed and no broken references.
    status: pending
---

# Validation + Dead-Code Cleanup Roadmap

## A. Validation Summary

- STL Generation Logic Analysis: Accurate overall. Matches current Python and client-side worker architecture, plate/cylinder branches, boolean fallbacks, and cache behavior.
- Single correction: `static/workers/csg-worker-manifold.js` is NOT unused; it's actively initialized and used for cylinder CSG when ready in the frontend.

Evidence:

```2491:2499:public/index.html
// Initialize Manifold CSG worker
manifoldWorker = new Worker('/static/workers/csg-worker-manifold.js', { type: 'module' });
```

## B. Unused / Duplicated Logic Identified

### B.1 Backend duplicates of plate logic (now also in `app/geometry/plates.py`):

| Function | backend.py Lines | plates.py Lines | Status |

|----------|------------------|-----------------|--------|

| `create_positive_plate_mesh` | 648-896 | 29-276 | DUPLICATE |

| `create_simple_negative_plate` | 897-1006 | 278-386 | DUPLICATE |

| `create_universal_counter_plate_fallback` | 1007-1065 | 388-445 | DUPLICATE |

| `create_fallback_plate` | 1066-1073 | 447-453 | DUPLICATE |

| `build_counter_plate_hemispheres` | 1240-1473 | 455-687 | DUPLICATE |

| `build_counter_plate_bowl` | 1474-1597 | 689-811 | DUPLICATE |

| `build_counter_plate_cone` | 1598-1807 | 813-1022 | DUPLICATE |

| `create_universal_counter_plate_2d` | 1074-1239 | N/A | DEAD CODE (never called) |

Evidence of duplicate definitions:

```29:33:app/geometry/plates.py
def create_positive_plate_mesh(lines, grade='g1', settings=None, original_lines=None):
    """
    Create a standard braille mesh (positive) ...
```
```648:656:backend.py
def create_positive_plate_mesh(lines, grade='g1', settings=None, original_lines=None):
    """
    Create a standard braille mesh (positive) ...
```

### B.2 Unused helpers:

| Function | File | Lines | Status |

|----------|------|-------|--------|

| `_is_serverless_env()` | `backend.py` | 93-103 | DEAD CODE (defined, never called) |

| `_is_serverless_env()` | `app/geometry/cylinder.py` | 37-44 | DEAD CODE (defined, never called) |

| `allow_serverless_booleans()` | `app/utils.py` | 143-170 | DEAD CODE (defined, never called) |

```92:102:backend.py
def _is_serverless_env() -> bool:
    ...
    return bool(
        os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('NOW_REGION')
    )
```

### B.3 Unused 2D cylinder counter-plate path:

| Function | File | Lines | Status |

|----------|------|-------|--------|

| `create_cylinder_counter_plate_2d()` | `app/geometry/cylinder.py` | 1286-1543 | DEAD CODE (never called) |

```1286:1291:app/geometry/cylinder.py
def create_cylinder_counter_plate_2d(settings, cylinder_params=None):
    """
    Create a cylinder counter plate using 2D Shapely operations...
```

## C. Removal/Unification Principles

- Single source of truth: keep plate generation functions in `app/geometry/plates.py` only; backend should import and call them.
- Preserve public behavior: no route or request/response changes.
- No silent functional regressions: run the existing smoke/golden tests before/after.
- Avoid removing legacy functions that are still used as fallbacks inside the geometry module; only remove true duplicates/unused.

---

# D. Step-by-Step Safe Cleanup Plan

## Pre-Flight Checklist

Run these commands BEFORE making any changes to establish a clean baseline:

```powershell
# 1. Ensure you're on a clean branch
git status

# 2. Create a backup branch
git checkout -b cleanup/dead-code-removal

# 3. Run tests to confirm baseline passes
python -m pytest tests/test_smoke.py -v
python -m pytest tests/test_golden.py -v

# 4. Verify the app starts without errors
python -c "from backend import app; print('Backend imports OK')"
```

**Expected Results:**

- [ ] `git status` shows clean working directory (or only expected changes)
- [ ] Both test suites pass
- [ ] Backend import succeeds without errors

---

## Step 1: Backend → Geometry Unification (Add Imports)

### 1.1 What to do

Add imports from `app.geometry.plates` to `backend.py` so the geometry module becomes the single source of truth.

### 1.2 Exact change location

**File:** `backend.py`

**Insert after line 18** (after `from app.geometry_spec import ...`)

### 1.3 Code to add

```python
from app.geometry.plates import (
    build_counter_plate_bowl,
    build_counter_plate_cone,
    build_counter_plate_hemispheres,
    create_fallback_plate,
    create_positive_plate_mesh,
    create_simple_negative_plate,
    create_universal_counter_plate_fallback,
)
```

### 1.4 Before state (lines 17-19):

```python
from app.geometry.booleans import mesh_difference, mesh_union
from app.geometry_spec import extract_card_geometry_spec, extract_cylinder_geometry_spec

try:
```

### 1.5 After state (lines 17-27):

```python
from app.geometry.booleans import mesh_difference, mesh_union
from app.geometry.plates import (
    build_counter_plate_bowl,
    build_counter_plate_cone,
    build_counter_plate_hemispheres,
    create_fallback_plate,
    create_positive_plate_mesh,
    create_simple_negative_plate,
    create_universal_counter_plate_fallback,
)
from app.geometry_spec import extract_card_geometry_spec, extract_cylinder_geometry_spec

try:
```

### 1.6 Verification command

```powershell
python -c "from backend import app; print('Import OK')"
```

---

## Step 2: Remove Duplicated Card Functions from backend.py

### 2.1 What to do

Delete the duplicated function definitions from `backend.py`. These are now imported from `app.geometry.plates`.

### 2.2 Exact lines to delete

**IMPORTANT:** Delete in REVERSE order (bottom-to-top) to preserve line numbers during editing.

| Order | Function | Lines to Delete | Line Count |

|-------|----------|-----------------|------------|

| 1 | `build_counter_plate_cone` | 1598-1807 | 210 lines |

| 2 | `build_counter_plate_bowl` | 1474-1597 | 124 lines |

| 3 | `build_counter_plate_hemispheres` | 1240-1473 | 234 lines |

| 4 | `create_universal_counter_plate_2d` | 1074-1239 | 166 lines |

| 5 | `create_fallback_plate` | 1066-1073 | 8 lines |

| 6 | `create_universal_counter_plate_fallback` | 1007-1065 | 59 lines |

| 7 | `create_simple_negative_plate` | 897-1006 | 110 lines |

| 8 | `create_positive_plate_mesh` | 648-896 | 249 lines |

**Total lines removed:** ~1,160 lines

### 2.3 Verification commands

```powershell
# Verify functions no longer defined locally in backend.py
rg "^def create_positive_plate_mesh" backend.py
rg "^def create_simple_negative_plate" backend.py
rg "^def create_universal_counter_plate" backend.py
rg "^def create_fallback_plate" backend.py
rg "^def build_counter_plate" backend.py

# All above should return NO matches

# Verify imports exist
rg "from app.geometry.plates import" backend.py
# Should return 1 match showing the import block

# Verify app still starts
python -c "from backend import app; print('Backend OK after function removal')"
```

---

## Step 3: Remove Unused `_is_serverless_env()` Helper

### 3.1 What to do

Remove the unused `_is_serverless_env()` function from both files where it's defined but never called.

### 3.2 File 1: backend.py

**Lines to delete:** 92-103 (including the comment above it)

**Before (lines 90-105):**

```python

# Environment detection helpers
def _is_serverless_env() -> bool:
    """
    Detect if running in a serverless environment (e.g., Vercel/AWS Lambda).
    Used to avoid backends that require external binaries (3D boolean engines).
    """
    try:
        return bool(
            os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('NOW_REGION')
        )
    except Exception:
        return False


# Security configurations
```

**After (lines 90-92):**

```python

# Security configurations
```

**Delete lines:** 91-104 (the comment line and entire function including trailing blank line)

### 3.3 File 2: app/geometry/cylinder.py

**Lines to delete:** 37-45

**Before (lines 35-47):**

```python


def _is_serverless_env() -> bool:
    """Detect serverless runtimes (e.g., Vercel/Lambda)."""
    try:
        return bool(
            _os.environ.get('VERCEL') or _os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or _os.environ.get('NOW_REGION')
        )
    except Exception:
        return False


def _booleans_enabled() -> bool:
```

**After (lines 35-38):**

```python


def _booleans_enabled() -> bool:
```

**Delete lines:** 37-45 (function and trailing blank lines, keeping one blank line before next function)

### 3.4 Verification commands

```powershell
# Verify function removed from both files
rg "_is_serverless_env" backend.py
rg "_is_serverless_env" app/geometry/cylinder.py

# Both should return NO matches

# Verify both files still import correctly
python -c "from backend import app; print('backend.py OK')"
python -c "from app.geometry.cylinder import create_cylinder_positive_mesh; print('cylinder.py OK')"
```

---

## Step 4: Remove Unused `create_cylinder_counter_plate_2d()`

### 4.1 What to do

Remove the unused 2D cylinder counter plate function from `app/geometry/cylinder.py`.

### 4.2 File: app/geometry/cylinder.py

**Lines to delete:** 1286-1543 (end of file)

This is a ~258 line function that is defined but never called anywhere in the codebase.

### 4.3 Verification commands

```powershell
# Verify function removed
rg "create_cylinder_counter_plate_2d" app/geometry/cylinder.py

# Should return NO matches

# Verify remaining cylinder functions still work
python -c "from app.geometry.cylinder import create_cylinder_positive_mesh, create_cylinder_counter_plate; print('Cylinder module OK')"
```

---

## Step 5: Remove Unused `allow_serverless_booleans()`

### 5.1 What to do

Remove the unused utility function from `app/utils.py`.

### 5.2 File: app/utils.py

**Lines to delete:** 143-170 (end of file, including the decorator)

**Before (lines 140-170):**

```python
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


@lru_cache(maxsize=1)
def allow_serverless_booleans() -> bool:
    """
    Determine if we can safely execute 3D boolean operations in serverless environments.
    ...
    """
    ...
    return False
```

**After (lines 140-141):**

```python
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')
```

**Delete lines:** 142-170 (blank line and entire function)

### 5.3 Verification commands

```powershell
# Verify function removed
rg "allow_serverless_booleans" app/utils.py

# Should return NO matches

# Verify utils module still works
python -c "from app.utils import get_logger, _truthy; print('utils.py OK')"
```

---

## Step 6: Scripts Hygiene (Optional)

### 6.1 What to do

Move legacy one-off refactor scripts to an archive folder or delete them.

### 6.2 Scripts to archive/delete

| Script | Purpose | Recommendation |

|--------|---------|----------------|

| `scripts/build_cylinder_module.py` | One-time extraction | Archive or delete |

| `scripts/extract_cylinder_functions.py` | One-time extraction | Archive or delete |

| `scripts/remove_cylinder_funcs.py` | One-time cleanup | Archive or delete |

| `scripts/replace_prints_with_logging.py` | One-time migration | Archive or delete |

### 6.3 Commands to archive

```powershell
# Create archive directory
mkdir scripts/archive

# Move legacy scripts
Move-Item scripts/build_cylinder_module.py scripts/archive/
Move-Item scripts/extract_cylinder_functions.py scripts/archive/
Move-Item scripts/remove_cylinder_funcs.py scripts/archive/
Move-Item scripts/replace_prints_with_logging.py scripts/archive/
```

### 6.4 Alternative: Delete if not needed

```powershell
Remove-Item scripts/build_cylinder_module.py
Remove-Item scripts/extract_cylinder_functions.py
Remove-Item scripts/remove_cylinder_funcs.py
Remove-Item scripts/replace_prints_with_logging.py
```

---

# E. Testing + Verification

## E.1 Test Commands

Run these commands after completing all cleanup steps:

```powershell
# Run smoke tests (endpoints respond, meshes valid)
python -m pytest tests/test_smoke.py -v

# Run golden tests (geometry regressions)
python -m pytest tests/test_golden.py -v

# Run the smoke test script
python scripts/smoke_test.py
```

**Expected Results:**

- [ ] All smoke tests pass
- [ ] All golden tests pass
- [ ] Smoke test script completes without errors

## E.2 Manual Spot-Check

Test the API endpoints manually:

```powershell
# Start the dev server
python backend.py

# In a separate terminal, test endpoints:
# 1. Health check
curl http://localhost:5000/health

# 2. Generate a positive plate (or use browser/Postman)
# POST to /generate_braille_stl with appropriate JSON body
```

## E.3 Final Verification Grep Commands

Run these to confirm all dead code is removed:

```powershell
# Verify no duplicate definitions remain in backend.py
rg "^def create_positive_plate_mesh" backend.py          # Should return nothing
rg "^def create_simple_negative_plate" backend.py        # Should return nothing
rg "^def create_universal_counter_plate" backend.py      # Should return nothing
rg "^def build_counter_plate" backend.py                 # Should return nothing
rg "^def _is_serverless_env" backend.py                  # Should return nothing

# Verify imports are in place
rg "from app.geometry.plates import" backend.py          # Should return 1 match

# Verify cylinder.py cleaned up
rg "^def _is_serverless_env" app/geometry/cylinder.py    # Should return nothing
rg "^def create_cylinder_counter_plate_2d" app/geometry/cylinder.py  # Should return nothing

# Verify utils.py cleaned up
rg "^def allow_serverless_booleans" app/utils.py         # Should return nothing
```

---

# F. Rollout + Risk Mitigation

## F.1 Commit Strategy

Create separate commits for easy rollback:

```powershell
# Commit 1: Add imports (safe, no behavior change)
git add backend.py
git commit -m "refactor(backend): import plate generators from app.geometry.plates"

# Commit 2: Remove duplicate functions
git add backend.py
git commit -m "refactor(backend): remove duplicate plate functions (1160 lines)

Functions now imported from app.geometry.plates:
- create_positive_plate_mesh
- create_simple_negative_plate
- create_universal_counter_plate_fallback
- create_fallback_plate
- build_counter_plate_hemispheres
- build_counter_plate_bowl
- build_counter_plate_cone

Also removed dead code:
- create_universal_counter_plate_2d (never called)"

# Commit 3: Remove unused helpers
git add backend.py app/geometry/cylinder.py app/utils.py
git commit -m "chore: remove unused helper functions

Removed:
- _is_serverless_env() from backend.py (never called)
- _is_serverless_env() from app/geometry/cylinder.py (never called)
- allow_serverless_booleans() from app/utils.py (never called)
- create_cylinder_counter_plate_2d() from cylinder.py (never called)"

# Commit 4 (optional): Archive legacy scripts
git add scripts/
git commit -m "chore: archive legacy refactor scripts"
```

## F.2 Rollback Commands

If any regression appears:

```powershell
# Rollback last commit
git revert HEAD

# Or rollback to specific commit
git revert <commit-hash>

# Or restore individual files
git checkout HEAD~1 -- backend.py
git checkout HEAD~1 -- app/geometry/cylinder.py
git checkout HEAD~1 -- app/utils.py
```

## F.3 Full Rollback (Nuclear Option)

If everything breaks:

```powershell
# Reset to the state before any cleanup
git checkout main -- backend.py app/geometry/cylinder.py app/utils.py

# Or abandon the cleanup branch entirely
git checkout main
git branch -D cleanup/dead-code-removal
```

---

# G. Summary Checklist

Use this checklist to track progress:

- [ ] **Pre-flight:** Baseline tests pass
- [ ] **Step 1:** Added imports to backend.py
- [ ] **Step 2:** Removed 8 duplicate functions from backend.py (~1160 lines)
- [ ] **Step 3:** Removed `_is_serverless_env()` from backend.py and cylinder.py
- [ ] **Step 4:** Removed `create_cylinder_counter_plate_2d()` from cylinder.py
- [ ] **Step 5:** Removed `allow_serverless_booleans()` from utils.py
- [ ] **Step 6:** (Optional) Archived legacy scripts
- [ ] **Testing:** All tests pass after cleanup
- [ ] **Verification:** All grep checks confirm dead code removed
- [ ] **Commits:** Changes committed with clear messages

---

# H. Notes for Future Roadmap Alignment

- OpenSCAD port references should continue to point to `app/geometry/*` (not backend) as the reference source.
- Cloudflare client-only path unaffected; server-side cleanups reduce maintenance for the Vercel app.
- Documentation reference in `docs/development/EMBOSSING_PLATE_RECESS_FIX.md` mentions `_is_serverless_env()` in historical context only - no code changes needed there.
