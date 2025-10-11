# Vercel Runtime Error Fix Summary

## Issue
When generating an embossing plate on the deployed Vercel app, the backend was attempting to create a cylinder mesh instead of a card mesh, resulting in a 500 Internal Server Error.

### Error Details
- The runtime logs showed: `Creating cylinder mesh - Diameter: 31.0mm, Height: 52.0mm, Cutout Radius: 13.0mm`
- This occurred when generating a card embossing plate
- Counter plates worked correctly

## Root Cause
The frontend was defaulting to `shape_type: 'cylinder'` instead of `shape_type: 'card'` when sending requests to the backend.

This was caused by:
1. The HTML had the cylinder radio button marked as `checked` by default
2. JavaScript code on page load was forcing the shape type to cylinder: `if (cyl) cyl.checked = true;`

## Solution
Changed the default shape type from 'cylinder' to 'card':

1. **HTML Change** (templates/index.html):
   - Removed `checked` attribute from cylinder radio button
   - Added `checked` attribute to card radio button

2. **JavaScript Change** (templates/index.html):
   - Changed initialization code from:
     ```javascript
     // Always default to cylinder on load; do not restore from storage
     const cyl = document.querySelector('input[name="shape_type"][value="cylinder"]');
     if (cyl) cyl.checked = true;
     ```
   - To:
     ```javascript
     // Always default to card on load; do not restore from storage
     const card = document.querySelector('input[name="shape_type"][value="card"]');
     if (card) card.checked = true;
     ```

## Impact
- Card generation now works correctly as the default option
- Users can still select cylinder if needed
- The backend properly routes to card or cylinder generation based on the shape_type parameter

## Deployment
The fix has been committed and pushed to the main branch. Vercel will automatically deploy the changes.
