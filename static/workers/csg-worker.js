/**
 * CSG Worker for client-side braille geometry generation
 * Uses three-bvh-csg for boolean operations
 */

let THREE, Brush, Evaluator, SUBTRACTION, ADDITION, STLExporter;
let evaluator, stlExporter;
let initError = null;

try {
    // Dynamic imports to catch any loading errors
    const threeModule = await import('/static/three.module.js');
    THREE = threeModule;

    const csgModule = await import('/static/vendor/three-bvh-csg/index.module.js');
    Brush = csgModule.Brush;
    Evaluator = csgModule.Evaluator;
    SUBTRACTION = csgModule.SUBTRACTION;
    ADDITION = csgModule.ADDITION;

    const exporterModule = await import('/static/examples/STLExporter.js');
    STLExporter = exporterModule.STLExporter;

    // Initialize evaluator and exporter
    evaluator = new Evaluator();
    stlExporter = new STLExporter();

    console.log('CSG Worker: All modules loaded successfully');
} catch (error) {
    initError = error;
    console.error('CSG Worker initialization error:', error.message, error.stack);
}

/**
 * Create a cone frustum (truncated cone) for braille dots
 */
function createConeFrustum(baseRadius, topRadius, height, segments = 16) {
    const geometry = new THREE.CylinderGeometry(topRadius, baseRadius, height, segments);
    return geometry;
}

/**
 * Create a spherical cap (dome) for rounded braille dots
 * Handles edge cases to prevent NaN in geometry
 */
function createSphericalCap(radius, height, subdivisions = 3) {
    // Validate inputs to prevent NaN
    if (!radius || radius <= 0 || !isFinite(radius)) {
        console.warn('createSphericalCap: Invalid radius, using fallback sphere');
        return new THREE.SphereGeometry(1, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2);
    }
    if (!height || height <= 0 || !isFinite(height)) {
        console.warn('createSphericalCap: Invalid height, using fallback sphere');
        return new THREE.SphereGeometry(radius, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2);
    }

    // Calculate the ratio for acos - must be in range [-1, 1]
    const ratio = 1 - height / radius;

    // Clamp ratio to valid acos range to prevent NaN
    // This handles cases where height > 2*radius (which would give ratio < -1)
    const clampedRatio = Math.max(-1, Math.min(1, ratio));

    // If height >= 2*radius, we essentially want a full hemisphere or more
    // In that case, use π/2 for a hemisphere (maximum practical spherical cap)
    const phiLength = clampedRatio <= -1 ? Math.PI : Math.acos(clampedRatio);

    const geometry = new THREE.SphereGeometry(radius, 16, 16, 0, Math.PI * 2, 0, phiLength);
    return geometry;
}

/**
 * Create a braille dot mesh at position (x, y, z) for flat card
 */
function createBrailleDot(spec) {
    const { x, y, z, type, params } = spec;

    let geometry;

    if (type === 'rounded') {
        // Rounded dot: cone frustum base + spherical cap dome
        const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;

        // Frustum base
        if (base_height > 0) {
            const frustum = createConeFrustum(base_radius, top_radius, base_height, 48);
            const dome_R = dome_radius;
            const dome_zc = (base_height / 2.0) + (dome_height - dome_R);
            const dome = createSphericalCap(dome_R, dome_height, 2);
            dome.translate(0, 0, dome_zc);

            // Use CSG union for rounded dots
            const frustumBrush = new Brush(frustum);
            const domeBrush = new Brush(dome);
            const combinedBrush = evaluator.evaluate(frustumBrush, domeBrush, ADDITION);
            geometry = combinedBrush.geometry;

            // Recenter and translate to position
            geometry.translate(0, 0, -dome_height / 2.0);
            geometry.translate(x, y, z);
        } else {
            // Only dome, no frustum
            const dome_R = dome_radius;
            const dome = createSphericalCap(dome_R, dome_height, 2);
            geometry = dome;
            geometry.translate(0, 0, -dome_height / 2.0);
            geometry.translate(x, y, z);
        }

    } else {
        // Default: simple cone frustum
        const { base_radius, top_radius, height } = params;
        geometry = createConeFrustum(base_radius, top_radius, height, 16);
        geometry.translate(x, y, z);
    }

    return geometry;
}

/**
 * Create a braille dot on a cylinder surface
 * The dot is positioned at (x, y, z) and oriented radially outward
 * For counter plates (recesses), the dot overlaps INTO the cylinder for subtraction
 */
function createCylinderDot(spec) {
    const { x, y, z, theta, radius: cylRadius, params, is_recess } = spec;

    // Validate essential parameters
    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderDot: Invalid theta or cylRadius, skipping dot');
        return null;
    }
    if (!params) {
        console.warn('createCylinderDot: Missing params, skipping dot');
        return null;
    }

    const shape = params.shape || 'standard';

    let geometry;
    let dotHeight = 0;
    const isRecess = is_recess || shape === 'hemisphere' || shape === 'bowl';

    if (shape === 'rounded') {
        // Rounded dot for positive plate
        const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;

        // Validate rounded dot parameters
        const validBaseRadius = (base_radius && base_radius > 0) ? base_radius : 1.0;
        const validTopRadius = (top_radius && top_radius > 0) ? top_radius : 0.75;
        const validBaseHeight = (base_height && base_height >= 0) ? base_height : 0.2;
        const validDomeHeight = (dome_height && dome_height > 0) ? dome_height : 0.6;
        const validDomeRadius = (dome_radius && dome_radius > 0) ? dome_radius : 0.5;

        dotHeight = validBaseHeight + validDomeHeight;

        if (validBaseHeight > 0) {
            // Frustum base + dome
            const frustum = createConeFrustum(validBaseRadius, validTopRadius, validBaseHeight, 32);
            const dome = createSphericalCap(validDomeRadius, validDomeHeight, 2);

            // Position dome on top of frustum
            dome.translate(0, validBaseHeight / 2, 0);

            const frustumBrush = new Brush(frustum);
            const domeBrush = new Brush(dome);
            const combinedBrush = evaluator.evaluate(frustumBrush, domeBrush, ADDITION);
            geometry = combinedBrush.geometry;
        } else {
            // Just dome
            geometry = createSphericalCap(validDomeRadius, validDomeHeight, 2);
        }
    } else if (shape === 'hemisphere') {
        // Hemisphere for counter plate recesses
        const { recess_radius } = params;
        const validRecessRadius = (recess_radius && recess_radius > 0) ? recess_radius : 1.0;
        dotHeight = validRecessRadius;
        // Use full sphere for better subtraction overlap (will be positioned to create hemisphere effect)
        geometry = new THREE.SphereGeometry(validRecessRadius, 16, 16);
    } else if (shape === 'bowl') {
        // Bowl (spherical cap) for counter plate
        const { bowl_radius, bowl_depth } = params;

        // Validate bowl parameters to prevent NaN
        const validBowlRadius = (bowl_radius && bowl_radius > 0) ? bowl_radius : 1.5;
        const validBowlDepth = (bowl_depth && bowl_depth > 0) ? bowl_depth : 0.8;

        dotHeight = validBowlDepth;
        const sphereR = (validBowlRadius * validBowlRadius + validBowlDepth * validBowlDepth) / (2.0 * validBowlDepth);

        // Use full sphere for better subtraction (positioned to create bowl effect)
        geometry = new THREE.SphereGeometry(sphereR, 16, 16);
    } else if (shape === 'cone') {
        // Cone frustum for counter plate
        const { base_radius, top_radius, height } = params;
        const validBaseRadius = (base_radius && base_radius > 0) ? base_radius : 1.0;
        const validTopRadius = (top_radius && top_radius >= 0) ? top_radius : 0.25;
        const validHeight = (height && height > 0) ? height : 1.0;
        dotHeight = validHeight;
        geometry = createConeFrustum(validBaseRadius, validTopRadius, validHeight, 16);
    } else {
        // Standard cone frustum for positive embossing
        const { base_radius, top_radius, height } = params;
        const validBaseRadius = (base_radius && base_radius > 0) ? base_radius : 0.8;
        const validTopRadius = (top_radius && top_radius >= 0) ? top_radius : 0.25;
        const validHeight = (height && height > 0) ? height : 0.5;
        dotHeight = validHeight;
        geometry = createConeFrustum(validBaseRadius, validTopRadius, validHeight, 16);
    }

    // For non-spherical shapes (cones, frustums), apply rotation to orient radially
    // Spheres don't need rotation since they're symmetric
    const isSpherical = (shape === 'hemisphere' || shape === 'bowl');

    if (!isSpherical) {
        // Apply rotation to orient dot radially on cylinder surface
        // Three.js CylinderGeometry creates along Y-axis (height along Y)
        // We need to rotate so the dot points radially outward at angle theta

        // Step 1: Rotate -90° around Z so dot points along +X instead of +Y
        geometry.rotateZ(-Math.PI / 2);

        // Step 2: Rotate around Y by -theta to position it at the correct radial angle
        // (negative because rotateY(θ) gives (cos(θ), 0, -sin(θ)) but radial is (cos(θ), 0, +sin(θ)))
        geometry.rotateY(-theta);
    }

    // Calculate the radial position
    // For recesses (counter plates): position sphere center AT the surface - subtraction creates cavity
    // For protrusions (embossing plates): position dot so base sits on surface and extends outward
    // Use larger epsilon to prevent coplanar triangles which cause CSG failures
    const epsilon = 0.05;
    let radialOffset;
    if (isRecess) {
        // For recesses (spheres), center at surface - half will be inside, half outside
        // The inside half gets subtracted to create the recess
        radialOffset = cylRadius;
    } else {
        // For protrusions, position so the dot sits ON the surface and extends outward
        radialOffset = cylRadius + dotHeight / 2 + epsilon;
    }

    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);
    const posY = isFinite(y) ? y : 0;

    // Validate final position values
    if (!isFinite(posX) || !isFinite(posZ) || !isFinite(posY)) {
        console.warn('createCylinderDot: Invalid position calculated, skipping dot');
        return null;
    }

    // Translate to position on cylinder surface
    geometry.translate(posX, posY, posZ);

    return geometry;
}

/**
 * Create a triangle marker on cylinder surface
 */
function createCylinderTriangleMarker(spec) {
    const { x, y, z, theta, radius: cylRadius, size, depth, is_recess } = spec;

    // Validate essential parameters
    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderTriangleMarker: Invalid parameters, skipping marker');
        return null;
    }

    const validSize = (size && size > 0) ? size : 2.0;
    const validDepth = (depth && depth > 0) ? depth : 0.6;

    // Create triangle shape in XY plane
    const triangleShape = new THREE.Shape();
    triangleShape.moveTo(-validSize / 2, -validSize);
    triangleShape.lineTo(validSize / 2, -validSize);
    triangleShape.lineTo(0, validSize);
    triangleShape.closePath();

    const extrudeSettings = {
        depth: validDepth,
        bevelEnabled: false
    };

    const geometry = new THREE.ExtrudeGeometry(triangleShape, extrudeSettings);

    // ExtrudeGeometry extrudes along +Z, we need it to point radially

    // Rotate so extrusion points along +X
    geometry.rotateY(Math.PI / 2);

    // Then rotate to the correct radial position using -theta
    // (negative because rotateY(θ) gives (cos(θ), 0, -sin(θ)) but radial is (cos(θ), 0, +sin(θ)))
    geometry.rotateY(-theta);

    // Position at cylinder surface with epsilon to prevent coplanar issues
    const epsilon = 0.05;
    let radialOffset;
    if (is_recess) {
        // For recesses, position so marker extends INTO cylinder for subtraction
        radialOffset = cylRadius - validDepth / 2;
    } else {
        // For protrusions, position so marker sits on surface and extends outward
        radialOffset = cylRadius + validDepth / 2 + epsilon;
    }
    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);
    const posY = isFinite(y) ? y : 0;

    // Validate final position
    if (!isFinite(posX) || !isFinite(posZ)) {
        console.warn('createCylinderTriangleMarker: Invalid position, skipping marker');
        return null;
    }

    geometry.translate(posX, posY, posZ);

    return geometry;
}

/**
 * Create a rectangular marker on cylinder surface
 */
function createCylinderRectMarker(spec) {
    const { x, y, z, theta, radius: cylRadius, width, height, depth, is_recess } = spec;

    // Validate essential parameters
    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderRectMarker: Invalid parameters, skipping marker');
        return null;
    }

    const validWidth = (width && width > 0) ? width : 2.0;
    const validHeight = (height && height > 0) ? height : 4.0;
    const validDepth = (depth && depth > 0) ? depth : 0.5;

    // BoxGeometry: width (X), height (Y), depth (Z)
    // We want depth to point radially outward
    const geometry = new THREE.BoxGeometry(validWidth, validHeight, validDepth);

    // Rotate so depth (Z) points radially outward at angle theta
    // First rotate π/2 to align Z with +X, then -theta to point toward (cos(θ), 0, sin(θ))
    geometry.rotateY(Math.PI / 2 - theta);

    // Position at cylinder surface with epsilon to prevent coplanar issues
    const epsilon = 0.05;
    let radialOffset;
    if (is_recess) {
        // For recesses, position so marker extends INTO cylinder for subtraction
        radialOffset = cylRadius - validDepth / 2;
    } else {
        // For protrusions, position so marker sits on surface and extends outward
        radialOffset = cylRadius + validDepth / 2 + epsilon;
    }
    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);
    const posY = isFinite(y) ? y : 0;

    // Validate final position
    if (!isFinite(posX) || !isFinite(posZ)) {
        console.warn('createCylinderRectMarker: Invalid position, skipping marker');
        return null;
    }

    geometry.translate(posX, posY, posZ);

    return geometry;
}

/**
 * Create a character marker on cylinder surface
 */
function createCylinderCharacterMarker(spec) {
    const { x, y, z, theta, radius: cylRadius, char, size, depth, is_recess } = spec;

    // Validate essential parameters
    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderCharacterMarker: Invalid parameters, skipping marker');
        return null;
    }

    const validSize = (size && size > 0) ? size : 3.0;
    const validDepth = (depth && depth > 0) ? depth : 1.0;

    // Approximate character as a box
    const charWidth = validSize * 0.6;
    const charHeight = validSize;
    const geometry = new THREE.BoxGeometry(charWidth, charHeight, validDepth);

    // Rotate so depth (Z) points radially outward at angle theta
    // First rotate π/2 to align Z with +X, then -theta to point toward (cos(θ), 0, sin(θ))
    geometry.rotateY(Math.PI / 2 - theta);

    // Position at cylinder surface with epsilon to prevent coplanar issues
    const epsilon = 0.05;
    let radialOffset;
    if (is_recess) {
        // For recesses, position so marker extends INTO cylinder for subtraction
        radialOffset = cylRadius - validDepth / 2;
    } else {
        // For protrusions, position so marker sits on surface and extends outward
        radialOffset = cylRadius + validDepth / 2 + epsilon;
    }
    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);
    const posY = isFinite(y) ? y : 0;

    // Validate final position
    if (!isFinite(posX) || !isFinite(posZ)) {
        console.warn('createCylinderCharacterMarker: Invalid position, skipping marker');
        return null;
    }

    geometry.translate(posX, posY, posZ);

    return geometry;
}

/**
 * Create a rectangular marker for flat card
 */
function createRectMarker(spec) {
    const { x, y, z, width, height, depth } = spec;
    const geometry = new THREE.BoxGeometry(width, height, depth);
    geometry.translate(x, y, z);
    return geometry;
}

/**
 * Create a triangular marker for flat card
 */
function createTriangleMarker(spec) {
    const { x, y, z, size, depth } = spec;

    // Create triangle shape
    const shape = new THREE.Shape();
    shape.moveTo(-size / 2, -size / 2);
    shape.lineTo(size / 2, -size / 2);
    shape.lineTo(0, size / 2);
    shape.closePath();

    const extrudeSettings = {
        depth: depth,
        bevelEnabled: false
    };

    const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    geometry.translate(x, y, z - depth / 2);
    return geometry;
}

/**
 * Create a character shape marker (alphanumeric) for flat card
 */
function createCharacterMarker(spec) {
    const { x, y, z, char, size, depth } = spec;

    // For simplicity, use a box with approximate character dimensions
    const width = size * 0.6;
    const height = size;
    const geometry = new THREE.BoxGeometry(width, height, depth);
    geometry.translate(x, y, z);
    return geometry;
}

/**
 * Create cylinder shell with polygonal cutout
 */
function createCylinderShell(spec) {
    const { radius, height, thickness, polygon_points } = spec;

    // Validate essential parameters
    const validRadius = (radius && radius > 0) ? radius : 30;
    const validHeight = (height && height > 0) ? height : 80;
    const validThickness = (thickness && thickness > 0) ? thickness : 3;

    // Create outer cylinder
    const outerGeom = new THREE.CylinderGeometry(validRadius, validRadius, validHeight, 64);

    // Create inner cylinder for hollow shell
    const innerRadius = Math.max(validRadius - validThickness, 0.1);
    const innerGeom = new THREE.CylinderGeometry(innerRadius, innerRadius, validHeight + 0.1, 64);

    // Create brushes and subtract
    const outerBrush = new Brush(outerGeom);
    const innerBrush = new Brush(innerGeom);

    let shellBrush = evaluator.evaluate(outerBrush, innerBrush, SUBTRACTION);

    // If polygon cutout is specified, create and subtract it
    if (polygon_points && polygon_points.length > 0) {
        // Validate polygon points
        const validPoints = polygon_points.filter(pt =>
            pt && isFinite(pt.x) && isFinite(pt.y)
        );

        if (validPoints.length >= 3) {
            // Create extruded polygon
            const polygonShape = new THREE.Shape();
            validPoints.forEach((pt, i) => {
                if (i === 0) {
                    polygonShape.moveTo(pt.x, pt.y);
                } else {
                    polygonShape.lineTo(pt.x, pt.y);
                }
            });
            polygonShape.closePath();

            const extrudeSettings = {
                depth: validHeight * 1.5, // Ensure it cuts all the way through
                bevelEnabled: false
            };

            const cutoutGeom = new THREE.ExtrudeGeometry(polygonShape, extrudeSettings);
            // Center the extrusion
            cutoutGeom.translate(0, 0, -validHeight * 0.75);
            // Rotate to align with cylinder's Y-axis
            cutoutGeom.rotateX(Math.PI / 2);

            const cutoutBrush = new Brush(cutoutGeom);
            shellBrush = evaluator.evaluate(shellBrush, cutoutBrush, SUBTRACTION);
        }
    }

    return shellBrush.geometry;
}

/**
 * Batch union geometries for efficiency
 */
function batchUnion(geometries, batchSize = 32) {
    if (geometries.length === 0) return null;
    if (geometries.length === 1) return geometries[0];

    // Convert to brushes
    let brushes = geometries.map(g => new Brush(g));

    // Process in batches
    while (brushes.length > 1) {
        const nextLevel = [];

        for (let i = 0; i < brushes.length; i += batchSize) {
            const batch = brushes.slice(i, i + batchSize);
            let result = batch[0];

            for (let j = 1; j < batch.length; j++) {
                result = evaluator.evaluate(result, batch[j], ADDITION);
            }

            nextLevel.push(result);
        }

        brushes = nextLevel;
    }

    return brushes[0].geometry;
}

/**
 * Process geometry spec and perform CSG operations
 *
 * CSG Operation Logic:
 * - Dots: ADD for positive plates (protrusions), SUBTRACT for negative plates (recesses)
 * - Markers: ALWAYS SUBTRACT (markers are always recessed on both plate types)
 */
function processGeometrySpec(spec) {
    const { shape_type, plate_type, plate, dots, markers, cylinder } = spec;
    const isNegative = plate_type === 'negative';
    const isCylinder = shape_type === 'cylinder';

    console.log(`CSG Worker: Processing ${shape_type} ${plate_type} with ${dots?.length || 0} dots and ${markers?.length || 0} markers`);

    try {
        // Create base geometry
        let baseGeometry;

        if (isCylinder && cylinder) {
            baseGeometry = createCylinderShell(cylinder);
            console.log('CSG Worker: Created cylinder shell');
        } else {
            // Card plate
            const { width, height, thickness, center_x, center_y, center_z } = plate;
            baseGeometry = new THREE.BoxGeometry(width, height, thickness);
            baseGeometry.translate(center_x, center_y, center_z);
        }

        // Collect dot geometries (separate from markers for different CSG operations)
        const dotGeometries = [];

        // Process dots
        if (dots && dots.length > 0) {
            console.log(`CSG Worker: Creating ${dots.length} dots`);
            dots.forEach((dotSpec, i) => {
                try {
                    let dotGeom;

                    if (dotSpec.type === 'cylinder_dot') {
                        // Cylinder surface dot
                        dotGeom = createCylinderDot(dotSpec);
                    } else {
                        // Flat card dot
                        dotGeom = createBrailleDot(dotSpec);
                    }

                    if (dotGeom) {
                        dotGeometries.push(dotGeom);
                    }
                } catch (err) {
                    console.warn(`CSG Worker: Failed to create dot ${i}:`, err.message);
                }
            });
        }

        // Collect marker geometries (always subtracted for recesses)
        const markerGeometries = [];

        // Process markers
        if (markers && markers.length > 0) {
            console.log(`CSG Worker: Creating ${markers.length} markers`);
            markers.forEach((markerSpec, i) => {
                try {
                    let markerGeom;

                    if (markerSpec.type === 'cylinder_triangle') {
                        markerGeom = createCylinderTriangleMarker(markerSpec);
                    } else if (markerSpec.type === 'cylinder_rect') {
                        markerGeom = createCylinderRectMarker(markerSpec);
                    } else if (markerSpec.type === 'cylinder_character') {
                        markerGeom = createCylinderCharacterMarker(markerSpec);
                    } else if (markerSpec.type === 'rect') {
                        markerGeom = createRectMarker(markerSpec);
                    } else if (markerSpec.type === 'triangle') {
                        markerGeom = createTriangleMarker(markerSpec);
                    } else if (markerSpec.type === 'character') {
                        markerGeom = createCharacterMarker(markerSpec);
                    }

                    if (markerGeom) {
                        markerGeometries.push(markerGeom);
                    }
                } catch (err) {
                    console.warn(`CSG Worker: Failed to create marker ${i}:`, err.message);
                }
            });
        }

        // Perform CSG operations
        let currentBrush = new Brush(baseGeometry);

        // Step 1: Process dots
        // For negative (counter) plates: subtract dots (create recesses)
        // For positive (emboss) plates: add dots (create protrusions)
        if (dotGeometries.length > 0) {
            console.log(`CSG Worker: Processing ${dotGeometries.length} dots`);
            const unionedDots = batchUnion(dotGeometries, 32);
            const dotsBrush = new Brush(unionedDots);

            if (isNegative) {
                // Counter plate: subtract to create recesses
                currentBrush = evaluator.evaluate(currentBrush, dotsBrush, SUBTRACTION);
                console.log('CSG Worker: Subtracted dots for counter plate');
            } else {
                // Positive plate: add to create protrusions
                currentBrush = evaluator.evaluate(currentBrush, dotsBrush, ADDITION);
                console.log('CSG Worker: Added dots for embossing plate');
            }
        }

        // Step 2: Process markers (ALWAYS subtract - markers are always recessed)
        // This matches the local Python behavior where markers are subtracted
        // using mesh_difference() regardless of plate type
        if (markerGeometries.length > 0) {
            console.log(`CSG Worker: Processing ${markerGeometries.length} markers (subtracting for recesses)`);
            const unionedMarkers = batchUnion(markerGeometries, 32);
            const markersBrush = new Brush(unionedMarkers);

            // Always subtract markers to create recesses
            currentBrush = evaluator.evaluate(currentBrush, markersBrush, SUBTRACTION);
            console.log('CSG Worker: Subtracted markers to create recesses');
        }

        let finalGeometry;
        if (dotGeometries.length > 0 || markerGeometries.length > 0) {
            // Fix drawRange for export
            currentBrush.geometry.setDrawRange(0, Infinity);
            finalGeometry = currentBrush.geometry;
        } else {
            console.log('CSG Worker: No features, returning base geometry');
            // No features, return base as-is
            baseGeometry.setDrawRange(0, Infinity);
            finalGeometry = baseGeometry;
        }

        // For cylinders: rotate from Y-up (Three.js) to Z-up (STL/CAD convention)
        // Rotate +90° around X-axis so the cylinder stands upright in correct orientation
        if (isCylinder) {
            finalGeometry.rotateX(Math.PI / 2);
            console.log('CSG Worker: Rotated cylinder to Z-up orientation (right-side up)');
        }

        return finalGeometry;

    } catch (error) {
        console.error('CSG Worker: Processing failed:', error);
        throw new Error(`CSG processing failed: ${error.message}`);
    }
}

/**
 * Export geometry to binary STL
 */
function exportToSTL(geometry) {
    // Create a temporary mesh for export
    const material = new THREE.MeshStandardMaterial({ color: 0x808080 });
    const mesh = new THREE.Mesh(geometry, material);

    // Export to binary STL
    const stlData = stlExporter.parse(mesh, { binary: true });

    return stlData;
}

/**
 * Message handler
 */
self.onmessage = function(event) {
    const { type, spec, requestId } = event.data;

    // Check if initialization failed
    if (initError) {
        self.postMessage({
            type: 'error',
            requestId: requestId,
            error: 'Worker initialization failed: ' + initError.message,
            stack: initError.stack
        });
        return;
    }

    try {
        if (type === 'generate') {
            console.log('CSG Worker: Starting generation for request', requestId);

            // Process geometry
            const geometry = processGeometrySpec(spec);

            // Export to STL
            const stlData = exportToSTL(geometry);

            // Prepare geometry for rendering (transferable)
            const positions = geometry.attributes.position.array;
            const normals = geometry.attributes.normal ? geometry.attributes.normal.array : null;
            const indices = geometry.index ? geometry.index.array : null;

            // Build transferable array carefully
            const transferables = [positions.buffer];
            if (normals) transferables.push(normals.buffer);
            if (indices) transferables.push(indices.buffer);
            // stlData is an ArrayBuffer, so add it if valid
            if (stlData instanceof ArrayBuffer) {
                transferables.push(stlData);
            }

            console.log('CSG Worker: Generation complete, sending result');

            // Send results back
            self.postMessage({
                type: 'success',
                requestId: requestId,
                geometry: {
                    positions: positions,
                    normals: normals,
                    indices: indices
                },
                stl: stlData
            }, transferables);

        } else if (type === 'ping') {
            // Health check
            self.postMessage({ type: 'pong', requestId: requestId });
        }

    } catch (error) {
        console.error('CSG Worker: Error:', error);
        self.postMessage({
            type: 'error',
            requestId: requestId,
            error: error.message,
            stack: error.stack
        });
    }
};

// Signal that worker is ready (or report initialization error)
if (initError) {
    self.postMessage({ type: 'init_error', error: initError.message, stack: initError.stack });
} else {
    self.postMessage({ type: 'ready' });
}
