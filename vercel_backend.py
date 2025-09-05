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

# Import all the necessary components from backend.py
# This way we maintain a single source of truth for the logic
try:
    from backend import (
        add_security_headers, rate_limit, validate_lines, validate_settings,
        handle_error, request_entity_too_large, bad_request,
        CardSettings, braille_to_dots, create_braille_dot,
        create_positive_plate_mesh, create_simple_negative_plate,
        create_fallback_plate, build_counter_plate_hemispheres,
        layout_cylindrical_cells, create_cylinder_shell,
        create_cylinder_braille_dot, generate_cylinder_stl,
        generate_cylinder_counter_plate, _scan_liblouis_tables
    )
    
    # Apply the imported decorators and error handlers
    app.after_request(add_security_headers)
    app.errorhandler(Exception)(handle_error)
    app.errorhandler(413)(request_entity_too_large)
    app.errorhandler(400)(bad_request)
    
except ImportError as e:
    # If backend.py is not available, we need to define the functions here
    # This is a fallback for Vercel deployment where we might not have access to backend.py
    print(f"Warning: Could not import from backend.py: {e}")
    # In this case, we would need to copy the essential functions here
    # For now, we'll just raise an error
    raise ImportError("backend.py must be available for vercel_backend.py to work")

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
@app.route('/favicon.png')
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

@app.route('/liblouis/tables')
def list_liblouis_tables():
    """List available liblouis translation tables from static assets."""
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
        original_lines = data.get('original_lines', None)
        # Normalize incoming enums for robustness
        plate_type = str(data.get('plate_type', 'positive')).strip().lower()
        shape_type = str(data.get('shape_type', 'card')).strip().lower()  # default to 'card' for backward compatibility
        grade = str(data.get('grade', 'g2')).strip().lower()
        settings_data = data.get('settings', {})
        cylinder_params = data.get('cylinder_params', {})

        # Debug: log request summary (safe)
        try:
            app.logger.info(
                f"Request /generate_braille_stl → plate_type={plate_type}, shape_type={shape_type}, grade={grade}, "
                f"orig_lines={'yes' if isinstance(original_lines, list) else 'no'}, grid={settings_data.get('grid_columns')}x{settings_data.get('grid_rows')}"
            )
            if shape_type == 'cylinder':
                app.logger.info(
                    f"Cylinder params: diameter={cylinder_params.get('diameter_mm')}, height={cylinder_params.get('height_mm')}, "
                    f"cutout_radius={cylinder_params.get('polygonal_cutout_radius_mm')}, seam_offset={cylinder_params.get('seam_offset_deg')}"
                )
        except Exception:
            pass
        
        # Validate inputs
        validate_lines(lines)
        validate_settings(settings_data)
        
        # Validate plate_type
        if plate_type not in ['positive', 'negative']:
            return jsonify({'error': 'Invalid plate_type. Must be "positive" or "negative"'}), 400
        
        # Validate shape_type
        if shape_type not in ['card', 'cylinder']:
            return jsonify({'error': 'Invalid shape_type. Must be "card" or "cylinder"'}), 400
        
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
    
    try:
        if shape_type == 'card':
            if plate_type == 'positive':
                mesh = create_positive_plate_mesh(lines, grade, settings, original_lines)
            elif plate_type == 'negative':
                # Counter plate uses hemispherical recesses as per project brief
                mesh = build_counter_plate_hemispheres(settings)
            else:
                return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400
        elif shape_type == 'cylinder':
            if plate_type == 'positive':
                mesh = generate_cylinder_stl(lines, grade, settings, cylinder_params, original_lines)
            elif plate_type == 'negative':
                mesh = generate_cylinder_counter_plate(lines, settings, cylinder_params)
            else:
                return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400
        else:
            return jsonify({'error': f'Invalid shape type: {shape_type}. Use "card" or "cylinder".'}), 400
        
        # Verify mesh is watertight and manifold
        if not mesh.is_watertight:
            mesh.fill_holes()
        
        if not mesh.is_winding_consistent:
            mesh.fix_normals()
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Create filename based on text content with fallback logic
        if plate_type == 'positive':
            filename = f'braille_embossing_plate-{shape_type}'
            for i, line in enumerate(lines):
                if line.strip():
                    # Sanitize filename: remove special characters and limit length
                    sanitized = re.sub(r'[^\w\s-]', '', line.strip()[:30])
                    sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
                    if sanitized:
                        filename = f'braille_embossing_plate_{sanitized}-{shape_type}'
                        break
        else:
            # For counter plates, include total diameter (base + offset) in filename
            total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
            filename = f'braille_counter_plate_{total_diameter}mm-{shape_type}'
        
        # Additional filename sanitization for security
        filename = re.sub(r'[^\w\-_]', '', filename)[:60]
        
        # Return the STL file
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
        mesh = build_counter_plate_hemispheres(settings)
        
        # Verify mesh is watertight
        if not mesh.is_watertight:
            mesh.fill_holes()
        
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        
        # Include total diameter (base + offset) in filename
        total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        filename = f'braille_counter_plate_{total_diameter}mm.stl'
        return send_file(stl_io, mimetype='model/stl', as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate counter plate: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment
app.debug = False

