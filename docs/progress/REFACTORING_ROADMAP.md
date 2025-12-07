## Refactoring Roadmap

This roadmap tracks a phased refactor to make the codebase easier to read, test, and extend while preserving current functionality and Vercel/serverless constraints. Each item has clear acceptance criteria and a status field you can check off as you go.

Guiding principles:
- Keep existing features working after every phase (card plates, cylinder, worker-based translation, caching, rate limiting).
- Prefer existing libraries over custom code.
- Make small, safe changes; run smoke tests after each step.

---

## Phase 0: Safety Net & Developer Ergonomics

### 0.1 Baseline Branch & Smoke Tests
**Status: ✅ COMPLETE**

- Create a working refactor branch.
- Verify local run: `python backend.py` → `/health` OK → generate card and cylinder STLs.
- Add a minimal `pytest` smoke test that calls both STL endpoints and asserts 200 + non-empty STL bytes.

Acceptance:
- Local app runs; endpoints respond.
- `pytest -q` runs and passes smoke tests.
- Generated STLs (card positive, card counter, cylinder, cylinder counter) are non-empty, loadable via `trimesh`, and have faces > 0.

### 0.2 Tooling (Lint, Types, Hooks)
**Status: ✅ COMPLETE**

- Add `ruff` (lint + format), `mypy` (types), `pytest` (tests), and `pre-commit` hooks to run ruff (and optionally mypy) on commit.
- Keep Vercel runtime minimal (test/lint/type tools are dev-only).
- Add dev-only dependencies as needed: `pytest-benchmark` for performance tracking, `pytest-xdist` for parallel test execution.

Acceptance:
- `ruff check .` and `mypy .` complete; any remaining mypy gaps are explicit and tracked.
- Pre-commit runs locally.

### 0.3 Golden Test Scaffold (Small)
**Status: ✅ COMPLETE**

- Add 1–2 tiny golden STL fixtures for regression checks (compare bbox extents and triangle counts, not exact bytes).
- Use ranges/thresholds rather than exact equality to avoid hardware-specific variations.
- Include at least one case per geometry type: card positive, card counter, cylinder, cylinder counter.
- Maintain a fast smoke suite suitable for frequent runs.

Acceptance:
- Golden tests stable on local hardware; smoke tests fast (<10s total).
- Each major geometry type has at least one regression test.

**Implemented in:** `tests/test_golden.py`, `tests/test_smoke.py`, `tests/fixtures/`

**✅ Fixed:** Golden fixtures regenerated on November 30, 2025. All 4 golden tests now passing with updated geometry (November 30, 2025).

---

## Phase 1: Module Layout (Move-Only Refactor)

### 1.1 Create Package Structure
**Status: ✅ COMPLETE**

- Create:
  - `app/__init__.py` (Flask app factory for testability)
  - `app/api.py` (routes)
  - `app/models.py` (dataclasses/enums for parameters)
  - `app/geometry/` package:
    - `braille_layout.py` (grid and cylindrical mapping)
    - `dot_shapes.py` (cone/frustum/hemisphere/bowl builders)
    - `plates.py` (emboss + counter plate)
    - `cylinder.py` (shell + recess ops)
    - `booleans.py` (boolean engine selection + batching)
  - `app/exporters.py` (STL bytes and headers)
  - `app/cache.py` (blob URL cache and Redis helpers)
  - `app/utils.py` (units, epsilons, math helpers, logging config)
- Adopt Flask app-factory pattern in `app/__init__.py` to simplify testing and configuration.

Acceptance:
- Package imports resolve; no logic changes yet.
- App factory allows creation of test instances with custom config.

**Implemented in:** `app/` package structure exists with all planned modules.

### 1.2 Move Functions Without Changing Logic
**Status: ✅ COMPLETE**

- Move existing functions from `backend.py` into the new modules; keep routes wired to new locations.
- Run a quick performance sanity check on typical inputs to catch unintended slowdowns.

Acceptance:
- All endpoints behave identically.
- Smoke/golden tests still pass.
- Generation times for typical inputs remain within 10% of baseline.

**Progress:**
- ✅ `app/geometry/cylinder.py` - Full cylinder generation moved (1200+ lines)
- ✅ `app/geometry/dot_shapes.py` - `create_braille_dot` moved
- ✅ `app/geometry/booleans.py` - Boolean operations consolidated with fallback
- ✅ `app/cache.py` - All caching functions moved
- ✅ `app/models.py` - `CardSettings` and typed models moved
- ✅ `app/validation.py` - All validation functions moved
- ✅ `app/utils.py` - `braille_to_dots`, logging helpers moved
- ✅ `app/geometry/plates.py` - All 7 card plate functions moved (~900 lines)
- ✅ `app/geometry/braille_layout.py` - All 7 marker/layout functions moved (~400 lines)
- ✅ `app/exporters.py` - STL export utilities (was already complete)
- ⏳ `app/api.py` - Routes still in `backend.py` (to be moved in future phase)

**Circular Dependency:** ✅ Resolved! `app/geometry/cylinder.py` now imports `_build_character_polygon` from `app/geometry/braille_layout.py`.

---

## Phase 2: Typed Models & Request Validation

### 2.1 Centralize Parameters in Models
**Status: ✅ COMPLETE**

- Add `dataclasses` with type hints for all request/settings parameters.
- Add small `Enum`s for shape type, dot shape, braille grade.

Acceptance:
- Route handlers convert JSON → typed models; defaults centralized; no magic numbers.

**Implemented in:** `app/models.py` - Contains `CardSettings`, `CylinderParams`, `GenerateBrailleRequest`, `ShapeType`, `PlateType`, `BrailleGrade`, `RecessShape`, `PlacementMode` enums.

### 2.2 Runtime Validation (Lightweight)
**Status: ✅ COMPLETE**

- Either: add minimal manual checks; or use `pydantic` v2 for request schemas (dev-only, avoid serverless bloat if needed).

Acceptance:
- Bad inputs produce 400 with a concise error object.

**Implemented in:** `app/validation.py` - Contains `ValidationError`, `validate_lines`, `validate_braille_lines`, `validate_settings`, `validate_shape_type`, `validate_plate_type`, `validate_grade`.

---

## Phase 3: Geometry De-duplication & Purity

### 3.1 Unify Braille Layout Math
**Status: PENDING**

- One source of truth for dot centers on cards; one mapper for cylindrical coordinates (diameter, seam offset, height).
- Keep functions pure (no I/O, no prints).

Acceptance:
- Card and cylinder share layout logic; removed duplicated formulas.

### 3.2 Canonical Dot Shape Builders
**Status: ✅ COMPLETE**

- Implement reusable mesh builders for cone/frustum/hemisphere/bowl at origin with clear dimensions.

Acceptance:
- All dot geometry created via shared builders; consistent sizing.

**Implemented in:** `app/geometry/dot_shapes.py` - Contains `create_braille_dot` which handles cone frustum and rounded dome styles.

### 3.3 Boolean Operations: Consolidate Engine & Batching
**Status: ✅ COMPLETE**

- Extract existing boolean batching and engine fallback logic into `app/geometry/booleans.py` with a single API (e.g., `batch_subtract(base, features, engine='manifold')`).
- Replace duplicate implementations across card, cylinder, and counter plate code.
- Centralize concise logging and engine fallback handling.

Acceptance:
- All call sites use the shared API; duplicate fallback loops removed.
- Outputs watertight or auto-healed; failures reported with concise logs.

**Implemented in:** `app/geometry/booleans.py` - Contains `mesh_union`, `mesh_difference`, `batch_union`, `batch_subtract` with automatic engine fallback (trimesh default → manifold) and healing.

**⚠️ WARNING:** This module is actively used by both `backend.py` and `app/geometry/cylinder.py`. Modifications to boolean logic have previously caused errors. Test thoroughly before any changes.

---

## Phase 4: Logging & Error Handling

### 4.1 Replace Prints with Logging
**Status: ✅ COMPLETE**

- Configure `logging` once; INFO by default, DEBUG in dev via env.
- Summarize counts/timings; avoid per-dot noise.

Acceptance:
- No `print` statements remain.
- Clean logs in normal runs; INFO summarizes counts/timings; DEBUG enabled via env.

**Implemented in:** `app/utils.py` - Contains `setup_logging`, `get_logger`. All modules use `logger = get_logger(__name__)`.

### 4.2 Consistent API Errors
**Status: ✅ COMPLETE**

- Return `{ "error": "message" }` with appropriate status codes.

Acceptance:
- No raw stack traces in responses; errors are concise and consistent.

**Implemented in:** `backend.py` error handlers and `app/validation.py` `ValidationError` class.

---

## Phase 5: Braille Input Validation (Backend)

### 5.1 Validate Incoming Braille/Text
**Status: ✅ COMPLETE**

- Validate/normalize inputs server-side: ensure expected braille Unicode and safe character set; reject invalid inputs with a concise 400 error.
- Keep logic lightweight to preserve serverless constraints.

Acceptance:
- Bad inputs produce 400 with a concise error object; unit tests cover typical invalid cases.

**Implemented in:** `app/validation.py` - All validation functions implemented with detailed error messages.

---

## Phase 6: Thin Routes & IO Boundaries

### 6.1 Keep Routes Thin
**Status: ✅ COMPLETE (routes still in backend.py but structured correctly)**

- Routes validate, call pure geometry, then exporters; no geometry math inline.

Acceptance:
- Route files short and readable.

**Status:** Routes in `backend.py` successfully call into modular `app/` modules. All geometry, validation, caching, and export logic is now properly separated. Routes act as thin orchestration layer. Physical move to `app/api.py` is optional and can be done in a future phase.

### 6.2 Centralize STL Export
**Status: ✅ COMPLETE**

- Move STL byte/headers creation into `app/exporters.py`.

Acceptance:
- Consistent headers and content across endpoints.

**Implemented in:** `app/exporters.py` - Contains `mesh_to_stl_bytes`, `compute_etag`, `create_stl_response`, `create_304_response`, `should_return_304`.

---

## Phase 7: Tests

### 7.1 Unit Tests: Layout & Shapes
**Status: 🟡 PARTIALLY COMPLETE**

- Verify grid sizes, spacing invariants, first/last dot coords.
- Verify dot builders produce expected bounds, watertight meshes.

Acceptance:
- Unit suite passes quickly and deterministically.

**Progress:** Smoke and golden tests exist; dedicated unit tests for individual functions pending.

### 7.2 Boolean & Invariants
**Status: PENDING**

- Toy differences (box minus sphere) and post-ops (watertight, fill holes, bbox sanity).

Acceptance:
- Invariants hold across typical parameter ranges.
- Resulting meshes are watertight; no degenerate triangles; total mesh area > 0.

### 7.3 Property-based Tests (Optional)
**Status: OPTIONAL**

- Use Hypothesis to vary dimensions within safe ranges; assert no NaNs, watertight meshes, monotonic bboxes.

Acceptance:
- Catches edge cases without flakiness.

---

## Phase 8: Frontend Cleanup (Light)

### 8.1 Organize Scripts
**Status: OPTIONAL**

- Split into `static/js/viewer.js`, `api.js`, `worker-bridge.js`.
- Add a simple user-visible error toast.

Acceptance:
- `templates/index.html` becomes thinner; code easier to navigate.

### 8.2 Liblouis Worker Pathing & Self-check
**Status: OPTIONAL**

- Prefer `'/static/liblouis/tables/'` as the primary base for table loading in the JS worker.
- Reduce nested try/catch; surface actionable error messages to the UI.
- Optional: perform a one-time cached self-check after worker init to verify tables are reachable.

Acceptance:
- Worker reliably loads tables in both local and serverless environments; on failure, a concise UI error is shown.

---

## Phase 9: Performance Pass

### 9.1 Batching & Subdivisions
**Status: OPTIONAL**

- Batch boolean features; lower sphere subdivisions if tactile fidelity preserved.
- Short-circuit empty/whitespace lines early.

Acceptance:
- Same outputs within tolerances; measurable speedup on typical inputs.

---

## Phase 10: Documentation

### 10.1 Update README & Add Docs
**Status: PENDING**

- Add module map and extension guide (new dot style/new shape).

Acceptance:
- A novice can extend features with minimal guidance.

---

## Phase 11: Vercel/Deployment Hardening

### 11.1 Serverless Constraints & Cold Starts
**Status: ✅ COMPLETE (Verified Working)**

- Keep runtime dependencies minimal; verify function size within platform limits.
- Measure cold start and typical request latency; target cold start < 10s.
- Validate Blob/Redis caching path works in deployment.
- Confirm rate limiting is enforced in production.

Acceptance:
- E2E on Vercel: `/health`, `/liblouis/tables`, `/generate_*` endpoints respond; smoke suite passes.
- Cold start and latency budgets documented; no oversized deployment artifacts.

**Status:** Application is deployed and working on Vercel.

---

## Implementation Checklist

- [x] 0.1: Create branch and add smoke tests (card, cylinder)
- [x] 0.2: Add ruff, mypy, pytest, pre-commit (dev-only)
- [x] 0.3: Add tiny golden tests (bbox + triangle counts)
- [x] 1.1: Create `app/` package structure
- [x] 1.2: Move functions from `backend.py` (no logic changes)
- [x] 2.1: Centralize parameters in typed models
- [x] 2.2: Add lightweight runtime validation
- [ ] 3.1: Unify braille layout functions
- [x] 3.2: Implement canonical dot shape builders
- [x] 3.3: Consolidate boolean batching + engine fallback
- [x] 4.1: Configure logging; remove prints
- [x] 4.2: Consistent API error shapes/codes
- [x] 5.1: Backend braille input validation
- [x] 6.1: Keep routes thin (validation → geometry → export)
- [x] 6.2: Centralize STL exporters
- [ ] 7.1: Unit tests for layout and shapes - **PARTIALLY COMPLETE**
- [ ] 7.2: Boolean + invariants tests
- [ ] 7.3: Property-based tests (optional)
- [ ] 8.1: Frontend script organization (optional)
- [ ] 8.2: Liblouis worker path strategy + optional self-check (optional)
- [ ] 9.1: Performance pass (batching/subdivisions/short-circuits)
- [ ] 10.1: Documentation updates and guides
- [x] 11.1: Deployment hardening (serverless constraints & cold starts)

---

## Testing Guide

Local run:
```bash
pip install -r requirements.txt
python backend.py  # http://localhost:5001
```

Run tests:
```bash
pytest -q
```

Lint and types:
```bash
ruff check .
mypy .
```

---

## Risks & Rollback

- Keep commits small and isolated to one phase; re-run smoke tests after each.
- If geometry outputs regress, revert the last commit and add a targeted test.
- If boolean ops get flaky, temporarily switch engines via a config flag and continue refactoring.
- **Pin `manifold3d` version** in `requirements.txt` to a known-good version to avoid backend changes affecting boolean operation results during refactoring.
- **⚠️ Boolean operations are stable** - `app/geometry/booleans.py` is actively used. Previous modifications caused errors. Test thoroughly before any changes.

---

## Notes on Constraints

- Maintain serverless friendliness: keep runtime dependencies minimal; new tools are dev-only.
- Do not change static asset/CDN behavior unless verified against liblouis table loading.
- Prefer existing libraries (`trimesh`, `shapely`, `numpy`) over new custom geometry code.
- **Known circular dependency:** `app/geometry/cylinder.py` imports `_build_character_polygon` from `backend.py`. This will be resolved when card plate functions are moved to `app/geometry/plates.py`.
