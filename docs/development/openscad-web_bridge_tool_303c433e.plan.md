---
name: OpenSCAD-Web Bridge Tool
overview: A bidirectional parameter/schema + validation harness that bridges OpenSCAD parametric models and web-based STL generators. v1 prioritizes reliable schema/UI parity + STL parity checks, and supports OpenSCAD→Web by running OpenSCAD in the browser (WASM) to avoid full geometry translation.
todos:
  - id: create-repo
    content: Create new openscad-web-bridge repository with project structure
    status: pending
  - id: decide-v1-scope
    content: Decide v1 execution strategy (OpenSCAD WASM wrapper) + explicit non-goals (no arbitrary SCAD→native-JS geometry translation)
    status: pending
    dependencies:
      - create-repo
  - id: license-strategy
    content: Decide licensing/distribution approach for OpenSCAD/WASM usage in generated web apps (notices, source availability, scaffold licensing)
    status: pending
    dependencies:
      - decide-v1-scope
  - id: port-validation
    content: Port and generalize validation framework from braille-stl-generator-openscad
    status: pending
    dependencies:
      - create-repo
  - id: define-schema
    content: Define Parameter Schema JSON spec as intermediate representation (JSON Schema + UI metadata + dependency rules)
    status: pending
    dependencies:
      - create-repo
      - decide-v1-scope
  - id: adapters
    content: Define adapter/plugin interfaces for (a) param extraction, (b) STL generation, (c) UI extraction/validation, (d) text/help extraction
    status: pending
    dependencies:
      - define-schema
  - id: openscad-parser
    content: Build OpenSCAD Customizer param extractor (plus optional params.json manifest fallback)
    status: pending
    dependencies:
      - define-schema
  - id: web-template
    content: Create Vercel web app template (v1: OpenSCAD WASM wrapper + schema-driven UI)
    status: pending
    dependencies:
      - define-schema
      - decide-v1-scope
      - license-strategy
  - id: ui-generator
    content: Build UI form generator from Parameter Schema (labels, help text, grouping, ordering, units, enable/disable rules)
    status: pending
    dependencies:
      - web-template
  - id: web-parser
    content: Build web API/UI parameter analyzer (v1: schema-first projects only; add heuristics later)
    status: pending
    dependencies:
      - define-schema
  - id: openscad-generator
    content: Build OpenSCAD file generator with Customizer annotations (for web→OpenSCAD in schema-first direction)
    status: pending
    dependencies:
      - define-schema
  - id: validation-engine
    content: Build iterative validation + refinement engine (schema + UI + STL parity), producing actionable diffs and optional safe auto-fixes
    status: pending
    dependencies:
      - port-validation
      - openscad-parser
      - web-parser
      - adapters
  - id: cli-tool
    content: Create CLI for extract, scaffold, validate, sync
    status: pending
    dependencies:
      - validation-engine
      - ui-generator
      - openscad-generator
  - id: security-sandbox
    content: Add safe-execution constraints for untrusted inputs (timeouts, resource limits, fetch allowlist, file access policy) and document threat model
    status: pending
    dependencies:
      - cli-tool
  - id: ci
    content: Add CI pipeline running validation suites against example projects + golden fixtures
    status: pending
    dependencies:
      - validation-engine
  - id: documentation
    content: Write docs + example projects (OpenSCAD→Web via WASM; Web→OpenSCAD via schema-first sample)
    status: pending
    dependencies:
      - ci
---

## Bidirectional OpenSCAD-Web Parametric Generator Tool

## Feasibility Report Summary

**Overall Feasibility: HIGH (v1, “same-geometry-source” approach)** — A general-purpose *parameter/schema + validation harness* is achievable if we **do not attempt geometry translation**. The proven path is: OpenSCAD remains the geometry source, and the web app runs OpenSCAD (WASM) to generate STL.

**Feasibility: MEDIUM (web→OpenSCAD, schema-first only)** — Generating OpenSCAD from a known schema is feasible (emit `-D` parameters + Customizer annotations), but reverse-engineering arbitrary web apps into `.scad` is not realistic without strong constraints.

**Feasibility: LOW (automatic SCAD↔native-JS geometry conversion)** — Converting arbitrary OpenSCAD geometry into an equivalent JS/Three.js/JSCAD generator is research-grade and not a v1/v2 target.

### v1 Scope Guardrails (must-haves)

- **Parameter extraction must be explicit**: require OpenSCAD Customizer annotations and/or a `params.json` manifest in v1.
- **Deterministic meshing**: enforce fixed tessellation settings (`$fn/$fa/$fs` or OpenSCAD CLI equivalents) and stable export flags to make STL diffs meaningful.
- **Validation uses tolerances, not exact equality**: mesh outputs will differ in triangle order/partitioning across engines.

---

## Research Findings: Existing Open Source Tools (building blocks only)

**No comprehensive solution exists** that does bidirectional scaffold + iterative schema/UI/STL parity validation for arbitrary projects. Useful components exist:

| Tool | Purpose | Limitation / Notes |
|------|---------|--------------------|
| [OpenSCAD](https://github.com/openscad/openscad) | Reference implementation; CLI renderer; source for WASM builds | Not a stable “SCAD→AST library” for third-party param extraction; WASM integration still requires significant glue. |
| [`seasick/openscad-web-gui`](https://github.com/seasick/openscad-web-gui) | Full web UI around OpenSCAD WASM | **License appears GPL-3.0** on GitHub; treat as reference architecture, not a drop-in MIT template. |
| [OpenJSCAD / JSCAD](https://openjscad.xyz/) | JS parametric CAD runtime | Different language/runtime; may help for optional “native JS” path, but doesn’t solve arbitrary `.scad` conversion. |
| [SolidPython](https://github.com/SolidCode/SolidPython) | Generate OpenSCAD from Python | Good for emitting OpenSCAD from schema; not reverse conversion. |
| [trimesh](https://trimesh.org/) | Python mesh analysis (load STLs, compute metrics) | Great for CI/local validation. **Not available in Vercel production for this repo** (heavy deps are dev-only). |
| [CloudCompare](https://cloudcompare.org/) | Mesh comparison tooling | Powerful, but an external dependency; consider optional “power user” integration only. |
| [STL-to-OpenSCAD Converter](https://github.com/raviriley/STL-to-OpenSCAD-Converter) | Convert mesh to OpenSCAD polyhedra | Loses parametric information; not a bridge. |
| JSON-Schema form renderers (e.g. `react-jsonschema-form`) | Generate web UI from JSON Schema | Excellent fit for schema-first UIs; still need extraction + validation + STL pipeline. |

**Conclusion**: We build a bridge tool + harness, and optionally reuse runtime components where licensing permits.

---

## OpenSCAD WASM: Integration Notes (v1 critical path)

Recommended execution model:

- **Main thread**: UI + preview + download
- **Web Worker**: OpenSCAD WASM runtime + virtual FS + STL export
- **Asset strategy**: lazy-load WASM after first paint; cache aggressively

Key requirements:

- Run WASM in a worker (avoid UI freeze)
- Virtualize filesystem (no direct disk access)
- Fetch `.scad` + includes into FS
- Return STL as `ArrayBuffer` over `postMessage()`

---

## Validation Strategy (what “iterative parity” means)

Validation is layered; only some layers can be auto-fixed safely:

- **Schema parity**: parameter names/types/defaults/ranges/enums/units match between sources.
- **UI parity**: labels/help/grouping/visibility rules match (best-effort; human review often required).
- **STL parity**: compare generated meshes under controlled settings with tolerances.

Suggested STL parity metrics (in order of robustness):

- bounding box extents (within tolerance)
- volume and surface area (within tolerance)
- sampled surface distance (approx Hausdorff / nearest-neighbor) (within tolerance)

---

## License Considerations ⚠️

**OpenSCAD is GPL-licensed.** Any approach that ships OpenSCAD (including WASM artifacts) in a web app should assume GPL obligations apply to that distributed runtime.

Practical compliance checklist for generated web apps:

1. Prominent OSS notices (About/Credits)
2. Clear instructions to obtain corresponding source for the shipped OpenSCAD artifact
3. Third-party notices file (`THIRD_PARTY_NOTICES.md`) + license bundle
4. Keep proprietary code separated; avoid commingling unless you intend to license compatibly

