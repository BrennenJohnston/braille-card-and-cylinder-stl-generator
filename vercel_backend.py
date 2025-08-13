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
    This creates a counter plate with holes for ALL possible dot positions (312 holes total).
    The plate mirrors the embossing plate positions.
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
    
    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Create holes for ALL possible dot positions (counter plate needs all 312 holes)
    holes = []
    total_dots = 0
    
    # Calculate hole radius based on dot dimensions plus offset
    hole_radius = (settings.recessed_dot_base_diameter / 2)
    print(f"DEBUG: Hole radius: {hole_radius:.2f}mm (based on recessed_dot_base_diameter: {settings.recessed_dot_base_diameter:.2f}mm)")
    
    # Generate holes for each grid position (all cells, all dots)
    for row in range(settings.grid_rows):
        # Calculate Y position for this row (top-down, but mirrored for counter plate)
        # For counter plate: Row 0 on embossing plate -> Row 3 on counter plate
        mirrored_row = settings.grid_rows - 1 - row
        y_pos = settings.card_height - settings.top_margin - (mirrored_row * settings.line_spacing) + settings.braille_y_adjust
        
        for col in range(settings.grid_columns):
            # Calculate X position for this column (mirrored for counter plate)
            # For counter plate: Col 0 on embossing plate -> Col 12 on counter plate
            mirrored_col = settings.grid_columns - 1 - col
            x_pos = settings.left_margin + (mirrored_col * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create holes for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create circular hole
                hole = Point(dot_x, dot_y).buffer(hole_radius, resolution=32)
                holes.append(hole)
                total_dots += 1
                
                if total_dots <= 10 or total_dots % 50 == 0:  # Log first 10 and every 50th
                    print(f"DEBUG: Hole {total_dots} at cell[{row},{col}] dot {dot_idx+1} -> mirrored cell[{mirrored_row},{mirrored_col}] at ({dot_x:.2f}, {dot_y:.2f})")
    
    print(f"DEBUG: Created {total_dots} holes total (expected: {settings.grid_rows * settings.grid_columns * 6})")
    
    # Combine all holes into one multi-polygon
    all_holes = unary_union(holes)
    
    # Subtract holes from base to create the plate with holes
    plate_with_holes = base_polygon.difference(all_holes)
    
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
        return final_mesh
    except Exception as e:
        print(f"ERROR: Failed to extrude polygon: {e}")
        # Fallback to simple base plate if extrusion fails
        print("WARNING: Returning base plate without holes")
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
                z_pos = (recessed_height / 2) - settings.negative_plate_offset
                cone_cutter.apply_translation((dot_x, dot_y, z_pos))
                
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
            return final_mesh
            
        except Exception as e:
            print(f"ERROR: Boolean operations with manifold failed: {e}")
            print("WARNING: Falling back to simple cylindrical holes.")
            # Fallback to the simple approach if manifold fails
            return create_simple_negative_plate(settings)
    else:
        print("WARNING: No cutters were generated. Returning base plate.")
        return plate


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
    return send_from_directory('static', filename)

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
            mesh = create_negative_plate_with_conical_holes(settings)
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment
app.debug = False
