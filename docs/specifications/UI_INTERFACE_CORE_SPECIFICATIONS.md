# UI Interface Core Specifications

## Document Purpose

This document provides **in-depth specifications** for all UI interface core logic and accessibility features in the Braille Card and Cylinder STL Generator application. It serves as an authoritative reference for future development by documenting:

1. **Theme System** — Dark mode, light mode, and high contrast mode implementations
2. **Font Size Adjustment** — Accessibility scaling system
3. **STL Preview Panel** — Three.js 3D viewer configuration and theme-aware rendering
4. **Accessibility Features** — Keyboard navigation, screen reader support, focus indicators
5. **User Preference Handling** — Session-based settings (non-persistent by design)
6. **Help Modal System** — Accessible tabbed help with BANA business card guidance

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source for server-side logic
2. `wsgi.py` — Application startup and configuration
3. `static/workers/csg-worker.js` — Client-side CSG (three-bvh-csg)
4. Manifold WASM (`csg-worker-manifold.js`) — Mesh repair and validation

---

## ⚠️ CRITICAL: HTML File Location Warning

**There are TWO `index.html` files in this project. You MUST edit the correct one:**

| File | Purpose | Served by Flask? | Status |
|------|---------|------------------|--------|
| **`public/index.html`** | **PRODUCTION FILE — Edit this one!** | ✅ YES | **ACTIVE** |
| `templates/index.html` | Legacy/backup file — NOT served | ❌ NO | **⛔ DEPRECATED** |

### `templates/index.html` Deprecation Notice (2026-01-28)

The `templates/index.html` file is **officially deprecated** and should not be edited. It is missing critical features present in `public/index.html`:

| Missing Feature | Purpose |
|----------------|---------|
| `viewport-fit=cover` | iOS notch support |
| `--vh` CSS variable | Mobile viewport handling |
| `safe-area-inset-*` CSS | Edge-to-edge display support |
| `nomodule` fallback script | Older browser compatibility |
| `prefers-reduced-motion` CSS/JS | Motion accessibility |
| WebGL context loss recovery | Graphics stability |

**This file may be removed in a future release.**

**Why this matters:**
- The Flask backend (`backend.py`) serves `public/index.html` via `send_from_directory('public', 'index.html')`
- Changes to `templates/index.html` will have **NO EFFECT** on the running application
- Both files may contain similar content, which can cause confusion

**Before making UI changes:**
1. Always edit `public/index.html`
2. Verify the correct file by checking `backend.py` routes if uncertain
3. Hard refresh the browser (Ctrl+Shift+R) after changes to clear cache

**Route Configuration (from `backend.py`):**
```python
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/index.html')
def index_explicit():
    return send_from_directory('public', 'index.html')
```

---

## Table of Contents

1. [Theme System](#1-theme-system)
   - 1.1 [Theme Modes Overview](#11-theme-modes-overview)
   - 1.2 [Theme CSS Variables](#12-theme-css-variables)
   - 1.3 [High Contrast Mode Specifications](#13-high-contrast-mode-specifications)
   - 1.4 [Theme Switching Logic](#14-theme-switching-logic)
   - 1.5 [Theme Persistence Policy](#15-theme-persistence-policy)
2. [Font Size Adjustment System](#2-font-size-adjustment-system)
   - 2.1 [Font Size Scale](#21-font-size-scale)
   - 2.2 [Font Size Controls UI](#22-font-size-controls-ui)
   - 2.3 [Font Size Logic](#23-font-size-logic)
   - 2.4 [Screen Reader Announcements](#24-screen-reader-announcements)
3. [STL Preview Panel](#3-stl-preview-panel)
   - 3.1 [Three.js Scene Configuration](#31-threejs-scene-configuration)
   - 3.2 [Theme-Aware Colors and Lighting](#32-theme-aware-colors-and-lighting)
   - 3.3 [High Contrast Mode Lighting](#33-high-contrast-mode-lighting)
   - 3.4 [Camera and Controls](#34-camera-and-controls)
     - 3.4.1 [CAMERA_SETTINGS Global Configuration](#341-camera_settings-global-configuration)
     - 3.4.2 [Coordinate System Reference](#342-coordinate-system-reference)
     - 3.4.3 [How to Adjust the Initial Camera View](#343-how-to-adjust-the-initial-camera-view)
     - 3.4.4 [Camera Implementation Details](#344-camera-implementation-details)
     - 3.4.5 [OrbitControls Configuration](#345-orbitcontrols-configuration)
   - 3.5 [Mobile Optimizations](#35-mobile-optimizations)
   - 3.6 [Dynamic Theme Updates](#36-dynamic-theme-updates)
   - 3.7 [STL Preview Label](#37-stl-preview-label)
   - 3.8 [Preview Display Settings (Brightness and Contrast)](#38-preview-display-settings-brightness-and-contrast)
   - 3.9 [WebGL Context Recovery](#39-webgl-context-recovery)
4. [Accessibility Features](#4-accessibility-features)
   - 4.1 [Skip Link Navigation](#41-skip-link-navigation)
   - 4.2 [Focus Indicators](#42-focus-indicators)
   - 4.3 [Screen Reader Support](#43-screen-reader-support)
   - 4.4 [Touch and Mobile Accessibility](#44-touch-and-mobile-accessibility)
   - 4.5 [Toggle Button ARIA Requirements](#45-toggle-button-aria-requirements)
   - 4.6 [Reduced Motion Support](#46-reduced-motion-support)
5. [Scrollbar Customization](#5-scrollbar-customization)
   - 5.1 [Form Section Scrollbar](#51-form-section-scrollbar)
   - 5.2 [Global Page Scrollbar](#52-global-page-scrollbar)
   - 5.3 [Theme-Specific Scrollbar Styles](#53-theme-specific-scrollbar-styles)
6. [Button State Management](#6-button-state-management)
   - 6.1 [Action Button States](#61-action-button-states)
   - 6.2 [High Contrast Button Styling](#62-high-contrast-button-styling)
7. [Layout Responsiveness](#7-layout-responsiveness)
   - 7.1 [Desktop Two-Column Layout](#71-desktop-two-column-layout)
   - 7.2 [Mobile Stacked Layout](#72-mobile-stacked-layout)
   - 7.3 [iOS Safe Area Handling](#73-ios-safe-area-handling)
8. [Help Modal System](#8-help-modal-system)
   - 8.1 [Overview](#81-overview)
   - 8.2 [Modal Structure](#82-modal-structure)
   - 8.3 [Tab Panels](#83-tab-panels)
   - 8.4 [Accessibility Features](#84-accessibility-features)
   - 8.5 [JavaScript API](#85-javascript-api)
   - 8.6 [Trigger Buttons](#86-trigger-buttons)
   - 8.7 [CSS Classes](#87-css-classes)
   - 8.8 [High Contrast Mode](#88-high-contrast-mode)
   - 8.9 [Related Documentation](#89-related-documentation)
9. [Design Rationale](#9-design-rationale)

---

## 1. Theme System

### 1.1 Theme Modes Overview

The application supports **three theme modes** designed to accommodate different visual preferences and accessibility needs:

| Theme | Purpose | Primary Users |
|-------|---------|---------------|
| **Dark** | Reduced eye strain in low-light environments | Default for all users |
| **Light** | Traditional high-brightness interface | Users preferring light backgrounds |
| **High Contrast** | Maximum visibility for low vision users | Users with visual impairments |

**Theme Cycle Order:**
```
Dark → High Contrast → Light → Dark (repeats)
```

**CRITICAL:** The application **always starts in Dark mode** regardless of user's system preferences. This is an intentional design decision to provide a consistent starting experience.

### 1.2 Theme CSS Variables

All theme-dependent colors are defined using CSS custom properties (variables) on the `:root` element and `[data-theme]` attribute selectors.

#### Light Mode (Default CSS Variables)

```css
:root {
    /* Background colors */
    --bg-gradient-start: #e0e7ff;
    --bg-gradient-end: #f6f8fa;
    --bg-primary: #fff;
    --bg-secondary: #f8fafc;
    --bg-tertiary: #f1f5f9;
    --bg-input: #f9fafb;

    /* Text colors */
    --text-primary: #2d3748;
    --text-secondary: #4a5568;
    --text-tertiary: #666;

    /* Border colors */
    --border-primary: #e2e8f0;
    --border-secondary: #cbd5e1;
    --border-focus: #3182ce;

    /* Button colors */
    --btn-primary-bg: linear-gradient(90deg, #3182ce 60%, #63b3ed 100%);
    --btn-primary-hover-bg: linear-gradient(90deg, #2563eb 60%, #4299e1 100%);
    --btn-success-bg: #10b981;
    --btn-success-hover-bg: #059669;
    --btn-secondary-bg: #9ca3af;
    --btn-tertiary-bg: #6b7280;

    /* Status colors */
    --error-bg: #fee2e2;
    --error-border: #fecaca;
    --error-text: #b91c1c;
    --info-bg: #dbeafe;
    --info-border: #93c5fd;
    --info-text: #1e40af;

    /* Shadow colors */
    --shadow-light: rgba(49,130,206,0.10);
    --shadow-medium: rgba(49,130,206,0.18);

    /* STL Preview colors - CRITICAL FOR 3D VIEWING */
    --stl-mesh-color: #6699cc;
    --stl-background: #f1f5f9;
    --stl-ambient-light: #888888;
    --stl-directional-light: #ffffff;
    --stl-ambient-intensity: 0.5;
    --stl-directional-intensity: 1.0;

    /* Scrollbar dimensions */
    --scrollbar-width: 18px;
    --global-scrollbar-width: 13.5px;
    --scrollbar-arrow-color: #3182ce;
}
```

#### Dark Mode

```css
[data-theme="dark"] {
    /* Background colors */
    --bg-gradient-start: #1a202c;
    --bg-gradient-end: #2d3748;
    --bg-primary: #2d3748;
    --bg-secondary: #374151;
    --bg-tertiary: #4a5568;
    --bg-input: #374151;

    /* Text colors */
    --text-primary: #f7fafc;
    --text-secondary: #e2e8f0;
    --text-tertiary: #cbd5e1;

    /* Border colors */
    --border-primary: #4a5568;
    --border-secondary: #718096;
    --border-focus: #63b3ed;

    /* Button colors */
    --btn-primary-bg: linear-gradient(90deg, #4299e1 60%, #63b3ed 100%);
    --btn-primary-hover-bg: linear-gradient(90deg, #3182ce 60%, #4299e1 100%);
    --btn-success-bg: #059669;
    --btn-success-hover-bg: #047857;
    --btn-secondary-bg: #718096;
    --btn-tertiary-bg: #4a5568;

    /* Status colors */
    --error-bg: #742a2a;
    --error-border: #9b2c2c;
    --error-text: #fed7d7;
    --info-bg: #2c5282;
    --info-border: #3182ce;
    --info-text: #bee3f8;

    /* Shadow colors */
    --shadow-light: rgba(0,0,0,0.3);
    --shadow-medium: rgba(0,0,0,0.5);

    /* STL Preview colors */
    --stl-mesh-color: #90cdf4;
    --stl-background: #2d3748;
    --stl-ambient-light: #666666;
    --stl-directional-light: #ffffff;
    --stl-ambient-intensity: 0.6;
    --stl-directional-intensity: 0.9;

    /* Scrollbar */
    --scrollbar-arrow-color: #63b3ed;
}
```

### 1.3 High Contrast Mode Specifications

**CRITICAL FOR LOW VISION USERS:** High Contrast mode uses a specific color palette designed for maximum visibility and readability. These values must be maintained precisely.

#### High Contrast Color Palette

```css
[data-theme="high-contrast"] {
    /* Background - Pure black for maximum contrast */
    --bg-gradient-start: #000000;
    --bg-gradient-end: #000000;
    --bg-primary: #000000;
    --bg-secondary: #1a1a1a;
    --bg-tertiary: #2a2a2a;
    --bg-input: #1a1a1a;

    /* Text - Bright green (#02fe05) for primary text */
    --text-primary: #02fe05;
    --text-secondary: #02fe05;
    --text-tertiary: #02fe05;

    /* Borders - High visibility colors */
    --border-primary: #ffff00;      /* Yellow */
    --border-secondary: #00ffff;    /* Cyan */
    --border-focus: #ff00ff;        /* Magenta */

    /* Buttons - Green for primary actions */
    --btn-primary-bg: #02fe05;
    --btn-primary-hover-bg: #02fe05;
    --btn-success-bg: #02fe05;
    --btn-success-hover-bg: #02fe05;
    --btn-secondary-bg: #ff6600;    /* Orange */
    --btn-tertiary-bg: #ff6600;

    /* Status colors */
    --error-bg: #ff0000;
    --error-border: #ff0000;
    --error-text: #02fe05;
    --info-bg: #0000ff;
    --info-border: #0000ff;
    --info-text: #02fe05;

    /* No shadows in high contrast mode */
    --shadow-light: none;
    --shadow-medium: none;

    /* STL Preview - CRITICAL SETTINGS FOR LOW VISION */
    --stl-mesh-color: #00ffff;              /* Bright cyan mesh */
    --stl-background: #000000;              /* Pure black background */
    --stl-ambient-light: #666666;           /* Reduced ambient to prevent washing out */
    --stl-directional-light: #e6e6e6;       /* Slightly dimmed for better contrast */
    --stl-ambient-intensity: 0.4;           /* Lower ambient intensity */
    --stl-directional-intensity: 0.8;       /* Controlled directional intensity */

    /* Scrollbar */
    --scrollbar-arrow-color: #02fe05;
}
```

#### High Contrast Color Semantics

| Color Code | Color Name | Usage |
|------------|------------|-------|
| `#02fe05` | Bright Green | Primary text, success states |
| `#fdfe00` | Yellow | Italic text, notes, secondary highlights |
| `#ffff00` | Pure Yellow | Borders, font size controls |
| `#00ffff` | Cyan | STL mesh, reset buttons, accent borders |
| `#ff00ff` | Magenta | Focus indicators |
| `#0201fe` | Blue | Generate button background |
| `#fd01fc` | Violet | Application title |
| `#ff6600` | Orange | Counter plate button, tertiary actions |
| `#000000` | Black | All backgrounds |

#### High Contrast Button Specifications

```css
/* Generate STL Button (Blue background, Yellow text) */
[data-theme="high-contrast"] #action-btn.generate-state {
    background: #0201fe !important;
    color: #fdfe00 !important;
    border: 2px solid #fdfe00 !important;
}

[data-theme="high-contrast"] #action-btn.generate-state:hover {
    border: 2px solid #02fe05 !important;  /* Green border on hover */
}

/* Download STL Button (Green background, Black text) */
[data-theme="high-contrast"] #action-btn.download-state {
    background: #02fe05 !important;
    color: #000000 !important;
    border: 2px solid #000000 !important;
}

[data-theme="high-contrast"] #action-btn.download-state:hover {
    border: 2px solid #ffff00 !important;  /* Yellow border on hover */
}

/* Disabled/Loading State */
[data-theme="high-contrast"] #action-btn:disabled {
    background: #666666 !important;
    color: #cccccc !important;
    border: 2px solid #999999 !important;
    cursor: not-allowed !important;
}
```

### 1.4 Theme Switching Logic

#### JavaScript Implementation

```javascript
// Theme configuration
const themes = ['dark', 'high-contrast', 'light'];
const themeIcons = {
    'dark': '🌙',
    'high-contrast': '⚡',
    'light': '🌞'
};
const themeNames = {
    'dark': 'Dark',
    'high-contrast': 'High Contrast',
    'light': 'Light'
};

let currentThemeIndex = 0;

// Always start in dark mode
applyTheme('dark');

function applyTheme(theme) {
    // Set the data-theme attribute on document root
    document.documentElement.setAttribute('data-theme', theme);

    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');
    const themeText = themeToggle.querySelector('.theme-text');

    // Calculate and display the NEXT theme (what clicking will change to)
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    const nextTheme = themes[nextIndex];

    // Button shows what will happen next, not current state
    themeIcon.textContent = themeIcons[nextTheme];
    themeText.textContent = themeNames[nextTheme];

    // Update ARIA label for screen readers
    themeToggle.setAttribute('aria-label',
        `Current theme: ${themeNames[theme]}. Click to switch to ${themeNames[nextTheme]} theme`);

    // Announce change to screen readers
    const announcement = document.createElement('div');
    announcement.className = 'sr-only';
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.textContent = `Theme changed to ${themeNames[theme]}`;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);

    // Update 3D scene colors
    update3DSceneColors();
}

// Theme toggle click handler
document.getElementById('theme-toggle').addEventListener('click', () => {
    currentThemeIndex = (currentThemeIndex + 1) % themes.length;
    applyTheme(themes[currentThemeIndex]);
});
```

### 1.5 Theme Persistence Policy

**IMPORTANT DESIGN DECISION:** Theme preferences are **NOT persisted** across sessions.

**Rationale:**
- Ensures consistent starting experience for all users
- Prevents confusion when users access from different devices
- Dark mode provides the best initial experience for most users
- Users with specific accessibility needs can quickly switch to High Contrast mode

**Implementation:**
```javascript
// Always start in dark mode; do not persist theme
applyTheme('dark');

// NO localStorage calls for theme preference
// Theme resets to dark on every page load
```

---

## 2. Font Size Adjustment System

### 2.1 Font Size Scale

The font size system uses a **predefined scale** of percentage values that apply to the root `<html>` element:

```javascript
const fontSizes = [75, 87.5, 100, 112.5, 125, 150, 175, 200];
//                  ↑    ↑     ↑     ↑      ↑    ↑    ↑    ↑
//               index: 0    1     2     3      4    5    6    7
//                    75%  87.5% 100%  112.5% 125% 150% 175% 200%
```

| Index | Percentage | Description |
|-------|------------|-------------|
| 0 | 75% | Minimum size |
| 1 | 87.5% | Small |
| 2 | 100% | **Default** (standard browser size) |
| 3 | 112.5% | Slightly enlarged |
| 4 | 125% | Medium enlargement |
| 5 | 150% | Large |
| 6 | 175% | Extra large |
| 7 | 200% | Maximum size |

### 2.2 Font Size Controls UI

```
┌─────────────────────────────────────────┐
│  [ A- ]  [ 100 ]  [ A+ ]  [ Reset ]     │
│    ↓        ↓        ↓        ↓         │
│ Decrease  Display  Increase  Reset      │
│           (shows %)          to 100%    │
└─────────────────────────────────────────┘
```

#### HTML Structure

```html
<div class="font-size-controls" role="group" aria-label="Font size controls">
    <button id="font-decrease" class="font-size-btn"
            aria-label="Decrease font size">A-</button>
    <span id="current-font-size" class="font-size-display"
          aria-live="polite">100</span>
    <button id="font-increase" class="font-size-btn"
            aria-label="Increase font size">A+</button>
    <button id="font-reset" class="font-size-btn reset-btn"
            aria-label="Reset font size to default">Reset</button>
</div>
```

### 2.3 Font Size Logic

```javascript
let currentFontSizeIndex = 2; // Start at 100%

// Always start at default 100%; do not persist font size
currentFontSizeIndex = 2;

function applyFontSize(sizeIndex) {
    const size = fontSizes[sizeIndex];

    // Apply to root element - all rem/em units scale accordingly
    document.documentElement.style.fontSize = size + '%';

    // Update display
    document.getElementById('current-font-size').textContent = size;
    currentFontSizeIndex = sizeIndex;

    // Screen reader announcement
    const announcement = document.createElement('div');
    announcement.className = 'sr-only';
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.textContent = `Font size changed to ${size}%`;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);
}

// Initialize
applyFontSize(currentFontSizeIndex);

// Event listeners
document.getElementById('font-decrease').addEventListener('click', () => {
    if (currentFontSizeIndex > 0) {
        applyFontSize(currentFontSizeIndex - 1);
    }
});

document.getElementById('font-increase').addEventListener('click', () => {
    if (currentFontSizeIndex < fontSizes.length - 1) {
        applyFontSize(currentFontSizeIndex + 1);
    }
});

document.getElementById('font-reset').addEventListener('click', () => {
    applyFontSize(2); // Reset to 100%
});
```

### 2.4 Screen Reader Announcements

Both theme changes and font size changes announce to screen readers using a dynamically created `aria-live` region:

```javascript
// Pattern for announcements
const announcement = document.createElement('div');
announcement.className = 'sr-only';           // Visually hidden
announcement.setAttribute('role', 'status');
announcement.setAttribute('aria-live', 'polite');
announcement.textContent = 'Announcement text here';
document.body.appendChild(announcement);
setTimeout(() => announcement.remove(), 1000);  // Clean up after 1 second
```

**CSS for Screen Reader Only Content:**
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

## 3. STL Preview Panel

### 3.1 Three.js Scene Configuration

The STL preview uses Three.js for 3D rendering with the following configuration:

```javascript
function init3D() {
    const isMobile = window.innerWidth <= 768;

    // Renderer configuration
    renderer = new THREE.WebGLRenderer({
        antialias: !isMobile,  // Disable antialiasing on mobile for performance
        powerPreference: isMobile ? "low-power" : "high-performance"
    });

    const initW = viewer.clientWidth;
    const initH = viewer.clientHeight || 420;
    renderer.setSize(initW, initH, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 2 : 3));

    // Scene setup
    scene = new THREE.Scene();

    // Camera configuration
    camera = new THREE.PerspectiveCamera(45, initW / initH, 0.1, 1000);
    camera.position.set(0, 0, 120);
    camera.up.set(0, 1, 0);  // Y-up orientation
    camera.lookAt(0, 0, 0);

    // Add camera to scene for attached lights
    scene.add(camera);

    // Orbit controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = isMobile ? 0.5 : 1.0;
    controls.zoomSpeed = isMobile ? 0.8 : 1.2;
    controls.panSpeed = isMobile ? 0.5 : 0.8;

    // Touch controls
    controls.touches = {
        ONE: THREE.TOUCH.ROTATE,
        TWO: THREE.TOUCH.DOLLY_PAN
    };
}
```

### 3.2 Theme-Aware Colors and Lighting

The 3D scene colors are read from CSS variables and applied dynamically:

```javascript
// Get theme colors from CSS variables
const styles = getComputedStyle(document.documentElement);
const stlBackground = styles.getPropertyValue('--stl-background').trim() || '#f1f5f9';
const stlAmbientLight = styles.getPropertyValue('--stl-ambient-light').trim() || '#888888';
const stlDirectionalLight = styles.getPropertyValue('--stl-directional-light').trim() || '#ffffff';
const stlMeshColor = styles.getPropertyValue('--stl-mesh-color').trim() || '#6699cc';
const stlAmbientIntensity = parseFloat(styles.getPropertyValue('--stl-ambient-intensity').trim()) || 0.5;
const stlDirectionalIntensity = parseFloat(styles.getPropertyValue('--stl-directional-intensity').trim()) || 1.0;

// Apply to scene
scene.background = new THREE.Color(stlBackground);
```

#### STL Preview Color Values by Theme

| Variable | Light Mode | Dark Mode | High Contrast |
|----------|------------|-----------|---------------|
| `--stl-mesh-color` | `#6699cc` (Steel Blue) | `#90cdf4` (Light Blue) | `#00ffff` (Bright Cyan) |
| `--stl-background` | `#f1f5f9` (Light Gray) | `#2d3748` (Dark Gray) | `#000000` (Pure Black) |
| `--stl-ambient-light` | `#888888` | `#666666` | `#666666` |
| `--stl-directional-light` | `#ffffff` | `#ffffff` | `#e6e6e6` |
| `--stl-ambient-intensity` | `0.5` | `0.6` | `0.4` |
| `--stl-directional-intensity` | `1.0` | `0.9` | `0.8` |

### 3.3 High Contrast Mode Lighting

**CRITICAL FOR LOW VISION USERS:** High contrast mode uses a specialized three-point lighting setup to maximize detail visibility:

```javascript
if (currentTheme === 'high-contrast') {
    // KEY LIGHT: 45° horizontal, 30° vertical (right side) - camera-relative
    // Provides primary illumination and shadow definition
    directionalLight.position.set(0.707, 0.5, 0.612).normalize();
    camera.add(directionalLight);

    // FILL LIGHT: 45° horizontal, 15° vertical (left side)
    // Softens shadows without eliminating them
    const fillLight = new THREE.DirectionalLight(
        new THREE.Color(stlDirectionalLight),
        stlDirectionalIntensity * 0.4  // 40% of key light intensity
    );
    fillLight.position.set(-0.707, 0.259, 0.659).normalize();
    camera.add(fillLight);

    // BACK LIGHT: Subtle edge definition
    const backLight = new THREE.DirectionalLight(
        new THREE.Color(stlDirectionalLight),
        stlDirectionalIntensity * 0.2  // 20% of key light intensity
    );
    backLight.position.set(0, 0.5, -0.866).normalize();
    camera.add(backLight);
} else {
    // Standard two-point lighting for other themes
    directionalLight.position.set(0.707, 0.5, 0.612).normalize();
    camera.add(directionalLight);

    const fillLight = new THREE.DirectionalLight(
        new THREE.Color(stlDirectionalLight),
        stlDirectionalIntensity * 0.3
    );
    fillLight.position.set(-0.5, 0.259, 0.659).normalize();
    camera.add(fillLight);
}

// Ambient light for all themes
scene.add(new THREE.AmbientLight(
    new THREE.Color(stlAmbientLight),
    stlAmbientIntensity
));
```

#### High Contrast Material Properties

```javascript
if (currentTheme === 'high-contrast') {
    mesh.material.specular = new THREE.Color(0xffffff);  // White specular highlights
    mesh.material.shininess = 300;  // Higher shininess for sharper highlights
} else {
    mesh.material.specular = new THREE.Color(0x111111);  // Standard specular
    mesh.material.shininess = 200;  // Standard shininess
}
```

### 3.4 Camera and Controls

#### 3.4.1 CAMERA_SETTINGS Global Configuration

The application uses a centralized `CAMERA_SETTINGS` object to control the initial camera position for each shape type. This allows easy adjustment of the default viewing angle without modifying multiple code locations.

**Location in Code:** Search for `CAMERA_SETTINGS` in `public/index.html` (near line 2890)

```javascript
// ═══════════════════════════════════════════════════════════════════════════════
// CAMERA SETTINGS - Central configuration for STL preview camera positions
// ═══════════════════════════════════════════════════════════════════════════════
const CAMERA_SETTINGS = {
    // Card shape camera settings (standard flat plate)
    CARD: {
        position: { x: 0, y: 0, z: 120 },   // Camera on +Z axis, looking at origin
        up: { x: 0, y: 1, z: 0 },           // Y-axis is up
        target: { x: 0, y: 0, z: 0 },       // Look at origin
        fov: 45,                            // Field of view in degrees
        near: 0.1,                          // Near clipping plane
        far: 1000                           // Far clipping plane
    },
    // Cylinder shape camera settings (cylindrical surface)
    // Camera positioned to view the indicator shapes (triangle/rectangle) side
    CYLINDER: {
        position: { x: -120, y: 0, z: 0 },  // Camera on -X axis (views indicator side)
        up: { x: 0, y: 0, z: 1 },           // Z-axis is up (cylinder axis)
        target: { x: 0, y: 0, z: 0 },       // Look at origin
        fov: 45,                            // Field of view in degrees
        near: 0.1,                          // Near clipping plane
        far: 1000                           // Far clipping plane
    }
};
```

#### 3.4.2 Coordinate System Reference

| Shape Type | Up Axis | Camera Default Position | Notes |
|------------|---------|------------------------|-------|
| **Card** | Y-axis (0,1,0) | (0, 0, 120) on +Z axis | Camera looks straight at the flat plate |
| **Cylinder** | Z-axis (0,0,1) | (-120, 0, 0) on -X axis | Camera views indicator shapes side |

**Cylinder Coordinate System:**
- The cylinder's central axis runs along the **Z-axis**
- The cylinder is centered at the origin (0, 0, 0)
- Camera orbits around the Z-axis in the XY plane

#### 3.4.3 How to Adjust the Initial Camera View

**To rotate the cylinder's initial view around its vertical axis:**

1. Modify `CAMERA_SETTINGS.CYLINDER.position.x` and `.y` values
2. The camera distance from origin (120 by default) controls zoom level
3. Use these position patterns for common rotations:

| Desired View | Position Values | Description |
|--------------|-----------------|-------------|
| View from -X axis | `{ x: -120, y: 0, z: 0 }` | **Current default** - Views indicator shapes |
| View from +X axis | `{ x: 120, y: 0, z: 0 }` | Opposite side (braille dots facing camera) |
| View from +Y axis | `{ x: 0, y: 120, z: 0 }` | 90° clockwise rotation |
| View from -Y axis | `{ x: 0, y: -120, z: 0 }` | 90° counter-clockwise rotation |
| View from corner | `{ x: 85, y: 85, z: 0 }` | 45° angle (diagonal view) |

**To adjust zoom level:**
- Increase position values (e.g., 150) to zoom out
- Decrease position values (e.g., 80) to zoom in

**To rotate the card's initial view:**
- Modify `CAMERA_SETTINGS.CARD.position` values similarly
- Cards use Y-up orientation, so adjust X and Y for rotation

#### 3.4.4 Camera Implementation Details

```javascript
// Camera settings usage in init3D()
const defaultCam = CAMERA_SETTINGS.CARD;
camera = new THREE.PerspectiveCamera(defaultCam.fov, initW / initH, defaultCam.near, defaultCam.far);
camera.position.set(defaultCam.position.x, defaultCam.position.y, defaultCam.position.z);
camera.up.set(defaultCam.up.x, defaultCam.up.y, defaultCam.up.z);
camera.lookAt(defaultCam.target.x, defaultCam.target.y, defaultCam.target.z);

// When loading STL, camera is repositioned based on shape type
if (isCylinder) {
    const cylCam = CAMERA_SETTINGS.CYLINDER;
    camera.up.set(cylCam.up.x, cylCam.up.y, cylCam.up.z);
    camera.position.set(cylCam.position.x, cylCam.position.y, cylCam.position.z);
    // ... rest of cylinder setup
} else {
    const cardCam = CAMERA_SETTINGS.CARD;
    camera.position.set(cardCam.position.x, cardCam.position.y, cardCam.position.z);
    // ... rest of card setup
}
```

#### 3.4.5 OrbitControls Configuration

```javascript
// OrbitControls settings
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// For cylinders: panning orthogonal to world up (Z-up)
controls.screenSpacePanning = false;

// For cards: screen-space panning (Y-up)
controls.screenSpacePanning = true;
```

### 3.5 Mobile Optimizations

```javascript
const isMobile = window.innerWidth <= 768;

// Renderer optimizations
renderer = new THREE.WebGLRenderer({
    antialias: !isMobile,                           // No AA on mobile
    powerPreference: isMobile ? "low-power" : "high-performance"
});
renderer.setPixelRatio(Math.min(devicePixelRatio, isMobile ? 2 : 3));

// Control speed adjustments
controls.rotateSpeed = isMobile ? 0.5 : 1.0;
controls.zoomSpeed = isMobile ? 0.8 : 1.2;
controls.panSpeed = isMobile ? 0.5 : 0.8;
```

### 3.6 Dynamic Theme Updates

When the theme changes, the 3D scene is updated dynamically:

```javascript
function update3DSceneColors() {
    if (scene && renderer) {
        // Get new theme colors
        const styles = getComputedStyle(document.documentElement);
        // ... extract all color variables ...

        // Update scene background
        scene.background = new THREE.Color(stlBackground);

        // Remove existing lights
        const sceneLightsToRemove = scene.children.filter(child =>
            child instanceof THREE.DirectionalLight ||
            child instanceof THREE.AmbientLight
        );
        sceneLightsToRemove.forEach(light => scene.remove(light));

        const cameraLightsToRemove = camera.children.filter(child =>
            child instanceof THREE.DirectionalLight
        );
        cameraLightsToRemove.forEach(light => camera.remove(light));

        // Rebuild lighting based on new theme
        // ... (theme-specific lighting setup) ...

        // Update mesh material
        if (mesh && mesh.material) {
            mesh.material.color = new THREE.Color(stlMeshColor);
            mesh.material.needsUpdate = true;
        }

        // Force re-render
        renderer.render(scene, camera);
    }
}
```

### 3.7 STL Preview Label

A clarifying label is displayed as an **overlay at the top** of the STL preview panel to help users understand its purpose. This was added because some users were confused and attempted to type text into the preview area. The label is positioned as a top-layer overlay to ensure maximum visibility.

#### HTML Structure

```html
<!-- Viewer Container with Overlay Label -->
<div class="viewer-container">
    <!-- STL Preview Label - Positioned as overlay at top of viewer -->
    <div class="stl-preview-label" id="stl-preview-label" role="note" aria-label="STL Preview information">
        <strong>3D STL Preview</strong> — Interactive preview only (drag to rotate, scroll to zoom)
    </div>
    <div id="viewer" role="img" ...>
        <!-- 3D viewer content -->
    </div>
</div>
```

#### CSS Styling

```css
/* Viewer Container - wraps viewer and overlay label */
.viewer-container {
    position: relative;
    width: 100%;
}

/* STL Preview Label - Overlay at top of viewer */
.stl-preview-label {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 10;
    text-align: center;
    padding: 0.5em 0.75em;
    font-size: 0.85em;
    color: var(--text-secondary);
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px 8px 0 0;
    opacity: 0.95;
}

.stl-preview-label strong {
    color: var(--text-primary);
}

/* High contrast mode */
[data-theme="high-contrast"] .stl-preview-label {
    background: #1a1a1a;
    border: 2px solid #ffff00;
    color: #02fe05;
    opacity: 1;
}

[data-theme="high-contrast"] .stl-preview-label strong {
    color: #fdfe00;
}
```

#### Purpose

The label serves to:
- Clearly identify the panel as an STL preview (not a text input)
- Provide brief interaction instructions (drag to rotate, scroll to zoom)
- Reduce user confusion about the panel's purpose
- **Positioned at top as overlay** to maximize visibility without taking extra space below the viewer

### 3.8 Preview Display Settings (Brightness and Contrast)

User-adjustable brightness and contrast controls allow customization of how the 3D preview appears. These settings affect **only the visual preview** and do not modify the exported STL file.

**UI Pattern:** Non-cycling **stepper controls** (`−` / `+`) with live value displays. Buttons disable at bounds (levels 1 and 5) and reuse the font-size control styling for consistent keyboard and screen reader behavior.

#### Control Overview

| Setting | Purpose | Range | Default | Step Behavior |
|---------|---------|-------|---------|---------------|
| **Brightness** | Adjusts overall light intensity | 1-5 | 3 (Normal) | Non-cycling; +/- buttons disable at min/max |
| **Contrast** | Adjusts ambient vs directional light ratio | 1-5 | 3 (Normal) | Non-cycling; +/- buttons disable at min/max |

#### Brightness Levels

| Level | Name | Multiplier | Description |
|-------|------|------------|-------------|
| 1 | Very Dim | 0.6× | Significantly reduced lighting |
| 2 | Dim | 0.8× | Slightly reduced lighting |
| 3 | Normal | 1.0× | **Default** - Base theme lighting |
| 4 | Bright | 1.2× | Slightly increased lighting |
| 5 | Very Bright | 1.4× | Significantly increased lighting |

#### Contrast Levels

| Level | Name | Ambient Ratio | Directional Ratio | Effect |
|-------|------|---------------|-------------------|--------|
| 1 | Very Low | 1.4× | 0.6× | Flat, even lighting |
| 2 | Low | 1.2× | 0.8× | Soft shadows |
| 3 | Normal | 1.0× | 1.0× | **Default** - Balanced lighting |
| 4 | High | 0.8× | 1.2× | More defined shadows |
| 5 | Very High | 0.6× | 1.4× | Dramatic lighting with strong shadows |

#### HTML Structure (Stepper)

```html
<!-- Preview Display Controls - Brightness and Contrast as +/- steppers -->
<div class="preview-display-controls" role="group" aria-label="Preview display settings">
    <div class="preview-control-group">
        <span class="preview-control-label" id="brightness-label">Brightness:</span>
        <div class="preview-stepper" role="group" aria-labelledby="brightness-label brightness-value">
            <button type="button" id="brightness-decrease" class="font-size-btn preview-stepper-btn"
                    aria-label="Decrease brightness" aria-controls="brightness-value">
                <span aria-hidden="true">−</span>
            </button>
            <span class="font-size-display preview-stepper-value" id="brightness-value" role="status" aria-live="polite">Normal</span>
            <button type="button" id="brightness-increase" class="font-size-btn preview-stepper-btn"
                    aria-label="Increase brightness" aria-controls="brightness-value">
                <span aria-hidden="true">+</span>
            </button>
        </div>
    </div>

    <div class="preview-control-group">
        <span class="preview-control-label" id="contrast-label">Contrast:</span>
        <div class="preview-stepper" role="group" aria-labelledby="contrast-label contrast-value">
            <button type="button" id="contrast-decrease" class="font-size-btn preview-stepper-btn"
                    aria-label="Decrease contrast" aria-controls="contrast-value">
                <span aria-hidden="true">−</span>
            </button>
            <span class="font-size-display preview-stepper-value" id="contrast-value" role="status" aria-live="polite">Normal</span>
            <button type="button" id="contrast-increase" class="font-size-btn preview-stepper-btn"
                    aria-label="Increase contrast" aria-controls="contrast-value">
                <span aria-hidden="true">+</span>
            </button>
        </div>
    </div>
</div>
```

#### JavaScript Implementation

```javascript
let previewBrightnessLevel = 3;
let previewContrastLevel = 3;

const BRIGHTNESS_MULTIPLIERS = { 1: 0.6, 2: 0.8, 3: 1.0, 4: 1.2, 5: 1.4 };
const CONTRAST_SETTINGS = {
    1: { ambientRatio: 1.4, directionalRatio: 0.6, specularIntensity: 0.3, shininessOffset: -80 },
    2: { ambientRatio: 1.2, directionalRatio: 0.8, specularIntensity: 0.6, shininessOffset: -40 },
    3: { ambientRatio: 1.0, directionalRatio: 1.0, specularIntensity: 1.0, shininessOffset: 0 },
    4: { ambientRatio: 0.8, directionalRatio: 1.2, specularIntensity: 1.3, shininessOffset: 40 },
    5: { ambientRatio: 0.6, directionalRatio: 1.4, specularIntensity: 1.6, shininessOffset: 80 }
};

const brightnessLevelNames = { 1: 'Very Dim', 2: 'Dim', 3: 'Normal', 4: 'Bright', 5: 'Very Bright' };
const contrastLevelNames   = { 1: 'Very Low', 2: 'Low', 3: 'Normal', 4: 'High', 5: 'Very High' };

const clampPreviewLevel = level => Math.min(5, Math.max(1, parseInt(level, 10) || 3));

function updatePreviewDisplaySettings() {
    // Applies brightness/contrast multipliers to lights and mesh material.
    // See implementation in templates/public index scripts for full logic.
}

function updateBrightnessStepper() {
    const name = brightnessLevelNames[previewBrightnessLevel];
    const percent = Math.round((BRIGHTNESS_MULTIPLIERS[previewBrightnessLevel] || 1) * 100);
    const value = document.getElementById('brightness-value');
    value.textContent = `${name}`;
    value.setAttribute('title', `${percent}% of base lighting`);

    const dec = document.getElementById('brightness-decrease');
    const inc = document.getElementById('brightness-increase');
    dec.disabled = previewBrightnessLevel <= 1;
    inc.disabled = previewBrightnessLevel >= 5;
    dec.setAttribute('aria-label', `Decrease brightness (current ${name})`);
    inc.setAttribute('aria-label', `Increase brightness (current ${name})`);
}

function applyPreviewBrightness(level) {
    previewBrightnessLevel = clampPreviewLevel(level);
    updatePreviewDisplaySettings();
    updateBrightnessStepper();
}

function updateContrastStepper() {
    const name = contrastLevelNames[previewContrastLevel];
    const ratios = CONTRAST_SETTINGS[previewContrastLevel];
    const value = document.getElementById('contrast-value');
    value.textContent = name;
    value.setAttribute('title', `${ratios.ambientRatio}× ambient / ${ratios.directionalRatio}× directional`);

    const dec = document.getElementById('contrast-decrease');
    const inc = document.getElementById('contrast-increase');
    dec.disabled = previewContrastLevel <= 1;
    inc.disabled = previewContrastLevel >= 5;
    dec.setAttribute('aria-label', `Decrease contrast (current ${name})`);
    inc.setAttribute('aria-label', `Increase contrast (current ${name})`);
}

function applyPreviewContrast(level) {
    previewContrastLevel = clampPreviewLevel(level);
    updatePreviewDisplaySettings();
    updateContrastStepper();
}

document.getElementById('brightness-decrease').addEventListener('click', () => {
    if (previewBrightnessLevel > 1) applyPreviewBrightness(previewBrightnessLevel - 1);
});
document.getElementById('brightness-increase').addEventListener('click', () => {
    if (previewBrightnessLevel < 5) applyPreviewBrightness(previewBrightnessLevel + 1);
});
document.getElementById('contrast-decrease').addEventListener('click', () => {
    if (previewContrastLevel > 1) applyPreviewContrast(previewContrastLevel - 1);
});
document.getElementById('contrast-increase').addEventListener('click', () => {
    if (previewContrastLevel < 5) applyPreviewContrast(previewContrastLevel + 1);
});

updateBrightnessStepper();
updateContrastStepper();
```

#### CSS Styling

```css
/* Preview Display Controls Container - Stepper style */
.preview-display-controls {
    width: 100%;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 1em;
    padding: 0.75em;
    margin-top: 0.5em;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    flex-wrap: wrap;
}

.preview-control-group {
    display: flex;
    align-items: center;
    gap: 0.75em;
    flex-wrap: wrap;
}

.preview-control-label {
    font-size: 0.85em;
    font-weight: 500;
    color: var(--text-primary);
}

.preview-controls-title {
    font-weight: 600;
    font-size: 0.9em;
    color: var(--text-primary);
    white-space: nowrap;
}

.preview-stepper {
    display: flex;
    align-items: center;
    gap: 0.4em;
    flex-wrap: wrap;
}

.preview-stepper .font-size-btn {
    min-width: 2.5em;
    padding: 0.4em 0.65em;
}

.preview-stepper-value {
    min-width: 9.5em;
    text-align: center;
}

[data-theme="high-contrast"] .preview-controls-title,
[data-theme="high-contrast"] .preview-control-label {
    color: #02fe05 !important;
}

@media (max-width: 768px) {
    .preview-display-controls {
        padding: 0.5em;
        flex-direction: column;
        align-items: flex-start;
    }

    .preview-control-group {
        width: 100%;
        flex-wrap: wrap;
    }

    .preview-stepper {
        width: 100%;
    }

    .preview-stepper .font-size-btn {
        flex: 1;
        min-width: unset;
    }

    .preview-stepper-value {
        flex: 1 1 auto;
    }
}
```

#### Integration with Theme System

The brightness and contrast settings work in conjunction with the theme system:

1. **Base Values from Theme**: Each theme provides base ambient and directional light intensities via CSS variables
2. **User Adjustments Applied**: Brightness/contrast multipliers are applied on top of theme values
3. **Theme Changes Preserve Settings**: When the theme changes, current brightness/contrast settings are reapplied

```javascript
// In update3DSceneColors():
// After rebuilding lights for new theme...
if (typeof storeOriginalLightIntensities === 'function') {
    storeOriginalLightIntensities();
}
if (typeof updatePreviewDisplaySettings === 'function') {
    updatePreviewDisplaySettings();
}
```

#### Accessibility Features

- **ARIA Labels**: Dynamic labels on +/- buttons reflect current level and action (e.g., "Decrease brightness (current Normal)")
- **Live Value Announcements**: Value displays use `role="status"` + `aria-live="polite"` to announce changes without duplicate overlays
- **Keyboard Navigation**: Native buttons with disabled states at bounds; Enter/Space activates, Shift+Tab/Tab respects grouping
- **Focus Indicators**: Clear 3px focus outlines with offset for visibility
- **High Contrast Mode**: Labels inherit high-contrast colors; buttons reuse font-size control styling that already meets WCAG AA

#### Non-Persistence Policy

Brightness and contrast settings are **not persisted** across sessions. This is consistent with the theme and font size policies:
- Settings reset to defaults (level 3) on page load
- Provides consistent starting experience for all users
- Users with specific needs can quickly adjust as needed

### 3.9 WebGL Context Recovery

The application implements resilient WebGL context loss and recovery handling for stability, especially on Safari/iOS where context loss may occur when tabs are backgrounded or when the system is under memory pressure.

#### Feature Detection

Before initializing the 3D viewer, the application checks for WebGL support:

```javascript
function checkWebGLSupport() {
    try {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        return !!context;
    } catch (e) {
        return false;
    }
}
```

If WebGL is not available, a user-friendly error message is displayed:

```html
<div class="webgl-error" role="alert">
    <strong>WebGL Not Available</strong>
    <p>Your browser does not support WebGL, which is required for the 3D preview.
    You can still generate and download STL files.</p>
    <p>Try updating your browser or enabling hardware acceleration in your browser settings.</p>
</div>
```

#### Context Loss Handling

Event listeners are attached to the WebGL canvas to handle context loss and recovery:

```javascript
renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault(); // Allow recovery
    console.warn('WebGL context lost');

    // Show user-friendly message
    const msg = document.createElement('div');
    msg.id = 'webgl-recovery-msg';
    msg.className = 'webgl-recovery';
    msg.setAttribute('role', 'alert');
    msg.innerHTML = `
        <strong>3D Preview Paused</strong>
        <p>The 3D viewer was interrupted. It will automatically recover.</p>
    `;
    viewer.appendChild(msg);
}, false);

renderer.domElement.addEventListener('webglcontextrestored', () => {
    console.log('WebGL context restored');

    // Remove recovery message
    const msg = document.getElementById('webgl-recovery-msg');
    if (msg) msg.remove();

    // Re-initialize scene
    reinitialize3DScene();

    // Reload last STL if available
    if (lastGeneratedSTLUrl) {
        // Reload the STL mesh
    }
}, false);
```

#### Recovery CSS

```css
.webgl-error,
.webgl-recovery {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--bg-secondary);
    border: 2px solid var(--border-primary);
    border-radius: 8px;
    padding: 1.5em;
    text-align: center;
    max-width: 80%;
    z-index: 20;
}

[data-theme="high-contrast"] .webgl-error,
[data-theme="high-contrast"] .webgl-recovery {
    background: #1a1a1a;
    border-color: #ffff00;
    color: #02fe05;
}
```

#### Browser Compatibility

| Browser | Context Loss Behavior | Recovery Support |
|---------|----------------------|------------------|
| Chrome | Rare (GPU reset) | ✅ Automatic |
| Firefox | Rare | ✅ Automatic |
| Safari Desktop | Occasional (tab backgrounding) | ✅ Automatic |
| Safari iOS | Common (M3/M4 chips, memory pressure) | ✅ Automatic |
| Edge | Rare (GPU reset) | ✅ Automatic |

---

## 4. Accessibility Features

### 4.1 Skip Link Navigation

A skip link is provided for keyboard users to bypass the header and jump directly to the main content:

```html
<a href="#main-content" class="skip-link" tabindex="0">Skip to main content</a>
```

```css
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--border-focus);
    color: white;
    padding: 8px 16px;
    text-decoration: none;
    border-radius: 0 0 8px 0;
    z-index: 1000;
    transition: top 0.3s;
}

.skip-link:focus {
    top: 0;  /* Becomes visible when focused */
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}
```

### 4.2 Focus Indicators

All interactive elements have enhanced focus indicators for keyboard navigation:

```css
/* Standard focus indicator */
button:focus,
input:focus,
select:focus,
textarea:focus,
a:focus {
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}

/* Keyboard-specific focus (more visible) */
*:focus-visible {
    outline: 3px solid var(--border-focus) !important;
    outline-offset: 2px !important;
}
```

### 4.3 Screen Reader Support

**ARIA Labels and Descriptions:**
```html
<!-- Font size controls with grouping -->
<div class="font-size-controls" role="group" aria-label="Font size controls">
    <button aria-label="Decrease font size">A-</button>
    <span aria-live="polite">100</span>
    <button aria-label="Increase font size">A+</button>
    <button aria-label="Reset font size to default">Reset</button>
</div>

<!-- Theme toggle with dynamic ARIA label -->
<button id="theme-toggle"
        aria-label="Current theme: Dark. Click to switch to High Contrast theme">
    ...
</button>

<!-- Line inputs with descriptions -->
<input type="text" id="line1"
       aria-describedby="line1-help">
<span id="line1-help" class="sr-only">Maximum 50 characters for line 1</span>
```

### 4.4 Touch and Mobile Accessibility

```css
/* Minimum touch target size (48px) */
@media (max-width: 768px) {
    button {
        min-height: 48px;
        min-width: 48px;
    }

    input[type="text"],
    input[type="number"] {
        min-height: 48px;
        font-size: 16px;  /* Prevents iOS zoom on focus */
    }
}

/* Disable double-tap zoom on buttons */
button {
    touch-action: manipulation;
}

/* Prevent text selection on UI elements */
button {
    -webkit-touch-callout: none;
    -webkit-user-select: none;
    user-select: none;
}
```

### 4.5 Toggle Button ARIA Requirements

All toggle buttons (Info dropdown, Expert Mode toggle, and submenu toggles) implement proper ARIA attributes to communicate their state to screen readers.

#### Required ARIA Attributes

```html
<!-- Info Toggle -->
<button type="button" id="info-toggle" class="info-toggle-btn"
        aria-expanded="false" aria-controls="info-content">
    <span id="info-toggle-text">Directions:</span>
    <span id="info-toggle-icon" aria-hidden="true">▼</span>
</button>
<div id="info-content" class="info-content" style="display: none;">
    <!-- Content -->
</div>

<!-- Expert Mode Toggle -->
<button type="button" id="expert-toggle" class="expert-toggle-btn"
        aria-expanded="false" aria-controls="expert-settings">
    <span id="expert-toggle-text">Show Expert Mode</span>
    <span id="expert-toggle-icon" aria-hidden="true">▼</span>
</button>
<div id="expert-settings" class="expert-settings" style="display: none;">
    <!-- Content -->
</div>
```

#### Key ARIA Requirements

| Attribute | Purpose | Values |
|-----------|---------|--------|
| `aria-expanded` | Indicates whether controlled element is expanded | `"true"` or `"false"` |
| `aria-controls` | Links button to the element it controls | ID of controlled element |
| `aria-hidden="true"` | Hides decorative icons from screen readers | Applied to icon spans |

#### JavaScript State Management

Toggle buttons must update `aria-expanded` dynamically when clicked:

```javascript
expertToggleBtn.addEventListener('click', () => {
    const isVisible = expertSettings.style.display !== 'none';
    expertSettings.style.display = isVisible ? 'none' : 'block';
    expertToggleText.textContent = isVisible ? 'Show Expert Mode' : 'Hide Expert Mode';
    expertToggleIcon.textContent = isVisible ? '▼' : '▲';
    expertToggleBtn.classList.toggle('active', !isVisible);

    // REQUIRED: Update ARIA state
    expertToggleBtn.setAttribute('aria-expanded', String(!isVisible));

    // Optional: Focus management when opening
    if (!isVisible) {
        const firstFocusable = expertSettings.querySelector(
            'input, select, button, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }
});
```

#### Screen Reader Announcements

When `aria-expanded` changes, screen readers automatically announce the new state:
- "expanded" when `aria-expanded="true"`
- "collapsed" when `aria-expanded="false"`

### 4.6 Reduced Motion Support

The application respects the user's operating system preference for reduced motion (`prefers-reduced-motion` media query) in compliance with WCAG 2.1 Success Criterion 2.3.3.

#### CSS Implementation

All animations and transitions are disabled when reduced motion is preferred:

```css
/* Reduced Motion Support - WCAG 2.1 Requirement */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }

    /* Specifically disable theme transition animations */
    body,
    .container,
    button,
    input,
    select,
    .preview-section,
    .form-section {
        transition: none !important;
    }
}
```

#### JavaScript Implementation

The 3D preview animation loop also respects reduced motion preferences:

```javascript
// Check reduced motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let animationEnabled = !prefersReducedMotion.matches;

function animate() {
    if (animationEnabled) {
        requestAnimationFrame(animate);
    }
    controls && controls.update();
    render();
}

function updateRenderingMode() {
    animationEnabled = !prefersReducedMotion.matches;
    if (!animationEnabled && controls) {
        // Stop continuous animation loop, render on demand only
        controls.addEventListener('change', () => {
            render();
        });
    } else if (animationEnabled) {
        // Resume continuous animation
        animate();
    }
}

prefersReducedMotion.addEventListener('change', updateRenderingMode);
updateRenderingMode();
```

#### Affected Elements

| Element Type | Normal Behavior | Reduced Motion Behavior |
|--------------|----------------|-------------------------|
| Theme transitions | 0.3s fade | Instant |
| Button hover effects | Animated | Instant |
| 3D preview rotation | Continuous animation loop | Render on user interaction only |
| Scroll behavior | Smooth scrolling | Instant jump |

#### How to Test

**On Windows:**
1. Open Settings → Accessibility → Visual effects
2. Toggle "Animation effects" off

**On macOS:**
1. System Settings → Accessibility → Display
2. Toggle "Reduce motion" on

**On iOS:**
1. Settings → Accessibility → Motion
2. Toggle "Reduce Motion" on

---

## 5. Scrollbar Customization

### 5.1 Form Section Scrollbar

The form section (right column on desktop) has a custom scrollbar for visibility:

```css
.form-section {
    scrollbar-gutter: stable;        /* Reserve space for scrollbar */
    scrollbar-width: auto;           /* Firefox */
    scrollbar-color: #3182ce #e2e8f0; /* Firefox: thumb track */
}

/* WebKit browsers */
.form-section::-webkit-scrollbar {
    width: var(--scrollbar-width);   /* 18px */
}

.form-section::-webkit-scrollbar-track {
    background: #e2e8f0;
    border-radius: 8px;
    border: 2px solid #3182ce;
}

.form-section::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #4299e1, #3182ce);
    border-radius: 10px;
    border: 2px solid #ffffff;
    box-shadow: 0 3px 6px rgba(49, 130, 206, 0.4);
}

.form-section::-webkit-scrollbar-thumb:hover {
    background: #2563eb;
}
```

### 5.2 Global Page Scrollbar

```css
body::-webkit-scrollbar {
    width: var(--global-scrollbar-width);  /* 13.5px (25% smaller than form) */
}

body::-webkit-scrollbar-track {
    background: var(--bg-tertiary);
    border-radius: 8px;
    border: 1px solid var(--border-secondary);
}

body::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--text-secondary), var(--text-primary));
    border-radius: 10px;
    border: 2px solid var(--bg-primary);
}
```

### 5.3 Theme-Specific Scrollbar Styles

**Dark Theme:**
```css
[data-theme="dark"] .form-section {
    scrollbar-color: #63b3ed #2d3748 !important;
}

[data-theme="dark"] .form-section::-webkit-scrollbar-track {
    background: #2d3748 !important;
    border: 1px solid #63b3ed !important;
}

[data-theme="dark"] .form-section::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #90cdf4, #63b3ed) !important;
    border: 2px solid #1a202c !important;
}
```

**High Contrast:**
```css
[data-theme="high-contrast"] .form-section {
    scrollbar-color: var(--text-secondary) var(--bg-tertiary) !important;
}

[data-theme="high-contrast"] .form-section::-webkit-scrollbar-track {
    background: var(--bg-tertiary) !important;
    border: 2px solid var(--border-secondary) !important;
}

[data-theme="high-contrast"] .form-section::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--text-secondary), var(--text-primary)) !important;
    box-shadow: none !important;
}
```

---

## 6. Button State Management

### 6.1 Action Button States

The main action button has two states: **Generate** and **Download**.

```javascript
// Generate state (blue, prompts user to create STL)
function resetToGenerateState() {
    actionBtn.textContent = 'Generate STL';
    actionBtn.className = 'generate-state';
    actionBtn.setAttribute('data-state', 'generate');
    actionBtn.setAttribute('aria-label', 'Generate STL file from entered text');
    actionBtn.style.opacity = '1';
    actionBtn.disabled = false;
}

// Download state (green, allows user to download generated STL)
function setToDownloadState() {
    actionBtn.textContent = 'Download STL';
    actionBtn.className = 'download-state';
    actionBtn.setAttribute('data-state', 'download');
    actionBtn.setAttribute('aria-label', 'Download generated STL file');
    actionBtn.style.opacity = '1';
    actionBtn.disabled = false;
}
```

**State Transitions:**
```
User enters text → Button shows "Generate STL" (generate-state)
                         ↓
User clicks "Generate STL" → Button shows "Generating..." (disabled)
                         ↓
Generation complete → Button shows "Download STL" (download-state)
                         ↓
User modifies any input → Button returns to "Generate STL" (generate-state)
```

### 6.2 High Contrast Button Styling

See Section 1.3 for complete high contrast button specifications.

---

## 7. Layout Responsiveness

### 7.1 Desktop Two-Column Layout

```css
.content-area {
    display: flex;
    gap: 2.5em;
    width: 100%;
}

/* Left Column - Preview (45% width) */
.preview-section {
    flex: 0 0 45%;
    position: sticky;
    top: 0;
}

/* Right Column - Form (55% width) */
.form-section {
    flex: 0 0 calc(55% - 2em);
    max-height: calc(100vh - 10em);
    overflow-y: scroll;
}
```

### 7.2 Mobile Stacked Layout

```css
@media (max-width: 768px) {
    .content-area {
        flex-direction: column;
        gap: 1.5em;
    }

    .preview-section {
        flex: none;
        width: 100%;
        height: auto;
    }

    .form-section {
        flex: 1;
        width: 100%;
        max-height: none;
    }

    #viewer {
        height: calc(40vh - 1em);  /* 40% of viewport on tablets */
    }
}

@media (max-width: 480px) {
    #viewer {
        height: calc(35vh - 1em);  /* 35% of viewport on phones */
    }
}
```

### 7.3 iOS Safe Area Handling

The application implements full iOS safe area support to prevent content from being hidden under device notches, the Dynamic Island, or the iOS address bar.

#### Viewport Meta Tag

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
```

The `viewport-fit=cover` attribute allows the app to extend into safe area insets.

#### CSS Safe Area Insets

```css
:root {
    /* iOS Safe Area Support */
    --vh: 1vh; /* Dynamic viewport height fallback */
}

body {
    /* Prevent content from being hidden under notch/Dynamic Island */
    padding-top: env(safe-area-inset-top);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
}

.form-section {
    /* Ensure bottom buttons are accessible (not hidden behind iOS toolbar) */
    padding-bottom: calc(1em + env(safe-area-inset-bottom));
}
```

#### Dynamic Viewport Height Support

iOS Safari's address bar can collapse/expand, changing the viewport height. The app handles this with both modern (`dvh`) and fallback (JavaScript) approaches:

```css
/* Dynamic viewport height for full-height layouts */
@supports (height: 100dvh) {
    .content-area {
        min-height: 100dvh;
    }
}

@supports not (height: 100dvh) {
    .content-area {
        min-height: calc(var(--vh, 1vh) * 100);
    }
}
```

#### JavaScript Viewport Height Handler

For browsers that don't support `dvh`, JavaScript dynamically updates the `--vh` custom property:

```javascript
// Dynamic viewport height fix for iOS Safari (address bar handling)
function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Set on load and resize
setVH();
window.addEventListener('resize', setVH);
window.addEventListener('orientationchange', setVH);

// Also handle visualViewport if available (more accurate on mobile)
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', setVH);
}
```

#### Safe Area Support Matrix

| Device Feature | CSS Solution | Fallback |
|----------------|-------------|----------|
| iPhone notch | `env(safe-area-inset-top)` | None needed (graceful) |
| Dynamic Island | `env(safe-area-inset-top)` | None needed (graceful) |
| Bottom gesture bar | `env(safe-area-inset-bottom)` | None needed (graceful) |
| Collapsing address bar | `100dvh` + JavaScript `--vh` | JavaScript only |

#### Testing on iOS

**Manual Testing Steps:**
1. Open app on iPhone with notch (iPhone X+) or Dynamic Island (iPhone 14 Pro+)
2. Verify top content is not hidden under notch/island
3. Verify bottom buttons are fully accessible (not cut off)
4. Scroll to bottom of form section and verify button row is visible
5. Rotate to landscape and verify all content remains accessible
6. Scroll up/down to collapse/expand address bar and verify layout adapts

---

## 8. Help Modal System

### 8.1 Overview

The Help Modal provides BANA-aligned business card guidance and application help through an accessible tabbed interface.

**Location:** `public/index.html` (added January 2026)

### 8.2 Modal Structure

```html
<div class="modal hidden" id="helpModal" role="dialog" aria-modal="true" aria-labelledby="helpModalTitle">
    <div class="modal-overlay" id="helpModalOverlay"></div>
    <div class="modal-content modal-large">
        <div class="modal-header">
            <h2 id="helpModalTitle">Help & Guide</h2>
            <button class="modal-close" id="helpModalClose" aria-label="Close help guide">...</button>
        </div>
        <div class="modal-body help-modal-body">
            <div class="help-tabs" role="tablist">...</div>
            <div class="help-panels">...</div>
        </div>
    </div>
</div>
```

### 8.3 Tab Panels

| Tab ID | Panel ID | Content |
|--------|----------|---------|
| `tab-quickstart` | `helpPanelQuickStart` | Getting started steps, basic layout |
| `tab-businesscard` | `helpPanelBusinessCard` | BANA priority guide, space-saving strategies |
| `tab-formatting` | `helpPanelFormatting` | Phone, email, web, name formatting tips |
| `tab-examples` | `helpPanelExamples` | Real-world BANA examples |
| `tab-resources` | `helpPanelResources` | Links to standards, credits |

### 8.4 Accessibility Features

| Feature | Implementation |
|---------|----------------|
| Focus Trap | Tab/Shift+Tab cycles within modal |
| Keyboard Navigation | Arrow keys navigate tabs, Escape closes modal |
| ARIA Roles | `role="dialog"`, `aria-modal="true"`, `role="tablist/tab/tabpanel"` |
| Focus Restoration | Returns focus to trigger element on close |
| Screen Reader | `aria-labelledby`, `aria-selected`, `aria-controls` |

### 8.5 JavaScript API

```javascript
// Open modal (default: quickstart tab)
window.openHelpModal('quickstart');

// Open modal to specific tab
window.openHelpModal('businesscard');

// Switch tabs programmatically
window.switchHelpTab('tab-formatting');
```

### 8.6 Trigger Buttons

**Location:** `.accessibility-controls-top` in title section

| Button | ID | Action |
|--------|-----|--------|
| GitHub Link | — | Opens GitHub repo in new tab |
| Help Button | `helpModalBtn` | Opens Help Modal |
| Info Panel Link | — | Calls `window.openHelpModal('quickstart')` |

### 8.7 CSS Classes

| Class | Purpose |
|-------|---------|
| `.modal` | Fixed full-screen overlay container |
| `.modal.hidden` | Hides modal (display: none) |
| `.modal-overlay` | Semi-transparent backdrop |
| `.modal-content` | Modal dialog box |
| `.modal-large` | Width: 90%, max-width: 800px |
| `.help-tabs` | Tab navigation container |
| `.help-tab` | Individual tab button |
| `.help-panel` | Tab panel content |
| `.help-table` | Styled table for help content |
| `.example-box` | Styled example container |

### 8.8 High Contrast Mode

| Element | High Contrast Style |
|---------|---------------------|
| Modal background | `#000` with `#ffff00` border |
| Tab text | `#02fe05` (green) |
| Active tab | `#ffff00` (yellow) with yellow bottom border |
| Links | `#00ffff` (cyan) |
| Table borders | `#ffff00` (yellow) |

### 8.9 Related Documentation

- [BUSINESS_CARD_TRANSLATION_GUIDE.md](../guides/BUSINESS_CARD_TRANSLATION_GUIDE.md) — Full in-depth guide linked from modal
- [ADA_ACCESSIBILITY_VALIDATION_SOP.md](../development/ADA_ACCESSIBILITY_VALIDATION_SOP.md) — Accessibility testing procedures

---

## 9. Design Rationale

### Why Dark Mode as Default

1. **Reduced Eye Strain** — Dark backgrounds are easier on the eyes, especially during extended use
2. **Power Efficiency** — Dark themes consume less power on OLED/AMOLED displays
3. **Focus on Content** — The 3D preview (main content) stands out better against dark backgrounds
4. **Consistency** — Users get the same starting experience regardless of system settings

### Why No Theme Persistence

1. **Accessibility First** — Users with visual impairments can quickly access High Contrast mode
2. **Device Independence** — Same experience across devices without sync complexity
3. **Predictable Behavior** — Users always know what to expect when loading the app

### Why Specific High Contrast Colors

The high contrast color palette follows WCAG AAA contrast requirements:

| Text Color | Background | Contrast Ratio |
|------------|------------|----------------|
| `#02fe05` (Green) | `#000000` (Black) | 15.4:1 (exceeds 7:1 AAA) |
| `#fdfe00` (Yellow) | `#000000` (Black) | 19.6:1 (exceeds 7:1 AAA) |
| `#00ffff` (Cyan) | `#000000` (Black) | 16.7:1 (exceeds 7:1 AAA) |

### Why Three-Point Lighting in High Contrast Mode

Low vision users benefit from enhanced depth perception:
- **Key Light** — Primary illumination from upper-right
- **Fill Light** — Prevents harsh shadows that obscure details
- **Back Light** — Edge definition helps distinguish the model from the background

---

## Appendix A: Complete Theme Toggle Button HTML

```html
<div class="theme-toggle-section" role="group" aria-labelledby="theme-label">
    <div id="theme-label" class="theme-label-box">
        <span class="theme-label-text">Change Theme to →</span>
    </div>
    <button id="theme-toggle" class="theme-toggle-btn"
            aria-label="Toggle theme"
            title="Toggle between light, dark, and high contrast themes">
        <span class="theme-icon" aria-hidden="true">⚡</span>
        <span class="theme-text">High Contrast</span>
    </button>
</div>
```

## Appendix B: Complete Font Size Controls HTML

```html
<div class="font-size-controls" role="group" aria-label="Font size adjustment">
    <button id="font-decrease" class="font-size-btn"
            aria-label="Decrease font size" title="Decrease font size">
        <span aria-hidden="true">A-</span>
        <span class="sr-only">Decrease font size</span>
    </button>
    <span class="font-size-display" aria-label="Current font size">
        <span id="current-font-size">100</span>%
    </span>
    <button id="font-increase" class="font-size-btn"
            aria-label="Increase font size" title="Increase font size">
        <span aria-hidden="true">A+</span>
        <span class="sr-only">Increase font size</span>
    </button>
    <button id="font-reset" class="font-size-btn reset-btn"
            aria-label="Reset font size to default" title="Reset font size to default">
        <span aria-hidden="true">⟲</span>
        <span class="sr-only">Reset font size</span>
    </button>
</div>
```

## Appendix C: CSS Transition for Theme Changes

```css
/* Smooth transitions between themes */
* {
    transition: background-color 0.3s ease,
                color 0.3s ease,
                border-color 0.3s ease;
    box-sizing: border-box;
}
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-06 | Initial specification document |
| 1.1 | 2024-12-06 | Cross-check verification completed; corrected skip link href from `#main-form` to `#main-content`; updated appendices to match actual implementation |
| 1.2 | 2024-12-06 | Added CAMERA_SETTINGS global configuration documentation in Section 3.4; expanded camera controls section with detailed instructions for adjusting initial view positions for cards and cylinders |
| 1.3 | 2025-12-08 | Added Section 3.7 (STL Preview Label) to clarify the preview panel's purpose; Added Section 3.8 (Preview Display Settings) documenting new brightness and contrast radio button controls for 3D preview customization |
| 1.4 | 2025-12-08 | Fixed Expert Toggle button active state contrast ratio: Changed background from `var(--border-focus)` to darker blues (`#1e4976` for light mode, `#1e5a8a` for dark mode) to meet WCAG AA 4.5:1 contrast requirement with white text |
| 1.5 | 2025-12-08 | **UI Enhancement:** (1) Moved STL Preview Label to top of preview panel as overlay with z-index for visibility; (2) Changed Brightness and Contrast controls from radio buttons to click-through toggle buttons (like Theme toggle) that cycle through levels 1→2→3→4→5→1 on each click |
| 1.6 | 2026-01-05 | Replaced brightness/contrast click-through toggles with +/- stepper controls, added live value display, and refreshed accessibility guidance |
| 1.7 | 2026-01-05 | Added critical warning section about HTML file locations — must edit `public/index.html` (served by Flask), not `templates/index.html` (legacy/not served) |
| 1.8 | 2026-01-05 | **Cross-Browser UI Hardening:** Added Section 3.9 (WebGL Context Recovery), Section 4.5 (Toggle Button ARIA Requirements), Section 4.6 (Reduced Motion Support), and Section 7.3 (iOS Safe Area Handling) to document new accessibility and cross-browser compatibility features |

---

## Appendix D: Cross-Check Verification Report

### Verification Summary

A full cross-check was performed between this specification document and the actual implementation in `public/index.html`. The following items were verified:

### ✅ Theme System (Section 1)

| Item | Status | Notes |
|------|--------|-------|
| Light mode CSS variables | ✅ PASS | All 30+ variables match exactly |
| Dark mode CSS variables | ✅ PASS | All variables match exactly |
| High contrast mode CSS variables | ✅ PASS | All critical colors verified |
| Theme cycle order (dark → high-contrast → light) | ✅ PASS | Implementation matches spec |
| Theme persistence policy (none) | ✅ PASS | Always starts in dark mode |
| High contrast button colors | ✅ PASS | Generate: #0201fe bg, #fdfe00 text; Download: #02fe05 bg |

### ✅ Font Size System (Section 2)

| Item | Status | Notes |
|------|--------|-------|
| Font size scale [75, 87.5, 100, 112.5, 125, 150, 175, 200] | ✅ PASS | Exact match |
| Default index = 2 (100%) | ✅ PASS | Verified in implementation |
| Font size persistence policy (none) | ✅ PASS | Always starts at 100% |
| Screen reader announcements | ✅ PASS | Uses aria-live regions |

### ✅ STL Preview Panel (Section 3)

| Item | Status | Notes |
|------|--------|-------|
| Three.js WebGLRenderer settings | ✅ PASS | Antialiasing disabled on mobile |
| Camera settings (45° FOV, position 0,0,120) | ✅ PASS | Exact match |
| OrbitControls damping (0.05) | ✅ PASS | Verified |
| Mobile control speeds (rotate: 0.5, zoom: 0.8, pan: 0.5) | ✅ PASS | Verified |
| High contrast three-point lighting | ✅ PASS | Key, fill, back lights configured |
| Light positions | ✅ PASS | Key: (0.707, 0.5, 0.612), Fill: (-0.707, 0.259, 0.659) |
| High contrast specular (shininess: 300) | ✅ PASS | Verified |
| Standard specular (shininess: 200) | ✅ PASS | Verified |

### ✅ Accessibility Features (Section 4)

| Item | Status | Notes |
|------|--------|-------|
| Skip link (`#main-content`) | ✅ PASS | *Fixed from #main-form* |
| Skip link CSS (top: -40px, focus: top: 0) | ✅ PASS | Verified |
| Focus indicators (3px outline, 2px offset) | ✅ PASS | Verified for all interactive elements |
| .sr-only CSS | ✅ PASS | Exact match |
| Touch targets (48px min on mobile) | ✅ PASS | Verified in media queries |

### ✅ Scrollbar Customization (Section 5)

| Item | Status | Notes |
|------|--------|-------|
| Form section scrollbar width (18px) | ✅ PASS | Uses CSS variable |
| Global scrollbar width (13.5px) | ✅ PASS | Uses CSS variable |
| Dark theme scrollbar colors | ✅ PASS | Gradient thumb, dark track |
| High contrast scrollbar | ✅ PASS | Uses theme variables |

### ✅ Button State Management (Section 6)

| Item | Status | Notes |
|------|--------|-------|
| Generate state (class: generate-state) | ✅ PASS | Verified |
| Download state (class: download-state) | ✅ PASS | Verified |
| State attribute (data-state) | ✅ PASS | Used for click handling |
| ARIA labels for each state | ✅ PASS | Dynamic updates verified |

### ✅ Layout Responsiveness (Section 7)

| Item | Status | Notes |
|------|--------|-------|
| Desktop: 45% preview / 55% form | ✅ PASS | flex: 0 0 45% and calc(55% - 2em) |
| Mobile breakpoint (768px) | ✅ PASS | Stack columns verified |
| Viewer height on tablet (40vh) | ✅ PASS | Verified |
| Viewer height on phone (35vh) | ✅ PASS | Verified in 480px breakpoint |

### Corrections Made During Verification

1. **Skip Link href** — Changed from `#main-form` to `#main-content` to match implementation
2. **Appendix A** — Updated theme toggle HTML to include full structure with label box
3. **Appendix B** — Updated font size controls HTML to include `aria-hidden`, `title`, and `.sr-only` spans

### Verification Method

- Line-by-line comparison of CSS variables
- JavaScript function signature and logic comparison
- HTML structure validation
- Cross-reference of all color hex codes
- Mobile media query verification

---

## Related Specifications

- [SURFACE_DIMENSIONS_SPECIFICATIONS.md](./SURFACE_DIMENSIONS_SPECIFICATIONS.md) — Plate and cylinder dimension controls
- [BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md](./BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md) — Braille dot shape parameters
- [BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md](./BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md) — Text input and translation
- [BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md](./BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md) — Translation preview panel
- [RECESS_INDICATOR_SPECIFICATIONS.md](./RECESS_INDICATOR_SPECIFICATIONS.md) — Counter plate indicator markers
