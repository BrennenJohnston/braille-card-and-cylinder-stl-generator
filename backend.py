import hashlib
import io
import json
import os
import re
import time
from datetime import datetime

import trimesh
from flask import Flask, jsonify, make_response, redirect, request, send_file, send_from_directory
from flask_cors import CORS
from shapely.geometry import Polygon
from shapely.ops import unary_union
from werkzeug.exceptions import HTTPException

from app.geometry.plates import (
    build_counter_plate_bowl,
    build_counter_plate_cone,
    build_counter_plate_hemispheres,
    create_positive_plate_mesh,
)
from app.geometry_spec import extract_card_geometry_spec, extract_cylinder_geometry_spec

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
from app.geometry.braille_layout import (
    create_card_line_end_marker_3d,
)

# Import geometry functions from app.geometry
from app.geometry.cylinder import generate_cylinder_counter_plate, generate_cylinder_stl

# Note: Other marker and plate functions are defined below in this file
# The marker functions above are imported to avoid NameError in counter plate generation
# Import models from app.models
from app.models import CardSettings

# Import utilities from app.utils
from app.utils import braille_to_dots, get_logger

# Import validation from app.validation
from app.validation import (
    validate_braille_lines,
    validate_lines,
    validate_original_lines,
    validate_settings,
)

# Configure logging for this module
logger = get_logger(__name__)

app = Flask(__name__)
# CORS configuration - uses environment variable for production domain
# SECURITY: CORS must be properly configured for production
allowed_origins = []

# Add production domain from environment variable
production_domain = os.environ.get('PRODUCTION_DOMAIN')
if production_domain:
    # Support comma-separated list of domains
    for domain in production_domain.split(','):
        domain = domain.strip()
        if domain:
            allowed_origins.append(domain)
            logger.info(f'CORS: Added production domain: {domain}')

# For development, allow localhost
if os.environ.get('FLASK_ENV') == 'development':
    allowed_origins.extend(
        ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5001', 'http://127.0.0.1:5001']
    )
    logger.info('CORS: Development mode - localhost origins enabled')

# SECURITY: In production without CORS configured, restrict to same-origin only
# This is more secure than allowing all origins
if not allowed_origins:
    if os.environ.get('FLASK_ENV') == 'development':
        # In development without explicit config, allow localhost
        allowed_origins = ['http://localhost:5001', 'http://127.0.0.1:5001']
        logger.warning('CORS: Development mode with no PRODUCTION_DOMAIN - allowing localhost only')
    else:
        # In production, if PRODUCTION_DOMAIN is not set, we still need the app to work
        # but we log a critical warning and restrict to same-origin behavior
        logger.critical(
            'CORS: PRODUCTION_DOMAIN environment variable is NOT set! '
            'This is a security risk. Set PRODUCTION_DOMAIN to your actual domain(s).'
        )
        # Use empty list which makes CORS more restrictive (same-origin only for credentialed requests)
        # We add the wildcard but WITHOUT supports_credentials to limit the exposure
        allowed_origins = ['*']
        logger.warning(
            'CORS: Falling back to allow-all origins WITHOUT credentials support. '
            'Set PRODUCTION_DOMAIN to enable proper CORS with credentials.'
        )

# When using wildcard, disable credentials support for security
cors_supports_credentials = '*' not in allowed_origins
if not cors_supports_credentials:
    logger.warning('CORS: Credentials support DISABLED due to wildcard origin')

CORS(app, origins=allowed_origins, supports_credentials=cors_supports_credentials)


# Security configurations
# Request size limits optimized for actual payload sizes
# Typical requests: Braille text (~10KB), Geometry spec (~50KB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024  # 100KB max (reduced from 1MB)

# SECRET_KEY configuration - mandatory in production
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if os.environ.get('FLASK_ENV') == 'development':
        SECRET_KEY = 'dev-key-change-in-production'
        logger.warning('Using insecure development SECRET_KEY - DO NOT use in production!')
    else:
        raise RuntimeError(
            'SECRET_KEY environment variable must be set in production. '
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
app.config['SECRET_KEY'] = SECRET_KEY

# Flask-Limiter setup with tiered rate limiting
# Stricter limits to prevent resource exhaustion and abuse
redis_url = os.environ.get('REDIS_URL')
storage_uri = redis_url if redis_url else 'memory://'
if Limiter is not None:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        default_limits=[
            '5 per minute',  # Burst protection
            '50 per hour',  # Sustained usage limit
            '200 per day',  # Daily cap
        ],
    )
    limiter.init_app(app)
else:

    class _NoopLimiter:
        def limit(self, *_args, **_kwargs):
            def decorator(f):
                return f

            return decorator

    limiter = _NoopLimiter()


# Rate limit exceeded handler
@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify(
        {
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please wait before trying again.',
            'retry_after': getattr(e, 'description', 'Please try again later'),
        }
    ), 429


# Helper functions for security (cache functions now in app.cache)


@app.route('/lookup_stl', methods=['GET'])
@limiter.limit('20 per minute; 200 per hour')
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
@limiter.limit('1 per minute')
def debug_blob_upload():
    """Try both direct and API blob uploads with a 1-byte payload and report results.

    SECURITY: This endpoint is restricted to development mode only.
    """
    # Restrict to development environment
    if os.environ.get('FLASK_ENV') != 'development' and not os.environ.get('ENABLE_DEBUG_ENDPOINTS'):
        return jsonify({'error': 'Endpoint not available'}), 404

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
    """Add comprehensive security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Cross-Origin Policies for enhanced security
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    # Content-Security-Policy allowing web workers, table loading, and Blob CDN redirects
    blob_base = _blob_public_base_url().rstrip('/')
    connect_sources = ["'self'", 'blob:', 'data:']
    if blob_base:
        connect_sources.append(blob_base)
    # Also allow generic Vercel Blob CDN wildcard as a fallback if no env set
    if not blob_base:
        connect_sources.append('https://*.vercel-storage.com')
    # Allow CDN sources for manifold-3d WASM loading
    connect_sources.append('https://cdn.jsdelivr.net')
    connect_sources.append('https://unpkg.com')

    # Improved CSP: Remove 'unsafe-eval' for modern browsers
    # Note: 'unsafe-eval' removed - requires Chrome 80+, Firefox 114+, Safari 15+, Edge 80+
    # If you need to support older browsers, uncomment the 'unsafe-eval' fallback below
    csp_policy = (
        "default-src 'self'; "
        # 'wasm-unsafe-eval' allows WebAssembly compilation without full eval
        "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' "
        'https://fonts.googleapis.com https://vercel.live '
        'https://cdn.jsdelivr.net https://unpkg.com; '
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        f'connect-src {" ".join(connect_sources)}; '
        "object-src 'none'; "
        "base-uri 'self'; "
        "worker-src 'self' blob:; "
        "frame-ancestors 'none'"
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
    return jsonify({'error': 'Request too large. Maximum size is 100KB.'}), 413


@app.before_request
def check_content_length():
    """Additional content length validation per endpoint."""
    if request.method in ['POST', 'PUT']:
        cl = request.content_length
        endpoint = request.endpoint

        # Stricter limits for specific endpoints
        if endpoint in ['generate_braille_stl', 'geometry_spec'] and cl and cl > 50 * 1024:
            return jsonify({'error': 'Request too large for this endpoint (max 50KB)'}), 413

        if endpoint == 'generate_counter_plate_stl' and cl and cl > 10 * 1024:
            return jsonify({'error': 'Request too large for this endpoint (max 10KB)'}), 413


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


def create_line_marker_polygon(x, y, settings: CardSettings):
    """
    Create a 2D rectangle polygon for the end-of-row line marker at the first cell.

    The rectangle height equals the cell height (2 * dot_spacing) and the
    width equals one dot spacing, centered at the right column of the first cell.

    Args:
        x: X position of the cell center
        y: Y position of the cell center
        settings: CardSettings object with braille dimensions

    Returns:
        Shapely Polygon representing the rectangle
    """
    line_width = settings.dot_spacing
    line_x = x + settings.dot_spacing / 2
    vertices = [
        (line_x - line_width / 2, y - settings.dot_spacing),  # Bottom left
        (line_x + line_width / 2, y - settings.dot_spacing),  # Bottom right
        (line_x + line_width / 2, y + settings.dot_spacing),  # Top right
        (line_x - line_width / 2, y + settings.dot_spacing),  # Top left
    ]
    return Polygon(vertices)


def create_character_shape_polygon(character, x, y, settings: CardSettings):
    """
    Create a 2D character polygon for the beginning-of-row indicator.
    This is used for creating recesses in embossing plates using 2D operations.

    Args:
        character: Single character (A-Z or 0-9)
        x: X position of the cell center
        y: Y position of the cell center
        settings: CardSettings object with braille dimensions

    Returns:
        Shapely Polygon representing the character, or None if character cannot be created
    """
    # Define character size (same as in create_character_shape_3d)
    char_height = 2 * settings.dot_spacing + 4.375  # 9.375mm for default 2.5mm dot spacing
    char_width = settings.dot_spacing * 0.8 + 2.6875  # 4.6875mm for default 2.5mm dot spacing

    # Position character at the right column of the cell
    char_x = x + settings.dot_spacing / 2
    char_y = y

    # Get the character definition
    char_upper = character.upper()
    if not (char_upper.isalpha() or char_upper.isdigit()):
        # Fall back to rectangle for undefined characters
        return create_line_marker_polygon(x, y, settings)

    try:
        # Build character polygon using shared helper
        char_2d = _build_character_polygon(char_upper, char_width, char_height)
        if char_2d is None:
            return create_line_marker_polygon(x, y, settings)

        # Translate to desired position
        from shapely import affinity as _affinity

        char_2d = _affinity.translate(char_2d, xoff=char_x, yoff=char_y)

        return char_2d
    except Exception as e:
        logger.warning(f'Failed to create character polygon: {e}')
        return create_line_marker_polygon(x, y, settings)


# create_card_triangle_marker_3d and create_card_line_end_marker_3d now imported from app.geometry.braille_layout


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


# layout_cylindrical_cells now imported from app.geometry.cylinder


# cylindrical_transform now imported from app.geometry.cylinder


# create_cylinder_shell now imported from app.geometry.cylinder

# create_cylinder_triangle_marker now imported from app.geometry.cylinder

# create_cylinder_line_end_marker now imported from app.geometry.cylinder

# create_cylinder_character_shape now imported from app.geometry.cylinder

# create_cylinder_braille_dot now imported from app.geometry.cylinder

# generate_cylinder_stl now imported from app.geometry.cylinder

# generate_cylinder_counter_plate now imported from app.geometry.cylinder


@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Vercel backend is running'})


@app.route('/')
def index():
    """
    Serve the main application page.
    Uses public/index.html as the single source of truth for both local and Vercel deployments.
    This ensures the client-side CSG generation logic is consistent across environments.
    """
    try:
        # Serve public/index.html directly - same file used by Vercel
        return send_from_directory('public', 'index.html')
    except Exception as e:
        logger.info(f'Error serving index.html: {e}')
        return jsonify({'error': 'Failed to load page'}), 500


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

        # Add security headers to static files
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Set cache headers for static assets
        if safe_path.endswith(('.js', '.css', '.woff', '.woff2', '.ttf', '.eot')):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            response.headers['Cache-Control'] = 'public, max-age=3600'

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
@limiter.limit('3 per minute; 20 per hour; 100 per day')
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
        validate_original_lines(original_lines)
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

    # Check if boolean backends are available - required for server-side generation
    from app.geometry.booleans import has_boolean_backend

    if not has_boolean_backend():
        # On Vercel or other serverless platforms without boolean backends
        # Client-side CSG should be used instead
        return jsonify(
            {
                'error': 'Server-side STL generation requires a modern browser with JavaScript enabled. '
                'This server does not have 3D boolean operation backends available. '
                'Please ensure JavaScript is enabled in your browser to use client-side geometry processing.',
                'error_code': 'NO_BOOLEAN_BACKEND',
                'suggestion': 'Use a modern browser (Chrome 80+, Firefox 114+, Safari 15+, or Edge 80+) with JavaScript enabled. '
                'The application will automatically generate STL files in your browser.',
            }
        ), 503

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
                # Always use 3D boolean approach; failure results in 500 to surface deployment/runtime issues
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

                # Rough sanity check: ensure we actually produced a complex mesh (counter plate should be detailed)
                if len(mesh.faces) < 100:
                    raise RuntimeError('3D boolean approach produced suspiciously few faces (possible failure)')
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

        def sanitize_filename(text: str, max_length: int = 30) -> str:
            """Safely sanitize text for use in filenames."""
            # Remove any null bytes
            text = text.replace('\x00', '')
            # Allow only alphanumeric, spaces, hyphens
            text = re.sub(r'[^\w\s-]', '', text)[:max_length]
            # Replace spaces and multiple hyphens with single underscore
            text = re.sub(r'[-\s]+', '_', text)
            # Remove leading/trailing underscores
            text = text.strip('_')
            # Prevent directory traversal sequences
            text = text.replace('..', '').replace('/', '').replace('\\', '')
            # Ensure not empty
            if not text:
                text = 'untitled'
            return text

        def extract_first_word(text: str) -> str:
            """Extract the first word from a text string."""
            words = text.strip().split()
            return words[0] if words else ''

        # Create filename based on text content with fallback logic
        if plate_type == 'positive':
            # For embossing plates, extract first word from first non-empty line
            filename = 'Embossing_Plate_untitled'
            for line in lines:
                if line.strip():
                    first_word = extract_first_word(line.strip())
                    sanitized = sanitize_filename(first_word)
                    if sanitized and sanitized != 'untitled':
                        filename = f'Embossing_Plate_{sanitized}'
                        break
        else:
            # For counter plates, use simple default name
            # (Frontend handles sequential counter for downloads)
            filename = 'Universal_Counter_Plate'

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


@app.route('/geometry_spec', methods=['POST'])
@limiter.limit('5 per minute; 40 per hour; 150 per day')
def geometry_spec():
    """
    Generate geometry specification (positions, dimensions) for client-side CSG.
    Returns JSON describing primitives without performing boolean operations.
    """
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json(force=True)

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        lines = data.get('lines', ['', '', '', ''])
        original_lines = data.get('original_lines', None)
        plate_type = data.get('plate_type', 'positive')
        grade = data.get('grade', 'g2')
        settings_data = data.get('settings', {})
        shape_type = data.get('shape_type', 'card')
        cylinder_params = data.get('cylinder_params', {})

        # Validate inputs
        validate_lines(lines)
        validate_original_lines(original_lines)
        validate_settings(settings_data)
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

        # Extract geometry spec
        if shape_type == 'card':
            spec = extract_card_geometry_spec(
                lines,
                grade,
                settings,
                original_lines,
                plate_type,
                braille_to_dots_func=braille_to_dots,
            )
        elif shape_type == 'cylinder':
            spec = extract_cylinder_geometry_spec(
                lines,
                grade,
                settings,
                cylinder_params,
                original_lines,
                plate_type,
                braille_to_dots_func=braille_to_dots,
            )
        else:
            return jsonify({'error': f'Invalid shape_type: {shape_type}'}), 400

        # Return spec as JSON
        return jsonify(spec), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f'Error in geometry_spec: {e}')
        return jsonify({'error': 'Failed to generate geometry specification'}), 500


@app.route('/generate_counter_plate_stl', methods=['POST'])
@limiter.limit('3 per minute; 20 per hour; 100 per day')
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

    # Check if boolean backends are available - required for server-side generation
    from app.geometry.booleans import has_boolean_backend

    if not has_boolean_backend():
        # On Vercel or other serverless platforms without boolean backends
        # Client-side CSG should be used instead
        return jsonify(
            {
                'error': 'Server-side STL generation requires a modern browser with JavaScript enabled. '
                'This server does not have 3D boolean operation backends available. '
                'Please ensure JavaScript is enabled in your browser to use client-side geometry processing.',
                'error_code': 'NO_BOOLEAN_BACKEND',
                'suggestion': 'Use a modern browser (Chrome 80+, Firefox 114+, Safari 15+, or Edge 80+) with JavaScript enabled. '
                'The application will automatically generate STL files in your browser.',
            }
        ), 503

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

        # Always use 3D boolean approach; failure results in 500 to surface deployment/runtime issues
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

        # Rough sanity check: ensure we actually produced a complex mesh (counter plate should be detailed)
        if len(mesh.faces) < 100:
            raise RuntimeError('3D boolean approach produced suspiciously few faces (possible failure)')

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

        # For counter plates, use simple default name
        # (Frontend handles sequential counter for downloads)
        filename = 'Universal_Counter_Plate'
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
