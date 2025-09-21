# 🌐 Cloudflare Pages Deployment Guide
## Braille STL Generator v2.0 - Production Deployment

This guide covers the complete deployment process for the Braille STL Generator on Cloudflare Pages.

---

## 📋 Prerequisites

### Required Tools
- **Node.js 20+** - Modern JavaScript runtime
- **npm or yarn** - Package manager
- **Git** - Version control
- **Wrangler CLI** - Cloudflare deployment tool

### Cloudflare Account Setup
1. **Create Cloudflare Account** at [dash.cloudflare.com](https://dash.cloudflare.com)
2. **Get API Token** from Cloudflare dashboard → My Profile → API Tokens
3. **Get Account ID** from Cloudflare dashboard → Right sidebar

---

## 🚀 Quick Deploy

### Option 1: Automatic Deployment (Recommended)
```bash
# 1. Clone and setup
git clone <repository-url>
cd braille-card-and-cylinder-stl-generator

# 2. Install dependencies
npm install

# 3. Run tests to verify everything works
npm run test:unit

# 4. Build and deploy
npm run deploy
```

### Option 2: Manual Deployment
```bash
# 1. Install Wrangler globally
npm install -g wrangler

# 2. Login to Cloudflare
wrangler login

# 3. Build the application
npm run build

# 4. Deploy to Cloudflare Pages
npm run deploy:manual
```

---

## ⚙️ Environment Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```env
# Cloudflare Configuration
CLOUDFLARE_API_TOKEN=your_api_token_here
CLOUDFLARE_ACCOUNT_ID=your_account_id_here

# Build Configuration
NODE_ENV=production
VITE_APP_NAME="Braille STL Generator"
VITE_APP_VERSION="2.0.0"
VITE_CLOUDFLARE_PAGES=true

# Optional: Custom Domain
CUSTOM_DOMAIN=your-domain.com
```

### GitHub Secrets (for CI/CD)

If using GitHub Actions, add these secrets in your repository settings:

- `CLOUDFLARE_API_TOKEN` - Your Cloudflare API token
- `CLOUDFLARE_ACCOUNT_ID` - Your Cloudflare account ID

---

## 🏗️ Build Configuration

### Production Build Features
- **🎯 Optimized bundles** with Terser minification
- **📦 Code splitting** for better caching
- **⚡ Tree shaking** to remove unused code
- **🗜️ Asset optimization** for faster loading
- **🔧 Worker bundling** for 3D processing

### Build Output Structure
```
dist/
├── index.html                 # Main application entry (0.77 KB)
├── main.js                    # UI and core logic (40 KB)
├── main-[hash].css           # Styles (13 KB)
├── geometry-worker.js        # 3D processing engine (731 KB)
├── liblouis-worker.js        # Braille translation (2.8 KB)
├── liblouis/                 # Braille translation tables
│   ├── build-no-tables-utf16.js
│   ├── easy-api.js
│   └── tables/               # 368+ braille table files
└── assets/                   # Optimized static assets
```

---

## 🌐 Cloudflare Pages Configuration

### Custom Headers (cloudflare/_headers)
- **🔒 Security headers** (CSP, HSTS, X-Frame-Options)
- **⚡ Caching policies** for optimal performance
- **🔄 CORS configuration** for cross-origin requests
- **📱 Worker routing** for proper file serving

### URL Routing (cloudflare/_redirects)
- **📍 SPA routing** for single-page application
- **🔄 Legacy redirects** from old Vercel deployment
- **📁 Asset optimization** routing
- **🚫 404 handling** with fallback to main app

### Build Commands
- **Build Command:** `npm run build`
- **Build Output Directory:** `dist`
- **Node.js Version:** `20`
- **Root Directory:** `.` (project root)

---

## 🔧 Deployment Environments

### Production (main branch)
- **URL:** `braille-stl-generator.pages.dev`
- **Branch:** `main` or `feature/cloudflare-client`
- **Auto-deploy:** Enabled on push
- **Custom domain:** Configure in Cloudflare dashboard

### Preview (pull requests)
- **URL:** `<commit-hash>.braille-stl-generator.pages.dev`
- **Trigger:** Pull request creation/update
- **Auto-deploy:** Enabled
- **Review:** Automatic preview comments

### Development (local)
```bash
npm run dev          # Start development server (port 3000)
npm run preview      # Preview production build (port 4173)
npm run build        # Build for production
```

---

## 🧪 Deployment Testing

### Pre-deployment Tests
```bash
# Run complete test suite
npm run test:all

# Run performance benchmarks
npm run test:performance

# Validate build output
npm run build && ls -la dist/
```

### Post-deployment Verification
1. **🌐 URL accessibility** - Check main page loads
2. **🔤 Braille translation** - Test text to braille conversion
3. **🏗️ STL generation** - Test complete workflow
4. **📱 Mobile compatibility** - Test responsive design
5. **⚡ Performance** - Verify load times under 3 seconds

---

## 🚨 Troubleshooting

### Common Issues

#### Build Fails
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for dependency conflicts
npm ls
```

#### Deployment Fails
```bash
# Verify Wrangler authentication
wrangler whoami

# Check project configuration
wrangler pages project list

# Manual deployment with debug
wrangler pages deploy dist --debug
```

#### Workers Not Loading
- Check `Content-Security-Policy` allows `'unsafe-eval'` for workers
- Verify worker files are in correct paths
- Check browser console for worker loading errors

#### Large Bundle Size
- Current geometry worker (731 KB) is expected for 3D processing
- Liblouis tables (~2 MB) are necessary for braille translation
- Use network throttling to test on slower connections

### Performance Optimization
```bash
# Analyze bundle
npm run build && npx vite-bundle-analyzer dist/

# Test with production settings
NODE_ENV=production npm run build
```

---

## 📊 Deployment Metrics

### Expected Performance
- **⚡ First load:** < 3 seconds on 3G
- **🔄 Subsequent loads:** < 1 second (cached)
- **🏗️ STL generation:** < 30 seconds for typical text
- **📱 Mobile performance:** 90+ Lighthouse score

### Bundle Size Targets
- **Main app:** ~40 KB (UI and core logic)
- **Geometry worker:** ~731 KB (3D processing)
- **Total bundle:** ~2-3 MB (including braille tables)
- **Gzipped:** ~200 KB initial load

---

## 🎯 Post-Deployment

### Monitoring
- **📊 Cloudflare Analytics** - Built-in traffic and performance metrics
- **🔍 Error tracking** - Monitor console errors
- **⚡ Performance monitoring** - Page load times
- **📱 User experience** - Mobile vs desktop usage

### Maintenance
- **🔄 Automatic updates** via GitHub Actions
- **🧪 Continuous testing** on each commit
- **📦 Dependency updates** via Dependabot
- **🔒 Security monitoring** via GitHub Security

### Custom Domain Setup
1. **Add domain** in Cloudflare Pages dashboard
2. **Configure DNS** with provided CNAME records
3. **Enable SSL/TLS** (automatic with Cloudflare)
4. **Test domain resolution** and HTTPS

---

## 📞 Support

### Resources
- **📚 Cloudflare Pages Docs:** [developers.cloudflare.com/pages](https://developers.cloudflare.com/pages)
- **🔧 Wrangler CLI Docs:** [developers.cloudflare.com/workers/wrangler](https://developers.cloudflare.com/workers/wrangler)
- **🚀 Vite Deployment:** [vitejs.dev/guide/static-deploy](https://vitejs.dev/guide/static-deploy)

### Getting Help
1. **Check deployment logs** in Cloudflare dashboard
2. **Review GitHub Actions** logs for CI/CD issues  
3. **Test locally** with `npm run preview`
4. **Check browser console** for runtime errors

---

## 🎉 Success!

Your Braille STL Generator is now deployed globally on Cloudflare's edge network with:

- **🌍 Global CDN** distribution
- **⚡ Lightning-fast** loading worldwide
- **🔒 Enterprise security** headers
- **📱 Mobile-optimized** responsive design
- **🚀 Serverless architecture** with zero maintenance

**The future of braille STL generation is now live! 🎯**
