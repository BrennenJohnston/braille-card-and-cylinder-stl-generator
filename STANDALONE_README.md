# Braille Card & Cylinder Generator - Standalone Package

This is a standalone, downloadable software package that allows you to generate 3D printable braille business cards and cylindrical objects without needing to install Python or any programming knowledge.

## 🎯 What This Package Does

The Braille Card & Cylinder Generator creates 3D printable STL files for braille objects that can be:
- **3D printed** on any FDM or SLA printer
- **Used immediately** without any programming knowledge
- **Customized** with your own text (up to 4 lines)
- **Generated** in both Grade 1 (uncontracted) and Grade 2 (contracted) braille
- **Created in two shapes**: Business cards (flat) or cylinders (curved)

## 📦 Package Contents

This standalone package includes:
- **BrailleCardGenerator.exe** - Desktop application (Windows)
- **BrailleCardGenerator_Web.exe** - Web-based application (Windows)
- **README.md** - This file
- **All dependencies** - No additional installation required

## 🚀 Quick Start Guide

### Option 1: Desktop Application (Recommended for Beginners)

1. **Download** the package to your computer
2. **Extract** the ZIP file to a folder of your choice
3. **Double-click** `BrailleCardGenerator.exe` to start
4. **Enter your text** in the 4 line inputs
5. **Select braille grade** (Grade 2 recommended)
6. **Click "Generate STL"** to create your 3D model
7. **Save the STL file** to your computer
8. **3D print** the file using your preferred slicer

### Option 2: Web Application

1. **Double-click** `BrailleCardGenerator_Web.exe` to start
2. **Open your web browser** to `http://localhost:5001`
3. **Use the web interface** to generate your braille card
4. **Download the STL file** directly from the browser

## 🎨 Card Specifications

- **Size**: 3.5 in × 2 in (90mm × 52mm) - Standard business card size
- **Thickness**: 2.0mm - Optimal for 3D printing
- **Grid**: 13 columns × 4 rows of braille cells
- **Margins**: 5.9mm left/right, 8.4mm top/bottom
- **Braille spacing**: Standard 6.5mm cell spacing, 10.0mm line spacing

## 🔤 Braille Grades

### Grade 2 (Contracted) - Recommended
- Uses contractions and abbreviations
- More space-efficient
- Standard for most braille users
- Example: "brl" = "braille"

### Grade 1 (Uncontracted)
- Spells out each letter
- Good for learning braille
- Takes more space
- Example: "b-r-a-i-l-l-e" = "braille"

## 📝 Usage Tips

### Text Guidelines
- **Maximum 4 lines** of text
- **Each line** can contain up to 13 braille cells
- **Grade 2** typically fits more text than Grade 1
- **Common contractions** are automatically applied in Grade 2

### 3D Printing Tips
- **Layer height**: 0.2mm or smaller for best detail
- **Infill**: 20-30% is sufficient
- **Support**: Usually not needed
- **Material**: PLA or PETG work well
- **Orientation**: Print flat side down

### File Management
- **Save STL files** with descriptive names
- **Keep backups** of your generated files
- **Test print** a small sample first
- **Check dimensions** in your slicer

## 🔧 Troubleshooting

### Common Issues

**Application won't start:**
- Make sure you're running Windows 10 or later
- Try running as administrator
- Check if antivirus is blocking the application

**STL file won't generate:**
- Make sure you've entered text in at least one line
- Check that line length is under 50 characters
- Try using Grade 1 instead of Grade 2

**3D printing issues:**
- Check that the STL file opens in your slicer
- Verify the dimensions are correct (90mm × 52mm)
- Try different print settings if quality is poor

**Web version won't open:**
- Make sure no other application is using port 5001
- Check if your firewall is blocking the connection
- Try refreshing the browser page

### Getting Help

If you encounter issues:
1. **Check this README** for common solutions
2. **Try both applications** (desktop and web versions)
3. **Restart the application** if it becomes unresponsive
4. **Check the file paths** for any error messages

## 🎯 Advanced Features

### Customization Options
- **Grade selection**: Choose between Grade 1 and Grade 2 braille
- **Line-by-line input**: Control exactly what goes on each line
- **Real-time validation**: Get feedback before generating
- **3D preview**: View the model before downloading

### Technical Details
- **Authoritative translation**: Uses liblouis for accurate braille
- **Standard compliance**: Follows UEB (Unified English Braille) standards
- **Optimized geometry**: Designed for 3D printing
- **Cross-platform**: Works on Windows, macOS, and Linux (source code)

## 📄 License and Attribution

This software uses:
- **liblouis** for braille translation (LGPL)
- **trimesh** for 3D mesh generation (MIT)
- **Flask** for web framework (BSD)
- **Three.js** for 3D visualization (MIT)

## 🤝 Community and Support

### For Makers
- **Share your prints** on social media with #BrailleCardGenerator
- **Contribute designs** to the community
- **Report issues** or suggest improvements

### For Educators
- **Use in classrooms** to teach braille
- **Create accessible materials** for students
- **Customize for specific needs**

### For Accessibility Advocates
- **Promote braille literacy** through 3D printing
- **Create inclusive materials** for organizations
- **Advocate for accessible design**

## 🔄 Updates and Development

This standalone package is based on the open-source Braille Card Generator project. For:
- **Latest updates**: Check the GitHub repository
- **Source code**: Available under open source license
- **Contributions**: Welcome from the community
- **Bug reports**: Please use GitHub issues

## 📞 Contact and Support

For questions, issues, or contributions:
- **GitHub**: [Project Repository]
- **Issues**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]

---

**Made with ❤️ for the maker and accessibility communities**

*This standalone package makes 3D printable braille accessible to everyone, regardless of programming experience.*

