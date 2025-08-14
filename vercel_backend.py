from flask import Flask, request, send_file, jsonify, render_template, send_from_directory
import trimesh
import numpy as np
import io
import os
import re
import json
from pathlib import Path
from flask_cors import CORS
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

app = Flask(__name__)
CORS(app)

# Add error handling for Vercel environment
@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    print(f"Error: {str(e)}")
    print(f"Traceback: {traceback.format_exc()}")
    return jsonify({'error': f'Server error: {str(e)}'}), 500

class CardSettings:
    def __init__(self, **kwargs):
        # Default values from OpenSCAD script
        defaults = {
            "card_width": 90,
            "card_height": 52,
            "card_thickness": 2.0,
            "grid_columns": 13,
            "grid_rows": 4,
            "cell_spacing": 7.0,
            "line_spacing": 12.0,
            "dot_spacing": 2.5,
            "dot_base_diameter": 2.0,
            "dot_hat_size": 0.8,
            "dot_height": 1.4,
            "braille_y_adjust": 0.4,
            "braille_x_adjust": 0.1,
            "negative_plate_offset": 0.4,
            # New parameters for hemispherical recesses
            "emboss_dot_base_diameter_mm": 2.0,
            "plate_thickness_mm": 2.0,
            "epsilon_mm": 0.001,
        }
        
        # Set attributes from kwargs or defaults, while being tolerant of "empty" inputs
        for key, default_val in defaults.items():
            raw_val = kwargs.get(key, None)

            # Treat None, empty string or string with only whitespace as "use default"
            if raw_val is None or (isinstance(raw_val, str) and raw_val.strip() == ""):
                val = default_val
            else:
                # Attempt to cast to float – this will still raise if an invalid value
                # is supplied, which is desirable as it surfaces bad input early.
                val = float(raw_val)

            setattr(self, key, val)
        
        # Ensure attributes that represent counts are integers
        self.grid_columns = int(self.grid_columns)
        self.grid_rows = int(self.grid_rows)
        
        # Calculated properties
        self.dot_top_diameter = self.dot_hat_size
        self.grid_width = (self.grid_columns - 1) * self.cell_spacing
        self.left_margin = (self.card_width - self.grid_width) / 2
        self.grid_height = (self.grid_rows - 1) * self.line_spacing
        self.top_margin = (self.card_height - self.grid_height) / 2
        
        # Recessed dot parameters (adjusted by offset)
        self.recessed_dot_base_diameter = self.dot_base_diameter + (self.negative_plate_offset * 2)
        self.recessed_dot_top_diameter = self.dot_hat_size + (self.negative_plate_offset * 2)
        self.recessed_dot_height = self.dot_height + self.negative_plate_offset
        
        # Counter plate specific parameters (can be adjusted independently)
        self.counter_plate_dot_base_diameter = self.dot_base_diameter + (self.negative_plate_offset * 2)
        self.counter_plate_dot_top_diameter = self.dot_hat_size + (self.negative_plate_offset * 2)
        self.counter_plate_dot_height = self.dot_height + self.negative_plate_offset
        
        # Hemispherical recess parameters
        self.hemisphere_radius = self.emboss_dot_base_diameter_mm / 2
        self.plate_thickness = self.plate_thickness_mm
        self.epsilon = self.epsilon_mm

def translate_with_liblouis_js(text: str, grade: str = "g2") -> str:
    """
    This function is not used since we expect the frontend to send proper braille Unicode.
    The frontend should use the liblouis web worker to translate text to braille Unicode.
    """
    raise RuntimeError("Direct translation not supported. Frontend must send proper braille Unicode characters.")

def convert_liblouis_output_to_unicode(liblouis_output: str, grade: str = "g2") -> str:
    """
    This function is not used since we expect the frontend to send proper braille Unicode.
    The frontend should use the liblouis web worker to translate text to braille Unicode.
    """
    raise RuntimeError("Liblouis output conversion not supported. Frontend must send proper braille Unicode characters.")

def braille_to_dots(braille_char: str) -> list:
    """
    Convert a braille character to dot pattern.
    Braille dots are arranged as:
    1 4
    2 5
    3 6
    """
    if not braille_char or braille_char == ' ':
        print(f"DEBUG: Empty/space character, returning [0,0,0,0,0,0]")
        return [0, 0, 0, 0, 0, 0]  # Empty cell
    
    # Check if it's in the braille Unicode block (U+2800 to U+28FF)
    code_point = ord(braille_char)
    print(f"DEBUG: Character '{braille_char}' has Unicode code point: {code_point} (0x{code_point:04X})")
    
    if code_point >= 0x2800 and code_point <= 0x28FF:
        # Extract the dot pattern (bits 0-7 for dots 1-8)
        dot_pattern = code_point - 0x2800
        print(f"DEBUG: Dot pattern value: {dot_pattern}")
        
        # Convert to 6-dot pattern (dots 1-6)
        dots = [0, 0, 0, 0, 0, 0]
        for i in range(6):
            if dot_pattern & (1 << i):
                dots[i] = 1
        
        print(f"DEBUG: Final dots array: {dots}")
        return dots
    else:
        print(f"DEBUG: Character '{braille_char}' is not in braille Unicode block, returning [0,0,0,0,0,0]")
        return [0, 0, 0, 0, 0, 0]

def create_braille_dot(x, y, z, settings: CardSettings):
    """
    Create a cone-shaped braille dot with specified dimensions from settings.
    """
    # Create a cylinder with the base diameter
    cylinder = trimesh.creation.cylinder(
        radius=settings.dot_base_diameter / 2,
        height=settings.dot_height,
        sections=16
    )
    
    # Scale the top vertices to create the cone shape (frustum)
    # This loop iterates through all vertices and scales the top ones.
    if settings.dot_base_diameter > 0:
        scale_factor = settings.dot_top_diameter / settings.dot_base_diameter
        
        # Apply scaling to vertices that are on the top surface of the cylinder
        top_surface_z = cylinder.vertices[:, 2].max()
        
        # A small tolerance for floating point comparison
        is_top_vertex = np.isclose(cylinder.vertices[:, 2], top_surface_z)
        
        cylinder.vertices[is_top_vertex, :2] *= scale_factor
        
    # Position the dot
    cylinder.apply_translation((x, y, z))
    return cylinder

def create_positive_plate_mesh(lines, grade="g1", settings=None):
    """
    Create a standard braille mesh (positive plate with raised dots).
    Lines are processed in top-down order.
    """
    if settings is None:
        settings = CardSettings()

    grade_name = f"Grade {grade.upper()}" if grade in ["g1", "g2"] else "Grade 1"
    print(f"Creating positive plate mesh with {grade_name} characters")
    print(f"Grid: {settings.grid_columns} columns × {settings.grid_rows} rows")
    print(f"Centering grid. Auto-calculated margins: Left/Right {settings.left_margin:.2f}mm, Top/Bottom {settings.top_margin:.2f}mm")
    print(f"Spacing: Cell-to-cell {settings.cell_spacing}mm, Line-to-line {settings.line_spacing}mm, Dot-to-dot {settings.dot_spacing}mm")
    
    # Create card base
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))
    
    meshes = [base]
    
    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]] # Map dot index (0-5) to [row, col]

    # Process each line in top-down order
    for row_num in range(settings.grid_rows):
        if row_num >= len(lines):
            break
            
        line_text = lines[row_num].strip()
        if not line_text:
            continue
            
        # Frontend must send proper braille Unicode characters
        # Check if input contains proper braille Unicode (U+2800 to U+28FF)
        has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)
        
        if has_braille_chars:
            # Input is proper braille Unicode, use it directly
            braille_text = line_text
            print(f"DEBUG: Input '{line_text}' is proper braille Unicode, using directly")
        else:
            # Input is not braille Unicode - this is an error
            error_msg = f"Line {row_num + 1} does not contain proper braille Unicode characters. Frontend must translate text to braille before sending."
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Check if braille text exceeds grid capacity
        if len(braille_text) > settings.grid_columns:
            print(f"Warning: Line {row_num + 1} exceeds {settings.grid_columns} braille cells by {len(braille_text) - settings.grid_columns} cells")
            braille_text = braille_text[:int(settings.grid_columns)]  # Truncate to fit
        
        # Calculate Y position for this row (top-down)
        y_pos = settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process each braille character in the line
        for col_num, braille_char in enumerate(braille_text):
            if col_num >= settings.grid_columns:
                break
                
            dots = braille_to_dots(braille_char)
            print(f"DEBUG: Braille char '{braille_char}' → dots {dots}")
            
            # Calculate X position for this column
            x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create dots for this cell
            dot_count = 0
            for i, dot_val in enumerate(dots):
                if dot_val == 1:
                    dot_pos = dot_positions[i]
                    dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                    dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                    z = settings.card_thickness + settings.dot_height / 2
                    
                    print(f"DEBUG: Creating dot {i+1} at ({dot_x:.2f}, {dot_y:.2f}, {z:.2f})")
                    dot_mesh = create_braille_dot(dot_x, dot_y, z, settings)
                    meshes.append(dot_mesh)
                    dot_count += 1
            
            print(f"DEBUG: Created {dot_count} dots for character '{braille_char}'")
    
    print(f"Created positive plate with {len(meshes)-1} cone-shaped dots")
    return trimesh.util.concatenate(meshes)

def create_simple_negative_plate(settings: CardSettings, lines=None):
    """
    Create a negative plate with recessed holes using 2D Shapely operations for Vercel compatibility.
    This creates a counter plate with holes that match the embossing plate dimensions and positioning.
    """
    print(f"DEBUG: Starting negative plate creation with Shapely approach")
    print(f"DEBUG: Settings: grid {settings.grid_columns}x{settings.grid_rows}, dot spacing: {settings.dot_spacing}")
    
    # Create base rectangle for the card
    base_polygon = Polygon([
        (0, 0),
        (settings.card_width, 0),
        (settings.card_width, settings.card_height),
        (0, settings.card_height)
    ])
    
    print(f"DEBUG: Base polygon area: {base_polygon.area:.2f}")
    
    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Create holes for the actual text content (not all possible positions)
    holes = []
    total_dots = 0
    
    # Calculate hole radius based on dot dimensions plus offset
    # Counter plate holes should be slightly larger than embossing dots for proper alignment
    hole_radius = (settings.recessed_dot_base_diameter / 2)
    
    # Add a small clearance factor to ensure holes are large enough
    clearance_factor = 0.1  # 0.1mm additional clearance
    hole_radius += clearance_factor
    
    print(f"DEBUG: Hole radius: {hole_radius:.2f}mm (base: {settings.recessed_dot_base_diameter/2:.2f}mm + clearance: {clearance_factor:.2f}mm)")
    print(f"DEBUG: Embossing dot radius: {settings.dot_base_diameter/2:.2f}mm")
    print(f"DEBUG: Hole-to-dot ratio: {hole_radius/(settings.dot_base_diameter/2):.2f}")
    
    # Ensure hole radius is reasonable (at least 0.5mm)
    if hole_radius < 0.5:
        print(f"WARNING: Hole radius {hole_radius:.2f}mm is very small, increasing to 0.5mm")
        hole_radius = 0.5
    
    # Process each line to create holes that match the embossing plate
    for row_num in range(settings.grid_rows):
        if lines and row_num < len(lines):
            line_text = lines[row_num].strip()
            if not line_text:
                continue
                
            # Check if input contains proper braille Unicode
            has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)
            if not has_braille_chars:
                print(f"WARNING: Line {row_num + 1} does not contain proper braille Unicode, skipping")
                continue
                
            # Calculate Y position for this row (same as embossing plate)
            y_pos = settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
            print(f"DEBUG: Row {row_num}: Y position = {settings.card_height} - {settings.top_margin} - ({row_num} * {settings.line_spacing}) + {settings.braille_y_adjust} = {y_pos:.2f}mm")
                
            # Process each braille character in the line
            for col_num, braille_char in enumerate(line_text):
                if col_num >= settings.grid_columns:
                    break
                        
                # Calculate X position for this column (same as embossing plate)
                x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust
                print(f"DEBUG: Cell[{row_num},{col_num}]: X position = {settings.left_margin} + ({col_num} * {settings.cell_spacing}) + {settings.braille_x_adjust} = {x_pos:.2f}mm")
                    
                # Create holes for the dots that are present in this braille character
                dots = braille_to_dots(braille_char)
                print(f"DEBUG: Creating holes for char '{braille_char}' → dots {dots} at cell[{row_num},{col_num}]")
                    
                for dot_idx, dot_val in enumerate(dots):
                    if dot_val == 1:  # Only create holes for dots that are present
                        dot_pos = dot_positions[dot_idx]
                        dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                        dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                        
                        print(f"DEBUG: Dot {dot_idx+1}: offset[{dot_pos[0]},{dot_pos[1]}] → ({dot_x:.2f}, {dot_y:.2f})")
                        
                        # Create circular hole with higher resolution
                        hole = Point(dot_x, dot_y).buffer(hole_radius, resolution=64)
                        holes.append(hole)
                        total_dots += 1
                        
                        print(f"DEBUG: Hole {total_dots} for dot {dot_idx+1} at ({dot_x:.2f}, {dot_y:.2f})")
    
    print(f"DEBUG: Created {total_dots} holes total for actual text content")
    
    if not holes:
        print("WARNING: No holes were created! Creating a plate with all possible holes as fallback")
        # Fallback: create holes for all possible positions
        return create_universal_counter_plate_fallback(settings)
    
    # Combine all holes into one multi-polygon
    try:
        print("DEBUG: Combining holes with unary_union...")
        all_holes = unary_union(holes)
        print(f"DEBUG: Combined holes area: {all_holes.area:.4f}")
        
        # Subtract holes from base to create the plate with holes
        print("DEBUG: Subtracting holes from base...")
        plate_with_holes = base_polygon.difference(all_holes)
        print(f"DEBUG: Plate with holes area: {plate_with_holes.area:.4f}")
        print(f"DEBUG: Area removed: {base_polygon.area - plate_with_holes.area:.4f}")
        
    except Exception as e:
        print(f"ERROR: Failed to combine holes or subtract from base: {e}")
        import traceback
        traceback.print_exc()
        return create_fallback_plate(settings)
    
    # Extrude the 2D shape to 3D
    try:
        # Handle both Polygon and MultiPolygon results
        if hasattr(plate_with_holes, 'geoms'):
            # It's a MultiPolygon - take the largest polygon (should be the main plate)
            largest_polygon = max(plate_with_holes.geoms, key=lambda p: p.area)
            final_mesh = trimesh.creation.extrude_polygon(largest_polygon, height=settings.card_thickness)
            print(f"DEBUG: MultiPolygon detected, using largest polygon with area {largest_polygon.area:.2f}")
        else:
            # It's a single Polygon
            final_mesh = trimesh.creation.extrude_polygon(plate_with_holes, height=settings.card_thickness)
        
        print(f"DEBUG: Successfully created counter plate with {total_dots} holes using Shapely")
        print(f"DEBUG: Final mesh bounds: {final_mesh.bounds}")
        print(f"DEBUG: Final mesh volume: {final_mesh.volume:.4f}")
        return final_mesh
    except Exception as e:
        print(f"ERROR: Failed to extrude polygon: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to simple base plate if extrusion fails
        return create_fallback_plate(settings)

def create_universal_counter_plate_fallback(settings: CardSettings):
    """Create a counter plate with all possible holes as fallback when text-based holes fail"""
    print("DEBUG: Creating universal counter plate fallback with all possible holes")
    
    # Create base rectangle for the card
    base_polygon = Polygon([
        (0, 0),
        (settings.card_width, 0),
        (settings.card_width, settings.card_height),
        (0, settings.card_height)
    ])
    
    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Create holes for ALL possible dot positions (312 holes total)
    holes = []
    total_dots = 0
    
    # Calculate hole radius
    hole_radius = max(0.5, (settings.recessed_dot_base_diameter / 2))
    
    # Generate holes for each grid position (all cells, all dots)
    for row in range(settings.grid_rows):
        # Calculate Y position for this row (same as embossing plate)
        y_pos = settings.card_height - settings.top_margin - (row * settings.line_spacing) + settings.braille_y_adjust
        
        for col in range(settings.grid_columns):
            # Calculate X position for this column (same as embossing plate)
            x_pos = settings.left_margin + (col * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create holes for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create circular hole
                hole = Point(dot_x, dot_y).buffer(hole_radius, resolution=64)
                holes.append(hole)
                total_dots += 1
    
    print(f"DEBUG: Fallback: Created {total_dots} holes total for all possible positions")
    
    # Combine and subtract holes
    try:
        all_holes = unary_union(holes)
        plate_with_holes = base_polygon.difference(all_holes)
        
        # Extrude to 3D
        if hasattr(plate_with_holes, 'geoms'):
            largest_polygon = max(plate_with_holes.geoms, key=lambda p: p.area)
            final_mesh = trimesh.creation.extrude_polygon(largest_polygon, height=settings.card_thickness)
        else:
            final_mesh = trimesh.creation.extrude_polygon(plate_with_holes, height=settings.card_thickness)
        
        print(f"DEBUG: Fallback counter plate created successfully")
        return final_mesh
        
    except Exception as e:
        print(f"ERROR: Fallback counter plate creation failed: {e}")
        return create_fallback_plate(settings)

def create_fallback_plate(settings: CardSettings):
    """Create a simple fallback plate when hole creation fails"""
    print("WARNING: Creating fallback plate without holes")
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))
    return base



def create_negative_plate_with_conical_holes(settings: CardSettings):
    """
    Create a negative plate with recessed conical holes using 3D boolean subtraction.
    This method is more geometrically accurate but may be slower.
    """
    print("DEBUG: Starting negative plate creation with conical holes (3D boolean subtraction)")

    # Create the base plate
    plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    plate.apply_translation((settings.card_width / 2, settings.card_height / 2, settings.card_thickness / 2))
    print(f"DEBUG: Base plate bounds: {plate.bounds}")

    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Create cone cutters for ALL possible dot positions
    cutters = []
    total_dots = 0

    # Recessed dot parameters
    recessed_base_radius = settings.recessed_dot_base_diameter / 2
    recessed_top_radius = settings.recessed_dot_top_diameter / 2
    recessed_height = settings.recessed_dot_height

    # Generate cones for each grid position
    for row in range(settings.grid_rows):
        mirrored_row = settings.grid_rows - 1 - row
        y_pos = settings.card_height - settings.top_margin - (mirrored_row * settings.line_spacing) + settings.braille_y_adjust

        for col in range(settings.grid_columns):
            mirrored_col = settings.grid_columns - 1 - col
            x_pos = settings.left_margin + (mirrored_col * settings.cell_spacing) + settings.braille_x_adjust

            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create a cone (frustum) cutter
                # We create it pointing up, then translate it
                cone_cutter = trimesh.creation.cylinder(
                    radius=recessed_base_radius,
                    height=recessed_height,
                    sections=16
                )

                # Scale top to create frustum
                if recessed_base_radius > 0:
                    scale_factor = recessed_top_radius / recessed_base_radius
                    top_surface_z = cone_cutter.vertices[:, 2].max()
                    is_top_vertex = np.isclose(cone_cutter.vertices[:, 2], top_surface_z)
                    cone_cutter.vertices[is_top_vertex, :2] *= scale_factor

                # Position the cutter to go through the plate
                # The cone should extend from below the plate (z < 0) to above it (z > card_thickness)
                # to ensure proper intersection for boolean subtraction
                z_pos = -settings.negative_plate_offset  # Start below the plate
                cone_cutter.apply_translation((dot_x, dot_y, z_pos))
                
                # Debug: Log first few cone positions to verify placement
                if total_dots < 5:
                    print(f"DEBUG: Cone {total_dots + 1} at ({dot_x:.2f}, {dot_y:.2f}, {z_pos:.2f}) - bounds: {cone_cutter.bounds}")
                
                cutters.append(cone_cutter)
                total_dots += 1

    print(f"DEBUG: Created {total_dots} conical cutters for boolean subtraction.")

    # Optimize boolean operations: union all cones first, then single difference
    if cutters:
        try:
            # First, union all the cone cutters together using manifold engine
            print(f"DEBUG: Unioning {len(cutters)} cone cutters...")
            if len(cutters) == 1:
                combined_cutters = cutters[0]
            else:
                combined_cutters = trimesh.boolean.union(cutters, engine='manifold')
            
            print("DEBUG: Cones unioned successfully. Performing plate subtraction...")
            
            # Then subtract the unified cones from the plate
            final_mesh = trimesh.boolean.difference([plate, combined_cutters], engine='manifold')
            print("DEBUG: Boolean subtraction successful using manifold engine.")
            print(f"DEBUG: Final mesh bounds: {final_mesh.bounds}")
            print(f"DEBUG: Final mesh volume: {final_mesh.volume:.4f} (original: {plate.volume:.4f})")
            return final_mesh
            
        except Exception as e:
            print(f"ERROR: Boolean operations with manifold failed: {e}")
            print("WARNING: Falling back to simple cylindrical holes.")
            # Fallback to the simple approach if manifold fails
            return create_simple_negative_plate(settings)
    else:
        print("WARNING: No cutters were generated. Returning base plate.")
        return plate


def create_universal_counter_plate(settings: CardSettings):
    """
    Create a universal counter plate with recessed conical holes for ALL possible dot positions.
    This function is completely independent of text input and generates a plate with 312 holes.
    
    The counter plate has its own parametric controls for:
    - Counter plate dot base diameter
    - Counter plate dot height  
    - Counter plate dot flat top diameter
    """
    print("DEBUG: Starting universal counter plate creation with conical holes")
    print(f"DEBUG: Grid: {settings.grid_columns}x{settings.grid_rows} = {settings.grid_columns * settings.grid_rows * 6} total holes")

    # Create the base plate
    plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    plate.apply_translation((settings.card_width / 2, settings.card_height / 2, settings.card_thickness / 2))
    print(f"DEBUG: Base plate bounds: {plate.bounds}")
    print(f"DEBUG: Base plate volume: {plate.volume:.4f}")

    # Dot positioning constants (same as emboss plate)
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Create cone cutters for ALL possible dot positions (312 total)
    cutters = []
    total_dots = 0

    # Counter plate specific parameters (can be adjusted independently)
    counter_dot_base_radius = settings.counter_plate_dot_base_diameter / 2
    counter_dot_top_radius = settings.counter_plate_dot_top_diameter / 2
    counter_dot_height = settings.counter_plate_dot_height

    print(f"DEBUG: Counter plate dot parameters:")
    print(f"DEBUG:   Base radius: {counter_dot_base_radius:.3f}mm")
    print(f"DEBUG:   Top radius: {counter_dot_top_radius:.3f}mm") 
    print(f"DEBUG:   Height: {counter_dot_height:.3f}mm")

    # Generate cones for each grid position
    for row in range(settings.grid_rows):
        # Mirror row for counter plate (row 0 -> row 3, row 1 -> row 2, etc.)
        mirrored_row = settings.grid_rows - 1 - row
        y_pos = settings.card_height - settings.top_margin - (mirrored_row * settings.line_spacing) + settings.braille_y_adjust

        for col in range(settings.grid_columns):
            # Mirror column for counter plate (col 0 -> col 12, col 1 -> col 11, etc.)
            mirrored_col = settings.grid_columns - 1 - col
            x_pos = settings.left_margin + (mirrored_col * settings.cell_spacing) + settings.braille_x_adjust

            # Create holes for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create a cone (frustum) cutter
                cone_cutter = trimesh.creation.cylinder(
                    radius=counter_dot_base_radius,
                    height=counter_dot_height,
                    sections=16
                )

                # Scale top to create frustum (cone shape)
                if counter_dot_base_radius > 0:
                    scale_factor = counter_dot_top_radius / counter_dot_base_radius
                    top_surface_z = cone_cutter.vertices[:, 2].max()
                    is_top_vertex = np.isclose(cone_cutter.vertices[:, 2], top_surface_z)
                    cone_cutter.vertices[is_top_vertex, :2] *= scale_factor

                # Position the cutter to ensure it goes completely through the plate
                # Start below the plate and extend above it
                z_pos = -counter_dot_height  # Start well below the plate
                cone_cutter.apply_translation((dot_x, dot_y, z_pos))
                
                # Debug: Log first few cone positions and bounds
                if total_dots < 5:
                    print(f"DEBUG: Cone {total_dots + 1} at ({dot_x:.2f}, {dot_y:.2f}, {z_pos:.2f})")
                    print(f"DEBUG:   Cone bounds: {cone_cutter.bounds}")
                    print(f"DEBUG:   Cone extends from Z={cone_cutter.bounds[0][2]:.3f} to Z={cone_cutter.bounds[1][2]:.3f}")
                
                cutters.append(cone_cutter)
                total_dots += 1

    print(f"DEBUG: Created {total_dots} conical cutters for boolean subtraction.")
    print(f"DEBUG: Expected total: {settings.grid_rows * settings.grid_columns * 6}")

    # Perform boolean operations
    if cutters:
        try:
            # First, union all the cone cutters together
            print(f"DEBUG: Unioning {len(cutters)} cone cutters...")
            if len(cutters) == 1:
                combined_cutters = cutters[0]
            else:
                combined_cutters = trimesh.boolean.union(cutters, engine='manifold')
            
            print("DEBUG: Cones unioned successfully.")
            print(f"DEBUG: Combined cutters bounds: {combined_cutters.bounds}")
            
            # Then subtract the unified cones from the plate
            print("DEBUG: Performing plate subtraction...")
            final_mesh = trimesh.boolean.difference([plate, combined_cutters], engine='manifold')
            
            print("DEBUG: Boolean subtraction successful using manifold engine.")
            print(f"DEBUG: Final mesh bounds: {final_mesh.bounds}")
            print(f"DEBUG: Final mesh volume: {final_mesh.volume:.4f} (original: {plate.volume:.4f})")
            print(f"DEBUG: Volume removed: {plate.volume - final_mesh.volume:.4f}")
            
            return final_mesh
            
        except Exception as e:
            print(f"ERROR: Boolean operations with manifold failed: {e}")
            print("WARNING: Falling back to simple cylindrical holes.")
            # Fallback to the simple approach if manifold fails
            return create_simple_negative_plate(settings)
    else:
        print("WARNING: No cutters were generated. Returning base plate.")
        return plate


def build_counter_plate_hemispheres(params: CardSettings) -> trimesh.Trimesh:
    """
    Create a counter plate with true hemispherical recesses using trimesh with Manifold backend.
    
    This function generates a full braille grid and creates hemispherical recesses at EVERY dot position,
    regardless of grade-2 translation. The hemisphere diameter exactly equals the Embossing Plate's
    "braille dot base diameter" parameter.
    
    Args:
        params: CardSettings object containing all layout and geometry parameters
        
    Returns:
        Trimesh object representing the counter plate with hemispherical recesses
        
    Technical details:
    - Plate thickness: TH (mm). Top surface is z=TH, bottom is z=0.
    - Hemisphere radius r = emboss_dot_base_diameter_mm / 2.
    - For each dot center (x, y) in the braille grid, creates an icosphere with radius r
      and translates its center to (x, y, TH + ε) so the lower hemisphere sits inside the slab
      and the equator coincides with the top surface.
    - Subtracts all spheres in one operation using trimesh.boolean.difference with engine='manifold'.
    - Generates dot centers from a full grid using the same layout parameters as the Embossing Plate.
    - Always places all 6 dots per cell (does not consult per-character translation).
    """
    print("DEBUG: Starting hemispherical counter plate creation with Manifold backend")
    print(f"DEBUG: Grid: {params.grid_columns}x{params.grid_rows} = {params.grid_columns * params.grid_rows * 6} total recesses")
    print(f"DEBUG: Hemisphere radius: {params.hemisphere_radius:.3f}mm")
    print(f"DEBUG: Plate thickness: {params.plate_thickness:.3f}mm")
    
    # Create the base plate as a box aligned to z=[0, TH], x=[0, W], y=[0, H]
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width/2, params.card_height/2, params.plate_thickness/2))
    
    print(f"DEBUG: Base plate bounds: {plate_mesh.bounds}")
    print(f"DEBUG: Base plate volume: {plate_mesh.volume:.4f}")
    
    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]
    
    # Create icospheres for ALL possible dot positions
    sphere_meshes = []
    total_spheres = 0
    
    # Generate spheres for each grid position
    for row in range(params.grid_rows):
        # Mirror row for counter plate (row 0 -> row 3, row 1 -> row 2, etc.)
        mirrored_row = params.grid_rows - 1 - row
        y_pos = params.card_height - params.top_margin - (mirrored_row * params.line_spacing) + params.braille_y_adjust
        
        for col in range(params.grid_columns):
            # Mirror column for counter plate (col 0 -> col 12, col 1 -> col 11, etc.)
            mirrored_col = params.grid_columns - 1 - col
            x_pos = params.left_margin + (mirrored_col * params.cell_spacing) + params.braille_x_adjust
            
            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create an icosphere with radius = emboss_dot_base_diameter_mm / 2
                # Use subdivisions=1 or 2 to keep triangle count low
                sphere = trimesh.creation.icosphere(subdivisions=1, radius=params.hemisphere_radius)
                
                # Position the sphere center at z = TH + ε so the lower hemisphere sits inside the slab
                # and the equator coincides with the top surface
                z_pos = params.plate_thickness + params.epsilon
                sphere.apply_translation((dot_x, dot_y, z_pos))
                
                # Debug: Log first few sphere positions
                if total_spheres < 5:
                    print(f"DEBUG: Sphere {total_spheres + 1} at ({dot_x:.2f}, {dot_y:.2f}, {z_pos:.3f})")
                    print(f"DEBUG:   Sphere bounds: {sphere.bounds}")
                    print(f"DEBUG:   Sphere extends from Z={sphere.bounds[0][2]:.3f} to Z={sphere.bounds[1][2]:.3f}")
                
                sphere_meshes.append(sphere)
                total_spheres += 1
    
    print(f"DEBUG: Created {total_spheres} icospheres for hemispherical recesses")
    print(f"DEBUG: Expected total: {params.grid_rows * params.grid_columns * 6}")
    
    if not sphere_meshes:
        print("WARNING: No spheres were generated. Returning base plate.")
        return plate_mesh
    
    # Perform boolean operations using Manifold backend
    try:
        # Union all spheres together (optional; Manifold can take a list)
        print(f"DEBUG: Unioning {len(sphere_meshes)} spheres...")
        if len(sphere_meshes) == 1:
            union_spheres = sphere_meshes[0]
        else:
            union_spheres = trimesh.boolean.union(sphere_meshes, engine='manifold')
        
        print("DEBUG: Spheres unioned successfully.")
        print(f"DEBUG: Combined spheres bounds: {union_spheres.bounds}")
        
        # Subtract the unified spheres from the plate in one operation
        print("DEBUG: Performing plate subtraction with Manifold...")
        counter_plate_mesh = trimesh.boolean.difference([plate_mesh, union_spheres], engine='manifold')
        
        print("DEBUG: Boolean subtraction successful using Manifold engine.")
        print(f"DEBUG: Final mesh bounds: {counter_plate_mesh.bounds}")
        print(f"DEBUG: Final mesh volume: {counter_plate_mesh.volume:.4f} (original: {plate_mesh.volume:.4f})")
        print(f"DEBUG: Volume removed: {plate_mesh.volume - counter_plate_mesh.volume:.4f}")
        
        # Verify the mesh is watertight
        if counter_plate_mesh.is_watertight:
            print("DEBUG: Final mesh is watertight ✓")
        else:
            print("WARNING: Final mesh is not watertight!")
        
        return counter_plate_mesh
        
    except Exception as e:
        print(f"ERROR: Boolean operations with Manifold failed: {e}")
        print("WARNING: Falling back to simple negative plate method.")
        # Fallback to the simple approach if Manifold fails
        return create_simple_negative_plate(params)


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Vercel backend is running'})

@app.route('/test-liblouis-files')
def test_liblouis_files():
    """Test endpoint to verify liblouis files are accessible"""
    import os
    
    files_to_check = [
        # Frontend liblouis files (web worker)
        'static/liblouis/build-no-tables-utf16.js',
        'static/liblouis/easy-api.js',
        'static/liblouis/tables/en-ueb-g1.ctb',
        'static/liblouis/tables/en-ueb-g2.ctb',
        'static/liblouis/tables/unicode.dis',
        'static/liblouis/tables/chardefs.cti',
        'static/liblouis/tables/braille-patterns.cti',
        'static/liblouis/tables/litdigits6Dots.uti',
        'static/liblouis-worker.js',
        # Backend no longer needs liblouis files - expects Unicode from frontend
    ]
    
    results = {}
    for file_path in files_to_check:
        try:
            exists = os.path.exists(file_path)
            if exists:
                size = os.path.getsize(file_path)
                results[file_path] = {'exists': True, 'size': size}
            else:
                results[file_path] = {'exists': False, 'size': 0}
        except Exception as e:
            results[file_path] = {'exists': False, 'error': str(e)}
    
    return jsonify({
        'status': 'file_check_complete',
        'files': results,
        'working_directory': os.getcwd(),
        'directory_contents': os.listdir('.')
    })

@app.route('/test-boolean-operation')
def test_boolean_operation():
    """Test endpoint to verify boolean operations work correctly"""
    try:
        # Create a simple test case
        base = trimesh.creation.box(extents=(10, 10, 2))
        base.apply_translation((5, 5, 1))
        
        # Create a test hole
        hole = trimesh.creation.cylinder(radius=1, height=3, sections=16)
        hole.apply_translation((5, 5, 0))
        
        # Try boolean subtraction
        result = base.difference(hole)
        
        return jsonify({
            'status': 'success',
            'message': 'Boolean operation test passed',
            'base_bounds': base.bounds.tolist(),
            'base_volume': float(base.volume),
            'hole_volume': float(hole.volume),
            'result_volume': float(result.volume)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Boolean operation test failed: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/test-manifold-cone-operations')
def test_manifold_cone_operations():
    """Test endpoint to verify manifold engine works with cone-shaped boolean operations"""
    try:
        # Create a test card base
        base = trimesh.creation.box(extents=(20, 20, 2))
        base.apply_translation((10, 10, 1))
        
        # Create a test cone similar to what we use for braille dots
        cone = trimesh.creation.cylinder(radius=1.0, height=1.5, sections=16)
        
        # Scale top to create frustum (cone shape)
        scale_factor = 0.4  # Top radius smaller than base
        top_surface_z = cone.vertices[:, 2].max()
        is_top_vertex = np.isclose(cone.vertices[:, 2], top_surface_z)
        cone.vertices[is_top_vertex, :2] *= scale_factor
        
        # Position the cone
        cone.apply_translation((10, 10, 0.75))
        
        # Test manifold engine specifically
        try:
            result_manifold = base.difference(cone, engine='manifold')
            manifold_success = True
            manifold_volume = float(result_manifold.volume)
            manifold_error = None
        except Exception as e:
            manifold_success = False
            manifold_volume = None
            manifold_error = str(e)
        
        # Test default engine for comparison
        try:
            result_default = base.difference(cone)
            default_success = True
            default_volume = float(result_default.volume)
            default_error = None
        except Exception as e:
            default_success = False
            default_volume = None
            default_error = str(e)
        
        return jsonify({
            'status': 'success',
            'message': 'Manifold cone operation test completed',
            'base_volume': float(base.volume),
            'cone_volume': float(cone.volume),
            'manifold': {
                'success': manifold_success,
                'volume': manifold_volume,
                'error': manifold_error
            },
            'default': {
                'success': default_success,
                'volume': default_volume,
                'error': default_error
            },
            'engines_available': ['manifold' if manifold_success else 'manifold_failed', 'default' if default_success else 'default_failed']
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Manifold cone operation test failed: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/test-cone-positioning')
def test_cone_positioning():
    """Test endpoint to verify cone positioning and intersection with plate"""
    try:
        # Use the same settings as the main application
        settings = CardSettings()
        
        # Create a test plate (smaller for testing)
        plate = trimesh.creation.box(extents=(30, 20, 2))
        plate.apply_translation((15, 10, 1))
        print(f"DEBUG: Test plate bounds: {plate.bounds}")
        
        # Create a few test cones with the same logic as the main function
        cutters = []
        recessed_base_radius = settings.recessed_dot_base_diameter / 2
        recessed_top_radius = settings.recessed_dot_top_diameter / 2
        recessed_height = settings.recessed_dot_height
        
        # Create cones at specific test positions
        test_positions = [(15, 10), (20, 15), (10, 5)]  # Center and corners
        
        for i, (x, y) in enumerate(test_positions):
            cone = trimesh.creation.cylinder(
                radius=recessed_base_radius,
                height=recessed_height,
                sections=16
            )
            
            # Scale top to create frustum
            if recessed_base_radius > 0:
                scale_factor = recessed_top_radius / recessed_base_radius
                top_surface_z = cone.vertices[:, 2].max()
                is_top_vertex = np.isclose(cone.vertices[:, 2], top_surface_z)
                cone.vertices[is_top_vertex, :2] *= scale_factor
            
            # Position the cone to intersect the plate
            z_pos = -settings.negative_plate_offset
            cone.apply_translation((x, y, z_pos))
            
            print(f"DEBUG: Test cone {i+1} at ({x}, {y}, {z_pos}) - bounds: {cone.bounds}")
            cutters.append(cone)
        
        # Test boolean operation
        if len(cutters) == 1:
            combined_cutters = cutters[0]
        else:
            combined_cutters = trimesh.boolean.union(cutters, engine='manifold')
        
        print(f"DEBUG: Combined cutters bounds: {combined_cutters.bounds}")
        
        # Perform subtraction
        result = trimesh.boolean.difference([plate, combined_cutters], engine='manifold')
        print(f"DEBUG: Result bounds: {result.bounds}")
        print(f"DEBUG: Result volume: {result.volume:.4f} (original: {plate.volume:.4f})")
        
        return jsonify({
            'status': 'success',
            'message': 'Cone positioning test completed',
            'plate_bounds': plate.bounds.tolist(),
            'plate_volume': float(plate.volume),
            'cone_count': len(cutters),
            'combined_cutters_bounds': combined_cutters.bounds.tolist(),
            'result_bounds': result.bounds.tolist(),
            'result_volume': float(result.volume),
            'volume_difference': float(plate.volume - result.volume)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Cone positioning test failed: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/test-universal-counter-plate')
def test_universal_counter_plate():
    """Test endpoint to verify universal counter plate generation"""
    try:
        # Use the same settings as the main application
        settings = CardSettings()
        
        print("DEBUG: Testing universal counter plate generation...")
        mesh = create_universal_counter_plate(settings)
        
        return jsonify({
            'status': 'success',
            'message': 'Universal counter plate test completed',
            'mesh_bounds': mesh.bounds.tolist(),
            'mesh_volume': float(mesh.volume),
            'expected_holes': settings.grid_rows * settings.grid_columns * 6,
            'settings': {
                'card_width': settings.card_width,
                'card_height': settings.card_height,
                'card_thickness': settings.card_thickness,
                'grid_columns': settings.grid_columns,
                'grid_rows': settings.grid_rows,
                'dot_base_diameter': settings.dot_base_diameter,
                'dot_height': settings.dot_height,
                'dot_hat_size': settings.dot_hat_size,
                'negative_plate_offset': settings.negative_plate_offset
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Universal counter plate test failed: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/test-simple-counter-plate')
def test_simple_counter_plate():
    """Test endpoint to verify simple counter plate generation with just a few holes"""
    try:
        # Use the same settings as the main application for consistency
        settings = CardSettings()
        
        print("DEBUG: Testing simple counter plate with main application settings")
        print(f"DEBUG: Grid: {settings.grid_columns}x{settings.grid_rows}")
        print(f"DEBUG: Card dimensions: {settings.card_width}x{settings.card_height}x{settings.card_thickness}mm")
        print(f"DEBUG: Dot spacing: {settings.dot_spacing}mm, Line spacing: {settings.line_spacing}mm")
        
        # Create a test counter plate with the same settings as the main app
        mesh = create_simple_negative_plate(settings)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name='test_counter_plate.stl')
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Simple counter plate test failed: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/test-text-counter-plate')
def test_text_counter_plate():
    """Test endpoint to verify counter plate generation with actual text content"""
    try:
        # Use the same settings as the main application
        settings = CardSettings()
        
        # Create test text lines with braille Unicode
        test_lines = [
            "⠠⠃⠗⠢⠝⠢",  # "Brennen" in braille
            "⠠⠚⠕⠓⠝⠌⠕⠝",  # "Johnston" in braille
            "",  # Empty line
            ""   # Empty line
        ]
        
        print("DEBUG: Testing text-based counter plate generation")
        print(f"DEBUG: Test text: {test_lines}")
        print(f"DEBUG: Grid: {settings.grid_columns}x{settings.grid_rows}")
        
        # Create a counter plate based on the actual text content
        mesh = create_simple_negative_plate(settings, test_lines)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name='test_text_counter_plate.stl')
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Text counter plate test failed: {str(e)}',
            'error': str(e)
        }), 500


@app.route('/test-hemispherical-counter-plate')
def test_hemispherical_counter_plate():
    """Test endpoint to verify hemispherical counter plate generation with Manifold backend"""
    try:
        # Use the same settings as the main application
        settings = CardSettings()
        
        print("DEBUG: Testing hemispherical counter plate generation with Manifold backend...")
        print(f"DEBUG: Grid: {settings.grid_columns}x{settings.grid_rows} = {settings.grid_columns * settings.grid_rows * 6} total recesses")
        print(f"DEBUG: Hemisphere radius: {settings.hemisphere_radius:.3f}mm")
        print(f"DEBUG: Plate thickness: {settings.plate_thickness:.3f}mm")
        
        # Create the hemispherical counter plate
        mesh = build_counter_plate_hemispheres(settings)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name='test_hemispherical_counter_plate.stl')
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Hemispherical counter plate test failed: {str(e)}',
            'error': str(e)
        }), 500


@app.route('/test-hemispherical-counter-plate-info')
def test_hemispherical_counter_plate_info():
    """Test endpoint to verify hemispherical counter plate properties without downloading"""
    try:
        # Use the same settings as the main application
        settings = CardSettings()
        
        print("DEBUG: Testing hemispherical counter plate generation with Manifold backend...")
        print(f"DEBUG: Grid: {settings.grid_columns}x{settings.grid_rows} = {settings.grid_columns * settings.grid_rows * 6} total recesses")
        print(f"DEBUG: Hemisphere radius: {settings.hemisphere_radius:.3f}mm")
        print(f"DEBUG: Plate thickness: {settings.plate_thickness:.3f}mm")
        
        # Create the hemispherical counter plate
        mesh = build_counter_plate_hemispheres(settings)
        
        # Analyze the mesh to verify it has the expected properties
        expected_recesses = settings.grid_rows * settings.grid_columns * 6
        expected_volume_removed = expected_recesses * (4/3 * np.pi * settings.hemisphere_radius**3) / 2  # Half sphere volume
        
        return jsonify({
            'status': 'success',
            'message': 'Hemispherical counter plate test completed',
            'mesh_properties': {
                'bounds': mesh.bounds.tolist(),
                'volume': float(mesh.volume),
                'is_watertight': bool(mesh.is_watertight),
                'vertex_count': len(mesh.vertices),
                'face_count': len(mesh.faces)
            },
            'expected_properties': {
                'total_recesses': expected_recesses,
                'hemisphere_radius_mm': float(settings.hemisphere_radius),
                'plate_thickness_mm': float(settings.plate_thickness),
                'expected_volume_removed': float(expected_volume_removed)
            },
            'settings': {
                'card_width': settings.card_width,
                'card_height': settings.card_height,
                'grid_columns': settings.grid_columns,
                'grid_rows': settings.grid_rows,
                'emboss_dot_base_diameter_mm': settings.emboss_dot_base_diameter_mm,
                'plate_thickness_mm': settings.plate_thickness_mm,
                'epsilon_mm': settings.epsilon_mm
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Hemispherical counter plate test failed: {str(e)}',
            'error': str(e)
        }), 500


@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return jsonify({'error': 'Failed to load template'}), 500

@app.route('/node_modules/<path:filename>')
def node_modules(filename):
    return send_from_directory('node_modules', filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    try:
        print(f"DEBUG: Static file request for: {filename}")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        print(f"DEBUG: Static directory exists: {os.path.exists('static')}")
        print(f"DEBUG: Full path exists: {os.path.exists(os.path.join('static', filename))}")
        
        if not os.path.exists('static'):
            print(f"ERROR: Static directory not found")
            return jsonify({'error': 'Static directory not found'}), 500
            
        if not os.path.exists(os.path.join('static', filename)):
            print(f"ERROR: File {filename} not found in static directory")
            return jsonify({'error': f'File {filename} not found'}), 404
            
        print(f"DEBUG: Serving file: {filename}")
        return send_from_directory('static', filename)
    except Exception as e:
        print(f"ERROR: Failed to serve static file {filename}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to serve file: {str(e)}'}), 500

@app.route('/generate_braille_stl', methods=['POST'])
def generate_braille_stl():
    data = request.get_json()
    lines = data.get('lines', ['', '', '', ''])
    plate_type = data.get('plate_type', 'positive')
    grade = data.get('grade', 'g2')
    settings_data = data.get('settings', {})
    
    # Validate input
    if not isinstance(lines, list) or len(lines) != 4:
        return jsonify({'error': 'Invalid input: must provide exactly 4 lines'}), 400
    
    settings = CardSettings(**settings_data)
    
    # Check for empty input
    if all(not line.strip() for line in lines):
        return jsonify({'error': 'Please enter text in at least one line'}), 400
    
    # Character limit validation is now done on frontend after braille translation
    # Backend expects lines to already be within limits
    
    try:
        if plate_type == 'positive':
            mesh = create_positive_plate_mesh(lines, grade, settings)
        elif plate_type == 'negative':
            # Use the simple 2D approach instead of complex 3D boolean operations
            # This is more reliable on Vercel and still creates proper holes
            print("DEBUG: Using simple negative plate method for better Vercel compatibility")
            mesh = create_simple_negative_plate(settings, lines)
        else:
            return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Create filename from first non-empty line
        filename = 'braille_card'
        for line in lines:
            if line.strip():
                # Sanitize filename: remove special characters and limit length
                sanitized = re.sub(r'[^\w\s-]', '', line.strip()[:20])
                sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
                if sanitized:
                    filename = sanitized
                break
        
        # Add plate type to filename
        plate_suffix = 'counter_plate' if plate_type == 'negative' else 'braille'
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=f'{filename}_{plate_suffix}.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate STL: {str(e)}'}), 500

@app.route('/generate_counter_plate_stl', methods=['POST'])
def generate_counter_plate_stl():
    """
    Counter plate generation with simplified approach for Vercel.
    """
    data = request.get_json()
    lines = data.get('lines', ['', '', '', ''])
    settings_data = data.get('settings', {})
    settings = CardSettings(**settings_data)
    
    try:
        mesh = create_simple_negative_plate(settings, lines)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name='counter_plate.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate counter plate: {str(e)}'}), 500

@app.route('/generate_universal_counter_plate', methods=['POST'])
def generate_universal_counter_plate_route():
    """
    Generate a universal counter plate with recessed conical holes for ALL possible dot positions.
    This endpoint does NOT require any text input - it generates a plate with 312 holes.
    """
    data = request.get_json()
    settings_data = data.get('settings', {})
    settings = CardSettings(**settings_data)
    
    try:
        print("DEBUG: Generating universal counter plate (no text input required)")
        mesh = create_universal_counter_plate(settings)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name='universal_counter_plate.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate universal counter plate: {str(e)}'}), 500


@app.route('/generate_hemispherical_counter_plate', methods=['POST'])
def generate_hemispherical_counter_plate_route():
    """
    Generate a counter plate with true hemispherical recesses using trimesh with Manifold backend.
    
    This endpoint creates a plate with hemispherical recesses at EVERY dot position in the braille grid,
    regardless of text content. The hemisphere diameter exactly equals the Embossing Plate's
    "braille dot base diameter" parameter.
    
    The counter plate has its own parametric controls for:
    - emboss_dot_base_diameter_mm (drives hemisphere radius)
    - plate_thickness_mm (TH)
    - All layout parameters (num_lines, cells_per_line, spacing, margins, offsets)
    """
    data = request.get_json()
    settings_data = data.get('settings', {})
    settings = CardSettings(**settings_data)
    
    try:
        print("DEBUG: Generating hemispherical counter plate with Manifold backend")
        print(f"DEBUG: Grid: {settings.grid_columns}x{settings.grid_rows} = {settings.grid_columns * settings.grid_rows * 6} total recesses")
        print(f"DEBUG: Hemisphere radius: {settings.hemisphere_radius:.3f}mm")
        print(f"DEBUG: Plate thickness: {settings.plate_thickness:.3f}mm")
        
        # Create the hemispherical counter plate
        mesh = build_counter_plate_hemispheres(settings)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name='hemispherical_counter_plate.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate hemispherical counter plate: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment
app.debug = False
