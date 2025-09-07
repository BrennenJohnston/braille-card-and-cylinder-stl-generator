// Minimal ASCII STL exporter for THREE.js geometries
// Exports a THREE.Object3D (Mesh or Group) to an ASCII STL Blob

import * as THREE from './three.module.js';

function writeFacet(lines, normal, a, b, c) {
    lines.push(`  facet normal ${normal.x} ${normal.y} ${normal.z}`);
    lines.push('    outer loop');
    lines.push(`      vertex ${a.x} ${a.y} ${a.z}`);
    lines.push(`      vertex ${b.x} ${b.y} ${b.z}`);
    lines.push(`      vertex ${c.x} ${c.y} ${c.z}`);
    lines.push('    endloop');
    lines.push('  endfacet');
}

export function exportObjectToAsciiSTL(object3D, solidName = 'exported') {
    const lines = [];
    lines.push(`solid ${solidName}`);

    const tempA = new THREE.Vector3();
    const tempB = new THREE.Vector3();
    const tempC = new THREE.Vector3();
    const cb = new THREE.Vector3();
    const ab = new THREE.Vector3();

    object3D.updateWorldMatrix(true, true);

    object3D.traverse((obj) => {
        if (!obj.isMesh) return;

        const sourceGeom = obj.geometry;
        if (!sourceGeom) return;

        // Clone so we can apply world transform safely
        const geom = sourceGeom.clone();
        geom.applyMatrix4(obj.matrixWorld);

        // Ensure non-indexed geometry so we can iterate triangles easily
        const bufferGeom = geom.index ? geom.toNonIndexed() : geom;
        const position = bufferGeom.getAttribute('position');
        const vertexCount = position ? position.count : 0;
        if (vertexCount === 0) return;

        for (let i = 0; i < vertexCount; i += 3) {
            tempA.fromBufferAttribute(position, i);
            tempB.fromBufferAttribute(position, i + 1);
            tempC.fromBufferAttribute(position, i + 2);

            cb.subVectors(tempC, tempB);
            ab.subVectors(tempA, tempB);
            cb.cross(ab).normalize();

            writeFacet(lines, cb, tempA, tempB, tempC);
        }
    });

    lines.push('endsolid');

    const stlString = lines.join('\n');
    return new Blob([stlString], { type: 'model/stl' });
}


