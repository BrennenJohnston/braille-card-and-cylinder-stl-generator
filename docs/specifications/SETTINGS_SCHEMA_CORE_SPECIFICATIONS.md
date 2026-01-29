# Settings Schema Core Specifications

## Document Purpose

This document defines a unified, canonical schema for all user-provided settings and derived parameters used across the Braille Card and Cylinder STL Generator. It centralizes field names, types, defaults, validation rules, and normalization behavior used by both the client and server. It complements feature-specific specifications by providing a single source of truth for parameter contracts and API payloads.

## Scope

- Request payloads for STL generation and geometry spec extraction
- Top-level settings structure and category groupings
- Field types, enumerations, and value constraints (high-level)
- Normalization and precedence rules
- Cross-field validation
- Example payloads

## Source Priority (Order of Correctness)
1. `backend.py` — Request validation, geometry generation
2. `geometry_spec.py` — Geometry spec extraction
3. `app/models.py` — Data models and defaults
4. `static/workers/*.js` — Client-side CSG workers (consumers of the spec)
5. Feature specs — Category-specific rules and formulas

---

## Table of Contents
1. Unified Settings Object Overview
2. Top-Level Request Schema (generate endpoints)
3. Category Reference and Field Definitions
   - 3.1 Text & Translation
   - 3.2 Plate Selection & Shape Type
   - 3.3 Spacing & Layout
   - 3.4 Surface Dimensions (Card & Cylinder)
   - 3.5 Braille Dot Shape & Dimensions (Emboss & Counter)
   - 3.6 Recess Indicators
   - 3.7 Export/Generation Options
4. Normalization Rules (Determinism & Caching)
5. Validation & Cross-Field Constraints
6. Example Requests
7. Versioning & Compatibility
8. Related Specifications
9. Document History

---

## 1. Unified Settings Object Overview

All generate requests use a JSON object composed of logical categories. Categories mirror the UI structure and feature specs.

Top-level conceptual shape:

```json
{
  "shape_type": "card | cylinder",
  "plate_type": "positive | negative",
  "placement_mode": "auto | manual",
  "text": { /* see 3.1 */ },
  "spacing": { /* see 3.3 */ },
  "card": { /* see 3.4 (Card) */ },
  "cylinder": { /* see 3.4 (Cylinder) */ },
  "dots": { /* see 3.5 */ },
  "indicators": { /* see 3.6 */ },
  "export": { /* see 3.7 */ }
}
```

Notes:
- Fields irrelevant to a chosen `shape_type` are ignored by validators but may still be present.
- All numeric fields are millimeters unless explicitly stated (angles in degrees).

---

## 2. Top-Level Request Schema (generate endpoints)

Applies to:
- POST `/generate_braille_stl`
- POST `/geometry_spec`
- POST `/generate_counter_plate_stl` (alias of the negative-plate path)

Minimal JSON Schema (high-level; see category sections for details):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://braille-stl/specs/settings.schema.json",
  "type": "object",
  "required": ["shape_type", "plate_type", "text"],
  "properties": {
    "shape_type": {"type": "string", "enum": ["card", "cylinder"]},
    "plate_type": {"type": "string", "enum": ["positive", "negative"]},
    "placement_mode": {"type": "string", "enum": ["auto", "manual"]},

    "text": {"type": "object"},
    "spacing": {"type": "object"},
    "card": {"type": "object"},
    "cylinder": {"type": "object"},
    "dots": {"type": "object"},
    "indicators": {"type": "object"},
    "export": {"type": "object"},

    "schema_version": {"type": "string"}
  },
  "additionalProperties": true
}
```

---

## 3. Category Reference and Field Definitions

This section lists canonical field names, high-level types, and brief rules. See the linked feature specs for formulas, geometry details, and UI mappings.

### 3.1 Text & Translation
- text.lines: array<string>
  - Required. Each entry MUST be Unicode braille (U+2800–U+28FF). See validation pipeline.
- text.languages: array<string>
  - Optional. Per-line table IDs; falls back to `text.default_language`.
- text.default_language: string
  - Default language table (e.g., `en-ueb-g1`).
- text.original_lines: array<string>
  - Optional. Original pre-translation lines for indicators and preview context.
- text.auto_wrap: boolean
  - Auto placement uses BANA-aware wrapping.

See: `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md`, `LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md`, `BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md`.

### 3.2 Plate Selection & Shape Type
- shape_type: "card" | "cylinder" (required)
- plate_type: "positive" | "negative" (required)

See: `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md`.

### 3.3 Spacing & Layout
- spacing.dot_spacing_mm: number (>= 0)
- spacing.cell_spacing_mm: number (>= 0)
- spacing.line_spacing_mm: number (>= 0)
- spacing.braille_x_adjust_mm: number (default: 0)
- spacing.braille_y_adjust_mm: number (default: 0)

Notes:
- Dot numbering and cell layout are fixed by standard; not user-configurable.

See: `BRAILLE_SPACING_SPECIFICATIONS.md`.

### 3.4 Surface Dimensions

Card:
- card.plate_width_mm: number (> 0)
- card.plate_height_mm: number (> 0)
- card.plate_thickness_mm: number (> 0)

Cylinder:
- cylinder.cylinder_diameter_mm: number (> 0)
- cylinder.cylinder_height_mm: number (> 0)
- cylinder.polygon_cutout_radius_mm: number (>= 0) — 0 disables cutout
- cylinder.polygon_cutout_points: integer (>= 3 when radius > 0)
- cylinder.seam_offset_degrees: number (0 ≤ value < 360)

See: `SURFACE_DIMENSIONS_SPECIFICATIONS.md`.

### 3.5 Braille Dot Shape & Dimensions

Selection:
- dots.combined_shape: "rounded" | "cone" (controls both emboss and counter selections)
- dots.dot_shape: "rounded" | "cone" (compatibility alias, optional)
- dots.recess_shape: 1 | 2 (bowl = 1, cone = 2; compatibility alias, optional)

Emboss (rounded):
- dots.rounded.base_diameter_mm: number (> 0)
- dots.rounded.base_height_mm: number (>= 0)
- dots.rounded.dome_diameter_mm: number (> 0)
- dots.rounded.dome_height_mm: number (>= 0)

Emboss (cone):
- dots.cone.diameter_mm: number (> 0)
- dots.cone.height_mm: number (>= 0)
- dots.cone.flat_hat_diameter_mm: number (>= 0)

Counter (bowl recess):
- dots.bowl.base_diameter_mm: number (> 0)
- dots.bowl.depth_mm: number (>= 0)

Counter (cone recess):
- dots.recess_cone.base_diameter_mm: number (> 0)
- dots.recess_cone.height_mm: number (>= 0)
- dots.recess_cone.flat_hat_diameter_mm: number (>= 0)

Notes:
- Category selection controls visibility and applicability of parameter groups.

See: `BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md`, `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md`.

### 3.6 Recess Indicators
- indicators.enabled: boolean
- indicators.type: "triangle" | "rectangle" | "character"
- indicators.depth_mm: number (default: 0.6)
- indicators.character: string (single alphanumeric for character marker)
- indicators.size_scale: number (scales relative to `spacing.dot_spacing_mm`)
- indicators.rotate_180: boolean (applies for counter plate on cylinder)

See: `RECESS_INDICATOR_SPECIFICATIONS.md`.

### 3.7 Export/Generation Options
- export.use_client_side_csg: boolean (default: true)
- export.use_manifold_repair: boolean (default: true when available)
- export.file_name_prefix: string (sanitized)

See: `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md`.

---

## 4. Normalization Rules (Determinism & Caching)

Applied before cache-key generation and geometry building:
- Convert numeric strings to numbers
- Round floats to 5 decimals
- Convert near-integers to integers (e.g., 1.0 → 1)
- Normalize booleans to JSON booleans; avoid 0/1 in payloads
- Omit non-geometry-affecting UI fields from geometry hashing

See: `CACHING_SYSTEM_CORE_SPECIFICATIONS.md` (Number normalization, canonical JSON).

---

## 5. Validation & Cross-Field Constraints

High-level checks (non-exhaustive):
- shape_type and plate_type must be valid enums
- text.lines are required and must be Braille Unicode (U+2800–U+28FF)
- cylinder.polygon_cutout_points valid only when radius > 0
- seam_offset_degrees normalized to [0, 360)
- For selected dot shape families, only corresponding parameter groups are required
- All mm values must be non-negative; heights/diameters > 0 where noted
- Geometry safety checks: margins, grid centering, cylinder wrap

See feature specs for detailed constraints and formulas.

---

## 6. Example Requests

Card, positive (emboss, rounded):

```json
{
  "shape_type": "card",
  "plate_type": "positive",
  "placement_mode": "auto",
  "text": {
    "lines": ["⠓⠑⠇⠇⠕ ⠺⠕⠗⠇⠙"],
    "default_language": "en-ueb-g1",
    "auto_wrap": true
  },
  "spacing": {
    "dot_spacing_mm": 2.5,
    "cell_spacing_mm": 6.5,
    "line_spacing_mm": 10.0
  },
  "card": {"plate_width_mm": 90, "plate_height_mm": 52, "plate_thickness_mm": 2.0},
  "dots": {
    "combined_shape": "rounded",
    "rounded": {"base_diameter_mm": 1.5, "base_height_mm": 0.6, "dome_diameter_mm": 1.5, "dome_height_mm": 0.4}
  },
  "indicators": {"enabled": true, "type": "triangle", "depth_mm": 0.6},
  "export": {"use_client_side_csg": true, "use_manifold_repair": true}
}
```

Cylinder, negative (counter, bowl recess):

```json
{
  "shape_type": "cylinder",
  "plate_type": "negative",
  "placement_mode": "manual",
  "text": {
    "lines": ["⠠⠁⠃⠉", "⠠⠙⠑⠋"],
    "languages": ["en-ueb-g2", "en-ueb-g2"]
  },
  "spacing": {"dot_spacing_mm": 2.5, "cell_spacing_mm": 6.5, "line_spacing_mm": 10.0},
  "cylinder": {
    "cylinder_diameter_mm": 30.75,
    "cylinder_height_mm": 52,
    "polygon_cutout_radius_mm": 0,
    "polygon_cutout_points": 12,
    "seam_offset_degrees": 355
  },
  "dots": {
    "combined_shape": "rounded",
    "bowl": {"base_diameter_mm": 1.8, "depth_mm": 0.6}
  },
  "indicators": {"enabled": true, "type": "rectangle", "depth_mm": 0.6, "rotate_180": true},
  "export": {"use_client_side_csg": false}
}
```

---

## 7. Versioning & Compatibility

- schema_version: optional string in requests. When present, backend may validate compatibility.
- Cache key may include a cache version field; see caching spec (recommended).

---

## 8. Related Specifications
- Text & Translation: `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md`
- Translation Engine: `LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md`
- Preview: `BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md`
- Spacing & Layout: `BRAILLE_SPACING_SPECIFICATIONS.md`
- Surface Dimensions: `SURFACE_DIMENSIONS_SPECIFICATIONS.md`
- Dot Shapes: `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md`
- Dot Adjustments: `BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md`
- Indicators: `RECESS_INDICATOR_SPECIFICATIONS.md`
- Export & Download: `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md`
- Caching: `CACHING_SYSTEM_CORE_SPECIFICATIONS.md`
- Manifold WASM: `MANIFOLD_WASM_IMPLEMENTATION.md`

---

## 9. Development Guidelines

This section provides explicit instructions for developers working on this codebase when implementing changes.

### Change Workflow for Developers

When asked to modify settings, defaults, UI controls, or core features:

```
1. CONSULT SPECIFICATIONS FIRST
   └── Read SPECIFICATIONS_INDEX.md to locate relevant spec(s)
   └── Read SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md for settings changes
   └── Read feature-specific spec for domain logic

2. VALIDATE AGAINST SCHEMA
   └── Check settings.schema.json for field constraints
   └── Verify enum values and type definitions
   └── Confirm default values match across schema and models

3. IMPLEMENT CHANGES IN ORDER
   └── settings.schema.json (if schema change)
   └── app/models.py CardSettings (if default change)
   └── backend.py (if API change)
   └── Frontend JS/HTML (if UI change)
   └── Update specification document(s)

4. CROSS-VALIDATE
   └── Verify cache key normalization handles new fields
   └── Confirm UI reflects schema constraints
   └── Update SPECIFICATIONS_INDEX.md if new subsystem
```

### Critical Constants (DO NOT CHANGE without updating all 9+ locations)

| Constant | Value | Locations |
|----------|-------|-----------|
| Braille Unicode Start | `0x2800` | app/utils.py, app/validation.py, backend.py (×2), app/geometry/plates.py (×2), app/geometry/cylinder.py, geometry_spec.py, liblouis-worker.js |
| Braille Unicode End | `0x28FF` | Same 9 locations |
| Dot Position Array | `[[0,0],[1,0],[2,0],[0,1],[1,1],[2,1]]` | BRAILLE_SPACING_SPECIFICATIONS.md, geometry generation modules |

### Settings Change Impact Matrix

| Change Type | Files to Modify | Specs to Update |
|-------------|-----------------|-----------------|
| New parameter | schema.json → models.py → backend.py | SETTINGS_SCHEMA_CORE_SPECIFICATIONS |
| Default value change | models.py → schema.json | SETTINGS_SCHEMA_CORE_SPECIFICATIONS + feature spec |
| New enum value | schema.json → models.py | SETTINGS_SCHEMA_CORE_SPECIFICATIONS |
| Remove parameter | Deprecate first, then remove | Add to Document History |
| Geometry-affecting change | Increment `cache_version` in schema | CACHING_SYSTEM_CORE_SPECIFICATIONS |

### Specification Verification Checklist

Before completing any task involving settings:

- [ ] `settings.schema.json` validates new/changed structure
- [ ] `app/models.py` CardSettings has matching defaults
- [ ] Relevant specification document updated with changes
- [ ] `SPECIFICATIONS_INDEX.md` updated if new system/spec added
- [ ] Cache key normalization handles geometry-affecting fields
- [ ] Document History section updated with date and changes

---

## 10. Document History

- 2025-12-06 — Initial creation. Consolidated settings schema across specs; added high-level JSON Schema, normalization and validation rules, and examples.
- 2025-12-06 — Added Development Guidelines (Section 9); added `cache_version` field to schema; added default values to schema properties.
