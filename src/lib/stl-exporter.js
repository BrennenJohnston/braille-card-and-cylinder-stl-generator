/**
 * STLExporter - Export Three.js geometry to STL binary format
 * High-performance STL generation for 3D printing
 */

import * as THREE from 'three';

export class STLExporter {
  constructor() {
    console.log('📤 STLExporter initialized');
  }

  /**
   * Export geometry to STL binary format
   * @param {THREE.BufferGeometry} geometry
   * @returns {ArrayBuffer} STL binary data
   */
  exportBinary(geometry) {
    console.log('🔄 Exporting geometry to STL binary format...');
    
    if (!geometry) {
      throw new Error('No geometry provided for STL export');
    }

    const positions = geometry.attributes.position.array;
    const normals = geometry.attributes.normal?.array;
    const indices = geometry.index?.array;
    
    const triangleCount = indices ? indices.length / 3 : positions.length / 9;
    console.log(`📊 Exporting ${triangleCount} triangles to STL...`);
    
    const bufferSize = 84 + (50 * triangleCount); // STL binary format size
    const buffer = new ArrayBuffer(bufferSize);
    const view = new DataView(buffer);
    
    // STL header (80 bytes) - can contain any message
    const header = 'Braille STL Generator v2.0 - Cloudflare Pages Edition';
    for (let i = 0; i < 80; i++) {
      view.setUint8(i, i < header.length ? header.charCodeAt(i) : 0);
    }
    
    // Number of triangles (4 bytes, little endian)
    view.setUint32(80, triangleCount, true);
    
    // Write triangles
    let offset = 84;
    for (let i = 0; i < triangleCount; i++) {
      // Get vertex indices
      const a = indices ? indices[i * 3] : i * 3;
      const b = indices ? indices[i * 3 + 1] : i * 3 + 1;
      const c = indices ? indices[i * 3 + 2] : i * 3 + 2;
      
      // Calculate normal if not provided
      const normal = normals ? 
        this.getVertexNormal(normals, a) : 
        this.calculateNormal(positions, a, b, c);
      
      // Write normal (12 bytes)
      view.setFloat32(offset, normal.x, true);
      view.setFloat32(offset + 4, normal.y, true);
      view.setFloat32(offset + 8, normal.z, true);
      offset += 12;
      
      // Write vertices (36 bytes total, 12 each)
      this.writeVertex(view, offset, positions, a);
      offset += 12;
      this.writeVertex(view, offset, positions, b);
      offset += 12;
      this.writeVertex(view, offset, positions, c);
      offset += 12;
      
      // Attribute byte count (2 bytes, unused)
      view.setUint16(offset, 0, true);
      offset += 2;
      
      // Progress callback for large models
      if (i % 1000 === 0 && i > 0) {
        // Yield occasionally for large models
        setTimeout(() => {}, 0);
      }
    }
    
    console.log(`✅ STL export complete! File size: ${(bufferSize / 1024).toFixed(1)} KB`);
    return buffer;
  }

  /**
   * Export geometry to STL ASCII format (for debugging)
   * @param {THREE.BufferGeometry} geometry
   * @returns {string} STL ASCII data
   */
  exportASCII(geometry) {
    console.log('📝 Exporting geometry to STL ASCII format...');
    
    const positions = geometry.attributes.position.array;
    const normals = geometry.attributes.normal?.array;
    const indices = geometry.index?.array;
    
    const triangleCount = indices ? indices.length / 3 : positions.length / 9;
    
    let output = 'solid BrailleSTLGenerator\n';
    
    for (let i = 0; i < triangleCount; i++) {
      const a = indices ? indices[i * 3] : i * 3;
      const b = indices ? indices[i * 3 + 1] : i * 3 + 1;
      const c = indices ? indices[i * 3 + 2] : i * 3 + 2;
      
      // Calculate normal
      const normal = normals ? 
        this.getVertexNormal(normals, a) : 
        this.calculateNormal(positions, a, b, c);
      
      output += `  facet normal ${normal.x.toExponential()} ${normal.y.toExponential()} ${normal.z.toExponential()}\n`;
      output += '    outer loop\n';
      
      // Write vertices
      const v1 = this.getVertex(positions, a);
      const v2 = this.getVertex(positions, b);
      const v3 = this.getVertex(positions, c);
      
      output += `      vertex ${v1.x.toExponential()} ${v1.y.toExponential()} ${v1.z.toExponential()}\n`;
      output += `      vertex ${v2.x.toExponential()} ${v2.y.toExponential()} ${v2.z.toExponential()}\n`;
      output += `      vertex ${v3.x.toExponential()} ${v3.y.toExponential()} ${v3.z.toExponential()}\n`;
      
      output += '    endloop\n';
      output += '  endfacet\n';
    }
    
    output += 'endsolid BrailleSTLGenerator\n';
    
    console.log(`✅ ASCII STL export complete! ${triangleCount} triangles`);
    return output;
  }

  /**
   * Write vertex data to DataView
   */
  writeVertex(view, offset, positions, index) {
    view.setFloat32(offset, positions[index * 3], true);
    view.setFloat32(offset + 4, positions[index * 3 + 1], true);
    view.setFloat32(offset + 8, positions[index * 3 + 2], true);
  }

  /**
   * Get vertex as Vector3
   */
  getVertex(positions, index) {
    return new THREE.Vector3(
      positions[index * 3],
      positions[index * 3 + 1],
      positions[index * 3 + 2]
    );
  }

  /**
   * Calculate face normal from vertices
   */
  calculateNormal(positions, a, b, c) {
    const v1 = new THREE.Vector3(
      positions[a * 3], positions[a * 3 + 1], positions[a * 3 + 2]
    );
    const v2 = new THREE.Vector3(
      positions[b * 3], positions[b * 3 + 1], positions[b * 3 + 2]
    );
    const v3 = new THREE.Vector3(
      positions[c * 3], positions[c * 3 + 1], positions[c * 3 + 2]
    );
    
    const edge1 = v2.clone().sub(v1);
    const edge2 = v3.clone().sub(v1);
    const normal = edge1.cross(edge2).normalize();
    
    return normal;
  }

  /**
   * Get vertex normal from normals array
   */
  getVertexNormal(normals, index) {
    return new THREE.Vector3(
      normals[index * 3],
      normals[index * 3 + 1],
      normals[index * 3 + 2]
    );
  }

  /**
   * Validate geometry before export
   */
  validateGeometry(geometry) {
    if (!geometry) {
      throw new Error('Geometry is null or undefined');
    }
    
    if (!geometry.attributes.position) {
      throw new Error('Geometry missing position attribute');
    }
    
    const positions = geometry.attributes.position.array;
    if (positions.length === 0) {
      throw new Error('Geometry has no vertices');
    }
    
    if (positions.length % 3 !== 0) {
      throw new Error('Invalid position data - not divisible by 3');
    }
    
    console.log(`✓ Geometry validation passed: ${positions.length / 3} vertices`);
    return true;
  }

  /**
   * Get export statistics
   */
  getStats(geometry) {
    const positions = geometry.attributes.position.array;
    const indices = geometry.index?.array;
    
    const vertexCount = positions.length / 3;
    const triangleCount = indices ? indices.length / 3 : vertexCount / 3;
    const estimatedFileSize = 84 + (50 * triangleCount);
    
    return {
      vertices: vertexCount,
      triangles: triangleCount,
      estimatedFileSize,
      hasNormals: !!geometry.attributes.normal,
      hasIndices: !!geometry.index
    };
  }
}
