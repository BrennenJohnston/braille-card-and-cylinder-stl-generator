# Web-to-OpenSCAD Porting Guide

A comprehensive guide for creating OpenSCAD implementations that match web-based 3D generators, with automated cross-platform validation.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Analysis & Planning](#phase-1-analysis--planning)
4. [Phase 2: Parameter Mapping](#phase-2-parameter-mapping)
5. [Phase 3: Geometry Implementation](#phase-3-geometry-implementation)
6. [Phase 4: Test Framework Setup](#phase-4-test-framework-setup)
7. [Phase 5: Fixture Generation](#phase-5-fixture-generation)
8. [Phase 6: Validation & Iteration](#phase-6-validation--iteration)
9. [Phase 7: CI/CD Integration](#phase-7-cicd-integration)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Reference Implementation](#reference-implementation)

---

## Introduction

### Purpose

This guide documents the methodology for creating an OpenSCAD implementation of a web-based 3D generator that:

1. **Matches geometry exactly** - Generated STL files are geometrically equivalent
2. **Uses the same parameters** - UI controls map 1:1 between platforms
3. **Has automated validation** - CI/CD catches regressions automatically
4. **Maintains parity** - Changes to either platform are detected

### Why OpenSCAD?

OpenSCAD provides:
- **Parametric design** - Easy customization via Customizer UI
- **Reproducibility** - Same parameters always produce identical output
- **Offline capability** - No server or internet required
- **Open source** - No vendor lock-in
- **3D printing friendly** - Direct STL export

### Prerequisites

- OpenSCAD 2024.x or later (2026.01.03+ recommended for Manifold backend)
- Python 3.10+ with pip
- Git with LFS support
- Access to web generator source code or deployed instance
- Basic understanding of 3D geometry and mesh concepts

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web-to-OpenSCAD Validation                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Web Generator │    │   OpenSCAD   │    │  Validation  │       │
│  │  (Reference)  │    │   Generator  │    │  Framework   │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Reference STL │    │  Test STL    │    │  Comparison  │       │
│  │   Fixtures    │◄───│   Output     │───►│   Results    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files

```
project/
├── model.scad                      # OpenSCAD implementation
├── tests/
│   ├── parameter_mapping.json      # Parameter name/type mapping
│   ├── compare_config.json         # Comparison tolerances
│   ├── compare_config_strict.json  # Strict tolerances for CI
│   ├── openscad_runner.py          # OpenSCAD CLI wrapper
│   ├── mesh_comparison.py          # STL comparison logic
│   ├── cross_platform_validation.py # Main test suite
│   └── fixtures/
│       └── cross_platform/
│           ├── test_cases.json     # Test case definitions
│           └── <test_name>/
│               ├── reference.stl   # Web-generated reference
│               ├── params.json     # Test parameters
│               └── metadata.json   # Mesh properties
├── scripts/
│   ├── generate_web_fixtures.py    # Playwright fixture generator
│   └── regenerate_fixtures.py      # Fixture management
└── .github/
    └── workflows/
        └── stl-validation.yml      # CI/CD workflow
```

---

## Phase 1: Analysis & Planning

### Step 1.1: Understand the Web Generator

Before writing any code, thoroughly analyze the web generator:

1. **Identify all parameters**
   - UI controls (dropdowns, sliders, text inputs)
   - Hidden/computed parameters
   - Default values

2. **Document geometry primitives**
   - What shapes are used? (cylinders, spheres, cones, etc.)
   - How are they combined? (union, difference, intersection)
   - What are the exact dimensions?

3. **Map coordinate systems**
   - Web generators often use Y-up (Three.js default)
   - OpenSCAD uses Z-up
   - Document transformation requirements

4. **Identify tessellation settings**
   - Sphere segment counts
   - Cylinder face counts
   - These affect mesh comparison

### Step 1.2: Create Analysis Document

Create a specification document covering:

```markdown
# Web Generator Analysis

## Parameters
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| width     | float | 100 | 10-500 | Object width in mm |
| ...       | ...   | ... | ...   | ... |

## Geometry Primitives
- Cylinder: radius=X, height=Y, segments=32
- Sphere: radius=Z, segments=24
- ...

## Coordinate System
- Web: Y-up, right-handed
- OpenSCAD: Z-up, right-handed
- Transform: rotate([90, 0, 0])

## Boolean Operations
1. Create base shape
2. Subtract cutouts
3. Add features
```

### Step 1.3: Define Test Matrix

Plan your test cases to cover:

- All parameter combinations (or representative subset)
- Edge cases (min/max values)
- Common use cases
- Known problem areas

Example matrix for a braille generator:

| Test Case | Dot Shape | Plate Type | Indicators |
|-----------|-----------|------------|------------|
| test_1    | Rounded   | Emboss     | On         |
| test_2    | Rounded   | Emboss     | Off        |
| test_3    | Rounded   | Counter    | On         |
| test_4    | Cone      | Emboss     | On         |
| ...       | ...       | ...        | ...        |

---

## Phase 2: Parameter Mapping

### Step 2.1: Create Parameter Mapping File

Create `tests/parameter_mapping.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OpenSCAD to Web API Parameter Mapping",
  "version": "1.0.0",
  
  "parameters": [
    {
      "openscad_name": "object_width",
      "web_api_name": "width",
      "web_ui_label": "Width (mm)",
      "type": "float",
      "default": 100.0,
      "range": [10, 500],
      "unit": "mm",
      "section": "Dimensions",
      "description": "Object width in millimeters"
    },
    {
      "openscad_name": "shape_type",
      "web_api_name": "shape",
      "web_ui_label": "Shape",
      "type": "enum",
      "default": "Cylinder",
      "values": ["Cylinder", "Box", "Sphere"],
      "section": "Shape Selection",
      "description": "Output shape type"
    }
  ],
  
  "validation_rules": {
    "checks": [
      {"name": "all_params_mapped", "severity": "error"},
      {"name": "defaults_match", "severity": "error"},
      {"name": "types_compatible", "severity": "error"}
    ]
  }
}
```

### Step 2.2: OpenSCAD Customizer Best Practices

**Dropdown Format (IMPORTANT)**

Use human-readable labels directly, NOT `value:Label` format:

```scad
// ✅ CORRECT - Clean dropdown, no duplicates
shape_type = "Cylinder"; // [Cylinder, Box, Sphere]

// ❌ WRONG - Can cause duplicate entries
shape_type = "cylinder"; // [cylinder:Cylinder, box:Box, sphere:Sphere]
```

**Backward Compatibility for Test System**

If your test system uses different values (e.g., lowercase), add hidden parameters:

```scad
/* [Hidden] */
// Test system compatibility - accepts lowercase values
shape_type_test = "";  // "cylinder", "box", "sphere"

// Normalize both UI and test values
actual_shape = (shape_type_test == "cylinder") ? "Cylinder" :
               (shape_type_test == "box") ? "Box" :
               (shape_type_test == "sphere") ? "Sphere" :
               shape_type;
```

### Step 2.3: Schema Validation Script

Create `tests/validate_parameter_schema.py`:

```python
"""Validate OpenSCAD parameters match web API schema."""

import json
import re
from pathlib import Path

def extract_openscad_params(scad_file: Path) -> dict:
    """Extract parameters from OpenSCAD Customizer sections."""
    params = {}
    content = scad_file.read_text()
    
    # Pattern: param_name = value; // [options] description
    pattern = r'^(\w+)\s*=\s*([^;]+);(?:\s*//\s*(.*))?$'
    
    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            name, value, comment = match.groups()
            params[name] = {
                'default': parse_value(value),
                'comment': comment or ''
            }
    
    return params

def validate_mapping(scad_params: dict, mapping: dict) -> list:
    """Check all mapped parameters exist and match."""
    errors = []
    
    for param in mapping['parameters']:
        openscad_name = param['openscad_name']
        
        if openscad_name not in scad_params:
            errors.append(f"Missing parameter: {openscad_name}")
            continue
        
        # Check default value matches
        expected = param['default']
        actual = scad_params[openscad_name]['default']
        
        if expected != actual:
            errors.append(
                f"Default mismatch for {openscad_name}: "
                f"expected {expected}, got {actual}"
            )
    
    return errors
```

---

## Phase 3: Geometry Implementation

### Step 3.1: Coordinate System Transformation

Most web 3D libraries (Three.js, Babylon.js) use Y-up coordinates. OpenSCAD uses Z-up.

**Transformation Matrix:**

```scad
// Transform from Y-up to Z-up
module y_up_to_z_up() {
    rotate([90, 0, 0])
        children();
}

// Or for individual points:
// web_point = [x, y, z]  (Y-up)
// openscad_point = [x, z, -y]  (Z-up)
```

### Step 3.2: Geometry Primitives

Match web generator geometry exactly:

**Spherical Cap (Dome)**

```scad
// Spherical cap formula: R = (r² + h²) / (2h)
// where r = base radius, h = cap height
module spherical_cap(base_radius, cap_height) {
    R = (base_radius * base_radius + cap_height * cap_height) / (2 * cap_height);
    center_z = cap_height - R;
    
    intersection() {
        translate([0, 0, center_z])
            sphere(r = R, $fn = 32);
        
        // Clip to cap region
        translate([0, 0, R])
            cube([R * 4, R * 4, R * 2], center = true);
    }
}
```

**Frustum (Truncated Cone)**

```scad
module frustum(base_r, top_r, height) {
    cylinder(h = height, r1 = base_r, r2 = top_r, $fn = 32);
}
```

### Step 3.3: Tessellation Matching

Web generators often use specific segment counts. Match them:

```scad
// Document tessellation settings
// Web generator uses: sphere segments=24, cylinder segments=32

$fn = 32;  // Default for cylinders

// For spheres, match web generator
sphere_segments = 24;
sphere(r = 10, $fn = sphere_segments);
```

### Step 3.4: Boolean Operations

Order matters! Match the web generator's boolean operation sequence:

```scad
// Web generator: base → subtract holes → add features
difference() {
    union() {
        base_shape();
        added_features();
    }
    subtracted_holes();
}
```

---

## Phase 4: Test Framework Setup

### Step 4.1: Install Dependencies

Create `tests/requirements.txt`:

```
trimesh>=4.0.0
numpy>=1.24.0
scipy>=1.10.0
pytest>=7.0.0
pyyaml>=6.0
jsonschema>=4.0.0
playwright>=1.40.0
```

Install:

```bash
pip install -r tests/requirements.txt
python -m playwright install chromium
```

### Step 4.2: OpenSCAD Runner

Create `tests/openscad_runner.py`:

```python
"""OpenSCAD CLI wrapper for automated STL generation."""

import subprocess
import shutil
from pathlib import Path
from typing import Optional

class OpenSCADRunner:
    def __init__(self, openscad_path: Optional[str] = None):
        self.openscad_path = openscad_path or self._find_openscad()
    
    def _find_openscad(self) -> str:
        """Auto-detect OpenSCAD executable."""
        candidates = ['openscad', 'OpenSCAD']
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path
        raise FileNotFoundError("OpenSCAD not found")
    
    def generate_stl(
        self,
        scad_file: Path,
        output_file: Path,
        parameters: dict,
        timeout: int = 300
    ) -> bool:
        """Generate STL from OpenSCAD file with parameters."""
        
        cmd = [self.openscad_path, '-o', str(output_file)]
        
        # Add parameters as -D flags
        for name, value in parameters.items():
            if isinstance(value, str):
                cmd.extend(['-D', f'{name}="{value}"'])
            else:
                cmd.extend(['-D', f'{name}={value}'])
        
        cmd.append(str(scad_file))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout
        )
        
        return result.returncode == 0 and output_file.exists()
```

### Step 4.3: Mesh Comparison

Create `tests/mesh_comparison.py`:

```python
"""Compare two STL meshes for geometric equivalence."""

import trimesh
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class ComparisonResult:
    passed: bool
    volume_diff_pct: float
    area_diff_pct: float
    bbox_diff_mm: float
    both_watertight: bool
    details: dict

class MeshComparator:
    def __init__(self, config: dict):
        self.tolerances = config.get('tolerances', {})
    
    def compare(
        self,
        reference_path: str,
        test_path: str
    ) -> ComparisonResult:
        """Compare reference and test STL files."""
        
        ref_mesh = trimesh.load(reference_path)
        test_mesh = trimesh.load(test_path)
        
        # Volume comparison
        vol_diff = abs(ref_mesh.volume - test_mesh.volume)
        vol_diff_pct = (vol_diff / ref_mesh.volume) * 100
        
        # Surface area comparison
        area_diff = abs(ref_mesh.area - test_mesh.area)
        area_diff_pct = (area_diff / ref_mesh.area) * 100
        
        # Bounding box comparison
        ref_bbox = ref_mesh.bounds
        test_bbox = test_mesh.bounds
        bbox_diff = np.max(np.abs(ref_bbox - test_bbox))
        
        # Watertightness
        both_watertight = ref_mesh.is_watertight and test_mesh.is_watertight
        
        # Check tolerances
        vol_ok = vol_diff_pct <= self.tolerances.get('volume_percent', 1.0)
        area_ok = area_diff_pct <= self.tolerances.get('area_percent', 0.5)
        bbox_ok = bbox_diff <= self.tolerances.get('bbox_mm', 0.1)
        
        passed = vol_ok and area_ok and bbox_ok and both_watertight
        
        return ComparisonResult(
            passed=passed,
            volume_diff_pct=vol_diff_pct,
            area_diff_pct=area_diff_pct,
            bbox_diff_mm=bbox_diff,
            both_watertight=both_watertight,
            details={
                'ref_volume': ref_mesh.volume,
                'test_volume': test_mesh.volume,
                'ref_area': ref_mesh.area,
                'test_area': test_mesh.area,
            }
        )
```

### Step 4.4: Test Suite

Create `tests/cross_platform_validation.py`:

```python
"""Cross-platform STL validation test suite."""

import pytest
import json
from pathlib import Path

from openscad_runner import OpenSCADRunner
from mesh_comparison import MeshComparator

FIXTURES_DIR = Path(__file__).parent / 'fixtures' / 'cross_platform'
SCAD_FILE = Path(__file__).parent.parent / 'model.scad'

def load_test_cases():
    """Load test case definitions."""
    with open(FIXTURES_DIR / 'test_cases.json') as f:
        data = json.load(f)
    return [tc['name'] for tc in data['test_cases']]

@pytest.fixture
def openscad_runner():
    return OpenSCADRunner()

@pytest.fixture
def mesh_comparator(request):
    config_path = request.config.getoption('--comparison-config')
    with open(config_path) as f:
        config = json.load(f)
    return MeshComparator(config)

@pytest.mark.parametrize('test_case', load_test_cases())
def test_stl_validation(test_case, openscad_runner, mesh_comparator, tmp_path):
    """Validate OpenSCAD output matches web reference."""
    
    fixture_dir = FIXTURES_DIR / test_case
    
    # Load parameters
    with open(fixture_dir / 'params.json') as f:
        params = json.load(f)
    
    # Generate OpenSCAD STL
    output_stl = tmp_path / 'output.stl'
    success = openscad_runner.generate_stl(
        SCAD_FILE, output_stl, params
    )
    assert success, "OpenSCAD generation failed"
    
    # Compare to reference
    reference_stl = fixture_dir / 'reference.stl'
    result = mesh_comparator.compare(
        str(reference_stl),
        str(output_stl)
    )
    
    assert result.passed, (
        f"Mesh comparison failed:\n"
        f"  Volume diff: {result.volume_diff_pct:.2f}%\n"
        f"  Area diff: {result.area_diff_pct:.2f}%\n"
        f"  Bbox diff: {result.bbox_diff_mm:.3f}mm"
    )
```

---

## Phase 5: Fixture Generation

### Step 5.1: Web Fixture Generator (Playwright)

Create `scripts/generate_web_fixtures.py`:

```python
"""Generate reference STL fixtures from web generator using Playwright."""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def generate_fixture(
    page,
    test_case: dict,
    output_dir: Path,
    web_url: str
):
    """Generate single fixture from web UI."""
    
    await page.goto(web_url)
    
    # Fill in parameters (UPDATE SELECTORS FOR YOUR WEB UI)
    for param, value in test_case['parameters'].items():
        selector = f'[name="{param}"], #{param}'
        element = page.locator(selector)
        
        if await element.count() > 0:
            tag = await element.evaluate('el => el.tagName')
            
            if tag == 'SELECT':
                await element.select_option(value)
            else:
                await element.fill(str(value))
    
    # Click generate/download button
    async with page.expect_download() as download_info:
        await page.click('button:has-text("Download")')
    
    download = await download_info.value
    
    # Save to fixture directory
    fixture_dir = output_dir / test_case['name']
    fixture_dir.mkdir(exist_ok=True)
    
    await download.save_as(fixture_dir / 'reference.stl')
    
    # Save parameters
    with open(fixture_dir / 'params.json', 'w') as f:
        json.dump(test_case['parameters'], f, indent=2)

async def main(web_url: str, test_cases_file: Path, output_dir: Path):
    """Generate all fixtures."""
    
    with open(test_cases_file) as f:
        data = json.load(f)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for test_case in data['test_cases']:
            print(f"Generating: {test_case['name']}")
            await generate_fixture(page, test_case, output_dir, web_url)
        
        await browser.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--web-url', required=True)
    parser.add_argument('--test-cases', default='tests/fixtures/cross_platform/test_cases.json')
    parser.add_argument('--output-dir', default='tests/fixtures/cross_platform')
    
    args = parser.parse_args()
    
    asyncio.run(main(
        args.web_url,
        Path(args.test_cases),
        Path(args.output_dir)
    ))
```

### Step 5.2: Test Cases Definition

Create `tests/fixtures/cross_platform/test_cases.json`:

```json
{
  "fixture_version": "1.0.0",
  "web_generator_url": "https://your-web-generator.com",
  "web_generator_commit": "abc123",
  "last_updated": "2026-01-10",
  
  "test_cases": [
    {
      "name": "basic_cylinder",
      "description": "Basic cylinder with default parameters",
      "parameters": {
        "shape_type": "Cylinder",
        "width": 100,
        "height": 50
      },
      "priority": "high"
    },
    {
      "name": "custom_dimensions",
      "description": "Cylinder with custom dimensions",
      "parameters": {
        "shape_type": "Cylinder",
        "width": 75.5,
        "height": 120
      },
      "priority": "medium"
    }
  ]
}
```

### Step 5.3: Comparison Configuration

Create `tests/compare_config.json` (baseline):

```json
{
  "profile": "baseline",
  "description": "Baseline tolerances for initial debugging",
  
  "tolerances": {
    "volume_percent": 1.0,
    "area_percent": 0.5,
    "bbox_mm": 0.1,
    "max_surface_deviation_mm": 0.05
  },
  
  "required_checks": {
    "volume": true,
    "area": true,
    "bbox": true,
    "watertight": true
  }
}
```

Create `tests/compare_config_strict.json`:

```json
{
  "profile": "strict",
  "description": "Strict tolerances for CI quality gates",
  
  "tolerances": {
    "volume_percent": 0.1,
    "area_percent": 0.1,
    "bbox_mm": 0.01,
    "max_surface_deviation_mm": 0.02
  },
  
  "required_checks": {
    "volume": true,
    "area": true,
    "bbox": true,
    "watertight": true
  }
}
```

---

## Phase 6: Validation & Iteration

### Step 6.1: Initial Validation Run

```bash
# Run with baseline tolerances first
pytest tests/cross_platform_validation.py -v

# Expect failures - document them
pytest tests/cross_platform_validation.py -v > initial_results.txt 2>&1
```

### Step 6.2: Analyze Failures

For each failing test:

1. **Identify failure type**: Volume? Area? Bounding box?
2. **Quantify difference**: How far off is it?
3. **Isolate cause**: Which geometry primitive is wrong?
4. **Compare visually**: Open both STLs in a mesh viewer

### Step 6.3: Fix Geometry Issues

Common issues and fixes:

| Issue | Cause | Fix |
|-------|-------|-----|
| Volume too high | Extra geometry | Check boolean operations |
| Volume too low | Missing geometry | Check all features added |
| Area mismatch | Tessellation diff | Match segment counts |
| Bbox mismatch | Coordinate system | Check Y-up vs Z-up |
| Not watertight | Boolean errors | Increase $fn, check overlaps |

### Step 6.4: Iterate Until Passing

```bash
# After fixes, run again
pytest tests/cross_platform_validation.py -v

# Once baseline passes, try strict
pytest tests/cross_platform_validation.py \
  --comparison-config=tests/compare_config_strict.json -v
```

---

## Phase 7: CI/CD Integration

### Step 7.1: GitHub Actions Workflow

Create `.github/workflows/stl-validation.yml`:

```yaml
name: STL Validation

on:
  push:
    branches: [main]
    paths:
      - '**.scad'
      - 'tests/**'
  pull_request:
    branches: [main]

env:
  CI: true

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install OpenSCAD
        run: |
          wget -q https://files.openscad.org/snapshots/OpenSCAD-2026.01.03-x86_64.AppImage -O openscad.AppImage
          chmod +x openscad.AppImage
          ./openscad.AppImage --appimage-extract
          sudo mv squashfs-root /opt/openscad
          sudo ln -sf /opt/openscad/AppRun /usr/local/bin/openscad
      
      - name: Install dependencies
        run: pip install -r tests/requirements.txt
      
      - name: Run validation tests
        run: pytest tests/cross_platform_validation.py -v
```

### Step 7.2: Git LFS for Fixtures

STL files should be tracked with Git LFS:

```bash
# Install Git LFS
git lfs install

# Track STL files
echo "*.stl filter=lfs diff=lfs merge=lfs -text" >> .gitattributes

# Add and commit
git add .gitattributes
git add tests/fixtures/
git commit -m "Add reference fixtures"
```

---

## Best Practices

### 1. Parameter Naming

- Use descriptive names matching web UI labels
- Document units (mm, degrees, etc.)
- Provide sensible defaults

### 2. Dropdown Menus

- Use human-readable labels directly
- Avoid `value:Label` format (causes duplicates)
- Add hidden parameters for test system compatibility

### 3. Geometry Precision

- Match web generator's tessellation settings
- Use explicit `$fn` values, not `$fa`/`$fs`
- Document any intentional differences

### 4. Test Coverage

- Cover all parameter combinations (or representative subset)
- Include edge cases (min/max values)
- Add isolation tests for complex features

### 5. Documentation

- Document coordinate system transformations
- Explain geometry formulas (spherical cap, etc.)
- Keep parameter mapping up to date

### 6. Version Control

- Track fixture version in metadata
- Record web generator commit hash
- Document reasons for fixture regeneration

---

## Troubleshooting

### "OpenSCAD not found"

```bash
# Check if installed
which openscad

# Set path explicitly
export OPENSCAD_PATH=/path/to/openscad
```

### "Fixtures not found"

```bash
# Pull LFS files
git lfs pull

# Or regenerate
python scripts/generate_web_fixtures.py --web-url https://...
```

### "Volume mismatch"

1. Check boolean operation order
2. Verify all geometry primitives match
3. Compare tessellation settings

### "Bounding box mismatch"

1. Check coordinate system (Y-up vs Z-up)
2. Verify centering/positioning
3. Check for off-by-one errors in positioning

### "Not watertight"

1. Increase `$fn` for smoother curves
2. Check for overlapping geometry
3. Ensure boolean operations are clean

---

## Reference Implementation

This guide is based on the Braille Cylinder STL Generator project:

- **Repository**: `braille-stl-generator-openscad`
- **Web Generator**: `braille-card-and-cylinder-stl-generator`

Key files to study:

1. `Braille_Card_And_Cylinder_STL_Generator.scad` - OpenSCAD implementation
2. `tests/parameter_mapping.json` - Parameter mapping schema
3. `tests/cross_platform_validation.py` - Test suite
4. `scripts/generate_web_fixtures.py` - Fixture generator
5. `.github/workflows/stl-validation.yml` - CI/CD workflow

---

## Conclusion

Creating an OpenSCAD implementation that matches a web generator requires:

1. **Thorough analysis** of the web generator's geometry
2. **Precise parameter mapping** between platforms
3. **Automated validation** to catch regressions
4. **Continuous integration** to maintain parity

By following this guide, you can create reliable, validated OpenSCAD implementations that produce geometrically equivalent output to web-based 3D generators.

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-01-10  
**License**: PolyForm Noncommercial 1.0.0
