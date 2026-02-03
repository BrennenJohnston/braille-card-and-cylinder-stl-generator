# Character Marker Fix for Manifold Worker

## Problem

When testing cylinder generation with text like "test test", the character indicators on braille rows 1 and 2 were displaying as "a more recessed rectangle shape with a small square within it" instead of showing the letter "T" or a clean rectangle fallback.

## Root Cause

The `createCylinderCharacterMarkerManifold()` function in `csg-worker-manifold.js` was attempting to create a character-like shape by:
1. Creating a main box
2. Creating a smaller notch box
3. Subtracting the notch from the main box

This resulted in a confusing appearance that looked like "a rectangle with a small square within it" rather than a proper character or clean rectangle.

The issue is that Manifold WASM doesn't have access to font rendering (unlike the standard Three.js worker which uses `TextGeometry`), so it cannot render actual letters.

## Solution

According to `RECESS_INDICATOR_SPECIFICATIONS.md` section 3 (Character Marker Indicator):

> **Fallback Behavior**
> If character rendering fails (no font, non-alphanumeric character, rendering error):
> - Falls back to **rectangle marker** with 0.5mm depth

The fix modifies `createCylinderCharacterMarkerManifold()` to:
1. Recognize that Manifold doesn't have font rendering capabilities
2. Fall back to `createCylinderRectMarkerManifold()` with proper rectangle dimensions
3. Use 0.5mm depth as specified for fallback rectangles

## Changes Made

### 1. `static/workers/csg-worker-manifold.js`

**Function:** `createCylinderCharacterMarkerManifold()`

**Before:** Created a box with a notch subtracted (confusing appearance)

**After:** Falls back to clean rectangle marker by calling `createCylinderRectMarkerManifold()`

```javascript
function createCylinderCharacterMarkerManifold(spec) {
    // ... parameter extraction and validation ...

    // Manifold doesn't have font rendering capabilities, so we fall back to rectangle marker
    // as specified in RECESS_INDICATOR_SPECIFICATIONS.md section 3

    console.log(`createCylinderCharacterMarkerManifold: Falling back to rectangle marker (no font available in Manifold)`);

    // Convert character marker spec to rectangle marker spec
    const dot_spacing = size / 1.5; // size is dot_spacing * 1.5 for character markers
    const rectSpec = {
        x: x,
        y: y,
        z: z,
        theta: theta,
        radius: cylRadius,
        width: dot_spacing,
        height: 2 * dot_spacing,
        depth: 0.5, // Fallback rectangle uses 0.5mm depth per spec
        is_recess: is_recess
    };

    return createCylinderRectMarkerManifold(rectSpec);
}
```

### 2. `geometry_spec.py`

**Added:** Debug logging to track character marker generation

```python
logger.info(f"Row {row_num}: original_line='{orig}', first_char='{first_char}', isalnum={first_char and (first_char.isalpha() or first_char.isdigit())}")
logger.info(f"Row {row_num}: Created character marker for '{first_char.upper()}'")
```

### 3. `static/workers/csg-worker-manifold.js`

**Added:** Debug logging to track marker processing

```javascript
console.log('Processing cylinder_character marker:', markerSpec);
```

## Expected Behavior After Fix

For test input "test test" with 4 rows:

| Braille Row | Column 0 | Column 1 | Expected Appearance |
|-------------|----------|----------|---------------------|
| Row 1 | Triangle | Rectangle (fallback for 'T') | Clean rectangle, 0.5mm deep |
| Row 2 | Triangle | Rectangle (fallback for 'T') | Clean rectangle, 0.5mm deep |
| Row 3 | Triangle | Rectangle (no char) | Clean rectangle, 0.5mm deep |
| Row 4 | Triangle | Rectangle (no char) | Clean rectangle, 0.5mm deep |

**Note:** Since Manifold worker cannot render actual font characters, all character indicators will appear as clean rectangles. This is the correct fallback behavior per the specification.

## Testing

1. Start the development server with Manifold worker enabled:
   ```powershell
   $env:FORCE_CLIENT_CSG = "1"
   .\.venv\Scripts\python.exe wsgi.py
   ```

2. Open the web interface and enter "test test" in auto mode

3. Select cylinder shape and generate the embossing plate

4. Verify that:
   - Rows 1 and 2 show clean rectangles at column 1 (not rectangles with notches)
   - Rows 3 and 4 show clean rectangles at column 1
   - All rectangles are the same size and appearance
   - Triangle markers appear correctly at column 0 for all rows

## Related Documentation

- `RECESS_INDICATOR_SPECIFICATIONS.md` - Complete specification for all indicator types (in docs/specifications/)
- `MANIFOLD_CYLINDER_FIX.md` - Manifold integration and cylinder generation
- `MANIFOLD_WORKER_VALIDATION.md` - Worker validation against specifications

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-06 | 1.0 | Initial fix for character marker fallback in Manifold worker |
