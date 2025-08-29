# Braille Business Card STL Generator 🎯

**Create professional, tactile braille business cards with 3D-printable embossing plates**

This web application generates STL files for 3D-printable braille embossing and counter plates. Simply enter your text, and the system automatically translates it to braille and creates the precise 3D models needed for embossing professional business cards.

🌐 **[Live Demo](https://your-domain.vercel.app)** | 📋 **[Deployment Guide](DEPLOYMENT_CHECKLIST.md)**

---

## ✨ Features

### 🎯 Core Functionality
- **Multi-language braille translation** with 50+ language tables
- **Grade 1 & Grade 2 braille** support (UEB compliant)
- **Dual plate generation**: Embossing plates (raised dots) + Counter plates (recessed dots)
- **Real-time 3D preview** of generated STL files
- **Expert mode** with full dimensional control

### ♿ Accessibility Features
- **WCAG 2.1 AA compliant** with comprehensive screen reader support
- **High contrast mode** for users with visual impairments  
- **Adjustable font sizes** (75% to 150%)
- **Full keyboard navigation** with skip links
- **Screen reader optimized** with ARIA labels and semantic HTML

### 🔒 Security & Performance
- **Rate limiting** and input validation
- **Security headers** (CSP, XSS protection, etc.)
- **Production-ready** error handling
- **Mobile responsive** design

---

## 🚀 Quick Start

### What You'll Create

| Component | Purpose |
|-----------|---------|
| **Embossing Plate** | Creates raised braille dots by pressing into paper |
| **Counter Plate** | Provides backing support with matching recesses |

**Process**: Place business card paper between plates → Apply pressure → Get professional braille cards!

### 🛠️ What You Need

| Item | Notes |
|------|-------|
| **3D Printer** | 0.4mm nozzle, PLA or PETG recommended |
| **Clamp/Press** | Hand-screw clamp, arbor press, or similar |
| **Card Stock** | Business card paper (exact thickness you'll use) |
| **Slicer Software** | Cura, PrusaSlicer, etc. |
| **Calipers** *(optional)* | For measuring dot accuracy |

### ⚡ 5-Minute Setup

1. **Visit the web application** at your deployed URL
2. **Enter your text** (up to 4 lines, 50 characters each)
3. **Select language/grade** if needed (defaults to English UEB Grade 2)
4. **Generate embossing plate** → Download STL
5. **Generate counter plate** → Download STL  
6. **3D print both plates** (flat on bed, embossed surface up)
7. **Test with business card** between plates

> 💡 **Pro Tip**: Always test with your actual business card stock first!

---

## 🎥 Usage Guide

### Basic Workflow
1. **Enter Text**: Type your business card content (name, title, contact info)
2. **Choose Language**: Select from 50+ braille translation tables
3. **Preview**: See real-time 3D preview of your plates
4. **Download**: Get both embossing and counter plate STL files
5. **Print & Use**: 3D print and create professional braille cards

### Language Support
- **English**: UEB Grade 1 & 2 (default)
- **European**: French, German, Spanish, Italian, Dutch, etc.
- **Nordic**: Danish, Swedish, Norwegian, Finnish
- **Slavic**: Polish, Czech, Russian, Bulgarian
- **Asian**: Chinese, Japanese, Korean, Hindi, Arabic
- **Many more**: 50+ total language tables supported

### 📚 Grade 1 vs Grade 2 Braille

**Grade 2 (Contracted) - Recommended Default**
- Uses contractions and abbreviations
- Standard for professional braille
- More compact, fewer characters
- Default setting in this application

**Grade 1 (Uncontracted)**  
- Letter-by-letter translation
- Used for technical terms, education
- Longer output
- Available for special cases

### 📏 Default Dimensions (Standards-Based)

The application uses professionally-recognized braille specifications:

| Parameter | Value | Standard |
|-----------|-------|----------|
| **Dot Height** | 1.0mm | NLS Spec 800 |
| **Dot Diameter** | 1.8mm | BANA Guidelines |
| **Cell Spacing** | 6.5mm | UEB Standards |
| **Line Spacing** | 10.0mm | International Standard |
| **Dot Spacing** | 2.5mm | ADA Guidelines |

**Expert Mode** allows full customization of all dimensions.

**Sources:**
- Braille Authority of North America (BANA)
- NLS Specification 800 (Library of Congress)  
- Unified English Braille (UEB) Standards
- ADA Accessibility Guidelines

---

## 🔧 Customization & Testing

### Recommended Testing Workflow
1. **Start Small**: Generate plates for 1-2 words first
2. **Test Print**: Use your actual business card stock
3. **Measure Results**: Check dot height and clarity
4. **Adjust Settings**: Use Expert Mode if needed
5. **Iterate**: Usually 1-2 tests get perfect results

### Common Adjustments
| Issue | Solution |
|-------|----------|
| Dots too flat | Increase dot height or apply more pressure |
| Dots too sharp | Reduce dot height |
| Text doesn't fit | Reduce cell spacing or shorten text |
| Poor alignment | Adjust X/Y positioning in Expert Mode |

### 🖨️ 3D Printing Tips

**Settings:**
- **Material**: PLA (easy), PETG (durable)
- **Layer Height**: 0.2mm or finer for smooth dots
- **Infill**: 40%+ for stiffness
- **Perimeters**: 3-4 for strength
- **Speed**: ≤30mm/s for outer walls (smoother finish)

**Orientation:**
- Print plates **flat on bed**
- Embossed surface facing **up**
- No supports needed

**Quality:**
- Use quality filament for consistent results
- Ensure bed is level for even dot height
- Consider printing multiple plates for high-volume use

---

## ⚠️ Safety & Usage

**Safety:**
- Keep fingers clear when using clamps/presses
- Apply controlled, even pressure
- Test pressure on sample cards first

**Best Practices:**
- Store plates in protective cases
- Clean plates gently with soft brush
- Check alignment before pressing each card
- Use consistent pressure for uniform results

---

## 💾 File Management

**Automatic File Naming:**
- Files named based on your input text
- Clear suffixes: `_braille.stl` (emboss) vs `_counter_plate.stl`
- Sanitized for compatibility across operating systems

**Organization Tips:**
- Create folders by client/project
- Keep emboss and counter plates together
- Document settings used for future reference

---

## 🙏 Acknowledgments

**Special Thanks:**
- **Tobi Weinberg** - Project originator and Cursor AI introduction
- **Liblouis Project** - Open-source braille translation engine
- **Three.js Community** - 3D visualization capabilities
- **Braille Authority of North America** - Standards and specifications

**Attribution:** This project builds upon
[tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator/tree/main), and an earlier iteration I maintained at
[BrennenJohnston/braile-card-generator](https://github.com/BrennenJohnston/braile-card-generator/blob/brennen-dev/README.md).

**Open Source Components:**
- Flask (Python web framework)
- Trimesh (3D mesh processing)
- Liblouis (braille translation)
- Three.js (3D rendering)
- Shapely (geometric operations)

---

## 🔗 Technical Resources

**Braille Standards:**
- [BANA - Braille Authority of North America](https://brailleauthority.org/)
- [NLS Specification 800](https://www.loc.gov/nls/wp-content/uploads/2019/09/Spec800.11October2014.final_.pdf)
- [UEB Guidelines](https://www.brailleauthority.org/ueb)
- [ADA Accessibility Standards](https://www.access-board.gov/aba/guides/chapter-7-signs/)

**Development & Deployment:**
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md)
- [Vercel Documentation](https://vercel.com/docs)
- [Flask Security Guide](https://flask.palletsprojects.com/en/2.3.x/security/)

---

## 🚀 Deployment

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for complete deployment instructions, security configurations, and production setup.

**Quick Deploy to Vercel:**
1. Fork this repository
2. Connect to Vercel
3. Set environment variables (see deployment guide)
4. Deploy!

**Required Environment Variables:**
```bash
SECRET_KEY=your-super-secure-secret-key-here
FLASK_ENV=production
```

**CORS Configuration:**
Update `vercel_backend.py` with your actual domain before deployment.

---

## 🛡️ Security Features

This application is production-ready with comprehensive security measures:

- **Input Validation**: All user input is validated and sanitized
- **Rate Limiting**: 10 requests per minute per IP address
- **Security Headers**: CSP, XSS protection, HSTS, etc.
- **Path Traversal Protection**: Secure file serving
- **Error Handling**: No sensitive information exposure
- **CORS Configuration**: Strict origin controls

---

## 📱 Accessibility Compliance

Built with accessibility as a core requirement:

- **WCAG 2.1 AA Compliant**: Meets international accessibility standards
- **Screen Reader Support**: Full ARIA labeling and semantic HTML
- **Keyboard Navigation**: Complete keyboard accessibility with skip links
- **Visual Accessibility**: High contrast mode and adjustable font sizes
- **Motor Accessibility**: Large touch targets and easy interaction

---

## 📄 License

This project is open source. Please respect braille standards and accessibility guidelines when using or modifying.

---

**Ready to create professional braille business cards? [Get started now!](https://your-domain.vercel.app)**

---

## 🏁 Summary for Public Launch

This braille business card generator is now **production-ready** with:

✅ **Security**: Comprehensive input validation, rate limiting, and security headers  
✅ **Accessibility**: WCAG 2.1 AA compliant with full screen reader support  
✅ **Performance**: Optimized code with production logging  
✅ **Documentation**: Complete deployment guide and user instructions  
✅ **Standards Compliance**: Follows official braille specifications  

**Next Steps:**
1. Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. Set up environment variables
3. Update CORS domains
4. Deploy to Vercel
5. Test thoroughly
6. Launch publicly!
