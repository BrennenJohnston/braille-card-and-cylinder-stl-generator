# Core Specifications Index

## Overview

This document serves as the **master index** for all core architecture specifications in the Braille Card and Cylinder STL Generator project. Each specification document provides comprehensive, in-depth technical documentation for a specific subsystem or feature.

**Last Updated:** 2025-12-08
**Total Specification Documents:** 13

---

## Core Feature Specifications

### 1. User Interface & Experience

#### [UI_INTERFACE_CORE_SPECIFICATIONS.md](./UI_INTERFACE_CORE_SPECIFICATIONS.md)
**Status:** ✅ Complete (Updated 2025-12-08)
**Covers:**
- Theme system (Dark, Light, High Contrast)
- Font size adjustment system
- STL preview panel (Three.js 3D viewer)
- **STL Preview Label** — Clarifying label below the preview panel (Section 3.7)
- **Preview Display Settings** — Brightness and contrast radio button controls (Section 3.8)
- Accessibility features (keyboard navigation, screen readers, ARIA)
- Button state management
- Layout responsiveness (desktop/mobile)

**Key Components:**
- CSS variables and theme switching
- Three-point lighting for high contrast mode
- OrbitControls configuration
- Skip link navigation
- Preview brightness/contrast controls (5 levels each)

#### [CARD_THICKNESS_PRESET_SPECIFICATIONS.md](./CARD_THICKNESS_PRESET_SPECIFICATIONS.md)
**Status:** ✅ Complete (Updated 2025-12-07)
**Covers:**
- Card Thickness Preset System (0.3mm, 0.4mm, and Custom options)
- Preset value definitions and optimization rationale
- UI controls and user interaction flow
- LocalStorage persistence and restoration
- Integration with Expert Mode
- Preset application logic affecting 26+ parameters
- **Custom preset auto-detection** when parameters are modified

**Key Components:**
- Dual event strategy (change + click) for re-applying presets
- Automatic application on page load (fixes HTML default mismatch)
- Frontend-only convenience layer (backend receives individual values)
- Graceful degradation and error handling
- `checkPresetMatch()` and `detectCurrentPreset()` for auto-detection
- Real-time input monitoring with `updatePresetSelection()`

---

### 2. Text Input & Translation

#### [BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md](./BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Placement mode system (Auto vs Manual)
- BANA-aware word wrapping algorithm
- Per-line text input with language selection
- Language selection menu and table discovery
- Translation pipeline data flow
- Backend request structure

**Key Components:**
- Auto placement textarea
- Dynamic line inputs
- Per-line language dropdowns
- Original lines for indicator characters

#### [BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md](./BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Preview button and display container
- Translation pipeline through liblouis worker
- Computer shorthand conversion (human-readable output)
- Manual vs Auto placement preview modes
- Error handling for failed translations

**Key Components:**
- Preview UI structure
- Computer shorthand mapping tables
- Braille Unicode character decoding

#### [LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md](./LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Client-side translation architecture
- Liblouis library integration (WASM/JS)
- Web Worker implementation
- Translation table system and table chains
- Unicode braille output standard (U+2800-U+28FF)
- Frontend/backend validation pipeline
- Braille-to-dots conversion
- Table discovery and metadata extraction

**Key Components:**
- Worker message protocol
- Table chain construction (`unicode.dis` requirement)
- `braille_to_dots()` function
- Validation consistency across 9 modules

---

### 3. Geometry & Dimensions

#### [SURFACE_DIMENSIONS_SPECIFICATIONS.md](./SURFACE_DIMENSIONS_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Cylinder dimensions (diameter, height, cutout, seam offset)
- Plate dimensions (width, height, thickness)
- Parameter flow from UI to backend
- Geometry construction details
- CSG worker implementation
- Default values and validation

**Key Components:**
- Polygonal cutout circumscribed radius
- Seam offset (polygon rotation only)
- Grid centering calculations
- Margin safety validation

#### [BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md](./BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Shape selection radio controls
- Embossing plate rounded shape parameters (4 params)
- Embossing plate cone shape parameters (3 params)
- Counter plate bowl recess parameters (2 params)
- Counter plate cone recess parameters (3 params)
- Parameter flow and geometric transformations

**Key Components:**
- Dome sphere radius formula
- Frustum taper calculations
- Combined shape selector logic
- Backend/CSG worker parameter mapping

#### [BRAILLE_DOT_SHAPE_SPECIFICATIONS.md](./BRAILLE_DOT_SHAPE_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Cone (standard) frustum geometry
- Rounded (dome) geometry with spherical cap
- Hemisphere recess geometry
- Bowl (spherical cap) recess geometry
- Cone recess geometry (inverted frustum)
- Cylinder-specific positioning rules

**Key Components:**
- Shape selection overview
- Critical formulas for sphere radii
- Radial offset calculations
- Orientation swap for cone recesses

#### [BRAILLE_SPACING_SPECIFICATIONS.md](./BRAILLE_SPACING_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Braille dot numbering standard (6-dot layout)
- Braille cell geometry and offsets
- Card row layout (top to bottom)
- Cylinder row layout (vertical centering)
- Angular direction rules for cylinders
- Column layout with indicators
- Embossing vs counter plate differences

**Key Components:**
- `dot_positions` array: `[[0,0], [1,0], [2,0], [0,1], [1,1], [2,1]]`
- `apply_seam()` and `apply_seam_mirrored()` functions
- Coordinate system transformations
- Manifold theta negation fix

#### [RECESS_INDICATOR_SPECIFICATIONS.md](./RECESS_INDICATOR_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Triangle marker geometry and positioning
- Rectangle marker geometry and positioning
- Character marker (alphanumeric) geometry
- Embossing vs counter plate differences
- Cylinder-specific marker placement
- Coordinate system conversions
- Manifold WASM character generation (bitmap font)

**Key Components:**
- Triangle apex direction (right for emboss, left for counter)
- Rectangle marker fallback logic
- 8×8 bitmap font for Manifold characters
- Column layout with indicators enabled

---

### 4. Generation & Export

#### [STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md](./STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md)
**Status:** ✅ Complete
**Covers:**
- Generation architecture (client-side primary, server fallback)
- Geometry specification JSON format
- CSG worker system and message protocol
- Manifold WASM mesh repair integration
- STL binary export format
- File naming conventions
- Download button state machine
- Fallback mechanisms
- Counter plate caching overview

**Key Components:**
- Worker initialization and communication
- Boolean operation pipeline
- STL binary structure (80-byte header, triangles)
- State transitions (Generate → Generating → Download)
- Performance characteristics

#### [CACHING_SYSTEM_CORE_SPECIFICATIONS.md](./CACHING_SYSTEM_CORE_SPECIFICATIONS.md)
**Status:** ✅ Complete (Created 2024-12-06)
**Covers:**
- Content-addressable caching architecture
- Cache key generation (SHA-256 hashing)
- Redis integration for URL mapping
- Vercel Blob storage upload/retrieval
- Counter plate caching strategy
- Cache flow diagrams (hit/miss paths)
- Environment variable configuration
- Performance metrics and monitoring

**Key Components:**
- `compute_cache_key()` — Deterministic hash generation
- Number normalization for cache stability
- Two-tier storage (Redis + Vercel Blob)
- Graceful degradation without cache configured
---

### 5. Global Settings & Schema

#### [SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md](./SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md)
**Status:** ✅ Complete (Enhanced 2025-12-06)
**Covers:**
- Unified request/settings schema across systems
- High-level JSON Schema for automated validation
- Normalization rules aligned with caching
- Cross-field validation constraints
- Example payloads
- **AI Model Development Guidelines** (Section 9)
- Change workflow and impact matrix for future development

**Key Components:**
- Top-level fields: `shape_type`, `plate_type`, `placement_mode`
- `text.lines` (braille Unicode), `spacing.*`
- `card.*`, `cylinder.*`
- `dots.*` families and indicator settings
- JSON Schema file: `settings.schema.json`
- `cache_version` for cache invalidation control
- Critical constants reference table

---

## Supporting Architecture Documentation

### [CLIENT_SIDE_CSG_DOCUMENTATION.md](./CLIENT_SIDE_CSG_DOCUMENTATION.md)
**Purpose:** High-level architecture overview of client-side CSG system
**Covers:**
- Why client-side CSG (Vercel compatibility, no timeouts)
- Component architecture diagram
- Data flow and worker communication
- Bundle size impact (~215 KB)
- Browser compatibility

### [MANIFOLD_WASM_IMPLEMENTATION.md](./MANIFOLD_WASM_IMPLEMENTATION.md)
**Purpose:** Implementation details for Manifold 3D mesh repair
**Covers:**
- CDN-based loading strategy
- Mesh repair integration
- Error handling and graceful degradation
- Performance characteristics
- Testing checklist

## Development Process Documentation

### [MAJOR_FEATURE_IMPLEMENTATION_SOP.md](../development/MAJOR_FEATURE_IMPLEMENTATION_SOP.md)
**Purpose:** Standard Operating Procedure for implementing major features
**Status:** ✅ Complete (Created 2025-12-07)
**Covers:**
- 6-phase implementation workflow (Investigation → Specification → Implementation → Documentation → Verification → Finalization)
- Comprehensive checklists for each phase
- Case study: Card Thickness Preset System implementation
- Common pitfalls and how to avoid them
- File change impact matrix
- Specification template and quick-start guide for AI assistants

**Target Audience:**
- AI coding assistants (Claude, GPT, etc.)
- Junior developers
- Senior developers implementing large features
- Code reviewers

---

## Coverage Analysis

### ✅ Fully Documented Core Systems

| System | Primary Spec | Additional Specs |
|--------|-------------|------------------|
| **UI/UX** | UI_INTERFACE_CORE_SPECIFICATIONS | CARD_THICKNESS_PRESET_SPECIFICATIONS |
| **Text Input** | BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS | BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS |
| **Translation** | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS | — |
| **Dimensions** | SURFACE_DIMENSIONS_SPECIFICATIONS | — |
| **Dot Geometry** | BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS, BRAILLE_DOT_SHAPE_SPECIFICATIONS | BRAILLE_SPACING_SPECIFICATIONS |
| **Indicators** | RECESS_INDICATOR_SPECIFICATIONS | — |
| **Generation** | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS | CLIENT_SIDE_CSG_DOCUMENTATION |
| **Caching** | CACHING_SYSTEM_CORE_SPECIFICATIONS | — |
| **Settings Schema** | SETTINGS_SCHEMA_CORE_SPECIFICATIONS | — |

### Supporting Code Modules (Documented Within Specs)

| Module | Purpose | Primary Documentation |
|--------|---------|----------------------|
| `app/validation.py` | Input validation | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 8) |
| `app/utils.py` | Utility functions | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 9) |
| `app/cache.py` | Caching logic | CACHING_SYSTEM_CORE_SPECIFICATIONS |
| `app/exporters.py` | STL export utilities | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS |
| `app/models.py` | Data models | Referenced across multiple specs |
| `app/geometry/*` | Geometry generation | Referenced across geometry-related specs |
| `app/geometry_spec.py` | Spec extraction | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 3) |
| `backend.py` | API endpoints | Documented per-endpoint in relevant specs |

---

## API Endpoint Coverage

| Endpoint | HTTP Method | Documentation |
|----------|-------------|---------------|
| `/` | GET | UI_INTERFACE_CORE_SPECIFICATIONS |
| `/health` | GET | (trivial health check) |
| `/static/<path>` | GET | (standard static file serving) |
| `/favicon.ico` | GET | (standard favicon) |
| `/liblouis/tables` | GET | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 10) |
| `/generate_braille_stl` | POST | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 11) |
| `/geometry_spec` | POST | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 11) |
| `/generate_counter_plate_stl` | POST | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 11) |
| `/lookup_stl` | GET | CACHING_SYSTEM_CORE_SPECIFICATIONS (Section 8) |
| `/debug/blob_upload` | GET | (debug endpoint, not spec'd) |

**Coverage:** 9/10 endpoints documented (90%)
**Note:** Debug endpoints intentionally excluded from core specifications.

---

## Web Worker Coverage

| Worker | Purpose | Shape Routing | Documentation |
|--------|---------|---------------|---------------|
| `static/liblouis-worker.js` | Braille translation | All | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 3) |
| `static/workers/csg-worker.js` | CSG operations (three-bvh-csg) | **Cards only** | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 4), CLIENT_SIDE_CSG_DOCUMENTATION |
| `static/workers/csg-worker-manifold.js` | CSG with Manifold WASM | **Cylinders only** | MANIFOLD_CYLINDER_FIX, MANIFOLD_WASM_IMPLEMENTATION |

**Coverage:** 3/3 workers documented (100%)

> **Dual Worker Architecture (2024-12-08):** The frontend automatically selects the appropriate CSG worker based on `shape_type`. Cylinders use the Manifold worker for guaranteed watertight output; cards use the standard worker for faster generation.

---

## Coordinate System Documentation

**Status:** ✅ Comprehensively documented

| System | Up Axis | Documentation |
|--------|---------|---------------|
| Python Backend (trimesh) | Z-up | RECESS_INDICATOR_SPECIFICATIONS (Section "Coordinate Systems") |
| Three.js (csg-worker.js) | Y-up | BRAILLE_SPACING_SPECIFICATIONS (Section 10) |
| Manifold WASM | Z-up | RECESS_INDICATOR_SPECIFICATIONS, BRAILLE_SPACING_SPECIFICATIONS |
| STL File Format | Z-up | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 6) |

**Transformations:** All documented including rotations, theta negation for Manifold, and Y-up to Z-up conversions.

---

## Data Flow Documentation

**Status:** ✅ Fully documented with diagrams

| Data Flow | Documentation |
|-----------|---------------|
| User Input → Translation → Backend → Geometry → STL | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 1) |
| Text Input → BANA Wrapping → Grid Layout | BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS (Section 9) |
| UI Settings → CardSettings → Geometry Spec → CSG Worker | SURFACE_DIMENSIONS_SPECIFICATIONS (Section 4) |
| Generate Request → Cache Check → Blob/Generate → Response | CACHING_SYSTEM_CORE_SPECIFICATIONS (Section 6) |
| Client-Side Generation → Geometry Spec → Worker → STL | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 1) |

---

## Critical Algorithms Documented

| Algorithm | Specification | Section |
|-----------|--------------|---------|
| BANA word wrapping | BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS | Section 9 |
| Braille Unicode → Dot patterns | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS | Section 9 |
| Dome sphere radius calculation | BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS | Section 3 |
| Bowl sphere radius calculation | BRAILLE_DOT_SHAPE_SPECIFICATIONS | Section 5 |
| Angular position on cylinders | BRAILLE_SPACING_SPECIFICATIONS | Section 4 |
| Cache key generation | CACHING_SYSTEM_CORE_SPECIFICATIONS | Section 2 |
| Number normalization for caching | CACHING_SYSTEM_CORE_SPECIFICATIONS | Section 2 |
| Computer shorthand conversion | BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS | Section 4 |

---

## Constants & Standards Documented

### Unicode Braille Range
**Value:** `0x2800` to `0x28FF`
**Verified Consistent Across:** 9 modules
**Documentation:** LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 6)

### Dot Position Mapping
**Value:** `[[0,0], [1,0], [2,0], [0,1], [1,1], [2,1]]`
**Documentation:** BRAILLE_SPACING_SPECIFICATIONS (Section 1)

### Default Spacing Values
**Documentation:** BRAILLE_SPACING_SPECIFICATIONS (Section 2)
- `dot_spacing`: 2.5mm
- `cell_spacing`: 6.5mm
- `line_spacing`: 10.0mm

### Shape Selection Values
**Documentation:** BRAILLE_DOT_SHAPE_SPECIFICATIONS (Section 1)
- Emboss: `use_rounded_dots` = 0 (cone) or 1 (rounded)
- Counter: `recess_shape` = 0 (hemisphere), 1 (bowl), or 2 (cone)

---

## Verification Reports Included

Each specification document includes a verification section confirming consistency between specification and implementation:

| Specification | Verification Section | Status |
|---------------|---------------------|--------|
| UI_INTERFACE_CORE_SPECIFICATIONS | Appendix D | ✅ Complete |
| BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS | Appendix D | ✅ Complete |
| BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS | Appendix A | ✅ Complete |
| LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS | Section 13 | ✅ Complete (28/28 components) |
| SURFACE_DIMENSIONS_SPECIFICATIONS | (Embedded throughout) | ✅ Complete |
| BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS | (No formal report) | ⚠️ Informal |
| BRAILLE_DOT_SHAPE_SPECIFICATIONS | (No formal report) | ⚠️ Informal |
| BRAILLE_SPACING_SPECIFICATIONS | Section 13 | ✅ Complete |
| RECESS_INDICATOR_SPECIFICATIONS | Section "Validation Checklist" | ✅ Complete |
| STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS | Section 14 | ✅ Complete |
| CACHING_SYSTEM_CORE_SPECIFICATIONS | Appendix C | ✅ Complete |

---

## Known Issues Documented

All specifications include sections on known issues, edge cases, and workarounds:

| Issue | Documentation | Status |
|-------|---------------|--------|
| Card cone recess inverted orientation | BRAILLE_DOT_SHAPE_SPECIFICATIONS (Bug 6) | Known, Low Priority |
| Manifold theta negation | BRAILLE_SPACING_SPECIFICATIONS (Bug 6) | Fixed (2024-12-06) |
| Triangle rotate_180 inversion | BRAILLE_SPACING_SPECIFICATIONS (Bug 6) | Fixed (2024-12-06) |
| Cylinder rounded dot floating | BRAILLE_DOT_SHAPE_SPECIFICATIONS (Bug 7) | Fixed (2024-12-07) |
| Counter plate uses rectangle only | RECESS_INDICATOR_SPECIFICATIONS | By Design |
| Seam offset only affects polygon | SURFACE_DIMENSIONS_SPECIFICATIONS (Section 10.2) | By Design |
| Hemisphere depth equals radius | BRAILLE_DOT_SHAPE_SPECIFICATIONS (Bug 4) | By Design |

---

## Cross-References & Relationships

### Specifications with Heavy Cross-Dependencies

**Surface Dimensions** references:
- BRAILLE_SPACING_SPECIFICATIONS (for margin calculations)
- BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS (for dot height)
- RECESS_INDICATOR_SPECIFICATIONS (for marker placement)

**STL Export** references:
- All geometry specifications (dimensions, dots, spacing, indicators)
- LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (for braille input)
- CACHING_SYSTEM_CORE_SPECIFICATIONS (for counter plates)

**Braille Spacing** references:
- RECESS_INDICATOR_SPECIFICATIONS (for marker column layout)
- BRAILLE_DOT_SHAPE_SPECIFICATIONS (for dot geometry)
- SURFACE_DIMENSIONS_SPECIFICATIONS (for grid boundaries)

---

## Reading Order for New Developers

### Understanding the Application Flow

1. **Start Here:** [README.md](./README.md) — Project overview
2. **UI Basics:** UI_INTERFACE_CORE_SPECIFICATIONS — How users interact
3. **Input System:** BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS — Text entry
4. **Translation:** LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS — Text to braille
5. **Geometry:** SURFACE_DIMENSIONS_SPECIFICATIONS → BRAILLE_SPACING_SPECIFICATIONS
6. **Dots & Shapes:** BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS → BRAILLE_DOT_SHAPE_SPECIFICATIONS
7. **Indicators:** RECESS_INDICATOR_SPECIFICATIONS
8. **Export:** STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS
9. **Caching:** CACHING_SYSTEM_CORE_SPECIFICATIONS

### Understanding Specific Features

**For cylindrical braille:**
1. SURFACE_DIMENSIONS_SPECIFICATIONS (Section 2)
2. BRAILLE_SPACING_SPECIFICATIONS (Section 4, 5)
3. RECESS_INDICATOR_SPECIFICATIONS (all sections)

**For character indicators:**
1. RECESS_INDICATOR_SPECIFICATIONS (Section 3)
2. BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS (Section 7)

**For client-side generation:**
1. CLIENT_SIDE_CSG_DOCUMENTATION
2. STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS
3. MANIFOLD_WASM_IMPLEMENTATION

---

## Gaps & Future Documentation Needs

### Currently Adequate (Covered Across Multiple Specs)

- **Validation System** — Documented in LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS and inline in other specs
- **Data Models** — Documented where used (CardSettings, CylinderParams)
- **Error Handling** — Documented per-feature with consistent patterns
- **API Endpoints** — Documented in context of their features

### Potential Future Enhancements

| Topic | Priority | Rationale |
|-------|----------|-----------|
| **Consolidated API Reference** | Low | Endpoints well-documented in feature specs |
| **Deployment Guide** | Medium | Would consolidate Vercel-specific setup |
| **Testing Guide** | Medium | Would help with QA and regression testing |
| **Performance Tuning Guide** | Low | Application performs well with defaults |

---

## Maintenance Guidelines

### When to Update Specifications

**Update a specification when:**
1. Core algorithm changes (e.g., BANA wrapping logic modified)
2. New parameters added to UI
3. Default values change
4. Critical bugs fixed that affect documented behavior
5. New features added to existing subsystems

**Create a new specification when:**
1. Entirely new subsystem added (e.g., user accounts, cloud storage)
2. Major architectural shift (e.g., moving to WebGPU for CSG)
3. New output format (e.g., OBJ export in addition to STL)

### Specification Update Process

1. **Identify changed code** — Note file, function, and line numbers
2. **Locate affected specification** — Use this index to find relevant doc
3. **Update specification** — Modify affected sections, update version history
4. **Verify cross-references** — Check if related specs need updates
5. **Run verification** — Ensure spec matches implementation
6. **Update "Document History" section** — Add entry with date and changes

---

## Document Conventions

### Structure

All core specifications follow this structure:
1. **Document Purpose** — What this spec covers
2. **Source Priority** — Order of correctness for implementations
3. **Table of Contents** — Navigation aid
4. **Main Content** — Sections with code examples, formulas, diagrams
5. **Appendices** — Examples, troubleshooting, verification reports
6. **Document History** — Version tracking
7. **Related Specifications** — Cross-references

### Code Citation Format

**For existing code:**
```python
# Source: backend.py (lines 134-142)
@app.route('/lookup_stl', methods=['GET'])
def lookup_stl_redirect():
    ...
```

**For specifications:**
```
Section Reference: SURFACE_DIMENSIONS_SPECIFICATIONS.md (Section 2.1)
```

### Diagrams

**ASCII art preferred for:**
- Data flow diagrams
- Geometric cross-sections
- State machines

**Tables preferred for:**
- Parameter reference
- Comparison matrices
- Coverage tracking

---

## Quick Reference: Which Spec Has What?

### Need to find...

**Default values?** → All specs have "Default Values Reference" sections
**Formulas?** → Look for "Formula Reference" or embedded in parameter descriptions
**Coordinate systems?** → RECESS_INDICATOR_SPECIFICATIONS, BRAILLE_SPACING_SPECIFICATIONS
**Error handling?** → "Error Handling" sections in each spec
**Cache key calculation?** → CACHING_SYSTEM_CORE_SPECIFICATIONS (Section 2)
**Translation process?** → LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS
**Button states?** → UI_INTERFACE_CORE_SPECIFICATIONS (Section 6), STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS (Section 8)
**Theme colors?** → UI_INTERFACE_CORE_SPECIFICATIONS (Section 1.2, 1.3)
**Card thickness presets?** → CARD_THICKNESS_PRESET_SPECIFICATIONS
**BANA wrapping?** → BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS (Section 9)
**Cylinder angular calculations?** → BRAILLE_SPACING_SPECIFICATIONS (Section 5)
**Dot numbering?** → BRAILLE_SPACING_SPECIFICATIONS (Section 1)
**Marker positioning?** → RECESS_INDICATOR_SPECIFICATIONS (Sections 1-3)
**High contrast mode?** → UI_INTERFACE_CORE_SPECIFICATIONS (Section 1.3)
**Preview brightness/contrast?** → UI_INTERFACE_CORE_SPECIFICATIONS (Section 3.8)
**STL preview label?** → UI_INTERFACE_CORE_SPECIFICATIONS (Section 3.7)

**Request schema?** → SETTINGS_SCHEMA_CORE_SPECIFICATIONS

---

## Compliance & Consistency Tracking

### Unicode Range Consistency
**Verified:** ✅ 9/9 modules use `0x2800` to `0x28FF`
**Documentation:** LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 12)

### braille_to_dots Function
**Verified:** ✅ 5/5 modules import from `app/utils.py`
**Documentation:** LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS (Section 12)

### Cache Key Determinism
**Verified:** ✅ Number normalization consistent
**Documentation:** CACHING_SYSTEM_CORE_SPECIFICATIONS (Appendix C)

### Coordinate System Transformations
**Verified:** ✅ All transformations documented
**Documentation:** BRAILLE_SPACING_SPECIFICATIONS (Section 10), RECESS_INDICATOR_SPECIFICATIONS

---

## Version History

| Date | Changes |
|------|---------|
| 2024-12-06 | Initial index creation |
| 2024-12-06 | Added CACHING_SYSTEM_CORE_SPECIFICATIONS.md to index |
| 2025-12-06 | Added SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md; updated counts and quick reference |
| 2025-12-06 | Enhanced SETTINGS_SCHEMA with AI Model Guidelines; added cache_version field; updated .cursorrules with architecture guidance |
| 2025-12-07 | Added CARD_THICKNESS_PRESET_SPECIFICATIONS.md documenting new Card Thickness Preset System (0.3mm/0.4mm layer height presets); updated UI/UX coverage; incremented total spec count to 13 |
| 2025-12-07 | Updated CARD_THICKNESS_PRESET_SPECIFICATIONS.md v1.3: Added "Custom" radio button with auto-detection when parameters deviate from presets |
| 2025-12-07 | Added MAJOR_FEATURE_IMPLEMENTATION_SOP.md - Standard Operating Procedure for implementing major features; documents 6-phase workflow with comprehensive checklists, case study, and development best practices |
| 2024-12-07 | Added Bug 7 (Cylinder rounded dot floating) to Known Issues as FIXED; fix applied in csg-worker-manifold.js |
| 2025-12-08 | Updated UI_INTERFACE_CORE_SPECIFICATIONS.md v1.3: Added STL Preview Label (Section 3.7) and Preview Display Settings with brightness/contrast controls (Section 3.8) |
| 2025-12-08 | **BUG FIX:** Manifold worker integration completed. Frontend now uses dual-worker architecture: csg-worker.js for cards, csg-worker-manifold.js for cylinders (guarantees manifold output). Updated Web Worker Coverage section. |

---

## Contributing to Specifications

### Adding a New Specification

1. **Create document** following naming convention: `{TOPIC}_SPECIFICATIONS.md`
2. **Use specification template** structure (see any existing spec as template)
3. **Add to this index** under appropriate category
4. **Cross-reference** from related specifications
5. **Include verification section** showing spec matches implementation

### Updating This Index

When specifications are added or modified:
1. Update relevant sections (Core Features, Supporting, Coverage Analysis)
2. Update "Last Updated" date at top
3. Update "Version History" section at bottom
4. Verify all cross-references are valid

---

*Document Version: 1.0*
*Created: 2024-12-06*
*Purpose: Master index for all core architecture specifications*
