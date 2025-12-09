# ADA Accessibility Validation SOP

## Standard Operating Procedure for Maintaining WCAG 2.1 Level AA Compliance

**Document Version:** 1.0
**Created:** December 8, 2025
**Standard:** WCAG 2.1 Level AA
**Compliance Deadline:** April 24, 2026 / April 26, 2027

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [When to Perform Validation](#3-when-to-perform-validation)
4. [Pre-Development Checklist](#4-pre-development-checklist)
5. [Development Guidelines](#5-development-guidelines)
6. [Post-Development Validation Procedure](#6-post-development-validation-procedure)
7. [Automated Testing Tools](#7-automated-testing-tools)
8. [Manual Testing Checklist](#8-manual-testing-checklist)
9. [Common Accessibility Issues and Fixes](#9-common-accessibility-issues-and-fixes)
10. [Documentation Requirements](#10-documentation-requirements)
11. [Quick Reference Card](#11-quick-reference-card)

---

## 1. Purpose

This SOP ensures that the Braille Card and Cylinder STL Generator maintains WCAG 2.1 Level AA compliance throughout its development lifecycle. Following these procedures prevents accessibility regressions and ensures the application remains usable by people with disabilities.

---

## 2. Scope

This procedure applies to:
- All changes to `templates/index.html` and `public/index.html`
- Any UI/UX modifications
- New feature implementations
- CSS styling changes
- JavaScript functionality changes affecting user interaction
- Third-party library updates

---

## 3. When to Perform Validation

### Full Validation Required (All Steps)

Perform **full validation** when:
- Adding new UI components (buttons, forms, panels, modals)
- Modifying existing interactive elements
- Changing color schemes or themes
- Adding or modifying accordion/toggle functionality
- Updating text content in significant amounts
- Modifying form controls or labels
- Adding new sections or reorganizing layout
- Updating third-party libraries (Three.js, etc.)

### Quick Validation Sufficient

Perform **quick validation** (Steps 6.1, 6.2, 6.3 only) when:
- Minor text corrections
- Bug fixes not affecting UI
- Backend-only changes
- Documentation updates

---

## 4. Pre-Development Checklist

Before starting development on a new feature, review:

- [ ] **Consult UI Specifications**: Read `docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md`
- [ ] **Review Accessibility Section**: Section 4 covers all accessibility requirements
- [ ] **Check Color Contrast Requirements**:
  - Text: 4.5:1 minimum ratio
  - Large text (18pt+ or 14pt bold): 3:1 minimum ratio
  - UI components: 3:1 minimum ratio
- [ ] **Plan ARIA Attributes**: Determine what ARIA attributes new elements need
- [ ] **Keyboard Navigation**: Plan how users will navigate the new feature with keyboard only

---

## 5. Development Guidelines

### 5.1 HTML Structure

```html
<!-- ✅ GOOD: Semantic HTML with proper ARIA -->
<button type="button"
        id="my-toggle"
        class="toggle-btn"
        aria-expanded="false"
        aria-controls="my-content">
    <span id="toggle-text">Show Content</span>
    <span class="toggle-icon">▼</span>
</button>
<div id="my-content" style="display: none;">
    <!-- Content here -->
</div>

<!-- ❌ BAD: Missing ARIA attributes -->
<div class="clickable" onclick="toggle()">
    Show Content
</div>
```

### 5.2 JavaScript Event Handlers

```javascript
// ✅ GOOD: Updates aria-expanded dynamically
myToggleBtn.addEventListener('click', () => {
    const isVisible = myContent.style.display !== 'none';
    myContent.style.display = isVisible ? 'none' : 'block';
    myToggleBtn.setAttribute('aria-expanded', String(!isVisible));
    myToggleBtn.classList.toggle('active', !isVisible);
});

// ❌ BAD: Does not update ARIA state
myToggleBtn.addEventListener('click', () => {
    myContent.style.display = myContent.style.display === 'none' ? 'block' : 'none';
});
```

### 5.3 CSS Color Contrast

```css
/* ✅ GOOD: Meets WCAG AA contrast (4.5:1+) */
.toggle-btn.active {
    background: #1e4976; /* Dark blue: 6.1:1 with white */
    color: #fff;
}

/* ❌ BAD: Fails WCAG AA contrast */
.toggle-btn.active {
    background: #3182ce; /* Light blue: 3.7:1 with white - FAILS */
    color: #fff;
}
```

### 5.4 Form Controls

```html
<!-- ✅ GOOD: Proper label association -->
<label for="my-input">Input Label:</label>
<input type="text" id="my-input" name="my_input" aria-describedby="my-input-help">
<div id="my-input-help" class="help-text">Help text here</div>

<!-- ✅ GOOD: Screen-reader-only label for visual context -->
<label for="language-select" class="sr-only">Select braille language table</label>
<select id="language-select" name="language_table">...</select>

<!-- ❌ BAD: No label association -->
<span>Input Label:</span>
<input type="text" name="my_input">
```

### 5.5 Focus Management

```javascript
// ✅ GOOD: Move focus to first focusable element when panel opens
panelToggle.addEventListener('click', () => {
    const isOpen = panel.style.display !== 'none';
    panel.style.display = isOpen ? 'none' : 'block';

    if (!isOpen) {
        // Move focus to first focusable element
        const firstFocusable = panel.querySelector(
            'input, select, button, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }
});
```

---

## 6. Post-Development Validation Procedure

### 6.1 W3C HTML Validation (Required)

1. Start local server: `$env:FLASK_ENV="development"; python wsgi.py`
2. Open https://validator.w3.org/
3. Select "Validate by URI" or "Validate by Direct Input"
4. Enter `http://127.0.0.1:5000` or paste HTML content
5. Click "Check"
6. **Target**: 0 errors, 0 warnings

**Common Errors to Watch For:**
- Duplicate IDs
- Missing closing tags
- Invalid ARIA attributes on wrong element types
- Deprecated attributes

### 6.2 Lighthouse Accessibility Audit (Required)

1. Open application in Chrome/Edge
2. Press **F12** to open DevTools
3. Click **Lighthouse** tab
4. Uncheck all categories except **Accessibility**
5. Select **Desktop** mode, click "Analyze page load"
6. Record score and any issues
7. Select **Mobile** mode, repeat analysis
8. **Target**: 100/100 on both Desktop and Mobile

**If Score < 100:**
- Review each failing audit item
- Fix issues in order of impact (Critical → Moderate → Minor)
- Re-run Lighthouse until 100/100 achieved

### 6.3 Color Contrast Verification (Required for Style Changes)

**Option A: WebAIM Contrast Checker**
1. Go to https://webaim.org/resources/contrastchecker/
2. Enter foreground and background colors
3. Verify "WCAG AA" shows "Pass" for your use case

**Option B: Chrome DevTools**
1. Right-click element → Inspect
2. In Styles panel, click any color value
3. Look for contrast ratio in color picker
4. Green checkmark = passes, Red X = fails

**Required Ratios:**
| Content Type | Minimum Ratio |
|--------------|---------------|
| Normal text (<18pt) | 4.5:1 |
| Large text (18pt+ or 14pt bold) | 3:1 |
| UI components (buttons, icons) | 3:1 |

### 6.4 Keyboard Navigation Test (Required for Interactive Changes)

1. Refresh the page
2. Press **Tab** repeatedly through entire page
3. Verify:
   - [ ] All interactive elements are reachable
   - [ ] Focus order is logical (top-to-bottom, left-to-right)
   - [ ] Focus indicator is visible on all elements
   - [ ] Skip link appears on first Tab and works
4. Test all toggles/accordions with **Enter** and **Space** keys
5. Test form submission with **Enter** key

### 6.5 Screen Reader Test (Required for Major UI Changes)

**Using NVDA (Free):**
1. Download from https://www.nvaccess.org/
2. Start NVDA, open application
3. Navigate using Tab key
4. Verify:
   - [ ] All buttons announce their purpose
   - [ ] Toggle buttons announce expanded/collapsed state
   - [ ] Form fields announce their labels
   - [ ] Error messages are announced when they appear
   - [ ] Images have appropriate alt text or are marked decorative

### 6.6 Theme Testing (Required for Color/Style Changes)

Test all functionality in each theme:
1. **Dark Mode** (default)
2. **High Contrast Mode**
3. **Light Mode**

For each theme, verify:
- [ ] All text is readable
- [ ] Focus indicators are visible
- [ ] Button states are distinguishable
- [ ] No content disappears or becomes unreadable

### 6.7 Font Size Testing (Required for Layout Changes)

1. Use application font controls to set 200% size
2. Verify:
   - [ ] No content is cut off or hidden
   - [ ] No horizontal scrolling required
   - [ ] All functionality remains accessible
3. Test at 75% minimum size
4. Verify all content remains readable

---

## 7. Automated Testing Tools

### Required Tools

| Tool | Purpose | URL |
|------|---------|-----|
| W3C HTML Validator | HTML syntax validation | https://validator.w3.org/ |
| Lighthouse | Accessibility scoring | Built into Chrome/Edge DevTools |
| WebAIM Contrast Checker | Color contrast verification | https://webaim.org/resources/contrastchecker/ |

### Recommended Tools

| Tool | Purpose | URL |
|------|---------|-----|
| WAVE | Visual accessibility evaluation | https://wave.webaim.org/extension/ |
| axe DevTools | Detailed accessibility testing | Chrome/Firefox extension |
| NVDA | Screen reader testing | https://www.nvaccess.org/ |
| Color Oracle | Color blindness simulation | https://colororacle.org/ |

---

## 8. Manual Testing Checklist

Use this checklist for each major feature release:

### HTML/Structure
- [ ] All interactive elements are semantic HTML (`<button>`, `<a>`, `<input>`)
- [ ] All form inputs have associated `<label>` elements
- [ ] Page has proper heading hierarchy (h1 → h2 → h3)
- [ ] Landmark regions are properly defined (`<main>`, `<nav>`, `<header>`)
- [ ] Skip link is present and functional

### ARIA
- [ ] All expandable elements have `aria-expanded`
- [ ] All expandable elements have `aria-controls` pointing to content ID
- [ ] Dynamic content updates use `aria-live` regions
- [ ] Decorative elements have `aria-hidden="true"`
- [ ] Icons have `aria-hidden="true"` with text alternatives

### Keyboard
- [ ] All functionality works with keyboard only
- [ ] Tab order follows visual layout
- [ ] Focus is never trapped
- [ ] Modal/dialogs trap focus appropriately
- [ ] Escape key closes modals/dropdowns

### Visual
- [ ] Focus indicators are visible in all themes
- [ ] Color is not the only means of conveying information
- [ ] Text contrast meets 4.5:1 minimum
- [ ] UI component contrast meets 3:1 minimum
- [ ] Content reflows at 400% zoom without horizontal scroll

---

## 9. Common Accessibility Issues and Fixes

### Issue: Toggle Button Missing aria-expanded

**Symptom:** Screen reader doesn't announce expanded/collapsed state

**Fix:**
```html
<!-- Add to button element -->
<button aria-expanded="false" aria-controls="panel-id">Toggle</button>

<!-- Add to JavaScript handler -->
button.setAttribute('aria-expanded', String(isExpanded));
```

### Issue: Insufficient Color Contrast

**Symptom:** Lighthouse reports contrast error

**Fix:**
1. Use WebAIM Contrast Checker to find compliant color
2. For active button states, use darker variants:
   - Light mode: `#1e4976` (6.1:1 with white)
   - Dark mode: `#1e5a8a` (4.7:1 with white)

### Issue: Form Input Without Label

**Symptom:** Screen reader doesn't announce input purpose

**Fix:**
```html
<!-- Option 1: Visible label -->
<label for="input-id">Label Text</label>
<input id="input-id" type="text">

<!-- Option 2: Screen-reader-only label -->
<label for="input-id" class="sr-only">Label Text</label>
<input id="input-id" type="text">

<!-- Option 3: aria-label (less preferred) -->
<input id="input-id" type="text" aria-label="Label Text">
```

### Issue: Missing Focus Indicator

**Symptom:** Can't see which element is focused when tabbing

**Fix:**
```css
button:focus,
input:focus,
select:focus {
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}
```

### Issue: Decorative Icon Read by Screen Reader

**Symptom:** Screen reader announces emoji/icon characters

**Fix:**
```html
<span aria-hidden="true">▼</span>
```

---

## 10. Documentation Requirements

After completing accessibility validation, update the following:

### 10.1 Update Accessibility Documentation

Add a new entry to your accessibility tracking with:
- Date of validation
- Issues found (if any)
- Fixes applied
- Verification results (W3C, Lighthouse scores)

### 10.2 Update UI Specifications (if applicable)

Location: `docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md`

If new accessibility patterns were introduced, document them in Section 4 (Accessibility Features).

### 10.3 Commit Message Format

Use this format for accessibility-related commits:

```
fix: resolve [N] accessibility issues found in [feature] audit

- [Brief description of fix 1] (WCAG X.X.X)
- [Brief description of fix 2] (WCAG X.X.X)
- Sync changes to public/index.html
- Update ADA accessibility roadmap

Lighthouse score: [before] → [after]
```

---

## 11. Quick Reference Card

### Minimum Requirements for Any UI Change

| Check | Tool | Target |
|-------|------|--------|
| HTML Valid | W3C Validator | 0 errors |
| Accessibility Score | Lighthouse | 100/100 |
| Text Contrast | Contrast Checker | 4.5:1+ |
| Keyboard Navigation | Manual | All reachable |

### Essential ARIA for Toggle Buttons

```html
<button aria-expanded="false" aria-controls="content-id">
```

```javascript
button.setAttribute('aria-expanded', String(!isCollapsed));
```

### Essential CSS for Focus

```css
:focus {
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}
```

### Color Contrast Safe Values

| Use Case | Light Mode | Dark Mode | High Contrast |
|----------|------------|-----------|---------------|
| Active button bg | `#1e4976` | `#1e5a8a` | `#000000` |
| Active button text | `#ffffff` | `#ffffff` | `#02fe05` |
| Focus outline | `#3182ce` | `#63b3ed` | `#ff00ff` |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial SOP created after re-audit session |

---

## Related Documents

- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md)
- [Browser Compatibility Audit](./BROWSER_COMPATIBILITY_AUDIT.md)
