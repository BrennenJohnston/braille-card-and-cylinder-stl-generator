# Vercel Deployment Guide for Braille Card Generator

## 🚀 Quick Deploy

### Option 1: Deploy from GitHub (Recommended)

1. **Go to [vercel.com](https://vercel.com)** and sign up/login
2. **Click "New Project"**
3. **Import your GitHub repository**: `BrennanJohnston/braile-card-generator`
4. **Select the repository** and click "Import"
5. **Configure the project**:
   - Framework Preset: `Other`
   - Root Directory: `./` (leave as default)
   - Build Command: Leave empty (Vercel will auto-detect)
   - Output Directory: Leave empty
6. **Click "Deploy"**

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy from your project directory**:
   ```bash
   vercel
   ```

4. **Follow the prompts** to configure your project

## 📁 Deployment Files Created

- **`vercel.json`** - Vercel configuration
- **`wsgi.py`** - WSGI entry point for Vercel
- **`.vercelignore`** - Files to exclude from deployment
- **`requirements.txt`** - Python dependencies

## ⚠️ Important Notes

### Dependencies
Your app requires these packages (already in requirements.txt):
- `flask` - Web framework
- `trimesh` - 3D mesh processing
- `numpy` - Numerical computing
- `flask-cors` - Cross-origin support
- `shapely` - Geometric operations
- `mapbox-earcut` - Polygon triangulation

### File Size Limits
- **Vercel has a 50MB limit** for serverless functions
- Your `third_party/liblouis` folder contains many files
- **Solution**: Consider hosting the liblouis files on a CDN or separate service

### Environment Variables
If you need to add environment variables:
1. Go to your Vercel project dashboard
2. Navigate to "Settings" → "Environment Variables"
3. Add any required variables

## 🔧 Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check that all dependencies are in `requirements.txt`
   - Ensure Python version compatibility

2. **Import Errors**:
   - Verify `wsgi.py` is correctly importing from `backend.py`
   - Check that all required files are included

3. **File Size Issues**:
   - The liblouis library is quite large
   - Consider alternatives or CDN hosting

### Performance Considerations

- **Cold Starts**: Serverless functions may have initial delay
- **Memory Limits**: Vercel has memory constraints for processing large 3D models
- **Timeout Limits**: Function execution time is limited

## 🌐 Custom Domain

1. **Add Custom Domain** in Vercel dashboard
2. **Configure DNS** as instructed by Vercel
3. **SSL Certificate** is automatically provisioned

## 📊 Monitoring

- **Vercel Analytics** - Built-in performance monitoring
- **Function Logs** - View execution logs in dashboard
- **Error Tracking** - Monitor function failures

## 🔄 Updates

- **Automatic Deployments**: Every push to your main branch triggers a new deployment
- **Preview Deployments**: Pull requests get preview URLs
- **Rollback**: Easy rollback to previous versions from dashboard

## 📞 Support

- **Vercel Documentation**: [vercel.com/docs](https://vercel.com/docs)
- **Community**: [github.com/vercel/vercel/discussions](https://github.com/vercel/vercel/discussions)
- **Status Page**: [vercel-status.com](https://vercel-status.com)

---

**Ready to deploy?** Your repository is now configured for Vercel! 🎉
