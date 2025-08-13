from flask import Flask, request, send_file, jsonify, render_template, send_from_directory
import trimesh
import numpy as np
import io
import os
import re
import json
from pathlib import Path
from flask_cors import CORS

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
    Create a negative plate with recessed holes for Vercel compatibility.
    This creates a plate with holes that can be used as a counter plate.
    """
    print(f"DEBUG: Starting negative plate creation with settings: {settings.__dict__}")
    
    # Create base plate
    base_plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base_plate.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))
    print(f"DEBUG: Created base plate with dimensions: {base_plate.bounds}")
    
    # Create recessed holes as cylinders
    recessed_holes = []
    
    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # If we have braille lines, create holes only where dots exist
    if lines and any(line.strip() for line in lines):
        print(f"DEBUG: Creating negative plate with braille content: {lines}")
        
        # Process each line in top-down order
        for row_num in range(settings.grid_rows):
            if row_num >= len(lines):
                break
                
            line_text = lines[row_num].strip()
            if not line_text:
                continue
                
            # Check if input contains proper braille Unicode (U+2800 to U+28FF)
            has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)
            
            if has_braille_chars:
                # Input is proper braille Unicode, use it directly
                braille_text = line_text
                print(f"DEBUG: Processing braille line '{braille_text}' for negative plate")
                
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
                    
                    # Create holes for each dot that exists
                    for i, dot_val in enumerate(dots):
                        if dot_val == 1:
                            dot_pos = dot_positions[i]
                            dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                            dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                            
                            # Create recessed hole (cylinder going down from top surface)
                            # Make the hole significantly larger than the dot to ensure proper boolean operation
                            hole_radius = (settings.dot_base_diameter / 2) + 0.5  # Increased tolerance to 0.5mm
                            hole_height = settings.card_thickness + 1.0  # Increased height to ensure complete penetration
                            
                            print(f"DEBUG: Creating hole with radius {hole_radius:.2f}mm, height {hole_height:.2f}mm")
                            
                            # Create a tall cylinder that definitely goes through the plate
                            recessed_hole = trimesh.creation.cylinder(
                                radius=hole_radius,
                                height=hole_height,
                                sections=32  # Increased sections for smoother holes
                            )
                            
                            # Position the hole to start above the plate and go completely through
                            # This ensures the hole definitely intersects with the plate
                            z_pos = settings.card_thickness + (hole_height / 2)
                            recessed_hole.apply_translation((dot_x, dot_y, z_pos))
                            recessed_holes.append(recessed_hole)
                            print(f"DEBUG: Created hole for dot {i+1} at ({dot_x:.2f}, {dot_y:.2f}, {z_pos:.2f})")
            else:
                print(f"WARNING: Line {row_num + 1} does not contain proper braille Unicode characters")
    else:
        print("DEBUG: No braille content provided, creating holes at all grid positions")
        # Create recessed holes for each grid position (fallback)
        for row in range(settings.grid_rows):
            for col in range(settings.grid_columns):
                # Calculate position
                x_pos = settings.left_margin + (col * settings.cell_spacing) + settings.braille_x_adjust
                y_pos = settings.card_height - settings.top_margin - (row * settings.line_spacing) + settings.braille_y_adjust
                
                # Create recessed hole (cylinder going down from top surface)
                hole_radius = (settings.dot_base_diameter / 2) + 0.5  # Increased tolerance
                hole_height = settings.card_thickness + 1.0  # Increased height
                
                recessed_hole = trimesh.creation.cylinder(
                    radius=hole_radius,
                    height=hole_height,
                    sections=32
                )
                
                # Position the hole to start above the plate and go completely through
                z_pos = settings.card_thickness + (hole_height / 2)
                recessed_hole.apply_translation((x_pos, y_pos, z_pos))
                recessed_holes.append(recessed_hole)
                print(f"DEBUG: Created fallback hole at ({x_pos:.2f}, {y_pos:.2f}, {z_pos:.2f})")
    
    print(f"DEBUG: Created {len(recessed_holes)} holes total")
    
    # Combine all recessed holes
    if recessed_holes:
        try:
            recessed_holes_combined = trimesh.util.concatenate(recessed_holes)
            print(f"DEBUG: Combined holes into single mesh with bounds: {recessed_holes_combined.bounds}")
            
            # Perform boolean difference to create actual holes
            print("DEBUG: Attempting boolean subtraction...")
            final_mesh = base_plate.difference(recessed_holes_combined)
            print(f"DEBUG: Boolean subtraction successful! Final mesh bounds: {final_mesh.bounds}")
            print(f"Successfully created negative plate with {len(recessed_holes)} holes")
            return final_mesh
            
        except Exception as e:
            print(f"ERROR: Boolean subtraction failed: {e}")
            print("DEBUG: Attempting alternative negative plate approach...")
            
            # Alternative approach: create a plate with holes by building it from scratch
            return create_alternative_negative_plate(settings)
    else:
        print("WARNING: No holes to create, returning base plate")
        return base_plate

def create_alternative_negative_plate(settings: CardSettings):
    """
    Alternative method to create negative plate when boolean operations fail.
    This creates a plate with holes by building it from individual components.
    """
    print("DEBUG: Using alternative negative plate creation method")
    
    # Create the base plate
    base_plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base_plate.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))
    
    # Create a large cylinder that covers the entire grid area
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_height = (settings.grid_rows - 1) * settings.line_spacing
    
    # Create a large hole that covers the entire braille area
    large_hole = trimesh.creation.cylinder(
        radius=max(grid_width, grid_height) / 2 + 2,  # Slightly larger than grid
        height=settings.card_thickness + 1.0,  # Increased height
        sections=32
    )
    
    # Position the large hole to start above the plate and go completely through
    center_x = settings.left_margin + (grid_width / 2)
    center_y = settings.card_height - settings.top_margin - (grid_height / 2)
    z_pos = settings.card_thickness + (large_hole.bounds[1][2] - large_hole.bounds[0][2]) / 2
    large_hole.apply_translation((center_x, center_y, z_pos))
    
    print(f"DEBUG: Alternative method - created large hole with radius {max(grid_width, grid_height) / 2 + 2:.2f}mm")
    print(f"DEBUG: Alternative method - hole positioned at ({center_x:.2f}, {center_y:.2f}, {z_pos:.2f})")
    
    try:
        # Try to subtract the large hole
        print("DEBUG: Alternative method - attempting boolean subtraction...")
        final_mesh = base_plate.difference(large_hole)
        print("DEBUG: Alternative method - boolean subtraction successful!")
        print("Successfully created negative plate with large hole")
        return final_mesh
    except Exception as e:
        print(f"ERROR: Alternative method also failed: {e}")
        # Last resort: return the base plate with a note
        print("WARNING: Returning base plate - holes could not be created")
        return base_plate

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment
app.debug = False
