# Vercel Deployment Fixes Summary

## Overview
This document summarizes all the fixes applied to resolve Vercel deployment issues.

## Issues and Fixes

### 1. Shapely Build Error (Fixed)
**Problem**: Vercel couldn't build shapely from source
```
error: command '/usr/bin/gcc' failed with exit code 1
fatal error: geos_c.h: No such file or directory
```

**Solution**:
- Updated Python runtime to 3.9 in `vercel.json`
- Upgraded shapely from 2.0.4 to 2.0.6 (has pre-built wheels)
- Added `PIP_ONLY_BINARY` environment variable
- Created `.python-version` and `runtime.txt` files

### 2. Default Shape Type Error (Fixed)
**Problem**: Embossing plates were incorrectly generating cylinder meshes
```
Creating cylinder mesh - Diameter: 31.0mm, Height: 52.0mm, Cutout Radius: 13.0mm
```

**Solution**:
- Changed default radio button from 'cylinder' to 'card' in HTML
- Updated JavaScript initialization to set 'card' as default

### 3. Missing mapbox_earcut Module (Fixed)
**Problem**: Runtime error - "No Module Named 'mapbox_earcut'"

**Solution**:
- Replaced mapbox-earcut with scipy for triangulation
- scipy has pre-built wheels available on Vercel

### 4. Scipy Version Incompatibility (Fixed)
**Problem**: scipy 1.14.1 requires Python >= 3.10
```
Because scipy==1.14.1 depends on Python>=3.10, we can conclude that scipy==1.14.1 cannot be used
```

**Solution**:
- Downgraded scipy from 1.14.1 to 1.10.1
- scipy 1.10.1 supports Python 3.9

## Final Configuration

### Python Version
- Runtime: Python 3.9
- Configured in: `vercel.json`, `.python-version`, `runtime.txt`, `pyproject.toml`

### Key Dependencies
```
flask==2.3.3
trimesh==3.23.5
numpy==1.26.4
flask-cors==4.0.0
shapely==2.0.6
Flask-Limiter==3.8.0
redis==5.0.7
requests==2.32.3
scipy==1.10.1
```

### Vercel Configuration (vercel.json)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "wsgi.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb",
        "runtime": "python3.9"
      }
    }
  ],
  "env": {
    "PIP_ONLY_BINARY": "shapely"
  },
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/wsgi.py"
    }
  ]
}
```

## Deployment Timeline
1. Initial deployment: Failed due to shapely build error
2. Fix 1: Updated Python version and shapely → Still had runtime errors
3. Fix 2: Changed default shape type → Fixed card generation
4. Fix 3: Replaced mapbox-earcut with scipy → Fixed triangulation
5. Fix 4: Downgraded scipy to 1.10.1 → Fixed Python 3.9 compatibility

## Verification
Once deployed, the application should:
- ✅ Build successfully without compilation errors
- ✅ Default to card generation (not cylinder)
- ✅ Generate both embossing and counter plates correctly
- ✅ Handle triangulation operations without missing modules

## Important Notes
- Always use the main production URL, not preview deployment URLs
- Preview deployments may not have the latest fixes
- Vercel automatically deploys the main branch after pushes
