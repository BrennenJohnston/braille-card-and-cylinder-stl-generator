from flask import Flask, request, send_file, jsonify, render_template, send_from_directory
import trimesh
import numpy as np
import io
import os
import subprocess
import re
import platform
from pathlib import Path
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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

# Liblouis integration
LIB = Path(__file__).parent / "third_party" / "liblouis"

# Cross-platform executable name
if platform.system() == "Windows":
    LOU = str(LIB / "bin" / "lou_translate.exe")
else:
    LOU = str(LIB / "bin" / "lou_translate")

# Liblouis table mapping
TABLES = {"g1": "en-ueb-g1.ctb", "g2": "en-ueb-g2.ctb"}

def translate_with_liblouis(text: str, grade: str = "g2") -> str:
    """
    Translate text to UEB braille using liblouis.
    
    Args:
        text: Input text to translate
        grade: "g1" for Grade 1 (uncontracted) or "g2" for Grade 2 (contracted)
    """

    table = TABLES.get(grade, "en-ueb-g2.ctb")
    env = os.environ.copy()
    env["LOUIS_TABLEPATH"] = str(LIB / "tables")
    args = [LOU, "--forward", f"unicode.dis,{table}"]
    
    try:
        p = subprocess.run(args, input=text.encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        if p.returncode != 0:
            raise RuntimeError(f"Liblouis translation failed: {p.stderr.decode('utf-8', 'ignore')}")
        return p.stdout.decode("utf-8").strip()
    except Exception as e:
        raise RuntimeError(f"Failed to translate text: {str(e)}")

def braille_to_dots(braille_char: str) -> list:
    """
    Convert a braille character to dot pattern.
    Braille dots are arranged as:
    1 4
    2 5
    3 6
    """
    # Braille Unicode block starts at U+2800
    # Each braille character is represented by 8 bits (dots 1-8)
    if not braille_char or braille_char == ' ':
        return [0, 0, 0, 0, 0, 0]  # Empty cell
    
    # Get the Unicode code point
    code_point = ord(braille_char)
    
    # Check if it's in the braille Unicode block (U+2800 to U+28FF)
    if code_point < 0x2800 or code_point > 0x28FF:
        return [0, 0, 0, 0, 0, 0]  # Not a braille character
    
    # Extract the dot pattern (bits 0-7 for dots 1-8)
    # The bit order is dot 1, 2, 3, 4, 5, 6, 7, 8
    dot_pattern = code_point - 0x2800
    
    # Convert to 6-dot pattern (dots 1-6)
    dots = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        if dot_pattern & (1 << i):
            dots[i] = 1
    
    return dots

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

def create_recessed_dot(x, y, z, settings: CardSettings):
    """
    Create a cone-shaped recessed dot (inverted cone) with specified dimensions from settings.
    This creates a cone that starts wide at the surface and narrows as it goes deeper.
    """
    # Create a cylinder with the base diameter (surface opening)
    cylinder = trimesh.creation.cylinder(
        radius=settings.recessed_dot_base_diameter / 2,
        height=settings.recessed_dot_height,
        sections=16
    )
    
    # Scale the bottom vertices to create the cone shape (frustum)
    # This creates a cone that narrows toward the bottom (deeper into the card)
    if settings.recessed_dot_base_diameter > 0:
        scale_factor = settings.recessed_dot_top_diameter / settings.recessed_dot_base_diameter
        
        # Apply scaling to vertices that are on the bottom surface of the cylinder
        bottom_surface_z = cylinder.vertices[:, 2].min()
        
        # A small tolerance for floating point comparison
        is_bottom_vertex = np.isclose(cylinder.vertices[:, 2], bottom_surface_z)
        
        cylinder.vertices[is_bottom_vertex, :2] *= scale_factor
        
    # Position the dot and flip it upside down (negative Z direction)
    cylinder.apply_translation((x, y, z))
    # Rotate 180 degrees around X axis to flip upside down
    rotation_matrix = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    cylinder.apply_transform(rotation_matrix)
    
    return cylinder

def create_positive_plate_mesh(lines, grade="g1", settings=None):
    """
    Create a standard braille mesh (positive plate with raised dots).
    Lines are processed in top-down order.
    
    Args:
        lines: List of 4 text lines
        grade: "g1" for Grade 1 or "g2" for Grade 2
        settings: A CardSettings object with all dimensional parameters.
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
            
        # Translate English text to braille using liblouis
        try:
            braille_text = translate_with_liblouis(line_text, grade)
            print(f"Line {row_num + 1}: '{line_text}' → '{braille_text}'")
        except Exception as e:
            print(f"Warning: Failed to translate line {row_num + 1}, using original text: {e}")
            braille_text = line_text
        
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
            
            # Calculate X position for this column
            x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create dots for this cell
            for i, dot_val in enumerate(dots):
                if dot_val == 1:
                    dot_pos = dot_positions[i]
                    dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                    dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                    z = settings.card_thickness + settings.dot_height / 2
                    
                    dot_mesh = create_braille_dot(dot_x, dot_y, z, settings)
                    meshes.append(dot_mesh)
    
    print(f"Created positive plate with {len(meshes)-1} cone-shaped dots")
    return trimesh.util.concatenate(meshes)

def create_negative_plate_mesh(settings=None):
    """
    Create a universal counter plate with recessed dots using boolean operations.
    We create a base plate and subtract cone-shaped recessed dots from it.
    """
    if settings is None:
        settings = CardSettings()

    try:
        import shapely.geometry as sg
        from shapely.ops import unary_union
        import mapbox_earcut  # noqa: F401 ensure triangulation backend is available
    except ImportError as e:
        raise RuntimeError("Shapely and mapbox-earcut are required. Install with `pip install shapely mapbox-earcut`.") from e

    # Create the base plate
    base_plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base_plate.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))

    # Generate cone-shaped recessed dots for every possible dot position
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    recessed_dots = []
    for row in range(settings.grid_rows):
        for col in range(settings.grid_columns):
            y_pos = settings.card_height - settings.top_margin - (row * settings.line_spacing) + settings.braille_y_adjust
            x_pos = settings.left_margin + (col * settings.cell_spacing) + settings.braille_x_adjust
            for pos in dot_positions:
                dot_x = x_pos + dot_col_offsets[pos[1]]
                dot_y = y_pos + dot_row_offsets[pos[0]]
                # Position the recessed dot at the surface of the card
                z = settings.card_thickness
                
                recessed_dot = create_recessed_dot(dot_x, dot_y, z, settings)
                recessed_dots.append(recessed_dot)

    if not recessed_dots:
        raise RuntimeError("No recessed dots generated for counter plate")

    # Combine all recessed dots into one mesh
    recessed_dots_combined = trimesh.util.concatenate(recessed_dots)

    # Perform boolean subtraction: base plate minus recessed dots
    try:
        final_mesh = base_plate.difference(recessed_dots_combined)
        if final_mesh is None:
            raise RuntimeError("Boolean subtraction failed")
    except Exception as e:
        print(f"Boolean subtraction failed, falling back to extruded top-layer approach: {e}")
        return create_extruded_negative_plate(settings)

    # Center at origin for consistent viewer orientation
    final_mesh.apply_translation(-final_mesh.bounds[0])
    final_mesh.apply_translation(-final_mesh.centroid)

    return final_mesh


def create_extruded_negative_plate(settings: CardSettings):
    """
    Alternative implementation that creates a counter plate using only 2-D
    polygon operations (Shapely) and extrusion (trimesh.creation.extrude_polygon).
    The result has *cylindrical* recess walls – but guarantees success even when
    no 3-D boolean backend is available.
    """
    try:
        import shapely.geometry as sg
        from shapely.ops import unary_union
        from trimesh.creation import extrude_polygon
    except ImportError as e:
        raise RuntimeError("Required libraries missing for fallback counter plate generation") from e

    # Plate outline in 2-D
    rect = sg.box(0, 0, settings.card_width, settings.card_height)

    # Create circular cutouts at every dot location
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    circles = []
    for row in range(settings.grid_rows):
        for col in range(settings.grid_columns):
            y_pos = settings.card_height - settings.top_margin - (row * settings.line_spacing) + settings.braille_y_adjust
            x_pos = settings.left_margin + (col * settings.cell_spacing) + settings.braille_x_adjust
            for pos in dot_positions:
                cx = x_pos + dot_col_offsets[pos[1]]
                cy = y_pos + dot_row_offsets[pos[0]]
                r = settings.recessed_dot_base_diameter / 2
                circles.append(sg.Point(cx, cy).buffer(r, resolution=16))

    if not circles:
        raise RuntimeError("No cutouts generated for fallback counter plate")

    # Create a simpler approach: just create a base plate with holes
    # We'll use the boolean difference but handle it more carefully
    try:
        # Try to create a single union of all circles
        circles_union = unary_union(circles)
        
        # Create the top layer by subtracting circles from the rectangle
        if hasattr(circles_union, 'geoms'):
            # MultiPolygon case - subtract each circle individually
            top_layer_polygon = rect
            for circle in circles_union.geoms:
                if top_layer_polygon.is_valid:
                    top_layer_polygon = top_layer_polygon.difference(circle)
        else:
            # Single polygon case
            top_layer_polygon = rect.difference(circles_union)
            
        # Ensure the polygon is valid
        if not top_layer_polygon.is_valid:
            top_layer_polygon = top_layer_polygon.buffer(0)
            
    except Exception as e:
        print(f"Complex polygon operations failed, using simple approach: {e}")
        # Fallback: create a simple plate without cutouts
        top_layer_polygon = rect

    # Create the meshes
    bottom_height = settings.card_thickness - settings.recessed_dot_height
    top_height = settings.recessed_dot_height

    try:
        bottom_mesh = extrude_polygon(rect, bottom_height)
        top_mesh = extrude_polygon(top_layer_polygon, top_height)
        top_mesh.apply_translation([0, 0, bottom_height])
        
        plate = trimesh.util.concatenate([bottom_mesh, top_mesh])
    except Exception as e:
        print(f"Extrusion failed, creating simple plate: {e}")
        # Ultimate fallback: just create a simple box
        plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
        plate.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))

    # Center at origin
    try:
        plate.apply_translation(-plate.bounds[0])
        plate.apply_translation(-plate.centroid)
    except:
        pass  # If centering fails, just return the plate as is

    return plate

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/node_modules/<path:filename>')
def node_modules(filename):
    return send_from_directory('node_modules', filename)

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
    
    # Validate each line length
    for i, line in enumerate(lines):
        if len(line.strip()) > settings.grid_columns:
            over = len(line.strip()) - settings.grid_columns
            return jsonify({'error': f'Line {i+1} exceeds {settings.grid_columns} braille cells by {over} cells. Please shorten your text.'}), 400
    
    try:
        if plate_type == 'positive':
            mesh = create_positive_plate_mesh(lines, grade, settings)
        else:
            mesh = create_negative_plate_mesh(settings)
        
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
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=f'{filename}_braille.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate STL: {str(e)}'}), 500

@app.route('/generate_counter_plate_stl', methods=['POST'])
def generate_counter_plate_stl():
    """
    Endpoint to generate and download the universal counter plate.
    """
    data = request.get_json()
    settings_data = data.get('settings', {})
    
    try:
        settings = CardSettings(**settings_data)
        mesh = create_negative_plate_mesh(settings)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        filename = "universal_counter_plate"
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl')

    except Exception as e:
        # It's helpful to log the full error on the server for debugging
        print(f"Error in /generate_counter_plate_stl: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate counter plate STL: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment
app.debug = False 