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
 */
function createSphericalCap(radius, height, subdivisions = 3) {
    const geometry = new THREE.SphereGeometry(radius, 16, 16, 0, Math.PI * 2, 0, Math.acos(1 - height / radius));
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
    const shape = params.shape || 'standard';

    let geometry;
    let dotHeight = 0;
    const isRecess = is_recess || shape === 'hemisphere' || shape === 'bowl';

    if (shape === 'rounded') {
        // Rounded dot for positive plate
        const { base_radius, top_radius, base_height, dome_height, dome_radius } = params;
        dotHeight = base_height + dome_height;

        if (base_height > 0) {
            // Frustum base + dome
            const frustum = createConeFrustum(base_radius, top_radius, base_height, 32);
            const dome = createSphericalCap(dome_radius, dome_height, 2);

            // Position dome on top of frustum
            dome.translate(0, base_height / 2, 0);

            const frustumBrush = new Brush(frustum);
            const domeBrush = new Brush(dome);
            const combinedBrush = evaluator.evaluate(frustumBrush, domeBrush, ADDITION);
            geometry = combinedBrush.geometry;
        } else {
            // Just dome
            geometry = createSphericalCap(dome_radius, dome_height, 2);
        }
    } else if (shape === 'hemisphere') {
        // Hemisphere for counter plate recesses
        const { recess_radius } = params;
        dotHeight = recess_radius;
        geometry = new THREE.SphereGeometry(recess_radius, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2);
    } else if (shape === 'bowl') {
        // Bowl (spherical cap) for counter plate
        const { bowl_radius, bowl_depth } = params;
        dotHeight = bowl_depth;
        const sphereR = (bowl_radius * bowl_radius + bowl_depth * bowl_depth) / (2.0 * bowl_depth);
        const thetaEnd = Math.acos(1 - bowl_depth / sphereR);
        geometry = new THREE.SphereGeometry(sphereR, 16, 16, 0, Math.PI * 2, 0, thetaEnd);
    } else if (shape === 'cone') {
        // Cone frustum for counter plate
        const { base_radius, top_radius, height } = params;
        dotHeight = height;
        geometry = createConeFrustum(base_radius, top_radius, height, 16);
    } else {
        // Standard cone frustum for positive embossing
        const { base_radius, top_radius, height } = params;
        dotHeight = height;
        geometry = createConeFrustum(base_radius, top_radius, height, 16);
    }

    // Apply rotation to orient dot radially on cylinder surface
    // Three.js CylinderGeometry creates along Y-axis (height along Y)
    // We need to rotate so the dot points radially outward at angle theta

    // Step 1: Rotate -90° around Z so dot points along +X instead of +Y
    geometry.rotateZ(-Math.PI / 2);

    // Step 2: Rotate around Y by -theta to position it at the correct radial angle
    // (negative because rotateY(θ) gives (cos(θ), 0, -sin(θ)) but radial is (cos(θ), 0, +sin(θ)))
    geometry.rotateY(-theta);

    // Calculate the radial position
    // For recesses (counter plates): position dot so it overlaps INTO cylinder for subtraction
    // For protrusions (embossing plates): position dot so base sits on surface
    // Add small epsilon to prevent coplanar triangles which cause CSG failures
    const epsilon = 0.01;
    let radialOffset;
    if (isRecess) {
        // For recesses, position so the dot extends INTO the cylinder
        // The CSG subtraction will carve out the shape
        radialOffset = cylRadius - dotHeight / 2 + epsilon;
    } else {
        // For protrusions, position so the dot sits ON the surface and extends outward
        radialOffset = cylRadius + dotHeight / 2 + epsilon;
    }

    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);

    // Translate to position on cylinder surface
    geometry.translate(posX, y, posZ);

    return geometry;
}

/**
 * Create a triangle marker on cylinder surface
 */
function createCylinderTriangleMarker(spec) {
    const { x, y, z, theta, radius: cylRadius, size, depth, is_recess } = spec;

    // Create triangle shape in XY plane
    const shape = new THREE.Shape();
    shape.moveTo(-size / 2, -size);
    shape.lineTo(size / 2, -size);
    shape.lineTo(0, size);
    shape.closePath();

    const extrudeSettings = {
        depth: depth,
        bevelEnabled: false
    };

    const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);

    // ExtrudeGeometry extrudes along +Z, we need it to point radially

    // Rotate so extrusion points along +X
    geometry.rotateY(Math.PI / 2);

    // Then rotate to the correct radial position using -theta
    // (negative because rotateY(θ) gives (cos(θ), 0, -sin(θ)) but radial is (cos(θ), 0, +sin(θ)))
    geometry.rotateY(-theta);

    // Position at cylinder surface with epsilon to prevent coplanar issues
    const epsilon = 0.01;
    let radialOffset;
    if (is_recess) {
        radialOffset = cylRadius - depth / 2 + epsilon;
    } else {
        radialOffset = cylRadius + depth / 2 + epsilon;
    }
    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);

    geometry.translate(posX, y, posZ);

    return geometry;
}

/**
 * Create a rectangular marker on cylinder surface
 */
function createCylinderRectMarker(spec) {
    const { x, y, z, theta, radius: cylRadius, width, height, depth, is_recess } = spec;

    // BoxGeometry: width (X), height (Y), depth (Z)
    // We want depth to point radially outward
    const geometry = new THREE.BoxGeometry(width, height, depth);

    // Rotate so depth (Z) points radially outward at angle theta
    // First rotate π/2 to align Z with +X, then -theta to point toward (cos(θ), 0, sin(θ))
    geometry.rotateY(Math.PI / 2 - theta);

    // Position at cylinder surface with epsilon to prevent coplanar issues
    const epsilon = 0.01;
    let radialOffset;
    if (is_recess) {
        radialOffset = cylRadius - depth / 2 + epsilon;
    } else {
        radialOffset = cylRadius + depth / 2 + epsilon;
    }
    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);

    geometry.translate(posX, y, posZ);

    return geometry;
}

/**
 * Create a character marker on cylinder surface
 */
function createCylinderCharacterMarker(spec) {
    const { x, y, z, theta, radius: cylRadius, char, size, depth, is_recess } = spec;

    // Approximate character as a box
    const charWidth = size * 0.6;
    const charHeight = size;
    const geometry = new THREE.BoxGeometry(charWidth, charHeight, depth);

    // Rotate so depth (Z) points radially outward at angle theta
    // First rotate π/2 to align Z with +X, then -theta to point toward (cos(θ), 0, sin(θ))
    geometry.rotateY(Math.PI / 2 - theta);

    // Position at cylinder surface with epsilon to prevent coplanar issues
    const epsilon = 0.01;
    let radialOffset;
    if (is_recess) {
        radialOffset = cylRadius - depth / 2 + epsilon;
    } else {
        radialOffset = cylRadius + depth / 2 + epsilon;
    }
    const posX = radialOffset * Math.cos(theta);
    const posZ = radialOffset * Math.sin(theta);

    geometry.translate(posX, y, posZ);

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

    // Create outer cylinder
    const outerGeom = new THREE.CylinderGeometry(radius, radius, height, 64);

    // Create inner cylinder for hollow shell
    const innerRadius = radius - thickness;
    const innerGeom = new THREE.CylinderGeometry(innerRadius, innerRadius, height + 0.1, 64);

    // Create brushes and subtract
    const outerBrush = new Brush(outerGeom);
    const innerBrush = new Brush(innerGeom);

    let shellBrush = evaluator.evaluate(outerBrush, innerBrush, SUBTRACTION);

    // If polygon cutout is specified, create and subtract it
    if (polygon_points && polygon_points.length > 0) {
        // Create extruded polygon
        const shape = new THREE.Shape();
        polygon_points.forEach((pt, i) => {
            if (i === 0) {
                shape.moveTo(pt.x, pt.y);
            } else {
                shape.lineTo(pt.x, pt.y);
            }
        });
        shape.closePath();

        const extrudeSettings = {
            depth: height * 1.5, // Ensure it cuts all the way through
            bevelEnabled: false
        };

        const cutoutGeom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
        // Center the extrusion
        cutoutGeom.translate(0, 0, -height * 0.75);
        // Rotate to align with cylinder's Y-axis
        cutoutGeom.rotateX(Math.PI / 2);

        const cutoutBrush = new Brush(cutoutGeom);
        shellBrush = evaluator.evaluate(shellBrush, cutoutBrush, SUBTRACTION);
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

        // Collect all feature geometries (dots and markers)
        const features = [];

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
                        features.push(dotGeom);
                    }
                } catch (err) {
                    console.warn(`CSG Worker: Failed to create dot ${i}:`, err.message);
                }
            });
        }

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
                        features.push(markerGeom);
                    }
                } catch (err) {
                    console.warn(`CSG Worker: Failed to create marker ${i}:`, err.message);
                }
            });
        }

        // Perform CSG operations
        let finalGeometry;

        if (features.length > 0) {
            console.log(`CSG Worker: Performing CSG with ${features.length} features`);

            // Union all features
            const unionedFeatures = batchUnion(features, 32);

            // For negative (counter) plates: subtract features (create recesses)
            // For positive (emboss) plates with cylinders: add features (create protrusions)
            // For positive cards: features are already positioned above surface, just union
            const baseBrush = new Brush(baseGeometry);
            const featureBrush = new Brush(unionedFeatures);

            let resultBrush;

            if (isNegative) {
                // Counter plate: subtract to create recesses
                resultBrush = evaluator.evaluate(baseBrush, featureBrush, SUBTRACTION);
                console.log('CSG Worker: Subtracted features for counter plate');
            } else if (isCylinder) {
                // Positive cylinder: add dots that protrude from surface
                resultBrush = evaluator.evaluate(baseBrush, featureBrush, ADDITION);
                console.log('CSG Worker: Added features for embossing cylinder');
            } else {
                // Positive card: features protrude above, use addition
                resultBrush = evaluator.evaluate(baseBrush, featureBrush, ADDITION);
                console.log('CSG Worker: Added features for embossing card');
            }

            // Fix drawRange for export
            resultBrush.geometry.setDrawRange(0, Infinity);
            finalGeometry = resultBrush.geometry;
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
