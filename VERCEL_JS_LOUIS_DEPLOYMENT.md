# Vercel Deployment with Liblouis JavaScript Build

## 🎯 **Overview**

This deployment strategy uses the [liblouis/js-build](https://github.com/liblouis/js-build) repository, which provides pre-compiled JavaScript binaries of liblouis using Emscripten. This approach is perfect for Vercel because:

- ✅ **Much smaller size** (~5-10MB vs 50MB+)
- ✅ **Web-optimized** - designed for JavaScript environments
- ✅ **No binary compatibility issues** - works on Vercel's Linux servers
- ✅ **Maintains full liblouis functionality** - Grade 1 and Grade 2 braille

## 🚀 **Deployment Steps**

### **Step 1: Prepare Your Repository**

Your repository is already set up with:
- `backend.py` - Flask app used locally and in serverless
- `wsgi.py` - Vercel entry point importing `app` from `backend.py`
- `requirements_vercel.txt` - Minimal dependencies
- `vercel.json` - Vercel configuration
- `.vercelignore` - Excludes heavy files

### **Step 2: Deploy to Vercel**

1. **Connect your GitHub repository to Vercel**
2. **Set build settings**:
   - Install Command: `pip install -r requirements_vercel.txt`
   - Output Directory: `.`
3. **Deploy!** 🎉

## 🔧 **How It Works**

### **Current Implementation**

The app uses full Liblouis JS in the browser (web worker) with on-demand table loading from `static/liblouis/tables/`.

### **Future Enhancement: Full Liblouis JS Integration**

To get full Grade 2 braille support everywhere, you can integrate the actual liblouis JavaScript build directly in the frontend (already included), or move translation server-side if needed.

```javascript
// In the frontend
import { translate } from 'liblouis-js';

async function translateToBraille(text, grade) {
    const table = grade === 'g2' ? 'en-ueb-g2.ctb' : 'en-ueb-g1.ctb';
    return await translate(text, table);
}
```

## 📊 **Size Comparison**

| Approach | Size | Vercel Compatible | Functionality |
|----------|------|-------------------|---------------|
| **Full C liblouis** | ~50MB+ | ❌ No | ✅ Full |
| **Liblouis JS Build** | ~5-10MB | ✅ Yes | ✅ Full |
| **Minimal Fallback** | ~1MB | ✅ Yes | ⚠️ Basic |

## 🎯 **Benefits of This Approach**

1. **Immediate Deployment** - Works right now with JS-based translation
2. **Vercel Optimized** - Designed for serverless environments
3. **Maintains Quality** - Generates proper 3D STL models

## 🔄 **Migration Path**

### **Phase 1: Deploy with Frontend Liblouis (Current)**
- ✅ Grade 1/2 braille support
- ✅ 3D STL generation
- ✅ Vercel compatibility
- ✅ Small deployment size

### **Phase 2: Optional Server-Side Translation**
- ✅ Add Python bindings or REST service if needed
- ✅ Keep JS worker as fallback

## 🚨 **Important Notes**

### **Current Limitations**
- Serverless function time/memory limits can affect large meshes

### **Vercel Considerations**
- **Function timeout** - 10s (hobby) / 60s (pro)
- **Memory limits** - 1024MB (hobby) / 3008MB (pro)
- **Cold starts** - May affect first request performance

## 🧪 **Testing Your Deployment**

1. **Deploy to Vercel**
2. **Test basic functionality**:
   - Enter text lines
   - Select Grade 2
   - Generate STL
3. **Verify output** - STL downloads and opens in slicer

## 🔮 **Next Steps**

### **Immediate (After Deployment)**
1. Test basic functionality
2. Verify STL generation works
3. Check performance on Vercel

### **Short Term (1-2 weeks)**
1. Profile boolean ops performance
2. Explore manifold3d usage on serverless
3. Test with real braille users

### **Long Term (1-2 months)**
1. Add more shapes or fixtures
2. Optimize for production use

## 📚 **Resources**

- [Liblouis JS Build Repository](https://github.com/liblouis/js-build)
- [Liblouis Official Documentation](https://liblouis.org/)
- [Vercel Python Documentation](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [UEB Braille Standards](https://www.brailleauthority.org/ueb.html)

## 🆘 **Troubleshooting**

### **Common Issues**

1. **Build fails on Vercel**
   - Check `requirements_vercel.txt` syntax
   - Verify Python version compatibility

2. **Function times out**
   - Optimize 3D generation code
   - Consider upgrading Vercel plan

3. **Memory errors**
   - Reduce mesh complexity
   - Optimize trimesh operations

### **Getting Help**
- Check Vercel deployment logs
- Test locally with `python backend.py`
- Review error messages in browser console

---

**Ready to deploy?** Your app is configured for Vercel! 🚀
