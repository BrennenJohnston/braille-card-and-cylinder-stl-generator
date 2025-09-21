/**
 * Geometry Utilities for Braille STL Generation
 * Helper functions for 3D geometry creation and optimization
 */

import * as THREE from 'three';

/**
 * Create rounded box geometry (card with rounded corners)
 * @param {number} width - Box width
 * @param {number} height - Box height  
 * @param {number} thickness - Box thickness
 * @param {number} radius - Corner radius
 * @returns {THREE.ExtrudeGeometry} Rounded box geometry
 */
export function createRoundedBox(width, height, thickness, radius = 2) {
  console.log(`📦 Creating rounded box: ${width}×${height}×${thickness}, radius=${radius}`);
  
  const shape = new THREE.Shape();
  
  // Clamp radius to prevent issues
  const maxRadius = Math.min(width / 2, height / 2);
  const clampedRadius = Math.min(radius, maxRadius);
  
  // Start from bottom-left corner + radius
  shape.moveTo(clampedRadius, 0);
  
  // Bottom edge
  shape.lineTo(width - clampedRadius, 0);
  
  // Bottom-right corner
  shape.quadraticCurveTo(width, 0, width, clampedRadius);
  
  // Right edge
  shape.lineTo(width, height - clampedRadius);
  
  // Top-right corner
  shape.quadraticCurveTo(width, height, width - clampedRadius, height);
  
  // Top edge
  shape.lineTo(clampedRadius, height);
  
  // Top-left corner
  shape.quadraticCurveTo(0, height, 0, height - clampedRadius);
  
  // Left edge
  shape.lineTo(0, clampedRadius);
  
  // Bottom-left corner
  shape.quadraticCurveTo(0, 0, clampedRadius, 0);
  
  // Extrude to create 3D shape
  const extrudeSettings = {
    depth: thickness,
    bevelEnabled: false
  };
  
  const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
  
  // Center the geometry
  geometry.translate(-width / 2, -height / 2, -thickness / 2);
  
  return geometry;
}

/**
 * Create cylinder geometry for braille dots
 * @param {number} radius - Dot radius
 * @param {number} height - Dot height
 * @param {number} segments - Radial segments
 * @returns {THREE.CylinderGeometry} Dot geometry
 */
export function createBrailleDot(radius = 0.75, height = 0.5, segments = 16) {
  // Use cylinder for more consistent boolean operations
  return new THREE.CylinderGeometry(
    radius,   // Top radius
    radius,   // Bottom radius  
    height,   // Height
    segments  // Radial segments
  );
}

/**
 * Create cone geometry for tapered braille dots
 * @param {number} topRadius - Top radius
 * @param {number} bottomRadius - Bottom radius
 * @param {number} height - Cone height
 * @param {number} segments - Radial segments
 * @returns {THREE.CylinderGeometry} Cone geometry
 */
export function createBrailleCone(topRadius = 0.5, bottomRadius = 0.75, height = 0.5, segments = 16) {
  return new THREE.CylinderGeometry(
    topRadius,    // Top radius (smaller)
    bottomRadius, // Bottom radius (larger)
    height,       // Height
    segments      // Radial segments
  );
}

/**
 * Create sphere geometry for rounded braille dots
 * @param {number} radius - Sphere radius
 * @param {number} widthSegments - Width segments
 * @param {number} heightSegments - Height segments
 * @returns {THREE.SphereGeometry} Sphere geometry
 */
export function createBrailleSphere(radius = 0.75, widthSegments = 16, heightSegments = 12) {
  return new THREE.SphereGeometry(radius, widthSegments, heightSegments);
}

/**
 * Calculate optimal geometry resolution based on model size
 * @param {number} modelSize - Approximate model size
 * @returns {Object} Suggested resolution settings
 */
export function calculateOptimalResolution(modelSize) {
  let segments, subdivisions;
  
  if (modelSize < 50) {
    segments = 8;
    subdivisions = 1;
  } else if (modelSize < 100) {
    segments = 12;
    subdivisions = 2;
  } else {
    segments = 16;
    subdivisions = 2;
  }
  
  return {
    dotSegments: segments,
    cardSubdivisions: subdivisions,
    cylinderSegments: segments * 2
  };
}

/**
 * Spatial indexing for performance optimization
 */
export class SpatialIndex {
  constructor(cellSize = 10) {
    this.cellSize = cellSize;
    this.cells = new Map();
    this.itemCount = 0;
    
    console.log(`🗺️ Spatial index initialized with cell size ${cellSize}`);
  }

  /**
   * Add item to spatial index
   * @param {*} item - Item to add
   * @param {number} x - X coordinate
   * @param {number} y - Y coordinate
   * @param {number} z - Z coordinate (optional)
   */
  add(item, x, y, z = 0) {
    const cellX = Math.floor(x / this.cellSize);
    const cellY = Math.floor(y / this.cellSize);
    const cellZ = Math.floor(z / this.cellSize);
    const key = `${cellX},${cellY},${cellZ}`;
    
    if (!this.cells.has(key)) {
      this.cells.set(key, []);
    }
    
    this.cells.get(key).push({ item, x, y, z });
    this.itemCount++;
  }

  /**
   * Get nearby items within radius
   * @param {number} x - X coordinate
   * @param {number} y - Y coordinate
   * @param {number} z - Z coordinate
   * @param {number} radius - Search radius
   * @returns {Array} Nearby items
   */
  getNearby(x, y, z = 0, radius = 5) {
    const nearby = [];
    const cellRadius = Math.ceil(radius / this.cellSize);
    const centerCellX = Math.floor(x / this.cellSize);
    const centerCellY = Math.floor(y / this.cellSize);
    const centerCellZ = Math.floor(z / this.cellSize);
    
    for (let dx = -cellRadius; dx <= cellRadius; dx++) {
      for (let dy = -cellRadius; dy <= cellRadius; dy++) {
        for (let dz = -cellRadius; dz <= cellRadius; dz++) {
          const key = `${centerCellX + dx},${centerCellY + dy},${centerCellZ + dz}`;
          const cell = this.cells.get(key);
          
          if (cell) {
            for (const entry of cell) {
              const dist = Math.sqrt(
                Math.pow(entry.x - x, 2) + 
                Math.pow(entry.y - y, 2) + 
                Math.pow(entry.z - z, 2)
              );
              if (dist <= radius) {
                nearby.push(entry);
              }
            }
          }
        }
      }
    }
    
    return nearby;
  }

  /**
   * Get all items in spatial index
   * @returns {Array} All items
   */
  getAllItems() {
    const allItems = [];
    for (const cell of this.cells.values()) {
      allItems.push(...cell);
    }
    return allItems;
  }

  /**
   * Clear spatial index
   */
  clear() {
    this.cells.clear();
    this.itemCount = 0;
  }

  /**
   * Get spatial index statistics
   * @returns {Object} Statistics
   */
  getStats() {
    return {
      totalItems: this.itemCount,
      totalCells: this.cells.size,
      cellSize: this.cellSize,
      averageItemsPerCell: this.itemCount / this.cells.size || 0
    };
  }
}

/**
 * Optimize geometry for better performance
 * @param {THREE.BufferGeometry} geometry - Geometry to optimize
 * @returns {THREE.BufferGeometry} Optimized geometry
 */
export function optimizeGeometry(geometry) {
  console.log('⚡ Optimizing geometry...');
  
  // Merge vertices
  geometry.mergeVertices();
  
  // Compute vertex normals if missing
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }
  
  // Compute bounding box/sphere for culling
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  
  console.log('✅ Geometry optimization complete');
  return geometry;
}

/**
 * Calculate geometry memory usage
 * @param {THREE.BufferGeometry} geometry - Geometry to analyze
 * @returns {Object} Memory usage statistics
 */
export function calculateGeometryMemory(geometry) {
  let totalBytes = 0;
  let attributes = {};
  
  for (const [name, attribute] of Object.entries(geometry.attributes)) {
    const bytes = attribute.array.byteLength;
    totalBytes += bytes;
    attributes[name] = {
      count: attribute.count,
      itemSize: attribute.itemSize,
      bytes: bytes,
      type: attribute.array.constructor.name
    };
  }
  
  if (geometry.index) {
    const indexBytes = geometry.index.array.byteLength;
    totalBytes += indexBytes;
    attributes.index = {
      count: geometry.index.count,
      bytes: indexBytes,
      type: geometry.index.array.constructor.name
    };
  }
  
  return {
    totalBytes,
    totalKB: totalBytes / 1024,
    totalMB: totalBytes / (1024 * 1024),
    attributes
  };
}

/**
 * Create debug wireframe from geometry
 * @param {THREE.BufferGeometry} geometry - Source geometry
 * @returns {THREE.WireframeGeometry} Wireframe geometry
 */
export function createDebugWireframe(geometry) {
  return new THREE.WireframeGeometry(geometry);
}

/**
 * Validate geometry for STL export
 * @param {THREE.BufferGeometry} geometry - Geometry to validate
 * @returns {Object} Validation results
 */
export function validateGeometryForSTL(geometry) {
  const issues = [];
  const warnings = [];
  
  // Check for required attributes
  if (!geometry.attributes.position) {
    issues.push('Missing position attribute');
  }
  
  // Check vertex count
  const vertexCount = geometry.attributes.position ? geometry.attributes.position.count : 0;
  if (vertexCount === 0) {
    issues.push('No vertices found');
  }
  
  // Check triangle count
  const triangleCount = geometry.index ? geometry.index.count / 3 : vertexCount / 3;
  if (triangleCount === 0) {
    issues.push('No triangles found');
  }
  
  // Warn about large models
  if (triangleCount > 100000) {
    warnings.push(`Large model: ${triangleCount} triangles may cause slow export`);
  }
  
  // Check for normals
  if (!geometry.attributes.normal) {
    warnings.push('No normals found - will be calculated during export');
  }
  
  // Check for non-manifold edges (basic)
  if (geometry.index && geometry.index.count % 3 !== 0) {
    issues.push('Invalid triangle count - index count not divisible by 3');
  }
  
  return {
    valid: issues.length === 0,
    issues,
    warnings,
    stats: {
      vertices: vertexCount,
      triangles: triangleCount,
      hasNormals: !!geometry.attributes.normal,
      hasIndices: !!geometry.index
    }
  };
}
