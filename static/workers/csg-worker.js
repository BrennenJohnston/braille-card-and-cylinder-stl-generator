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
 * Create a braille dot mesh at position (x, y, z)
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
 * Create a rectangular marker
 */
function createRectMarker(spec) {
    const { x, y, z, width, height, depth } = spec;
    const geometry = new THREE.BoxGeometry(width, height, depth);
    geometry.translate(x, y, z);
    return geometry;
}

/**
 * Create a triangular marker
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
 * Create a character shape marker (alphanumeric)
 */
function createCharacterMarker(spec) {
    const { x, y, z, char, size, depth } = spec;

    // For simplicity, use a box with approximate character dimensions
    // In a full implementation, this could use text geometry
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
    const innerGeom = new THREE.CylinderGeometry(radius - thickness, radius - thickness, height + 0.1, 64);

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
            depth: radius * 3, // Ensure it cuts all the way through
            bevelEnabled: false
        };

        const cutoutGeom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
        cutoutGeom.rotateX(Math.PI / 2); // Align with cylinder
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
    const { shape_type, plate, dots, markers, cylinder } = spec;

    try {
        // Create base geometry
        let baseGeometry;

        if (shape_type === 'cylinder' && cylinder) {
            baseGeometry = createCylinderShell(cylinder);
        } else {
            // Card plate
            const { width, height, thickness, center_x, center_y, center_z } = plate;
            baseGeometry = new THREE.BoxGeometry(width, height, thickness);
            baseGeometry.translate(center_x, center_y, center_z);
        }

        // Collect all cutout geometries
        const cutouts = [];

        // Add dots
        if (dots && dots.length > 0) {
            dots.forEach(dotSpec => {
                const dotGeom = createBrailleDot(dotSpec);
                cutouts.push(dotGeom);
            });
        }

        // Add markers
        if (markers && markers.length > 0) {
            markers.forEach(markerSpec => {
                let markerGeom;

                if (markerSpec.type === 'rect') {
                    markerGeom = createRectMarker(markerSpec);
                } else if (markerSpec.type === 'triangle') {
                    markerGeom = createTriangleMarker(markerSpec);
                } else if (markerSpec.type === 'character') {
                    markerGeom = createCharacterMarker(markerSpec);
                }

                if (markerGeom) {
                    cutouts.push(markerGeom);
                }
            });
        }

        // Perform CSG operations
        if (cutouts.length > 0) {
            // Union all cutouts
            const unionedCutouts = batchUnion(cutouts, 32);

            // Subtract from base
            const baseBrush = new Brush(baseGeometry);
            const cutoutBrush = new Brush(unionedCutouts);
            const resultBrush = evaluator.evaluate(baseBrush, cutoutBrush, SUBTRACTION);

            // Fix drawRange for export
            resultBrush.geometry.setDrawRange(0, Infinity);

            return resultBrush.geometry;
        } else {
            // No cutouts, return base as-is
            baseGeometry.setDrawRange(0, Infinity);
            return baseGeometry;
        }

    } catch (error) {
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
            // Process geometry
            const geometry = processGeometrySpec(spec);

            // Export to STL
            const stlData = exportToSTL(geometry);

            // Prepare geometry for rendering (transferable)
            const positions = geometry.attributes.position.array;
            const normals = geometry.attributes.normal ? geometry.attributes.normal.array : null;
            const indices = geometry.index ? geometry.index.array : null;

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
            }, [positions.buffer, stlData, ...(normals ? [normals.buffer] : []), ...(indices ? [indices.buffer] : [])]);

        } else if (type === 'ping') {
            // Health check
            self.postMessage({ type: 'pong', requestId: requestId });
        }

    } catch (error) {
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
