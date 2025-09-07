// Geometry builders for client-side STL generation
// Uses three.js primitives to construct positive embossing plates for card and cylinder

import * as THREE from './three.module.js';

function getAvailableColumns(settings) {
    const gridColumns = Number(settings.grid_columns || settings.gridColumns || 26);
    return Math.max(0, gridColumns - 2);
}

function getGridRows(settings) {
    return Number(settings.grid_rows || settings.gridRows || 4);
}

function toNumber(v, fallback = 0) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
}

function brailleUnicodeToDots(ch) {
    // Braille patterns: U+2800 base, bits 0..5 correspond to dots 1..6
    const code = ch.codePointAt(0) || 0;
    const pattern = code - 0x2800;
    const dots = new Array(6).fill(0);
    for (let i = 0; i < 6; i++) {
        dots[i] = (pattern & (1 << i)) ? 1 : 0;
    }
    return dots; // order: [1,2,3,4,5,6]
}

function createDotGeometry(settings) {
    const baseDiameter = toNumber(settings.emboss_dot_base_diameter, 1.5);
    const flatHat = toNumber(settings.emboss_dot_flat_hat, baseDiameter * 0.6);
    const height = toNumber(settings.emboss_dot_height, 0.6);
    const radialSegments = 16;
    const topRadius = Math.max(0, flatHat / 2);
    const bottomRadius = Math.max(0, baseDiameter / 2);
    // CylinderGeometry height is along +Y. Rotate so height aligns with +Z for card dots.
    const geom = new THREE.CylinderGeometry(topRadius, bottomRadius, height, radialSegments, 1, false);
    geom.rotateX(Math.PI / 2);
    return geom;
}

function createBasePlateGeometry(settings) {
    const w = toNumber(settings.card_width, 86);
    const h = toNumber(settings.card_height, 54);
    const t = toNumber(settings.card_thickness, 1.6);
    const geom = new THREE.BoxGeometry(w, h, t, 1, 1, 1);
    return geom;
}

export function buildCardEmbossingPlate(translatedLines, settings) {
    const group = new THREE.Group();
    const material = new THREE.MeshBasicMaterial();

    // Base plate
    const baseGeom = createBasePlateGeometry(settings);
    const baseMesh = new THREE.Mesh(baseGeom, material);
    baseMesh.position.set(
        toNumber(settings.card_width, 86) / 2,
        toNumber(settings.card_height, 54) / 2,
        toNumber(settings.card_thickness, 1.6) / 2
    );
    group.add(baseMesh);

    // Dot positioning constants
    const dotSpacing = toNumber(settings.dot_spacing, 2.54);
    const dotColOffsets = [-dotSpacing / 2, dotSpacing / 2];
    const dotRowOffsets = [dotSpacing, 0, -dotSpacing];
    const dotIndexToRowCol = [
        [0, 0], [1, 0], [2, 0], // dots 1,2,3 left column
        [0, 1], [1, 1], [2, 1]  // dots 4,5,6 right column
    ];

    const leftMargin = toNumber(settings.left_margin, 8);
    const topMargin = toNumber(settings.top_margin, 8);
    const cellSpacing = toNumber(settings.cell_spacing, 6.0);
    const lineSpacing = toNumber(settings.line_spacing, 10.0);
    const zTop = toNumber(settings.card_thickness, 1.6) + toNumber(settings.emboss_dot_height, 0.6) / 2;
    const xAdjust = toNumber(settings.braille_x_adjust, 0);
    const yAdjust = toNumber(settings.braille_y_adjust, 0);
    const availableColumns = getAvailableColumns(settings);
    const gridRows = getGridRows(settings);

    const dotGeom = createDotGeometry(settings);

    for (let rowIdx = 0; rowIdx < gridRows; rowIdx++) {
        const brailleText = (translatedLines[rowIdx] || '').slice(0, availableColumns);
        const yPos = toNumber(settings.card_height, 54) - topMargin - (rowIdx * lineSpacing) + yAdjust;

        for (let col = 0; col < brailleText.length; col++) {
            const ch = brailleText[col];
            const dots = brailleUnicodeToDots(ch);
            const xCell = leftMargin + ((col + 1) * cellSpacing) + xAdjust;

            for (let i = 0; i < 6; i++) {
                if (!dots[i]) continue;
                const [r, c] = dotIndexToRowCol[i];
                const x = xCell + dotColOffsets[c];
                const y = yPos + dotRowOffsets[r];

                const mesh = new THREE.Mesh(dotGeom, material);
                mesh.position.set(x, y, zTop);
                group.add(mesh);
            }
        }
    }

    return group;
}

export function buildCylinderEmbossingPlate(translatedLines, settings, cylinderParams = {}) {
    const group = new THREE.Group();
    const material = new THREE.MeshBasicMaterial();

    const diameter = toNumber(cylinderParams.diameter_mm, 31.35);
    const height = toNumber(cylinderParams.height_mm, toNumber(settings.card_height, 54));
    const seamOffsetDeg = toNumber(cylinderParams.seam_offset_deg, 355);

    const radius = diameter / 2;

    // Cylinder base oriented along Z (match backend STL orientation)
    const cylGeomY = new THREE.CylinderGeometry(radius, radius, height, 96, 1, false);
    cylGeomY.rotateX(Math.PI / 2);
    const cylMesh = new THREE.Mesh(cylGeomY, material);
    group.add(cylMesh);

    // Dot positioning constants
    const dotSpacing = toNumber(settings.dot_spacing, 2.54);
    const dotColAngleOffsets = [-(dotSpacing / radius) / 2, (dotSpacing / radius) / 2];
    const dotRowOffsets = [dotSpacing, 0, -dotSpacing];
    const dotIndexToRowCol = [
        [0, 0], [1, 0], [2, 0],
        [0, 1], [1, 1], [2, 1]
    ];

    const leftMargin = toNumber(settings.left_margin, 8);
    const topMargin = toNumber(settings.top_margin, 8);
    const cellSpacing = toNumber(settings.cell_spacing, 6.0);
    const lineSpacing = toNumber(settings.line_spacing, 10.0);
    const xAdjust = toNumber(settings.braille_x_adjust, 0);
    const yAdjust = toNumber(settings.braille_y_adjust, 0);
    const availableColumns = getAvailableColumns(settings);
    const gridRows = getGridRows(settings);

    const dotHeight = toNumber(settings.emboss_dot_height, 0.6);
    const centerRadialDistance = radius + dotHeight / 2;
    const thetaOffset = seamOffsetDeg * Math.PI / 180;

    const dotGeom = createDotGeometry(settings);
    const zCenterOffset = -height / 2; // center cylinder along Z

    for (let rowIdx = 0; rowIdx < gridRows; rowIdx++) {
        const brailleText = (translatedLines[rowIdx] || '').slice(0, availableColumns);
        const yLocal = toNumber(settings.card_height, 54) - topMargin - (rowIdx * lineSpacing) + yAdjust; // planar Y maps to local Z

        for (let col = 0; col < brailleText.length; col++) {
            const ch = brailleText[col];
            const dots = brailleUnicodeToDots(ch);
            const xCell = leftMargin + ((col + 1) * cellSpacing) + xAdjust; // planar X maps to angle

            const circumference = Math.PI * diameter;
            const baseTheta = (xCell / circumference) * Math.PI * 2 + thetaOffset;

            for (let i = 0; i < 6; i++) {
                if (!dots[i]) continue;
                const [r, c] = dotIndexToRowCol[i];
                const theta = baseTheta + dotColAngleOffsets[c];

                const rHat = new THREE.Vector3(Math.cos(theta), Math.sin(theta), 0);
                const tangent = new THREE.Vector3(-Math.sin(theta), Math.cos(theta), 0);

                const mesh = new THREE.Mesh(dotGeom, material);
                // Rotate so +Z aligns with radial direction rHat
                const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), rHat);
                mesh.setRotationFromQuaternion(q);

                const zLocal = yLocal + dotRowOffsets[r] + zCenterOffset;
                const xWorld = rHat.x * centerRadialDistance;
                const yWorld = rHat.y * centerRadialDistance;
                mesh.position.set(xWorld, yWorld, zLocal);
                group.add(mesh);
            }
        }
    }

    return group;
}


