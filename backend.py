from flask import Flask, request, send_file, jsonify, render_template, send_from_directory, redirect
import trimesh
import numpy as np
import io
import os
import re
import json
from datetime import datetime
from pathlib import Path
from flask_cors import CORS
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from functools import wraps
import time
from collections import defaultdict
import hashlib

app = Flask(__name__)
# CORS configuration - update with your actual domain before deployment
allowed_origins = [
    'https://your-vercel-domain.vercel.app',  # Replace with your actual Vercel domain
    'https://your-custom-domain.com'  # Replace with your custom domain if any
]

# For development, allow localhost
if os.environ.get('FLASK_ENV') == 'development':
    allowed_origins.extend(['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5001'])

CORS(app, origins=allowed_origins, supports_credentials=True)

# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max request size
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Rate limiting storage
request_counts = defaultdict(list)
REQUEST_LIMIT = 10  # requests per minute
TIME_WINDOW = 60  # seconds

# Security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # More permissive CSP to allow STL loading and other necessary resources
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://vercel.live; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' blob: data:; "
        "object-src 'none'; "
        "base-uri 'self'"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# Rate limiting decorator
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP (considering proxy headers for production)
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = request.remote_addr
        
        # Clean old requests
        current_time = time.time()
        request_counts[client_ip] = [
            req_time for req_time in request_counts[client_ip]
            if current_time - req_time < TIME_WINDOW
        ]
        
        # Check rate limit
        if len(request_counts[client_ip]) >= REQUEST_LIMIT:
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        # Record this request
        request_counts[client_ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function

# Input validation functions
def validate_lines(lines):
    """Validate the lines input for security and correctness"""
    if not isinstance(lines, list):
        raise ValueError("Lines must be a list")
    
    if len(lines) != 4:
        raise ValueError("Must provide exactly 4 lines")
    
    for i, line in enumerate(lines):
        if not isinstance(line, str):
            raise ValueError(f"Line {i+1} must be a string")
        
        # Check length to prevent extremely long inputs
        if len(line) > 50:
            raise ValueError(f"Line {i+1} is too long (max 50 characters)")
        
        # Basic sanitization - remove potentially harmful characters
        if any(char in line for char in ['<', '>', '&', '"', "'", '\x00']):
            raise ValueError(f"Line {i+1} contains invalid characters")
    
    return True

def validate_settings(settings_data):
    """Validate settings data for security"""
    if not isinstance(settings_data, dict):
        raise ValueError("Settings must be a dictionary")
    
    # Define allowed settings keys and their types/ranges
    allowed_settings = {
        'card_width': (float, 50, 200),
        'card_height': (float, 30, 150),
        'card_thickness': (float, 1, 10),
        'grid_columns': (int, 1, 20),
        'grid_rows': (int, 1, 10),
        'cell_spacing': (float, 2, 15),
        'line_spacing': (float, 5, 25),
        'dot_spacing': (float, 1, 5),
        'emboss_dot_base_diameter': (float, 0.5, 3),
        'emboss_dot_height': (float, 0.3, 2),
        'emboss_dot_flat_hat': (float, 0.1, 2),
        'braille_x_adjust': (float, -10, 10),
        'braille_y_adjust': (float, -10, 10),
        'counter_plate_dot_size_offset': (float, 0, 2),
        'hemisphere_subdivisions': (int, 1, 3)
    }
    
    for key, value in settings_data.items():
        if key not in allowed_settings:
            continue  # Ignore unknown settings (CardSettings will use defaults)
        
        expected_type, min_val, max_val = allowed_settings[key]
        
        # Type validation
        try:
            if expected_type == int:
                value = int(float(value))  # Allow "2.0" to become int 2
            else:
                value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Setting '{key}' must be a number")
        
        # Range validation
        if not (min_val <= value <= max_val):
            raise ValueError(f"Setting '{key}' must be between {min_val} and {max_val}")
    
    return True

# Add error handling for Vercel environment
@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    # Log error for debugging in production
    app.logger.error(f"Error: {str(e)}")
    app.logger.error(f"Traceback: {traceback.format_exc()}")
    # Don't expose internal details in production
    if app.debug:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    else:
        return jsonify({'error': 'An internal server error occurred'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 1MB.'}), 413

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Invalid request format'}), 400

class CardSettings:
    def __init__(self, **kwargs):
        # Default values matching project brief
        defaults = {
            # Card parameters
            "card_width": 90,
            "card_height": 52,
            "card_thickness": 2.0,
            # Grid parameters
            "grid_columns": 13,
            "grid_rows": 4,
            "cell_spacing": 6.5,  # Project brief default
            "line_spacing": 10.0,
            "dot_spacing": 2.5,
            # Emboss plate dot parameters (as per project brief)
            "emboss_dot_base_diameter": 1.8,  # Updated default: 1.8 mm
            "emboss_dot_height": 1.0,  # Project brief default: 1.0 mm
            "emboss_dot_flat_hat": 0.4,  # Updated default: 0.4 mm
            # Offset adjustments
            "braille_y_adjust": 0.0,  # Default to center
            "braille_x_adjust": 0.0,  # Default to center
            # Counter plate specific parameters
            "hemisphere_subdivisions": 1,  # For mesh density control
            "counter_plate_dot_size_offset": 0.0,  # Default offset from emboss dot diameter
            # Legacy parameters (for backward compatibility)
            "dot_base_diameter": 1.8,  # Updated default: 1.8 mm
            "dot_height": 1.0,  # Project brief default: 1.0 mm
            "dot_hat_size": 0.4,  # Updated default: 0.4 mm
            "negative_plate_offset": 0.4,  # Legacy name for backward compatibility
            "emboss_dot_base_diameter_mm": 1.8,  # Updated default: 1.8 mm
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
        self.grid_width = (self.grid_columns - 1) * self.cell_spacing
        self.left_margin = (self.card_width - self.grid_width) / 2
        self.grid_height = (self.grid_rows - 1) * self.line_spacing
        self.top_margin = (self.card_height - self.grid_height) / 2
        
        # Map new parameter names to legacy ones for backward compatibility
        if 'emboss_dot_base_diameter' in kwargs:
            self.dot_base_diameter = self.emboss_dot_base_diameter
        if 'emboss_dot_height' in kwargs:
            self.dot_height = self.emboss_dot_height
        if 'emboss_dot_flat_hat' in kwargs:
            self.dot_hat_size = self.emboss_dot_flat_hat
        
        # Handle legacy parameter name for backward compatibility
        if 'negative_plate_offset' in kwargs and 'counter_plate_dot_size_offset' not in kwargs:
            self.counter_plate_dot_size_offset = self.negative_plate_offset
            
        # Ensure consistency between parameter names
        self.dot_top_diameter = self.emboss_dot_flat_hat
        self.emboss_dot_base_diameter_mm = self.emboss_dot_base_diameter
        
        # Recessed dot parameters (adjusted by offset) - for legacy functions
        self.recessed_dot_base_diameter = self.emboss_dot_base_diameter + (self.negative_plate_offset * 2)
        self.recessed_dot_top_diameter = self.emboss_dot_flat_hat + (self.negative_plate_offset * 2)
        self.recessed_dot_height = self.emboss_dot_height + self.negative_plate_offset
        
        # Counter plate specific parameters (not used in hemisphere approach)
        self.counter_plate_dot_base_diameter = self.emboss_dot_base_diameter + (self.negative_plate_offset * 2)
        self.counter_plate_dot_top_diameter = self.emboss_dot_flat_hat + (self.negative_plate_offset * 2)
        self.counter_plate_dot_height = self.emboss_dot_height + self.negative_plate_offset
        
        # Hemispherical recess parameters (as per project brief)
        # The hemisphere radius is now affected by the counter plate dot size offset
        self.hemisphere_radius = (self.emboss_dot_base_diameter + self.counter_plate_dot_size_offset) / 2
        self.plate_thickness = self.card_thickness
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
    Uses the project brief parameter names.
    """
    # Create a cylinder with the base diameter
    cylinder = trimesh.creation.cylinder(
        radius=settings.emboss_dot_base_diameter / 2,
        height=settings.emboss_dot_height,
        sections=16
    )
    
    # Scale the top vertices to create the cone shape (frustum)
    # This creates a cone with flat top (as per project brief)
    if settings.emboss_dot_base_diameter > 0:
        scale_factor = settings.emboss_dot_flat_hat / settings.emboss_dot_base_diameter
        
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
            
        # Frontend must send proper braille Unicode characters
        # Check if input contains proper braille Unicode (U+2800 to U+28FF)
        has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)
        
        if has_braille_chars:
            # Input is proper braille Unicode, use it directly
            braille_text = line_text
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
            
            # Calculate X position for this column
            x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create dots for this cell
            for i, dot_val in enumerate(dots):
                if dot_val == 1:
                    dot_pos = dot_positions[i]
                    dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                    dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                    z = settings.card_thickness + settings.emboss_dot_height / 2
                    
                    dot_mesh = create_braille_dot(dot_x, dot_y, z, settings)
                    meshes.append(dot_mesh)
    
    print(f"Created positive plate with {len(meshes)-1} cone-shaped dots")
    return trimesh.util.concatenate(meshes)

def create_simple_negative_plate(settings: CardSettings, lines=None):
    """
    Create a negative plate with recessed holes using 2D Shapely operations for Vercel compatibility.
    This creates a counter plate with holes that match the embossing plate dimensions and positioning.
    """
    
    # Create base rectangle for the card
    base_polygon = Polygon([
        (0, 0),
        (settings.card_width, 0),
        (settings.card_width, settings.card_height),
        (0, settings.card_height)
    ])
    
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
    
    # Ensure hole radius is reasonable (at least 0.5mm)
    if hole_radius < 0.5:
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
                
            # Process each braille character in the line
            for col_num, braille_char in enumerate(line_text):
                if col_num >= settings.grid_columns:
                    break
                    
                # Calculate X position for this column (same as embossing plate)
                x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust
                    
                # Create holes for the dots that are present in this braille character
                dots = braille_to_dots(braille_char)
                    
                for dot_idx, dot_val in enumerate(dots):
                    if dot_val == 1:  # Only create holes for dots that are present
                        dot_pos = dot_positions[dot_idx]
                        dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                        dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                        
                        
                        # Create circular hole with higher resolution
                        hole = Point(dot_x, dot_y).buffer(hole_radius, resolution=64)
                        holes.append(hole)
                        total_dots += 1
                        
    
    if not holes:
        print("WARNING: No holes were created! Creating a plate with all possible holes as fallback")
        # Fallback: create holes for all possible positions
        return create_universal_counter_plate_fallback(settings)
    
    # Combine all holes into one multi-polygon
    try:
        all_holes = unary_union(holes)
        
        # Subtract holes from base to create the plate with holes
        plate_with_holes = base_polygon.difference(all_holes)
        
    except Exception as e:
        app.logger.error(f"Failed to combine holes or subtract from base: {e}")
        return create_fallback_plate(settings)
    
    # Extrude the 2D shape to 3D
    try:
        # Handle both Polygon and MultiPolygon results
        if hasattr(plate_with_holes, 'geoms'):
            # It's a MultiPolygon - take the largest polygon (should be the main plate)
            largest_polygon = max(plate_with_holes.geoms, key=lambda p: p.area)
            final_mesh = trimesh.creation.extrude_polygon(largest_polygon, height=settings.card_thickness)

        else:
            # It's a single Polygon
            final_mesh = trimesh.creation.extrude_polygon(plate_with_holes, height=settings.card_thickness)
        
        return final_mesh
    except Exception as e:
        app.logger.error(f"Failed to extrude polygon: {e}")
        # Fallback to simple base plate if extrusion fails
        return create_fallback_plate(settings)

def create_universal_counter_plate_fallback(settings: CardSettings):
    """Create a counter plate with all possible holes as fallback when text-based holes fail"""
    
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
    
    # Create the base plate as a box aligned to z=[0, TH], x=[0, W], y=[0, H]
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width/2, params.card_height/2, params.plate_thickness/2))
    
    
    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]
    
    # Create icospheres for ALL possible dot positions
    sphere_meshes = []
    total_spheres = 0
    
    # Generate spheres for each grid position
    for row in range(params.grid_rows):
        # Calculate Y position for this row (same as embossing plate)
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust
        
        for col in range(params.grid_columns):
            # Calculate X position for this column (same as embossing plate)
            x_pos = params.left_margin + (col * params.cell_spacing) + params.braille_x_adjust
            
            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create an icosphere with radius = emboss_dot_base_diameter / 2
                # Use hemisphere_subdivisions parameter to control mesh density
                sphere = trimesh.creation.icosphere(subdivisions=params.hemisphere_subdivisions, radius=params.hemisphere_radius)
                
                # Position the sphere center at z = TH + ε so the lower hemisphere sits inside the slab
                # and the equator coincides with the top surface
                z_pos = params.plate_thickness + params.epsilon
                sphere.apply_translation((dot_x, dot_y, z_pos))
                

                
                sphere_meshes.append(sphere)
                total_spheres += 1
    
    
    if not sphere_meshes:
        print("WARNING: No spheres were generated. Returning base plate.")
        return plate_mesh
    
    # Perform boolean operations using Manifold backend
    try:
        # Union all spheres together (optional; Manifold can take a list)
        if len(sphere_meshes) == 1:
            union_spheres = sphere_meshes[0]
        else:
            union_spheres = trimesh.boolean.union(sphere_meshes, engine='manifold')
        
        
        # Subtract the unified spheres from the plate in one operation
        counter_plate_mesh = trimesh.boolean.difference([plate_mesh, union_spheres], engine='manifold')
        
        # Verify the mesh is watertight
        if not counter_plate_mesh.is_watertight:
            # Try to fix the mesh
            counter_plate_mesh.fill_holes()
        
        return counter_plate_mesh
        
    except Exception as e:
        print(f"ERROR: Boolean operations with Manifold failed: {e}")
        print("WARNING: Falling back to simple negative plate method.")
        # Fallback to the simple approach if Manifold fails
        return create_simple_negative_plate(params)

@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Vercel backend is running'})




@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return jsonify({'error': 'Failed to load template'}), 500

@app.route('/node_modules/<path:filename>')
def node_modules(filename):
    """Redirect node_modules requests to static files for Vercel deployment"""
    # Map common node_modules paths to static equivalents
    if filename.startswith('liblouis-build/') or filename.startswith('liblouis/'):
        # Remove the 'liblouis-build/' or 'liblouis/' prefix and redirect to static
        static_path = filename.replace('liblouis-build/', 'liblouis/').replace('liblouis/', 'liblouis/')
        return redirect(f'/static/{static_path}')
    
    # For other node_modules requests, return 404
    return jsonify({'error': 'node_modules not available on deployment'}), 404

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests to prevent 404 errors"""
    return '', 204  # Return empty response with "No Content" status

@app.route('/static/<path:filename>')
def static_files(filename):
    try:
        # Security: Prevent path traversal attacks
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Normalize the path to prevent bypassing
        safe_path = os.path.normpath(filename)
        if safe_path != filename or safe_path.startswith('..'):
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Check if static directory exists
        if not os.path.exists('static'):
            app.logger.error("Static directory not found")
            return jsonify({'error': 'Resource not found'}), 404
        
        # Check if file exists
        full_path = os.path.join('static', safe_path)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Additional security: ensure the resolved path is still under static/
        if not os.path.abspath(full_path).startswith(os.path.abspath('static')):
            return jsonify({'error': 'Invalid file path'}), 400
        
        return send_from_directory('static', safe_path)
    except Exception as e:
        app.logger.error(f"Failed to serve static file {filename}: {e}")
        return jsonify({'error': 'Failed to serve file'}), 500

@app.route('/generate_braille_stl', methods=['POST'])
@rate_limit
def generate_braille_stl():
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json(force=True)
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        lines = data.get('lines', ['', '', '', ''])
        plate_type = data.get('plate_type', 'positive')
        grade = data.get('grade', 'g2')
        settings_data = data.get('settings', {})
        
        # Validate inputs
        validate_lines(lines)
        validate_settings(settings_data)
        
        # Validate plate_type
        if plate_type not in ['positive', 'negative']:
            return jsonify({'error': 'Invalid plate_type. Must be "positive" or "negative"'}), 400
        
        # Validate grade
        if grade not in ['g1', 'g2']:
            return jsonify({'error': 'Invalid grade. Must be "g1" or "g2"'}), 400
        
        settings = CardSettings(**settings_data)
        
        # Check for empty input only for positive plates (emboss plates require text)
        if plate_type == 'positive' and all(not line.strip() for line in lines):
            return jsonify({'error': 'Please enter text in at least one line'}), 400
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Validation error in generate_braille_stl: {e}")
        return jsonify({'error': 'Invalid request data'}), 400
    
    # Character limit validation is now done on frontend after braille translation
    # Backend expects lines to already be within limits
    
    try:
        if plate_type == 'positive':
            mesh = create_positive_plate_mesh(lines, grade, settings)
        elif plate_type == 'negative':
            # Counter plate uses hemispherical recesses as per project brief
            # It does NOT depend on text input - always creates ALL 6 dots per cell
            print("DEBUG: Generating counter plate with hemispherical recesses (all positions)")
            mesh = build_counter_plate_hemispheres(settings)
        else:
            return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400
        
        # Verify mesh is watertight and manifold
        if not mesh.is_watertight:
            print(f"WARNING: Generated {plate_type} plate mesh is not watertight!")
            # Try to fix the mesh
            mesh.fill_holes()
            if mesh.is_watertight:
                print("INFO: Mesh holes filled successfully")
            else:
                print("ERROR: Could not make mesh watertight")
        
        if not mesh.is_winding_consistent:
            print(f"WARNING: Generated {plate_type} plate mesh has inconsistent winding!")
            mesh.fix_normals()
            print("INFO: Fixed mesh normals")
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Create JSON config dump for reproducibility
        config_dump = {
            "timestamp": datetime.now().isoformat(),
            "plate_type": plate_type,
            "grade": grade if plate_type == 'positive' else "n/a",
            "text_lines": lines if plate_type == 'positive' else ["Counter plate - all positions"],
            "settings": {
                # Card parameters
                "card_width": settings.card_width,
                "card_height": settings.card_height,
                "card_thickness": settings.card_thickness,
                # Grid parameters
                "grid_columns": settings.grid_columns,
                "grid_rows": settings.grid_rows,
                "cell_spacing": settings.cell_spacing,
                "line_spacing": settings.line_spacing,
                "dot_spacing": settings.dot_spacing,
                # Emboss plate dot parameters
                "emboss_dot_base_diameter": settings.emboss_dot_base_diameter,
                "emboss_dot_height": settings.emboss_dot_height,
                "emboss_dot_flat_hat": settings.emboss_dot_flat_hat,
                # Offsets
                "braille_x_adjust": settings.braille_x_adjust,
                "braille_y_adjust": settings.braille_y_adjust,
                # Counter plate specific
                "hemisphere_subdivisions": settings.hemisphere_subdivisions if plate_type == 'negative' else "n/a"
            },
            "mesh_info": {
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
                "is_watertight": bool(mesh.is_watertight),
                "volume": float(mesh.volume)
            }
        }
        
        # Save config as JSON
        config_json = json.dumps(config_dump, indent=2)
        print(f"DEBUG: Config dump:\n{config_json}")
        
        # Create filename based on text content with fallback logic
        if plate_type == 'positive':
            # For embossing plates, prioritize Line 1, then fallback to other lines
            filename = 'braille_embossing_plate'
            for i, line in enumerate(lines):
                if line.strip():
                    # Sanitize filename: remove special characters and limit length
                    sanitized = re.sub(r'[^\w\s-]', '', line.strip()[:30])
                    sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
                    if sanitized:
                        if i == 0:  # Line 1
                            filename = f'braille_embossing_plate_{sanitized}'
                        else:  # Other lines as fallback
                            filename = f'braille_embossing_plate_{sanitized}'
                        break
        else:
            # For counter plates, include total diameter (base + offset) in filename
            total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
            filename = f'braille_counter_plate_{total_diameter}mm'
        
        # Additional filename sanitization for security
        filename = re.sub(r'[^\w\-_]', '', filename)[:50]  # Allow longer names for embossing plates
        
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate STL: {str(e)}'}), 500

@app.route('/generate_counter_plate_stl', methods=['POST'])
@rate_limit
def generate_counter_plate_stl():
    """
    Generate counter plate with hemispherical recesses as per project brief.
    Counter plate does NOT depend on text input - it always creates ALL 6 dots per cell.
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        settings_data = data.get('settings', {})
        validate_settings(settings_data)
        settings = CardSettings(**settings_data)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Validation error in generate_counter_plate_stl: {e}")
        return jsonify({'error': 'Invalid request data'}), 400
    
    try:
        print("DEBUG: Generating counter plate with hemispherical recesses (all positions)")
        mesh = build_counter_plate_hemispheres(settings)
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Include total diameter (base + offset) in filename
        total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        filename = f"braille_counter_plate_{total_diameter}mm"
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl')
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate counter plate: {str(e)}'}), 500

@app.route('/generate_universal_counter_plate', methods=['POST'])
@rate_limit
def generate_universal_counter_plate_route():
    """
    Generate a universal counter plate with hemispherical recesses for ALL possible dot positions.
    This endpoint does NOT require any text input - it generates a plate with recesses at all 312 dot positions.
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        settings_data = data.get('settings', {})
        validate_settings(settings_data)
        settings = CardSettings(**settings_data)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Validation error in generate_universal_counter_plate: {e}")
        return jsonify({'error': 'Invalid request data'}), 400
    
    try:
        print("DEBUG: Generating universal counter plate with hemispherical recesses (no text input required)")
        mesh = build_counter_plate_hemispheres(settings)
        
        # Verify mesh is watertight
        if not mesh.is_watertight:
            print("WARNING: Universal counter plate mesh is not watertight, attempting to fix...")
            mesh.fill_holes()
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Include total diameter (base + offset) in filename
        total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        filename = f'braille_universal_counter_plate_{total_diameter}mm.stl'
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate universal counter plate: {str(e)}'}), 500


@app.route('/generate_hemispherical_counter_plate', methods=['POST'])
@rate_limit
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
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        settings_data = data.get('settings', {})
        validate_settings(settings_data)
        settings = CardSettings(**settings_data)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Validation error in generate_hemispherical_counter_plate: {e}")
        return jsonify({'error': 'Invalid request data'}), 400
    
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
        
        # Include total diameter (base + offset) in filename
        total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        filename = f'braille_hemispherical_counter_plate_{total_diameter}mm.stl'
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate hemispherical counter plate: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment
app.debug = False 