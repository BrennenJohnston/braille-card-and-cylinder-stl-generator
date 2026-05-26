# Braille Cylinder STL Generator (OpenSCAD)

> **About this folder.** This is the OpenSCAD version of the Braille STL Generator,
> vendored into the main `braille-card-and-cylinder-stl-generator` repository so
> users can download and use it without the browser app. The original standalone
> repo at [BrennenJohnston/braille-stl-generator-openscad](https://github.com/BrennenJohnston/braille-stl-generator-openscad)
> is no longer the active home for this project — please open issues and pull
> requests against the main repository.
>
> **What you need:** just the file `Braille_Card_And_Cylinder_STL_Generator.scad`
> and [OpenSCAD](https://openscad.org/) (2024.x or newer). Everything else in this
> folder is documentation. See the *Quick Start* section below.

Parametric OpenSCAD program for generating braille embossing plates and counter plates for cylindrical objects.

[![STL Validation](https://github.com/BrennenJohnston/braille-stl-generator-openscad/actions/workflows/stl-validation.yml/badge.svg)](https://github.com/BrennenJohnston/braille-stl-generator-openscad/actions/workflows/stl-validation.yml)

## 🔗 Related Project

This is the **offline OpenSCAD companion** to the web-based Braille STL Generator:

| Version | Link | Use Case |
|---------|------|----------|
| **Web App** | [braille-card-and-cylinder-stl-gener.vercel.app](https://braille-card-and-cylinder-stl-gener.vercel.app) | Browser-based with automatic translation |
| **OpenSCAD** (this repo) | [github.com/BrennenJohnston/braille-stl-generator-openscad](https://github.com/BrennenJohnston/braille-stl-generator-openscad) | Offline use, full parametric control |
| **Web App Source** | [github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator](https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator) | Web app source code |

## ⚠️ Key Difference

**This OpenSCAD version requires pre-translated Unicode braille text.** It does NOT include automatic translation.

---

## 🚀 Quick Start

1. **Translate your text**:
   - Go to https://www.branah.com/braille-translator
   - Select Grade 1 or Grade 2 braille
   - Ensure "Unicode Braille" is selected (NOT ASCII)
   - Type your text and copy the braille output (e.g., ⠓⠑⠇⠇⠕)

2. **Open in OpenSCAD**:
   - Open `Braille_Card_And_Cylinder_STL_Generator.scad`
   - Open the Customizer panel (View → Customizer)

3. **Configure**:
   - Paste braille into `Line_1`, `Line_2`, etc.
   - Choose `plate_type`: Embossing Plate or Counter Plate
   - Choose `paper_thickness_preset`: 0.4mm, 0.3mm, or Custom
   - Choose `dot_shape`: Rounded or Cone

4. **Generate**:
   - Render: F6 (or Design → Render)
   - Export: File → Export → Export as STL

---

## 📋 What This Makes

- **Cylinder Emboss Plate**: Raised braille dots on cylindrical surface
- **Cylinder Counter Plate**: Recessed support for embossing cylindrical objects

## 🎯 Features

### Shape Options
- **Rounded**: Dome-shaped dots with spherical bowl recesses
- **Cone**: Traditional frustum cone dots with matching cone recesses

### Indicator Shapes
- Optional start/end markers for each row (triangle and rectangle)
- Helps with plate alignment during embossing
- Reserves 2 cells per row when enabled

### Paper Thickness Presets
- **0.4mm Preset** (default): Optimized for thicker paper, larger dots
- **0.3mm Preset**: Optimized for thinner paper, smaller dots
- **Custom**: Use manually-entered parameter values

The preset system controls 24 parameters at once (spacing, dot dimensions, cylinder settings) matching the web app's "Card Thickness" dropdown.

### Parametric Control
All parameters match the web-based generator UI:
- Cylinder dimensions (diameter, height, cutout)
- Braille spacing (cell, line, dot spacing)
- Dot dimensions (separate controls for rounded and cone shapes)
- Counter plate recess dimensions
- Positioning adjustments (X/Y offsets)

---

## 📐 Default Settings

All defaults match the web app's **0.4mm Paper Thickness Preset** (applied on load):

### Cylinder Settings
- Diameter: 30.8mm
- Height: 52mm
- Polygonal Cutout: 13mm radius, 12 points/sides
- Seam Offset: 0°

### Braille Grid
- Cells per row: 11 (available for text; 2 additional cells reserved when indicators are on)
- Number of rows: 4
- Cell spacing: 6.5mm
- Line spacing: 10.0mm
- Dot spacing: 2.5mm

### Dot Dimensions (Rounded - 0.4mm Preset)
- Base diameter: 1.5mm
- Base height: 0.5mm
- Dome diameter: 1.0mm
- Dome height: 0.5mm

### Counter Plate (Bowl - 0.4mm Preset)
- Base diameter: 1.8mm
- Depth: 0.8mm

---

## 🖨️ 3D Printing Tips

- **Material**: PLA works well; PETG is more durable
- **Layer Height**: 0.1-0.2mm for smooth dots
- **Infill**: 40%+ recommended for stiffness
- **Perimeters**: 3-4 for strength
- **Orientation**: Print upright as oriented in preview
- **Speed**: Slower outer walls (≤30mm/s) for smoother dots

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [docs/WEB_TO_OPENSCAD_PORTING_GUIDE.md](docs/WEB_TO_OPENSCAD_PORTING_GUIDE.md) | Comprehensive guide for porting web generators to OpenSCAD |
| [docs/OPENSCAD_COORDINATE_SYSTEM_SPECIFICATIONS.md](docs/OPENSCAD_COORDINATE_SYSTEM_SPECIFICATIONS.md) | Technical coordinate system documentation |
| [docs/QUICK_START_TESTING.md](docs/QUICK_START_TESTING.md) | Notes from the original cross-platform validation suite (test files themselves are not vendored) |
| [PARAMETER_MAPPING.md](PARAMETER_MAPPING.md) | Parameter mapping between OpenSCAD and web UI |

---

## 🧪 Automated Testing

A cross-platform validation framework comparing OpenSCAD output against web-generated reference STLs was developed alongside this project. The test suite (≈30 fixtures, including binary STL references) is not vendored into this repository to keep the download lightweight. If you want to run those tests, see the historical snapshot at [github.com/BrennenJohnston/braille-stl-generator-openscad](https://github.com/BrennenJohnston/braille-stl-generator-openscad). For day-to-day OpenSCAD use, none of it is needed — just open the `.scad` file and use the Customizer.

---

## 🆚 Web App vs. OpenSCAD

### Use Web App When:
- ✅ You need automatic braille translation
- ✅ You want live 3D preview
- ✅ You prefer no software installation
- ✅ You need multi-language support (100+ tables)

### Use OpenSCAD When:
- ✅ You want to work offline
- ✅ You need full parametric control
- ✅ You want to modify/extend the code
- ✅ You have existing OpenSCAD workflows
- ✅ You need version control (plain text files)
- ✅ You want batch processing capability

---

## 🐛 Troubleshooting

### "INVALID CHARACTERS" Warning
- You pasted regular text instead of Unicode braille
- Solution: Translate at Branah.com and copy the braille output

### "TEXT TOO LONG" Warning
- Your braille text exceeds `grid_columns` limit
- Solution: Reduce text length or increase `grid_columns`

### Dots Don't Align
- Check `braille_x_adjust` and `braille_y_adjust`
- Ensure spacing settings match between emboss and counter plates

### Plates Don't Fit Together
- Verify both plates use same `dot_shape` setting
- Check that counter plate dimensions match emboss dimensions
- Ensure `indicators` setting is same for both plates

---

## 📚 References

1. **Web Generator**: https://braille-card-and-cylinder-stl-gener.vercel.app
2. **Branah Translator**: https://www.branah.com/braille-translator
3. **BANA Standards**: https://brailleauthority.org/size-and-spacing-braille-characters
4. **NLS Spec 800**: https://www.loc.gov/nls/
5. **ADA Standards**: https://archive.ada.gov/

---

## 🙏 Acknowledgments

- **Brennen Johnston**: Original web-based generator
- **Tobi Weinberg**: Project inception and development support
- **Liblouis**: Professional braille translation library (used in web app)

---

## 📄 License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**.

- ✅ Free for personal, educational, and non-commercial use
- ✅ Modification and remixing allowed
- ❌ **No commercial use permitted**

See the [LICENSE](LICENSE) file for full terms.

---

## 📞 Support

For issues specific to this OpenSCAD version:
1. [Open an issue](https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator/issues) on the main repository (use the `OpenSCAD` label)
2. Check parameter values in Customizer
3. Verify Unicode braille character validity
4. Ensure OpenSCAD version 2024.x or newer (2026.01.03+ recommended)

For general braille embossing questions, see the [web app](https://braille-card-and-cylinder-stl-gener.vercel.app).

---

**Version**: 2.1.0  
**Last Updated**: 2026-01-11
