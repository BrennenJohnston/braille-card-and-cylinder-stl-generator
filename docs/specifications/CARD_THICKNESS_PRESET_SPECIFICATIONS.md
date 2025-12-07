# Card Thickness Preset System Specifications

## Document Purpose

This document defines the Card Thickness Preset System, a frontend convenience feature that automatically adjusts all braille geometry parameters to optimal values for specific 3D printer layer heights (0.3mm and 0.4mm). This system ensures users can quickly configure appropriate settings for their printing capabilities without manually adjusting dozens of individual parameters.

## Scope

- Frontend preset system architecture
- Preset value definitions for 0.3mm and 0.4mm layer heights
- UI controls and user interaction flow
- LocalStorage persistence
- Preset application logic and affected parameters
- Relationship to backend parameter submission

**Out of Scope:**
- Backend validation (presets are frontend-only; backend receives individual parameter values)
- Dynamic preset generation (only two fixed presets)
- Custom preset creation by users

## Source Priority (Order of Correctness)

1. `public/index.html` — Production frontend with preset definitions
2. `templates/index.html` — Template source (should match public/)
3. This specification document
4. SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md — Backend schema for individual parameters

---

## Table of Contents

1. Feature Overview
2. Preset Definitions
3. UI Controls and User Interaction
4. Preset Application Logic
5. Affected Parameters
6. LocalStorage Persistence
7. Integration with Expert Mode
8. Default Behavior
9. Error Handling
10. Verification Checklist
11. Related Specifications
12. Document History

---

## 1. Feature Overview

### Purpose

The Card Thickness Preset System provides two optimized parameter configurations:
- **0.4mm preset**: Optimized for 0.4mm layer height (standard FDM printing)
- **0.3mm preset**: Optimized for 0.3mm layer height (finer detail FDM printing)

### Key Benefits

1. **Simplicity**: Users select one radio button instead of adjusting 20+ parameters
2. **Consistency**: All parameters are guaranteed to work together harmoniously
3. **Print Quality**: Values are pre-tested for optimal braille readability
4. **Persistence**: Selected preset is remembered across browser sessions

### Architecture

```
Frontend Only
┌─────────────────────────────────────┐
│  Card Thickness Radio Buttons       │
│  ┌───────┐ ┌───────┐                │
│  │ 0.4mm │ │ 0.3mm │                │
│  └───────┘ └───────┘                │
└───────────┬─────────────────────────┘
            │
            ├─► Apply Preset (JS function)
            │   └─► Sets all input field values
            │   └─► Updates localStorage
            │   └─► Triggers UI updates
            │
            └─► User submits form
                └─► Backend receives individual parameter values
                    (backend is unaware of "presets")
```

---

## 2. Preset Definitions

### Source Code Location

- `public/index.html`: Lines ~4222-4295
- `templates/index.html`: Lines ~4011-4084

### Complete Preset Values

```javascript
const THICKNESS_PRESETS = {
    '0.4': {
        // Braille Spacing
        grid_columns: 13,
        grid_rows: 4,
        cell_spacing: 6.5,
        line_spacing: 10.0,
        dot_spacing: 2.5,
        braille_x_adjust: 0.0,
        braille_y_adjust: 0.0,

        // Emboss Dot (Rounded)
        rounded_dot_base_diameter: 1.5,
        rounded_dot_base_height: 0.5,
        rounded_dot_dome_diameter: 1.0,
        rounded_dot_dome_height: 0.5,

        // Emboss Dot (Cone)
        emboss_dot_base_diameter: 1.5,
        emboss_dot_height: 0.8,
        emboss_dot_flat_hat: 0.4,

        // Counter Dot (Bowl/Rounded)
        bowl_counter_dot_base_diameter: 1.8,
        counter_dot_depth: 0.8,

        // Counter Dot (Cone)
        cone_counter_dot_base_diameter: 1.9,
        cone_counter_dot_height: 0.7,
        cone_counter_dot_flat_hat: 1.0,

        // Cylinder Dimensions
        cylinder_diameter_mm: 30.8,
        cylinder_height_mm: 52,
        cylinder_polygonal_cutout_radius_mm: 13,
        cylinder_polygonal_cutout_sides: 12,
        seam_offset_deg: 0,

        // Card/Plate Dimensions
        card_width: 90,
        card_height: 52,
        card_thickness: 2.0
    },

    '0.3': {
        // Braille Spacing
        grid_columns: 15,  // More characters possible with finer layers
        grid_rows: 4,
        cell_spacing: 6.5,
        line_spacing: 10.0,
        dot_spacing: 2.5,
        braille_x_adjust: 0.0,
        braille_y_adjust: 0.0,

        // Emboss Dot (Rounded) - optimized for 0.3mm layer
        rounded_dot_base_diameter: 1.5,
        rounded_dot_base_height: 0.5,
        rounded_dot_dome_diameter: 1.0,
        rounded_dot_dome_height: 0.5,

        // Emboss Dot (Cone) - optimized for 0.3mm layer
        emboss_dot_base_diameter: 1.5,
        emboss_dot_height: 0.8,
        emboss_dot_flat_hat: 0.5,  // Slightly larger for 0.3mm

        // Counter Dot (Bowl/Rounded) - optimized for 0.3mm layer
        bowl_counter_dot_base_diameter: 1.5,  // Smaller for finer detail
        counter_dot_depth: 0.7,

        // Counter Dot (Cone) - optimized for 0.3mm layer
        cone_counter_dot_base_diameter: 1.5,
        cone_counter_dot_height: 0.8,
        cone_counter_dot_flat_hat: 0.5,

        // Cylinder Dimensions (same as 0.4mm)
        cylinder_diameter_mm: 30.8,
        cylinder_height_mm: 52,
        cylinder_polygonal_cutout_radius_mm: 13,
        cylinder_polygonal_cutout_sides: 12,
        seam_offset_deg: 0,

        // Card/Plate Dimensions (same as 0.4mm)
        card_width: 90,
        card_height: 52,
        card_thickness: 2.0
    }
};
```

### Key Differences Between Presets

| Parameter | 0.4mm | 0.3mm | Rationale |
|-----------|-------|-------|-----------|
| `grid_columns` | 13 | 15 | Finer layers allow more characters |
| `emboss_dot_flat_hat` | 0.4 | 0.5 | Slightly larger for 0.3mm detail |
| `bowl_counter_dot_base_diameter` | 1.8 | 1.5 | Smaller for finer layer control |
| `cone_counter_dot_base_diameter` | 1.9 | 1.5 | Smaller for finer layer control |
| `cone_counter_dot_flat_hat` | 1.0 | 0.5 | Adjusted for layer height |
| `counter_dot_depth` | 0.8 | 0.7 | Slightly shallower for fine layers |

---

## 3. UI Controls and User Interaction

### UI Location

Card Thickness preset selector appears **above** the Expert Mode toggle:
- After the Braille Grade selection
- Before the "Show Expert Mode" button

### HTML Structure

```html
<div class="grade-selection">
    <fieldset>
        <legend class="grade-label">Card Thickness</legend>
        <div class="radio-group thickness-toggle" role="radiogroup" aria-required="true" aria-label="Select card thickness preset">
            <label class="radio-option">
                <input type="radio" name="card_thickness_preset" value="0.4" checked aria-describedby="thickness-04-desc">
                <span class="radio-text">0.4mm</span>
            </label>
            <span id="thickness-04-desc" class="sr-only">Preset settings optimized for 0.4mm layer height printing</span>
            <label class="radio-option">
                <input type="radio" name="card_thickness_preset" value="0.3" aria-describedby="thickness-03-desc">
                <span class="radio-text">0.3mm</span>
            </label>
            <span id="thickness-03-desc" class="sr-only">Preset settings optimized for 0.3mm layer height printing</span>
        </div>
        <div class="grade-note" style="margin-top: 6px; font-size: 0.85em;">
            Selecting a thickness preset will automatically adjust all braille dot and surface parameters to optimal values for that layer height.
        </div>
    </fieldset>
</div>
```

### User Interaction Flow

1. **User clicks 0.4mm or 0.3mm radio button**
2. **JavaScript applies preset immediately** (no confirmation needed)
3. **All expert mode input fields update** (visible if expert mode is open)
4. **LocalStorage saves selection** (persists across sessions)
5. **Confirmation message displays** (3-second info banner)
6. **User can see updated values** by opening Expert Mode

### Confirmation Message

Format: `Card Thickness preset "X.Xmm" applied. All parameters updated.`

Styling:
- Appears in the existing error/info banner area
- Uses `.error-message.info` classes (blue/info styling)
- Auto-dismisses after 3 seconds

---

## 4. Preset Application Logic

### Function: `applyThicknessPreset(presetKey)`

**Location**: `public/index.html` ~lines 4302-4342, `templates/index.html` ~lines 4091-4131

**Purpose**: Applies all values from a preset to the form inputs

**Algorithm**:

```javascript
function applyThicknessPreset(presetKey) {
    const preset = THICKNESS_PRESETS[presetKey];
    if (!preset) {
        log.debug('Unknown thickness preset:', presetKey);
        return;
    }

    log.debug('Applying thickness preset:', presetKey);

    // Apply each preset value to the corresponding input
    Object.entries(preset).forEach(([inputId, value]) => {
        const input = document.getElementById(inputId);
        if (input) {
            input.value = value;
            log.debug(`Set ${inputId} = ${value}`);

            // Also persist the value to localStorage
            const persistKey = `braille_prefs_${inputId}`;
            try { localStorage.setItem(persistKey, value); } catch (e) {}
        }
    });

    // Persist the selected preset
    try { localStorage.setItem('braille_prefs_thickness_preset', presetKey); } catch (e) {}

    // Update related UI elements
    try { updateGridColumnsForPlateType(); } catch (e) {}
    try { checkCylinderOverflow(); } catch (e) {}
    try { resetToGenerateState(); } catch (e) {}

    // Show confirmation message
    try {
        errorText.textContent = `Card Thickness preset "${presetKey}mm" applied. All parameters updated.`;
        errorDiv.style.display = 'flex';
        errorDiv.className = 'error-message info';
        setTimeout(() => {
            errorDiv.style.display = 'none';
            errorDiv.className = 'error-message';
        }, 3000);
    } catch (e) { /* ignore */ }
}
```

### Event Listeners

**Dual Event Strategy**: Both `change` and `click` events

```javascript
document.querySelectorAll('input[name="card_thickness_preset"]').forEach(radio => {
    // Fires when switching between radio buttons
    radio.addEventListener('change', function() {
        if (this.checked) {
            applyThicknessPreset(this.value);
        }
    });

    // Fires when clicking an already-selected radio button (re-apply)
    radio.addEventListener('click', function() {
        if (this.checked) {
            applyThicknessPreset(this.value);
        }
    });
});
```

**Rationale for Dual Events**:
- `change`: Handles switching between 0.3mm and 0.4mm
- `click`: Allows users to re-apply the current preset (resets manually changed values)

---

## 5. Affected Parameters

### Complete Parameter List

The preset system controls **26 parameters** across 5 categories:

#### A. Braille Spacing (7 parameters)
- `grid_columns` — Number of braille cells (characters)
- `grid_rows` — Number of braille lines
- `cell_spacing` — Horizontal spacing between braille cells (mm)
- `line_spacing` — Vertical spacing between braille lines (mm)
- `dot_spacing` — Spacing between individual dots in a cell (mm)
- `braille_x_adjust` — Horizontal offset adjustment (mm)
- `braille_y_adjust` — Vertical offset adjustment (mm)

#### B. Emboss Dot Rounded Shape (4 parameters)
- `rounded_dot_base_diameter` — Cone base diameter at surface (mm)
- `rounded_dot_base_height` — Cone base height (mm)
- `rounded_dot_dome_diameter` — Dome diameter / cone flat top (mm)
- `rounded_dot_dome_height` — Dome height above cone (mm)

#### C. Emboss Dot Cone Shape (3 parameters)
- `emboss_dot_base_diameter` — Dot diameter at base (mm)
- `emboss_dot_height` — Dot height (mm)
- `emboss_dot_flat_hat` — Flat hat diameter at top (mm)

#### D. Counter Dot Bowl Recess (2 parameters)
- `bowl_counter_dot_base_diameter` — Bowl opening diameter (mm)
- `counter_dot_depth` — Bowl recess depth (mm)

#### E. Counter Dot Cone Recess (3 parameters)
- `cone_counter_dot_base_diameter` — Cone base diameter (mm)
- `cone_counter_dot_height` — Cone recess height (mm)
- `cone_counter_dot_flat_hat` — Flat hat diameter (mm)

#### F. Cylinder Dimensions (5 parameters)
- `cylinder_diameter_mm` — Cylinder outer diameter (mm)
- `cylinder_height_mm` — Cylinder height (mm)
- `cylinder_polygonal_cutout_radius_mm` — Cutout radius (mm)
- `cylinder_polygonal_cutout_sides` — Cutout polygon sides
- `seam_offset_deg` — Seam rotation offset (degrees)

#### G. Card/Plate Dimensions (3 parameters)
- `card_width` — Card width (mm)
- `card_height` — Card height (mm)
- `card_thickness` — Card thickness (mm)

### Parameters NOT Affected by Presets

The following UI elements are **NOT** controlled by presets:

1. **Text Input Fields**:
   - `line1`, `line2`, `line3`, `line4` (braille text)
   - `original_line1`, etc. (original text for indicators)

2. **Selection Controls**:
   - Language table dropdown
   - Shape type (Card/Cylinder)
   - Plate type (Emboss/Counter)
   - Dot shape selection (Rounded/Cone radio)
   - Recess shape selection (Bowl/Cone radio)
   - Indicator shapes toggle

3. **Export Options**:
   - Filename prefix
   - Client-side CSG toggle
   - Manifold repair toggle

---

## 6. LocalStorage Persistence

### Keys Stored

1. **Preset Selection**:
   - Key: `braille_prefs_thickness_preset`
   - Value: `"0.4"` or `"0.3"`

2. **Individual Parameters** (26 keys):
   - Format: `braille_prefs_{parameter_name}`
   - Example: `braille_prefs_grid_columns` = `"13"`
   - Example: `braille_prefs_emboss_dot_height` = `"0.8"`

### Persistence Strategy

**Both** the preset selection AND individual values are stored:
- **Preset key**: Used to restore the selected radio button on page load
- **Individual values**: Ensures values persist even if preset definition changes

### Restoration on Page Load

```javascript
(function restoreThicknessPreset() {
    try {
        const savedPreset = localStorage.getItem('braille_prefs_thickness_preset');
        const presetToApply = (savedPreset && THICKNESS_PRESETS[savedPreset]) ? savedPreset : '0.4';

        // Set the radio button
        const radio = document.querySelector(`input[name="card_thickness_preset"][value="${presetToApply}"]`);
        if (radio) {
            radio.checked = true;
        }

        // Apply the preset to ensure all values are consistent
        // This fixes the issue where HTML defaults don't match preset values
        applyThicknessPreset(presetToApply);
        log.debug('Applied thickness preset on load:', presetToApply);
    } catch (e) {
        log.debug('Error restoring thickness preset:', e);
    }
})();
```

**Critical Fix (2025-12-07)**:
- **Problem**: Original implementation only set the radio button but didn't apply preset values on load
- **Result**: HTML default values (which didn't match presets) were displayed instead
- **Solution**: Now applies the preset on page load, ensuring consistency

---

## 7. Integration with Expert Mode

### Visibility Behavior

- **Preset Controls**: Always visible (above Expert Mode toggle)
- **Affected Parameters**: Only visible when Expert Mode is expanded
- **Real-time Updates**: If Expert Mode is open, parameter changes are immediately visible

### Interaction with Manual Changes

1. **User selects 0.4mm preset** → All parameters set to 0.4mm values
2. **User opens Expert Mode** → Sees all values matching 0.4mm preset
3. **User manually changes one parameter** (e.g., `grid_columns` to 14)
4. **Parameter localStorage updates** with new value
5. **Preset localStorage still shows "0.4"** (not cleared)
6. **User clicks 0.4mm again** → Resets all parameters to original 0.4mm values

This behavior allows "resetting" manually changed values by re-clicking the current preset.

### Expert Mode Parameter Location

All preset-controlled parameters are located in Expert Mode submenus:

```
Expert Mode (dropdown)
├── Braille Spacing
│   ├── grid_columns, grid_rows
│   ├── cell_spacing, line_spacing, dot_spacing
│   └── braille_x_adjust, braille_y_adjust
├── Braille Dot Adjustments
│   ├── Rounded Shape (4 params)
│   ├── Cone Shape (3 params)
│   ├── Counter Bowl (2 params)
│   └── Counter Cone (3 params)
└── Surface Dimensions
    ├── Cylinder (5 params)
    └── Plate (3 params)
```

---

## 8. Default Behavior

### First-Time User (No LocalStorage)

1. **0.4mm radio button is checked** (HTML `checked` attribute)
2. **Preset is applied on page load** (as of 2025-12-07 fix)
3. **All parameters match 0.4mm preset**
4. **LocalStorage is populated** with 0.4mm values

### Returning User (LocalStorage Exists)

1. **Saved preset radio button is checked**
2. **Saved preset is applied** (overwrites HTML defaults)
3. **All parameters match saved preset**
4. **If saved preset is invalid**: Falls back to 0.4mm

### Reset All Preferences

When user clicks "Reset All Preferences" button:
1. **LocalStorage is cleared** (all keys)
2. **0.4mm preset is applied** (explicit reset)
3. **Radio button set to 0.4mm**

**Code Reference** (`public/index.html` ~lines 4171-4178):

```javascript
// Reset thickness preset to default (0.4mm)
try {
    localStorage.setItem('braille_prefs_thickness_preset', '0.4');
    const thicknessRadio = document.querySelector('input[name="card_thickness_preset"][value="0.4"]');
    if (thicknessRadio) thicknessRadio.checked = true;
} catch (e) {}
```

---

## 9. Error Handling

### Graceful Degradation

All preset operations are wrapped in try-catch blocks:

```javascript
try { localStorage.setItem(persistKey, value); } catch (e) {}
try { updateGridColumnsForPlateType(); } catch (e) {}
try { checkCylinderOverflow(); } catch (e) {}
try { resetToGenerateState(); } catch (e) {}
```

### Failure Scenarios

| Scenario | Behavior |
|----------|----------|
| LocalStorage unavailable (private browsing) | Preset still applies to current session |
| Invalid preset key in localStorage | Falls back to 0.4mm preset |
| Missing input element for parameter | Skips that parameter, continues with others |
| UI update function throws error | Continues applying other parameters |
| Confirmation message fails | Preset still applies (message is cosmetic) |

### No User-Facing Errors

The preset system is designed to **never fail visibly**:
- If localStorage fails, values persist for current session
- If a parameter fails to apply, others still apply
- If UI updates fail, core preset application continues

---

## 10. Verification Checklist

### Implementation Consistency

- [x] `public/index.html` contains preset definitions
- [x] `templates/index.html` matches `public/index.html` exactly
- [x] All 26 parameters have corresponding `<input>` elements with matching IDs
- [x] Both `change` and `click` events are attached to radio buttons
- [x] Preset is applied on page load (2025-12-07 fix)
- [x] LocalStorage persistence works for both preset and individual values
- [x] Reset All Preferences resets to 0.4mm preset
- [x] Confirmation message displays with 3-second timeout

### Parameter Coverage

- [x] All spacing parameters included (7 parameters)
- [x] All emboss rounded dot parameters included (4 parameters)
- [x] All emboss cone dot parameters included (3 parameters)
- [x] All counter bowl parameters included (2 parameters)
- [x] All counter cone parameters included (3 parameters)
- [x] All cylinder dimension parameters included (5 parameters)
- [x] All card dimension parameters included (3 parameters)
- [x] **Total**: 27 parameters (26 in presets + 1 derived)

### Backend Integration

- [x] Backend receives individual parameter values (not aware of presets)
- [x] All preset parameters exist in `settings.schema.json` or equivalent backend structures
- [x] Parameter names match between frontend and backend APIs
- [x] No backend changes required for preset system (frontend-only feature)

---

## 11. Related Specifications

### Direct Dependencies
- **BRAILLE_SPACING_SPECIFICATIONS.md** — Spacing parameter definitions
- **BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md** — Dot shape parameter definitions
- **SURFACE_DIMENSIONS_SPECIFICATIONS.md** — Cylinder and plate dimension parameters
- **UI_INTERFACE_CORE_SPECIFICATIONS.md** — UI layout and controls

### Schema References
- **SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md** — Backend parameter schema
- **settings.schema.json** — JSON schema for backend validation

### User Interaction
- **BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md** — Text input (not affected by presets)
- **STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md** — Generation process using preset values

---

## 12. Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-07 | 1.0 | Initial creation. Documented Card Thickness Preset System including preset definitions, UI controls, application logic, localStorage persistence, and default behavior. |
| 2025-12-07 | 1.1 | Documented critical bug fix: preset now applies on page load to ensure consistency between HTML defaults and preset values. Added dual event listener strategy (change + click). |

---

**Document Version**: 1.1
**Created**: 2025-12-07
**Purpose**: Specification for Card Thickness Preset System (frontend convenience feature)
**Status**: ✅ Complete
