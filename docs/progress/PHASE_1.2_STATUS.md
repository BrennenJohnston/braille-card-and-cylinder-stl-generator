# Phase 1.2 Migration Status

## Objective
Move functions from `backend.py` into modular structure while maintaining all functionality.

## Progress Summary

**Original backend.py:** 4455 lines
**Current backend.py:** 3849 lines
**Lines migrated:** 606 lines (13.6%)

## Completed Batches

### ✅ Batch 1: Cache Functions (12 functions, ~200 lines)
**Target:** `app/cache.py`
**Functions moved:**
- `_get_redis_client()`
- `_blob_url_cache_get()`, `_blob_url_cache_set()`
- `_blob_public_base_url()`, `_build_blob_public_url()`, `_blob_check_exists()`, `_blob_upload()`
- `_canonical_json()`, `compute_cache_key()`
- `_normalize_number()`, `_normalize_settings_for_cache()`, `_normalize_cylinder_params_for_cache()`

**Status:** ✅ Committed & Tested

### ✅ Batch 2: CardSettings Class (~318 lines)
**Target:** `app/models.py`
**Functions moved:**
- `CardSettings` class with `__init__()` and `_validate_margins()` methods

**Status:** ✅ Committed & Tested

### ✅ Batch 3: Braille Utility (31 lines)
**Target:** `app/utils.py`
**Functions moved:**
- `braille_to_dots()`

**Status:** ✅ Committed & Tested

### ✅ Batch 4: Cylinder Frame Utility (15 lines)
**Target:** `app/geometry/cylinder.py`
**Functions moved:**
- `_compute_cylinder_frame()`

**Status:** ✅ Committed & Tested

## Remaining Functions (40)

### Routes (10 - Will move in Phase 6.1)
Keep in backend.py for now - Phase 6 focuses on "thin routes":
1. `lookup_stl_redirect()`
2. `debug_blob_upload()`
3. `health_check()`
4. `index()`
5. `favicon()`, `favicon_png()`
6. `static_files()`
7. `list_liblouis_tables()` + `_scan_liblouis_tables()`
8. `generate_braille_stl()`
9. `generate_counter_plate_stl()`

### Validation (3 - Will refactor in Phase 5.1)
Keep in backend.py for now:
- `validate_lines()`
- `validate_braille_lines()`
- `validate_settings()`

### Error Handlers (4 - Keep in backend.py)
- `add_security_headers()`
- `handle_error()`
- `request_entity_too_large()`
- `bad_request()`

### Card Geometry (Priority - Move Next)
**Target:** `app/geometry/plates.py` and `app/geometry/dot_shapes.py`

Dot/Shape Builders (6 functions):
- `create_braille_dot()`
- `create_triangle_marker_polygon()`
- `create_card_triangle_marker_3d()`
- `create_card_line_end_marker_3d()`
- `_build_character_polygon()`
- `create_character_shape_3d()`

Plate Generation (7 functions):
- `create_positive_plate_mesh()`
- `create_simple_negative_plate()`
- `create_universal_counter_plate_fallback()`
- `create_fallback_plate()`
- `build_counter_plate_hemispheres()`
- `build_counter_plate_bowl()`
- `build_counter_plate_cone()`

### Cylinder Geometry (Priority - Move Next)
**Target:** `app/geometry/cylinder.py`

Layout & Transform (2 functions):
- `layout_cylindrical_cells()`
- `cylindrical_transform()`

Shell & Shapes (5 functions):
- `create_cylinder_shell()`
- `create_cylinder_braille_dot()`
- `create_cylinder_triangle_marker()`
- `create_cylinder_line_end_marker()`
- `create_cylinder_character_shape()`

Generation (2 functions):
- `generate_cylinder_stl()`
- `generate_cylinder_counter_plate()`

## Strategy

### Immediate Next Steps
1. **Batch 5:** Move card dot/shape builders to `app/geometry/dot_shapes.py`
2. **Batch 6:** Move card plate generation to `app/geometry/plates.py`
3. **Batch 7:** Move cylinder functions to `app/geometry/cylinder.py`
4. **Complete Phase 1.2**

### Functions Staying in backend.py (for now)
- Routes (10) - Phase 6
- Validation (3) - Phase 5
- Error handlers (4) - Keep
- **Remaining in backend after Phase 1.2:** ~17 functions + routes

## Test Status
**All 13 tests passing ✓** after every batch

## Next Actions
Continue with Batch 5: Card shape builders
