# Cloudflare Pages Deployment Guide

## Important Build Settings

### Correct Configuration

When deploying to Cloudflare Pages, use these **exact** settings:

- **Build command**: `npm run build`
- **Build output directory**: `/dist`
- **Root directory**: `/`
- **Build system version**: 3 (latest)

### ⚠️ Critical Warning

**DO NOT** use `npm install --legacy-peer-deps && npm run build` as your build command. This will remove packages and cause the build to fail with "vite: not found".

The Cloudflare Pages build system automatically runs `npm clean-install` before your build command, so additional `npm install` commands are unnecessary and can be harmful.

## wrangler.toml Configuration

### Option 1: Minimal wrangler.toml (Recommended)
Keep only the essential fields:
```toml
name = "braille-stl-generator"
compatibility_date = "2024-09-21"
pages_build_output_dir = "dist"
```

### Option 2: No wrangler.toml
If deployment still fails, remove wrangler.toml entirely and configure everything through the Cloudflare Pages dashboard.

## Environment Variables

Set these in your Cloudflare Pages dashboard:

```
NODE_VERSION=20
NODE_ENV=production
VITE_CLOUDFLARE_PAGES=true
```

## Deployment Steps

1. **Commit the fixed files**
   ```bash
   git add package-lock.json wrangler.toml
   git commit -m "fix: Minimal wrangler.toml for Pages compatibility"
   git push origin feature/cloudflare-client
   ```

2. **Update Cloudflare Pages Build Settings**
   - Go to your Cloudflare Pages project settings
   - Navigate to "Settings" > "Builds & deployments"
   - Update the "Build command" to: `npm run build`
   - Ensure "Build output directory" is: `/dist`
   - Save changes

3. **Trigger New Deployment**
   - Either push a new commit or
   - Go to "Deployments" and click "Retry deployment"

## Troubleshooting

### If you see "unable to read wrangler.toml"
- The file might have unsupported sections for Pages
- Either use minimal configuration or remove the file entirely

### If you see "vite: not found"
- Check that your build command is exactly `npm run build`
- Ensure package-lock.json has `"lockfileVersion": 2`
- Verify that vite is listed in devDependencies in package.json

### If only a few packages are installed
- Your package-lock.json might have lockfileVersion 3
- Regenerate it with: `npm install --lockfile-version=2`

### Build fails with module errors
- Ensure all dependencies are properly listed in package.json
- Check that the build system version is set to 3 (latest)

## Verification

After deployment, verify:

1. All JavaScript files load correctly
2. Web Workers function properly
3. STL generation works as expected
4. No console errors in browser DevTools

## Local Testing

To simulate the Cloudflare Pages build environment locally:

```bash
# Clean install (like Cloudflare does)
rm -rf node_modules
npm clean-install --progress=false

# Run build
npm run build

# Preview the built site
npm run preview
```

## Alternative: Remove wrangler.toml

If issues persist, you can remove wrangler.toml entirely:

```bash
git rm wrangler.toml
git commit -m "fix: Remove wrangler.toml for Pages compatibility"
git push origin feature/cloudflare-client
```

Then configure everything through the Cloudflare Pages dashboard.

## Support

If you continue to experience issues:

1. Check the deployment logs in Cloudflare Pages dashboard
2. Ensure all files are committed to git
3. Verify Node.js version compatibility (v20 recommended)