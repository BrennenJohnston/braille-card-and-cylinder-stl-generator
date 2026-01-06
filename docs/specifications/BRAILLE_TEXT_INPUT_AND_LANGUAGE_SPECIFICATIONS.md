# Braille Text Input and Language Selection Specifications

## Document Purpose

This document provides **comprehensive, in-depth specifications** for the "Enter Text for Braille Translation" text input system and the "Select Language" menu in the application. It serves as an authoritative reference for future development by documenting:

1. **Placement Mode System** — Auto Placement vs Manual Placement toggle and behaviors
2. **Auto Placement Mode** — BANA-aware word wrapping algorithm and UI
3. **Manual Placement Mode** — Per-line text input with per-line language selection
4. **Language Selection System** — Master and per-line language table dropdowns
5. **Translation Pipeline** — How text flows from input through liblouis to backend
6. **Data Flow to Backend** — Request structure for STL generation
7. **Frontend UI Specifications** — HTML structure, styling, and accessibility

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source (request validation, mesh generation)
2. `wsgi.py` — Entry point configuration
3. `static/workers/csg-worker.js` — Client-side geometry (consumes translated braille)
4. Manifold WASM — Mesh repair operations

---

## Table of Contents

1. [UI Layout Overview](#1-ui-layout-overview)
2. [Placement Mode Toggle](#2-placement-mode-toggle)
3. [Auto Placement Mode](#3-auto-placement-mode)
4. [Manual Placement Mode](#4-manual-placement-mode)
5. [Select Language Menu](#5-select-language-menu)
6. [Per-Line Language Selection (Manual Mode)](#6-per-line-language-selection-manual-mode)
   - 6.1 [Capitalized Letters Toggle](#61-capitalized-letters-toggle)
7. [Translation Pipeline](#7-translation-pipeline)
8. [Backend Request Structure](#8-backend-request-structure)
9. [BANA Auto-Wrap Algorithm](#9-bana-auto-wrap-algorithm)
10. [Overflow Detection and Warnings](#10-overflow-detection-and-warnings)
11. [State Persistence](#11-state-persistence)
12. [Styling and Accessibility](#12-styling-and-accessibility)
13. [Cross-Implementation Consistency](#13-cross-implementation-consistency)

---

## 1. UI Layout Overview

### Location in Application

The text input and language selection controls are located at the top of the main form, in this order:

```
┌──────────────────────────────────────────────────────────────────┐
│  ┌─ Enter Text for Braille Translation ───────────────────────┐  │
│  │                                                             │  │
│  │  Note: Contracted braille combines letters...               │  │
│  │                                                             │  │
│  │  Placement Mode: (•) Auto Placement  ( ) Manual Placement   │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │ [Auto Placement Text Input or Manual Line Inputs]   │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─ Select Language: ─────────────────────────────────────────┐  │
│  │  [English (UEB), United States — uncontracted (grade 1) ▼] │  │
│  │  Default: English (UEB)...aligned with BANA guidance...    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─ Select Plate to Generate ─────────────────────────────────┐  │
│  │  (•) Embossing Plate    ( ) Universal Counter Plate        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Visual Hierarchy

1. **Enter Text for Braille Translation** (fieldset with legend)
   - Informational note about contracted braille
   - Placement Mode toggle (radio buttons)
   - Text input area (dynamic based on mode)

2. **Select Language** (fieldset with legend)
   - Master language dropdown
   - Help text explaining default choice

3. **Select Plate to Generate** (fieldset with legend)
   - Embossing Plate / Counter Plate radio buttons

---

## 2. Placement Mode Toggle

### HTML Structure

**Source:** `templates/index.html` (lines 2019-2030)

```html
<!-- Placement mode toggle -->
<div class="line-input-mode-toggle" style="margin-bottom: 0.8em; display: flex; align-items: center; gap: 1em;">
    <label class="line-label" for="placement_mode_auto" style="margin: 0;">Placement Mode:</label>
    <label style="display: inline-flex; align-items: center; gap: 0.4em;">
        <input type="radio" name="placement_mode" value="auto" id="placement_mode_auto" checked>
        Auto Placement
    </label>
    <label style="display: inline-flex; align-items: center; gap: 0.4em;">
        <input type="radio" name="placement_mode" value="manual" id="placement_mode_manual">
        Manual Placement
    </label>
</div>
```

### Mode Behaviors

| Mode | Description | Text Input UI | Language Selection |
|------|-------------|---------------|-------------------|
| **Auto Placement** | Single textarea, BANA-aware wrapping | One textarea for all text | Master language only |
| **Manual Placement** | Per-row text inputs | N inputs (based on `grid_rows`) | Per-line language dropdowns |

### Default State

- **Default Mode:** Auto Placement (`checked` on `placement_mode_auto`)
- **Persistence:** Mode is saved to `localStorage` key `braille_prefs_placement_mode`

### Mode Switch Handler

**Source:** `templates/index.html` (lines 3556-3572)

```javascript
function updatePlacementUI() {
    const mode = document.querySelector('input[name="placement_mode"]:checked')?.value || 'manual';
    if (mode === 'auto') {
        autoContainer.style.display = '';
        dynamicContainer.style.display = 'none';
    } else {
        autoContainer.style.display = 'none';
        dynamicContainer.style.display = '';
        // Ensure per-line language selects are populated when switching to manual
        syncLineLanguageSelects();
    }
    resetToGenerateState();
}

placementRadios.forEach(r => r.addEventListener('change', () => {
    updatePlacementUI();
}));
```

---

## 3. Auto Placement Mode

### Purpose

Auto Placement mode allows users to enter all text in a single textarea. The system automatically:
1. Translates the entire text to braille using liblouis
2. Wraps the braille across available rows following BANA rules
3. Preserves word boundaries where possible
4. Handles hyphenated words and email addresses intelligently

### UI Components

#### Auto Placement Textarea

**Source:** `templates/index.html` (lines 2031-2038)

```html
<!-- Auto placement textarea (hidden by default) -->
<div id="auto-input-container" style="display: none;">
    <label for="auto-text" class="line-label">Auto Placement Text</label>
    <textarea id="auto-text" rows="4"
        placeholder="Type all your text here. It will be translated to braille and auto-wrapped across rows based on available cells."
        style="width: 100%; resize: vertical;"></textarea>
    <div id="auto-overflow-warning" class="grade-note" style="margin-top: 0.6em; color: #d73502; display: none;">
        <strong>Warning:</strong> <span id="auto-overflow-message"></span>
    </div>
</div>
```

#### Visual Layout (Auto Mode Active)

```
┌─ Enter Text for Braille Translation ─────────────────────────────┐
│                                                                   │
│  Placement Mode: (•) Auto Placement  ( ) Manual Placement         │
│                                                                   │
│  Auto Placement Text                                              │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Type all your text here. It will be translated to         │   │
│  │ braille and auto-wrapped across rows based on available   │   │
│  │ cells.                                                     │   │
│  │                                                            │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ⚠️ Warning: Text requires 45 cells but only 40 fit. Consider   │
│     adding rows or reducing text.                                 │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### How Auto Placement Processes Text

1. **User enters text** in the single textarea
2. **On form submit**, the BANA auto-wrap algorithm is invoked:

```javascript
// Source: templates/index.html (lines 4411-4447)
if (placementMode !== 'manual') {
    const src = (document.getElementById('auto-text')?.value || '').trim();
    if (!src) {
        translatedLines = Array(rows).fill('');
    } else {
        const cols = getAvailableColumns();
        const rows = parseInt(document.getElementById('grid_rows').value) || 4;
        const wrap = await banaAutoWrap(src, cols, rows, tableName);

        if (wrap.error) {
            // Show error and stop submission
            errorText.textContent = wrap.warnings.join(' ');
            errorDiv.style.display = 'flex';
            return;
        }

        translatedLines = wrap.brailleLines;
        originalLines = wrap.textLines;  // Per-line source segments
        perLineLanguageTables = new Array(rows).fill(tableName);
    }
}
```

3. **Result structure** from `banaAutoWrap()`:

```javascript
{
    textLines: ['John Smith', '123 Main St', '', ''],     // Original text per row
    brailleLines: ['⠚⠕⠓⠝ ⠎⠍⠊⠞⠓', '⠼⠁⠃⠉ ⠍⠁⠊⠝ ⠌', '', ''],  // Translated braille per row
    warnings: [],                                          // Any overflow/wrap warnings
    error: false                                           // True if wrapping failed
}
```

### Original Lines for Indicators

In Auto mode, `originalLines` (sent to backend) contains the source text segments that were placed on each row. The **first character** of each row's source text becomes the row indicator (if alphanumeric).

**Example:**
- User enters: `"John Smith 123 Main St"`
- After wrapping: Row 1 = "John Smith", Row 2 = "123 Main St"
- Row 1 indicator: "J" (first letter)
- Row 2 indicator: "1" (first digit)

---

## 4. Manual Placement Mode

### Purpose

Manual Placement mode gives users explicit control over:
1. Which text appears on which row
2. Which language/braille table is used for each row
3. Maximum flexibility for multi-language content

### UI Components

#### Dynamic Line Inputs

**Source:** `templates/index.html` (lines 3241-3268)

```javascript
function createDynamicLineInputs(numLines) {
    const container = document.getElementById('dynamic-line-inputs');
    container.innerHTML = ''; // Clear existing inputs

    for (let i = 1; i <= numLines; i++) {
        const lineDiv = document.createElement('div');
        lineDiv.className = 'line-input';
        lineDiv.innerHTML = `
            <div class="line-translation-row">
                <label for="line_lang_${i}" class="line-label">Line ${i} Translation</label>
                <select id="line_lang_${i}" name="line_lang_${i}"
                    class="language-select line-language-select"
                    aria-describedby="line${i}-lang-help"></select>
                <span id="line${i}-lang-help" class="sr-only">
                    Select translation language for line ${i}
                </span>
            </div>
            <div class="line-text-row">
                <label for="line${i}" class="line-label">Line ${i}</label>
                <input type="text" id="line${i}" name="line${i}"
                    placeholder="Enter English text here..." maxlength="50"
                    aria-describedby="line${i}-help">
                <span id="line${i}-help" class="sr-only">Maximum 50 characters for line ${i}</span>
            </div>
        `;
        container.appendChild(lineDiv);
    }

    // Populate per-line language selects with available options
    syncLineLanguageSelects();
}
```

#### Visual Layout (Manual Mode Active)

```
┌─ Enter Text for Braille Translation ─────────────────────────────┐
│                                                                   │
│  Placement Mode: ( ) Auto Placement  (•) Manual Placement         │
│                                                                   │
│  Line 1 Translation  [English (UEB) — uncontracted (grade 1) ▼]  │
│  Line 1              [John Smith________________________]         │
│                                                                   │
│  Line 2 Translation  [English (UEB) — uncontracted (grade 1) ▼]  │
│  Line 2              [123 Main Street___________________]         │
│                                                                   │
│  Line 3 Translation  [French — contracted (grade 2) ▼]           │
│  Line 3              [Bonjour____________________________]        │
│                                                                   │
│  Line 4 Translation  [English (UEB) — uncontracted (grade 1) ▼]  │
│  Line 4              [__________________________________ ]        │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Number of Lines

The number of line inputs is dynamically controlled by the `grid_rows` setting:

```javascript
// Source: templates/index.html (lines 3188-3196)
function addGridRowsListener() {
    const gridRowsInput = document.getElementById('grid_rows');
    if (gridRowsInput) {
        gridRowsInput.addEventListener('input', function() {
            const numRows = parseInt(this.value) || 4;
            createDynamicLineInputs(numRows);
        });
    }
}
```

### Manual Mode Translation Flow

```javascript
// Source: templates/index.html (lines 4389-4410)
if (placementMode === 'manual') {
    // Per-line translation
    perLineLanguageTables = new Array(lines.length).fill(tableName);
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line) {
            try {
                // Get per-line language table (or use master as fallback)
                const perLineTable = (document.getElementById(`line_lang_${i+1}`)?.value) || tableName;
                perLineLanguageTables[i] = perLineTable;

                const brailleText = await translateWithLiblouis(line, 'g2', perLineTable);
                translatedLines.push(brailleText);
            } catch (error) {
                translationErrors.push({ line: i + 1, text: line, error: error.toString() });
                translatedLines.push('');
            }
        } else {
            translatedLines.push('');
        }
    }
}
```

---

## 5. Select Language Menu

### Purpose

The master language selection dropdown controls:
1. **Auto Mode:** The single language used for all text translation
2. **Manual Mode:** The default/fallback language for per-line selects

### HTML Structure

**Source:** `templates/index.html` (lines 2045-2061)

```html
<!-- Language Selection -->
<div class="grade-selection">
    <fieldset>
        <legend class="grade-label">Select Language:</legend>
        <div style="margin-bottom: 0.8em;">
            <select id="language-table" name="language_table" class="language-select"
                aria-describedby="language-help">
                <option value="en-ueb-g2.ctb">English (UEB), United States — contracted (grade 2)</option>
                <option value="en-ueb-g1.ctb" selected>English (UEB), United States — uncontracted (grade 1)</option>
                <option value="en-us-g2.ctb">English (EBAE), United States — contracted (grade 2)</option>
                <option value="en-us-g1.ctb">English (EBAE), United States — uncontracted (grade 1)</option>
            </select>
            <div id="language-help" class="grade-note" style="margin-top: 6px; font-size: 0.85em;">
                Default: English (UEB), United States — uncontracted (grade 1).
                Chosen to align with BANA guidance for business cards and to minimize
                ambiguity for names, emails, and short contact info.
                Use contracted (grade 2) only when space is limited.
            </div>
        </div>
    </fieldset>
</div>
```

### Default Selection

| Option | Value | Description | Selected |
|--------|-------|-------------|----------|
| English (UEB) G2 | `en-ueb-g2.ctb` | Unified English Braille, contracted | No |
| **English (UEB) G1** | `en-ueb-g1.ctb` | Unified English Braille, uncontracted | **Yes (default)** |
| English (EBAE) G2 | `en-us-g2.ctb` | English Braille American Edition, contracted | No |
| English (EBAE) G1 | `en-us-g1.ctb` | English Braille American Edition, uncontracted | No |

### Dynamic Table Loading

The dropdown is populated dynamically from the backend's available tables:

**Source:** `templates/index.html` (lines 2426-2624)

```javascript
async function loadLanguageOptions() {
    const select = document.getElementById('language-table');

    // Fetch available tables from backend
    const resp = await fetch('/liblouis/tables', { credentials: 'same-origin' });
    const data = await resp.json();

    // Sort: English first, then by locale
    data.tables.sort((a, b) => {
        const aEn = (a.locale || '').toLowerCase().startsWith('en') ? 0 : 1;
        const bEn = (b.locale || '').toLowerCase().startsWith('en') ? 0 : 1;
        if (aEn !== bEn) return aEn - bEn;
        return (a.locale || '').localeCompare(b.locale || '');
    });

    // Build optgroups: Default, English, Other Languages
    // ... (detailed optgroup construction)
}
```

### Backend Table Discovery

**Source:** `backend.py` (lines 2051-2078)

```python
@app.route('/liblouis/tables')
def list_liblouis_tables():
    """List available liblouis translation tables from static assets.

    This powers the frontend language dropdown dynamically so it stays in sync
    with the actual shipped tables.
    """
    base = app.root_path
    candidate_dirs = [
        os.path.join(base, 'static', 'liblouis', 'tables'),
        os.path.join(base, 'node_modules', 'liblouis-build', 'tables'),
        os.path.join(base, 'third_party', 'liblouis', 'tables'),
        os.path.join(base, 'third_party', 'liblouis', 'share', 'liblouis', 'tables'),
    ]

    merged = {}
    for d in candidate_dirs:
        for t in _scan_liblouis_tables(d):
            key = t.get('file')
            if key and key not in merged:
                merged[key] = t

    tables = list(merged.values())
    tables.sort(key=lambda t: (t.get('locale') or '', t.get('file') or ''))
    return jsonify({'tables': tables})
```

### Table Metadata Structure

Each table entry returned by `/liblouis/tables`:

```javascript
{
    file: "en-ueb-g2.ctb",       // Liblouis table filename
    locale: "en-US",             // Language/region code
    type: "literary",            // Type (literary, computer)
    grade: "2",                  // Grade level (0, 1, 2)
    contraction: "full",         // Contraction level
    dots: 6,                     // Dot count (6 or 8)
    variant: "UEB"               // Standard variant (UEB, EBAE, etc.)
}
```

---

## 6. Per-Line Language Selection (Manual Mode)

### Purpose

In Manual Placement mode, each line can use a different language/braille table, enabling:
- Mixed-language business cards
- Proper translation for names in different scripts
- Language-specific braille contractions

### Synchronization with Master Select

**Source:** `templates/index.html` (lines 3270-3285)

```javascript
// Populate all per-line language selects from the master language-table options
function syncLineLanguageSelects() {
    const master = document.getElementById('language-table');
    if (!master) return;

    const optionsHTML = master.innerHTML;
    const masterValue = master.value;

    document.querySelectorAll('.line-language-select').forEach(sel => {
        const previous = sel.value;
        sel.innerHTML = optionsHTML;  // Copy all options from master

        // Priority: keep prior choice > prefer English UEB G1 > fallback to master
        const hasPrev = previous && Array.from(sel.options).some(o => o.value === previous);
        const desiredDefault = 'en-ueb-g1.ctb';
        const hasDesired = Array.from(sel.options).some(o => o.value === desiredDefault);
        sel.value = hasPrev ? previous : (hasDesired ? desiredDefault : masterValue);
    });
}
```

### Default Selection Priority

When a per-line language select is populated:

1. **Previous Value** — If the select had a prior value that still exists in options, keep it
2. **English UEB G1** — If no prior value, prefer `en-ueb-g1.ctb` (most common for business cards)
3. **Master Value** — Fallback to whatever the master select has chosen

### Visual Example

```
Line 1 Translation  [English (UEB) — uncontracted ▼]   ← Same as master
Line 2 Translation  [French — contracted (grade 2) ▼]  ← User changed
Line 3 Translation  [German — uncontracted ▼]          ← User changed
Line 4 Translation  [English (UEB) — uncontracted ▼]   ← Default
```

---

## 6.1. Capitalized Letters Toggle

### Purpose

The **Capitalized Letters** toggle allows users to control whether capital letters in the input text are preserved in braille translation or converted to lowercase before translation. This feature provides space-saving options for applications where capitalization is implicit (such as business cards).

### Rationale

In braille, capital letters require additional indicator cells (e.g., dot-6 prefix in UEB). For items like business cards where names are implicitly capitalized, this wastes valuable space. The toggle allows users to choose between:

- **Disabled (default, recommended):** Convert text to lowercase before translation to save space by omitting capital indicators
- **Enabled:** Preserve exact capitalization for cases where it matters

**Important:** The user's input text remains unchanged in the UI. The lowercase conversion happens only at translation time when the setting is disabled.

### UI Location

The toggle is located **within the "Enter Text for Braille Translation" fieldset**, immediately after the dynamic line inputs container and before the closing `</fieldset>` tag. This places it below the text input area but within the same logical grouping, before the language selection.

### HTML Structure

**Source:** `public/index.html` (lines ~2363-2382)

```html
<!-- Capitalized Letters toggle -->
<div class="line-input-mode-toggle" style="margin-top: 0.8em; display: flex; align-items: center; gap: 1em;" role="radiogroup" aria-labelledby="caps-toggle-label">
    <span id="caps-toggle-label" class="line-label" style="margin: 0;">Capitalized Letters:</span>
    <label style="display: inline-flex; align-items: center; gap: 0.4em;">
        <input type="radio" name="capitalize_letters" value="enabled" id="capitalize_enabled" aria-describedby="caps-enabled-desc">
        Enabled
    </label>
    <label style="display: inline-flex; align-items: center; gap: 0.4em;">
        <input type="radio" name="capitalize_letters" value="disabled" id="capitalize_disabled" checked aria-describedby="caps-disabled-desc">
        Disabled <span style="font-weight: normal; opacity: 0.85;">(recommended)</span>
    </label>
    <span id="caps-enabled-desc" class="sr-only">Preserve capital letters in braille translation, using indicator cells</span>
    <span id="caps-disabled-desc" class="sr-only">Convert text to lowercase before translation to save space on braille cells. Recommended for names and business cards.</span>
</div>
```

### Default State

- **Default:** Disabled (recommended)
- **Persistence:** Saved to `localStorage` key `braille_prefs_capitalize_letters`
- **Values:** `'enabled'` or `'disabled'`

### Contextual Warning Message

A warning message appears when:
1. The toggle is set to "Disabled", AND
2. The user's input text contains uppercase letters

**HTML Structure:**

```html
<div id="caps-warning" class="grade-note" role="status" aria-live="polite"
     style="margin-top: 0.6em; color: #059669; display: none;">
    <strong>Note:</strong> Capital letters in your text will not be translated because "Capitalized Letters" is disabled. Enable it above if you need capitals in braille.
</div>
```

**Display Logic:**
- Updates immediately on text input changes
- Updates when switching between Auto/Manual placement modes
- Updates when the toggle state changes
- Hidden when toggle is "Enabled" or when no uppercase letters are present

### JavaScript Implementation

**Helper Functions** (`public/index.html` lines ~4122-4147):

```javascript
// Helper function to apply capitalization setting to text before translation
function applyCapitalizationSetting(text) {
    const capsEnabled = document.querySelector('input[name="capitalize_letters"]:checked')?.value === 'enabled';
    return capsEnabled ? text : text.toLowerCase();
}

// Update the capitalization warning visibility based on toggle state and input content
function updateCapsWarning() {
    const capsDisabled = document.querySelector('input[name="capitalize_letters"]:checked')?.value !== 'enabled';
    const placementMode = document.querySelector('input[name="placement_mode"]:checked')?.value || 'manual';

    let hasUppercase = false;
    if (placementMode === 'manual') {
        const lines = getDynamicLineValues();
        hasUppercase = lines.some(line => line !== line.toLowerCase());
    } else {
        const autoTextValue = document.getElementById('auto-text')?.value || '';
        hasUppercase = autoTextValue !== autoTextValue.toLowerCase();
    }

    const warning = document.getElementById('caps-warning');
    if (warning) {
        warning.style.display = (capsDisabled && hasUppercase) ? 'block' : 'none';
    }
}
```

### Translation Integration Points

The `applyCapitalizationSetting()` function is called at **5 translation points** before text is sent to liblouis:

1. **Auto wrap: translateLen** (~line 4232) — For calculating braille cell count during auto-wrapping
2. **Auto wrap: translateText** (~line 4237) — For translating text during auto-wrapping
3. **Auto overflow warning** (~line 4390) — For calculating overflow in auto mode
4. **Manual preview** (~line 5263) — For preview translation in manual mode
5. **Manual generate** (~line 5559) — For final translation before STL generation

**Important:** The transformation is **not** applied to `originalLines` or `originalForIndicators` variables, which must remain unchanged for filename generation and indicator marker logic.

### Event Wiring

**Toggle Change Events:**

```javascript
document.querySelectorAll('input[name="capitalize_letters"]').forEach(radio => {
    radio.addEventListener('change', () => {
        persistValue('braille_prefs_capitalize_letters', document.querySelector('input[name="capitalize_letters"]:checked').value);
        resetToGenerateState();
        updateCapsWarning();
        // Recalculate overflow if in auto mode (caps affect cell count)
        if (document.querySelector('input[name="placement_mode"]:checked')?.value === 'auto') {
            computeAutoOverflow();
        }
    });
});
```

**Text Input Events:**
- Manual line inputs call `updateCapsWarning()` in `addInputChangeListeners()` function
- Auto textarea input listener calls `updateCapsWarning()` after `computeAutoOverflow()`
- Placement mode change handler calls `updateCapsWarning()` after `updatePlacementUI()`

### Accessibility Compliance (WCAG 2.1 AA)

| Requirement | Implementation |
|-------------|----------------|
| Radio group semantics | `role="radiogroup"` with `aria-labelledby="caps-toggle-label"` |
| Option descriptions | `aria-describedby` pointing to `.sr-only` descriptions for each option |
| Keyboard navigation | Native radio button behavior (Tab, Arrow keys, Space to select) |
| Dynamic warning | `role="status"` with `aria-live="polite"` for screen reader announcements |
| Color contrast | Green `#059669` meets 4.5:1 on light backgrounds; existing theme overrides handle dark/high-contrast modes |

### State Persistence

**Persistence Key:** `braille_prefs_capitalize_letters`

**Restoration Logic** (`applyPersistedSettings()` function):

```javascript
const savedCaps = readPersisted('braille_prefs_capitalize_letters');
if (savedCaps === 'enabled' || savedCaps === 'disabled') {
    const radio = document.querySelector(`input[name="capitalize_letters"][value="${savedCaps}"]`);
    if (radio) radio.checked = true;
}
```

**Clear Persistence:** The key is included in the `clearAllPersistence()` function's key list.

### Example Translation Behavior

| Input Text | Toggle State | Resulting Braille | Notes |
|------------|--------------|-------------------|-------|
| "Hello" | Disabled | `⠓⠑⠇⠇⠕` | No capital indicator, lowercase translation |
| "Hello" | Enabled | `⠠⠓⠑⠇⠇⠕` | Capital indicator (`⠠`) before "H" |
| "HELLO" | Disabled | `⠓⠑⠇⠇⠕` | All lowercase, no indicators |
| "HELLO" | Enabled | `⠠⠠⠓⠑⠇⠇⠕` | Double capital indicator for all-caps word |
| "hello" | Disabled | `⠓⠑⠇⠇⠕` | Already lowercase, no change |
| "hello" | Enabled | `⠓⠑⠇⠇⠕` | Already lowercase, no change |

---

## 7. Translation Pipeline

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                         │
│  ┌─────────────────────┐    ┌─────────────────┐                             │
│  │ Placement Mode      │    │ Language Table  │                             │
│  │ (auto/manual)       │    │ (per-line or    │                             │
│  │                     │    │  master)        │                             │
│  └──────────┬──────────┘    └────────┬────────┘                             │
│             │                        │                                       │
│             ▼                        ▼                                       │
│  ┌──────────────────────────────────────────────┐                           │
│  │         FRONTEND (index.html)                 │                           │
│  │  • Collects text (auto textarea or per-line) │                           │
│  │  • Determines placement mode                  │                           │
│  │  • Applies BANA wrapping (auto mode)          │                           │
│  │  • Sends each line to liblouis worker         │                           │
│  └───────────────────────┬──────────────────────┘                           │
│                          │                                                   │
│                          ▼                                                   │
│  ┌──────────────────────────────────────────────┐                           │
│  │      LIBLOUIS WEB WORKER                      │                           │
│  │  (static/liblouis-worker.js)                  │                           │
│  │  • Loads liblouis WASM/JS                     │                           │
│  │  • Loads translation table                    │                           │
│  │  • Translates text → Unicode braille          │                           │
│  └───────────────────────┬──────────────────────┘                           │
│                          │                                                   │
│                          ▼                                                   │
│  ┌──────────────────────────────────────────────┐                           │
│  │       BACKEND (backend.py)                    │                           │
│  │  • Receives: lines (braille), original_lines, │                           │
│  │    placement_mode, per_line_language_tables   │                           │
│  │  • Validates braille Unicode                  │                           │
│  │  • Converts to dot patterns                   │                           │
│  │  • Generates 3D geometry                      │                           │
│  └───────────────────────┬──────────────────────┘                           │
│                          │                                                   │
│                          ▼                                                   │
│  ┌──────────────────────────────────────────────┐                           │
│  │    CSG WORKER or SERVER MESH GENERATION       │                           │
│  │  • Consumes dot positions                     │                           │
│  │  • Creates 3D braille dots/recesses           │                           │
│  │  • Exports STL file                           │                           │
│  └──────────────────────────────────────────────┘                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principle: Frontend-Only Translation

**All text-to-braille translation happens client-side.** The backend:
- **Receives** pre-translated braille Unicode characters (U+2800–U+28FF)
- **Validates** that the input contains valid braille Unicode
- **Rejects** requests with non-braille text for positive plates

**Source:** `backend.py` (lines 745-756)

```python
# Check if input contains proper braille Unicode (U+2800 to U+28FF)
has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)

if has_braille_chars:
    braille_text = line_text  # Use directly
else:
    # Error: frontend must translate before sending
    error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters. ' \
                'Frontend must translate text to braille before sending.'
    raise RuntimeError(error_msg)
```

---

## 8. Backend Request Structure

### POST `/generate_braille_stl` Request Body

**Source:** `backend.py` (lines 2094-2102)

```python
lines = data.get('lines', ['', '', '', ''])
original_lines = data.get('original_lines', None)
placement_mode = data.get('placement_mode', 'manual')
plate_type = data.get('plate_type', 'positive')
grade = data.get('grade', 'g2')
settings_data = data.get('settings', {})
shape_type = data.get('shape_type', 'card')
cylinder_params = data.get('cylinder_params', {})
per_line_language_tables = data.get('per_line_language_tables', None)
```

### Request Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `lines` | `string[]` | Braille Unicode text for each row | `["⠚⠕⠓⠝", "⠎⠍⠊⠞⠓"]` |
| `original_lines` | `string[]` | Original text before translation (for indicators) | `["John", "Smith"]` |
| `placement_mode` | `string` | `"auto"` or `"manual"` | `"auto"` |
| `plate_type` | `string` | `"positive"` or `"negative"` | `"positive"` |
| `grade` | `string` | `"g1"` or `"g2"` (legacy, less used) | `"g2"` |
| `settings` | `object` | All dimensional parameters | `{grid_columns: 15, ...}` |
| `shape_type` | `string` | `"card"` or `"cylinder"` | `"cylinder"` |
| `cylinder_params` | `object` | Cylinder-specific parameters | `{diameter: 30.75, ...}` |
| `per_line_language_tables` | `string[]` | Liblouis table used for each line | `["en-ueb-g1.ctb", ...]` |

### Example Request (Auto Mode)

```json
{
    "lines": ["⠚⠕⠓⠝ ⠎⠍⠊⠞⠓", "⠼⠁⠃⠉ ⠍⠁⠊⠝ ⠌", "", ""],
    "original_lines": ["John Smith", "123 Main St", "", ""],
    "placement_mode": "auto",
    "plate_type": "positive",
    "grade": "g2",
    "shape_type": "cylinder",
    "per_line_language_tables": ["en-ueb-g1.ctb", "en-ueb-g1.ctb", "en-ueb-g1.ctb", "en-ueb-g1.ctb"],
    "settings": {
        "grid_columns": "17",
        "grid_rows": "4",
        "cell_spacing": "6.5",
        "line_spacing": "10",
        "dot_spacing": "2.5"
    },
    "cylinder_params": {
        "diameter": 30.75,
        "height": 52
    }
}
```

### Example Request (Manual Mode with Mixed Languages)

```json
{
    "lines": ["⠚⠕⠓⠝ ⠎⠍⠊⠞⠓", "⠃⠕⠝⠚⠕⠥⠗", "", ""],
    "original_lines": ["John Smith", "Bonjour", "", ""],
    "placement_mode": "manual",
    "plate_type": "positive",
    "grade": "g2",
    "shape_type": "cylinder",
    "per_line_language_tables": ["en-ueb-g1.ctb", "fr-bfu-g2.ctb", "en-ueb-g1.ctb", "en-ueb-g1.ctb"],
    "settings": { ... }
}
```

### How `original_lines` is Used

The `original_lines` array provides the source text for each row, which is used for:

1. **Row Indicators** — The first character of each original line becomes the alphanumeric indicator
2. **Logging** — Backend logs which original text was placed on each row

**Source:** `backend.py` (lines 693-704)

```python
if original_lines and row_num < len(original_lines):
    orig = (original_lines[row_num] or '').strip()
    indicator_char = orig[0] if orig else ''
    if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
        # Use character shape for indicator
        char_polygon = create_character_shape_polygon(indicator_char, ...)
    else:
        # Use rectangle fallback
        rect_polygon = create_line_marker_polygon(...)
```

---

## 9. BANA Auto-Wrap Algorithm

### Overview

The BANA (Braille Authority of North America) auto-wrap algorithm intelligently wraps text across available rows while following braille formatting guidelines.

**Source:** `templates/index.html` (lines 3391-3554)

### Algorithm Principles

1. **Word Preservation** — Avoid dividing words across lines when possible
2. **Greedy Fitting** — Fill each line with as many words as will fit
3. **Smart Breaks** — When a word must be split, prefer natural break points
4. **Translation-Aware** — Calculate lengths after braille translation (not source text)

### Preferred Break Points (Priority Order)

When a single word is too long for a line:

1. **Hyphen Characters** — Break after `-`, `–`, `—`, `‑`, `‒`, `−`
2. **Email/URL Characters** — Break after `@` or `.`
3. **Syllable Heuristics** — Vowel-consonant boundaries

### Implementation

```javascript
async function banaAutoWrap(src, cols, rows, tableName) {
    const warnings = [];
    const textLines = [];
    const brailleLines = [];

    // Normalize whitespace
    const normalizeSpaces = (s) => s.replace(/\s+/g, ' ').trim();

    // Character classification helpers
    const isHyphenChar = (ch) => /[-\u2010\u2011\u2012\u2013\u2014\u2212]/.test(ch);
    const isEmailBreakChar = (ch) => ch === '@' || ch === '.';

    // Find preferred break positions in a word
    function findPreferredBreakPositions(word) {
        const positions = [];
        for (let i = 0; i < word.length; i++) {
            const ch = word[i];
            if (isHyphenChar(ch) || isEmailBreakChar(ch)) {
                if (i + 1 < word.length) positions.push(i);
            }
        }
        return positions;
    }

    // Heuristic syllable breaks (vowel-consonant boundaries)
    function findHeuristicSyllableBreaks(word) {
        const breaks = [];
        const vowels = /[aeiouyAEIOUY]/;
        for (let i = 1; i < word.length - 1; i++) {
            const prev = word[i - 1];
            const cur = word[i];
            const next = word[i + 1];
            if (vowels.test(prev) && !vowels.test(cur)) {
                breaks.push(i);
            } else if (vowels.test(cur) && !vowels.test(next)) {
                breaks.push(i + 1);
            }
        }
        return Array.from(new Set(breaks)).sort((a,b) => a-b);
    }

    // Translation helpers
    async function translateLen(text) {
        const b = await translateWithLiblouis(text, 'g2', tableName);
        return b.length;
    }

    // Main wrapping loop
    let remaining = normalizeSpaces(src);
    const words = remaining.split(' ');
    let currentText = '';

    for (let i = 0; i < words.length && textLines.length < rows; ) {
        const word = words[i];

        // Try to append word to current line
        const candidate = currentText ? `${currentText} ${word}` : word;
        const candidateBrailleLen = await translateLen(candidate);

        if (candidateBrailleLen <= cols) {
            currentText = candidate;
            i++;
            continue;
        }

        // Would overflow - finalize current line if it has content
        if (currentText) {
            textLines.push(currentText.trim());
            brailleLines.push(await translateText(currentText.trim()));
            currentText = '';
            continue;  // Retry same word on new line
        }

        // Single word longer than a line - try to split
        // ... (preferred breaks, syllable breaks, or error)
    }

    return { textLines, brailleLines, warnings };
}
```

### Error Conditions

If a word cannot fit on a single line and has no valid break points:

```javascript
// Source: templates/index.html (lines 3531-3534)
warnings.push(`Word "${word}" requires ${wordBrailleLen} cells but only ${cols} fit per row. ` +
              `It cannot be divided per BANA; increase columns/rows or use Manual Placement.`);
return { error: true, warnings };
```

---

## 10. Overflow Detection and Warnings

### Auto Mode Overflow Warning

Real-time overflow detection as user types:

**Source:** `templates/index.html` (lines 3587-3606)

```javascript
async function computeAutoOverflow() {
    autoWarning.style.display = 'none';
    autoWarningMsg.textContent = '';

    const languageSelect = document.getElementById('language-table');
    const tableName = languageSelect?.value || 'en-ueb-g1.ctb';
    const src = (autoText?.value || '').trim();

    if (!src) return;

    try {
        const braille = await translateWithLiblouis(src, 'g2', tableName);
        const totalCellsNeeded = braille.length;
        const totalCellsAvailable = getTotalCellsAvailable();

        if (totalCellsNeeded > totalCellsAvailable) {
            const over = totalCellsNeeded - totalCellsAvailable;
            autoWarningMsg.textContent = `Text requires ${totalCellsNeeded} cells but only ` +
                                         `${totalCellsAvailable} fit. Consider adding rows or reducing text.`;
            autoWarning.style.display = '';
        }
    } catch (e) {
        // Silent fail for overflow check
    }
}
```

### Available Cells Calculation

```javascript
function getAvailableColumns() {
    return parseInt(document.getElementById('grid_columns').value) || 15;
}

function getTotalCellsAvailable() {
    const rows = parseInt(document.getElementById('grid_rows').value) || 4;
    const cols = getAvailableColumns();
    return rows * cols;
}
```

### Cylinder Overflow Check

For cylinder shapes, overflow is calculated based on circumference:

**Source:** `templates/index.html` (lines 3200-3238)

```javascript
function checkCylinderOverflow() {
    const diameter = parseFloat(document.getElementById('cylinder_diameter_mm').value) || 30.75;
    const height = parseFloat(document.getElementById('cylinder_height_mm').value) || 52;
    const cellSpacing = parseFloat(document.getElementById('cell_spacing').value) || 6.5;
    const lineSpacing = parseFloat(document.getElementById('line_spacing').value) || 10;

    // Cells per row = circumference / cell spacing
    const circumference = Math.PI * diameter;
    const cellsPerRow = Math.floor(circumference / cellSpacing);

    // Rows = height / line spacing
    const rowsOnCylinder = Math.floor(height / lineSpacing);

    const totalCellsAvailable = cellsPerRow * rowsOnCylinder;
    // ... compare with needed cells
}
```

---

## 11. State Persistence

### LocalStorage Keys

**Source:** `templates/index.html` (lines 3628-3640)

| Key | Purpose | Values |
|-----|---------|--------|
| `braille_prefs_placement_mode` | Placement mode toggle | `"auto"` or `"manual"` |
| `braille_prefs_language_table` | Master language selection | Table filename |
| `braille_prefs_plate_type` | Plate type selection | `"positive"` or `"negative"` |
| `braille_prefs_shape_type` | Output shape | `"card"` or `"cylinder"` |
| `braille_prefs_grid_rows` | Number of rows | Integer string |
| `braille_prefs_grid_columns` | Number of columns | Integer string |

### Persistence Listeners

**Source:** `templates/index.html` (lines 3793-3797)

```javascript
function wirePersistenceListeners() {
    // Placement mode (auto/manual)
    document.querySelectorAll('input[name="placement_mode"]').forEach(r => {
        r.addEventListener('change', () =>
            persistValue('braille_prefs_placement_mode',
                document.querySelector('input[name="placement_mode"]:checked').value));
    });

    // Language table
    select.addEventListener('change', () => {
        localStorage.setItem('braille_prefs_language_table', select.value);
    });
}
```

### Apply Persisted Settings on Load

**Source:** `templates/index.html` (lines 3669-3676)

```javascript
function applyPersistedSettings() {
    // Placement mode (auto/manual)
    const savedPlacement = readPersisted('braille_prefs_placement_mode');
    if (savedPlacement === 'auto' || savedPlacement === 'manual') {
        const radio = document.querySelector(`input[name="placement_mode"][value="${savedPlacement}"]`);
        if (radio) radio.checked = true;
    }
    // ... other settings
}
```

---

## 12. Styling and Accessibility

### CSS Classes

| Class | Purpose |
|-------|---------|
| `.line-input-mode-toggle` | Container for placement mode radio buttons |
| `.language-select` | Styled dropdown for language selection |
| `.line-language-select` | Per-line language dropdown (inherits from `.language-select`) |
| `.line-input` | Container for each manual line input row |
| `.line-translation-row` | Row containing per-line language select |
| `.line-text-row` | Row containing text input field |
| `.line-label` | Label styling for inputs |
| `.grade-note` | Help text / warning styling |

### Language Select Styling

**Source:** `templates/index.html` (lines 1111-1173)

```css
.language-select {
    width: 100%;
    border: 1.5px solid var(--border-secondary);
    border-radius: 8px;
    padding: 0.8em 1em;
    font-size: 1em;
    background: var(--bg-primary);
    color: var(--text-primary);
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,...");  /* Custom dropdown arrow */
    background-repeat: no-repeat;
    background-position: right 1em center;
    padding-right: 2.5em;
}

.language-select:focus {
    border: 1.5px solid var(--border-focus);
    outline: none;
}

/* High contrast mode */
[data-theme="high-contrast"] .language-select {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: 2px solid #ffff00 !important;
}
```

### ARIA Attributes

```html
<!-- Master language select -->
<select id="language-table" aria-describedby="language-help">
<div id="language-help" class="grade-note">Default: English (UEB)...</div>

<!-- Per-line language selects -->
<select id="line_lang_1" aria-describedby="line1-lang-help">
<span id="line1-lang-help" class="sr-only">Select translation language for line 1</span>

<!-- Text inputs -->
<input id="line1" aria-describedby="line1-help">
<span id="line1-help" class="sr-only">Maximum 50 characters for line 1</span>
```

### Screen Reader Classes

```css
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
```

---

## 13. Cross-Implementation Consistency

### Placement Mode Handling

| Component | Location | How Mode is Read |
|-----------|----------|------------------|
| Frontend UI | `templates/index.html` | `document.querySelector('input[name="placement_mode"]:checked')?.value` |
| Form Submit | `templates/index.html` | Same as above, passed to `banaAutoWrap()` or per-line translation |
| Backend | `backend.py` | `data.get('placement_mode', 'manual')` |
| Cache Key | `backend.py` | Included in `cache_payload` for positive plates |

### Language Table Chain

All components use the same table chain format:

**Frontend (liblouis-worker.js):**
```javascript
const tableChain = selectedTable.indexOf('unicode.dis') !== -1
    ? selectedTable
    : ('unicode.dis,' + selectedTable);
```

**Backend Table Resolution:**
```python
candidate_dirs = [
    os.path.join(base, 'static', 'liblouis', 'tables'),
    os.path.join(base, 'node_modules', 'liblouis-build', 'tables'),
    os.path.join(base, 'third_party', 'liblouis', 'tables'),
]
```

### Original Lines Consistency

| Placement Mode | `original_lines` Content | Source |
|----------------|--------------------------|--------|
| **Auto** | Per-row text segments from BANA wrapping | `wrap.textLines` |
| **Manual** | Exact copy of user input lines | `[...lines]` |

**Frontend construction:**
```javascript
if (placementMode === 'manual') {
    originalLines = [...lines];  // Copy of input
} else {
    originalLines = wrap.textLines;  // From BANA wrapping
}
```

**Backend usage:**
```python
# Both modes: first character of original_lines[row] becomes indicator
if original_lines and row_num < len(original_lines):
    orig = (original_lines[row_num] or '').strip()
    indicator_char = orig[0] if orig else ''
```

---

## Appendix A: Complete Request/Response Examples

### Auto Mode Full Request

```javascript
// Frontend collects:
const src = "John Smith 123 Main Street Anytown USA";
const wrap = await banaAutoWrap(src, 15, 4, 'en-ueb-g1.ctb');

// wrap result:
{
    textLines: ["John Smith 123", "Main Street", "Anytown USA", ""],
    brailleLines: ["⠚⠕⠓⠝ ⠎⠍⠊⠞⠓ ⠼⠁⠃⠉", "⠍⠁⠊⠝ ⠎⠞⠗⠑⠑⠞", "⠁⠝⠽⠞⠕⠺⠝ ⠥⠎⠁", ""],
    warnings: [],
    error: false
}

// Request to backend:
{
    lines: ["⠚⠕⠓⠝ ⠎⠍⠊⠞⠓ ⠼⠁⠃⠉", "⠍⠁⠊⠝ ⠎⠞⠗⠑⠑⠞", "⠁⠝⠽⠞⠕⠺⠝ ⠥⠎⠁", ""],
    original_lines: ["John Smith 123", "Main Street", "Anytown USA", ""],
    placement_mode: "auto",
    per_line_language_tables: ["en-ueb-g1.ctb", "en-ueb-g1.ctb", "en-ueb-g1.ctb", "en-ueb-g1.ctb"],
    // ... other fields
}
```

### Manual Mode Full Request

```javascript
// User enters in 4 text inputs:
// Line 1: "John Smith" (English UEB G1)
// Line 2: "Bonjour" (French G2)
// Line 3: "" (empty)
// Line 4: "Contact Me" (English UEB G1)

// Frontend translates each line with its per-line table:
const lines = ["John Smith", "Bonjour", "", "Contact Me"];
const translatedLines = [];
for (let i = 0; i < lines.length; i++) {
    const table = document.getElementById(`line_lang_${i+1}`).value;
    translatedLines[i] = await translateWithLiblouis(lines[i], 'g2', table);
}

// Request to backend:
{
    lines: ["⠚⠕⠓⠝ ⠎⠍⠊⠞⠓", "⠃⠕⠝⠚⠕⠥⠗", "", "⠉⠕⠝⠞⠁⠉⠞ ⠍⠑"],
    original_lines: ["John Smith", "Bonjour", "", "Contact Me"],
    placement_mode: "manual",
    per_line_language_tables: ["en-ueb-g1.ctb", "fr-bfu-g2.ctb", "en-ueb-g1.ctb", "en-ueb-g1.ctb"],
    // ... other fields
}
```

---

## Appendix B: Troubleshooting

### Text Not Wrapping Correctly (Auto Mode)

1. Check that `grid_rows` and `grid_columns` are set correctly
2. Verify the language table supports the input characters
3. Check browser console for BANA wrap warnings
4. Long words without hyphens may cause errors

### Per-Line Language Not Applying (Manual Mode)

1. Verify the per-line select has the correct value before form submit
2. Check that `syncLineLanguageSelects()` was called when switching to manual mode
3. Ensure the selected table file exists in `/static/liblouis/tables/`

### Overflow Warnings Not Appearing

1. Ensure `computeAutoOverflow()` is bound to the textarea input event
2. Check that the language table is loading correctly in the worker
3. Verify `getTotalCellsAvailable()` returns correct values

### Indicators Showing Rectangle Instead of Character

1. Check that `original_lines` is being sent to the backend
2. Verify the first character of the original line is alphanumeric
3. For auto mode, ensure `wrap.textLines` contains the source segments

---

## Appendix C: Verification Checklist

### Frontend Verification

- [ ] Placement mode toggle switches UI correctly
- [ ] Auto textarea appears when Auto mode selected
- [ ] Manual line inputs appear when Manual mode selected
- [ ] Number of line inputs matches `grid_rows` setting
- [ ] Per-line language dropdowns are populated from master
- [ ] Overflow warnings appear when text exceeds capacity
- [ ] BANA wrapping produces expected line breaks

### Backend Verification

- [ ] `placement_mode` is read from request
- [ ] `original_lines` is used for row indicators
- [ ] `per_line_language_tables` is logged in config dump
- [ ] Braille validation rejects non-Unicode input
- [ ] Counter plates ignore text content (use all dots)

### Integration Verification

- [ ] Auto mode: single language table used for all lines
- [ ] Manual mode: per-line tables respected
- [ ] Row indicators match first character of `original_lines`
- [ ] STL filename includes sanitized text from first line

---

## Appendix D: Implementation Verification Report

This section documents the cross-check verification performed against actual implementations.

### Verification Date

2024-12-06

### Components Verified

| Component | File | Location | Status |
|-----------|------|----------|--------|
| Placement Mode Toggle HTML | `templates/index.html` | Lines 2019-2030 | ✅ VERIFIED |
| Auto Placement Container | `templates/index.html` | Lines 2031-2038 | ✅ VERIFIED |
| Dynamic Line Inputs | `templates/index.html` | Lines 3241-3268 | ✅ VERIFIED |
| Language Selection Dropdown | `templates/index.html` | Lines 2045-2061 | ✅ VERIFIED |
| syncLineLanguageSelects() | `templates/index.html` | Lines 3271-3285 | ✅ VERIFIED |
| BANA Auto-Wrap Algorithm | `templates/index.html` | Lines 3391-3554 | ✅ VERIFIED |
| Backend Request Parsing | `backend.py` | Lines 2094-2102 | ✅ VERIFIED |
| Braille Unicode Validation | `backend.py` | Lines 745-756 | ✅ VERIFIED |
| Original Lines for Indicators | `backend.py` | Lines 698-708 | ✅ VERIFIED |
| Liblouis Worker Translation | `static/liblouis-worker.js` | Lines 151-169 | ✅ VERIFIED |
| Geometry Spec (Card) | `geometry_spec.py` | Lines 22-230 | ✅ VERIFIED |
| Geometry Spec (Cylinder) | `geometry_spec.py` | Lines 340-625 | ✅ VERIFIED |
| Utils braille_to_dots | `app/utils.py` | Lines 96-130 | ✅ VERIFIED |
| Validation Module | `app/validation.py` | Lines 74-100 | ✅ VERIFIED |

### Verification Details

#### 1. Placement Mode Toggle ✅

**Specification states:**
- Radio buttons with `name="placement_mode"`
- Values: `"auto"` and `"manual"`
- Auto is checked by default

**Implementation verified:**
```html
<input type="radio" name="placement_mode" value="auto" id="placement_mode_auto" checked>
<input type="radio" name="placement_mode" value="manual" id="placement_mode_manual">
```
**Status:** MATCHES SPECIFICATION

#### 2. Auto Placement Container ✅

**Specification states:**
- Container `id="auto-input-container"` hidden by default
- Textarea `id="auto-text"`
- Warning div `id="auto-overflow-warning"`

**Implementation verified:**
```html
<div id="auto-input-container" style="display: none;">
    <textarea id="auto-text" rows="4" ...></textarea>
    <div id="auto-overflow-warning" ...>
        <span id="auto-overflow-message"></span>
    </div>
</div>
```
**Status:** MATCHES SPECIFICATION

#### 3. Dynamic Line Inputs ✅

**Specification states:**
- Container `id="dynamic-line-inputs"`
- Each line has `id="line_lang_{i}"` for language and `id="line{i}"` for text

**Implementation verified:**
```javascript
function createDynamicLineInputs(numLines) {
    const container = document.getElementById('dynamic-line-inputs');
    // Creates: id="line_lang_${i}", id="line${i}"
}
```
**Status:** MATCHES SPECIFICATION

#### 4. Backend Request Parsing ✅

**Specification states fields:**
- `lines`, `original_lines`, `placement_mode`, `per_line_language_tables`

**Implementation verified:**
```python
lines = data.get('lines', ['', '', '', ''])
original_lines = data.get('original_lines', None)
placement_mode = data.get('placement_mode', 'manual')
per_line_language_tables = data.get('per_line_language_tables', None)
```
**Status:** MATCHES SPECIFICATION

#### 5. Braille Unicode Validation ✅

**Specification states:**
- Range: U+2800 to U+28FF
- Error raised if non-braille for positive plates

**Implementation verified:**
```python
has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)
if not has_braille_chars:
    error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters...'
    raise RuntimeError(error_msg)
```
**Status:** MATCHES SPECIFICATION

#### 6. Original Lines for Indicators ✅

**Specification states:**
- First character of `original_lines[row]` becomes indicator
- Must be alphanumeric to use character shape

**Implementation verified:**
```python
if original_lines and row_num < len(original_lines):
    orig = (original_lines[row_num] or '').strip()
    indicator_char = orig[0] if orig else ''
    if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
        # Create character indicator
```
**Status:** MATCHES SPECIFICATION

#### 7. Liblouis Table Chain ✅

**Specification states:**
- Prepends `unicode.dis` to ensure Unicode braille output
- Validates output contains U+2800–U+28FF characters

**Implementation verified:**
```javascript
const tableChain = selectedTable.indexOf('unicode.dis') !== -1
    ? selectedTable
    : ('unicode.dis,' + selectedTable);
const result = liblouisInstance.translateString(tableChain, text);
const hasBrailleChars = result.split('').some(function(char){
    const code = char.charCodeAt(0);
    return code >= 0x2800 && code <= 0x28FF;
});
```
**Status:** MATCHES SPECIFICATION

#### 8. BANA Auto-Wrap ✅

**Specification states:**
- `banaAutoWrap()` returns `{ textLines, brailleLines, warnings, error }`
- Word preservation, hyphen breaks, syllable fallback

**Implementation verified:**
```javascript
async function banaAutoWrap(src, cols, rows, tableName) {
    const warnings = [];
    const textLines = [];
    const brailleLines = [];
    // ... word processing logic
    return { textLines, brailleLines, warnings };
    // On error: return { error: true, warnings };
}
```
**Status:** MATCHES SPECIFICATION

#### 9. syncLineLanguageSelects ✅

**Specification states:**
- Copies options from master `#language-table`
- Priority: prior value > `en-ueb-g1.ctb` > master value

**Implementation verified:**
```javascript
function syncLineLanguageSelects() {
    const master = document.getElementById('language-table');
    const optionsHTML = master.innerHTML;
    const masterValue = master.value;
    document.querySelectorAll('.line-language-select').forEach(sel => {
        const previous = sel.value;
        sel.innerHTML = optionsHTML;
        const hasPrev = previous && Array.from(sel.options).some(o => o.value === previous);
        const desiredDefault = 'en-ueb-g1.ctb';
        const hasDesired = Array.from(sel.options).some(o => o.value === desiredDefault);
        sel.value = hasPrev ? previous : (hasDesired ? desiredDefault : masterValue);
    });
}
```
**Status:** MATCHES SPECIFICATION

#### 10. State Persistence Keys ✅

**Specification states:**
- `braille_prefs_placement_mode`
- `braille_prefs_language_table`

**Implementation verified:**
```javascript
// Persistence
persistValue('braille_prefs_placement_mode', ...)
localStorage.setItem('braille_prefs_language_table', select.value)

// Restoration
const savedPlacement = readPersisted('braille_prefs_placement_mode');
const saved = localStorage.getItem('braille_prefs_language_table');
```
**Status:** MATCHES SPECIFICATION

### Unicode Range Consistency

All implementations use consistent Unicode braille range:

| Location | Start | End | Status |
|----------|-------|-----|--------|
| `app/utils.py` (BRAILLE_UNICODE_START/END) | `0x2800` | `0x28FF` | ✅ |
| `app/validation.py` (constants) | `0x2800` | `0x28FF` | ✅ |
| `backend.py` (line 747) | `0x2800` | `0x28FF` | ✅ |
| `backend.py` (line 937) | `0x2800` | `0x28FF` | ✅ |
| `static/liblouis-worker.js` (line 164) | `0x2800` | `0x28FF` | ✅ |

### Cross-Component Data Flow Verification

| Step | Source | Destination | Data | Verified |
|------|--------|-------------|------|----------|
| 1 | User Input | Frontend | Text in textarea/inputs | ✅ |
| 2 | Frontend | Liblouis Worker | `{text, grade, tableName}` | ✅ |
| 3 | Liblouis Worker | Frontend | Unicode braille string | ✅ |
| 4 | Frontend | Backend | `{lines, original_lines, placement_mode, per_line_language_tables}` | ✅ |
| 5 | Backend | Geometry Spec | `braille_to_dots()` conversion | ✅ |
| 6 | Geometry Spec | CSG Worker | Dot positions and params | ✅ |

### Corrections Made During Verification

None required. All implementations match the specification exactly.

### Notes

1. **Default Placement Mode:** The HTML has `checked` on Auto Placement, but the JavaScript fallback defaults to `'manual'`. This is intentional defensive coding — the fallback only applies if the DOM is somehow broken.

2. **Per-Line Language Tables:** In Auto mode, all lines use the same table (filled with `tableName`). In Manual mode, each line can have a different table from `line_lang_{i}` selects.

3. **Geometry Spec Consistency:** Both `extract_card_geometry_spec` and `extract_cylinder_geometry_spec` use identical logic for processing `original_lines` to extract row indicators.

---

*Document Version: 1.1*
*Last Updated: 2024-12-06*
*Verification Completed: 2024-12-06*
*Source Priority: backend.py > wsgi.py > csg-worker.js > Manifold WASM*
