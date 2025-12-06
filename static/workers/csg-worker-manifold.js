/**
 * CSG Worker using Manifold3D WASM for guaranteed manifold output
 *
 * This worker uses Manifold primitives for the entire CSG pipeline,
 * which guarantees watertight (manifold) meshes - no post-repair needed.
 *
 * Primarily designed for cylinder generation where three-bvh-csg produces
 * non-manifold edges due to complex curved surface boolean operations.
 */

let wasm = null;
let Manifold = null;
let CrossSection = null;
let Mesh = null;
let manifoldReady = false;
let initError = null;

// Initialize Manifold WASM module
async function initManifold() {
    if (wasm) return true;

    const manifoldUrls = [
        'https://cdn.jsdelivr.net/npm/manifold-3d@2.5.1/manifold.js',
        'https://unpkg.com/manifold-3d@2.5.1/manifold.js'
    ];

    for (const url of manifoldUrls) {
        try {
            console.log('Manifold CSG Worker: Attempting to load from', url);
            const module = await import(url);
            console.log('Manifold CSG Worker: Module imported, initializing WASM...');
            wasm = await module.default();
            wasm.setup();
            Manifold = wasm.Manifold;
            CrossSection = wasm.CrossSection;
            Mesh = wasm.Mesh;
            manifoldReady = true;
            console.log('Manifold CSG Worker: WASM loaded and initialized from', url);
            console.log('Manifold CSG Worker: Available classes:', Object.keys(wasm).join(', '));
            return true;
        } catch (e) {
            console.warn('Manifold CSG Worker: Failed to load from', url, ':', e.message);
            console.warn('Manifold CSG Worker: Error stack:', e.stack);
        }
    }

    throw new Error('Failed to load Manifold WASM from any CDN');
}

// Initialize on worker load
try {
    await initManifold();
    console.log('Manifold CSG Worker: Initialization complete, ready for requests');
} catch (error) {
    initError = error;
    console.error('Manifold CSG Worker: Initialization failed:', error.message);
}

/**
 * Create a cylinder using Manifold primitives
 * Manifold.cylinder(height, radiusLow, radiusHigh, circularSegments)
 * Creates a cylinder along the Z-axis, centered at origin
 */
function createManifoldCylinder(height, radius, segments = 64) {
    return Manifold.cylinder(height, radius, radius, segments, true);
}

/**
 * Create a cone frustum using Manifold primitives
 * For braille dots: base at bottom (Z=0), top at Z=height
 */
function createManifoldFrustum(baseRadius, topRadius, height, segments = 24) {
    // Manifold.cylinder creates along Z-axis, centered at origin
    // radiusLow is at -height/2, radiusHigh is at +height/2
    return Manifold.cylinder(height, baseRadius, topRadius, segments, true);
}

/**
 * Create a sphere using Manifold primitives
 */
function createManifoldSphere(radius, segments = 24) {
    return Manifold.sphere(radius, segments);
}

/**
 * Create a box using Manifold primitives
 * centered: if true, centered at origin; if false, corner at origin
 */
function createManifoldBox(width, height, depth, centered = true) {
    return Manifold.cube([width, height, depth], centered);
}

/**
 * Create a spherical cap (dome) for rounded dots
 * Uses sphere intersection with a half-space
 */
function createSphericalCap(radius, capHeight, segments = 24) {
    if (capHeight >= 2 * radius) {
        // Full hemisphere or more - just use hemisphere
        capHeight = radius;
    }

    const sphere = createManifoldSphere(radius, segments);

    // Create cutting box to trim sphere into a cap
    // The cap rises from z=0 to z=capHeight
    // Sphere center at z = capHeight - radius (so top of sphere is at z=capHeight)
    const sphereCenterZ = capHeight - radius;

    // Cut off everything below z=0
    const cutBoxSize = radius * 4;
    const cutBox = createManifoldBox(cutBoxSize, cutBoxSize, cutBoxSize, true);
    // Position cut box below z=0
    const positionedCutBox = cutBox.translate([0, 0, -cutBoxSize / 2]);

    // Position sphere and subtract cut box
    const positionedSphere = sphere.translate([0, 0, sphereCenterZ]);
    const cap = positionedSphere.subtract(positionedCutBox);

    // Clean up intermediate objects
    sphere.delete();
    cutBox.delete();
    positionedCutBox.delete();
    positionedSphere.delete();

    return cap;
}

/**
 * Create a braille dot on cylinder surface using Manifold primitives
 * Returns the dot geometry positioned and oriented on the cylinder
 */
function createCylinderDotManifold(spec) {
    const { x, y, z, theta, radius: cylRadius, params, is_recess } = spec;

    // Validate parameters
    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0 || !params) {
        console.warn('createCylinderDotManifold: Invalid parameters, skipping dot');
        return null;
    }

    // CRITICAL: Negate theta to match Three.js coordinate convention
    // Three.js (Y-up) after rotateX(π/2) gives: (cos(θ), -sin(θ), height)
    // Manifold (Z-up) natively gives: (cos(θ), sin(θ), height)
    // Negating theta makes sin(-θ) = -sin(θ), matching Three.js output
    // This ensures braille cells are generated in the correct order
    // See BRAILLE_SPACING_SPECIFICATIONS.md Section 10: Coordinate Systems
    const adjustedTheta = -theta;

    const shape = params.shape || 'standard';
    const isRecess = is_recess || shape === 'hemisphere' || shape === 'bowl';

    let dot = null;
    let dotHeight = 0;

    try {
        if (shape === 'rounded') {
            // Rounded dot: frustum base + spherical cap
            const baseRadius = (params.base_radius > 0) ? params.base_radius : 1.0;
            const topRadius = (params.top_radius > 0) ? params.top_radius : baseRadius;
            const baseHeight = (params.base_height >= 0) ? params.base_height : 0.2;
            const domeHeight = (params.dome_height > 0) ? params.dome_height : 0.6;
            const domeRadius = (params.dome_radius > 0) ? params.dome_radius : Math.max(topRadius, 0.5);

            dotHeight = baseHeight + domeHeight;

            if (baseHeight > 0) {
                // Create frustum base
                const frustum = createManifoldFrustum(baseRadius, topRadius, baseHeight, 24);
                // Frustum is centered at origin, move so base is at z=0
                const positionedFrustum = frustum.translate([0, 0, baseHeight / 2]);
                frustum.delete();

                // Create dome on top of frustum
                const dome = createSphericalCap(domeRadius, domeHeight, 24);
                const positionedDome = dome.translate([0, 0, baseHeight]);
                dome.delete();

                // Union frustum and dome
                dot = positionedFrustum.add(positionedDome);
                positionedFrustum.delete();
                positionedDome.delete();
            } else {
                // Dome only
                dot = createSphericalCap(domeRadius, domeHeight, 24);
            }

        } else if (shape === 'hemisphere') {
            // Hemisphere recess
            const recessRadius = (params.recess_radius > 0) ? params.recess_radius : 1.0;
            dotHeight = recessRadius;
            // Full sphere for better subtraction (positioned so half is in cylinder)
            dot = createManifoldSphere(recessRadius, 24);

        } else if (shape === 'bowl') {
            // Bowl (spherical cap) recess
            const bowlRadius = (params.bowl_radius > 0) ? params.bowl_radius : 1.5;
            const bowlDepth = (params.bowl_depth > 0) ? params.bowl_depth : 0.8;
            dotHeight = bowlDepth;
            // Calculate sphere radius for bowl
            const sphereR = (bowlRadius * bowlRadius + bowlDepth * bowlDepth) / (2.0 * bowlDepth);
            dot = createManifoldSphere(sphereR, 24);

        } else if (shape === 'cone') {
            // Cone frustum recess - large opening at surface, small tip inward
            const baseRadius = (params.base_radius > 0) ? params.base_radius : 1.0;
            const topRadius = (params.top_radius >= 0) ? params.top_radius : 0.25;
            const height = (params.height > 0) ? params.height : 1.0;
            dotHeight = height;
            // Swap radii for recess: large at top (surface), small at bottom (inside)
            dot = createManifoldFrustum(topRadius, baseRadius, height, 24);

        } else {
            // Standard frustum for positive embossing
            const baseRadius = (params.base_radius > 0) ? params.base_radius : 0.8;
            const topRadius = (params.top_radius >= 0) ? params.top_radius : 0.25;
            const height = (params.height > 0) ? params.height : 0.5;
            dotHeight = height;
            dot = createManifoldFrustum(baseRadius, topRadius, height, 24);
        }

        if (!dot) return null;

        // Position dot on cylinder surface
        // Dot is created along Z-axis, need to rotate to point radially outward

        const isSpherical = (shape === 'hemisphere' || shape === 'bowl');

        let radialOffset;
        if (isRecess) {
            if (shape === 'cone') {
                radialOffset = cylRadius - dotHeight / 2;
            } else {
                radialOffset = cylRadius;
            }
        } else {
            radialOffset = cylRadius + dotHeight / 2;
        }

        // For Manifold, we work in Z-up coordinate system
        // Cylinder axis is along Z, dots need to point radially outward in XY plane
        // Using adjustedTheta (negated) to match Three.js coordinate convention

        let positionedDot;
        if (isSpherical) {
            // Spherical shapes don't need rotation, just translation
            const posX = radialOffset * Math.cos(adjustedTheta);
            const posY = radialOffset * Math.sin(adjustedTheta);
            const posZ = isFinite(y) ? y : 0; // Y in spec becomes Z in Manifold coords
            positionedDot = dot.translate([posX, posY, posZ]);
            dot.delete();
        } else {
            // Non-spherical: rotate so Z-axis points radially outward at angle adjustedTheta
            // Rotate 90° around Y to make dot point along X
            // NOTE: rotate() takes (xDeg, yDeg, zDeg) as separate args, not an array
            const rotatedDot = dot.rotate(0, 90, 0);
            dot.delete();

            // Then rotate around Z by adjustedTheta to point at correct angle
            const thetaDeg = adjustedTheta * 180 / Math.PI;
            const rotatedDot2 = rotatedDot.rotate(0, 0, thetaDeg);
            rotatedDot.delete();

            // Translate to position
            const posX = radialOffset * Math.cos(adjustedTheta);
            const posY = radialOffset * Math.sin(adjustedTheta);
            const posZ = isFinite(y) ? y : 0;
            positionedDot = rotatedDot2.translate([posX, posY, posZ]);
            rotatedDot2.delete();
        }

        return positionedDot;

    } catch (error) {
        console.error('createCylinderDotManifold error:', error.message);
        if (dot) dot.delete();
        return null;
    }
}

/**
 * Create a triangle marker on cylinder surface using Manifold
 * Creates a proper triangular prism using convex hull of 6 points
 */
function createCylinderTriangleMarkerManifold(spec) {
    const { x, y, z, theta, radius: cylRadius, size, depth, is_recess, rotate_180 } = spec;

    console.log(`createCylinderTriangleMarkerManifold: theta=${theta?.toFixed(3)}, cylRadius=${cylRadius}, is_recess=${is_recess}, rotate_180=${rotate_180}`);

    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderTriangleMarkerManifold: Invalid parameters');
        return null;
    }

    // CRITICAL: Negate theta to match Three.js coordinate convention
    // See BRAILLE_SPACING_SPECIFICATIONS.md Section 10: Coordinate Systems
    const adjustedTheta = -theta;

    // CRITICAL: Invert rotate_180 to compensate for theta negation
    // When theta is negated, the rotation around Z also flips direction,
    // which would swap the triangle orientation. We invert rotate_180 to
    // counteract this effect and match the Three.js output.
    // - Embossing plate (rotate_180=false in spec) → use true here → apex points LEFT after mirroring
    // - Counter plate (rotate_180=true in spec) → use false here → apex points RIGHT after mirroring
    // After the adjustedTheta rotation, this produces the correct final orientation.
    const adjustedRotate180 = !rotate_180;

    const validSize = (size > 0) ? size : 2.0;
    const validDepth = (depth > 0) ? depth : 0.6;
    const recessPadding = is_recess ? 0.2 : 0;
    const extrudeDepth = validDepth + recessPadding;

    try {
        // Triangle vertices in the XZ plane (X = tangent direction, Z = cylinder axis)
        // Y will be the depth (radial) direction
        // Triangle: base is vertical (along Z), apex points in X direction

        let v1, v2, v3;  // Three vertices of the triangle
        if (adjustedRotate180) {
            // Rotated triangle - apex points left (-X)
            v1 = [validSize / 2, 0, validSize];    // top-right
            v2 = [validSize / 2, 0, -validSize];   // bottom-right
            v3 = [-validSize / 2, 0, 0];           // apex left
        } else {
            // Normal triangle - apex points right (+X)
            v1 = [-validSize / 2, 0, -validSize];  // bottom-left
            v2 = [-validSize / 2, 0, validSize];   // top-left
            v3 = [validSize / 2, 0, 0];            // apex right
        }

        // Create 6 small spheres at the front and back of each vertex
        const sphereRadius = 0.05;  // Small spheres for hull
        const halfDepth = extrudeDepth / 2;

        const spheres = [];
        for (const v of [v1, v2, v3]) {
            // Front face (positive Y)
            const sFront = createManifoldSphere(sphereRadius, 6);
            const pFront = sFront.translate([v[0], halfDepth, v[2]]);
            sFront.delete();
            spheres.push(pFront);

            // Back face (negative Y)
            const sBack = createManifoldSphere(sphereRadius, 6);
            const pBack = sBack.translate([v[0], -halfDepth, v[2]]);
            sBack.delete();
            spheres.push(pBack);
        }

        // Union all spheres and compute convex hull to get triangular prism
        const allSpheres = Manifold.union(spheres);
        spheres.forEach(s => s.delete());

        const prism = allSpheres.hull();
        allSpheres.delete();

        // Rotate so Y (depth) points radially outward at angle adjustedTheta
        // Rotate around Z axis by (adjustedTheta - 90°) to make +Y point toward radial direction
        const thetaDeg = adjustedTheta * 180 / Math.PI;
        const rotated = prism.rotate(0, 0, thetaDeg - 90);
        prism.delete();

        // Position at cylinder surface
        let radialOffset;
        if (is_recess) {
            radialOffset = cylRadius - validDepth / 2;
        } else {
            radialOffset = cylRadius + validDepth / 2 + 0.05;
        }

        const posX = radialOffset * Math.cos(adjustedTheta);
        const posY = radialOffset * Math.sin(adjustedTheta);
        const posZ = isFinite(y) ? y : 0;

        console.log(`createCylinderTriangleMarkerManifold: positioning at (${posX.toFixed(2)}, ${posY.toFixed(2)}, ${posZ.toFixed(2)})`);

        const positioned = rotated.translate([posX, posY, posZ]);
        rotated.delete();

        return positioned;

    } catch (error) {
        console.error('createCylinderTriangleMarkerManifold error:', error.message, error.stack);
        return null;
    }
}

/**
 * Create a rectangular marker on cylinder surface using Manifold
 */
function createCylinderRectMarkerManifold(spec) {
    const { x, y, z, theta, radius: cylRadius, width, height, depth, is_recess } = spec;

    console.log(`createCylinderRectMarkerManifold: theta=${theta?.toFixed(3)}, cylRadius=${cylRadius}, width=${width}, height=${height}, depth=${depth}, is_recess=${is_recess}`);

    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderRectMarkerManifold: Invalid parameters');
        return null;
    }

    // CRITICAL: Negate theta to match Three.js coordinate convention
    // See BRAILLE_SPACING_SPECIFICATIONS.md Section 10: Coordinate Systems
    const adjustedTheta = -theta;

    const validWidth = (width > 0) ? width : 2.0;
    const validHeight = (height > 0) ? height : 4.0;
    const validDepth = (depth > 0) ? depth : 0.5;

    try {
        // Create box: In Manifold cube([x, y, z]), dimensions are along X, Y, Z axes
        // We want: width along the tangent direction, height along cylinder axis, depth radially
        // After rotation, depth will point radially outward
        //
        // In Manifold Z-up: cylinder axis is Z, radial is XY plane
        // Create box with width along X (will become tangent), height along Z (stays along cylinder), depth along Y (will become radial after rotation)
        // Wait, that's not right...
        //
        // Let me reconsider: after rotate(0, 90, 0), Z becomes X (radial direction at theta=0)
        // So initially: width=X, height=Y, depth=Z
        // After rotate(0, 90, 0): width stays as tangent, height=Y, old-Z now points along X
        // After rotate(0, 0, theta): X points radially at angle theta
        //
        // But height should be along the cylinder axis (Z), not Y!
        // So I need: width=X (tangent), height=Z (cylinder axis), depth=Y (will become radial)
        // This means I should create cube([width, depth, height]) so that after rotations it's correct

        // Actually let me trace through more carefully:
        // Start: cube([width, height, depth]) = X=width, Y=height, Z=depth
        // We want: width in tangent direction, height along cylinder Z-axis, depth pointing radially
        // After rotate(0, 90, 0): Z->X, X->-Z, Y stays
        //   So: old-X=width -> new-(-Z), old-Y=height -> new-Y, old-Z=depth -> new-X
        // After rotate(0, 0, theta): X,Y rotate in XY plane
        //   X -> X*cos(theta) - Y*sin(theta)
        //   Y -> X*sin(theta) + Y*cos(theta)
        //
        // After both rotations:
        //   depth (was Z) is now pointing radially at angle theta ✓
        //   height (was Y) is still along Y, not Z!
        //
        // This is the bug! I need height to end up along Z (cylinder axis)

        // Correct approach: create cube([width, depth, height])
        // Start: X=width, Y=depth, Z=height
        // After rotate(0, 90, 0): Z->X, X->-Z, Y stays
        //   old-X=width -> new-(-Z), old-Y=depth -> new-Y, old-Z=height -> new-X
        // Hmm, this still puts height along X, not Z...

        // Let me think differently. I want:
        // - Final width (tangent) = should not be affected by radial rotation
        // - Final height along Z (cylinder axis)
        // - Final depth pointing radially at angle theta
        //
        // If I rotate(0, 0, theta) only, the Z axis stays fixed, and X,Y rotate.
        // So height should be along Z from the start.
        // Width should be along the direction perpendicular to radial in the XY plane.
        // Depth should be along X before rotation (so it points radially after rotate(0,0,theta)).
        //
        // Create cube([depth, width, height]) with depth along X, width along Y, height along Z
        // After rotate(0, 0, theta): X -> radial at theta, Y -> tangent at theta, Z stays
        // This gives: depth radial, width tangent, height along cylinder ✓
        //
        // But wait, I also have rotate(0, 90, 0) which changes things...
        // Let me remove the Y rotation and just do Z rotation.

        // Actually, the simplest fix is to just swap width and height in the box creation
        // so that after the Y rotation, height ends up along Z.

        // Let me try: create box with dimensions arranged differently
        // Create cube([width, validDepth, height])
        const box = Manifold.cube([validWidth, validDepth, validHeight], true);

        // Only rotate around Z to point toward the radial direction
        // Since depth is along Y, we need to rotate so Y points radially
        // rotate(0, 0, adjustedTheta-90) would rotate Y to point at angle adjustedTheta
        const thetaDeg = adjustedTheta * 180 / Math.PI;
        const rotated = box.rotate(0, 0, thetaDeg - 90);
        box.delete();

        // Position at cylinder surface
        let radialOffset;
        if (is_recess) {
            radialOffset = cylRadius - validDepth / 2;
        } else {
            radialOffset = cylRadius + validDepth / 2 + 0.05;
        }

        const posX = radialOffset * Math.cos(adjustedTheta);
        const posY = radialOffset * Math.sin(adjustedTheta);
        const posZ = isFinite(y) ? y : 0;

        console.log(`createCylinderRectMarkerManifold: positioning at (${posX.toFixed(2)}, ${posY.toFixed(2)}, ${posZ.toFixed(2)})`);

        const positioned = rotated.translate([posX, posY, posZ]);
        rotated.delete();

        return positioned;

    } catch (error) {
        console.error('createCylinderRectMarkerManifold error:', error.message, error.stack);
        return null;
    }
}

/**
 * Clean Sans-Serif 8x8 Bitmap Font
 *
 * A minimal, geometric sans-serif font designed for clarity at small sizes.
 * No serifs, no decorative flourishes - pure functional letterforms.
 *
 * Each character is an 8x8 bitmap represented as 8 bytes.
 * Each byte represents one row (top to bottom), with bit 0 being the leftmost pixel.
 * A set bit (1) means the pixel is "on" and should be rendered as a box.
 *
 * Visual guide for hex values:
 *   0x00 = 00000000 = ........
 *   0x18 = 00011000 = ...██...
 *   0x3C = 00111100 = ..████..
 *   0x7E = 01111110 = .██████.
 *   0x66 = 01100110 = .██..██.
 */
const FONT8X8_BASIC = {
    // Letters A-Z (Clean Sans-Serif)
    'A': [
        0x18,  // ...██...
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x7E,  // .██████.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x00   // ........
    ],
    'B': [
        0x3E,  // .█████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3E,  // .█████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3E,  // .█████..
        0x00   // ........
    ],
    'C': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    'D': [
        0x1E,  // .████...
        0x36,  // .██.██..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x36,  // .██.██..
        0x1E,  // .████...
        0x00   // ........
    ],
    'E': [
        0x7E,  // .██████.
        0x06,  // .....██.
        0x06,  // .....██.
        0x3E,  // .█████..
        0x06,  // .....██.
        0x06,  // .....██.
        0x7E,  // .██████.
        0x00   // ........
    ],
    'F': [
        0x7E,  // .██████.
        0x06,  // .....██.
        0x06,  // .....██.
        0x3E,  // .█████..
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x00   // ........
    ],
    'G': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x06,  // .....██.
        0x76,  // .███.██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    'H': [
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x7E,  // .██████.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x00   // ........
    ],
    'I': [
        0x3C,  // ..████..
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x3C,  // ..████..
        0x00   // ........
    ],
    'J': [
        0x60,  // .....██.
        0x60,  // .....██.
        0x60,  // .....██.
        0x60,  // .....██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    'K': [
        0x66,  // .██..██.
        0x36,  // .██.██..
        0x1E,  // .████...
        0x0E,  // .███....
        0x1E,  // .████...
        0x36,  // .██.██..
        0x66,  // .██..██.
        0x00   // ........
    ],
    'L': [
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x7E,  // .██████.
        0x00   // ........
    ],
    'M': [
        0x63,  // ██...██.
        0x77,  // ███.███.
        0x7F,  // ███████.
        0x6B,  // ██.█.██.
        0x63,  // ██...██.
        0x63,  // ██...██.
        0x63,  // ██...██.
        0x00   // ........
    ],
    'N': [
        0x66,  // .██..██.
        0x6E,  // .███.██.
        0x7E,  // .██████.
        0x76,  // .███.██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x00   // ........
    ],
    'O': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    'P': [
        0x3E,  // .█████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3E,  // .█████..
        0x06,  // .....██.
        0x06,  // .....██.
        0x06,  // .....██.
        0x00   // ........
    ],
    'Q': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x76,  // .███.██.
        0x3C,  // ..████..
        0x60,  // .....██.
        0x00   // ........
    ],
    'R': [
        0x3E,  // .█████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3E,  // .█████..
        0x36,  // .██.██..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x00   // ........
    ],
    'S': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x0C,  // ..██....
        0x18,  // ...██...
        0x30,  // ....██..
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    'T': [
        0x7E,  // .██████.
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x00   // ........
    ],
    'U': [
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    'V': [
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x18,  // ...██...
        0x00   // ........
    ],
    'W': [
        0x63,  // ██...██.
        0x63,  // ██...██.
        0x63,  // ██...██.
        0x6B,  // ██.█.██.
        0x7F,  // ███████.
        0x77,  // ███.███.
        0x63,  // ██...██.
        0x00   // ........
    ],
    'X': [
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x18,  // ...██...
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x00   // ........
    ],
    'Y': [
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x00   // ........
    ],
    'Z': [
        0x7E,  // .██████.
        0x60,  // .....██.
        0x30,  // ....██..
        0x18,  // ...██...
        0x0C,  // ..██....
        0x06,  // .....██.
        0x7E,  // .██████.
        0x00   // ........
    ],
    // Numbers 0-9 (Clean Sans-Serif)
    '0': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x76,  // .███.██.
        0x6E,  // .███.██.
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    '1': [
        0x18,  // ...██...
        0x1C,  // ..███...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x00   // ........
    ],
    '2': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x60,  // .....██.
        0x30,  // ....██..
        0x18,  // ...██...
        0x0C,  // ..██....
        0x7E,  // .██████.
        0x00   // ........
    ],
    '3': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x60,  // .....██.
        0x38,  // ...███..
        0x60,  // .....██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    '4': [
        0x30,  // ....██..
        0x38,  // ...███..
        0x3C,  // ..████..
        0x36,  // .██.██..
        0x7E,  // .██████.
        0x30,  // ....██..
        0x30,  // ....██..
        0x00   // ........
    ],
    '5': [
        0x7E,  // .██████.
        0x06,  // .....██.
        0x3E,  // .█████..
        0x60,  // .....██.
        0x60,  // .....██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    '6': [
        0x38,  // ...███..
        0x0C,  // ..██....
        0x06,  // .....██.
        0x3E,  // .█████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    '7': [
        0x7E,  // .██████.
        0x60,  // .....██.
        0x30,  // ....██..
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x18,  // ...██...
        0x00   // ........
    ],
    '8': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x3C,  // ..████..
        0x00   // ........
    ],
    '9': [
        0x3C,  // ..████..
        0x66,  // .██..██.
        0x66,  // .██..██.
        0x7C,  // ..█████.
        0x60,  // .....██.
        0x30,  // ....██..
        0x1C,  // ..███...
        0x00   // ........
    ]
};

/**
 * Create a letter shape from font8x8 bitmap data using Manifold box primitives
 *
 * Converts the 8x8 bitmap into Manifold boxes, one for each "on" pixel.
 * The letter is created in the XZ plane (X=width, Z=height) with Y=depth.
 * Origin is at the center of the bounding box.
 *
 * @param {string} char - Single character (A-Z, 0-9)
 * @param {number} width - Total width of the character bounding box
 * @param {number} height - Total height of the character bounding box
 * @param {number} depth - Extrusion depth (Y direction)
 * @returns {Object|null} Manifold object or null if character not supported
 */
function createLetterShapeManifold(char, width, height, depth) {
    const c = (char || '').toUpperCase();

    // Get the bitmap data for this character
    const bitmap = FONT8X8_BASIC[c];
    if (!bitmap) {
        console.log(`createLetterShapeManifold: Character '${c}' not in font, falling back to rectangle`);
        return null;
    }

    // Calculate pixel dimensions
    // The font is 8x8, but we use 7x8 effective area (rightmost column often empty)
    const gridCols = 7;  // Effective columns used in font8x8
    const gridRows = 8;  // Rows in the font

    const pixelW = width / gridCols;   // Width of each pixel box
    const pixelH = height / gridRows;  // Height of each pixel box

    // Half dimensions for centering
    const halfW = width / 2;
    const halfH = height / 2;

    const parts = [];

    try {
        // Iterate through the bitmap
        // Row 0 is at the top (highest Z), row 7 is at the bottom (lowest Z)
        for (let row = 0; row < gridRows; row++) {
            const rowData = bitmap[row];

            for (let col = 0; col < gridCols; col++) {
                // Check if this pixel is "on" (bit is set)
                // Bit 0 is leftmost pixel in the font definition
                if ((rowData >> col) & 1) {
                    // Calculate position for this pixel box
                    // MIRROR horizontally: col 0 at RIGHT (+halfW), col 6 at LEFT (-halfW)
                    // This is necessary because the letter is viewed from OUTSIDE the cylinder.
                    // Without mirroring, letters appear reversed (like reading text through glass).
                    const posX = halfW - (col + 0.5) * pixelW;

                    // Z: row 0 is at top (+halfH), row 7 is at bottom (-halfH)
                    const posZ = halfH - (row + 0.5) * pixelH;

                    // Create a box for this pixel
                    const box = Manifold.cube([pixelW, depth, pixelH], true);
                    const positioned = box.translate([posX, 0, posZ]);
                    box.delete();

                    parts.push(positioned);
                }
            }
        }

        if (parts.length === 0) {
            console.warn(`createLetterShapeManifold: No pixels found for character '${c}'`);
            return null;
        }

        // Union all pixel boxes into a single manifold
        const result = Manifold.union(parts);
        parts.forEach(p => p.delete());

        console.log(`createLetterShapeManifold: Created letter '${c}' from ${parts.length} pixel boxes`);
        return result;

    } catch (error) {
        console.error(`createLetterShapeManifold: Error creating letter '${c}':`, error.message);
        // Clean up any created parts
        parts.forEach(p => { try { p.delete(); } catch (e) { } });
        return null;
    }
}

/**
 * Create a character marker on cylinder surface using Manifold
 * Creates actual letter/number shapes using Manifold primitives (boxes combined)
 *
 * Character marker dimensions fit within the braille cell boundary:
 * - Character Width: dot_spacing (horizontal/tangential direction)
 * - Character Height: 2 × dot_spacing (vertical/cylinder axis direction)
 * - Recess Depth: 0.5mm (default, matches rectangle marker depth)
 *
 * Viewing orientation (from outer cylinder surface, cylinder axis vertical):
 * - Width = left-right direction = dot_spacing
 * - Height = top-bottom direction = 2 × dot_spacing
 *
 * Falls back to rectangle marker if character rendering fails
 */
function createCylinderCharacterMarkerManifold(spec) {
    const { x, y, z, theta, radius: cylRadius, char, size, depth, is_recess } = spec;

    console.log(`createCylinderCharacterMarkerManifold: char='${char}', theta=${theta?.toFixed(3)}, cylRadius=${cylRadius}, size=${size}, depth=${depth}, is_recess=${is_recess}, y=${y}`);

    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderCharacterMarkerManifold: Invalid parameters');
        return null;
    }

    // Calculate dimensions to fit within braille cell boundary
    // size is dot_spacing * 1.5 (from geometry_spec.py line 837)
    const dotSpacing = size && size > 0 ? size / 1.5 : 2.5;

    // Character fits within braille cell perimeter:
    // - Width (tangential): dot_spacing (e.g., 2.5mm)
    // - Height (axial): 2 × dot_spacing (e.g., 5.0mm)
    const charWidth = dotSpacing;           // Fits within cell width
    const charHeight = 2 * dotSpacing;      // Fits within cell height
    const validDepth = depth > 0 ? depth : 0.5;   // 0.5mm depth (matches rectangle marker)

    console.log(`createCylinderCharacterMarkerManifold: Calculated dimensions - dotSpacing=${dotSpacing.toFixed(2)}, width=${charWidth.toFixed(2)}, height=${charHeight.toFixed(2)}, depth=${validDepth.toFixed(2)}`);

    // CRITICAL: Negate theta to match Three.js coordinate convention
    // See BRAILLE_SPACING_SPECIFICATIONS.md Section 10: Coordinate Systems
    const adjustedTheta = -theta;

    try {
        // Try to create the actual letter shape
        let letterShape = createLetterShapeManifold(char, charWidth, charHeight, validDepth);

        if (!letterShape) {
            // Letter not supported or creation failed - fall back to rectangle
            console.log(`createCylinderCharacterMarkerManifold: Falling back to rectangle for char '${char}'`);

            // Create simple rectangle as fallback (per spec, uses 0.5mm depth for fallback)
            const rectSpec = {
                x: x,
                y: y,
                z: z,
                theta: theta,
                radius: cylRadius,
                width: dotSpacing,
                height: 2 * dotSpacing,
                depth: 0.5,  // Fallback depth per spec
                is_recess: is_recess
            };
            return createCylinderRectMarkerManifold(rectSpec);
        }

        // Rotate so depth (Y) points radially outward
        // After rotation: Y axis points toward radial direction at angle adjustedTheta
        const thetaDeg = adjustedTheta * 180 / Math.PI;
        const rotated = letterShape.rotate(0, 0, thetaDeg - 90);
        letterShape.delete();

        // Position on cylinder surface
        let radialOffset;
        if (is_recess) {
            radialOffset = cylRadius - validDepth / 2;
        } else {
            radialOffset = cylRadius + validDepth / 2 + 0.05;
        }

        const posX = radialOffset * Math.cos(adjustedTheta);
        const posY = radialOffset * Math.sin(adjustedTheta);
        const posZ = isFinite(y) ? y : 0;

        console.log(`createCylinderCharacterMarkerManifold: Positioning '${char}' at (${posX.toFixed(2)}, ${posY.toFixed(2)}, ${posZ.toFixed(2)}), radialOffset=${radialOffset.toFixed(2)}`);

        const positioned = rotated.translate([posX, posY, posZ]);
        rotated.delete();

        return positioned;

    } catch (error) {
        console.error('createCylinderCharacterMarkerManifold error:', error.message, error.stack);

        // Spec fallback: rectangle marker with 0.5mm depth
        console.log(`createCylinderCharacterMarkerManifold: Error occurred, falling back to rectangle`);
        const rectSpec = {
            x: x,
            y: y,
            z: z,
            theta: theta,
            radius: cylRadius,
            width: dotSpacing,
            height: 2 * dotSpacing,
            depth: 0.5,
            is_recess: is_recess
        };

        return createCylinderRectMarkerManifold(rectSpec);
    }
}

/**
 * Create cylinder shell with polygonal cutout using Manifold
 */
function createCylinderShellManifold(spec) {
    const { radius, height, thickness, polygon_points } = spec;

    const validRadius = (radius > 0) ? radius : 30;
    const validHeight = (height > 0) ? height : 80;
    const validThickness = (thickness > 0) ? thickness : 2;

    try {
        // Create outer cylinder
        const outer = createManifoldCylinder(validHeight, validRadius, 64);

        // Check for polygon cutout
        const validPoints = (polygon_points && polygon_points.length >= 3)
            ? polygon_points.filter(pt => pt && isFinite(pt.x) && isFinite(pt.y))
            : [];

        if (validPoints.length >= 3) {
            // Use polygon as inner boundary
            const polyPoints = validPoints.map(pt => [pt.x, pt.y]);
            const crossSection = new CrossSection([polyPoints], 'NonNegative');

            // Extrude polygon slightly longer than cylinder height
            const cutoutHeight = validHeight * 1.5;
            const cutout = Manifold.extrude(crossSection, cutoutHeight);
            crossSection.delete();

            // Center the cutout
            const centeredCutout = cutout.translate([0, 0, -cutoutHeight / 2]);
            cutout.delete();

            // Subtract polygon from outer cylinder
            const shell = outer.subtract(centeredCutout);
            outer.delete();
            centeredCutout.delete();

            console.log('Manifold CSG Worker: Created cylinder shell with polygon cutout');
            return shell;
        } else {
            // No polygon - create hollow cylinder using wall thickness
            const innerRadius = validRadius - validThickness;
            if (innerRadius > 0) {
                const inner = createManifoldCylinder(validHeight + 0.2, innerRadius, 64);
                const shell = outer.subtract(inner);
                outer.delete();
                inner.delete();
                console.log('Manifold CSG Worker: Created hollow cylinder shell');
                return shell;
            } else {
                console.log('Manifold CSG Worker: Created solid cylinder');
                return outer;
            }
        }

    } catch (error) {
        console.error('createCylinderShellManifold error:', error.message);
        throw error;
    }
}

/**
 * Batch union multiple Manifold objects efficiently
 */
function batchUnionManifold(manifolds) {
    if (manifolds.length === 0) return null;
    if (manifolds.length === 1) return manifolds[0];

    // Use Manifold's batch operation for efficiency
    try {
        const result = Manifold.union(manifolds);
        // Clean up input manifolds
        manifolds.forEach(m => { if (m) m.delete(); });
        return result;
    } catch (e) {
        // Fallback to sequential union
        console.warn('Manifold batch union failed, using sequential:', e.message);
        let result = manifolds[0];
        for (let i = 1; i < manifolds.length; i++) {
            const newResult = result.add(manifolds[i]);
            result.delete();
            manifolds[i].delete();
            result = newResult;
        }
        return result;
    }
}

/**
 * Process geometry spec using Manifold primitives
 * This is the main entry point for geometry generation
 */
function processGeometrySpec(spec) {
    const { shape_type, plate_type, plate, dots, markers, cylinder } = spec;
    const isNegative = plate_type === 'negative';
    const isCylinder = shape_type === 'cylinder';

    console.log(`Manifold CSG Worker: Processing ${shape_type} ${plate_type} with ${dots?.length || 0} dots and ${markers?.length || 0} markers`);

    const manifoldsToCleanup = [];

    try {
        // Create base geometry
        let base;

        if (isCylinder && cylinder) {
            base = createCylinderShellManifold(cylinder);
            console.log('Manifold CSG Worker: Created cylinder shell');
        } else {
            // Card plate - simple box
            const { width, height, thickness, center_x, center_y, center_z } = plate;
            base = createManifoldBox(width, height, thickness, true);
            const translatedBase = base.translate([center_x, center_y, center_z]);
            base.delete();
            base = translatedBase;
            console.log('Manifold CSG Worker: Created card plate');
        }

        // Collect dot manifolds
        const dotManifolds = [];

        if (dots && dots.length > 0) {
            console.log(`Manifold CSG Worker: Creating ${dots.length} dots`);
            let successCount = 0;

            for (const dotSpec of dots) {
                try {
                    let dotManifold;
                    if (dotSpec.type === 'cylinder_dot') {
                        dotManifold = createCylinderDotManifold(dotSpec);
                    } else {
                        // Flat card dot - use simple geometry
                        const { x, y, z, type, params } = dotSpec;
                        if (type === 'rounded' && params) {
                            const baseRadius = params.base_radius || 0.8;
                            const height = (params.base_height || 0) + (params.dome_height || 0.5);
                            const sphere = createManifoldSphere(baseRadius, 16);
                            const scaled = sphere.scale([1, 1, height / (2 * baseRadius)]);
                            sphere.delete();
                            const translated = scaled.translate([x, y, z]);
                            scaled.delete();
                            dotManifold = translated;
                        } else {
                            const baseRadius = params?.base_radius || 0.8;
                            const topRadius = params?.top_radius || 0.25;
                            const height = params?.height || 0.5;
                            const frustum = createManifoldFrustum(baseRadius, topRadius, height, 16);
                            const translated = frustum.translate([x, y, z]);
                            frustum.delete();
                            dotManifold = translated;
                        }
                    }

                    if (dotManifold) {
                        dotManifolds.push(dotManifold);
                        successCount++;
                    }
                } catch (err) {
                    console.warn(`Manifold CSG Worker: Failed to create dot:`, err.message);
                }
            }
            console.log(`Manifold CSG Worker: Created ${successCount}/${dots.length} dots successfully`);
        }

        // Collect marker manifolds
        const markerManifolds = [];

        if (markers && markers.length > 0) {
            console.log(`Manifold CSG Worker: Creating ${markers.length} markers`);

            // Log all markers to detect potential overlaps
            const markerPositions = {};
            for (let i = 0; i < markers.length; i++) {
                const m = markers[i];
                const posKey = `theta:${m.theta?.toFixed(3)}_y:${m.y?.toFixed(2)}`;
                if (!markerPositions[posKey]) {
                    markerPositions[posKey] = [];
                }
                markerPositions[posKey].push({ index: i, type: m.type });
            }

            // Warn about potential overlaps
            for (const [pos, items] of Object.entries(markerPositions)) {
                if (items.length > 1) {
                    console.warn(`Manifold CSG Worker: POTENTIAL OVERLAP at ${pos}:`, items.map(i => `${i.index}:${i.type}`).join(', '));
                }
            }

            let markerSuccessCount = 0;

            for (let i = 0; i < markers.length; i++) {
                const markerSpec = markers[i];
                try {
                    let markerManifold = null;
                    console.log(`Manifold CSG Worker: Creating marker ${i}: type=${markerSpec.type}, theta=${markerSpec.theta?.toFixed(3)}, y=${markerSpec.y?.toFixed(2)}, char=${markerSpec.char || 'N/A'}`);

                    if (markerSpec.type === 'cylinder_triangle') {
                        markerManifold = createCylinderTriangleMarkerManifold(markerSpec);
                    } else if (markerSpec.type === 'cylinder_rect') {
                        console.log('Processing cylinder_rect marker:', markerSpec);
                        markerManifold = createCylinderRectMarkerManifold(markerSpec);
                    } else if (markerSpec.type === 'cylinder_character') {
                        console.log('Processing cylinder_character marker:', markerSpec);
                        markerManifold = createCylinderCharacterMarkerManifold(markerSpec);
                    } else if (markerSpec.type === 'rect') {
                        const { x, y, z, width, height, depth } = markerSpec;
                        const box = createManifoldBox(width, height, depth, true);
                        markerManifold = box.translate([x, y, z]);
                        box.delete();
                    } else if (markerSpec.type === 'triangle') {
                        const { x, y, z, size, depth } = markerSpec;
                        const points = [
                            [-size / 2, -size],
                            [-size / 2, size],
                            [size / 2, 0]
                        ];
                        const crossSection = new CrossSection([points], 'Positive');
                        const extruded = Manifold.extrude(crossSection, depth);
                        crossSection.delete();
                        markerManifold = extruded.translate([x, y, z - depth / 2]);
                        extruded.delete();
                    } else {
                        console.warn(`Manifold CSG Worker: Unknown marker type: ${markerSpec.type}`);
                    }

                    if (markerManifold) {
                        markerManifolds.push(markerManifold);
                        markerSuccessCount++;
                        console.log(`Manifold CSG Worker: Marker ${i} created successfully`);
                    } else {
                        console.warn(`Manifold CSG Worker: Marker ${i} returned null`);
                    }
                } catch (err) {
                    console.error(`Manifold CSG Worker: Failed to create marker ${i}:`, err.message, err.stack);
                }
            }
            console.log(`Manifold CSG Worker: Created ${markerSuccessCount}/${markers.length} markers successfully`);
        } else {
            console.log('Manifold CSG Worker: No markers to process');
        }

        // Perform CSG operations
        let result = base;

        // Process dots
        if (dotManifolds.length > 0) {
            console.log(`Manifold CSG Worker: Processing ${dotManifolds.length} dots`);
            const unionedDots = batchUnionManifold(dotManifolds);

            if (unionedDots) {
                if (isNegative) {
                    // Counter plate: subtract dots
                    const newResult = result.subtract(unionedDots);
                    result.delete();
                    unionedDots.delete();
                    result = newResult;
                    console.log('Manifold CSG Worker: Subtracted dots for counter plate');
                } else {
                    // Positive plate: add dots
                    const newResult = result.add(unionedDots);
                    result.delete();
                    unionedDots.delete();
                    result = newResult;
                    console.log('Manifold CSG Worker: Added dots for embossing plate');
                }
            }
        }

        // Process markers (always subtract)
        if (markerManifolds.length > 0) {
            console.log(`Manifold CSG Worker: Processing ${markerManifolds.length} markers`);
            const unionedMarkers = batchUnionManifold(markerManifolds);

            if (unionedMarkers) {
                const newResult = result.subtract(unionedMarkers);
                result.delete();
                unionedMarkers.delete();
                result = newResult;
                console.log('Manifold CSG Worker: Subtracted markers');
            }
        }

        // For cylinders: the coordinate system is already correct (Z-up)
        // No rotation needed since Manifold uses Z-up natively

        return result;

    } catch (error) {
        console.error('Manifold CSG Worker: Processing failed:', error);
        manifoldsToCleanup.forEach(m => { if (m) m.delete(); });
        throw error;
    }
}

/**
 * Export Manifold mesh to binary STL format
 */
function exportToSTL(manifold) {
    const mesh = manifold.getMesh();

    const vertProps = mesh.vertProperties;
    const triVerts = mesh.triVerts;
    const numTri = triVerts.length / 3;
    const numProp = mesh.numProp;

    console.log(`Manifold CSG Worker: Exporting ${numTri} triangles to STL`);

    // Binary STL format:
    // 80 bytes header
    // 4 bytes triangle count (uint32)
    // For each triangle:
    //   12 bytes normal (3 x float32)
    //   36 bytes vertices (3 vertices x 3 coords x float32)
    //   2 bytes attribute byte count (uint16)
    const bufferLength = 80 + 4 + numTri * 50;
    const buffer = new ArrayBuffer(bufferLength);
    const view = new DataView(buffer);

    // Write header (80 bytes, can be anything)
    const header = 'Binary STL exported by Manifold CSG Worker';
    for (let i = 0; i < 80; i++) {
        view.setUint8(i, i < header.length ? header.charCodeAt(i) : 0);
    }

    // Write triangle count
    view.setUint32(80, numTri, true);

    let offset = 84;

    for (let i = 0; i < numTri; i++) {
        // Get vertex indices
        const i0 = triVerts[i * 3];
        const i1 = triVerts[i * 3 + 1];
        const i2 = triVerts[i * 3 + 2];

        // Get vertex positions
        const v0 = [
            vertProps[i0 * numProp],
            vertProps[i0 * numProp + 1],
            vertProps[i0 * numProp + 2]
        ];
        const v1 = [
            vertProps[i1 * numProp],
            vertProps[i1 * numProp + 1],
            vertProps[i1 * numProp + 2]
        ];
        const v2 = [
            vertProps[i2 * numProp],
            vertProps[i2 * numProp + 1],
            vertProps[i2 * numProp + 2]
        ];

        // Calculate normal (cross product of edges)
        const e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]];
        const e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]];
        const nx = e1[1] * e2[2] - e1[2] * e2[1];
        const ny = e1[2] * e2[0] - e1[0] * e2[2];
        const nz = e1[0] * e2[1] - e1[1] * e2[0];
        const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
        const normal = len > 0 ? [nx / len, ny / len, nz / len] : [0, 0, 1];

        // Write normal
        view.setFloat32(offset, normal[0], true); offset += 4;
        view.setFloat32(offset, normal[1], true); offset += 4;
        view.setFloat32(offset, normal[2], true); offset += 4;

        // Write vertices
        view.setFloat32(offset, v0[0], true); offset += 4;
        view.setFloat32(offset, v0[1], true); offset += 4;
        view.setFloat32(offset, v0[2], true); offset += 4;

        view.setFloat32(offset, v1[0], true); offset += 4;
        view.setFloat32(offset, v1[1], true); offset += 4;
        view.setFloat32(offset, v1[2], true); offset += 4;

        view.setFloat32(offset, v2[0], true); offset += 4;
        view.setFloat32(offset, v2[1], true); offset += 4;
        view.setFloat32(offset, v2[2], true); offset += 4;

        // Attribute byte count (unused)
        view.setUint16(offset, 0, true); offset += 2;
    }

    return buffer;
}

/**
 * Convert Manifold mesh to geometry data for preview rendering
 */
function getGeometryData(manifold) {
    const mesh = manifold.getMesh();

    const vertProps = mesh.vertProperties;
    const triVerts = mesh.triVerts;
    const numTri = triVerts.length / 3;
    const numProp = mesh.numProp;

    // Create non-indexed geometry for preview
    const positions = new Float32Array(numTri * 9);
    const normals = new Float32Array(numTri * 9);

    for (let i = 0; i < numTri; i++) {
        const i0 = triVerts[i * 3];
        const i1 = triVerts[i * 3 + 1];
        const i2 = triVerts[i * 3 + 2];

        // Vertices
        const v0 = [
            vertProps[i0 * numProp],
            vertProps[i0 * numProp + 1],
            vertProps[i0 * numProp + 2]
        ];
        const v1 = [
            vertProps[i1 * numProp],
            vertProps[i1 * numProp + 1],
            vertProps[i1 * numProp + 2]
        ];
        const v2 = [
            vertProps[i2 * numProp],
            vertProps[i2 * numProp + 1],
            vertProps[i2 * numProp + 2]
        ];

        positions[i * 9 + 0] = v0[0];
        positions[i * 9 + 1] = v0[1];
        positions[i * 9 + 2] = v0[2];
        positions[i * 9 + 3] = v1[0];
        positions[i * 9 + 4] = v1[1];
        positions[i * 9 + 5] = v1[2];
        positions[i * 9 + 6] = v2[0];
        positions[i * 9 + 7] = v2[1];
        positions[i * 9 + 8] = v2[2];

        // Calculate normal
        const e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]];
        const e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]];
        const nx = e1[1] * e2[2] - e1[2] * e2[1];
        const ny = e1[2] * e2[0] - e1[0] * e2[2];
        const nz = e1[0] * e2[1] - e1[1] * e2[0];
        const len = Math.sqrt(nx * nx + ny * ny + nz * nz);
        const normal = len > 0 ? [nx / len, ny / len, nz / len] : [0, 0, 1];

        for (let j = 0; j < 3; j++) {
            normals[i * 9 + j * 3 + 0] = normal[0];
            normals[i * 9 + j * 3 + 1] = normal[1];
            normals[i * 9 + j * 3 + 2] = normal[2];
        }
    }

    return { positions, normals, indices: null };
}

/**
 * Message handler
 */
self.onmessage = async function(event) {
    const { type, spec, requestId } = event.data;

    console.log('Manifold CSG Worker: Received message type:', type, 'requestId:', requestId);

    // Check if initialization failed
    if (initError) {
        console.error('Manifold CSG Worker: Init error present:', initError.message);
        self.postMessage({
            type: 'error',
            requestId: requestId,
            error: 'Manifold Worker initialization failed: ' + initError.message
        });
        return;
    }

    // Ensure Manifold is ready
    if (!manifoldReady) {
        console.log('Manifold CSG Worker: Not ready, attempting initialization...');
        try {
            await initManifold();
        } catch (e) {
            console.error('Manifold CSG Worker: Failed to initialize:', e.message);
            self.postMessage({
                type: 'error',
                requestId: requestId,
                error: 'Failed to initialize Manifold: ' + e.message
            });
            return;
        }
    }

    try {
        if (type === 'generate') {
            console.log('Manifold CSG Worker: ===== STARTING GENERATION =====');
            console.log('Manifold CSG Worker: Request ID:', requestId);
            console.log('Manifold CSG Worker: Shape type:', spec.shape_type);
            console.log('Manifold CSG Worker: Plate type:', spec.plate_type);
            console.log('Manifold CSG Worker: Dots count:', spec.dots?.length || 0);
            console.log('Manifold CSG Worker: Markers count:', spec.markers?.length || 0);

            // Process geometry using Manifold
            const manifold = processGeometrySpec(spec);

            // Get mesh statistics
            const mesh = manifold.getMesh();
            const numTriangles = mesh.triVerts.length / 3;
            const numVertices = mesh.vertProperties.length / mesh.numProp;
            console.log(`Manifold CSG Worker: Generated mesh - ${numTriangles} triangles, ${numVertices} vertices`);

            // Export to STL
            console.log('Manifold CSG Worker: Exporting to STL...');
            const stlData = exportToSTL(manifold);
            console.log('Manifold CSG Worker: STL size:', stlData.byteLength, 'bytes');

            // Get geometry data for preview
            const geometryData = getGeometryData(manifold);

            // Clean up
            manifold.delete();

            console.log('Manifold CSG Worker: ===== GENERATION COMPLETE =====');

            // Send results
            self.postMessage({
                type: 'success',
                requestId: requestId,
                geometry: geometryData,
                stl: stlData
            }, [geometryData.positions.buffer, geometryData.normals.buffer, stlData]);

        } else if (type === 'ping') {
            console.log('Manifold CSG Worker: Responding to ping');
            self.postMessage({ type: 'pong', requestId: requestId });
        }

    } catch (error) {
        console.error('Manifold CSG Worker: ===== ERROR =====');
        console.error('Manifold CSG Worker: Error message:', error.message);
        console.error('Manifold CSG Worker: Error stack:', error.stack);
        self.postMessage({
            type: 'error',
            requestId: requestId,
            error: error.message,
            stack: error.stack
        });
    }
};

// Signal that worker is ready
if (initError) {
    self.postMessage({ type: 'init_error', error: initError.message });
} else {
    self.postMessage({ type: 'ready' });
}
