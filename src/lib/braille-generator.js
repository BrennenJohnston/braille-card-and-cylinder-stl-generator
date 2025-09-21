/**
 * BrailleGenerator - Core STL Generation Logic  
 * Ported from Python backend with three-bvh-csg for fast boolean operations
 */

import * as THREE from 'three';
import { SUBTRACTION, ADDITION, Brush, Evaluator } from 'three-bvh-csg';

/**
 * Card Settings - Configuration for braille card generation
 * Ported from Python CardSettings class
 */
export class CardSettings {
  constructor(options = {}) {
    // Card dimensions (mm)
    this.card_width = options.card_width ?? 85.60;
    this.card_height = options.card_height ?? 53.98;
    this.card_thickness = options.card_thickness ?? 0.76;
    
    // Grid configuration
    this.grid_columns = options.grid_columns ?? 32;
    this.grid_rows = options.grid_rows ?? 4;
    
    // Spacing (mm)
    this.cell_spacing = options.cell_spacing ?? 2.5;
    this.line_spacing = options.line_spacing ?? 10.0;
    this.dot_spacing = options.dot_spacing ?? 2.5;
    
    // Margins (mm)
    this.left_margin = options.left_margin ?? 5.0;
    this.top_margin = options.top_margin ?? 5.0;
    
    // Braille positioning adjustments
    this.braille_x_adjust = options.braille_x_adjust ?? 0.0;
    this.braille_y_adjust = options.braille_y_adjust ?? 0.0;
    
    // Dot configuration
    this.active_dot_height = options.active_dot_height ?? 0.6;
    this.active_dot_base_diameter = options.active_dot_base_diameter ?? 1.5;
    this.active_dot_top_diameter = options.active_dot_top_diameter ?? 1.2;
    
    // Advanced dot options
    this.use_rounded_dots = options.use_rounded_dots ?? false;
    this.rounded_dot_base_diameter = options.rounded_dot_base_diameter ?? 2.0;
    this.rounded_dot_dome_diameter = options.rounded_dot_dome_diameter ?? 1.5;
    this.rounded_dot_base_height = options.rounded_dot_base_height ?? 0.2;
    this.rounded_dot_dome_height = options.rounded_dot_dome_height ?? 0.6;
    
    // Indicators and markers
    this.indicator_shapes = options.indicator_shapes ?? 1;
    this.recess_shape = options.recess_shape ?? 1;
    
    // Counter plate settings
    this.recessed_dot_base_diameter = options.recessed_dot_base_diameter ?? 1.8;
    this.hemisphere_subdivisions = options.hemisphere_subdivisions ?? 1;
  }
}

export class BrailleGenerator {
  constructor() {
    this.evaluator = new Evaluator();
    this.evaluator.attributes = ['position', 'normal'];
    this.evaluator.useGroups = false;
    
    // Braille dot position mapping (Python: dot_positions)
    // Maps dot index (0-5) to [row, col] in braille cell
    this.dotPositions = [
      [0, 0], [1, 0], [2, 0],  // Left column: dots 1, 2, 3
      [0, 1], [1, 1], [2, 1]   // Right column: dots 4, 5, 6
    ];
    
    console.log('🔧 BrailleGenerator initialized with three-bvh-csg');
  }

  /**
   * Convert braille Unicode character to dot pattern
   * Ported from Python braille_to_dots function
   * @param {string} brailleChar - Braille Unicode character (U+2800-U+28FF)
   * @returns {number[]} Array of 6 values (0 or 1) representing dot pattern
   */
  brailleToDots(brailleChar) {
    if (!brailleChar || typeof brailleChar !== 'string') {
      return [0, 0, 0, 0, 0, 0];
    }
    
    const codePoint = brailleChar.charCodeAt(0);
    
    // Check if it's in the braille Unicode block (U+2800 to U+28FF)
    if (codePoint < 0x2800 || codePoint > 0x28FF) {
      return [0, 0, 0, 0, 0, 0];
    }
    
    // Extract dot pattern (bits 0-7 for dots 1-8)
    const dotPattern = codePoint - 0x2800;
    
    // Convert to 6-dot pattern (dots 1-6)
    const dots = [0, 0, 0, 0, 0, 0];
    for (let i = 0; i < 6; i++) {
      if (dotPattern & (1 << i)) {
        dots[i] = 1;
      }
    }
    
    return dots;
  }

  /**
   * Create a braille dot at the specified position
   * Ported from Python create_braille_dot function
   * @param {number} x - X position (mm)
   * @param {number} y - Y position (mm) 
   * @param {number} z - Z position (mm)
   * @param {CardSettings} settings - Card settings
   * @returns {THREE.BufferGeometry} Dot geometry
   */
  createBrailleDot(x, y, z, settings) {
    let dotGeometry;
    
    if (settings.use_rounded_dots) {
      // Create rounded dot (cone frustum + spherical cap)
      const baseRadius = Math.max(0.0, settings.rounded_dot_base_diameter / 2.0);
      const topRadius = Math.max(0.0, settings.rounded_dot_dome_diameter / 2.0);
      const baseHeight = Math.max(0.0, settings.rounded_dot_base_height);
      const domeHeight = Math.max(0.0, settings.rounded_dot_dome_height);
      
      if (baseRadius > 0 && baseHeight >= 0 && domeHeight > 0) {
        const parts = [];
        
        // Create frustum base if height > 0
        if (baseHeight > 0) {
          // Create cylinder and taper the top
          const frustum = new THREE.CylinderGeometry(
            topRadius, baseRadius, baseHeight, 48
          );
          parts.push(frustum);
        }
        
        // Create spherical cap dome
        if (domeHeight > 0 && topRadius > 0) {
          // Approximate spherical cap with sphere geometry
          const R = (topRadius * topRadius + domeHeight * domeHeight) / (2.0 * domeHeight);
          const dome = new THREE.SphereGeometry(R, 32, 16);
          
          // Position dome at top of frustum
          const domeOffset = baseHeight / 2.0 + (domeHeight - R);
          dome.translate(0, domeOffset, 0);
          
          parts.push(dome);
        }
        
        // Merge parts
        if (parts.length > 1) {
          // For now, use the frustum as primary geometry
          // TODO: Implement proper boolean union
          dotGeometry = parts[0];
        } else {
          dotGeometry = parts[0] || new THREE.CylinderGeometry(baseRadius, baseRadius, baseHeight, 16);
        }
      } else {
        // Fallback to simple cylinder
        dotGeometry = new THREE.CylinderGeometry(
          settings.active_dot_base_diameter / 2, 
          settings.active_dot_base_diameter / 2, 
          settings.active_dot_height, 
          16
        );
      }
    } else {
      // Standard cone frustum dot
      const baseRadius = settings.active_dot_base_diameter / 2;
      const topRadius = settings.active_dot_top_diameter / 2;
      const height = settings.active_dot_height;
      
      dotGeometry = new THREE.CylinderGeometry(topRadius, baseRadius, height, 16);
    }
    
    // Position the dot
    dotGeometry.translate(x, y, z);
    
    return dotGeometry;
  }

  /**
   * Generate braille card STL
   * Ported from Python create_positive_plate_mesh function
   * @param {string[]} lines - Array of braille Unicode text lines
   * @param {Object} options - Generation options
   * @returns {THREE.BufferGeometry} - Final geometry
   */
  async generateCard(lines, options = {}) {
    const settings = new CardSettings(options);
    const onProgress = options.onProgress || (() => {});
    
    console.log('🏗️ Generating braille card...');
    console.log(`Grid: ${settings.grid_columns} columns × ${settings.grid_rows} rows`);
    console.log(`Card: ${settings.card_width}×${settings.card_height}×${settings.card_thickness}mm`);

    onProgress(5, 'Creating card base...');

    // Create card base
    const baseGeometry = new THREE.BoxGeometry(
      settings.card_width, 
      settings.card_height, 
      settings.card_thickness
    );
    
    // Position card so bottom-left-back corner is at origin
    baseGeometry.translate(
      settings.card_width / 2, 
      settings.card_height / 2, 
      settings.card_thickness / 2
    );
    
    const cardBrush = new Brush(baseGeometry);
    const dotBrushes = [];
    
    onProgress(10, 'Processing braille text...');

    // Validate input lines
    const processedLines = [];
    for (let row = 0; row < Math.min(lines.length, settings.grid_rows); row++) {
      const line = lines[row] || '';
      processedLines.push(line.trim());
    }

    // Dot positioning constants (from Python)
    const dotColOffsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2];
    const dotRowOffsets = [settings.dot_spacing, 0, -settings.dot_spacing];

    let totalDots = 0;
    let processedDots = 0;

    // Count total dots for progress
    for (let row = 0; row < processedLines.length; row++) {
      const lineText = processedLines[row];
      for (const char of lineText) {
        const dots = this.brailleToDots(char);
        totalDots += dots.filter(d => d === 1).length;
      }
    }

    console.log(`🔵 Processing ${totalDots} braille dots...`);

    // Process each line in top-down order (ported from Python)
    for (let rowNum = 0; rowNum < processedLines.length; rowNum++) {
      const lineText = processedLines[rowNum];
      if (!lineText) continue;

      // Check if input contains proper braille Unicode
      const hasBrailleChars = Array.from(lineText).some(char => {
        const code = char.charCodeAt(0);
        return code >= 0x2800 && code <= 0x28FF;
      });

      if (!hasBrailleChars) {
        console.warn(`Line ${rowNum + 1} does not contain proper braille Unicode, skipping`);
        continue;
      }

      // Calculate Y position for this row (Python logic)
      const yPos = settings.card_height - settings.top_margin - 
                   (rowNum * settings.line_spacing) + settings.braille_y_adjust;

      // Process each character in the line
      const characters = Array.from(lineText);
      for (let colNum = 0; colNum < characters.length && colNum < settings.grid_columns - 2; colNum++) {
        const brailleChar = characters[colNum];
        const dots = this.brailleToDots(brailleChar);

        // Calculate X position (with space for indicators if enabled)
        const indicatorOffset = settings.indicator_shapes ? 1 : 0;
        const xPos = settings.left_margin + 
                     ((colNum + indicatorOffset) * settings.cell_spacing) + 
                     settings.braille_x_adjust;

        // Create dots for this cell
        for (let i = 0; i < dots.length; i++) {
          if (dots[i] === 1) {
            const dotPos = this.dotPositions[i];
            const dotX = xPos + dotColOffsets[dotPos[1]];
            const dotY = yPos + dotRowOffsets[dotPos[0]];
            // Position Z so dot sits on card surface
            const dotZ = settings.card_thickness + settings.active_dot_height / 2;

            const dotGeometry = this.createBrailleDot(dotX, dotY, dotZ, settings);
            dotBrushes.push(new Brush(dotGeometry));

            processedDots++;

            // Update progress
            if (processedDots % 10 === 0 || processedDots === totalDots) {
              const progress = 10 + (processedDots / totalDots) * 80;
              onProgress(Math.min(90, progress), `Processing dots: ${processedDots}/${totalDots}`);
              
              // Yield occasionally
              if (processedDots % 50 === 0) {
                await new Promise(resolve => setTimeout(resolve, 0));
              }
            }
          }
        }
      }
    }

    onProgress(90, 'Combining geometry...');

    // Union all dots with the card base
    let result = cardBrush;
    const batchSize = 20; // Process dots in smaller batches
    
    for (let i = 0; i < dotBrushes.length; i += batchSize) {
      const batch = dotBrushes.slice(i, i + batchSize);
      
      for (const dotBrush of batch) {
        try {
          result = this.evaluator.evaluate(result, dotBrush, ADDITION);
        } catch (error) {
          console.warn('Failed to union dot:', error.message);
        }
      }
      
      // Update progress
      const batchProgress = 90 + ((i + batch.length) / dotBrushes.length) * 10;
      onProgress(Math.min(100, batchProgress), 'Combining geometry...');
      
      // Yield between batches
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    onProgress(100, 'Card generation complete!');
    console.log('✅ Braille card generation complete!');

    return result.geometry;
  }


  /**
   * Generate cylinder STL
   * Ported from Python generate_cylinder_stl function
   * @param {string[]} lines - Array of braille Unicode text lines
   * @param {Object} options - Cylinder dimensions and settings
   * @returns {THREE.BufferGeometry} - Final geometry
   */
  async generateCylinder(lines, options = {}) {
    const settings = new CardSettings(options);
    const onProgress = options.onProgress || (() => {});
    
    // Cylinder parameters
    const cylinderParams = {
      diameter_mm: 31.35,
      height_mm: settings.card_height,
      polygonal_cutout_radius_mm: 13,
      polygonal_cutout_sides: 12,
      seam_offset_deg: 355,
      ...options.cylinder_params
    };
    
    const diameter = cylinderParams.diameter_mm;
    const height = cylinderParams.height_mm;
    const radius = diameter / 2;
    
    console.log('🥤 Generating braille cylinder...');
    console.log(`Cylinder: ${diameter}mm diameter, ${height}mm height`);

    onProgress(10, 'Creating cylinder shell...');

    // Create base cylinder
    const cylinderGeometry = new THREE.CylinderGeometry(radius, radius, height, 48);
    // Position cylinder so bottom center is at origin
    cylinderGeometry.translate(0, height / 2, 0);
    
    const cylinderBrush = new Brush(cylinderGeometry);

    onProgress(20, 'Processing braille text for cylinder...');

    // Validate input lines
    const processedLines = [];
    for (let row = 0; row < Math.min(lines.length, settings.grid_rows); row++) {
      const line = lines[row] || '';
      processedLines.push(line.trim());
    }

    // Calculate angular spacing for dots on cylinder surface
    const dotSpacingAngle = settings.dot_spacing / radius;
    const cellSpacingAngle = settings.cell_spacing / radius;
    const dotColAngleOffsets = [-dotSpacingAngle / 2, dotSpacingAngle / 2];
    const dotRowOffsets = [settings.dot_spacing, 0, -settings.dot_spacing];

    // Calculate grid layout on cylinder
    const gridWidth = (settings.grid_columns - 1) * settings.cell_spacing;
    const gridAngle = gridWidth / radius;
    const startAngle = -gridAngle / 2;

    const dotBrushes = [];
    let totalDots = 0;
    let processedDots = 0;

    // Count total dots
    for (const lineText of processedLines) {
      for (const char of lineText) {
        const dots = this.brailleToDots(char);
        totalDots += dots.filter(d => d === 1).length;
      }
    }

    console.log(`🔵 Processing ${totalDots} cylinder dots...`);

    // Process each line
    for (let rowNum = 0; rowNum < processedLines.length; rowNum++) {
      const lineText = processedLines[rowNum];
      if (!lineText) continue;

      // Check for braille Unicode
      const hasBrailleChars = Array.from(lineText).some(char => {
        const code = char.charCodeAt(0);
        return code >= 0x2800 && code <= 0x28FF;
      });

      if (!hasBrailleChars) {
        console.warn(`Line ${rowNum + 1} does not contain proper braille Unicode, skipping`);
        continue;
      }

      // Calculate Y position on cylinder (vertical)
      const yPos = height - settings.top_margin - (rowNum * settings.line_spacing) + settings.braille_y_adjust;

      // Process each character
      const characters = Array.from(lineText);
      for (let colNum = 0; colNum < characters.length && colNum < settings.grid_columns - 2; colNum++) {
        const brailleChar = characters[colNum];
        const dots = this.brailleToDots(brailleChar);

        // Calculate angle position on cylinder
        const cellAngle = startAngle + (colNum * cellSpacingAngle);

        // Create dots for this cell
        for (let i = 0; i < dots.length; i++) {
          if (dots[i] === 1) {
            const dotPos = this.dotPositions[i];
            const dotAngle = cellAngle + dotColAngleOffsets[dotPos[1]];
            const dotY = yPos + dotRowOffsets[dotPos[0]];

            // Convert cylindrical coordinates to Cartesian
            const dotRadius = radius + settings.active_dot_height / 2;
            const dotX = dotRadius * Math.cos(dotAngle);
            const dotZ = dotRadius * Math.sin(dotAngle);

            // Create dot geometry positioned on cylinder surface
            const dotGeometry = this.createBrailleDot(dotX, dotY, dotZ, settings);
            dotBrushes.push(new Brush(dotGeometry));

            processedDots++;

            // Update progress
            if (processedDots % 10 === 0 || processedDots === totalDots) {
              const progress = 20 + (processedDots / totalDots) * 60;
              onProgress(Math.min(80, progress), `Processing cylinder dots: ${processedDots}/${totalDots}`);
            }
          }
        }
      }
    }

    onProgress(80, 'Combining cylinder geometry...');

    // Union dots with cylinder
    let result = cylinderBrush;
    const batchSize = 15; // Smaller batches for cylinder

    for (let i = 0; i < dotBrushes.length; i += batchSize) {
      const batch = dotBrushes.slice(i, i + batchSize);
      
      for (const dotBrush of batch) {
        try {
          result = this.evaluator.evaluate(result, dotBrush, UNION);
        } catch (error) {
          console.warn('Failed to union cylinder dot:', error.message);
        }
      }
      
      const batchProgress = 80 + ((i + batch.length) / dotBrushes.length) * 20;
      onProgress(Math.min(100, batchProgress), 'Combining cylinder geometry...');
      
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    onProgress(100, 'Cylinder generation complete!');
    console.log('✅ Braille cylinder generation complete!');

    return result.geometry;
  }

  /**
   * Clean up resources
   */
  dispose() {
    // Clean up any retained resources
    console.log('🧹 BrailleGenerator cleanup complete');
  }
}
