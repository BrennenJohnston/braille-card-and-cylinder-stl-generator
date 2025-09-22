/**
 * Client-side STL Generator for Braille Cards and Cylinders
 * Uses three.js for 3D geometry and STL export
 */

// Import three.js and STLExporter from CDN (loaded in HTML)
// Assumes THREE and STLExporter are available globally

class BrailleSTLGenerator {
    constructor() {
        this.scene = new THREE.Scene();
        this.brailleDotPositions = [
            [0, 0], [0, 1], [0, 2],  // Left column
            [1, 0], [1, 1], [1, 2]   // Right column
        ];
    }

    /**
     * Generate STL for a braille card (positive/embossing plate)
     */
    generateCardSTL(lines, settings) {
        const scene = new THREE.Scene();
        
        // Card dimensions
        const cardWidth = parseFloat(settings.card_width) || 89;
        const cardHeight = parseFloat(settings.card_height) || 52;
        const cardThickness = parseFloat(settings.card_thickness) || 1.0;
        
        // Braille parameters - use the settings from the form
        const dotRadius = parseFloat(settings.emboss_dot_base_diameter) / 2 || 0.8;
        const dotHeight = parseFloat(settings.emboss_dot_height) || 0.5;
        const dotSpacing = parseFloat(settings.dot_spacing) || 2.5;
        const cellSpacing = parseFloat(settings.cell_spacing) || 6.5;
        const lineSpacing = parseFloat(settings.line_spacing) || 10;
        
        // Margins - use braille x/y adjust from form
        const marginLeft = parseFloat(settings.braille_x_adjust) || 4;
        const marginTop = parseFloat(settings.braille_y_adjust) || 4;
        
        // Create base card
        const cardGeometry = new THREE.BoxGeometry(cardWidth, cardHeight, cardThickness);
        const cardMaterial = new THREE.MeshBasicMaterial({ color: 0xcccccc });
        const card = new THREE.Mesh(cardGeometry, cardMaterial);
        card.position.z = cardThickness / 2;
        scene.add(card);
        
        // Add braille dots
        lines.forEach((line, lineIndex) => {
            if (!line || line.trim() === '') return;
            
            // Calculate starting position for this line
            const lineY = cardHeight/2 - marginTop - (lineIndex * lineSpacing);
            let currentX = -cardWidth/2 + marginLeft;
            
            // Process each braille character
            for (let i = 0; i < line.length; i++) {
                const char = line[i];
                if (this.isBrailleChar(char)) {
                    const dots = this.getBrailleDots(char);
                    
                    // Create dots for this character
                    dots.forEach(dotIndex => {
                        const [col, row] = this.brailleDotPositions[dotIndex];
                        const dotX = currentX + col * dotSpacing;
                        const dotY = lineY - row * dotSpacing;
                        
                        // Create dot (cylinder)
                        const dotGeometry = new THREE.CylinderGeometry(
                            dotRadius, dotRadius, dotHeight, 16
                        );
                        const dotMaterial = new THREE.MeshBasicMaterial({ color: 0x333333 });
                        const dot = new THREE.Mesh(dotGeometry, dotMaterial);
                        
                        // Position dot
                        dot.position.x = dotX;
                        dot.position.y = dotY;
                        dot.position.z = cardThickness + dotHeight/2;
                        dot.rotation.x = Math.PI / 2;
                        
                        scene.add(dot);
                    });
                    
                    currentX += cellSpacing;
                }
            }
        });
        
        // Merge geometries for better performance
        const mergedGeometry = this.mergeGeometries(scene);
        
        // Export to STL
        return this.exportSTL(mergedGeometry);
    }
    
    /**
     * Generate STL for counter plate (negative plate with recesses)
     */
    generateCounterPlateSTL(settings) {
        const scene = new THREE.Scene();
        
        // Card dimensions
        const cardWidth = parseFloat(settings.card_width) || 89;
        const cardHeight = parseFloat(settings.card_height) || 52;
        const thickness = parseFloat(settings.card_thickness) || 12;
        
        // Braille parameters - use the settings from the form
        const dotRadius = parseFloat(settings.emboss_dot_base_diameter) / 2 || 0.8;
        const dotSpacing = parseFloat(settings.dot_spacing) || 2.5;
        const cellSpacing = parseFloat(settings.cell_spacing) || 6.5;
        const lineSpacing = parseFloat(settings.line_spacing) || 10;
        
        // Recess parameters
        const recessDepth = parseFloat(settings.counter_dot_depth) || 1.0;
        const recessDiameter = parseFloat(settings.counter_dot_base_diameter) || 2.4;
        
        // Margins - use braille x/y adjust from form
        const marginLeft = parseFloat(settings.braille_x_adjust) || 4;
        const marginTop = parseFloat(settings.braille_y_adjust) || 4;
        const marginRight = parseFloat(settings.braille_x_adjust) || 4;
        const marginBottom = parseFloat(settings.braille_y_adjust) || 4;
        
        // Create base plate
        const plateGeometry = new THREE.BoxGeometry(cardWidth, cardHeight, thickness);
        const plateMaterial = new THREE.MeshBasicMaterial({ color: 0xaaaaaa });
        const plate = new THREE.Mesh(plateGeometry, plateMaterial);
        plate.position.z = thickness / 2;
        
        // Calculate grid of all possible dot positions
        const dotsPerLine = Math.floor((cardWidth - marginLeft - marginRight) / cellSpacing) * 6;
        const numLines = parseInt(settings.grid_rows) || 4;
        
        // Create recesses using CSG (Constructive Solid Geometry)
        // For simplicity, we'll create an array of cylinder positions
        const recesses = [];
        
        for (let lineIndex = 0; lineIndex < numLines; lineIndex++) {
            const lineY = cardHeight/2 - marginTop - (lineIndex * lineSpacing);
            let currentX = -cardWidth/2 + marginLeft;
            
            // Create recesses for all possible dot positions
            const cellsInLine = Math.floor((cardWidth - marginLeft - marginRight) / cellSpacing);
            
            for (let cellIndex = 0; cellIndex < cellsInLine; cellIndex++) {
                // All 6 dots in each cell
                for (let dotIndex = 0; dotIndex < 6; dotIndex++) {
                    const [col, row] = this.brailleDotPositions[dotIndex];
                    const dotX = currentX + col * dotSpacing;
                    const dotY = lineY - row * dotSpacing;
                    
                    recesses.push({ x: dotX, y: dotY });
                }
                currentX += cellSpacing;
            }
        }
        
        // Create a compound shape with holes
        // Note: True CSG operations would require a library like ThreeCSG
        // For now, we'll create a visual representation
        scene.add(plate);
        
        // Add visual representations of recesses
        recesses.forEach(pos => {
            const recessGeometry = new THREE.CylinderGeometry(
                recessDiameter/2, recessDiameter/2, recessDepth, 16
            );
            const recessMaterial = new THREE.MeshBasicMaterial({ color: 0x666666 });
            const recess = new THREE.Mesh(recessGeometry, recessMaterial);
            recess.position.x = pos.x;
            recess.position.y = pos.y;
            recess.position.z = thickness - recessDepth/2;
            recess.rotation.x = Math.PI / 2;
            scene.add(recess);
        });
        
        // Export to STL
        const mergedGeometry = this.mergeGeometries(scene);
        return this.exportSTL(mergedGeometry);
    }
    
    /**
     * Generate STL for a braille cylinder
     */
    generateCylinderSTL(lines, settings, cylinderParams) {
        const scene = new THREE.Scene();
        
        // Cylinder parameters
        const diameter = parseFloat(cylinderParams.diameter_mm) || 30.75;
        const height = parseFloat(cylinderParams.height_mm) || 52;
        const radius = diameter / 2;
        
        // Braille parameters - use the settings from the form
        const dotRadius = parseFloat(settings.emboss_dot_base_diameter) / 2 || 0.8;
        const dotHeight = parseFloat(settings.emboss_dot_height) || 0.5;
        const cellSpacing = parseFloat(settings.cell_spacing) || 6.5;
        const lineSpacing = parseFloat(settings.line_spacing) || 10;
        const marginTop = parseFloat(settings.braille_y_adjust) || 4;
        
        // Create cylinder
        const cylinderGeometry = new THREE.CylinderGeometry(radius, radius, height, 32);
        const cylinderMaterial = new THREE.MeshBasicMaterial({ color: 0xcccccc });
        const cylinder = new THREE.Mesh(cylinderGeometry, cylinderMaterial);
        scene.add(cylinder);
        
        // Add braille dots on cylinder surface
        lines.forEach((line, lineIndex) => {
            if (!line || line.trim() === '') return;
            
            const lineY = height/2 - marginTop - (lineIndex * lineSpacing);
            let angle = 0; // Start angle for text
            
            for (let i = 0; i < line.length; i++) {
                const char = line[i];
                if (this.isBrailleChar(char)) {
                    const dots = this.getBrailleDots(char);
                    
                    // Create dots for this character
                    dots.forEach(dotIndex => {
                        const [col, row] = this.brailleDotPositions[dotIndex];
                        
                        // Calculate position on cylinder surface
                        const dotAngle = angle + (col * 2.5 / radius); // Angular spacing
                        const dotY = lineY - row * 2.5;
                        
                        // Convert to cartesian coordinates
                        const dotX = (radius + dotHeight/2) * Math.cos(dotAngle);
                        const dotZ = (radius + dotHeight/2) * Math.sin(dotAngle);
                        
                        // Create dot
                        const dotGeometry = new THREE.SphereGeometry(dotRadius, 8, 8);
                        const dotMaterial = new THREE.MeshBasicMaterial({ color: 0x333333 });
                        const dot = new THREE.Mesh(dotGeometry, dotMaterial);
                        
                        dot.position.set(dotX, dotY, dotZ);
                        scene.add(dot);
                    });
                    
                    // Update angle for next character
                    angle += cellSpacing / radius;
                }
            }
        });
        
        // Export to STL
        const mergedGeometry = this.mergeGeometries(scene);
        return this.exportSTL(mergedGeometry);
    }
    
    /**
     * Check if a character is a braille character
     */
    isBrailleChar(char) {
        const code = char.charCodeAt(0);
        return code >= 0x2800 && code <= 0x28FF;
    }
    
    /**
     * Get which dots are raised for a braille character
     */
    getBrailleDots(char) {
        const code = char.charCodeAt(0) - 0x2800;
        const dots = [];
        
        for (let i = 0; i < 6; i++) {
            if (code & (1 << i)) {
                dots.push(i);
            }
        }
        
        return dots;
    }
    
    /**
     * Merge all geometries in the scene for better performance
     */
    mergeGeometries(scene) {
        const geometries = [];
        
        scene.traverse((child) => {
            if (child.isMesh) {
                child.updateMatrix();
                const geometry = child.geometry.clone();
                geometry.applyMatrix4(child.matrix);
                geometries.push(geometry);
            }
        });
        
        // Use BufferGeometryUtils to merge
        if (window.THREE && window.THREE.BufferGeometryUtils) {
            return window.THREE.BufferGeometryUtils.mergeGeometries(geometries);
        } else {
            // Fallback: return first geometry if merge utils not available
            console.warn('BufferGeometryUtils not available, returning unmerged geometry');
            return geometries[0] || new THREE.BoxGeometry(1, 1, 1);
        }
    }
    
    /**
     * Export geometry to STL string
     */
    exportSTL(geometry) {
        const exporter = new window.STLExporter();
        const stlString = exporter.parse(geometry);
        return stlString;
    }
    
    /**
     * Convert STL string to blob for download
     */
    stlToBlob(stlString) {
        return new Blob([stlString], { type: 'application/octet-stream' });
    }
}

// Export for use in other scripts
window.BrailleSTLGenerator = BrailleSTLGenerator;
