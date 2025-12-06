# Braille Translation Preview Specifications

## Document Purpose

This document provides **comprehensive, in-depth specifications** for the Braille Translation Preview feature in the application. It serves as an authoritative reference for future development by documenting:

1. **UI Controls** — The preview button, display container, and their behaviors
2. **Translation Pipeline** — How text flows from input through liblouis to Unicode braille
3. **Computer Shorthand Conversion** — How braille Unicode is decoded for readability
4. **Placement Modes** — Manual line-by-line vs. BANA-aware auto-wrapping
5. **Error Handling** — Graceful degradation when translation fails
6. **Backend Integration** — Language table discovery and braille validation

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source (braille validation, table scanning)
2. `wsgi.py` — Entry point configuration
3. `static/workers/csg-worker.js` — Client-side geometry (consumes translated braille)
4. `static/liblouis-worker.js` — Translation web worker

---

## Table of Contents

1. [UI Layout: Braille Translation Preview](#1-ui-layout-braille-translation-preview)
2. [Translation Architecture Overview](#2-translation-architecture-overview)
3. [Liblouis Web Worker Integration](#3-liblouis-web-worker-integration)
4. [Computer Shorthand Conversion](#4-computer-shorthand-conversion)
5. [Manual Placement Mode Preview](#5-manual-placement-mode-preview)
6. [Auto Placement Mode Preview (BANA Wrapping)](#6-auto-placement-mode-preview-bana-wrapping)
7. [Language Table System](#7-language-table-system)
8. [Backend Braille Validation](#8-backend-braille-validation)
9. [Braille Unicode Character Handling](#9-braille-unicode-character-handling)
10. [Error States and Fallbacks](#10-error-states-and-fallbacks)
11. [Styling and Accessibility](#11-styling-and-accessibility)
12. [Cross-Implementation Consistency](#12-cross-implementation-consistency)

---

## 1. UI Layout: Braille Translation Preview

### Location in Application

The Braille Translation Preview controls are located under:

```
Expert Mode → Preview Braille Translation (button at top of Expert Mode)
```

The preview is **hidden by default** and appears only after clicking the preview button.

### Visual Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  ▼ Expert Mode                                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─ Any changes made here will affect both plates. ────────────┐ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│        [ Preview Braille Translation ]   ← Button (centered)     │
│                                                                   │
│  ┌─ Braille Translation Preview: ──────────────────────────────┐ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ Line 1: "Hello" → "⠓⠑⠇⠇⠕"                           │   │ │
│  │  │ Computer shorthand: "h e l l o"                       │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ Line 2: "World" → "⠺⠕⠗⠇⠙"                           │   │ │
│  │  │ Computer shorthand: "w o r l d"                       │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ▼ Shape Selection                                               │
│  ▼ Surface Dimensions                                            │
│  ... (other submenus)                                            │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### HTML Structure

```html
<!-- Preview button -->
<div style="margin-top: 1em; margin-bottom: 0.5em; text-align: center;">
    <button type="button" id="preview-braille-btn">Preview Braille Translation</button>
</div>

<!-- Preview container (initially hidden) -->
<div id="braille-preview" class="braille-preview" style="display: none;"
     role="region" aria-label="Braille translation preview">
    <h3 class="preview-heading">Braille Translation Preview:</h3>
    <div id="preview-content"></div>
</div>
```

### CSS Styling Classes

| Class | Purpose | Description |
|-------|---------|-------------|
| `.braille-preview` | Container | Holds all preview content with padding and border |
| `.preview-heading` | Title | "Braille Translation Preview:" heading |
| `.preview-line-success` | Success row | Neutral background for successful translations |
| `.preview-line-error` | Error row | Red-tinted background for failed translations |
| `.preview-subline` | Secondary info | Computer shorthand display (90% font size, 85% opacity) |

---

## 2. Translation Architecture Overview

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                         │
│  ┌─────────────┐    ┌─────────────────┐                                     │
│  │ Line 1 Text │    │ Language Table  │                                     │
│  │ Line 2 Text │    │ (en-ueb-g2.ctb) │                                     │
│  │ Line 3 Text │    └────────┬────────┘                                     │
│  │ Line 4 Text │             │                                              │
│  └──────┬──────┘             │                                              │
│         │                    │                                              │
│         ▼                    ▼                                              │
│  ┌──────────────────────────────────────┐                                   │
│  │         FRONTEND (index.html)         │                                   │
│  │  • Collects text from input fields    │                                   │
│  │  • Determines placement mode          │                                   │
│  │  • Sends to liblouis web worker       │                                   │
│  └──────────────────┬───────────────────┘                                   │
│                     │                                                        │
│                     ▼                                                        │
│  ┌──────────────────────────────────────┐                                   │
│  │      LIBLOUIS WEB WORKER              │                                   │
│  │  (static/liblouis-worker.js)          │                                   │
│  │  • Loads liblouis WASM/JS             │                                   │
│  │  • Loads translation tables           │                                   │
│  │  • Translates text → Unicode braille  │                                   │
│  └──────────────────┬───────────────────┘                                   │
│                     │                                                        │
│                     ▼                                                        │
│  ┌──────────────────────────────────────┐                                   │
│  │       PREVIEW DISPLAY                 │                                   │
│  │  • Shows original text                │                                   │
│  │  • Shows braille Unicode              │                                   │
│  │  • Shows computer shorthand           │                                   │
│  └──────────────────────────────────────┘                                   │
│                                                                              │
│         │ (On Generate STL)                                                  │
│         ▼                                                                    │
│  ┌──────────────────────────────────────┐                                   │
│  │        BACKEND (backend.py)           │                                   │
│  │  • Validates braille Unicode          │                                   │
│  │  • Converts to dot patterns           │                                   │
│  │  • Generates 3D geometry              │                                   │
│  └──────────────────────────────────────┘                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Frontend Translation** — All text-to-braille translation happens client-side using liblouis web worker
2. **Backend Validation** — Backend receives pre-translated braille Unicode and validates it
3. **Unicode Standard** — All braille is represented as Unicode characters (U+2800 to U+28FF)
4. **Graceful Degradation** — Preview works even if backend is unavailable

---

## 3. Liblouis Web Worker Integration

### Worker Initialization

**Source:** `static/liblouis-worker.js`

```javascript
// Web Worker for liblouis translation
// Uses enableOnDemandTableLoading which only works in web workers

let liblouisInstance = null;
let liblouisReady = false;

// Import liblouis scripts
importScripts('/static/liblouis/build-no-tables-utf16.js');
importScripts('/static/liblouis/easy-api.js');
```

### Initialization Sequence

```
1. Load build-no-tables-utf16.js (liblouis WASM/JS core)
2. Load easy-api.js (JavaScript API wrapper)
3. Create LiblouisEasyApi instance
4. Enable on-demand table loading from /static/liblouis/tables/
5. Preload core tables (unicode.dis, en-ueb-g1.ctb, en-ueb-g2.ctb)
6. Run test translation to verify functionality
```

### Worker Message Protocol

**Request Format:**

```javascript
{
    id: Number,           // Unique message ID for response matching
    type: 'translate',    // Message type
    data: {
        text: String,     // Original text to translate
        grade: String,    // 'g1' or 'g2' (only used if tableName is null)
        tableName: String // Liblouis table file (e.g., 'en-ueb-g2.ctb')
    }
}
```

**Response Format:**

```javascript
{
    id: Number,           // Matches request ID
    type: 'translate',    // Message type
    result: {
        success: Boolean,
        translation: String,  // Unicode braille output (on success)
        error: String         // Error message (on failure)
    }
}
```

### Translation Function

**Source:** `static/liblouis-worker.js` (lines 135-181)

```javascript
case 'translate':
    if (!liblouisReady || !liblouisInstance) {
        throw new Error('Liblouis not initialized');
    }

    const { text, grade, tableName } = data;

    // Use provided table or default based on grade
    let selectedTable = tableName || (grade === 'g2' ? 'en-ueb-g2.ctb' : 'en-ueb-g1.ctb');

    // Ensure unicode braille output by prepending unicode.dis
    const tableChain = selectedTable.indexOf('unicode.dis') !== -1
        ? selectedTable
        : ('unicode.dis,' + selectedTable);

    const result = liblouisInstance.translateString(tableChain, text);

    // Validate result contains braille Unicode
    const hasBrailleChars = result.split('').some(char => {
        const code = char.charCodeAt(0);
        return code >= 0x2800 && code <= 0x28FF;
    });

    if (!hasBrailleChars) {
        throw new Error('Translation produced no braille Unicode output');
    }
```

### Table Chain Construction

The translation always uses a table chain to ensure Unicode braille output:

| Input Table | Resulting Chain |
|-------------|-----------------|
| `en-ueb-g2.ctb` | `unicode.dis,en-ueb-g2.ctb` |
| `en-ueb-g1.ctb` | `unicode.dis,en-ueb-g1.ctb` |
| `unicode.dis,en-ueb-g2.ctb` | `unicode.dis,en-ueb-g2.ctb` (unchanged) |

---

## 4. Computer Shorthand Conversion

### Purpose

Converts Unicode braille characters to human-readable "computer shorthand" notation, helping sighted users verify the translation without needing to read braille.

### Function Definition

**Source:** `templates/index.html` (lines 4044-4166)

```javascript
function brailleToComputerShorthand(brailleStr) {
    // Common UEB contractions and indicators
    const contractionMap = { ... };
    const indicatorMap = { ... };
    const punctuationMap = { ... };
    const letterMap = { ... };
    const digitMap = { ... };

    let result = '';
    let numericMode = false;
    let pendingWordGap = false;

    for (const ch of brailleStr) {
        // Process each character according to current mode
    }

    return result;
}
```

### Mapping Tables

#### Letter Map (Basic Braille Alphabet)

| Braille | Letter | Braille | Letter | Braille | Letter |
|---------|--------|---------|--------|---------|--------|
| ⠁ | a | ⠅ | k | ⠥ | u |
| ⠃ | b | ⠇ | l | ⠧ | v |
| ⠉ | c | ⠍ | m | ⠺ | w |
| ⠙ | d | ⠝ | n | ⠭ | x |
| ⠑ | e | ⠕ | o | ⠽ | y |
| ⠋ | f | ⠏ | p | ⠵ | z |
| ⠛ | g | ⠟ | q |   |   |
| ⠓ | h | ⠗ | r |   |   |
| ⠊ | i | ⠎ | s |   |   |
| ⠚ | j | ⠞ | t |   |   |

#### Contraction Map (UEB Contractions)

| Braille | Shorthand | Braille | Shorthand |
|---------|-----------|---------|-----------|
| ⠡ | [ch] | ⠬ | [ing] |
| ⠩ | [sh] | ⠢ | [en] |
| ⠹ | [th] | ⠔ | [in] |
| ⠱ | [wh] | ⠌ | [st] |
| ⠫ | [ed] | ⠮ | [the] |
| ⠻ | [er] | ⠯ | [and] |
| ⠳ | [ou] | ⠷ | [of] |
| ⠪ | [ow] | ⠿ | [for] |
| ⠜ | [ar] | ⠾ | [with] |

#### Indicator Map

| Braille | Display |
|---------|---------|
| ⠠ | [Capital Symbol] |
| ⠼ | [Number Symbol] |

#### Punctuation Map

| Braille | Character |
|---------|-----------|
| ⠂ | , (comma) |
| ⠆ | ; (semicolon) |
| ⠒ | : (colon) |
| ⠲ | . (period) |
| ⠖ | ! (exclamation) |
| ⠦ | ? (question) |
| ⠤ | - (hyphen) |
| ⠄ | ' (apostrophe) |

#### Digit Map (Numeric Mode)

After a number indicator (⠼), letters become digits:

| Braille | Digit |
|---------|-------|
| ⠁ | 1 |
| ⠃ | 2 |
| ⠉ | 3 |
| ⠙ | 4 |
| ⠑ | 5 |
| ⠋ | 6 |
| ⠛ | 7 |
| ⠓ | 8 |
| ⠊ | 9 |
| ⠚ | 0 |

### Processing Logic

```
1. Space → Ends numeric mode, sets pending word gap
2. Indicator → Add to result with word gap, update mode (⠼ enables numeric mode)
3. Contraction → Add bracketed contraction, end numeric mode
4. Digit (in numeric mode) → Add digit character
5. Letter → Add letter, end numeric mode
6. Punctuation → Add punctuation character, end numeric mode
7. Unknown → Show raw braille character as fallback
```

### Example Output

| Input Text | Unicode Braille | Computer Shorthand |
|------------|-----------------|-------------------|
| "Hello" | ⠓⠑⠇⠇⠕ | h e l l o |
| "The" | ⠮ | [the] |
| "123" | ⠼⠁⠃⠉ | [Number Symbol] 1 2 3 |
| "John" | ⠠⠚⠕⠓⠝ | [Capital Symbol] j o h n |

---

## 5. Manual Placement Mode Preview

### Trigger Behavior

**Source:** `templates/index.html` (lines 4168-4204)

When the "Preview Braille Translation" button is clicked in Manual placement mode:

```javascript
previewBrailleBtn.addEventListener('click', async () => {
    resetToGenerateState();  // Reset button state

    const languageSelect = document.getElementById('language-table');
    const tableName = languageSelect.value;
    const placementMode = document.querySelector('input[name="placement_mode"]:checked')?.value || 'manual';

    if (placementMode === 'manual') {
        const lines = getDynamicLineValues();

        // Validate: at least one line must have content
        if (lines.every(line => !line.trim())) {
            errorText.textContent = 'Please enter text in at least one line.';
            errorDiv.style.display = 'flex';
            return;
        }

        // Translate each non-empty line
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].trim()) {
                // Get per-line language table (or use default)
                const perLineTable = document.getElementById(`line_lang_${i+1}`)?.value || tableName;
                const braille = await translateWithLiblouis(lines[i].trim(), 'g2', perLineTable);
                const shorthand = brailleToComputerShorthand(braille);
                // Build preview HTML...
            }
        }
    }

    previewContent.innerHTML = previewHTML;
    braillePreview.style.display = 'block';
});
```

### Preview HTML Generation

**Success Template:**

```html
<div class="preview-line-success">
    <div><strong>Line 1:</strong> "Hello" → "⠓⠑⠇⠇⠕"</div>
    <div class="preview-subline">Computer shorthand: "h e l l o"</div>
</div>
```

**Error Template:**

```html
<div class="preview-line-error">
    <strong>Line 1:</strong> "Hello" → Error: Translation failed for table xyz
</div>
```

### Per-Line Language Support

Each line can have its own language table selector, allowing mixed-language content:

```
Line 1: [English UEB G2 ▼] "Hello"
Line 2: [French G2     ▼] "Bonjour"
Line 3: [German G2     ▼] "Hallo"
```

---

## 6. Auto Placement Mode Preview (BANA Wrapping)

### BANA Wrapping Algorithm

**Source:** `templates/index.html` (lines 3391-3580)

The BANA (Braille Authority of North America) auto-wrap algorithm distributes text across available rows while following braille formatting rules.

```javascript
async function banaAutoWrap(src, cols, rows, tableName) {
    const warnings = [];
    const textLines = [];
    const brailleLines = [];

    // Helper functions
    const normalizeSpaces = (s) => s.replace(/\s+/g, ' ').trim();
    const isHyphenChar = (ch) => /[-\u2010\u2011\u2012\u2013\u2014\u2212]/.test(ch);
    const isEmailBreakChar = (ch) => ch === '@' || ch === '.';

    // ... word processing logic
}
```

### BANA Wrapping Rules

1. **Word Preservation** — Prefer not dividing words across lines
2. **Hyphen Breaks** — Hyphenated words may break after the hyphen
3. **Email/URL Breaks** — May break after `@` or `.` characters
4. **Syllable Fallback** — For overlong words, attempt vowel-based syllable breaks
5. **Overflow Warning** — If text exceeds available cells, display warning

### Auto Mode Preview Flow

```javascript
if (placementMode !== 'manual') {
    const src = document.getElementById('auto-text')?.value.trim();

    const shapeTypeEl = document.querySelector('input[name="shape_type"]:checked');
    const cols = getAvailableColumns();
    const rows = parseInt(document.getElementById('grid_rows').value) || 4;

    const wrap = await banaAutoWrap(src, cols, rows, tableName);

    // Display wrapped lines
    for (let r = 0; r < rows; r++) {
        const slice = wrap.brailleLines[r] || '';
        const shorthand = slice ? brailleToComputerShorthand(slice) : '';
        // Build preview HTML...
    }

    // Show any wrapping warnings
    if (wrap.warnings && wrap.warnings.length) {
        errorText.textContent = wrap.warnings.join(' ');
        errorDiv.style.display = 'flex';
        errorDiv.className = 'grade-note';
    }
}
```

### Overflow Detection

The system calculates available cells and warns when text exceeds capacity:

```javascript
function getAvailableColumns() {
    const gridColumnsValue = parseInt(document.getElementById('grid_columns').value) || 15;
    return gridColumnsValue;  // UI dial shows usable text cells directly
}

function getTotalCellsAvailable() {
    const rows = parseInt(document.getElementById('grid_rows').value) || 4;
    const cols = getAvailableColumns();
    return rows * cols;
}
```

---

## 7. Language Table System

### Backend Table Discovery

**Source:** `backend.py` (lines 2051-2078)

```python
@app.route('/liblouis/tables')
def list_liblouis_tables():
    """List available liblouis translation tables from static assets."""
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

Each table entry contains:

```javascript
{
    file: "en-ueb-g2.ctb",       // Table filename
    locale: "en-US",             // Language/region code
    name: "Unified English Braille Grade 2",  // Display name
    grade: "2",                  // Grade level (0, 1, 2)
    type: "literary",            // Type (literary, computer)
    contraction: "full",         // Contraction level
    dots: 6,                     // Dot count (6 or 8)
    variant: "UEB"               // Standard variant (UEB, EBAE, etc.)
}
```

### Default Tables (Hardcoded)

```javascript
const defaultValues = new Set([
    'en-ueb-g2.ctb',  // Unified English Braille Grade 2
    'en-ueb-g1.ctb',  // Unified English Braille Grade 1
    'en-us-g2.ctb',   // English US Grade 2 (EBAE)
    'en-us-g1.ctb'    // English US Grade 1 (EBAE)
]);
```

### Frontend Table Loading

**Source:** `templates/index.html` (lines 2411-2500)

```javascript
async function loadLanguageOptions() {
    const select = document.getElementById('language-table');

    // Preserve defaults
    const defaultGroup = document.createElement('optgroup');
    defaultGroup.label = 'Default';
    // ... add default options

    // Fetch additional tables from backend
    const resp = await fetch('/liblouis/tables', { credentials: 'same-origin' });
    const data = await resp.json();

    // Sort: English first, then by locale
    data.tables.sort((a, b) => {
        const aEn = (a.locale || '').toLowerCase().startsWith('en') ? 0 : 1;
        const bEn = (b.locale || '').toLowerCase().startsWith('en') ? 0 : 1;
        if (aEn !== bEn) return aEn - bEn;
        // ... additional sorting
    });

    // Build options with autonym labels
    for (const entry of data.tables) {
        const opt = document.createElement('option');
        opt.value = entry.file;
        opt.textContent = buildLabel(entry);
        otherGroup.appendChild(opt);
    }
}
```

---

## 8. Backend Braille Validation

### Validation at Generation Time

**Source:** `backend.py` (lines 745-756)

The backend validates that incoming text contains proper braille Unicode:

```python
# Check if input contains proper braille Unicode (U+2800 to U+28FF)
has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)

if has_braille_chars:
    # Input is proper braille Unicode, use it directly
    braille_text = line_text
else:
    # Input is not braille Unicode - this is an error
    error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters. ' \
                'Frontend must translate text to braille before sending.'
    logger.error(f'{error_msg}')
    raise RuntimeError(error_msg)
```

### Braille-to-Dots Conversion

**Source:** `app/utils.py` (lines 96-133)

```python
def braille_to_dots(braille_char: str) -> list:
    """
    Convert a braille character to dot pattern.

    Braille dots are arranged as:
    1 4
    2 5
    3 6

    Returns:
        List of 6 integers (0 or 1) representing dot pattern
    """
    if not braille_char or braille_char == ' ':
        return [0, 0, 0, 0, 0, 0]  # Empty cell

    code_point = ord(braille_char)

    # Check if it's in the braille Unicode block (U+2800 to U+28FF)
    if code_point < 0x2800 or code_point > 0x28FF:
        return [0, 0, 0, 0, 0, 0]  # Not a braille character

    # Extract the dot pattern (bits 0-5 for dots 1-6)
    dot_pattern = code_point - 0x2800

    dots = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        if dot_pattern & (1 << i):
            dots[i] = 1

    return dots
```

### Dot Pattern Encoding

The Unicode braille block encodes dots as bits:

| Bit Position | Dot Number | Braille Cell Position |
|--------------|------------|----------------------|
| Bit 0 | Dot 1 | Top-left |
| Bit 1 | Dot 2 | Middle-left |
| Bit 2 | Dot 3 | Bottom-left |
| Bit 3 | Dot 4 | Top-right |
| Bit 4 | Dot 5 | Middle-right |
| Bit 5 | Dot 6 | Bottom-right |

**Example:** ⠓ (U+2813) = 0x2813 - 0x2800 = 0x13 = 10011₂ = dots 1, 2, 5 = "h"

---

## 9. Braille Unicode Character Handling

### Unicode Constants

**Source:** `app/utils.py` (lines 17-19)

```python
# Braille Unicode range
BRAILLE_UNICODE_START = 0x2800  # ⠀ (blank braille pattern)
BRAILLE_UNICODE_END = 0x28FF    # ⣿ (all 8 dots)
```

### Character Detection

**Source:** `app/utils.py` (lines 63-77)

```python
def is_braille_char(char: str) -> bool:
    """Check if a character is a braille Unicode character."""
    if not char or len(char) != 1:
        return False
    code = ord(char)
    return BRAILLE_UNICODE_START <= code <= BRAILLE_UNICODE_END
```

### JavaScript Equivalent

```javascript
// Check for braille Unicode characters
const hasBrailleChars = result.split('').some(function(char){
    const code = char.charCodeAt(0);
    return code >= 0x2800 && code <= 0x28FF;
});
```

---

## 10. Error States and Fallbacks

### Worker Initialization Failure

**Source:** `templates/index.html` (lines 5052-5067)

```javascript
} catch (error) {
    log.error('Failed to initialize liblouis worker:', error);

    // Fallback: disable liblouis
    liblouisReady = false;
    liblouisWorker = null;

    // Show user that translation is disabled
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    if (errorDiv && errorText) {
        errorText.textContent = 'Web worker failed to initialize. ' +
            'Braille translation preview is disabled on this deployment.';
        errorDiv.style.display = 'flex';
    }
}
```

### Translation Failure Handling

**Source:** `templates/index.html` (lines 5078-5097)

```javascript
async function translateWithLiblouis(text, grade, tableName = null) {
    if (!liblouisReady || !liblouisWorker) {
        throw new Error('Liblouis worker not initialized - ' +
            'translation preview unavailable on this deployment');
    }

    try {
        const result = await sendWorkerMessage('translate', { text, grade, tableName });
        if (result.success && result.translation) {
            return result.translation;
        } else {
            throw new Error('Translation failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        log.error('Worker translation failed:', error);
        throw error;
    }
}
```

### Error Display States

| Error Type | Display Location | Styling |
|------------|-----------------|---------|
| Worker init failure | Error message div | `.error-message` |
| Translation failure | Preview line | `.preview-line-error` |
| Empty input | Error message div | `.error-message` |
| BANA wrap warning | Error message div | `.grade-note` |
| Overflow warning | Error message div | `.grade-note` |

---

## 11. Styling and Accessibility

### CSS Variables (Theme Support)

```css
.braille-preview {
    margin-top: 20px;
    padding: 15px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
}

.preview-heading {
    margin-top: 0;
    color: var(--text-primary);
}

.preview-line-success {
    margin: 10px 0;
    padding: 10px;
    background: var(--bg-primary);
    border-radius: 5px;
    border: 1px solid var(--border-primary);
}

.preview-line-error {
    margin: 10px 0;
    padding: 10px;
    background: var(--error-bg);
    border-radius: 5px;
    border: 1px solid var(--error-border);
    color: var(--error-text);
}

.preview-subline {
    font-size: 0.9em;
    opacity: 0.85;
    margin-top: 0.25em;
}
```

### High Contrast Mode

```css
[data-theme="high-contrast"] .braille-preview {
    background: #1a1a1a !important;
    color: #ffff00 !important;
    border: 2px solid #ffff00 !important;
}

[data-theme="high-contrast"] .preview-line-success {
    background: #2a2a2a !important;
    color: #02fe05 !important;     /* Green for success */
    border: 2px solid #00ffff !important;  /* Cyan border */
}
```

### ARIA Attributes

```html
<div id="braille-preview" class="braille-preview"
     role="region"
     aria-label="Braille translation preview">
```

---

## 12. Cross-Implementation Consistency

### Translation Chain Verification

| Stage | Component | Verification Method |
|-------|-----------|---------------------|
| Input | Frontend | Collect text from input fields |
| Translation | liblouis-worker.js | Uses `unicode.dis` chain for Unicode output |
| Validation | backend.py | Checks U+2800–U+28FF range |
| Conversion | app/utils.py | `braille_to_dots()` for geometry |
| Rendering | csg-worker.js | Consumes dot patterns, not text |

### Unicode Braille Consistency

All components agree on braille Unicode handling:

**Frontend (liblouis-worker.js):**
```javascript
const code = char.charCodeAt(0);
return code >= 0x2800 && code <= 0x28FF;
```

**Backend (app/utils.py):**
```python
BRAILLE_UNICODE_START = 0x2800
BRAILLE_UNICODE_END = 0x28FF
```

**Backend (backend.py):**
```python
has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)
```

### Table Path Consistency

**Note:** There is a difference in table path resolution between the worker and backend:

**Worker (`liblouis-worker.js`) table paths:**

| Priority | Path |
|----------|------|
| 1 | `{origin}/static/liblouis/tables/` |
| 2 | `/node_modules/liblouis-build/tables/` |
| 3 | `static/liblouis/tables/` (relative fallback) |

**Backend (`backend.py`) table paths:**

| Priority | Path |
|----------|------|
| 1 | `{app_root}/static/liblouis/tables/` |
| 2 | `{app_root}/node_modules/liblouis-build/tables/` |
| 3 | `{app_root}/third_party/liblouis/tables/` |
| 4 | `{app_root}/third_party/liblouis/share/liblouis/tables/` |

The backend has additional fallback paths for alternative deployment configurations. Both prioritize `/static/liblouis/tables/` as the primary location.

---

## Appendix A: Specification Verification Report

This section documents the cross-check verification performed against actual implementations.

### Verification Date

2024-12-06

### Components Verified

| Component | File | Status |
|-----------|------|--------|
| HTML Structure | `templates/index.html` | ✅ VERIFIED |
| HTML Structure | `public/index.html` | ✅ VERIFIED (identical structure) |
| CSS Classes | `templates/index.html` | ✅ VERIFIED |
| Liblouis Worker | `static/liblouis-worker.js` | ✅ VERIFIED |
| Backend Validation | `backend.py` | ✅ VERIFIED |
| Backend Utils | `app/utils.py` | ✅ VERIFIED |
| Backend Validation Module | `app/validation.py` | ✅ VERIFIED |

### Unicode Range Consistency

All implementations use consistent Unicode braille range:

| Location | Start | End | Status |
|----------|-------|-----|--------|
| `app/utils.py` (constants) | `0x2800` | `0x28FF` | ✅ |
| `app/validation.py` (constants) | `0x2800` | `0x28FF` | ✅ |
| `backend.py` (line 747) | `0x2800` | `0x28FF` | ✅ |
| `backend.py` (line 937) | `0x2800` | `0x28FF` | ✅ |
| `app/geometry/cylinder.py` | `0x2800` | `0x28FF` | ✅ |
| `app/geometry/plates.py` | `0x2800` | `0x28FF` | ✅ |
| `static/liblouis-worker.js` | `0x2800` | `0x28FF` | ✅ |

### Computer Shorthand Maps Verified

The `brailleToComputerShorthand()` function maps were verified against the code:

- **Letter Map**: 26 letters (a-z) ✅
- **Contraction Map**: 18 contractions (ch, sh, th, wh, ed, er, ou, ow, ar, ing, en, in, st, the, and, of, for, with) ✅
- **Indicator Map**: 2 indicators (Capital, Number) ✅
- **Punctuation Map**: 8 punctuation marks ✅
- **Digit Map**: 10 digits (0-9) ✅

### Corrections Made During Verification

1. **Table Path Discrepancy** — The worker (`liblouis-worker.js`) does NOT check `third_party/liblouis/tables/` path, only the backend does. Specification updated to reflect the actual difference.

2. **CSS Class Description** — Added missing `font-size` and `opacity` properties for `.preview-subline` class.

3. **Success Row Description** — Changed from "Green-tinted background" to "Neutral background" as `--bg-primary` is theme-dependent.

---

## Appendix B: Complete Braille Unicode Block Reference

The Braille Patterns Unicode block (U+2800–U+28FF) contains 256 characters representing all possible 8-dot braille patterns. For 6-dot braille (standard literary braille), only characters U+2800–U+283F (64 patterns) are used.

### 6-Dot Pattern Range (U+2800–U+283F)

| Range | Pattern Description |
|-------|---------------------|
| U+2800 | ⠀ Blank (no dots) |
| U+2801–U+280F | Single dot patterns (dots 1-4) |
| U+2810–U+281F | Two-dot patterns |
| U+2820–U+282F | Three-dot patterns |
| U+2830–U+283F | Four+ dot patterns (6-dot max) |

### Pattern Calculation Formula

```
Unicode Code Point = 0x2800 + (dot1 × 1) + (dot2 × 2) + (dot3 × 4) +
                              (dot4 × 8) + (dot5 × 16) + (dot6 × 32)
```

---

## Appendix C: Liblouis Table File Format

Liblouis tables use a specific format with directives for translation rules:

```
# Table metadata (parsed by backend)
#+language: en
#+type: literary
#+contraction: full
#+grade: 2
#+region: US
#+variant: UEB

# Include other tables
include unicode.dis
include en-ueb-g2.ctb

# Translation rules
word the 2346
word and 12346
```

The backend's `_scan_liblouis_tables()` function parses these metadata lines to populate the language dropdown.

---

## Appendix D: Troubleshooting

### Preview Button Not Working

1. Check browser console for liblouis worker errors
2. Verify `/static/liblouis/` files are accessible
3. Ensure web workers are supported in the browser

### Translation Returns Empty

1. Verify table file exists in tables directory
2. Check worker logs for "Translation produced no braille Unicode output"
3. Ensure `unicode.dis` is in the table chain

### Computer Shorthand Shows Raw Braille

This occurs when a braille character is not in any mapping table. The function falls back to displaying the raw Unicode braille character.

### Backend Rejects Valid Braille

If backend returns "does not contain proper braille Unicode characters":
1. Frontend translation may have failed silently
2. Data may have been corrupted in transit
3. Check that lines are not empty strings
