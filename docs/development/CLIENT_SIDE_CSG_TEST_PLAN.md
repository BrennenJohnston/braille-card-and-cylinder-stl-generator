# Client-Side CSG Testing Plan

## Implementation Status
- ✅ Vendored three-bvh-csg and three-mesh-bvh libraries
- ✅ Added STLExporter from three.js examples
- ✅ Created CSG worker for client-side geometry generation
- ✅ Added /geometry_spec endpoint to backend
- ✅ Wired frontend to use worker with fallback to server
- ✅ Implemented automatic fallback logic

## Test Scenarios

### 1. Browser Compatibility Tests
- [ ] **Chrome/Edge (latest)**: Full support expected
- [ ] **Firefox (latest)**: Full support expected
- [ ] **Safari (latest)**: Check Module Worker support
- [ ] **Mobile browsers**: iOS Safari, Chrome Android
- [ ] **Older browsers**: Should fall back to server gracefully

### 2. Functional Tests

#### Positive Plate Generation
- [ ] Simple text (1 line, few characters)
- [ ] Full grid (4 lines, max characters per line)
- [ ] Special characters and markers
- [ ] Standard cone frustums
- [ ] Rounded dots (if enabled)

#### Counter Plate Generation
- [ ] Hemisphere recesses
- [ ] Bowl (spherical cap) recesses
- [ ] Cone frustum recesses
- [ ] All markers and indicators

#### Cylinder Generation
- [ ] Basic cylinder positive
- [ ] Cylinder counter plate
- [ ] Polygonal cutout variations

### 3. Performance Tests
- [ ] Small model (10-20 dots): Should complete in < 5 seconds
- [ ] Medium model (50-100 dots): Should complete in < 15 seconds
- [ ] Large model (200+ dots): Should complete in < 60 seconds
- [ ] Memory usage remains stable across multiple generations

### 4. Fallback Tests
- [ ] Server fallback when worker fails
- [ ] Server fallback when geometry spec endpoint fails
- [ ] Server fallback when Worker not supported
- [ ] Graceful error messages on all failure modes

### 5. Download Tests
- [ ] STL file downloads correctly
- [ ] File size is reasonable (not bloated)
- [ ] STL opens in slicer software (Cura, PrusaSlicer, etc.)
- [ ] Geometry is watertight (no errors in slicer)

### 6. 3D Preview Tests
- [ ] Model renders correctly in Three.js viewer
- [ ] Camera positioning correct for cards vs cylinders
- [ ] OrbitControls work smoothly
- [ ] Theme changes apply to model color

## Known Limitations

### Current Implementation
1. **Cylinder spec extraction**: Not fully implemented - uses basic structure only
2. **Character markers**: Use simplified box geometry instead of text paths
3. **No multi-threading**: CSG operations are serial in Web Worker
4. **Memory**: Large models (500+ dots) may hit browser memory limits

### Compared to manifold3d
- **Robustness**: three-bvh-csg may have edge cases with non-manifold geometry
- **Performance**: ~10-100x slower than native manifold3d C++ (but still fast enough)
- **Output guarantees**: May not always produce perfectly watertight meshes

## Vercel Hobby Considerations

### Advantages of Client-Side Approach
- ✅ No 10-60 second timeout limits
- ✅ No serverless function cold starts
- ✅ No need for external binary dependencies
- ✅ Reduces server load (only serves geometry spec, not full STL)
- ✅ Works offline after initial page load

### Bundle Size Impact
- three.module.js: ~600 KB (already present)
- three-bvh-csg: ~50-80 KB
- three-mesh-bvh: ~150-200 KB
- STLExporter: ~5 KB
- csg-worker.js: ~10 KB
- **Total new**: ~215-295 KB minified (~60-80 KB gzipped)

### Feature Flag
- `useClientSideCSG` in public/index.html (line ~2417)
- Set to `false` to force server-side generation
- Automatically disabled if Worker initialization fails

## Next Steps for Testing

1. **Local Testing**:
   ```bash
   python wsgi.py
   # Visit http://localhost:5001
   # Open browser console for CSG Worker logs
   ```

2. **Test Cases**:
   - Start with simple single-line text
   - Check console for "CSG Worker initialized and ready"
   - Check for "Attempting client-side CSG generation..."
   - Verify download works and STL is valid

3. **Vercel Deploy**:
   - Deploy to Vercel preview
   - Test from multiple browsers
   - Monitor function logs for fallback usage
   - Check CDN caching still works for counter plates

4. **Edge Cases**:
   - Disable JavaScript → server fallback
   - Network issues during spec fetch
   - Worker timeout on very large models
   - Browser memory limits

## Debugging Commands

### Check Worker Status
Open browser console:
```javascript
console.log('Worker ready:', workerReady);
console.log('Use client-side:', useClientSideCSG);
```

### Force Server Fallback
```javascript
useClientSideCSG = false;
```

### Monitor Worker Messages
Already logged via existing `log` object in public/index.html

## Success Criteria

✅ Implementation is successful if:
1. Client-side CSG works in modern browsers (Chrome, Firefox, Safari)
2. Automatic fallback to server works reliably
3. Generated STLs match server-generated quality
4. Performance is acceptable (< 30s for typical models)
5. Bundle size increase is reasonable (< 300 KB)
6. No breaking changes to existing functionality
