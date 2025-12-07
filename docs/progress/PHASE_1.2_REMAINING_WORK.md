# Phase 1.2 Remaining Work - Function Migration from backend.py

## Overview

Phase 1.2 requires moving functions from `backend.py` (currently 2,585 lines) into appropriate modules without changing logic. This document tracks exactly what needs to be moved.

**Current Status:** ~60% complete (cylinder, cache, validation, models moved; card plates and routes remain)

---

## Functions Still in backend.py

### Category 1: Card Plate Generation → `app/geometry/plates.py`

**Target:** Move ~900 lines of card plate geometry

| Function | Lines | Description | Dependencies |
|----------|-------|-------------|--------------|
| `create_positive_plate_mesh` | ~250 | Main embossing plate generation | Uses marker functions, braille_to_dots, create_braille_dot |
| `create_simple_negative_plate` | ~110 | Counter plate with recesses | Uses build_counter_plate_* functions |
| `build_counter_plate_hemispheres` | ~235 | Counter plate with hemisphere recesses | Uses CardSettings, booleans, create_braille_dot |
| `build_counter_plate_bowl` | ~125 | Counter plate with bowl/spherical cap recesses | Uses CardSettings, booleans |
| `build_counter_plate_cone` | ~210 | Counter plate with cone frustum recesses | Uses CardSettings, booleans |
| `create_universal_counter_plate_fallback` | ~60 | Fallback universal counter plate | Uses CardSettings |
| `create_fallback_plate` | ~30 | Simple fallback plate | Uses CardSettings |

**Approximate lines:** 900
**Complexity:** Medium - well-isolated geometry functions
**Blockers:** None (can be moved immediately)

---

### Category 2: Card Layout & Markers → `app/geometry/braille_layout.py` or `plates.py`

**Target:** Move ~400 lines of layout, marker, and character rendering

| Function | Lines | Description | Dependencies |
|----------|-------|-------------|--------------|
| `create_triangle_marker_polygon` | ~35 | Creates 2D triangle marker polygon | Uses CardSettings, Shapely |
| `create_line_marker_polygon` | ~25 | Creates 2D line marker polygon | Uses CardSettings, Shapely |
| `create_character_shape_polygon` | ~45 | Creates 2D character shape (alphanumeric) | Uses _build_character_polygon |
| `create_card_triangle_marker_3d` | ~50 | Creates 3D triangle marker mesh | Uses marker polygon function |
| `create_card_line_end_marker_3d` | ~50 | Creates 3D line end marker mesh | Uses marker polygon function |
| `_build_character_polygon` | ~95 | Builds 2D character polygon from font | Uses matplotlib, numpy |
| `create_character_shape_3d` | ~80 | Creates 3D character mesh | Uses _build_character_polygon |

**Approximate lines:** 400
**Complexity:** Medium - some matplotlib font rendering complexity
**Blockers:** None, but `_build_character_polygon` is used by cylinder.py (lazy import)
**Note:** Resolves circular dependency once moved

**Decision needed:** Should markers go in `braille_layout.py` or `plates.py`?
- **Option A:** All layout/marker functions → `braille_layout.py`
- **Option B:** 2D polygons → `braille_layout.py`, 3D meshes → `plates.py`
- **Recommendation:** Option A for simplicity

---

### Category 3: API Routes → `app/api.py`

**Target:** Move ~600 lines of route handlers

| Route | Function | Lines | Description |
|-------|----------|-------|-------------|
| `GET /lookup_stl` | `lookup_stl_redirect` | ~75 | Lookup cached STL by hash |
| `GET /debug/blob_upload` | `debug_blob_upload` | ~75 | Debug blob upload endpoint |
| `GET /health` | `health_check` | ~5 | Health check endpoint |
| `GET /` | `index` | ~20 | Serve index.html |
| `GET /favicon.ico` | `favicon` | ~5 | Serve favicon |
| `GET /favicon.png` | `favicon_png` | ~5 | Serve PNG favicon |
| `GET /static/<path>` | `static_files` | ~50 | Serve static files |
| `GET /liblouis/tables` | `list_liblouis_tables` | ~30 | List available liblouis tables |
| `POST /generate_braille_stl` | `generate_braille_stl` | ~380 | Main STL generation endpoint |
| `POST /generate_counter_plate_stl` | `generate_counter_plate_stl` | ~180 | Universal counter plate endpoint |

**Helper functions for routes:**
| Function | Lines | Description |
|----------|-------|-------------|
| `_scan_liblouis_tables` | ~135 | Scans tables directory |

**Approximate lines:** ~960 (routes + helpers)
**Complexity:** Medium - need to preserve Flask app context
**Blockers:** None, but requires testing after move

**Note:** Routes should remain thin - validation → geometry → export pattern

---

### Category 4: Infrastructure (Keep in backend.py)

**These should NOT be moved:**

| Component | Lines | Reason to Keep |
|-----------|-------|----------------|
| App initialization | ~30 | Entry point |
| CORS configuration | ~10 | App-level config |
| Flask-Limiter setup | ~20 | App-level config |
| Security headers middleware | ~10 | App-level middleware |
| Error handlers | ~50 | App-level handlers |
| `if __name__ == '__main__':` block | ~10 | Entry point |

**Total to keep:** ~130 lines

---

## Migration Plan

### Step 1: Move Card Plate Functions (Highest Priority)
**Estimated time:** 2 hours

1. Create proper imports in `app/geometry/plates.py`
2. Move all 7 plate generation functions from backend.py
3. Update backend.py to import from `app.geometry.plates`
4. Run tests to verify no breakage

**Files affected:**
- `app/geometry/plates.py` (currently 14 lines → ~920 lines)
- `backend.py` (2,585 lines → ~1,685 lines)

### Step 2: Move Layout & Marker Functions
**Estimated time:** 1.5 hours

1. Move all marker and layout functions to `app/geometry/braille_layout.py`
2. Update imports in backend.py and plates.py
3. Update cylinder.py to import `_build_character_polygon` from braille_layout
4. Remove lazy import hack from cylinder.py
5. Run tests to verify

**Files affected:**
- `app/geometry/braille_layout.py` (13 lines → ~413 lines)
- `app/geometry/cylinder.py` (remove lazy import)
- `backend.py` (1,685 lines → ~1,285 lines)

### Step 3: Move Route Handlers
**Estimated time:** 1.5 hours

1. Move all route functions to `app/api.py`
2. Register routes with Flask app in backend.py or via Blueprint
3. Move liblouis scanning helper
4. Run full integration tests

**Files affected:**
- `app/api.py` (10 lines → ~970 lines)
- `backend.py` (1,285 lines → ~325 lines infrastructure only)

### Step 4: Final Cleanup
**Estimated time:** 30 minutes

1. Remove dead imports from backend.py
2. Update docstrings
3. Run full test suite
4. Run linter and fix any issues
5. Update REFACTORING_ROADMAP.md

**Total estimated time:** ~5.5 hours

---

## Testing Strategy

After each step:

1. **Run smoke tests:**
   ```bash
   python -m pytest tests/test_smoke.py -v
   ```

2. **Run golden tests:**
   ```bash
   python -m pytest tests/test_golden.py -v
   ```

3. **Manual smoke test:**
   - Start server: `python backend.py`
   - Visit http://localhost:5001
   - Generate a card STL
   - Generate a cylinder STL
   - Verify downloads work

4. **Check for import errors:**
   ```bash
   python -c "from app.geometry import plates, braille_layout; from app import api; print('All imports OK')"
   ```

---

## Potential Issues and Solutions

### Issue 1: Circular Dependencies
**Risk:** Import cycles between modules
**Solution:** Keep dependencies unidirectional:
- `braille_layout.py` → No internal app dependencies (only external libs)
- `plates.py` → Can import from `braille_layout.py`, `dot_shapes.py`, `booleans.py`
- `api.py` → Can import from any app module

### Issue 2: Flask App Context
**Risk:** Routes need access to Flask `app` object
**Solution:** Pass app as parameter or use Flask Blueprints:
```python
# Option A: Register routes in backend.py after creating app
from app.api import register_routes
app = Flask(__name__)
register_routes(app)

# Option B: Use Blueprint
from app.api import api_blueprint
app.register_blueprint(api_blueprint)
```

### Issue 3: Test Failures After Move
**Risk:** Logic accidentally changed during move
**Solution:**
- Move code verbatim (copy-paste, don't rewrite)
- Run tests after each category move
- Keep commits small and atomic

---

## Success Criteria

Phase 1.2 will be considered complete when:

✅ All plate generation functions moved to `app/geometry/plates.py`
✅ All layout/marker functions moved to `app/geometry/braille_layout.py`
✅ All routes moved to `app/api.py`
✅ Circular dependency resolved (cylinder.py no longer imports backend)
✅ All smoke tests pass (9/9)
✅ All golden tests pass (after regenerating fixtures if needed)
✅ `backend.py` reduced to ~300 lines (infrastructure only)
✅ No logic changes (behavior identical before/after)
✅ Linter passes with no new errors

---

## File Size Projections

| File | Current | After Migration |
|------|---------|-----------------|
| `backend.py` | 2,585 lines | ~325 lines ⬇️ 87% |
| `app/geometry/plates.py` | 14 lines | ~920 lines ⬆️ |
| `app/geometry/braille_layout.py` | 13 lines | ~413 lines ⬆️ |
| `app/api.py` | 10 lines | ~970 lines ⬆️ |

**Total lines unchanged:** ~2,585 lines (just reorganized)

---

## Next Actions

To continue Phase 1.2:

1. **Immediate:** Regenerate golden test fixtures (20 min)
   ```bash
   python tests/generate_golden_fixtures.py
   python -m pytest tests/test_golden.py -v
   ```

2. **Step 1:** Move card plate functions to `app/geometry/plates.py` (2 hours)

3. **Step 2:** Move layout functions to `app/geometry/braille_layout.py` (1.5 hours)

4. **Step 3:** Move routes to `app/api.py` (1.5 hours)

5. **Step 4:** Final cleanup and verification (30 min)

**Total remaining work:** ~5.5 hours to complete Phase 1.2
