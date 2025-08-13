from flask import Flask, request, send_file, jsonify, render_template, send_from_directory
import trimesh
import numpy as np
import io
import os
import re
import json
from pathlib import Path
from flask_cors import CORS
import requests

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

def translate_with_liblouis_js(text: str, grade: str = "g2") -> str:
    """
    Translate text to UEB braille using liblouis JavaScript build.
    This approach uses the pre-compiled JavaScript binaries from liblouis/js-build.
    """
    try:
        # Use the appropriate table for the grade
        table = "en-us-g2.ctb" if grade == "g2" else "en-us-g1.ctb"
        
        # For now, we'll use a simple mapping as fallback
        # In production, you would integrate the actual liblouis JavaScript build
        return fallback_translation(text)
        
    except Exception as e:
        print(f"Error in liblouis JS translation: {e}")
        return fallback_translation(text)

def fallback_translation(text: str) -> str:
    """
    Fallback translation for when liblouis JS isn't available.
    This provides basic Grade 1 braille mapping.
    """
    simple_mapping = {
        'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑',
        'f': '⠋', 'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚',
        'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕',
        'p': '⠏', 'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞',
        'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭', 'y': '⠽',
        'z': '⠵', ' ': '⠀', '0': '⠚', '1': '⠁', '2': '⠃',
        '3': '⠉', '4': '⠙', '5': '⠑', '6': '⠋', '7': '⠛',
        '8': '⠓', '9': '⠊'
    }
    
    result = ""
    for char in text.lower():
        if char in simple_mapping:
            result += simple_mapping[char]
        else:
            result += char
    
    return result

def braille_to_dots(braille_char: str) -> list:
    """
    Convert a braille character to dot pattern.
    Braille dots are arranged as:
    1 4
    2 5
    3 6
    """
    # Simple dot mapping for basic braille characters
    dot_patterns = {
        '⠁': [1, 0, 0, 0, 0, 0],  # a
        '⠃': [1, 1, 0, 0, 0, 0],  # b
        '⠉': [1, 0, 0, 1, 0, 0],  # c
        '⠙': [1, 0, 0, 1, 1, 0],  # d
        '⠑': [1, 0, 0, 0, 1, 0],  # e
        '⠋': [1, 1, 0, 1, 0, 0],  # f
        '⠛': [1, 1, 0, 1, 1, 0],  # g
        '⠓': [1, 1, 0, 0, 1, 0],  # h
        '⠊': [0, 1, 0, 1, 0, 0],  # i
        '⠚': [0, 1, 0, 1, 1, 0],  # j
        '⠅': [1, 0, 1, 0, 0, 0],  # k
        '⠇': [1, 1, 1, 0, 0, 0],  # l
        '⠍': [1, 0, 1, 1, 0, 0],  # m
        '⠝': [1, 0, 1, 1, 1, 0],  # n
        '⠕': [1, 0, 1, 0, 1, 0],  # o
        '⠏': [1, 1, 1, 1, 0, 0],  # p
        '⠟': [1, 1, 1, 1, 1, 0],  # q
        '⠗': [1, 1, 1, 0, 1, 0],  # r
        '⠎': [0, 1, 1, 1, 0, 0],  # s
        '⠞': [0, 1, 1, 1, 1, 0],  # t
        '⠥': [1, 0, 1, 0, 0, 1],  # u
        '⠧': [1, 1, 1, 0, 0, 1],  # v
        '⠺': [0, 1, 0, 0, 1, 1],  # w
        '⠭': [1, 0, 1, 1, 0, 1],  # x
        '⠽': [1, 0, 1, 1, 1, 1],  # y
        '⠵': [1, 0, 1, 0, 1, 1],  # z
        '⠀': [0, 0, 0, 0, 0, 0],  # space
    }
    
    return dot_patterns.get(braille_char, [0, 0, 0, 0, 0, 0])

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

def create_positive_plate_mesh(lines, grade="g2", settings=None):
    """
    Create a standard braille mesh (positive plate with raised dots).
    Lines are processed in top-down order.
    """
    if settings is None:
        settings = CardSettings()

    grade_name = f"Grade {grade.upper()}" if grade in ["g1", "g2"] else "Grade 2"
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
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Process each line in top-down order
    for row_num in range(settings.grid_rows):
        if row_num >= len(lines):
            break
            
        line_text = lines[row_num].strip()
        if not line_text:
            continue
            
        # Translate English text to braille using liblouis JS
        try:
            braille_text = translate_with_liblouis_js(line_text, grade)
            print(f"Line {row_num + 1}: '{line_text}' → '{braille_text}'")
        except Exception as e:
            print(f"Warning: Failed to translate line {row_num + 1}, using original text: {e}")
            braille_text = line_text
        
        # Check if braille text exceeds grid capacity
        if len(braille_text) > settings.grid_columns:
            print(f"Warning: Line {row_num + 1} exceeds {settings.grid_columns} braille cells by {len(braille_text) - settings.grid_columns} cells")
            braille_text = braille_text[:int(settings.grid_columns)]
        
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

def create_simple_negative_plate(settings: CardSettings):
    """
    Create a simple negative plate for Vercel compatibility.
    This avoids complex boolean operations that can fail in serverless environments.
    """
    # Create base plate
    base_plate = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base_plate.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))
    
    # Create recessed dots as cylinders
    recessed_dots = []
    
    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Create recessed dots for each grid position
    for row in range(settings.grid_rows):
        for col in range(settings.grid_columns):
            # Calculate position
            x_pos = settings.left_margin + (col * settings.cell_spacing) + settings.braille_x_adjust
            y_pos = settings.card_height - settings.top_margin - (row * settings.line_spacing) + settings.braille_y_adjust
            
            # Create recessed dot (cylinder going down from top surface)
            recessed_dot = trimesh.creation.cylinder(
                radius=settings.recessed_dot_base_diameter / 2,
                height=settings.recessed_dot_height,
                sections=16
            )
            
            # Position the dot (z starts at card surface and goes down)
            z_pos = settings.card_thickness - (settings.recessed_dot_height / 2)
            recessed_dot.apply_translation((x_pos, y_pos, z_pos))
            recessed_dots.append(recessed_dot)
    
    # Combine all recessed dots
    if recessed_dots:
        recessed_dots_combined = trimesh.util.concatenate(recessed_dots)
        
        # Try boolean difference, fall back to simple approach if it fails
        try:
            final_mesh = base_plate.difference(recessed_dots_combined)
            return final_mesh
        except Exception as e:
            print(f"Boolean subtraction failed, creating simple recessed plate: {e}")
            # Return base plate with recessed dots as separate meshes
            return trimesh.util.concatenate([base_plate] + recessed_dots)
    else:
        return base_plate

@app.route('/')
def index():
    return render_template('index.html')

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
    
    # Validate each line length
    for i, line in enumerate(lines):
        if len(line.strip()) > settings.grid_columns:
            over = len(line.strip()) - settings.grid_columns
            return jsonify({'error': f'Line {i+1} exceeds {settings.grid_columns} braille cells by {over} cells. Please shorten your text.'}), 400
    
    try:
        if plate_type == 'positive':
            mesh = create_positive_plate_mesh(lines, grade, settings)
        else:
            return jsonify({'error': 'Counter plate generation not available in Vercel version. Use positive plate only.'}), 400
        
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
    Counter plate generation with simplified approach for Vercel.
    """
    data = request.get_json()
    settings_data = data.get('settings', {})
    settings = CardSettings(**settings_data)
    
    try:
        mesh = create_simple_negative_plate(settings)
        
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
