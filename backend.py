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
            "card_height": 60,
            "card_thickness": 2.0,
            # Grid parameters
            "grid_columns": 14,
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
            # Cylinder counter plate robustness (how much the sphere crosses the outer surface)
            "cylinder_counter_plate_overcut_mm": 0.05,
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
        
        # Calculate grid dimensions first
        self.grid_width = (self.grid_columns - 1) * self.cell_spacing
        self.grid_height = (self.grid_rows - 1) * self.line_spacing
        
        # Center the grid on the card with calculated margins
        self.left_margin = (self.card_width - self.grid_width) / 2
        self.right_margin = (self.card_width - self.grid_width) / 2
        self.top_margin = (self.card_height - self.grid_height) / 2
        self.bottom_margin = (self.card_height - self.grid_height) / 2
        
        # Safety margin minimum (½ of cell spacing)
        self.min_safe_margin = self.cell_spacing / 2
        
        # Validate that braille dots stay within solid surface boundaries (if not in initialization)
        try:
            self._validate_margins()
        except Exception as e:
            # Don't fail initialization due to validation issues
            print(f"Note: Margin validation skipped during initialization: {e}")
        
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
        # The hemisphere radius is affected by the counter plate dot size offset
        self.hemisphere_radius = (self.emboss_dot_base_diameter + self.counter_plate_dot_size_offset) / 2
        self.plate_thickness = self.card_thickness
        self.epsilon = self.epsilon_mm
        self.cylinder_counter_plate_overcut_mm = self.cylinder_counter_plate_overcut_mm

    def _validate_margins(self):
        """
        Validate that the centered margins provide enough space for braille dots
        and meet the minimum safety margin requirements.
        """
        try:
            # Ensure all required attributes exist
            required_attrs = ['dot_spacing', 'left_margin', 'right_margin', 'top_margin', 'bottom_margin', 
                            'grid_width', 'grid_height', 'card_width', 'card_height', 'cell_spacing', 'min_safe_margin']
            for attr in required_attrs:
                if not hasattr(self, attr):
                    return  # Skip validation if attributes are missing
            
            # Check if margins meet minimum safety requirements
            margin_warnings = []
            if self.left_margin < self.min_safe_margin:
                margin_warnings.append(f"Left margin ({self.left_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)")
            if self.right_margin < self.min_safe_margin:
                margin_warnings.append(f"Right margin ({self.right_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)")
            if self.top_margin < self.min_safe_margin:
                margin_warnings.append(f"Top margin ({self.top_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)")
            if self.bottom_margin < self.min_safe_margin:
                margin_warnings.append(f"Bottom margin ({self.bottom_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)")
            
            # Calculate the actual space needed for the braille grid with dots
            # Each braille cell is cell_spacing wide, dot spacing extends ±dot_spacing/2 from center
            max_dot_extension = self.dot_spacing / 2
            
            # Check if outermost dots will be within boundaries
            # Consider that dots extend ±dot_spacing/2 from their centers
            left_edge_clearance = self.left_margin - max_dot_extension
            right_edge_clearance = self.right_margin - max_dot_extension
            top_edge_clearance = self.top_margin - max_dot_extension
            bottom_edge_clearance = self.bottom_margin - max_dot_extension
            
            if margin_warnings:
                print("⚠ WARNING: Margins below minimum safe values:")
                for warning in margin_warnings:
                    print(f"  - {warning}")
                print(f"  - Recommended minimum margin: {self.min_safe_margin:.2f}mm (½ of {self.cell_spacing:.1f}mm cell spacing)")
                print(f"  - Consider reducing grid size or increasing card dimensions")
            
            # Check if dots will extend beyond card edges
            edge_warnings = []
            if left_edge_clearance < 0:
                edge_warnings.append(f"Left edge dots will extend {-left_edge_clearance:.2f}mm beyond card edge")
            if right_edge_clearance < 0:
                edge_warnings.append(f"Right edge dots will extend {-right_edge_clearance:.2f}mm beyond card edge")
            if top_edge_clearance < 0:
                edge_warnings.append(f"Top edge dots will extend {-top_edge_clearance:.2f}mm beyond card edge")
            if bottom_edge_clearance < 0:
                edge_warnings.append(f"Bottom edge dots will extend {-bottom_edge_clearance:.2f}mm beyond card edge")
            
            if edge_warnings:
                print("⚠ CRITICAL WARNING: Braille dots will extend beyond card boundaries!")
                for warning in edge_warnings:
                    print(f"  - {warning}")
            
            # Log successful validation if all is well
            if not margin_warnings and not edge_warnings:
                print(f"✓ Grid centering validation passed: Braille grid is centered with safe margins")
                print(f"  - Grid dimensions: {self.grid_width:.2f}mm × {self.grid_height:.2f}mm")
                print(f"  - Card dimensions: {self.card_width:.2f}mm × {self.card_height:.2f}mm")
                print(f"  - Centered margins: L/R={self.left_margin:.2f}mm, T/B={self.top_margin:.2f}mm")
                print(f"  - Minimum safe margin: {self.min_safe_margin:.2f}mm (½ of {self.cell_spacing:.1f}mm cell spacing)")
        except Exception as e:
            # Silently skip validation if there are any issues
            pass

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


def create_triangle_marker_polygon(x, y, settings: CardSettings):
    """
    Create a 2D triangle polygon for the first cell of each braille row.
    The triangle base height equals the distance between top and bottom braille dots.
    The triangle extends horizontally to the middle-right dot position.
    
    Args:
        x: X position of the cell center
        y: Y position of the cell center
        settings: CardSettings object with braille dimensions
    
    Returns:
        Shapely Polygon representing the triangle
    """
    # Calculate triangle dimensions based on braille dot spacing
    # Base height = distance from top to bottom dot = 2 * dot_spacing
    base_height = 2 * settings.dot_spacing
    
    # Triangle height (horizontal extension) = dot_spacing (to reach middle-right dot)
    triangle_width = settings.dot_spacing
    
    # Triangle vertices:
    # Base is centered between top-left and bottom-left dots
    base_x = x - settings.dot_spacing / 2  # Left column position
    
    # Create triangle vertices
    vertices = [
        (base_x, y - settings.dot_spacing),      # Bottom of base
        (base_x, y + settings.dot_spacing),      # Top of base
        (base_x + triangle_width, y)             # Apex (at middle-right dot height)
    ]
    
    # Create and return the triangle polygon
    return Polygon(vertices)


def create_card_triangle_marker_3d(x, y, settings: CardSettings, height=0.4, for_subtraction=False):
    """
    Create a 3D triangular prism for card surface marking.
    
    Args:
        x, y: Center position of the first braille cell
        settings: CardSettings object with spacing parameters
        height: Depth/height of the triangle marker (default 0.4mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses
    
    Returns:
        Trimesh object representing the 3D triangle marker
    """
    # Calculate triangle dimensions based on braille dot spacing
    base_height = 2 * settings.dot_spacing
    triangle_width = settings.dot_spacing
    
    # Triangle vertices (same as 2D version)
    base_x = x - settings.dot_spacing / 2  # Left column position
    
    vertices = [
        (base_x, y - settings.dot_spacing),      # Bottom of base
        (base_x, y + settings.dot_spacing),      # Top of base
        (base_x + triangle_width, y)             # Apex (at middle-right dot height)
    ]
    
    # Create 2D polygon using Shapely
    tri_2d = Polygon(vertices)
    
    if for_subtraction:
        # For counter plate recesses, extrude downward from top surface
        # Create a prism that extends from above the surface into the plate
        extrude_height = height + 0.5  # Extra depth to ensure clean boolean
        tri_prism = trimesh.creation.extrude_polygon(tri_2d, height=extrude_height)
        
        # Position at the top surface of the card
        z_pos = settings.card_thickness - 0.1  # Start slightly above surface
        tri_prism.apply_translation([0, 0, z_pos])
    else:
        # For embossing plate, extrude upward from top surface
        tri_prism = trimesh.creation.extrude_polygon(tri_2d, height=height)
        
        # Position on top of the card base
        z_pos = settings.card_thickness
        tri_prism.apply_translation([0, 0, z_pos])
    
    return tri_prism


def create_card_line_end_marker_3d(x, y, settings: CardSettings, height=0.5, for_subtraction=False):
    """
    Create a 3D line (rectangular prism) for end of row marking on card surface.
    
    Args:
        x, y: Center position of the last braille cell in the row
        settings: CardSettings object with spacing parameters
        height: Depth/height of the line marker (default 0.5mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses
    
    Returns:
        Trimesh object representing the 3D line marker
    """
    # Calculate line dimensions based on braille dot spacing
    line_height = 2 * settings.dot_spacing  # Vertical extent (same as cell height)
    line_width = settings.dot_spacing  # Horizontal extent
    
    # Position line at the right column of the cell
    # The line should be centered on the right column dot positions
    line_x = x + settings.dot_spacing / 2  # Right column position
    
    # Create rectangle vertices
    vertices = [
        (line_x - line_width/2, y - settings.dot_spacing),  # Bottom left
        (line_x + line_width/2, y - settings.dot_spacing),  # Bottom right
        (line_x + line_width/2, y + settings.dot_spacing),  # Top right
        (line_x - line_width/2, y + settings.dot_spacing)   # Top left
    ]
    
    # Create 2D polygon using Shapely
    line_2d = Polygon(vertices)
    
    if for_subtraction:
        # For counter plate recesses, extrude downward from top surface
        # Create a prism that extends from above the surface into the plate
        extrude_height = height + 0.5  # Extra depth to ensure clean boolean
        line_prism = trimesh.creation.extrude_polygon(line_2d, height=extrude_height)
        
        # Position at the top surface of the card
        z_pos = settings.card_thickness - 0.1  # Start slightly above surface
        line_prism.apply_translation([0, 0, z_pos])
    else:
        # For embossing plate, extrude upward from top surface
        line_prism = trimesh.creation.extrude_polygon(line_2d, height=height)
        
        # Position on top of the card base
        z_pos = settings.card_thickness
        line_prism.apply_translation([0, 0, z_pos])
    
    return line_prism


def create_character_shape_3d(character, x, y, settings: CardSettings, height=0.6, for_subtraction=True):
    """
    Create a 3D character shape (capital letter A-Z or number 0-9) for end of row marking.
    
    Args:
        character: Single character (A-Z or 0-9)
        x, y: Center position of the last braille cell in the row
        settings: CardSettings object with spacing parameters
        height: Depth of the character recess (default 0.6mm as requested)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses
    
    Returns:
        Trimesh object representing the 3D character marker
    """
    # Define character size based on braille cell dimensions (with 1mm increase)
    char_height = 2 * settings.dot_spacing + 1.0  # Increased by 1mm as requested
    char_width = settings.dot_spacing * 0.8 + 1.0  # Increased by 1mm as requested
    
    # Position character at the right column of the cell
    char_x = x + settings.dot_spacing / 2
    char_y = y
    
    # Define simple line segments for each character
    # Each character is defined as a list of line segments (start_x, start_y, end_x, end_y)
    # Coordinates are normalized to a unit square and will be scaled
    char_definitions = {
        'A': [
            (0.2, 0, 0.5, 1), (0.5, 1, 0.8, 0),  # Two sides of triangle
            (0.35, 0.5, 0.65, 0.5)  # Horizontal bar
        ],
        'B': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65), (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.2, 0.5),  # Top curve
            (0.2, 0.5, 0.7, 0.5), (0.7, 0.5, 0.8, 0.35), (0.8, 0.35, 0.8, 0.15), (0.8, 0.15, 0.7, 0), (0.7, 0, 0.2, 0)  # Bottom curve
        ],
        'C': [
            (0.8, 0.8, 0.7, 0.9), (0.7, 0.9, 0.5, 1), (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7),
            (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.2)
        ],
        'D': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.6, 1), (0.6, 1, 0.8, 0.8), (0.8, 0.8, 0.8, 0.2), (0.8, 0.2, 0.6, 0), (0.6, 0, 0.2, 0)
        ],
        'E': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.2, 0.5, 0.7, 0.5),  # Middle horizontal
            (0.2, 0, 0.8, 0)  # Bottom horizontal
        ],
        'F': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.2, 0.5, 0.7, 0.5)  # Middle horizontal
        ],
        'G': [
            (0.8, 0.8, 0.7, 0.9), (0.7, 0.9, 0.5, 1), (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7),
            (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.2),
            (0.8, 0.2, 0.8, 0.5), (0.8, 0.5, 0.5, 0.5)
        ],
        'H': [
            (0.2, 0, 0.2, 1),  # Left vertical
            (0.8, 0, 0.8, 1),  # Right vertical
            (0.2, 0.5, 0.8, 0.5)  # Horizontal bar
        ],
        'I': [
            (0.3, 1, 0.7, 1),  # Top horizontal
            (0.5, 1, 0.5, 0),  # Vertical
            (0.3, 0, 0.7, 0)  # Bottom horizontal
        ],
        'J': [
            (0.4, 1, 0.8, 1),  # Top horizontal
            (0.6, 1, 0.6, 0.2),  # Vertical
            (0.6, 0.2, 0.5, 0.1), (0.5, 0.1, 0.3, 0), (0.3, 0, 0.2, 0.1), (0.2, 0.1, 0.2, 0.3)
        ],
        'K': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.8, 1, 0.2, 0.5),  # Upper diagonal
            (0.2, 0.5, 0.8, 0)  # Lower diagonal
        ],
        'L': [
            (0.2, 1, 0.2, 0),  # Vertical line
            (0.2, 0, 0.8, 0)  # Bottom horizontal
        ],
        'M': [
            (0.2, 0, 0.2, 1),  # Left vertical
            (0.2, 1, 0.5, 0.6),  # Left diagonal
            (0.5, 0.6, 0.8, 1),  # Right diagonal
            (0.8, 1, 0.8, 0)  # Right vertical
        ],
        'N': [
            (0.2, 0, 0.2, 1),  # Left vertical
            (0.2, 1, 0.8, 0),  # Diagonal
            (0.8, 0, 0.8, 1)  # Right vertical
        ],
        'O': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1),
            (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 0.7),
            (0.8, 0.7, 0.7, 0.9), (0.7, 0.9, 0.5, 1)
        ],
        'P': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65), (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.2, 0.5)
        ],
        'Q': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1),
            (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 0.7),
            (0.8, 0.7, 0.7, 0.9), (0.7, 0.9, 0.5, 1),
            (0.6, 0.2, 0.8, 0)  # Tail
        ],
        'R': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65), (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.2, 0.5),
            (0.2, 0.5, 0.8, 0)  # Diagonal leg
        ],
        'S': [
            (0.8, 0.85, 0.7, 1), (0.7, 1, 0.3, 1), (0.3, 1, 0.2, 0.85), (0.2, 0.85, 0.2, 0.65),
            (0.2, 0.65, 0.3, 0.5), (0.3, 0.5, 0.7, 0.5), (0.7, 0.5, 0.8, 0.35), (0.8, 0.35, 0.8, 0.15),
            (0.8, 0.15, 0.7, 0), (0.7, 0, 0.3, 0), (0.3, 0, 0.2, 0.15)
        ],
        'T': [
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.5, 1, 0.5, 0)  # Vertical
        ],
        'U': [
            (0.2, 1, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 1)
        ],
        'V': [
            (0.2, 1, 0.5, 0),  # Left diagonal
            (0.5, 0, 0.8, 1)  # Right diagonal
        ],
        'W': [
            (0.1, 1, 0.3, 0),  # First diagonal
            (0.3, 0, 0.5, 0.4),  # Second diagonal up
            (0.5, 0.4, 0.7, 0),  # Third diagonal down
            (0.7, 0, 0.9, 1)  # Fourth diagonal
        ],
        'X': [
            (0.2, 1, 0.8, 0),  # Diagonal 1
            (0.2, 0, 0.8, 1)  # Diagonal 2
        ],
        'Y': [
            (0.2, 1, 0.5, 0.5),  # Left diagonal
            (0.8, 1, 0.5, 0.5),  # Right diagonal
            (0.5, 0.5, 0.5, 0)  # Vertical
        ],
        'Z': [
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.8, 1, 0.2, 0),  # Diagonal
            (0.2, 0, 0.8, 0)  # Bottom horizontal
        ],
        '0': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1),
            (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 0.7),
            (0.8, 0.7, 0.7, 0.9), (0.7, 0.9, 0.5, 1)
        ],
        '1': [
            (0.3, 0.8, 0.5, 1),  # Diagonal top
            (0.5, 1, 0.5, 0),  # Vertical
            (0.3, 0, 0.7, 0)  # Bottom horizontal
        ],
        '2': [
            (0.2, 0.8, 0.3, 0.9), (0.3, 0.9, 0.5, 1), (0.5, 1, 0.7, 0.9), (0.7, 0.9, 0.8, 0.8),
            (0.8, 0.8, 0.8, 0.6), (0.8, 0.6, 0.7, 0.5), (0.7, 0.5, 0.2, 0), (0.2, 0, 0.8, 0)
        ],
        '3': [
            (0.2, 0.85, 0.3, 1), (0.3, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65),
            (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.4, 0.5),
            (0.7, 0.5, 0.8, 0.35), (0.8, 0.35, 0.8, 0.15), (0.8, 0.15, 0.7, 0), (0.7, 0, 0.3, 0), (0.3, 0, 0.2, 0.15)
        ],
        '4': [
            (0.7, 0, 0.7, 1),  # Vertical line
            (0.2, 0.6, 0.2, 1), (0.2, 0.6, 0.8, 0.6)  # Horizontal and left part
        ],
        '5': [
            (0.8, 1, 0.2, 1),  # Top horizontal
            (0.2, 1, 0.2, 0.6),  # Vertical down
            (0.2, 0.6, 0.7, 0.6), (0.7, 0.6, 0.8, 0.45), (0.8, 0.45, 0.8, 0.15), (0.8, 0.15, 0.7, 0), (0.7, 0, 0.3, 0), (0.3, 0, 0.2, 0.15)
        ],
        '6': [
            (0.7, 0.9, 0.5, 1), (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3),
            (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3),
            (0.8, 0.3, 0.8, 0.5), (0.8, 0.5, 0.7, 0.6), (0.7, 0.6, 0.3, 0.6), (0.3, 0.6, 0.2, 0.5)
        ],
        '7': [
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.8, 1, 0.4, 0)  # Diagonal
        ],
        '8': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.75), (0.2, 0.75, 0.3, 0.6), (0.3, 0.6, 0.5, 0.5),
            (0.5, 0.5, 0.7, 0.4), (0.7, 0.4, 0.8, 0.25), (0.8, 0.25, 0.7, 0.1), (0.7, 0.1, 0.5, 0),
            (0.5, 0, 0.3, 0.1), (0.3, 0.1, 0.2, 0.25), (0.2, 0.25, 0.3, 0.4), (0.3, 0.4, 0.5, 0.5),
            (0.5, 0.5, 0.7, 0.6), (0.7, 0.6, 0.8, 0.75), (0.8, 0.75, 0.7, 0.9), (0.7, 0.9, 0.5, 1)
        ],
        '9': [
            (0.8, 0.5, 0.7, 0.4), (0.7, 0.4, 0.5, 0.4), (0.5, 0.4, 0.3, 0.5), (0.3, 0.5, 0.2, 0.7),
            (0.2, 0.7, 0.2, 0.85), (0.2, 0.85, 0.3, 1), (0.3, 1, 0.7, 1), (0.7, 1, 0.8, 0.85),
            (0.8, 0.85, 0.8, 0.3), (0.8, 0.3, 0.7, 0.1), (0.7, 0.1, 0.5, 0), (0.5, 0, 0.3, 0.1)
        ]
    }
    
    # Get the character definition
    char_upper = character.upper()
    if char_upper not in char_definitions:
        # Fall back to rectangle for undefined characters
        return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)
    
    line_segments = char_definitions[char_upper]
    
    # Create polygon paths for the character
    # Convert line segments to polygons with thickness
    line_thickness = 0.20  # Increased thickness for bold effect
    polygons = []
    
    for seg in line_segments:
        x1, y1, x2, y2 = seg
        
        # Scale to actual size
        x1 = char_x - char_width/2 + x1 * char_width
        y1 = char_y - char_height/2 + y1 * char_height
        x2 = char_x - char_width/2 + x2 * char_width
        y2 = char_y - char_height/2 + y2 * char_height
        
        # Create a rectangle for the line segment
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        if length > 0:
            # Normal vector (perpendicular to line)
            nx = -dy / length * char_width * line_thickness / 2
            ny = dx / length * char_width * line_thickness / 2
            
            # Four corners of the rectangle
            vertices = [
                (x1 - nx, y1 - ny),
                (x1 + nx, y1 + ny),
                (x2 + nx, y2 + ny),
                (x2 - nx, y2 - ny)
            ]
            
            polygons.append(Polygon(vertices))
    
    # Union all polygons into one shape
    if polygons:
        try:
            char_2d = unary_union(polygons)
            
            # Handle different geometry types
            if hasattr(char_2d, 'geoms'):
                # MultiPolygon - take the largest polygon
                largest_poly = max(char_2d.geoms, key=lambda p: p.area)
                char_2d = largest_poly
            
            # Ensure the polygon is valid
            if not char_2d.is_valid:
                char_2d = char_2d.buffer(0)  # Fix self-intersections
            
            # Simplify the polygon slightly to avoid numerical issues
            char_2d = char_2d.simplify(0.05, preserve_topology=True)
            
        except Exception as e:
            print(f"WARNING: Failed to create character shape: {e}")
            return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)
    else:
        # Fallback to rectangle
        return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)
    
    # Extrude to 3D
    try:
        if for_subtraction:
            # For embossing plate recesses, extrude downward from top surface
            extrude_height = height + 0.5  # Extra depth to ensure clean boolean
            char_prism = trimesh.creation.extrude_polygon(char_2d, height=extrude_height)
            
            # Ensure the mesh is valid
            if not char_prism.is_volume:
                char_prism.fix_normals()
                if not char_prism.is_volume:
                    print(f"WARNING: Character mesh is not a valid volume")
                    return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)
            
            # Position at the top surface of the card
            z_pos = settings.card_thickness - 0.1  # Start slightly above surface
            char_prism.apply_translation([0, 0, z_pos])
        else:
            # For raised characters (if needed in future)
            char_prism = trimesh.creation.extrude_polygon(char_2d, height=height)
            
            # Position on top of the card base
            z_pos = settings.card_thickness
            char_prism.apply_translation([0, 0, z_pos])
    except Exception as e:
        print(f"WARNING: Failed to extrude character shape: {e}")
        return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)
    
    return char_prism


def create_positive_plate_mesh(lines, grade="g1", settings=None, original_lines=None):
    """
    Create a standard braille mesh (positive plate with raised dots).
    Lines are processed in top-down order.
    
    Args:
        lines: List of 4 text lines (braille Unicode)
        grade: "g1" for Grade 1 or "g2" for Grade 2
        settings: A CardSettings object with all dimensional parameters.
        original_lines: List of 4 original text lines (before braille conversion) for character indicators
    """
    if settings is None:
        settings = CardSettings()

    grade_name = f"Grade {grade.upper()}" if grade in ["g1", "g2"] else "Grade 1"
    print(f"Creating positive plate mesh with {grade_name} characters")
    print(f"Grid: {settings.grid_columns} columns × {settings.grid_rows} rows")
    print(f"Centered margins: L/R={settings.left_margin:.2f}mm, T/B={settings.top_margin:.2f}mm")
    print(f"Spacing: Cell-to-cell {settings.cell_spacing}mm, Line-to-line {settings.line_spacing}mm, Dot-to-dot {settings.dot_spacing}mm")
    
    # Create card base
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width/2, settings.card_height/2, settings.card_thickness/2))
    
    meshes = [base]
    marker_meshes = []  # Store markers separately for subtraction
    
    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]] # Map dot index (0-5) to [row, col]

    # Add triangle markers and end line markers for ALL rows (not just those with content)
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Add triangle marker at the first cell position (column 0)
        # Calculate X position for the first column
        x_pos = settings.left_margin + settings.braille_x_adjust
        
        # Create triangle marker for this row (recessed for embossing plate)
        triangle_mesh = create_card_triangle_marker_3d(x_pos, y_pos, settings, height=0.4, for_subtraction=True)
        marker_meshes.append(triangle_mesh)
        
        # Add end of row line marker at the last cell position (grid_columns - 1)
        # Calculate X position for the last column
        x_pos_end = settings.left_margin + ((settings.grid_columns - 1) * settings.cell_spacing) + settings.braille_x_adjust
        
        # Determine which character to use for end-of-row indicator
        if original_lines and row_num < len(original_lines):
            original_text = original_lines[row_num].strip()
            if original_text:
                # Get the first character (letter or number)
                first_char = original_text[0]
                if first_char.isalpha() or first_char.isdigit():
                    # Create character shape for end-of-row indicator (0.6mm deep as requested)
                    line_end_mesh = create_character_shape_3d(first_char, x_pos_end, y_pos, settings, height=0.6, for_subtraction=True)
                else:
                    # Fall back to rectangle for non-alphanumeric first characters
                    line_end_mesh = create_card_line_end_marker_3d(x_pos_end, y_pos, settings, height=0.5, for_subtraction=True)
            else:
                # Empty line, use rectangle
                line_end_mesh = create_card_line_end_marker_3d(x_pos_end, y_pos, settings, height=0.5, for_subtraction=True)
        else:
            # No original text provided, use rectangle as fallback
            line_end_mesh = create_card_line_end_marker_3d(x_pos_end, y_pos, settings, height=0.5, for_subtraction=True)
        
        marker_meshes.append(line_end_mesh)
    
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
        
        # Check if braille text exceeds grid capacity (accounting for both markers taking columns)
        available_columns = settings.grid_columns - 2  # Two less due to triangle and line end markers
        if len(braille_text) > available_columns:
            error_msg = f"Error: Line {row_num + 1} contains {len(braille_text)} braille cells, which exceeds the maximum of {available_columns} cells (grid has {settings.grid_columns} total cells with 2 reserved for row indicators)"
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Calculate Y position for this row (top-down)
        y_pos = settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process each braille character in the line
        for col_num, braille_char in enumerate(braille_text):
            if col_num >= available_columns:
                break
                
            dots = braille_to_dots(braille_char)
            
            # Calculate X position for this column (shifted by one cell due to triangle marker)
            x_pos = settings.left_margin + ((col_num + 1) * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create dots for this cell
            for i, dot_val in enumerate(dots):
                if dot_val == 1:
                    dot_pos = dot_positions[i]
                    dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                    dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                    z = settings.card_thickness + settings.emboss_dot_height / 2
                    
                    dot_mesh = create_braille_dot(dot_x, dot_y, z, settings)
                    meshes.append(dot_mesh)
    
    print(f"Created positive plate with {len(meshes)-1} cone-shaped dots, {settings.grid_rows} triangle markers, and {settings.grid_rows} line end markers")
    
    # Combine all positive meshes (base + dots)
    combined_mesh = trimesh.util.concatenate(meshes)
    
    # Subtract marker recesses from the combined mesh
    if marker_meshes:
        try:
            # Union all markers for efficient boolean operation
            if len(marker_meshes) == 1:
                union_markers = marker_meshes[0]
            else:
                union_markers = trimesh.boolean.union(marker_meshes, engine='manifold')
            
            print(f"DEBUG: Subtracting {len(marker_meshes)} marker recesses from embossing plate...")
            # Subtract markers to create recesses
            combined_mesh = trimesh.boolean.difference([combined_mesh, union_markers], engine='manifold')
            print(f"DEBUG: Marker subtraction successful")
        except Exception as e:
            print(f"WARNING: Could not create marker recesses with manifold engine: {e}")
            # Try fallback with default engine
            try:
                print("DEBUG: Trying marker subtraction with default engine...")
                if len(marker_meshes) == 1:
                    union_markers = marker_meshes[0]
                else:
                    union_markers = trimesh.boolean.union(marker_meshes)
                combined_mesh = trimesh.boolean.difference([combined_mesh, union_markers])
                print("DEBUG: Marker subtraction successful with default engine")
            except Exception as e2:
                print(f"ERROR: Marker subtraction failed with all engines: {e2}")
                print("Returning embossing plate without marker recesses")
    
    return combined_mesh

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
                
            # Calculate Y position for this row (same as embossing plate, using safe margin)
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

def layout_cylindrical_cells(braille_lines, settings: CardSettings, cylinder_diameter_mm: float, cylinder_height_mm: float):
    """
    Calculate positions for braille cells on a cylinder surface.
    Returns a list of (braille_char, x_theta, y_z) tuples where:
    - x_theta is the position along the circumference (will be converted to angle)
    - y_z is the vertical position on the cylinder
    """
    cells = []
    radius = cylinder_diameter_mm / 2
    circumference = np.pi * cylinder_diameter_mm
    
    # Use grid_columns from settings instead of calculating based on circumference
    cells_per_row = settings.grid_columns
    
    # Calculate the total grid width (same as card)
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    
    # Convert grid width to angular width
    grid_angle = grid_width / radius
    
    # Center the grid around the cylinder (calculate left margin angle)
    # The grid should be centered, so start angle is -grid_angle/2
    start_angle = -grid_angle / 2
    
    # Convert cell_spacing from linear to angular
    cell_spacing_angle = settings.cell_spacing / radius
    
    # Calculate row height (same as card - vertical spacing doesn't change)
    row_height = settings.line_spacing
    
    # Start from top of cylinder (using safe margin = ½ cell spacing)
    current_y = cylinder_height_mm - settings.top_margin
    
    # Process up to grid_rows lines
    for row_num in range(min(settings.grid_rows, len(braille_lines))):
        line = braille_lines[row_num].strip()
        if not line:
            continue
            
        # Check if input contains proper braille Unicode
        has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line)
        if not has_braille_chars:
            continue
        
        # Calculate Y position for this row (same as card)
        y_pos = cylinder_height_mm - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process each character up to grid_columns-2 (two less due to triangle and line end markers)
        for col_num, braille_char in enumerate(line[:settings.grid_columns-2]):
            # Calculate angular position for this column (shifted by one cell)
            angle = start_angle + ((col_num + 1) * cell_spacing_angle)
            x_pos = angle * radius  # Convert to arc length for compatibility
            cells.append((braille_char, x_pos, y_pos))
    
    return cells, cells_per_row

def cylindrical_transform(x, y, z, cylinder_diameter_mm, seam_offset_deg=0):
    """
    Transform planar coordinates to cylindrical coordinates.
    x -> theta (angle around cylinder)
    y -> z (height on cylinder)
    z -> radial offset from cylinder surface
    """
    radius = cylinder_diameter_mm / 2
    circumference = np.pi * cylinder_diameter_mm
    
    # Convert x position to angle
    theta = (x / circumference) * 2 * np.pi + np.radians(seam_offset_deg)
    
    # Calculate cylindrical coordinates
    cyl_x = radius * np.cos(theta)
    cyl_y = radius * np.sin(theta)
    cyl_z = y
    
    # Apply radial offset (for dot height)
    cyl_x += z * np.cos(theta)
    cyl_y += z * np.sin(theta)
    
    return cyl_x, cyl_y, cyl_z

def create_cylinder_shell(diameter_mm, height_mm, polygonal_cutout_radius_mm):
    """
    Create a cylinder with a 12-point polygonal cutout along its length.
    
    Args:
        diameter_mm: Outer diameter of the cylinder
        height_mm: Height of the cylinder
        polygonal_cutout_radius_mm: Inscribed radius of the 12-point polygonal cutout
    """
    outer_radius = diameter_mm / 2
    
    # Create the main solid cylinder
    main_cylinder = trimesh.creation.cylinder(radius=outer_radius, height=height_mm, sections=64)
    
    # If no cutout is specified, return the solid cylinder
    if polygonal_cutout_radius_mm <= 0:
        return main_cylinder
    
    # Create a 12-point polygonal prism for the cutout
    # The prism extends the full height of the cylinder
    # Calculate the circumscribed radius from the inscribed radius
    # For a regular 12-gon: circumscribed_radius = inscribed_radius / cos(15°)
    # cos(15°) = cos(π/12)
    circumscribed_radius = polygonal_cutout_radius_mm / np.cos(np.pi / 12)
    
    # Create the 12-point polygon vertices
    angles = np.linspace(0, 2*np.pi, 12, endpoint=False)
    vertices_2d = []
    for angle in angles:
        x = circumscribed_radius * np.cos(angle)
        y = circumscribed_radius * np.sin(angle)
        vertices_2d.append([x, y])
    
    # Create the polygonal prism by extruding the polygon along the Z-axis
    # The prism should be slightly longer than the cylinder to ensure complete cutting
    prism_height = height_mm + 2.0  # Add 1mm on each end
    
    # Create the polygonal prism using trimesh
    # We'll create it by making a 3D mesh from the 2D polygon
    from trimesh.creation import extrude_polygon
    
    # Create the polygon using shapely
    from shapely.geometry import Polygon as ShapelyPolygon
    polygon = ShapelyPolygon(vertices_2d)
    
    # Extrude the polygon to create the prism
    cutout_prism = extrude_polygon(polygon, height=prism_height)
    
    # Center the prism vertically at origin (extrude_polygon creates it from Z=0 to Z=height)
    prism_center_z = cutout_prism.bounds[1][2] / 2.0  # Get center of prism's Z bounds
    cutout_prism.apply_translation([0, 0, -prism_center_z])
    
    # Debug: Print prism and cylinder dimensions
    print(f"DEBUG: Cylinder height: {height_mm}mm, extends from Z={-height_mm/2:.2f} to Z={height_mm/2:.2f}")
    print(f"DEBUG: Prism height: {prism_height}mm, after centering extends from Z={-prism_height/2:.2f} to Z={prism_height/2:.2f}")
    print(f"DEBUG: Prism bounds after centering: {cutout_prism.bounds}")
    
    # Center the prism at the origin - no translation needed
    # Both the cylinder and prism are already centered at origin
    # The prism extends from -prism_height/2 to +prism_height/2
    # The cylinder extends from -height_mm/2 to +height_mm/2
    # Since prism_height > height_mm, the prism will cut through the entire cylinder
    
    # Perform boolean subtraction to create the cutout
    try:
        result = trimesh.boolean.difference([main_cylinder, cutout_prism], engine='manifold')
        if result.is_watertight:
            return result
    except Exception as e:
        print(f"Warning: Boolean operation failed with manifold engine: {e}")
    
    # Fallback: try with default engine
    try:
        result = trimesh.boolean.difference([main_cylinder, cutout_prism])
        if result.is_watertight:
            return result
    except Exception as e:
        print(f"Warning: Boolean operation failed with default engine: {e}")
    
    # Final fallback: return the original cylinder if all boolean operations fail
    print("Warning: Could not create polygonal cutout, returning solid cylinder")
    return main_cylinder

def create_cylinder_triangle_marker(x_arc, y_local, settings: CardSettings, cylinder_diameter_mm, seam_offset_deg=0, height_mm=0.4, for_subtraction=True):
    """
    Create a triangular prism for cylinder surface marking.
    
    Args:
        x_arc: Arc length position along circumference (same units as mm on the card)
        y_local: Z position relative to cylinder center (card Y minus height/2)
        settings: CardSettings object
        cylinder_diameter_mm: Cylinder diameter
        seam_offset_deg: Rotation offset for seam
        height_mm: Depth/height of the triangle marker (default 0.4mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses
    """
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm
    
    # Angle around cylinder for planar x position
    theta = (x_arc / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)
    
    # Local orthonormal frame at theta
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])      # radial outward
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])     # tangential
    z_hat = np.array([0.0, 0.0, 1.0])                          # cylinder axis
    
    # Triangle dimensions - standard guide triangle shape
    base_height = 2.0 * settings.dot_spacing  # Vertical extent
    triangle_width = settings.dot_spacing     # Horizontal extent (pointing right in tangent direction)
    
    # Build 2D triangle in local tangent (X=t) and vertical (Y=z) plane
    # Vertices: base on left, apex pointing right
    from shapely.geometry import Polygon as ShapelyPolygon
    tri_2d = ShapelyPolygon([
        (0.0, -settings.dot_spacing),    # Bottom of base
        (0.0,  settings.dot_spacing),    # Top of base
        (triangle_width, 0.0)            # Apex (pointing tangentially)
    ])
    
    # For subtraction tool, we need to extend beyond the surface
    if for_subtraction:
        # Extrude to create cutting tool that extends from outside to inside the cylinder
        extrude_height = height_mm + 1.0  # Total extrusion depth
        tri_prism_local = trimesh.creation.extrude_polygon(tri_2d, height=extrude_height)
        
        # The prism is created with Z from 0 to extrude_height
        # We need to center it so it extends from -0.5 to (height_mm + 0.5)
        tri_prism_local.apply_translation([0, 0, -0.5])
        
        # Build transform: map local coords to cylinder coords
        T = np.eye(4)
        T[:3, 0] = t_hat   # X axis (tangential)
        T[:3, 1] = z_hat   # Y axis (vertical)
        T[:3, 2] = r_hat   # Z axis (radial outward)
        
        # Position so the prism starts outside the cylinder and cuts inward
        # The prism's Z=0 should be at radius (cylinder surface)
        center_pos = r_hat * radius + z_hat * y_local
        T[:3, 3] = center_pos
        
        # Apply the transform
        tri_prism_local.apply_transform(T)
        
        # Debug output - only print for first triangle to avoid spam
        if abs(y_local) < settings.line_spacing:  # First row
            print(f"DEBUG: Triangle at theta={np.degrees(theta):.1f}°, y_local={y_local:.1f}mm")
            print(f"DEBUG: Triangle bounds after transform: {tri_prism_local.bounds}")
            print(f"DEBUG: Cylinder radius: {radius}mm")
    else:
        # For direct recessed triangle (not used currently)
        tri_prism_local = trimesh.creation.extrude_polygon(tri_2d, height=height_mm)
        
        # Build transform for inward extrusion
        T = np.eye(4)
        T[:3, 0] = t_hat   # X axis
        T[:3, 1] = z_hat   # Y axis
        T[:3, 2] = -r_hat  # Z axis (inward)
        
        # Position recessed into surface
        center_pos = r_hat * (radius - height_mm / 2.0) + z_hat * y_local
        T[:3, 3] = center_pos
        
        tri_prism_local.apply_transform(T)
    
    return tri_prism_local


def create_cylinder_line_end_marker(x_arc, y_local, settings: CardSettings, cylinder_diameter_mm, seam_offset_deg=0, height_mm=0.5, for_subtraction=True):
    """
    Create a line (rectangular prism) for end of row marking on cylinder surface.
    
    Args:
        x_arc: Arc length position along circumference (same units as mm on the card)
        y_local: Z position relative to cylinder center (card Y minus height/2)
        settings: CardSettings object
        cylinder_diameter_mm: Cylinder diameter
        seam_offset_deg: Rotation offset for seam
        height_mm: Depth/height of the line marker (default 0.5mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses
    """
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm
    
    # Angle around cylinder for planar x position
    theta = (x_arc / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)
    
    # Local orthonormal frame at theta
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])      # radial outward
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])     # tangential
    z_hat = np.array([0.0, 0.0, 1.0])                          # cylinder axis
    
    # Line dimensions - vertical line at end of row
    line_height = 2.0 * settings.dot_spacing  # Vertical extent (same as cell height)
    line_width = settings.dot_spacing         # Horizontal extent in tangent direction
    
    # Build 2D rectangle in local tangent (X=t) and vertical (Y=z) plane
    # Rectangle centered at origin, extending in both directions
    from shapely.geometry import Polygon as ShapelyPolygon
    line_2d = ShapelyPolygon([
        (-line_width/2, -settings.dot_spacing),  # Bottom left
        (line_width/2, -settings.dot_spacing),   # Bottom right
        (line_width/2, settings.dot_spacing),    # Top right
        (-line_width/2, settings.dot_spacing)    # Top left
    ])
    
    # For subtraction tool, we need to extend beyond the surface
    if for_subtraction:
        # Extrude to create cutting tool that extends from outside to inside the cylinder
        extrude_height = height_mm + 1.0  # Total extrusion depth
        line_prism_local = trimesh.creation.extrude_polygon(line_2d, height=extrude_height)
        
        # The prism is created with Z from 0 to extrude_height
        # We need to center it so it extends from -0.5 to (height_mm + 0.5)
        line_prism_local.apply_translation([0, 0, -0.5])
        
        # Build transform: map local coords to cylinder coords
        T = np.eye(4)
        T[:3, 0] = t_hat   # X axis (tangential)
        T[:3, 1] = z_hat   # Y axis (vertical)
        T[:3, 2] = r_hat   # Z axis (radial outward)
        
        # Position so the prism starts outside the cylinder and cuts inward
        # The prism's Z=0 should be at radius (cylinder surface)
        center_pos = r_hat * radius + z_hat * y_local
        T[:3, 3] = center_pos
        
        # Apply the transform
        line_prism_local.apply_transform(T)
    else:
        # For direct recessed line (not used currently)
        line_prism_local = trimesh.creation.extrude_polygon(line_2d, height=height_mm)
        
        # Build transform for inward extrusion
        T = np.eye(4)
        T[:3, 0] = t_hat   # X axis
        T[:3, 1] = z_hat   # Y axis
        T[:3, 2] = -r_hat  # Z axis (inward)
        
        # Position recessed into surface
        center_pos = r_hat * (radius - height_mm / 2.0) + z_hat * y_local
        T[:3, 3] = center_pos
        
        line_prism_local.apply_transform(T)
    
    return line_prism_local


def create_cylinder_character_shape(character, x_arc, y_local, settings: CardSettings, cylinder_diameter_mm, seam_offset_deg=0, height_mm=0.6, for_subtraction=True):
    """
    Create a 3D character shape (capital letter A-Z or number 0-9) for end of row marking on cylinder surface.
    
    Args:
        character: Single character (A-Z or 0-9)
        x_arc: Arc length position along circumference (same units as mm on the card)
        y_local: Z position relative to cylinder center (card Y minus height/2)
        settings: CardSettings object
        cylinder_diameter_mm: Cylinder diameter
        seam_offset_deg: Seam rotation offset in degrees
        height_mm: Depth of the character recess (default 0.6mm as requested)
        for_subtraction: If True, creates a tool for boolean subtraction
    
    Returns:
        Trimesh object representing the 3D character marker transformed to cylinder
    """
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm
    
    # Angle around cylinder for planar x position
    theta = (x_arc / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)
    
    # Local orthonormal frame at theta
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])      # radial outward
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])     # tangential
    z_hat = np.array([0.0, 0.0, 1.0])                          # cylinder axis
    
    # Define character size based on braille cell dimensions (with 1mm increase)
    char_height = 2 * settings.dot_spacing + 1.0  # Increased by 1mm as requested
    char_width = settings.dot_spacing * 0.8 + 1.0  # Increased by 1mm as requested
    
    # Character definitions (same as card version)
    char_definitions = {
        'A': [
            (0.2, 0, 0.5, 1), (0.5, 1, 0.8, 0),  # Two sides of triangle
            (0.35, 0.5, 0.65, 0.5)  # Horizontal bar
        ],
        'B': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65), (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.2, 0.5),  # Top curve
            (0.2, 0.5, 0.7, 0.5), (0.7, 0.5, 0.8, 0.35), (0.8, 0.35, 0.8, 0.15), (0.8, 0.15, 0.7, 0), (0.7, 0, 0.2, 0)  # Bottom curve
        ],
        'C': [
            (0.8, 0.8, 0.7, 0.9), (0.7, 0.9, 0.5, 1), (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7),
            (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.2)
        ],
        'D': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.6, 1), (0.6, 1, 0.8, 0.8), (0.8, 0.8, 0.8, 0.2), (0.8, 0.2, 0.6, 0), (0.6, 0, 0.2, 0)
        ],
        'E': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.2, 0.5, 0.7, 0.5),  # Middle horizontal
            (0.2, 0, 0.8, 0)  # Bottom horizontal
        ],
        'F': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.2, 0.5, 0.7, 0.5)  # Middle horizontal
        ],
        'G': [
            (0.8, 0.8, 0.7, 0.9), (0.7, 0.9, 0.5, 1), (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7),
            (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.2),
            (0.8, 0.2, 0.8, 0.5), (0.8, 0.5, 0.5, 0.5)
        ],
        'H': [
            (0.2, 0, 0.2, 1),  # Left vertical
            (0.8, 0, 0.8, 1),  # Right vertical
            (0.2, 0.5, 0.8, 0.5)  # Horizontal bar
        ],
        'I': [
            (0.3, 1, 0.7, 1),  # Top horizontal
            (0.5, 1, 0.5, 0),  # Vertical
            (0.3, 0, 0.7, 0)  # Bottom horizontal
        ],
        'J': [
            (0.4, 1, 0.8, 1),  # Top horizontal
            (0.6, 1, 0.6, 0.2),  # Vertical
            (0.6, 0.2, 0.5, 0.1), (0.5, 0.1, 0.3, 0), (0.3, 0, 0.2, 0.1), (0.2, 0.1, 0.2, 0.3)
        ],
        'K': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.8, 1, 0.2, 0.5),  # Upper diagonal
            (0.2, 0.5, 0.8, 0)  # Lower diagonal
        ],
        'L': [
            (0.2, 1, 0.2, 0),  # Vertical line
            (0.2, 0, 0.8, 0)  # Bottom horizontal
        ],
        'M': [
            (0.2, 0, 0.2, 1),  # Left vertical
            (0.2, 1, 0.5, 0.6),  # Left diagonal
            (0.5, 0.6, 0.8, 1),  # Right diagonal
            (0.8, 1, 0.8, 0)  # Right vertical
        ],
        'N': [
            (0.2, 0, 0.2, 1),  # Left vertical
            (0.2, 1, 0.8, 0),  # Diagonal
            (0.8, 0, 0.8, 1)  # Right vertical
        ],
        'O': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1),
            (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 0.7),
            (0.8, 0.7, 0.7, 0.9), (0.7, 0.9, 0.5, 1)
        ],
        'P': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65), (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.2, 0.5)
        ],
        'Q': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1),
            (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 0.7),
            (0.8, 0.7, 0.7, 0.9), (0.7, 0.9, 0.5, 1),
            (0.6, 0.2, 0.8, 0)  # Tail
        ],
        'R': [
            (0.2, 0, 0.2, 1),  # Vertical line
            (0.2, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65), (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.2, 0.5),
            (0.2, 0.5, 0.8, 0)  # Diagonal leg
        ],
        'S': [
            (0.8, 0.85, 0.7, 1), (0.7, 1, 0.3, 1), (0.3, 1, 0.2, 0.85), (0.2, 0.85, 0.2, 0.65),
            (0.2, 0.65, 0.3, 0.5), (0.3, 0.5, 0.7, 0.5), (0.7, 0.5, 0.8, 0.35), (0.8, 0.35, 0.8, 0.15),
            (0.8, 0.15, 0.7, 0), (0.7, 0, 0.3, 0), (0.3, 0, 0.2, 0.15)
        ],
        'T': [
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.5, 1, 0.5, 0)  # Vertical
        ],
        'U': [
            (0.2, 1, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 1)
        ],
        'V': [
            (0.2, 1, 0.5, 0),  # Left diagonal
            (0.5, 0, 0.8, 1)  # Right diagonal
        ],
        'W': [
            (0.1, 1, 0.3, 0),  # First diagonal
            (0.3, 0, 0.5, 0.4),  # Second diagonal up
            (0.5, 0.4, 0.7, 0),  # Third diagonal down
            (0.7, 0, 0.9, 1)  # Fourth diagonal
        ],
        'X': [
            (0.2, 1, 0.8, 0),  # Diagonal 1
            (0.2, 0, 0.8, 1)  # Diagonal 2
        ],
        'Y': [
            (0.2, 1, 0.5, 0.5),  # Left diagonal
            (0.8, 1, 0.5, 0.5),  # Right diagonal
            (0.5, 0.5, 0.5, 0)  # Vertical
        ],
        'Z': [
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.8, 1, 0.2, 0),  # Diagonal
            (0.2, 0, 0.8, 0)  # Bottom horizontal
        ],
        '0': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3), (0.2, 0.3, 0.3, 0.1),
            (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3), (0.8, 0.3, 0.8, 0.7),
            (0.8, 0.7, 0.7, 0.9), (0.7, 0.9, 0.5, 1)
        ],
        '1': [
            (0.3, 0.8, 0.5, 1),  # Diagonal top
            (0.5, 1, 0.5, 0),  # Vertical
            (0.3, 0, 0.7, 0)  # Bottom horizontal
        ],
        '2': [
            (0.2, 0.8, 0.3, 0.9), (0.3, 0.9, 0.5, 1), (0.5, 1, 0.7, 0.9), (0.7, 0.9, 0.8, 0.8),
            (0.8, 0.8, 0.8, 0.6), (0.8, 0.6, 0.7, 0.5), (0.7, 0.5, 0.2, 0), (0.2, 0, 0.8, 0)
        ],
        '3': [
            (0.2, 0.85, 0.3, 1), (0.3, 1, 0.7, 1), (0.7, 1, 0.8, 0.85), (0.8, 0.85, 0.8, 0.65),
            (0.8, 0.65, 0.7, 0.5), (0.7, 0.5, 0.4, 0.5),
            (0.7, 0.5, 0.8, 0.35), (0.8, 0.35, 0.8, 0.15), (0.8, 0.15, 0.7, 0), (0.7, 0, 0.3, 0), (0.3, 0, 0.2, 0.15)
        ],
        '4': [
            (0.7, 0, 0.7, 1),  # Vertical line
            (0.2, 0.6, 0.2, 1), (0.2, 0.6, 0.8, 0.6)  # Horizontal and left part
        ],
        '5': [
            (0.8, 1, 0.2, 1),  # Top horizontal
            (0.2, 1, 0.2, 0.6),  # Vertical down
            (0.2, 0.6, 0.7, 0.6), (0.7, 0.6, 0.8, 0.45), (0.8, 0.45, 0.8, 0.15), (0.8, 0.15, 0.7, 0), (0.7, 0, 0.3, 0), (0.3, 0, 0.2, 0.15)
        ],
        '6': [
            (0.7, 0.9, 0.5, 1), (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.7), (0.2, 0.7, 0.2, 0.3),
            (0.2, 0.3, 0.3, 0.1), (0.3, 0.1, 0.5, 0), (0.5, 0, 0.7, 0.1), (0.7, 0.1, 0.8, 0.3),
            (0.8, 0.3, 0.8, 0.5), (0.8, 0.5, 0.7, 0.6), (0.7, 0.6, 0.3, 0.6), (0.3, 0.6, 0.2, 0.5)
        ],
        '7': [
            (0.2, 1, 0.8, 1),  # Top horizontal
            (0.8, 1, 0.4, 0)  # Diagonal
        ],
        '8': [
            (0.5, 1, 0.3, 0.9), (0.3, 0.9, 0.2, 0.75), (0.2, 0.75, 0.3, 0.6), (0.3, 0.6, 0.5, 0.5),
            (0.5, 0.5, 0.7, 0.4), (0.7, 0.4, 0.8, 0.25), (0.8, 0.25, 0.7, 0.1), (0.7, 0.1, 0.5, 0),
            (0.5, 0, 0.3, 0.1), (0.3, 0.1, 0.2, 0.25), (0.2, 0.25, 0.3, 0.4), (0.3, 0.4, 0.5, 0.5),
            (0.5, 0.5, 0.7, 0.6), (0.7, 0.6, 0.8, 0.75), (0.8, 0.75, 0.7, 0.9), (0.7, 0.9, 0.5, 1)
        ],
        '9': [
            (0.8, 0.5, 0.7, 0.4), (0.7, 0.4, 0.5, 0.4), (0.5, 0.4, 0.3, 0.5), (0.3, 0.5, 0.2, 0.7),
            (0.2, 0.7, 0.2, 0.85), (0.2, 0.85, 0.3, 1), (0.3, 1, 0.7, 1), (0.7, 1, 0.8, 0.85),
            (0.8, 0.85, 0.8, 0.3), (0.8, 0.3, 0.7, 0.1), (0.7, 0.1, 0.5, 0), (0.5, 0, 0.3, 0.1)
        ]
    }
    
    # Get the character definition
    char_upper = character.upper()
    if char_upper not in char_definitions:
        # Fall back to rectangle for undefined characters
        return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
    
    line_segments = char_definitions[char_upper]
    
    # Create polygon paths for the character
    # Convert line segments to polygons with thickness
    line_thickness = 0.20  # Increased thickness for bold effect
    polygons = []
    
    for seg in line_segments:
        x1, y1, x2, y2 = seg
        
        # Scale to actual size (centered at origin)
        x1 = (x1 - 0.5) * char_width
        y1 = (y1 - 0.5) * char_height
        x2 = (x2 - 0.5) * char_width
        y2 = (y2 - 0.5) * char_height
        
        # Create a rectangle for the line segment
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        if length > 0:
            # Normal vector (perpendicular to line)
            nx = -dy / length * char_width * line_thickness / 2
            ny = dx / length * char_width * line_thickness / 2
            
            # Four corners of the rectangle
            vertices = [
                (x1 - nx, y1 - ny),
                (x1 + nx, y1 + ny),
                (x2 + nx, y2 + ny),
                (x2 - nx, y2 - ny)
            ]
            
            polygons.append(Polygon(vertices))
    
    # Union all polygons into one shape
    if polygons:
        try:
            char_2d = unary_union(polygons)
            
            # Handle different geometry types
            if hasattr(char_2d, 'geoms'):
                # MultiPolygon - take the largest polygon
                largest_poly = max(char_2d.geoms, key=lambda p: p.area)
                char_2d = largest_poly
            
            # Ensure the polygon is valid
            if not char_2d.is_valid:
                char_2d = char_2d.buffer(0)  # Fix self-intersections
            
            # Simplify the polygon slightly to avoid numerical issues
            char_2d = char_2d.simplify(0.05, preserve_topology=True)
            
        except Exception as e:
            print(f"WARNING: Failed to create character shape: {e}")
            return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
    else:
        # Fallback to rectangle
        return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
    
    # For subtraction tool, we need to extend beyond the surface
    try:
        if for_subtraction:
            # Extrude to create cutting tool that extends from outside to inside the cylinder
            extrude_height = height_mm + 1.0  # Total extrusion depth
            char_prism_local = trimesh.creation.extrude_polygon(char_2d, height=extrude_height)
            
            # Ensure the mesh is valid
            if not char_prism_local.is_volume:
                char_prism_local.fix_normals()
                if not char_prism_local.is_volume:
                    print(f"WARNING: Character mesh is not a valid volume")
                    return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
            
            # The prism is created with Z from 0 to extrude_height
            # We need to center it so it extends from -0.5 to (height_mm + 0.5)
            char_prism_local.apply_translation([0, 0, -0.5])
            
            # Build transform: map local coords to cylinder coords
            T = np.eye(4)
            T[:3, 0] = t_hat   # X axis (tangential)
            T[:3, 1] = z_hat   # Y axis (vertical)
            T[:3, 2] = r_hat   # Z axis (radial outward)
            
            # Position so the prism starts outside the cylinder and cuts inward
            # The prism's Z=0 should be at radius (cylinder surface)
            center_pos = r_hat * radius + z_hat * y_local
            T[:3, 3] = center_pos
            
            # Apply the transform
            char_prism_local.apply_transform(T)
        else:
            # For direct recessed character (not used currently)
            char_prism_local = trimesh.creation.extrude_polygon(char_2d, height=height_mm)
            
            # Build transform for inward extrusion
            T = np.eye(4)
            T[:3, 0] = t_hat   # X axis
            T[:3, 1] = z_hat   # Y axis
            T[:3, 2] = -r_hat  # Z axis (inward)
            
            # Position recessed into surface
            center_pos = r_hat * (radius - height_mm / 2.0) + z_hat * y_local
            T[:3, 3] = center_pos
            
            char_prism_local.apply_transform(T)
    except Exception as e:
        print(f"WARNING: Failed to extrude character shape: {e}")
        return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
    
    return char_prism_local


def create_cylinder_braille_dot(x, y, z, settings: CardSettings, cylinder_diameter_mm, seam_offset_deg=0):
    """
    Create a braille dot transformed to cylinder surface.
    """
    # Create the dot at origin (axis along +Z)
    dot = create_braille_dot(0, 0, 0, settings)

    # Cylinder geometry
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm

    # Angle around cylinder for planar x-position
    theta = (x / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)

    # Unit vectors at this theta
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])
    t_axis = np.array([-np.sin(theta), np.cos(theta), 0.0])  # tangent axis used for rotation

    # Rotate dot so its +Z axis aligns with radial outward direction (r_hat)
    rot_to_radial = trimesh.transformations.rotation_matrix(np.pi / 2.0, t_axis)
    dot.apply_transform(rot_to_radial)

    # Place the dot so its base is flush with the cylinder outer surface
    dot_height = settings.emboss_dot_height
    center_radial_distance = radius + (dot_height / 2.0)
    center_position = r_hat * center_radial_distance + np.array([0.0, 0.0, y])
    dot.apply_translation(center_position)

    return dot

def generate_cylinder_stl(lines, grade="g1", settings=None, cylinder_params=None, original_lines=None):
    """
    Generate a cylinder-shaped braille card with dots on the outer surface.
    
    Args:
        lines: List of text lines (braille Unicode)
        grade: Braille grade
        settings: CardSettings object
        cylinder_params: Dictionary with cylinder-specific parameters:
            - diameter_mm: Cylinder diameter
            - height_mm: Cylinder height  
            - polygonal_cutout_radius_mm: Inscribed radius of 12-point polygonal cutout (0 = no cutout)
            - seam_offset_deg: Rotation offset for seam
        original_lines: List of original text lines (before braille conversion) for character indicators
    """
    if settings is None:
        settings = CardSettings()
    
    if cylinder_params is None:
        cylinder_params = {
            'diameter_mm': 30,
            'height_mm': settings.card_height,
            'polygonal_cutout_radius_mm': 13,
            'seam_offset_deg': 0
        }
    
    diameter = float(cylinder_params.get('diameter_mm', 30))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    seam_offset = float(cylinder_params.get('seam_offset_deg', 0))
    
    print(f"Creating cylinder mesh - Diameter: {diameter}mm, Height: {height}mm, Cutout Radius: {polygonal_cutout_radius}mm")
    
    # Print grid and angular spacing information
    radius = diameter / 2
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_angle_deg = np.degrees(grid_width / radius)
    cell_spacing_angle_deg = np.degrees(settings.cell_spacing / radius)
    dot_spacing_angle_deg = np.degrees(settings.dot_spacing / radius)
    
    print(f"Grid configuration:")
    print(f"  - Grid: {settings.grid_columns} columns × {settings.grid_rows} rows")
    print(f"  - Grid width: {grid_width:.1f}mm → {grid_angle_deg:.1f}° arc on cylinder")
    print(f"Angular spacing calculations:")
    print(f"  - Cell spacing: {settings.cell_spacing}mm → {cell_spacing_angle_deg:.2f}° on cylinder")
    print(f"  - Dot spacing: {settings.dot_spacing}mm → {dot_spacing_angle_deg:.2f}° on cylinder")
    
    # Create cylinder shell
    cylinder_shell = create_cylinder_shell(diameter, height, polygonal_cutout_radius)
    meshes = [cylinder_shell]
    
    # Layout braille cells on cylinder
    cells, cells_per_row = layout_cylindrical_cells(lines, settings, diameter, height)
    
    # Add triangle recess markers and end line markers for ALL rows (not just those with content)
    triangle_meshes = []
    line_end_meshes = []
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Calculate X position for triangle marker (at column 0 position)
        # The grid is centered, so start angle is -grid_angle/2
        grid_width = (settings.grid_columns - 1) * settings.cell_spacing
        grid_angle = grid_width / radius
        start_angle = -grid_angle / 2
        
        # Triangle goes at the first cell position (column 0)
        triangle_x = start_angle * radius
        
        # Create triangle marker for subtraction (will create recess)
        y_local = y_pos - (height / 2.0)
        triangle_mesh = create_cylinder_triangle_marker(
            triangle_x, y_local, settings, diameter, seam_offset, height_mm=0.4, for_subtraction=True
        )
        triangle_meshes.append(triangle_mesh)
        
        # Add end of row line marker at the last cell position (grid_columns - 1)
        # Calculate X position for the last column
        end_angle = start_angle + ((settings.grid_columns - 1) * settings.cell_spacing / radius)
        line_end_x = end_angle * radius
        
        # Determine which character to use for end-of-row indicator
        if original_lines and row_num < len(original_lines):
            original_text = original_lines[row_num].strip()
            if original_text:
                # Get the first character (letter or number)
                first_char = original_text[0]
                if first_char.isalpha() or first_char.isdigit():
                    # Create character shape for end-of-row indicator (0.6mm deep as requested)
                    line_end_mesh = create_cylinder_character_shape(
                        first_char, line_end_x, y_local, settings, diameter, seam_offset, height_mm=0.6, for_subtraction=True
                    )
                else:
                    # Fall back to rectangle for non-alphanumeric first characters
                    line_end_mesh = create_cylinder_line_end_marker(
                        line_end_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
                    )
            else:
                # Empty line, use rectangle
                line_end_mesh = create_cylinder_line_end_marker(
                    line_end_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
                )
        else:
            # No original text provided, use rectangle as fallback
            line_end_mesh = create_cylinder_line_end_marker(
                line_end_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
            )
        
        line_end_meshes.append(line_end_mesh)
    
    # Subtract triangle markers and line end markers to recess them into the surface
    print(f"DEBUG: Creating {len(triangle_meshes)} triangle recesses and {len(line_end_meshes)} line end recesses on emboss cylinder")
    
    # Combine all markers (triangles and line ends) for efficient boolean operations
    all_markers = triangle_meshes + line_end_meshes
    
    if all_markers:
        try:
            # Union all markers first
            if len(all_markers) == 1:
                union_markers = all_markers[0]
            else:
                union_markers = trimesh.boolean.union(all_markers, engine='manifold')
            
            print(f"DEBUG: Marker union successful, subtracting from cylinder shell...")
            # Subtract from shell to recess
            cylinder_shell = trimesh.boolean.difference([cylinder_shell, union_markers], engine='manifold')
            print(f"DEBUG: Marker subtraction successful")
        except Exception as e:
            print(f"ERROR: Could not create marker cutouts: {e}")
            # Try fallback with default engine
            try:
                print("DEBUG: Trying marker subtraction with default engine...")
                if len(all_markers) == 1:
                    union_markers = all_markers[0]
                else:
                    union_markers = trimesh.boolean.union(all_markers)
                cylinder_shell = trimesh.boolean.difference([cylinder_shell, union_markers])
                print("DEBUG: Marker subtraction successful with default engine")
            except Exception as e2:
                print(f"ERROR: Marker subtraction failed with all engines: {e2}")
    
    meshes = [cylinder_shell]
    
    # Check for overflow based on grid dimensions (accounting for both markers)
    total_cells_needed = sum(len(line.strip()) for line in lines if line.strip())
    total_cells_available = (settings.grid_columns - 2) * settings.grid_rows  # Two less columns due to triangles and line ends
    
    if total_cells_needed > total_cells_available:
        print(f"Warning: Text requires {total_cells_needed} cells but grid has {total_cells_available} cells ({settings.grid_columns-2}×{settings.grid_rows} after row markers)")
    
    # Check if grid wraps too far around cylinder
    if grid_angle_deg > 360:
        print(f"Warning: Grid width ({grid_angle_deg:.1f}°) exceeds cylinder circumference (360°)")
    
    # Convert dot spacing to angular measurements for cylinder
    radius = diameter / 2
    dot_spacing_angle = settings.dot_spacing / radius  # Convert linear to angular
    
    # Dot positioning with angular offsets for columns, linear for rows
    dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]  # Vertical stays linear
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Create dots for each cell
    for braille_char, cell_x, cell_y in cells:
        dots = braille_to_dots(braille_char)
        
        for i, dot_val in enumerate(dots):
            if dot_val == 1:
                dot_pos = dot_positions[i]
                # Use angular offset for horizontal spacing, converted back to arc length
                dot_x = cell_x + (dot_col_angle_offsets[dot_pos[1]] * radius)
                dot_y = cell_y + dot_row_offsets[dot_pos[0]]
                # Map absolute card Y to cylinder's local Z (centered at 0)
                dot_z_local = dot_y - (height / 2.0)
                z = polygonal_cutout_radius + settings.emboss_dot_height / 2  # unused in transform now
                
                dot_mesh = create_cylinder_braille_dot(dot_x, dot_z_local, z, settings, diameter, seam_offset)
                meshes.append(dot_mesh)
    
    print(f"Created cylinder with {len(meshes)-1} braille dots")
    
    # Combine all meshes
    final_mesh = trimesh.util.concatenate(meshes)
    
    # The cylinder is already created with vertical axis (along Z)
    # No rotation needed - it should stand upright
    # Just ensure the base is at Z=0
    min_z = final_mesh.bounds[0][2]
    final_mesh.apply_translation([0, 0, -min_z])
    
    return final_mesh

def generate_cylinder_counter_plate(lines, settings: CardSettings, cylinder_params=None):
    """
    Generate a cylinder-shaped counter plate with hemispherical recesses on the OUTER surface.
    Similar to the card counter plate, it creates recesses at ALL possible dot positions.
    
    Args:
        lines: List of text lines
        settings: CardSettings object
        cylinder_params: Dictionary with cylinder-specific parameters:
            - diameter_mm: Cylinder diameter
            - height_mm: Cylinder height  
            - polygonal_cutout_radius_mm: Inscribed radius of 12-point polygonal cutout (0 = no cutout)
            - seam_offset_deg: Rotation offset for seam
    """
    if cylinder_params is None:
        cylinder_params = {
            'diameter_mm': 30,
            'height_mm': settings.card_height,
            'polygonal_cutout_radius_mm': 13,
            'seam_offset_deg': 0
        }
    
    diameter = float(cylinder_params.get('diameter_mm', 30))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    seam_offset = float(cylinder_params.get('seam_offset_deg', 0))
    
    print(f"Creating cylinder counter plate - Diameter: {diameter}mm, Height: {height}mm, Cutout Radius: {polygonal_cutout_radius}mm")
    
    # Create cylinder shell
    cylinder_shell = create_cylinder_shell(diameter, height, polygonal_cutout_radius)
    
    # Use grid dimensions from settings (same as card)
    radius = diameter / 2
    circumference = np.pi * diameter
    
    # Calculate the total grid width (same as card)
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    
    # Convert grid width to angular width
    grid_angle = grid_width / radius
    
    # Center the grid around the cylinder (calculate start angle)
    start_angle = -grid_angle / 2
    
    # Convert cell_spacing from linear to angular
    cell_spacing_angle = settings.cell_spacing / radius
    
    # Use grid_rows from settings
    rows_on_cylinder = settings.grid_rows
    
    # Convert dot spacing to angular measurements
    dot_spacing_angle = settings.dot_spacing / radius
    
    # Dot positioning with angular offsets for columns, linear for rows
    dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]  # Vertical stays linear
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Create triangle marker recesses and end of row line recesses for ALL rows
    triangle_meshes = []
    line_end_meshes = []
    
    # Create triangles and line ends for ALL rows in the grid
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Add triangle marker at the first cell position (column 0)
        triangle_x = start_angle * radius
        
        # Create triangle marker for subtraction (will create recess)
        y_local = y_pos - (height / 2.0)
        triangle_mesh = create_cylinder_triangle_marker(
            triangle_x, y_local, settings, diameter, seam_offset, height_mm=0.4, for_subtraction=True
        )
        triangle_meshes.append(triangle_mesh)
        
        # Add end of row line marker at the last cell position (grid_columns - 1)
        # Calculate X position for the last column
        end_angle = start_angle + ((settings.grid_columns - 1) * cell_spacing_angle)
        line_end_x = end_angle * radius
        
        # Create line end marker for subtraction (will create recess)
        line_end_mesh = create_cylinder_line_end_marker(
            line_end_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
        )
        line_end_meshes.append(line_end_mesh)
    
    # Create spheres for ALL dot positions in ALL cells (universal counter plate)
    sphere_meshes = []
    
    # Process ALL cells in the grid (not just those with braille content)
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process ALL columns (minus two for triangle and line end marker spaces)
        for col_num in range(settings.grid_columns - 2):
            # Calculate cell position (shifted by one cell for triangle marker)
            cell_angle = start_angle + ((col_num + 1) * cell_spacing_angle)
            cell_x = cell_angle * radius  # Convert to arc length
            
            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                # Use angular offset for horizontal spacing, converted back to arc length
                dot_x = cell_x + (dot_col_angle_offsets[dot_pos[1]] * radius)
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create sphere with radius based on counter plate offset
                hemisphere_radius = (settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset) / 2
                sphere = trimesh.creation.icosphere(subdivisions=settings.hemisphere_subdivisions, radius=hemisphere_radius)
                
                # Ensure sphere is a valid volume
                if not sphere.is_volume:
                    sphere.fix_normals()
                
                # Transform to cylindrical coordinates on OUTER surface
                outer_radius = diameter / 2
                # Convert x position to angle
                theta = (dot_x / (np.pi * diameter)) * 2 * np.pi + np.radians(seam_offset)
                
                # Place sphere center at the cylinder's outer radius
                overcut = max(settings.epsilon, getattr(settings, 'cylinder_counter_plate_overcut_mm', 0.05))
                center_radius = outer_radius + overcut
                cyl_x = center_radius * np.cos(theta)
                cyl_y = center_radius * np.sin(theta)
                # Map planar Y to cylinder local Z (centered at 0)
                cyl_z = dot_y - (height / 2.0)
                
                sphere.apply_translation([cyl_x, cyl_y, cyl_z])
                sphere_meshes.append(sphere)
    
    print(f"DEBUG: Creating {len(sphere_meshes)} hemispherical recesses on cylinder counter plate")
    
    if not sphere_meshes:
        print("WARNING: No spheres were generated for cylinder counter plate. Returning base shell.")
        # The cylinder is already created with vertical axis (along Z)
        # No rotation needed - it should stand upright
        # Just ensure the base is at Z=0
        min_z = cylinder_shell.bounds[0][2]
        cylinder_shell.apply_translation([0, 0, -min_z])
        
        return cylinder_shell
    
    # More robust boolean strategy:
    # 1) Start with the cylinder shell (which already has the polygonal cutout)
    # 2) Subtract the union of all spheres and triangles to create outer recesses
    
    engines_to_try = ['manifold', None]  # None uses trimesh default
    
    for engine in engines_to_try:
        try:
            engine_name = engine if engine else "trimesh-default"
            
            # Union all spheres
            print(f"DEBUG: Cylinder boolean - union spheres with {engine_name}...")
            if len(sphere_meshes) == 1:
                union_spheres = sphere_meshes[0]
            else:
                union_spheres = trimesh.boolean.union(sphere_meshes, engine=engine)
            
            # Union all triangles
            if triangle_meshes:
                print(f"DEBUG: Cylinder boolean - union triangles with {engine_name}...")
                if len(triangle_meshes) == 1:
                    union_triangles = triangle_meshes[0]
                else:
                    union_triangles = trimesh.boolean.union(triangle_meshes, engine=engine)
            
            # Union all line end markers
            if line_end_meshes:
                print(f"DEBUG: Cylinder boolean - union line end markers with {engine_name}...")
                if len(line_end_meshes) == 1:
                    union_line_ends = line_end_meshes[0]
                else:
                    union_line_ends = trimesh.boolean.union(line_end_meshes, engine=engine)
            
            # Combine all cutouts (spheres, triangles, and line ends)
            print(f"DEBUG: Cylinder boolean - combining all cutouts with {engine_name}...")
            all_cutouts_list = [union_spheres]
            if triangle_meshes:
                all_cutouts_list.append(union_triangles)
            if line_end_meshes:
                all_cutouts_list.append(union_line_ends)
            
            if len(all_cutouts_list) > 1:
                all_cutouts = trimesh.boolean.union(all_cutouts_list, engine=engine)
            else:
                all_cutouts = all_cutouts_list[0]
            
            print(f"DEBUG: Cylinder boolean - subtract all cutouts from cylinder shell with {engine_name}...")
            final_shell = trimesh.boolean.difference([cylinder_shell, all_cutouts], engine=engine)
            
            if not final_shell.is_watertight:
                print("DEBUG: Cylinder final shell not watertight, attempting to fill holes...")
                final_shell.fill_holes()
            
            print(f"DEBUG: Cylinder counter plate completed with {engine_name}: {len(final_shell.vertices)} vertices, {len(final_shell.faces)} faces")
            
            # The cylinder is already created with vertical axis (along Z)
            # No rotation needed - it should stand upright
            # Just ensure the base is at Z=0
            min_z = final_shell.bounds[0][2]
            final_shell.apply_translation([0, 0, -min_z])
            
            return final_shell
        except Exception as e:
            print(f"ERROR: Cylinder robust boolean with {engine_name} failed: {e}")
            continue
    
    # Fallback: subtract spheres individually from cylinder shell
    try:
        print("DEBUG: Fallback - individual subtraction from cylinder shell...")
        result_shell = cylinder_shell.copy()
        for i, sphere in enumerate(sphere_meshes):
            try:
                print(f"DEBUG: Subtracting sphere {i+1}/{len(sphere_meshes)} from cylinder shell...")
                result_shell = trimesh.boolean.difference([result_shell, sphere])
            except Exception as sphere_error:
                print(f"WARNING: Failed to subtract sphere {i+1}: {sphere_error}")
                continue
        
        # Subtract triangles individually
        for i, triangle in enumerate(triangle_meshes):
            try:
                print(f"DEBUG: Subtracting triangle {i+1}/{len(triangle_meshes)} from cylinder shell...")
                result_shell = trimesh.boolean.difference([result_shell, triangle])
            except Exception as triangle_error:
                print(f"WARNING: Failed to subtract triangle {i+1}: {triangle_error}")
                continue
        
        # Subtract line end markers individually
        for i, line_end in enumerate(line_end_meshes):
            try:
                print(f"DEBUG: Subtracting line end marker {i+1}/{len(line_end_meshes)} from cylinder shell...")
                result_shell = trimesh.boolean.difference([result_shell, line_end])
            except Exception as line_error:
                print(f"WARNING: Failed to subtract line end marker {i+1}: {line_error}")
                continue
        
        final_shell = result_shell
        if not final_shell.is_watertight:
            final_shell.fill_holes()
        print(f"DEBUG: Fallback completed: {len(final_shell.vertices)} vertices, {len(final_shell.faces)} faces")
        
        # The cylinder is already created with vertical axis (along Z)
        # No rotation needed - it should stand upright
        # Just ensure the base is at Z=0
        min_z = final_shell.bounds[0][2]
        final_shell.apply_translation([0, 0, -min_z])
        
        return final_shell
    except Exception as final_error:
        print(f"ERROR: Cylinder fallback boolean failed: {final_error}")
        print("WARNING: Returning simple cylinder shell without recesses.")
        
        # The cylinder is already created with vertical axis (along Z)
        # No rotation needed - it should stand upright
        # Just ensure the base is at Z=0
        min_z = cylinder_shell.bounds[0][2]
        cylinder_shell.apply_translation([0, 0, -min_z])
        
        return cylinder_shell

def build_counter_plate_hemispheres(params: CardSettings) -> trimesh.Trimesh:
    """
    Create a counter plate with true hemispherical recesses using trimesh with Manifold backend.
    
    This function generates a full braille grid and creates hemispherical recesses at EVERY dot position,
    regardless of grade-2 translation. The hemisphere diameter exactly equals the Embossing Plate's
    "braille dot base diameter" parameter plus the counter plate dot size offset.
    
    Args:
        params: CardSettings object containing all layout and geometry parameters
        
    Returns:
        Trimesh object representing the counter plate with hemispherical recesses
        
    Technical details:
    - Plate thickness: TH (mm). Top surface is z=TH, bottom is z=0.
    - Hemisphere radius r = (emboss_dot_base_diameter + counter_plate_dot_size_offset) / 2.
    - For each dot center (x, y) in the braille grid, creates an icosphere with radius r
      and translates its center to (x, y, TH - r + ε) so the lower hemisphere sits inside the slab
      and the equator coincides with the top surface.
    - Subtracts all spheres in one operation using trimesh.boolean.difference with engine='manifold'.
    - Generates dot centers from a full grid using the same layout parameters as the Embossing Plate.
    - Always places all 6 dots per cell (does not consult per-character translation).
    """
    
    # Create the base plate as a box aligned to z=[0, TH], x=[0, W], y=[0, H]
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width/2, params.card_height/2, params.plate_thickness/2))
    
    print(f"DEBUG: Creating counter plate base: {params.card_width}mm x {params.card_height}mm x {params.plate_thickness}mm")
    
    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]
    
    # Calculate hemisphere radius including the counter plate offset
    hemisphere_radius = (params.emboss_dot_base_diameter + params.counter_plate_dot_size_offset) / 2
    print(f"DEBUG: Hemisphere radius: {hemisphere_radius:.3f}mm (base: {params.emboss_dot_base_diameter}mm + offset: {params.counter_plate_dot_size_offset}mm)")
    
    # Create icospheres for ALL possible dot positions
    sphere_meshes = []
    total_spheres = 0
    
    # Generate spheres for each grid position
    for row in range(params.grid_rows):
        # Calculate Y position for this row (same as embossing plate, using safe margin)
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust
        
        # Process ALL columns (minus two for triangle and line end marker spaces)
        for col in range(params.grid_columns - 2):
            # Calculate X position for this column (shifted by one cell due to triangle marker)
            x_pos = params.left_margin + ((col + 1) * params.cell_spacing) + params.braille_x_adjust
            
            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create an icosphere with the calculated hemisphere radius
                # Use hemisphere_subdivisions parameter to control mesh density
                sphere = trimesh.creation.icosphere(subdivisions=params.hemisphere_subdivisions, radius=hemisphere_radius)
                
                # CRITICAL FIX: Position the sphere center AT the plate surface level
                # This ensures when the sphere is subtracted, it creates a hemispherical recess going DOWN into the plate
                # The sphere center should be exactly at the top surface (z = plate_thickness)
                z_pos = params.plate_thickness
                sphere.apply_translation((dot_x, dot_y, z_pos))
                
                sphere_meshes.append(sphere)
                total_spheres += 1
    
    print(f"DEBUG: Created {total_spheres} hemispheres for counter plate")
    
    # Create triangle marker recesses and end of row line recesses for ALL rows
    triangle_meshes = []
    line_end_meshes = []
    for row_num in range(params.grid_rows):
        # Calculate Y position for this row
        y_pos = params.card_height - params.top_margin - (row_num * params.line_spacing) + params.braille_y_adjust
        
        # Add triangle marker at the first cell position (column 0)
        x_pos = params.left_margin + params.braille_x_adjust
        
        # Create triangle marker for subtraction (will create recess)
        triangle_mesh = create_card_triangle_marker_3d(x_pos, y_pos, params, height=0.4, for_subtraction=True)
        triangle_meshes.append(triangle_mesh)
        
        # Add end of row line marker at the last cell position (grid_columns - 1)
        x_pos_end = params.left_margin + ((params.grid_columns - 1) * params.cell_spacing) + params.braille_x_adjust
        
        # Create line end marker for subtraction (will create recess)
        line_end_mesh = create_card_line_end_marker_3d(x_pos_end, y_pos, params, height=0.5, for_subtraction=True)
        line_end_meshes.append(line_end_mesh)
    
    print(f"DEBUG: Created {len(triangle_meshes)} triangle markers and {len(line_end_meshes)} line end markers for counter plate")
    
    if not sphere_meshes:
        print("WARNING: No spheres were generated. Returning base plate.")
        return plate_mesh
    
    # Perform boolean operations - try manifold first, then trimesh default
    engines_to_try = ['manifold', 'blender', None]  # None uses trimesh default (usually CGAL or OpenSCAD)
    
    for engine in engines_to_try:
        try:
            engine_name = engine if engine else "trimesh-default"
            print(f"DEBUG: Attempting boolean operations with {engine_name} engine...")
            
            # Union all spheres together for more efficient subtraction
            if len(sphere_meshes) == 1:
                union_spheres = sphere_meshes[0]
            else:
                print("DEBUG: Unioning spheres...")
                union_spheres = trimesh.boolean.union(sphere_meshes, engine=engine)
            
            # Union all triangles
            if triangle_meshes:
                print(f"DEBUG: Unioning {len(triangle_meshes)} triangles...")
                if len(triangle_meshes) == 1:
                    union_triangles = triangle_meshes[0]
                else:
                    union_triangles = trimesh.boolean.union(triangle_meshes, engine=engine)
            
            # Union all line end markers
            if line_end_meshes:
                print(f"DEBUG: Unioning {len(line_end_meshes)} line end markers...")
                if len(line_end_meshes) == 1:
                    union_line_ends = line_end_meshes[0]
                else:
                    union_line_ends = trimesh.boolean.union(line_end_meshes, engine=engine)
            
            # Combine all cutouts (spheres, triangles, and line ends)
            print("DEBUG: Combining all cutouts...")
            all_cutouts_list = [union_spheres]
            if triangle_meshes:
                all_cutouts_list.append(union_triangles)
            if line_end_meshes:
                all_cutouts_list.append(union_line_ends)
            
            if len(all_cutouts_list) > 1:
                all_cutouts = trimesh.boolean.union(all_cutouts_list, engine=engine)
            else:
                all_cutouts = all_cutouts_list[0]
            
            print("DEBUG: Subtracting all cutouts from plate...")
            # Subtract the unified cutouts from the plate in one operation
            counter_plate_mesh = trimesh.boolean.difference([plate_mesh, all_cutouts], engine=engine)
            
            # Verify the mesh is watertight
            if not counter_plate_mesh.is_watertight:
                print("DEBUG: Counter plate mesh not watertight, attempting to fix...")
                counter_plate_mesh.fill_holes()
                if counter_plate_mesh.is_watertight:
                    print("DEBUG: Successfully fixed counter plate mesh")
            
            print(f"DEBUG: Counter plate completed with {engine_name} engine: {len(counter_plate_mesh.vertices)} vertices, {len(counter_plate_mesh.faces)} faces")
            return counter_plate_mesh
            
        except Exception as e:
            print(f"ERROR: Boolean operations with {engine_name} failed: {e}")
            if engine == engines_to_try[-1]:  # Last engine failed
                print("WARNING: All boolean engines failed. Creating hemisphere counter plate with individual subtraction...")
                break
            else:
                print(f"WARNING: Trying next engine...")
                continue
    
    # Final fallback: subtract spheres and triangles one by one (slower but more reliable)
    try:
        print("DEBUG: Attempting individual sphere and triangle subtraction...")
        counter_plate_mesh = plate_mesh.copy()
        
        for i, sphere in enumerate(sphere_meshes):
            try:
                print(f"DEBUG: Subtracting sphere {i+1}/{len(sphere_meshes)}...")
                counter_plate_mesh = trimesh.boolean.difference([counter_plate_mesh, sphere])
            except Exception as sphere_error:
                print(f"WARNING: Failed to subtract sphere {i+1}: {sphere_error}")
                continue
        
        # Subtract triangles individually
        for i, triangle in enumerate(triangle_meshes):
            try:
                print(f"DEBUG: Subtracting triangle {i+1}/{len(triangle_meshes)}...")
                counter_plate_mesh = trimesh.boolean.difference([counter_plate_mesh, triangle])
            except Exception as triangle_error:
                print(f"WARNING: Failed to subtract triangle {i+1}: {triangle_error}")
                continue
        
        # Subtract line end markers individually
        for i, line_end in enumerate(line_end_meshes):
            try:
                print(f"DEBUG: Subtracting line end marker {i+1}/{len(line_end_meshes)}...")
                counter_plate_mesh = trimesh.boolean.difference([counter_plate_mesh, line_end])
            except Exception as line_error:
                print(f"WARNING: Failed to subtract line end marker {i+1}: {line_error}")
                continue
        
        # Try to fix the mesh
        if not counter_plate_mesh.is_watertight:
            counter_plate_mesh.fill_holes()
        
        print(f"DEBUG: Individual subtraction completed: {len(counter_plate_mesh.vertices)} vertices, {len(counter_plate_mesh.faces)} faces")
        return counter_plate_mesh
        
    except Exception as final_error:
        print(f"ERROR: Individual sphere subtraction failed: {final_error}")
        print("WARNING: Falling back to simple negative plate method.")
        # Final fallback to the simple approach
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

def _scan_liblouis_tables(directory: str):
    """Scan a directory for liblouis translation tables and extract basic metadata.

    Returns a list of dicts with keys: file, locale, type, grade, contraction, dots, variant.
    """
    tables_info = []
    try:
        if not os.path.isdir(directory):
            return tables_info

        # Walk recursively to find tables in subfolders as well
        for root, _, files in os.walk(directory):
            for fname in files:
                low = fname.lower()
                # Only expose primary translation tables
                if not (low.endswith('.ctb') or low.endswith('.utb') or low.endswith('.tbl')):
                    continue

                fpath = os.path.join(root, fname)

                meta = {
                    'file': fname,
                    'locale': None,
                    'type': None,
                    'grade': None,
                    'contraction': None,
                    'dots': None,
                    'variant': None,
                }

                # Parse lightweight metadata from the file header
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for _ in range(200):
                            line = f.readline()
                            if not line:
                                break
                            m = re.match(r'^\s*#\+\s*([A-Za-z_-]+)\s*:\s*(.+?)\s*$', line)
                            if not m:
                                continue
                            key = m.group(1).strip().lower()
                            val = m.group(2).strip()
                            if key == 'locale' and not meta['locale']:
                                # Normalize locale casing, e.g., en-us -> en-US
                                parts = val.replace('_', '-').split('-')
                                if parts:
                                    parts[0] = parts[0].lower()
                                    for i in range(1, len(parts)):
                                        if len(parts[i]) in (2, 3):
                                            parts[i] = parts[i].upper()
                                meta['locale'] = '-'.join(parts)
                            elif key == 'type' and not meta['type']:
                                meta['type'] = val.lower()
                            elif key == 'grade' and not meta['grade']:
                                meta['grade'] = str(val)
                            elif key == 'contraction' and not meta['contraction']:
                                meta['contraction'] = val.lower()
                            elif key == 'dots' and not meta['dots']:
                                try:
                                    meta['dots'] = int(val)
                                except Exception:
                                    meta['dots'] = None
                except Exception:
                    pass

                base = os.path.splitext(fname)[0]
                base_norm = base.lower()

                # Derive locale from filename when missing
                if not meta['locale']:
                    candidate = base
                    # Common separators to normalize
                    candidate = candidate.replace('_', '-')
                    # Trim trailing grade tokens for locale inference
                    candidate = re.sub(r'-g[012]\b.*$', '', candidate, flags=re.IGNORECASE)
                    # Special english variants keep base 'en'
                    if candidate.startswith('en-ueb') or candidate.startswith('en-us') or candidate.startswith('en-gb'):
                        loc = candidate.split('-')[0]
                    else:
                        parts = candidate.split('-')
                        loc = parts[0]
                        if len(parts) > 1 and len(parts[1]) in (2, 3):
                            loc = f"{parts[0]}-{parts[1]}"
                    parts = loc.split('-')
                    if parts:
                        parts[0] = parts[0].lower()
                        for i in range(1, len(parts)):
                            if len(parts[i]) in (2, 3):
                                parts[i] = parts[i].upper()
                        meta['locale'] = '-'.join(parts)

                # Derive grade from filename when missing
                if not meta['grade']:
                    m = re.search(r'-g([012])\b', base_norm)
                    if m:
                        meta['grade'] = m.group(1)

                # Derive dots from filename if not present (e.g., comp8/comp6)
                if meta['dots'] is None:
                    if 'comp8' in base_norm or re.search(r'8dot|8-dot', base_norm):
                        meta['dots'] = 8
                    elif 'comp6' in base_norm or re.search(r'6dot|6-dot', base_norm):
                        meta['dots'] = 6

                # Derive type/contraction heuristics if missing
                if not meta['type']:
                    if 'comp' in base_norm or (meta['dots'] in (6, 8) and 'g' not in (meta['grade'] or '')):
                        meta['type'] = 'computer'
                    else:
                        meta['type'] = 'literary'

                if not meta['contraction']:
                    # Infer from grade when possible
                    if meta['grade'] == '2':
                        meta['contraction'] = 'full'
                    elif meta['grade'] in ('0', '1'):
                        meta['contraction'] = 'no'

                # Variant hints (primarily for English)
                if 'ueb' in base_norm:
                    meta['variant'] = 'UEB'
                elif base_norm.startswith('en-us'):
                    meta['variant'] = 'EBAE'

                tables_info.append(meta)
    except Exception:
        # Fail silently and return whatever we collected
        return tables_info

    return tables_info

@app.route('/liblouis/tables')
def list_liblouis_tables():
    """List available liblouis translation tables from static assets.

    This powers the frontend language dropdown dynamically so it stays in sync
    with the actual shipped tables.
    """
    # Resolve candidate directories relative to app root
    base = app.root_path
    candidate_dirs = [
        os.path.join(base, 'static', 'liblouis', 'tables'),
        os.path.join(base, 'node_modules', 'liblouis-build', 'tables'),
        os.path.join(base, 'third_party', 'liblouis', 'tables'),
        os.path.join(base, 'third_party', 'liblouis', 'share', 'liblouis', 'tables'),
    ]

    merged = {}
    for d in candidate_dirs:
        for t in _scan_liblouis_tables(d):
            # Deduplicate by file name, prefer the first occurrence
            key = t.get('file')
            if key and key not in merged:
                merged[key] = t

    tables = list(merged.values())
    # Sort deterministically by locale then file name
    tables.sort(key=lambda t: (t.get('locale') or '', t.get('file') or ''))
    return jsonify({'tables': tables})

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
        original_lines = data.get('original_lines', None)  # Optional: original text before braille conversion
        plate_type = data.get('plate_type', 'positive')
        grade = data.get('grade', 'g2')
        settings_data = data.get('settings', {})
        shape_type = data.get('shape_type', 'card')  # New: default to 'card' for backward compatibility
        cylinder_params = data.get('cylinder_params', {})  # New: optional cylinder parameters
        
        # Validate inputs
        validate_lines(lines)
        validate_settings(settings_data)
        
        # Validate plate_type
        if plate_type not in ['positive', 'negative']:
            return jsonify({'error': 'Invalid plate_type. Must be "positive" or "negative"'}), 400
        
        # Validate grade
        if grade not in ['g1', 'g2']:
            return jsonify({'error': 'Invalid grade. Must be "g1" or "g2"'}), 400
        
        # Validate shape_type
        if shape_type not in ['card', 'cylinder']:
            return jsonify({'error': 'Invalid shape_type. Must be "card" or "cylinder"'}), 400
        
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
        if shape_type == 'card':
            # Original card generation logic
            if plate_type == 'positive':
                mesh = create_positive_plate_mesh(lines, grade, settings, original_lines)
            elif plate_type == 'negative':
                # Counter plate uses hemispherical recesses as per project brief
                # It does NOT depend on text input - always creates ALL 6 dots per cell
                print("DEBUG: Generating counter plate with hemispherical recesses (all positions)")
                mesh = build_counter_plate_hemispheres(settings)
            else:
                return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400
        
        elif shape_type == 'cylinder':
            # New cylinder generation logic
            if plate_type == 'positive':
                mesh = generate_cylinder_stl(lines, grade, settings, cylinder_params, original_lines)
            elif plate_type == 'negative':
                # Cylinder counter plate - needs implementation
                mesh = generate_cylinder_counter_plate(lines, settings, cylinder_params)
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
            try:
                mesh.fix_normals()
                print("INFO: Fixed mesh normals")
            except ImportError:
                # fix_normals requires scipy, try unify_normals instead
                mesh.unify_normals()
                print("INFO: Unified mesh normals (scipy not available)")
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Create JSON config dump for reproducibility
        config_dump = {
            "timestamp": datetime.now().isoformat(),
            "plate_type": plate_type,
            "shape_type": shape_type,
            "grade": grade if plate_type == 'positive' else "n/a",
            "text_lines": lines if plate_type == 'positive' else ["Counter plate - all positions"],
            "cylinder_params": cylinder_params if shape_type == 'cylinder' else "n/a",
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
            filename = f'braille_embossing_plate-{shape_type}'
            for i, line in enumerate(lines):
                if line.strip():
                    # Sanitize filename: remove special characters and limit length
                    sanitized = re.sub(r'[^\w\s-]', '', line.strip()[:30])
                    sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
                    if sanitized:
                        if i == 0:  # Line 1
                            filename = f'braille_embossing_plate_{sanitized}-{shape_type}'
                        else:  # Other lines as fallback
                            filename = f'braille_embossing_plate_{sanitized}-{shape_type}'
                        break
        else:
            # For counter plates, include total diameter (base + offset) in filename
            total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
            filename = f'braille_counter_plate_{total_diameter}mm-{shape_type}'
        
        # Additional filename sanitization for security
        filename = re.sub(r'[^\w\-_]', '', filename)[:60]  # Allow longer names to accommodate shape type
        
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