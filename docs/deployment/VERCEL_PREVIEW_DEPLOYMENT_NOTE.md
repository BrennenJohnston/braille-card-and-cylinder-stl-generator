# Vercel Preview Deployment Issue

## Problem
You're experiencing errors on a preview deployment URL:
`https://braille-card-and-cylinder-stl-generator-1hohqc6vd.vercel.app/`

This URL (ending with `-1hohqc6vd`) is a **preview deployment**, not the main production deployment.

## Issues on Preview Deployment

1. **Still defaulting to cylinder shape**: The preview deployment doesn't have our fix that changes the default from cylinder to card
2. **Missing mapbox_earcut module**: The preview deployment is missing the triangulation dependency

## Fixes Applied to Main Branch

1. **Shape Type Fix** (commit: 30aefb1)
   - Changed default shape from 'cylinder' to 'card'
   - Fixed the issue where card generation was incorrectly creating cylinders

2. **Dependency Fix** (commit: 97c3bea)
   - Replaced mapbox-earcut with scipy for triangulation
   - scipy has pre-built wheels and doesn't require compilation on Vercel

## Solution

The preview deployment appears to be from an older commit. To use the fixed version:

1. **Use the main deployment URL**:
   - The main deployment URL should be something like:
   - `https://braille-card-and-cylinder-stl-generator.vercel.app/`
   - (without the random suffix like `-1hohqc6vd`)

2. **Wait for automatic deployment**:
   - Vercel should automatically deploy the main branch after our pushes
   - The deployment typically takes 1-3 minutes

3. **Check deployment status**:
   - You can check the deployment status in your Vercel dashboard
   - Look for deployments from the `main` branch

## Verification

Once using the correct deployment URL, you should see:
- Card generation works by default (not cylinder)
- No "mapbox_earcut" errors
- Both embossing and counter plates generate correctly

## Timeline of Fixes
1. First deployment issue: Missing shapely GEOS libraries → Fixed with Python 3.9 and shapely 2.0.6
2. Runtime issue: Wrong default shape type → Fixed by changing default to 'card'
3. Dependency issue: Missing mapbox_earcut → Fixed by using scipy instead
