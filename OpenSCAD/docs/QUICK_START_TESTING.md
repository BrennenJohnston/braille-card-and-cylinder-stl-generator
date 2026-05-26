# Quick Start: Cross-Platform STL Validation

Fast-track guide to using the comprehensive STL testing framework.

## Prerequisites

```bash
# 1. Install OpenSCAD 2026.01.03+ with Manifold backend
# Download from: https://openscad.org/downloads.html#snapshots

# 2. Install Python dependencies
pip install -r tests/requirements.txt

# 3. (Optional) Install Playwright for web fixture generation
pip install playwright
python -m playwright install chromium

# 4. (Optional) Install CloudCompare for surface deviation checks
# See tests/tool_versions.yml for installation instructions
```

## Running Tests

### Basic Test Run (Baseline Tolerances)

```bash
# Run all 11 cylinder tests
pytest tests/cross_platform_validation.py -v

# Run specific test
pytest tests/cross_platform_validation.py::TestCrossPlatformValidation::test_stl_validation[cylinder_rounded_emboss_indicators_on] -v

# Run only indicator isolation tests
pytest tests/cross_platform_validation.py -k "indicator_recess" -v
```

### Strict Validation (Tight Tolerances)

```bash
# Run with strict comparison profile
pytest tests/cross_platform_validation.py --comparison-config=tests/compare_config_strict.json -v

# Or set environment variable
export COMPARISON_CONFIG=tests/compare_config_strict.json
pytest tests/cross_platform_validation.py -v
```

### Skip CloudCompare (if not installed)

```bash
pytest tests/cross_platform_validation.py --skip-cloudcompare -v
```

## Generating Fixtures

### Current Status

⚠️ **Current fixtures are OpenSCAD self-test mode** (not true cross-platform validation)

You need to generate web reference fixtures first!

### Generate Web Reference Fixtures (Playwright)

```bash
# 1. Update selectors in scripts/generate_web_fixtures.py to match your web UI
# 2. Run generator against deployed web app

# Generate all fixtures
python scripts/generate_web_fixtures.py --web-url https://your-web-generator.com

# Generate single fixture (debug mode with visible browser)
python scripts/generate_web_fixtures.py \
  --web-url https://your-web-generator.com \
  --test-case cylinder_rounded_emboss_indicators_on \
  --no-headless

# Dry run (check setup)
python scripts/generate_web_fixtures.py --web-url https://your-web-generator.com --dry-run
```

### Generate OpenSCAD Fixtures (Self-Test Mode)

⚠️ **Not recommended for cross-platform validation** (only validates OpenSCAD internal consistency)

```bash
# Generate all fixtures
python scripts/regenerate_fixtures.py --openscad-mode

# Generate single fixture
python scripts/regenerate_fixtures.py --openscad-mode --test-case cylinder_rounded_emboss_indicators_on
```

## Understanding Test Results

### Test Output

```
tests/cross_platform_validation.py::TestCrossPlatformValidation::test_stl_validation[cylinder_rounded_emboss_indicators_on]
  OpenSCAD: Generating STL...
  ✓ Generated in 12.3s
  Comparison:
    Volume: 1234.56 mm³ (ref) vs 1235.12 mm³ (test) - diff: 0.05% ✓
    Surface Area: 2345.67 mm² (ref) vs 2346.01 mm² (test) - diff: 0.01% ✓
    Bounding Box: [0,0,0] to [30.75,52.0,30.75] - diff: 0.00mm ✓
    Watertight: True (both) ✓
    CloudCompare C2M: max 0.03mm ✓
  PASSED
```

### Common Failures

#### Volume/Area Mismatch

```
AssertionError: Volume difference 2.3% exceeds tolerance 1.0%
```

**Cause**: Geometry discrepancy between OpenSCAD and web generator  
**Fix**: Investigate dot shape implementation (rounded vs cone)

#### Indicator Recess Bug

```
AssertionError: Surface deviation 0.15mm exceeds tolerance 0.05mm
Test: cylinder_indicator_recess_rounded
```

**Cause**: Known bug - indicator recesses not generating correctly in counter plates  
**Fix**: Debug `cylinder_counter_plate()` module, check indicator placement/radius

#### Watertightness Failure

```
AssertionError: Test mesh is not watertight (reference is watertight)
```

**Cause**: OpenSCAD boolean operation created non-manifold geometry  
**Fix**: Check for overlapping/intersecting geometry, increase $fn if needed

## Test Case Categories

### Core Matrix (8 tests)

All combinations: dot shape × plate type × indicators

- `cylinder_rounded_emboss_indicators_on`
- `cylinder_rounded_emboss_indicators_off`
- `cylinder_rounded_counter_indicators_on`
- `cylinder_rounded_counter_indicators_off`
- `cylinder_cone_emboss_indicators_on`
- `cylinder_cone_emboss_indicators_off`
- `cylinder_cone_counter_indicators_on`
- `cylinder_cone_counter_indicators_off`

### Indicator Isolation (2 tests)

Minimal fixtures for bug diagnosis (1 row, no text):

- `cylinder_indicator_recess_rounded`
- `cylinder_indicator_recess_cone`

### Parametric Variation (1 test)

Custom geometry:

- `cylinder_rounded_emboss_custom_cutout`

## Debugging Geometry Issues

### Visual Inspection

```bash
# Generate test STL
pytest tests/cross_platform_validation.py::TestCrossPlatformValidation::test_stl_validation[cylinder_rounded_emboss_indicators_on] -v

# Find generated STL in test output directory
# Open in MeshLab, Blender, or OpenSCAD for visual comparison
```

### Isolate Specific Geometry

Use indicator isolation tests to focus on specific features:

```bash
# Test only indicator recesses (no braille dots)
pytest tests/cross_platform_validation.py -k "indicator_recess" -v
```

### Compare Mesh Properties

```bash
# Run with verbose output
pytest tests/cross_platform_validation.py -v -s

# Check logs for detailed mesh properties:
# - Volume, surface area, bounding box
# - Face/vertex counts
# - Watertightness status
# - CloudCompare deviation statistics
```

## CI Integration

### GitHub Actions Example

```yaml
name: STL Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    env:
      CI: true  # Enables strict version enforcement
    
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true  # Pull STL fixtures from Git LFS
      
      - name: Install OpenSCAD 2026.01.03
        run: |
          wget -q https://files.openscad.org/snapshots/OpenSCAD-2026.01.03-x86_64.AppImage -O openscad.AppImage
          chmod +x openscad.AppImage
          sudo mv openscad.AppImage /usr/local/bin/openscad
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r tests/requirements.txt
      
      - name: Run validation tests (baseline)
        run: pytest tests/cross_platform_validation.py -v
      
      - name: Run validation tests (strict)
        run: pytest tests/cross_platform_validation.py --comparison-config=tests/compare_config_strict.json -v
```

## Troubleshooting

### OpenSCAD Not Found

```
OpenSCADNotFoundError: OpenSCAD executable not found
```

**Fix**: Install OpenSCAD 2026.01.03+ and add to PATH, or set `OPENSCAD_PATH` environment variable

### Version Mismatch (CI Mode)

```
OpenSCADNotFoundError: OpenSCAD version mismatch!
Required: 2026.01.03
Found: OpenSCAD version 2021.01
```

**Fix**: Install exact version 2026.01.03 nightly (see tests/tool_versions.yml)

### Manifold Backend Not Available

```
OpenSCADNotFoundError: Manifold backend is required but not available
```

**Fix**: Install OpenSCAD 2026.01.03+ nightly (stable releases don't have Manifold)

### Card Test Case Blocked

```
pytest.fail: BLOCKED: Card test case 'card_rounded_emboss_basic' found in test_cases.json
```

**Fix**: This is intentional! Remove card test cases. Only cylinder tests are allowed until web UI parity is restored.

### Fixtures Missing

```
FileNotFoundError: tests/fixtures/cross_platform/cylinder_rounded_emboss_indicators_on/reference.stl
```

**Fix**: Generate fixtures first (see "Generating Fixtures" section above)

## Performance Tips

### Speed Up Counter Plate Tests

Counter plates use `hemisphere_quality="low"` and `cone_segments=8` for faster rendering (~5 min per test vs ~15 min with medium quality).

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest tests/cross_platform_validation.py -n auto
```

⚠️ **Warning**: Parallel execution may cause issues with OpenSCAD file locking on some platforms.

### Skip Slow Tests

```bash
# Skip counter plate tests (marked as slow_openscad)
pytest tests/cross_platform_validation.py -m "not slow_openscad" -v
```

## Next Steps

1. **Generate web reference fixtures** (update selectors in `scripts/generate_web_fixtures.py`)
2. **Run baseline tests** to identify gross issues
3. **Fix indicator recess bug** using isolation tests
4. **Fix geometry discrepancies** identified by tests
5. **Run strict tests** for final validation

## Documentation

- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Fixture Generation Guide**: `tests/fixtures/cross_platform/README_FIXTURE_GENERATION.md`
- **Tool Versions**: `tests/tool_versions.yml`
- **Comparison Config**: `tests/compare_config.json`, `tests/compare_config_strict.json`

## Support

For issues or questions:

1. Check `IMPLEMENTATION_SUMMARY.md` for known issues
2. Review fixture generation guide for setup problems
3. Check tool_versions.yml for version requirements
4. Examine test output logs for detailed error messages
