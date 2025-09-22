# Cloudflare Pages Deployment Guide

## Important Build Settings

### Correct Configuration

When deploying to Cloudflare Pages, use these **exact** settings:

- **Build command**: `npm run build`
- **Build output directory**: `/dist`
- **Root directory**: `/`
- **Build system version**: 3 (latest)

### ⚠️ Cross-Platform Deployment Note

**IMPORTANT**: This project is deployed without a `package-lock.json` file. This is intentional!

- Cloudflare Pages runs on Linux
- Local development may happen on Windows/Mac
- Platform-specific dependencies (like rollup binaries) differ between OS
- Letting Cloudflare generate the lock file ensures Linux dependencies are installed

### DO NOT:
- Commit `package-lock.json` to the repository
- Use `npm ci` commands (they require a lock file)
- Use `npm install --legacy-peer-deps` in the build command

## wrangler.toml Configuration

Keep the minimal configuration:
```toml
name = "braille-stl-generator"
compatibility_date = "2024-09-21"
pages_build_output_dir = "dist"
```

## Environment Variables

Set these in your Cloudflare Pages dashboard:

```
NODE_VERSION=20
NODE_ENV=production
VITE_CLOUDFLARE_PAGES=true
```

## Deployment Steps

1. **Make changes and commit** (without package-lock.json)
   ```bash
   git add .
   git commit -m "your changes"
   git push origin feature/cloudflare-client
   ```

2. **Cloudflare Pages will**:
   - Clone your repository
   - Run `npm install` (generating a Linux-compatible lock file)
   - Run `npm run build`
   - Deploy the `dist` directory

## Troubleshooting

### If you see "Cannot find module @rollup/rollup-linux-x64-gnu"
- This means a Windows/Mac package-lock.json was committed
- Remove it: `git rm package-lock.json`
- Commit and push the removal

### If you see "npm ci can only install packages..."
- This means package.json and package-lock.json are out of sync
- Remove package-lock.json and let Cloudflare regenerate it

### Local Development

For local development, you can still use package-lock.json:

```bash
# Install dependencies locally
npm install

# Run development server
npm run dev

# Build locally to test
npm run build
```

Just don't commit the `package-lock.json` file!

## Alternative: Platform-Agnostic Lock File

If you need to commit a lock file in the future:

1. Use npm 9+ which handles cross-platform dependencies better
2. Or use pnpm which has better cross-platform support
3. Or generate the lock file in a Linux Docker container

## Verification

After deployment, verify:

1. Check the Cloudflare Pages deployment logs
2. Ensure all JavaScript files load correctly
3. Test STL generation functionality
4. Check browser console for errors

## Summary

The key to successful Cloudflare Pages deployment is:
- Let Cloudflare's Linux environment handle dependency installation
- Don't commit platform-specific lock files
- Keep build commands simple: `npm run build`
- Trust the platform to handle the rest