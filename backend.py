import hashlib
import io
import json
import os
import re
import time
from datetime import datetime

import numpy as np
import trimesh
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_file, send_from_directory
from flask_cors import CORS
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from werkzeug.exceptions import HTTPException

try:
    import requests  # Optional, used for Vercel Blob REST API
except Exception:
    requests = None
# Matplotlib imports are intentionally deferred to inside functions that need them
# to keep the serverless deployment lightweight and optional

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:  # pragma: no cover - allow local dev without limiter installed
    Limiter = None

    def get_remote_address():
        return request.remote_addr


# Import cache functions from app.cache module
import contextlib

from app.cache import (
    _blob_check_exists,
    _blob_public_base_url,
    _blob_upload,
    _blob_url_cache_get,
    _blob_url_cache_set,
    _build_blob_public_url,
    _normalize_cylinder_params_for_cache,
    _normalize_settings_for_cache,
    compute_cache_key,
)

# Import geometry functions from app.geometry
from app.geometry.cylinder import generate_cylinder_counter_plate, generate_cylinder_stl
from app.geometry.dot_shapes import create_braille_dot

# Import models from app.models
from app.models import CardSettings

# Import utilities from app.utils
from app.utils import braille_to_dots, get_logger

# Import validation from app.validation
from app.validation import (
    validate_braille_lines,
    validate_lines,
    validate_settings,
)

# Configure logging for this module
logger = get_logger(__name__)

app = Flask(__name__)
# CORS configuration - update with your actual domain before deployment
allowed_origins = [
    'https://your-vercel-domain.vercel.app',  # Replace with your actual Vercel domain
    'https://your-custom-domain.com',  # Replace with your custom domain if any
]

# For development, allow localhost
if os.environ.get('FLASK_ENV') == 'development':
    allowed_origins.extend(['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5001'])

CORS(app, origins=allowed_origins, supports_credentials=True)


# Environment detection helpers
def _is_serverless_env() -> bool:
    """
    Detect if running in a serverless environment (e.g., Vercel/AWS Lambda).
    Used to avoid backends that require external binaries (3D boolean engines).
    """
    try:
        return bool(
            os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('NOW_REGION')
        )
    except Exception:
        return False


# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max request size
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Flask-Limiter setup (Phase 4.1/4.2) - ENABLED with Redis when available, memory fallback otherwise
redis_url = os.environ.get('REDIS_URL')
storage_uri = redis_url if redis_url else 'memory://'
if Limiter is not None:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        default_limits=['10 per minute'],
    )
    limiter.init_app(app)
else:

    class _NoopLimiter:
        def limit(self, *_args, **_kwargs):
            def decorator(f):
                return f

            return decorator

    limiter = _NoopLimiter()

# Helper functions for security (cache functions now in app.cache)


@app.route('/lookup_stl', methods=['GET'])
@limiter.limit('60 per minute')
def lookup_stl_redirect():
    """Return cached negative plate location (302 redirect or JSON) if available.

    Query params:
    - shape_type: 'card' (default) or 'cylinder'
    - settings: JSON for CardSettings
    - cylinder_params: JSON for cylinder (when shape_type='cylinder')
    - format: 'json' to return { url, cache_key } with cacheable headers instead of 302
    """
    try:
        shape_type = request.args.get('shape_type', 'card')
        if shape_type not in ('card', 'cylinder'):
            return jsonify({'error': 'Invalid shape_type'}), 400

        settings_json = request.args.get('settings', '')
        cylinder_json = request.args.get('cylinder_params', '')

        try:
            settings_data = json.loads(settings_json) if settings_json else {}
            validate_settings(settings_data)
            settings = CardSettings(**settings_data)
        except Exception:
            settings = CardSettings(**{})

        cylinder_params = {}
        if shape_type == 'cylinder':
            try:
                cylinder_params = json.loads(cylinder_json) if cylinder_json else {}
            except Exception:
                cylinder_params = {}

        cache_payload = {
            'plate_type': 'negative',
            'shape_type': shape_type,
            'settings': _normalize_settings_for_cache(settings),
        }
        if shape_type == 'cylinder':
            cache_payload['cylinder_params'] = _normalize_cylinder_params_for_cache(cylinder_params)
        cache_key = compute_cache_key(cache_payload)

        mapped = _blob_url_cache_get(cache_key)
        public_url = mapped or _build_blob_public_url(cache_key)
        if public_url and _blob_check_exists(public_url):
            if request.args.get('format') == 'json' or 'application/json' in (request.headers.get('Accept') or ''):
                payload = {'url': public_url, 'cache_key': cache_key}
                resp = make_response(jsonify(payload), 200)
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
                resp.headers['X-Blob-Cache'] = 'hit'
                resp.headers['X-Blob-Cache-Reason'] = 'lookup-exists'
                resp.headers['X-Cache'] = 'hit-json'
                resp.headers['X-Compute-Time'] = '0'
                return resp
            resp = redirect(public_url, code=302)
            resp.headers['X-Blob-Cache-Key'] = cache_key
            resp.headers['X-Blob-URL'] = public_url
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
            resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
            resp.headers['X-Blob-Cache'] = 'hit'
            resp.headers['X-Blob-Cache-Reason'] = 'lookup-exists'
            resp.headers['X-Cache'] = 'hit-redirect'
            resp.headers['X-Compute-Time'] = '0'
            return resp

        resp = make_response(jsonify({'error': 'not-found', 'cache_key': cache_key}), 404)
        resp.headers['Cache-Control'] = 'no-store'
        resp.headers['CDN-Cache-Control'] = 'no-store'
        return resp
    except Exception as e:
        return jsonify({'error': f'lookup-failed: {str(e)}'}), 500


# Blob storage functions now in app.cache


@app.route('/debug/blob_upload', methods=['GET'])
def debug_blob_upload():
    """Try both direct and API blob uploads with a 1-byte payload and report results."""
    try:
        token = os.environ.get('BLOB_STORE_WRITE_TOKEN') or os.environ.get('BLOB_READ_WRITE_TOKEN')
        public_base = os.environ.get('BLOB_PUBLIC_BASE_URL')
        direct_base = os.environ.get('BLOB_DIRECT_UPLOAD_URL', 'https://blob.vercel-storage.com')
        api_base = os.environ.get('BLOB_API_BASE_URL', 'https://api.vercel.com')
        info = {
            'env': {
                'has_BLOB_STORE_WRITE_TOKEN': bool(os.environ.get('BLOB_STORE_WRITE_TOKEN')),
                'has_BLOB_READ_WRITE_TOKEN': bool(os.environ.get('BLOB_READ_WRITE_TOKEN')),
                'BLOB_PUBLIC_BASE_URL': public_base,
                'BLOB_DIRECT_UPLOAD_URL': direct_base,
                'BLOB_API_BASE_URL': api_base,
            }
        }
        if not token:
            info['error'] = 'missing-token'
            return jsonify(info), 200

        test_key = f'debug_{int(time.time())}'
        pathname = f'stl/{test_key}.bin'
        payload = b'x'

        # Direct upload
        direct_headers = {
            'Authorization': f'Bearer {token}',
            'x-vercel-filename': pathname,
            # support both header spellings seen in docs
            'x-vercel-blob-add-random-suffix': '0',
            'x-vercel-blobs-add-random-suffix': '0',
            'x-vercel-blob-access': 'public',
            'x-vercel-blobs-access': 'public',
            'content-type': 'application/octet-stream',
        }
        try:
            d_resp = requests.put(
                f'{direct_base.rstrip("/")}/{pathname}', data=payload, headers=direct_headers, timeout=20
            )
            info['direct'] = {
                'status': d_resp.status_code,
                'text': d_resp.text[:800] if hasattr(d_resp, 'text') else '<no text>',
            }
            with contextlib.suppress(Exception):
                info['direct']['json'] = d_resp.json()
        except Exception as e:
            info['direct'] = {'exception': str(e)}

        # API upload
        api_url = f'{api_base.rstrip("/")}/v2/blobs'
        files = {'file': (pathname, payload, 'application/octet-stream')}
        data = {
            'pathname': pathname,
            'contentType': 'application/octet-stream',
            'cacheControlMaxAge': os.environ.get('BLOB_CACHE_MAX_AGE', '31536000'),
            'access': 'public',
            'addRandomSuffix': 'false',
        }
        api_headers = {'Authorization': f'Bearer {token}'}
        try:
            a_resp = requests.post(api_url, files=files, data=data, headers=api_headers, timeout=20)
            info['api'] = {
                'status': a_resp.status_code,
                'text': a_resp.text[:800] if hasattr(a_resp, 'text') else '<no text>',
            }
            with contextlib.suppress(Exception):
                info['api']['json'] = a_resp.json()
        except Exception as e:
            info['api'] = {'exception': str(e)}

        return jsonify(info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 200


# Security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Content-Security-Policy allowing web workers, table loading, and Blob CDN redirects
    blob_base = _blob_public_base_url().rstrip('/')
    connect_sources = ["'self'", 'blob:', 'data:']
    if blob_base:
        connect_sources.append(blob_base)
    # Also allow generic Vercel Blob CDN wildcard as a fallback if no env set
    if not blob_base:
        connect_sources.append('https://*.vercel-storage.com')
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://vercel.live; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        f'connect-src {" ".join(connect_sources)}; '
        "object-src 'none'; "
        "base-uri 'self'; worker-src 'self' blob:"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


## Removed legacy in-memory rate limiting in favor of Flask-Limiter


# Input validation functions
# Validation functions now imported from app.validation


# Add error handling for Vercel environment
@app.errorhandler(Exception)
def handle_error(e):
    import traceback

    # Pass through HTTPExceptions (e.g., 404) so they keep their original status codes
    if isinstance(e, HTTPException):
        return e
    # Log unexpected errors for debugging in production
    app.logger.error(f'Error: {str(e)}')
    app.logger.error(f'Traceback: {traceback.format_exc()}')
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


# braille_to_dots now imported from app.utils

# create_braille_dot now imported from app.geometry.dot_shapes


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
    2 * settings.dot_spacing

    # Triangle height (horizontal extension) = dot_spacing (to reach middle-right dot)
    triangle_width = settings.dot_spacing

    # Triangle vertices:
    # Base is centered between top-left and bottom-left dots
    base_x = x - settings.dot_spacing / 2  # Left column position

    # Create triangle vertices
    vertices = [
        (base_x, y - settings.dot_spacing),  # Bottom of base
        (base_x, y + settings.dot_spacing),  # Top of base
        (base_x + triangle_width, y),  # Apex (at middle-right dot height)
    ]

    # Create and return the triangle polygon
    return Polygon(vertices)


def create_card_triangle_marker_3d(x, y, settings: CardSettings, height=0.6, for_subtraction=False):
    """
    Create a 3D triangular prism for card surface marking.

    Args:
        x, y: Center position of the first braille cell
        settings: CardSettings object with spacing parameters
        height: Depth/height of the triangle marker (default 0.6mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses

    Returns:
        Trimesh object representing the 3D triangle marker
    """
    # Calculate triangle dimensions based on braille dot spacing
    2 * settings.dot_spacing
    triangle_width = settings.dot_spacing

    # Triangle vertices (same as 2D version)
    base_x = x - settings.dot_spacing / 2  # Left column position

    vertices = [
        (base_x, y - settings.dot_spacing),  # Bottom of base
        (base_x, y + settings.dot_spacing),  # Top of base
        (base_x + triangle_width, y),  # Apex (at middle-right dot height)
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
    2 * settings.dot_spacing  # Vertical extent (same as cell height)
    line_width = settings.dot_spacing  # Horizontal extent

    # Position line at the right column of the cell
    # The line should be centered on the right column dot positions
    line_x = x + settings.dot_spacing / 2  # Right column position

    # Create rectangle vertices
    vertices = [
        (line_x - line_width / 2, y - settings.dot_spacing),  # Bottom left
        (line_x + line_width / 2, y - settings.dot_spacing),  # Bottom right
        (line_x + line_width / 2, y + settings.dot_spacing),  # Top right
        (line_x - line_width / 2, y + settings.dot_spacing),  # Top left
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


def _build_character_polygon(char_upper: str, target_width: float, target_height: float):
    """
    Build a 2D character outline as a shapely polygon, scaled to fit within
    the provided target width/height, centered at origin. Uses matplotlib if
    available; returns None on failure so callers can fall back gracefully.
    """
    try:
        # Lazy import to keep serverless light
        try:
            from matplotlib.font_manager import FontProperties  # type: ignore
            from matplotlib.path import Path  # type: ignore
            from matplotlib.textpath import TextPath  # type: ignore
        except Exception:
            return None

        # Preferred tactile-friendly font with robust fallback
        try:
            font_prop = FontProperties(family='Arial Rounded MT Bold', weight='bold')
        except Exception:
            font_prop = FontProperties(family='monospace', weight='bold')

        # Matplotlib expects points; approximate 1 mm ≈ 2.835 pt
        font_size = max(target_height, target_width) * 2.835

        text_path = TextPath((0, 0), char_upper, size=font_size, prop=font_prop)
        vertices = text_path.vertices
        codes = text_path.codes

        # Convert matplotlib path codes to polygons
        polygons = []
        current_polygon = []
        i = 0
        while i < len(codes):
            code = codes[i]
            if code == Path.MOVETO:
                if current_polygon and len(current_polygon) >= 3:
                    polygons.append(Polygon(current_polygon))
                current_polygon = [tuple(vertices[i])]
            elif code == Path.LINETO:
                current_polygon.append(tuple(vertices[i]))
            elif code == Path.CURVE3:
                if i + 1 < len(codes):
                    current_polygon.append(tuple(vertices[i]))
                    current_polygon.append(tuple(vertices[i + 1]))
                    i += 1
            elif code == Path.CURVE4:
                if i + 2 < len(codes):
                    current_polygon.append(tuple(vertices[i]))
                    current_polygon.append(tuple(vertices[i + 1]))
                    current_polygon.append(tuple(vertices[i + 2]))
                    i += 2
            elif code == Path.CLOSEPOLY:
                if current_polygon and len(current_polygon) >= 3:
                    polygons.append(Polygon(current_polygon))
                current_polygon = []
            i += 1

        if current_polygon and len(current_polygon) >= 3:
            polygons.append(Polygon(current_polygon))
        if not polygons:
            return None

        char_2d = unary_union(polygons)
        if char_2d.is_empty:
            return None

        bounds = char_2d.bounds
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        if w <= 0 or h <= 0:
            return None

        # Uniform scale to fit within target rectangle with margin
        scale = min(target_width / w, target_height / h) * 0.8
        from shapely import affinity as _affinity

        char_2d = _affinity.scale(char_2d, xfact=scale, yfact=scale, origin=(0, 0))
        # Center at origin
        c = char_2d.centroid
        char_2d = _affinity.translate(char_2d, xoff=-c.x, yoff=-c.y)

        # Simplify slightly to reduce triangulation issues
        char_2d = char_2d.simplify(0.05, preserve_topology=True)
        if not char_2d.is_valid:
            char_2d = char_2d.buffer(0)
        return char_2d
    except Exception:
        return None


# _compute_cylinder_frame now imported from app.geometry.cylinder


def create_character_shape_3d(character, x, y, settings: CardSettings, height=1.0, for_subtraction=True):
    """
    Create a 3D character shape (capital letter A-Z or number 0-9) for end of row marking.
    Uses matplotlib's TextPath for proper font rendering.

    Args:
        character: Single character (A-Z or 0-9)
        x, y: Center position of the last braille cell in the row
        settings: CardSettings object with spacing parameters
        height: Depth of the character recess (default 1.0mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses

    Returns:
        Trimesh object representing the 3D character marker
    """
    # Debug: character marker generation

    # Define character size based on braille cell dimensions (scaled 56.25% bigger than original)
    char_height = 2 * settings.dot_spacing + 4.375  # 9.375mm for default 2.5mm dot spacing
    char_width = settings.dot_spacing * 0.8 + 2.6875  # 4.6875mm for default 2.5mm dot spacing

    # Position character at the right column of the cell
    char_x = x + settings.dot_spacing / 2
    char_y = y

    # Get the character definition
    char_upper = character.upper()
    if not (char_upper.isalpha() or char_upper.isdigit()):
        # Fall back to rectangle for undefined characters
        return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)

    try:
        # Build character polygon using shared helper (handles matplotlib/lazy import)
        char_2d = _build_character_polygon(char_upper, char_width, char_height)
        if char_2d is None:
            return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)

        # Translate to desired position
        from shapely import affinity as _affinity

        char_2d = _affinity.translate(char_2d, xoff=char_x, yoff=char_y)

    except Exception as e:
        logger.warning(f'Failed to create character shape using matplotlib: {e}')
        logger.info('Falling back to rectangle marker')
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
                    logger.warning('Character mesh is not a valid volume')
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
        logger.warning(f'Failed to extrude character shape: {e}')
        return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)

    # Debug: character marker generated
    return char_prism


def create_positive_plate_mesh(lines, grade='g1', settings=None, original_lines=None):
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

    grade_name = f'Grade {grade.upper()}' if grade in ['g1', 'g2'] else 'Grade 1'
    logger.info(f'Creating positive plate mesh with {grade_name} characters')
    logger.info(f'Grid: {settings.grid_columns} columns × {settings.grid_rows} rows')
    logger.info(f'Centered margins: L/R={settings.left_margin:.2f}mm, T/B={settings.top_margin:.2f}mm')
    print(
        f'Spacing: Cell-to-cell {settings.cell_spacing}mm, Line-to-line {settings.line_spacing}mm, Dot-to-dot {settings.dot_spacing}mm'
    )

    # Create card base
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width / 2, settings.card_height / 2, settings.card_thickness / 2))

    meshes = [base]
    marker_meshes = []  # Store markers separately for subtraction

    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]

    # Add end-of-row text/number indicators and triangle markers for ALL rows (not just those with content)
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = (
            settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        )

        if getattr(settings, 'indicator_shapes', 1):
            # Add end-of-row text/number indicator at the first cell position (column 0)
            # Calculate X position for the first column
            x_pos_first = settings.left_margin + settings.braille_x_adjust

            # Determine which character to use for beginning-of-row indicator
            # In manual mode: first character from the corresponding manual line
            # In auto mode: original_lines is an array of per-row indicator characters
            print(
                f'DEBUG: Row {row_num}, original_lines provided: {original_lines is not None}, length: {len(original_lines) if original_lines else 0}'
            )
            if original_lines and row_num < len(original_lines):
                orig = (original_lines[row_num] or '').strip()
                # If auto supplied a single indicator character per row, just use it
                indicator_char = orig[0] if orig else ''
                logger.debug(f"Row {row_num} indicator candidate: '{indicator_char}'")
                if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
                    logger.debug(f"Creating character shape for '{indicator_char}' at first cell")
                    line_end_mesh = create_character_shape_3d(
                        indicator_char, x_pos_first, y_pos, settings, height=1.0, for_subtraction=True
                    )
                else:
                    logger.debug(f'Indicator not alphanumeric or empty, using rectangle for row {row_num}')
                    line_end_mesh = create_card_line_end_marker_3d(
                        x_pos_first, y_pos, settings, height=0.5, for_subtraction=True
                    )
            else:
                # No indicator info; default to rectangle
                logger.debug(f'No indicator info for row {row_num}, using rectangle')
                line_end_mesh = create_card_line_end_marker_3d(
                    x_pos_first, y_pos, settings, height=0.5, for_subtraction=True
                )

            marker_meshes.append(line_end_mesh)

            # Add triangle marker at the last cell position (grid_columns - 1)
            # Calculate X position for the last column
            x_pos_last = (
                settings.left_margin + ((settings.grid_columns - 1) * settings.cell_spacing) + settings.braille_x_adjust
            )

            # Create triangle marker for this row (recessed for embossing plate)
            triangle_mesh = create_card_triangle_marker_3d(
                x_pos_last, y_pos, settings, height=0.6, for_subtraction=True
            )
            marker_meshes.append(triangle_mesh)

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
            error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters. Frontend must translate text to braille before sending.'
            logger.error(f'{error_msg}')
            raise RuntimeError(error_msg)

        # Check if braille text exceeds grid capacity
        reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
        available_columns = settings.grid_columns - reserved
        if len(braille_text) > available_columns:
            # Warn and truncate instead of failing hard
            over = len(braille_text) - available_columns
            print(
                f'WARNING: Line {row_num + 1} exceeds available columns by {over} cells. '
                f'Truncating to {available_columns} cells to continue generation.'
            )
            braille_text = braille_text[:available_columns]

        # Calculate Y position for this row (top-down)
        y_pos = (
            settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        )

        # Process each braille character in the line
        for col_num, braille_char in enumerate(braille_text):
            if col_num >= available_columns:
                break

            dots = braille_to_dots(braille_char)

            # Calculate X position for this column. Shift by one cell if indicators are enabled.
            x_pos = (
                settings.left_margin
                + ((col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)) * settings.cell_spacing)
                + settings.braille_x_adjust
            )

            # Create dots for this cell
            for i, dot_val in enumerate(dots):
                if dot_val == 1:
                    dot_pos = dot_positions[i]
                    dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                    dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                    # Position Z by active dot height so the dot sits on the surface
                    z = settings.card_thickness + settings.active_dot_height / 2

                    dot_mesh = create_braille_dot(dot_x, dot_y, z, settings)
                    meshes.append(dot_mesh)

    if getattr(settings, 'indicator_shapes', 1):
        print(
            f'Created positive plate with {len(meshes) - 1} braille dots, {settings.grid_rows} text/number indicators, and {settings.grid_rows} triangle markers'
        )
    else:
        logger.info(f'Created positive plate with {len(meshes) - 1} braille dots and no indicator shapes')

    # Combine all positive meshes (base + dots)
    combined_mesh = trimesh.util.concatenate(meshes)

    # Subtract marker recesses from the combined mesh (avoid heavy 3D booleans on serverless)
    if getattr(settings, 'indicator_shapes', 1) and marker_meshes and not _is_serverless_env():
        try:
            # Union all markers for efficient boolean operation
            if len(marker_meshes) == 1:
                union_markers = marker_meshes[0]
            else:
                union_markers = trimesh.boolean.union(marker_meshes)

            logger.debug(f'Subtracting {len(marker_meshes)} marker recesses from embossing plate...')
            # Subtract markers to create recesses
            combined_mesh = trimesh.boolean.difference([combined_mesh, union_markers])
            logger.debug('Marker subtraction successful')
        except Exception as e:
            logger.warning(f'Could not create marker recesses: {e}')
            logger.info('Returning embossing plate without marker recesses')

    return combined_mesh


def create_simple_negative_plate(settings: CardSettings, lines=None):
    """
    Create a negative plate with recessed holes using 2D Shapely operations for Vercel compatibility.
    This creates a counter plate with holes that match the embossing plate dimensions and positioning.
    """

    # Create base rectangle for the card
    base_polygon = Polygon(
        [(0, 0), (settings.card_width, 0), (settings.card_width, settings.card_height), (0, settings.card_height)]
    )

    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Create holes for the actual text content (not all possible positions)
    holes = []
    total_dots = 0

    # Calculate hole radius based on dot dimensions plus offset
    # Counter plate holes should be slightly larger than embossing dots for proper alignment
    hole_radius = settings.recessed_dot_base_diameter / 2

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
                logger.warning(f'Line {row_num + 1} does not contain proper braille Unicode, skipping')
                continue

            # Calculate Y position for this row (same as embossing plate, using safe margin)
            y_pos = (
                settings.card_height
                - settings.top_margin
                - (row_num * settings.line_spacing)
                + settings.braille_y_adjust
            )

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
        logger.warning('No holes were created! Creating a plate with all possible holes as fallback')
        # Fallback: create holes for all possible positions
        return create_universal_counter_plate_fallback(settings)

    # Combine all holes into one multi-polygon
    try:
        all_holes = unary_union(holes)

        # Subtract holes from base to create the plate with holes
        plate_with_holes = base_polygon.difference(all_holes)

    except Exception as e:
        app.logger.error(f'Failed to combine holes or subtract from base: {e}')
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
        app.logger.error(f'Failed to extrude polygon: {e}')
        # Fallback to simple base plate if extrusion fails
        return create_fallback_plate(settings)


def create_universal_counter_plate_fallback(settings: CardSettings):
    """Create a counter plate with all possible holes as fallback when text-based holes fail"""

    # Create base rectangle for the card
    base_polygon = Polygon(
        [(0, 0), (settings.card_width, 0), (settings.card_width, settings.card_height), (0, settings.card_height)]
    )

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
        logger.error(f'Fallback counter plate creation failed: {e}')
        return create_fallback_plate(settings)


def create_fallback_plate(settings: CardSettings):
    """Create a simple fallback plate when hole creation fails"""
    logger.warning('Creating fallback plate without holes')
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width / 2, settings.card_height / 2, settings.card_thickness / 2))
    return base


# layout_cylindrical_cells now imported from app.geometry.cylinder


# cylindrical_transform now imported from app.geometry.cylinder


# create_cylinder_shell now imported from app.geometry.cylinder

# create_cylinder_triangle_marker now imported from app.geometry.cylinder

# create_cylinder_line_end_marker now imported from app.geometry.cylinder

# create_cylinder_character_shape now imported from app.geometry.cylinder

# create_cylinder_braille_dot now imported from app.geometry.cylinder

# generate_cylinder_stl now imported from app.geometry.cylinder

# generate_cylinder_counter_plate now imported from app.geometry.cylinder


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
    - Hemisphere radius r = counter_dot_base_diameter / 2 (or legacy: (emboss_dot_base_diameter + counter_plate_dot_size_offset) / 2).
    - For each dot center (x, y) in the braille grid, creates an icosphere with radius r
      and translates its center to (x, y, TH - r + ε) so the lower hemisphere sits inside the slab
      and the equator coincides with the top surface.
    - Subtracts all spheres in one operation using trimesh.boolean.difference with built-in engine.
    - Generates dot centers from a full grid using the same layout parameters as the Embossing Plate.
    - Always places all 6 dots per cell (does not consult per-character translation).
    """

    # Create the base plate as a box aligned to z=[0, TH], x=[0, W], y=[0, H]
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width / 2, params.card_height / 2, params.plate_thickness / 2))

    print(
        f'DEBUG: Creating counter plate base: {params.card_width}mm x {params.card_height}mm x {params.plate_thickness}mm'
    )

    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]

    # Calculate hemisphere radius including the counter plate offset
    try:
        counter_base = float(getattr(params, 'hemi_counter_dot_base_diameter', params.counter_dot_base_diameter))
    except Exception:
        counter_base = params.emboss_dot_base_diameter + params.counter_plate_dot_size_offset
    hemisphere_radius = counter_base / 2
    print(
        f'DEBUG: Hemisphere radius: {hemisphere_radius:.3f}mm (base: {params.emboss_dot_base_diameter}mm + offset: {params.counter_plate_dot_size_offset}mm)'
    )

    # Create icospheres (hemispheres) for ALL possible dot positions
    sphere_meshes = []
    total_spheres = 0

    # Generate spheres for each grid position
    for row in range(params.grid_rows):
        # Calculate Y position for this row (same as embossing plate, using safe margin)
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust

        # Process columns (reserve two if indicators enabled)
        reserved = 2 if getattr(params, 'indicator_shapes', 1) else 0
        for col in range(params.grid_columns - reserved):
            # Calculate X position for this column (shift by one if indicators enabled)
            x_pos = (
                params.left_margin
                + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing)
                + params.braille_x_adjust
            )

            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]

                # Create an icosphere with the calculated hemisphere radius
                # Use hemisphere_subdivisions parameter to control mesh density
                sphere = trimesh.creation.icosphere(
                    subdivisions=params.hemisphere_subdivisions, radius=hemisphere_radius
                )
                # Position the sphere so its equator lies at the top surface (z = plate_thickness)
                z_pos = params.plate_thickness
                sphere.apply_translation((dot_x, dot_y, z_pos))
                sphere_meshes.append(sphere)
                total_spheres += 1

    logger.debug(f'Created {total_spheres} hemispheres for counter plate')

    # Create end of row line recesses and triangle marker recesses for ALL rows
    line_end_meshes = []
    triangle_meshes = []
    for row_num in range(params.grid_rows):
        # Calculate Y position for this row
        y_pos = params.card_height - params.top_margin - (row_num * params.line_spacing) + params.braille_y_adjust

        # Add end of row line marker at the first cell position (column 0) to match embossing plate layout
        x_pos_first = params.left_margin + params.braille_x_adjust

        # Create line end marker for subtraction (will create recess)
        line_end_mesh = create_card_line_end_marker_3d(x_pos_first, y_pos, params, height=0.5, for_subtraction=True)
        line_end_meshes.append(line_end_mesh)

        # Add triangle marker at the last cell position (grid_columns - 1) to match embossing plate layout
        x_pos_last = params.left_margin + ((params.grid_columns - 1) * params.cell_spacing) + params.braille_x_adjust

        # Create triangle marker for subtraction (recessed triangle in counter plate)
        triangle_mesh = create_card_triangle_marker_3d(x_pos_last, y_pos, params, height=0.5, for_subtraction=True)
        triangle_meshes.append(triangle_mesh)

    print(
        f'DEBUG: Created {len(triangle_meshes)} triangle markers and {len(line_end_meshes)} line end markers for counter plate'
    )

    if not sphere_meshes:
        logger.warning('No spheres were generated. Returning base plate.')
        return plate_mesh

    # Perform boolean operations - try trimesh default first (serverless-compatible)
    engines_to_try = [None]  # None uses trimesh built-in boolean engine (no external dependencies)

    for engine in engines_to_try:
        try:
            engine_name = engine if engine else 'trimesh-default'
            logger.debug(f'Attempting boolean operations with {engine_name} engine...')

            # Union all spheres together for more efficient subtraction
            if len(sphere_meshes) == 1:
                union_spheres = sphere_meshes[0]
            else:
                logger.debug('Unioning spheres...')
                union_spheres = trimesh.boolean.union(sphere_meshes, engine=engine)

            # Union all triangles (these will be used for subtraction into the plate)
            union_triangles = None
            if triangle_meshes:
                logger.debug(f'Unioning {len(triangle_meshes)} triangles (for subtraction)...')
                if len(triangle_meshes) == 1:
                    union_triangles = triangle_meshes[0]
                else:
                    union_triangles = trimesh.boolean.union(triangle_meshes, engine=engine)

            # Union all line end markers
            if line_end_meshes:
                logger.debug(f'Unioning {len(line_end_meshes)} line end markers...')
                if len(line_end_meshes) == 1:
                    union_line_ends = line_end_meshes[0]
                else:
                    union_line_ends = trimesh.boolean.union(line_end_meshes, engine=engine)

            # Combine cutouts (spheres and line ends) for subtraction
            logger.debug('Combining cutouts for subtraction...')
            cutouts_list = [union_spheres]
            if line_end_meshes:
                cutouts_list.append(union_line_ends)
            if union_triangles is not None:
                cutouts_list.append(union_triangles)

            if len(cutouts_list) > 1:
                all_cutouts = trimesh.boolean.union(cutouts_list, engine=engine)
            else:
                all_cutouts = cutouts_list[0]

            logger.debug('Subtracting cutouts from plate...')
            # Subtract the cutouts (spheres, line ends, and triangles) from the plate
            counter_plate_mesh = trimesh.boolean.difference([plate_mesh, all_cutouts], engine=engine)

            # Verify the mesh is watertight
            if not counter_plate_mesh.is_watertight:
                logger.debug('Counter plate mesh not watertight, attempting to fix...')
                counter_plate_mesh.fill_holes()
                if counter_plate_mesh.is_watertight:
                    logger.debug('Successfully fixed counter plate mesh')

            print(
                f'DEBUG: Counter plate completed with {engine_name} engine: {len(counter_plate_mesh.vertices)} vertices, {len(counter_plate_mesh.faces)} faces'
            )
            return counter_plate_mesh

        except Exception as e:
            logger.error(f'Boolean operations with {engine_name} failed: {e}')
            if engine == engines_to_try[-1]:  # Last engine failed
                print(
                    'WARNING: All boolean engines failed. Creating hemisphere counter plate with individual subtraction...'
                )
                break
            else:
                logger.warning('Trying next engine...')
                continue

    # Final fallback: subtract spheres and triangles one by one (slower but more reliable)
    try:
        logger.debug('Attempting individual sphere and triangle subtraction...')
        counter_plate_mesh = plate_mesh.copy()

        for i, sphere in enumerate(sphere_meshes):
            try:
                logger.debug(f'Subtracting sphere {i + 1}/{len(sphere_meshes)}...')
                counter_plate_mesh = trimesh.boolean.difference([counter_plate_mesh, sphere])
            except Exception as sphere_error:
                logger.warning(f'Failed to subtract sphere {i + 1}: {sphere_error}')
                continue

        # Subtract triangles individually (recess them)
        for i, triangle in enumerate(triangle_meshes):
            try:
                logger.debug(f'Subtracting triangle {i + 1}/{len(triangle_meshes)}...')
                counter_plate_mesh = trimesh.boolean.difference([counter_plate_mesh, triangle])
            except Exception as triangle_error:
                logger.warning(f'Failed to subtract triangle {i + 1}: {triangle_error}')
                continue

        # Subtract line end markers individually
        for i, line_end in enumerate(line_end_meshes):
            try:
                logger.debug(f'Subtracting line end marker {i + 1}/{len(line_end_meshes)}...')
                counter_plate_mesh = trimesh.boolean.difference([counter_plate_mesh, line_end])
            except Exception as line_error:
                logger.warning(f'Failed to subtract line end marker {i + 1}: {line_error}')
                continue

        # Try to fix the mesh
        if not counter_plate_mesh.is_watertight:
            counter_plate_mesh.fill_holes()

        print(
            f'DEBUG: Individual subtraction completed: {len(counter_plate_mesh.vertices)} vertices, {len(counter_plate_mesh.faces)} faces'
        )
        return counter_plate_mesh

    except Exception as final_error:
        logger.error(f'Individual sphere subtraction failed: {final_error}')
        logger.warning('Falling back to simple negative plate method.')
        # Final fallback to the simple approach
        return create_simple_negative_plate(params)


def build_counter_plate_bowl(params: CardSettings) -> trimesh.Trimesh:
    """Create a counter plate with spherical-cap (bowl) recesses of independent depth.

    The opening diameter at the surface is set by `counter_dot_base_diameter`.
    The recess depth is independently controlled by `counter_dot_depth`.

    For each dot, we compute a sphere of radius R such that a^2 = 2 R h - h^2,
    where a = opening radius and h = desired depth, and place the sphere center
    at z = TH - (R - h) so its intersection at the top surface matches the opening.
    """

    # Base plate
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width / 2, params.card_height / 2, params.plate_thickness / 2))

    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Inputs
    a = (
        float(getattr(params, 'bowl_counter_dot_base_diameter', getattr(params, 'counter_dot_base_diameter', 1.6)))
        / 2.0
    )
    h = float(getattr(params, 'counter_dot_depth', 0.6))
    # Guard against zero or negative depth
    if h <= max(0.0, float(getattr(params, 'epsilon_mm', 0.001))):
        # Degenerate: fall back to hemisphere (very shallow)
        return build_counter_plate_hemispheres(params)

    # Compute sphere radius from opening radius and depth: R = (a^2 + h^2) / (2h)
    R = (a * a + h * h) / (2.0 * h)

    # Build spheres
    sphere_meshes = []
    total_spheres = 0
    for row in range(params.grid_rows):
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust
        reserved = 2 if getattr(params, 'indicator_shapes', 1) else 0
        for col in range(params.grid_columns - reserved):
            x_pos = (
                params.left_margin
                + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing)
                + params.braille_x_adjust
            )
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]

                sphere = trimesh.creation.icosphere(subdivisions=params.hemisphere_subdivisions, radius=R)
                # Place center below the surface by c = R - h
                zc = params.plate_thickness - (R - h)
                sphere.apply_translation((dot_x, dot_y, zc))
                sphere_meshes.append(sphere)
                total_spheres += 1

    logger.debug(f'Created {total_spheres} bowl caps for counter plate (a={a:.3f}mm, h={h:.3f}mm, R={R:.3f}mm)')

    # Markers (same as hemispheres)
    line_end_meshes = []
    triangle_meshes = []
    for row_num in range(params.grid_rows):
        y_pos = params.card_height - params.top_margin - (row_num * params.line_spacing) + params.braille_y_adjust
        x_pos_first = params.left_margin + params.braille_x_adjust
        line_end_mesh = create_card_line_end_marker_3d(x_pos_first, y_pos, params, height=0.5, for_subtraction=True)
        line_end_meshes.append(line_end_mesh)
        x_pos_last = params.left_margin + ((params.grid_columns - 1) * params.cell_spacing) + params.braille_x_adjust
        triangle_mesh = create_card_triangle_marker_3d(x_pos_last, y_pos, params, height=0.5, for_subtraction=True)
        triangle_meshes.append(triangle_mesh)

    if not sphere_meshes:
        logger.warning('No spheres were generated. Returning base plate.')
        return plate_mesh

    # Boolean operations - use trimesh default (serverless-compatible)
    engines_to_try = [None]  # None uses trimesh built-in boolean engine
    for engine in engines_to_try:
        try:
            engine_name = engine if engine else 'trimesh-default'
            logger.debug(f'Bowl boolean ops with {engine_name}...')

            if len(sphere_meshes) == 1:
                union_spheres = sphere_meshes[0]
            else:
                union_spheres = trimesh.boolean.union(sphere_meshes, engine=engine)

            union_triangles = None
            if triangle_meshes:
                if len(triangle_meshes) == 1:
                    union_triangles = triangle_meshes[0]
                else:
                    union_triangles = trimesh.boolean.union(triangle_meshes, engine=engine)

            if line_end_meshes:
                if len(line_end_meshes) == 1:
                    union_line_ends = line_end_meshes[0]
                else:
                    union_line_ends = trimesh.boolean.union(line_end_meshes, engine=engine)

            cutouts_list = [union_spheres]
            if line_end_meshes:
                cutouts_list.append(union_line_ends)
            if union_triangles is not None:
                cutouts_list.append(union_triangles)

            if len(cutouts_list) > 1:
                all_cutouts = trimesh.boolean.union(cutouts_list, engine=engine)
            else:
                all_cutouts = cutouts_list[0]

            counter_plate_mesh = trimesh.boolean.difference([plate_mesh, all_cutouts], engine=engine)
            if not counter_plate_mesh.is_watertight:
                counter_plate_mesh.fill_holes()
            logger.debug(f'Counter plate with bowl recess completed: {len(counter_plate_mesh.vertices)} verts')
            return counter_plate_mesh
        except Exception as e:
            logger.error(f'Bowl boolean with {engine_name} failed: {e}')
            if engine == engines_to_try[-1]:
                logger.warning('Falling back to simple negative plate method.')
                return create_simple_negative_plate(params)
            continue


def build_counter_plate_cone(params: CardSettings) -> trimesh.Trimesh:
    """Create a counter plate with conical frustum recesses.

    The opening diameter at the surface is set by `cone_counter_dot_base_diameter`.
    The recess height is `cone_counter_dot_height`.
    The flat hat diameter at the tip is `cone_counter_dot_flat_hat`.
    """

    # Base plate
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width / 2, params.card_height / 2, params.plate_thickness / 2))

    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Inputs
    base_d = float(getattr(params, 'cone_counter_dot_base_diameter', getattr(params, 'counter_dot_base_diameter', 1.6)))
    hat_d = float(getattr(params, 'cone_counter_dot_flat_hat', 0.4))
    height_h = float(getattr(params, 'cone_counter_dot_height', 0.8))
    base_r = max(params.epsilon_mm, base_d / 2.0)
    hat_r = max(params.epsilon_mm, hat_d / 2.0)
    height_h = max(params.epsilon_mm, min(height_h, params.plate_thickness - params.epsilon_mm))
    # Small positive overlap above the top surface to avoid coplanar boolean issues
    overcut_z = max(params.epsilon_mm, 0.05)

    # OPTIMIZATION: Use configurable segments for better performance while maintaining shape quality
    # Default to 16 segments - still provides good circular approximation, but allow user control
    segments = int(getattr(params, 'cone_segments', 16))
    segments = max(8, min(32, segments))  # Clamp to valid range

    # OPTIMIZATION: Pre-calculate common values to avoid repeated computation
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    cos_angles = np.cos(angles)
    sin_angles = np.sin(angles)

    # Create conical frustum solids for subtraction using optimized approach
    recess_meshes = []
    total_recess = 0
    for row in range(params.grid_rows):
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust
        reserved = 2 if getattr(params, 'indicator_shapes', 1) else 0
        for col in range(params.grid_columns - reserved):
            x_pos = (
                params.left_margin
                + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing)
                + params.braille_x_adjust
            )
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]

                # OPTIMIZATION: Use pre-calculated trigonometric values
                top_ring = np.column_stack([base_r * cos_angles, base_r * sin_angles, np.zeros_like(angles)])
                bot_ring = np.column_stack([hat_r * cos_angles, hat_r * sin_angles, -height_h * np.ones_like(angles)])
                vertices = np.vstack([top_ring, bot_ring, [[0, 0, 0]], [[0, 0, -height_h]]])
                top_center_index = 2 * segments
                bot_center_index = 2 * segments + 1

                # OPTIMIZATION: Pre-allocate faces array for better performance
                faces = np.zeros((segments * 4, 3), dtype=int)
                face_idx = 0

                for i in range(segments):
                    j = (i + 1) % segments
                    ti = i
                    tj = j
                    bi = segments + i
                    bj = segments + j
                    # side quads as two triangles (ensure correct orientation for outward normals)
                    faces[face_idx] = [ti, bi, tj]
                    faces[face_idx + 1] = [bi, bj, tj]
                    # top cap (at z=0) - outward normal pointing up
                    faces[face_idx + 2] = [top_center_index, ti, tj]
                    # bottom cap (at z=-height_h) - outward normal pointing down
                    faces[face_idx + 3] = [bot_center_index, bj, bi]
                    face_idx += 4

                # OPTIMIZATION: Create mesh with minimal processing and skip extensive repair operations
                frustum = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

                # OPTIMIZATION: Only perform essential mesh validation
                if not frustum.is_volume:
                    try:
                        frustum.fix_normals()
                        if not frustum.is_watertight:
                            frustum.fill_holes()
                    except Exception:
                        # Skip extensive repair operations for better performance
                        pass

                # Position with slight overlap so top cap is slightly above the surface to ensure robust boolean subtraction
                frustum.apply_translation((dot_x, dot_y, params.plate_thickness + overcut_z))
                recess_meshes.append(frustum)
                total_recess += 1

    # Markers (same as hemispheres/bowl)
    line_end_meshes = []
    triangle_meshes = []
    for row_num in range(params.grid_rows):
        y_pos = params.card_height - params.top_margin - (row_num * params.line_spacing) + params.braille_y_adjust
        x_pos_first = params.left_margin + params.braille_x_adjust
        line_end_mesh = create_card_line_end_marker_3d(x_pos_first, y_pos, params, height=0.5, for_subtraction=True)
        line_end_meshes.append(line_end_mesh)
        x_pos_last = params.left_margin + ((params.grid_columns - 1) * params.cell_spacing) + params.braille_x_adjust
        triangle_mesh = create_card_triangle_marker_3d(x_pos_last, y_pos, params, height=0.5, for_subtraction=True)
        triangle_meshes.append(triangle_mesh)

    if not recess_meshes:
        logger.warning('No cone recesses were generated. Returning base plate.')
        return plate_mesh

    print(
        f'DEBUG: Created {total_recess} cone frusta for counter plate (base_d={base_d:.3f}mm, hat_d={hat_d:.3f}mm, h={height_h:.3f}mm)'
    )

    # OPTIMIZATION: Use union operations like bowl/hemisphere for better performance
    try:
        # Union all recess meshes first (like bowl/hemisphere approach)
        if len(recess_meshes) == 1:
            union_recesses = recess_meshes[0]
        else:
            # Use trimesh default engine (serverless-compatible)
            engines_to_try = [None]  # None uses trimesh built-in boolean engine
            union_recesses = None
            for engine in engines_to_try:
                try:
                    engine_name = engine if engine else 'trimesh-default'
                    logger.debug(f'Cone union with {engine_name}...')
                    union_recesses = trimesh.boolean.union(recess_meshes, engine=engine)
                    break
                except Exception as e:
                    logger.warning(f'Failed to union with {engine_name}: {e}')
                    continue

            if union_recesses is None:
                raise Exception('All union engines failed')

        # Union markers
        union_triangles = None
        if triangle_meshes:
            if len(triangle_meshes) == 1:
                union_triangles = triangle_meshes[0]
            else:
                union_triangles = trimesh.boolean.union(triangle_meshes)

        union_line_ends = None
        if line_end_meshes:
            if len(line_end_meshes) == 1:
                union_line_ends = line_end_meshes[0]
            else:
                union_line_ends = trimesh.boolean.union(line_end_meshes)

        # Combine all cutouts
        cutouts_list = [union_recesses]
        if union_line_ends is not None:
            cutouts_list.append(union_line_ends)
        if union_triangles is not None:
            cutouts_list.append(union_triangles)

        # Single difference operation (much faster than individual subtractions)
        if len(cutouts_list) > 1:
            union_cutouts = trimesh.boolean.union(cutouts_list)
        else:
            union_cutouts = cutouts_list[0]

        result_mesh = trimesh.boolean.difference([plate_mesh, union_cutouts])

        if not result_mesh.is_watertight:
            result_mesh.fill_holes()
        logger.debug(f'Cone recess (optimized union approach) completed: {len(result_mesh.vertices)} verts')
        return result_mesh

    except Exception as e_final:
        logger.error(f'Cone recess union approach failed: {e_final}')
        logger.warning('Falling back to individual subtraction method.')

        # Fallback to individual subtraction if union approach fails
        try:
            result_mesh = plate_mesh.copy()
            for i, recess in enumerate(recess_meshes):
                try:
                    if (i % 50) == 0:
                        logger.debug(f'Subtracting cone frustum {i + 1}/{len(recess_meshes)}...')
                    result_mesh = trimesh.boolean.difference([result_mesh, recess])
                except Exception as e_sub:
                    logger.warning(f'Failed to subtract frustum {i + 1}: {e_sub}')
                    continue
            for i, triangle in enumerate(triangle_meshes):
                try:
                    result_mesh = trimesh.boolean.difference([result_mesh, triangle])
                except Exception as e_tri:
                    logger.warning(f'Failed to subtract triangle {i + 1}: {e_tri}')
                    continue
            for i, line_end in enumerate(line_end_meshes):
                try:
                    result_mesh = trimesh.boolean.difference([result_mesh, line_end])
                except Exception as e_line:
                    logger.warning(f'Failed to subtract line end {i + 1}: {e_line}')
                    continue
            if not result_mesh.is_watertight:
                result_mesh.fill_holes()
            logger.debug(f'Cone recess (fallback individual subtraction) completed: {len(result_mesh.vertices)} verts')
            return result_mesh
        except Exception as e_fallback:
            logger.error(f'All cone recess methods failed: {e_fallback}')
            logger.warning('Returning simple negative plate method.')
            return create_simple_negative_plate(params)


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Vercel backend is running'})


@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.info(f'Error rendering template: {e}')
        return jsonify({'error': 'Failed to load template'}), 500


# @app.route('/node_modules/<path:filename>')
# def node_modules(filename):
#     """Redirect node_modules requests to static files for Vercel deployment"""
#     # Map common node_modules paths to static equivalents
#     if filename.startswith('liblouis-build/') or filename.startswith('liblouis/'):
#         # Remove the 'liblouis-build/' or 'liblouis/' prefix and redirect to static
#         static_path = filename.replace('liblouis-build/', 'liblouis/').replace('liblouis/', 'liblouis/')
#         return redirect(f'/static/{static_path}')
#
#     # For other node_modules requests, return 404
#     return jsonify({'error': 'node_modules not available on deployment'}), 404


@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests to prevent 404 errors"""
    return '', 204  # Return empty response with "No Content" status


@app.route('/favicon.png')
def favicon_png():
    """Serve or gracefully handle /favicon.png requests"""
    try:
        static_dir = 'static'
        png_path = os.path.join(static_dir, 'favicon.png')
        ico_path = os.path.join(static_dir, 'favicon.ico')
        # Prefer a real png if present
        if os.path.exists(png_path) and os.path.isfile(png_path):
            return send_from_directory(static_dir, 'favicon.png')
        # Fall back to ico if present
        if os.path.exists(ico_path) and os.path.isfile(ico_path):
            return send_from_directory(static_dir, 'favicon.ico')
        # Nothing available; avoid noisy 404 -> return 204
        return '', 204
    except Exception as e:
        app.logger.error(f'Failed to serve favicon: {e}')
        return '', 204


@app.route('/static/<path:filename>', methods=['GET', 'OPTIONS'])
def static_files(filename):
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'OK'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

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
            app.logger.error('Static directory not found')
            return jsonify({'error': 'Resource not found'}), 404

        # Check if file exists
        full_path = os.path.join('static', safe_path)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return jsonify({'error': 'File not found'}), 404

        # Additional security: ensure the resolved path is still under static/
        if not os.path.abspath(full_path).startswith(os.path.abspath('static')):
            return jsonify({'error': 'Invalid file path'}), 400

        response = send_from_directory('static', safe_path)

        # Add CORS headers for liblouis files to ensure they can be loaded by web workers
        if 'liblouis' in safe_path:
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            # Set appropriate content type for liblouis table files
            if safe_path.endswith('.ctb') or safe_path.endswith('.utb') or safe_path.endswith('.dis'):
                response.headers['Content-Type'] = 'text/plain; charset=utf-8'

        return response
    except Exception as e:
        app.logger.error(f'Failed to serve static file {filename}: {e}')
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
                    with open(fpath, encoding='utf-8', errors='ignore') as f:
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
                            loc = f'{parts[0]}-{parts[1]}'
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
@limiter.limit('10 per minute')
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
        placement_mode = data.get('placement_mode', 'manual')
        plate_type = data.get('plate_type', 'positive')
        grade = data.get('grade', 'g2')
        settings_data = data.get('settings', {})
        shape_type = data.get('shape_type', 'card')  # New: default to 'card' for backward compatibility
        cylinder_params = data.get('cylinder_params', {})  # New: optional cylinder parameters
        per_line_language_tables = data.get('per_line_language_tables', None)  # Optional: per-line liblouis tables used

        # Validate inputs
        validate_lines(lines)
        validate_settings(settings_data)

        # Validate braille characters for positive plates
        validate_braille_lines(lines, plate_type)

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
        app.logger.error(f'Validation error in generate_braille_stl: {e}')
        return jsonify({'error': 'Invalid request data'}), 400

    # Character limit validation is now done on frontend after braille translation
    # Backend expects lines to already be within limits

    try:
        allow_blob_cache = plate_type == 'negative'
        # EARLY BLOB CACHE CHECK (before heavy mesh generation)
        if allow_blob_cache:
            try:
                # For counter plates, exclude user-provided text/grade from cache key
                if plate_type == 'negative':
                    cache_payload_early = {
                        'plate_type': 'negative',
                        'shape_type': shape_type,
                        'settings': _normalize_settings_for_cache(settings),
                    }
                    if shape_type == 'cylinder':
                        cache_payload_early['cylinder_params'] = _normalize_cylinder_params_for_cache(cylinder_params)
                else:
                    cache_payload_early = {
                        'lines': lines,
                        'original_lines': original_lines,
                        'placement_mode': placement_mode,
                        'plate_type': plate_type,
                        'grade': grade,
                        'settings': settings_data,
                        'shape_type': shape_type,
                        'cylinder_params': cylinder_params,
                    }
                early_cache_key = compute_cache_key(cache_payload_early)
                # Check Redis mapping (URL may include random suffix set by provider)
                mapped_url = _blob_url_cache_get(early_cache_key)
                early_public = mapped_url or _build_blob_public_url(early_cache_key)
                if early_public and _blob_check_exists(early_public):
                    app.logger.info(f'BLOB CACHE EARLY HIT (counter plate) key={early_cache_key}')
                    resp = redirect(early_public, code=302)
                    resp.headers['X-Blob-Cache-Key'] = early_cache_key
                    resp.headers['X-Blob-URL'] = early_public
                    resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                    resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
                    resp.headers['X-Cache'] = 'hit-redirect'
                    resp.headers['X-Compute-Time'] = '0'
                    resp.headers['X-Blob-Cache'] = 'hit'
                    resp.headers['X-Blob-Cache-Reason'] = 'early-exists'
                    return resp
            except Exception:
                pass

        if shape_type == 'card':
            # Original card generation logic
            if plate_type == 'positive':
                # Use provided original_lines (manual lines or auto-derived indicators)
                mesh = create_positive_plate_mesh(lines, grade, settings, original_lines)
            elif plate_type == 'negative':
                # Counter plate: choose recess shape
                # It does NOT depend on text input - always creates ALL 6 dots per cell
                recess_shape = int(getattr(settings, 'recess_shape', 1))
                if recess_shape == 1:
                    logger.debug('Generating counter plate with bowl (spherical cap) recesses (all positions)')
                    mesh = build_counter_plate_bowl(settings)
                elif recess_shape == 0:
                    logger.debug('Generating counter plate with hemispherical recesses (all positions)')
                    mesh = build_counter_plate_hemispheres(settings)
                elif recess_shape == 2:
                    logger.debug('Generating counter plate with conical (frustum) recesses (all positions)')
                    mesh = build_counter_plate_cone(settings)
                else:
                    logger.warning('Unknown recess_shape value, defaulting to bowl')
                    mesh = build_counter_plate_bowl(settings)
            else:
                return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400

        elif shape_type == 'cylinder':
            # New cylinder generation logic
            if plate_type == 'positive':
                mesh = generate_cylinder_stl(lines, grade, settings, cylinder_params, original_lines)
            elif plate_type == 'negative':
                # Cylinder counter plate
                mesh = generate_cylinder_counter_plate(lines, settings, cylinder_params)
            else:
                return jsonify({'error': f'Invalid plate type: {plate_type}. Use "positive" or "negative".'}), 400

        # Verify mesh is watertight and manifold
        if not mesh.is_watertight:
            logger.warning(f'Generated {plate_type} plate mesh is not watertight!')
            # Try to fix the mesh
            mesh.fill_holes()
            if mesh.is_watertight:
                logger.info('Mesh holes filled successfully')
            else:
                logger.error('Could not make mesh watertight')

        if not mesh.is_winding_consistent:
            logger.warning(f'Generated {plate_type} plate mesh has inconsistent winding!')
            try:
                mesh.fix_normals()
                logger.info('Fixed mesh normals')
            except ImportError:
                # fix_normals requires scipy, try unify_normals instead
                mesh.unify_normals()
                logger.info('Unified mesh normals (scipy not available)')

        # Compute content-addressable cache key from request payload
        # Build cache payload; exclude user text/grade for counter plates for universal caching
        if plate_type == 'negative':
            cache_payload = {
                'plate_type': 'negative',
                'shape_type': shape_type,
                'settings': _normalize_settings_for_cache(settings),
            }
            if shape_type == 'cylinder':
                cache_payload['cylinder_params'] = _normalize_cylinder_params_for_cache(cylinder_params)
        else:
            cache_payload = {
                'lines': lines,
                'original_lines': original_lines,
                'placement_mode': placement_mode,
                'plate_type': plate_type,
                'grade': grade,
                'settings': settings_data,
                'shape_type': shape_type,
                'cylinder_params': cylinder_params,
            }
        cache_key = compute_cache_key(cache_payload)

        # If a public base is configured and the blob already exists, redirect (only for card counter plates)
        if allow_blob_cache:
            mapped = _blob_url_cache_get(cache_key)
            cached_public = mapped or _build_blob_public_url(cache_key)
            if cached_public and _blob_check_exists(cached_public):
                app.logger.info(f'BLOB CACHE HIT (pre-export) key={cache_key}')
                resp = redirect(cached_public, code=302)
                resp.headers['X-Blob-Cache-Key'] = cache_key
                resp.headers['X-Blob-URL'] = cached_public
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
                resp.headers['X-Cache'] = 'hit-redirect'
                resp.headers['X-Compute-Time'] = '0'
                resp.headers['X-Blob-Cache'] = 'hit'
                resp.headers['X-Blob-Cache-Reason'] = 'pre-export-exists'
                return resp

        # Compute time around STL export for observability
        t0 = time.time()
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        compute_ms = int((time.time() - t0) * 1000)

        # Compute ETag and conditional 304 handling
        stl_bytes = stl_io.getvalue()
        etag = hashlib.sha256(stl_bytes).hexdigest()
        client_etag = request.headers.get('If-None-Match')
        if client_etag and client_etag == etag:
            resp = make_response('', 304)
            resp.headers['ETag'] = etag
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
            resp.headers['X-Blob-Cache'] = 'miss' if allow_blob_cache else 'bypass'
            resp.headers['X-Blob-Cache-Key'] = cache_key
            resp.headers['X-Blob-URL'] = _build_blob_public_url(cache_key)
            return resp

        # Create JSON config dump for reproducibility
        # Avoid accessing volume when booleans may be disabled or mesh invalid in serverless
        safe_volume = None
        try:
            safe_volume = float(mesh.volume)
        except Exception:
            safe_volume = None

        config_dump = {
            'timestamp': datetime.now().isoformat(),
            'plate_type': plate_type,
            'shape_type': shape_type,
            'grade': grade if plate_type == 'positive' else 'n/a',
            'text_lines': lines if plate_type == 'positive' else ['Counter plate - all positions'],
            'cylinder_params': cylinder_params if shape_type == 'cylinder' else 'n/a',
            'per_line_language_tables': per_line_language_tables if per_line_language_tables else 'n/a',
            'settings': {
                # Card parameters
                'card_width': settings.card_width,
                'card_height': settings.card_height,
                'card_thickness': settings.card_thickness,
                # Grid parameters
                'grid_columns': settings.grid_columns,
                'grid_rows': settings.grid_rows,
                'cell_spacing': settings.cell_spacing,
                'line_spacing': settings.line_spacing,
                'dot_spacing': settings.dot_spacing,
                # Emboss plate dot parameters
                'emboss_dot_base_diameter': settings.emboss_dot_base_diameter,
                'emboss_dot_height': settings.emboss_dot_height,
                'emboss_dot_flat_hat': settings.emboss_dot_flat_hat,
                # Offsets
                'braille_x_adjust': settings.braille_x_adjust,
                'braille_y_adjust': settings.braille_y_adjust,
                # Counter plate specific
                'hemisphere_subdivisions': settings.hemisphere_subdivisions if plate_type == 'negative' else 'n/a',
                'cone_segments': settings.cone_segments if plate_type == 'negative' else 'n/a',
                'hemi_counter_dot_base_diameter': getattr(
                    settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 'n/a')
                )
                if plate_type == 'negative'
                else 'n/a',
                'bowl_counter_dot_base_diameter': getattr(
                    settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 'n/a')
                )
                if plate_type == 'negative'
                else 'n/a',
                'use_bowl_recess': int(getattr(settings, 'use_bowl_recess', 0)) if plate_type == 'negative' else 'n/a',
                'counter_dot_depth': float(getattr(settings, 'counter_dot_depth', 0.6))
                if (plate_type == 'negative' and int(getattr(settings, 'use_bowl_recess', 0)) == 1)
                else ('n/a' if plate_type != 'negative' else 0.0),
            },
            'mesh_info': {
                'vertices': len(mesh.vertices),
                'faces': len(mesh.faces),
                'is_watertight': bool(getattr(mesh, 'is_watertight', False)),
                'volume': safe_volume,
            },
        }

        # Save config as JSON
        config_json = json.dumps(config_dump, indent=2)
        logger.debug(f'Config dump:\n{config_json}')

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
            # For counter plates, include actual counter base diameter in filename
            try:
                if int(getattr(settings, 'use_bowl_recess', 0)) == 1:
                    total_diameter = float(
                        getattr(settings, 'bowl_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                    )
                else:
                    total_diameter = float(
                        getattr(settings, 'hemi_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                    )
            except Exception:
                total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
            filename = f'braille_counter_plate_{total_diameter}mm-{shape_type}'

        # Additional filename sanitization for security
        filename = re.sub(r'[^\w\-_]', '', filename)[:60]  # Allow longer names to accommodate shape type

        # Attempt to persist to Blob store and redirect if successful (only for card counter plates)
        if allow_blob_cache:
            public_url = _blob_upload(cache_key, stl_bytes)
            if public_url:
                app.logger.info(f'BLOB CACHE MISS -> UPLOAD OK key={cache_key}')
                # Persist mapping so future early checks can redirect immediately
                _blob_url_cache_set(cache_key, public_url)
                resp = redirect(public_url, code=302)
                resp.headers['ETag'] = etag
                resp.headers['X-Blob-Cache-Key'] = cache_key
                resp.headers['X-Blob-URL'] = public_url
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
                resp.headers['X-Cache'] = 'miss-redirect'
                resp.headers['X-Compute-Time'] = str(compute_ms)
                resp.headers['X-Blob-Cache'] = 'miss'
                resp.headers['X-Blob-Cache-Reason'] = 'uploaded-now'
                # Structured cost log
                with contextlib.suppress(Exception):
                    app.logger.info(
                        json.dumps(
                            {
                                'event': 'stl_upload',
                                'cache_key': cache_key,
                                'size_bytes': len(stl_bytes),
                                'compute_ms': compute_ms,
                                'shape_type': shape_type,
                                'plate_type': plate_type,
                                'action': 'upload-and-redirect',
                            }
                        )
                    )
                return resp

        # Build response with headers
        resp = make_response(
            send_file(io.BytesIO(stl_bytes), mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl')
        )
        resp.headers['ETag'] = etag
        resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
        resp.headers['X-Blob-Cache'] = 'miss' if allow_blob_cache else 'bypass'
        resp.headers['X-Blob-Cache-Reason'] = 'no-upload-url' if allow_blob_cache else 'embossing-disabled'
        resp.headers['X-Blob-Cache-Key'] = cache_key
        resp.headers['X-Blob-URL'] = _build_blob_public_url(cache_key)
        resp.headers['X-Cache'] = 'origin'
        resp.headers['X-Compute-Time'] = str(compute_ms)
        # Structured cost log for origin send
        with contextlib.suppress(Exception):
            app.logger.info(
                json.dumps(
                    {
                        'event': 'stl_origin',
                        'cache_key': cache_key,
                        'size_bytes': len(stl_bytes),
                        'compute_ms': compute_ms,
                        'shape_type': shape_type,
                        'plate_type': plate_type,
                        'action': 'origin-send',
                    }
                )
            )
        return resp

    except Exception as e:
        return jsonify({'error': f'Failed to generate STL: {str(e)}'}), 500


@app.route('/generate_counter_plate_stl', methods=['POST'])
@limiter.limit('10 per minute')
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
        app.logger.error(f'Validation error in generate_counter_plate_stl: {e}')
        return jsonify({'error': 'Invalid request data'}), 400

    try:
        # EARLY BLOB CACHE CHECK (before heavy mesh generation)
        try:
            cache_payload_early = {
                'plate_type': 'negative',
                'settings': _normalize_settings_for_cache(settings),
                'shape_type': 'card',
            }
            early_cache_key = compute_cache_key(cache_payload_early)
            early_public = _build_blob_public_url(early_cache_key)
            if _blob_check_exists(early_public):
                app.logger.info(f'BLOB CACHE EARLY HIT (counter plate standalone) key={early_cache_key}')
                resp = redirect(early_public, code=302)
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
                resp.headers['X-Cache'] = 'hit-redirect'
                resp.headers['X-Compute-Time'] = '0'
                resp.headers['X-Blob-Cache'] = 'hit'
                resp.headers['X-Blob-Cache-Reason'] = 'early-exists'
                return resp
        except Exception:
            pass

        # Counter plate: choose recess shape
        # It does NOT depend on text input - always creates ALL 6 dots per cell
        recess_shape = int(getattr(settings, 'recess_shape', 1))
        if recess_shape == 1:
            logger.debug('Generating counter plate with bowl (spherical cap) recesses (all positions)')
            mesh = build_counter_plate_bowl(settings)
        elif recess_shape == 0:
            logger.debug('Generating counter plate with hemispherical recesses (all positions)')
            mesh = build_counter_plate_hemispheres(settings)
        elif recess_shape == 2:
            logger.debug('Generating counter plate with conical (frustum) recesses (all positions)')
            mesh = build_counter_plate_cone(settings)
        else:
            logger.warning(f'Unknown recess_shape={recess_shape}, defaulting to hemisphere')
            mesh = build_counter_plate_hemispheres(settings)

        # Compute content-addressable cache key from request payload
        cache_payload = {
            'plate_type': 'negative',
            'settings': _normalize_settings_for_cache(settings),
            'shape_type': 'card',
        }
        cache_key = compute_cache_key(cache_payload)

        # If a public base is configured and the blob already exists, redirect
        mapped = _blob_url_cache_get(cache_key)
        cached_public = mapped or _build_blob_public_url(cache_key)
        if cached_public and _blob_check_exists(cached_public):
            app.logger.info(f'BLOB CACHE HIT (pre-export standalone) key={cache_key}')
            resp = redirect(cached_public, code=302)
            resp.headers['X-Blob-Cache-Key'] = cache_key
            resp.headers['X-Blob-URL'] = cached_public
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
            resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
            resp.headers['X-Cache'] = 'hit-redirect'
            resp.headers['X-Compute-Time'] = '0'
            resp.headers['X-Blob-Cache'] = 'hit'
            resp.headers['X-Blob-Cache-Reason'] = 'pre-export-exists'
            return resp

        # Compute time around STL export for observability
        t0 = time.time()
        # Export to STL
        stl_io = io.BytesIO()
        mesh.export(stl_io, file_type='stl')
        stl_io.seek(0)
        compute_ms = int((time.time() - t0) * 1000)

        # Compute ETag and conditional 304 handling
        stl_bytes = stl_io.getvalue()
        etag = hashlib.sha256(stl_bytes).hexdigest()
        client_etag = request.headers.get('If-None-Match')
        if client_etag and client_etag == etag:
            resp = make_response('', 304)
            resp.headers['ETag'] = etag
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
            resp.headers['X-Blob-Cache'] = 'miss'
            return resp

        # Include actual counter base diameter in filename
        try:
            if recess_shape == 1:  # Bowl
                total_diameter = float(
                    getattr(settings, 'bowl_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                )
            elif recess_shape == 2:  # Cone
                total_diameter = float(
                    getattr(settings, 'cone_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                )
            else:  # Hemisphere (recess_shape == 0)
                total_diameter = float(
                    getattr(settings, 'hemi_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                )
        except Exception:
            total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        filename = f'braille_counter_plate_{total_diameter}mm'
        # Attempt to persist to Blob store and redirect if successful
        public_url = _blob_upload(cache_key, stl_bytes)
        if public_url and _blob_check_exists(public_url):
            app.logger.info(f'BLOB CACHE MISS -> UPLOAD OK (standalone) key={cache_key}')
            resp = redirect(public_url, code=302)
            resp.headers['ETag'] = etag
            resp.headers['X-Blob-Cache-Key'] = cache_key
            resp.headers['X-Blob-URL'] = public_url
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
            resp.headers['CDN-Cache-Control'] = 'public, s-maxage=3600, stale-while-revalidate=86400'
            resp.headers['X-Cache'] = 'miss-redirect'
            resp.headers['X-Compute-Time'] = str(compute_ms)
            resp.headers['X-Blob-Cache'] = 'miss'
            resp.headers['X-Blob-Cache-Reason'] = 'uploaded-now'
            # Structured cost log
            with contextlib.suppress(Exception):
                app.logger.info(
                    json.dumps(
                        {
                            'event': 'stl_upload',
                            'cache_key': cache_key,
                            'size_bytes': len(stl_bytes),
                            'compute_ms': compute_ms,
                            'shape_type': 'card',
                            'plate_type': 'negative',
                            'action': 'upload-and-redirect',
                        }
                    )
                )
            return resp

        # Build response with headers
        resp = make_response(
            send_file(io.BytesIO(stl_bytes), mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl')
        )
        resp.headers['ETag'] = etag
        resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
        resp.headers['X-Blob-Cache'] = 'miss'
        resp.headers['X-Blob-Cache-Reason'] = 'no-upload-url'
        resp.headers['X-Cache'] = 'origin'
        resp.headers['X-Compute-Time'] = str(compute_ms)
        # Structured cost log for origin send
        with contextlib.suppress(Exception):
            app.logger.info(
                json.dumps(
                    {
                        'event': 'stl_origin',
                        'cache_key': cache_key,
                        'size_bytes': len(stl_bytes),
                        'compute_ms': compute_ms,
                        'shape_type': 'card',
                        'plate_type': 'negative',
                        'action': 'origin-send',
                    }
                )
            )
        return resp

    except Exception as e:
        return jsonify({'error': f'Failed to generate counter plate: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)

# For Vercel deployment - DISABLED for baseline
# app.debug = False
