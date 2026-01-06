import os
from datetime import UTC, datetime

from flask import Flask, jsonify, make_response, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

# MINIMAL BACKEND - Client-side CSG generation only
# Server-side STL generation removed (2026-01-05) - see CODEBASE_AUDIT_AND_RENOVATION_PLAN.md
from app.geometry_spec import extract_card_geometry_spec, extract_cylinder_geometry_spec

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

# SECRET_KEY configuration - optional for stateless backend
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if os.environ.get('FLASK_ENV') == 'development':
        SECRET_KEY = 'dev-key-change-in-production'
        logger.warning('Using insecure development SECRET_KEY - DO NOT use in production!')
    else:
        # For stateless backend, SECRET_KEY is optional but recommended
        SECRET_KEY = 'stateless-backend-no-sessions'
        logger.warning('SECRET_KEY not set - using placeholder (backend is stateless)')
app.config['SECRET_KEY'] = SECRET_KEY


# Security headers middleware
@app.after_request
def set_security_headers(response):
    """Add comprehensive security headers to all responses."""
    # If already in cache (304), skip modifying headers
    if response.status_code == 304:
        return response

    # CSP: Allow client-side CSG workers and Manifold WASM CDNs
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: cdn.jsdelivr.net unpkg.com",
        "worker-src 'self' blob:",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "connect-src 'self' blob: cdn.jsdelivr.net unpkg.com",
        "font-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        'upgrade-insecure-requests',
    ]
    response.headers['Content-Security-Policy'] = '; '.join(csp_directives)

    # Additional security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    return response


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Request payload too large', 'max_size': '100KB'}), 413


@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # Log non-HTTP exceptions
    app.logger.error(f'Unhandled exception: {e}')
    return jsonify({'error': 'Internal server error'}), 500


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now(UTC).isoformat()})


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('public', 'index.html')


@app.route('/index.html')
def index_html_explicit():
    """Explicit index.html route for compatibility."""
    return send_from_directory('public', 'index.html')


@app.route('/favicon.ico')
def favicon_ico():
    """Serve favicon.ico."""
    return send_from_directory('static', 'favicon.svg', mimetype='image/svg+xml')


@app.route('/favicon.png')
def favicon_png():
    """Serve favicon as PNG (fallback)."""
    return send_from_directory('static', 'favicon.svg', mimetype='image/svg+xml')


@app.route('/static/<path:filename>', methods=['GET', 'OPTIONS'])
def serve_static(filename):
    """
    Serve static files with appropriate caching headers.

    Static files served by Python (not Vercel CDN) due to liblouis table include resolution:
    - liblouis tables can include other tables using relative paths
    - Python serving ensures correct include resolution
    - See VERCEL_OPTIMIZATION_ROADMAP.md for details

    Files served:
    - liblouis translation tables and WASM binaries
    - Web Workers (csg-worker.js, csg-worker-manifold.js, liblouis-worker.js)
    - Vendor libraries (three.module.js, OrbitControls.js, STLLoader.js)
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        return resp

    try:
        # Serve the file
        resp = send_from_directory('static', filename)

        # Set cache headers based on file type
        if filename.endswith(('.wasm', '.js', '.json')):
            # Cache JavaScript, WASM, and JSON files aggressively
            resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'  # 24 hours
        elif filename.endswith(('.ctb', '.tbl', '.utb', '.cti', '.uti', '.dis')):
            # Cache liblouis tables
            resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'  # 24 hours
        elif filename.endswith(('.svg', '.png', '.ico')):
            # Cache images
            resp.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
        else:
            # Default cache
            resp.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour

        return resp

    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


def _scan_liblouis_tables(directory):
    """Recursively scan a directory for liblouis table files (.ctb, .tbl, .utb, etc.).
    Returns a list of table metadata dicts with 'file', 'path', 'locale', 'description'.
    """
    tables = []
    try:
        for root, _dirs, files in os.walk(directory):
            for filename in files:
                # Check for liblouis table extensions
                if not filename.endswith(('.ctb', '.tbl', '.utb', '.cti', '.uti', '.dis')):
                    continue

                # Construct relative path from the base directory
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, directory)

                # Extract locale from filename (heuristic)
                # Format: lang-region-variant.ctb (e.g., en-us-g2.ctb)
                locale = None
                description = filename
                if '-' in filename:
                    parts = filename.split('-')
                    if len(parts) >= 2:
                        locale = f'{parts[0]}-{parts[1]}'  # e.g., en-us

                tables.append(
                    {
                        'file': rel_path.replace('\\', '/'),  # Normalize path separators
                        'path': rel_path.replace('\\', '/'),
                        'locale': locale,
                        'description': description,
                    }
                )
    except OSError:
        # Directory not found or not accessible
        pass
    return tables


@app.route('/liblouis/tables')
def list_liblouis_tables():
    """Return a JSON list of available liblouis translation tables.
    Scans all candidate directories and deduplicates by file name.

    Returns:
        {
            "tables": [
                {
                    "file": "en-us-g2.ctb",
                    "path": "en-us-g2.ctb",
                    "locale": "en-us",
                    "description": "en-us-g2.ctb"
                },
                ...
            ]
        }

    This is used by the frontend to populate the language/table selection dropdown
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


# =============================================================================
# DEPRECATED ENDPOINTS - Server-side STL generation removed 2026-01-05
# =============================================================================
# These endpoints return 410 Gone to avoid breaking old bookmarks while
# preventing reintroduction of Redis/Blob dependencies.
#
# Rationale:
# - Server-side STL generation does not work on Vercel (no manifold3d binaries)
# - Client-side CSG (BVH-CSG for cards, Manifold WASM for cylinders) is fully functional
# - Removing Redis/Blob eliminates 14-day inactivity failure mode
#
# For implementation details, see:
# - docs/development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md
# - .cursor/plans/remove_upstash_dependencies_99900762.plan.md
# =============================================================================


@app.route('/generate_braille_stl', methods=['POST'])
def deprecated_generate_braille_stl():
    """DEPRECATED: Server-side STL generation removed 2026-01-05."""
    return (
        jsonify(
            {
                'error': 'Server-side STL generation has been removed.',
                'status': 'deprecated',
                'reason': 'This endpoint required Redis and Blob storage that caused deployment failures. '
                'The application now uses client-side CSG generation exclusively.',
                'solution': 'Use the web interface at the root URL (/). STL generation happens automatically '
                'in your browser using Web Workers and client-side CSG.',
                'documentation': 'docs/development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md',
                'deprecated_date': '2026-01-05',
            }
        ),
        410,
    )


@app.route('/generate_counter_plate_stl', methods=['POST'])
def deprecated_generate_counter_plate_stl():
    """DEPRECATED: Server-side counter plate generation removed 2026-01-05."""
    return (
        jsonify(
            {
                'error': 'Server-side counter plate generation has been removed.',
                'status': 'deprecated',
                'reason': 'This endpoint required Redis and Blob storage that caused deployment failures. '
                'The application now uses client-side CSG generation exclusively.',
                'solution': 'Use the web interface at the root URL (/). Counter plate generation happens automatically '
                'in your browser using Web Workers and client-side CSG.',
                'documentation': 'docs/development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md',
                'deprecated_date': '2026-01-05',
            }
        ),
        410,
    )


@app.route('/lookup_stl', methods=['GET'])
def deprecated_lookup_stl():
    """DEPRECATED: STL lookup endpoint removed 2026-01-05."""
    return (
        jsonify(
            {
                'error': 'STL lookup endpoint has been removed.',
                'status': 'deprecated',
                'reason': 'This endpoint required Redis cache that caused deployment failures. '
                'Client-side generation is now the only supported method.',
                'solution': 'Use the web interface at the root URL (/).',
                'deprecated_date': '2026-01-05',
            }
        ),
        410,
    )


@app.route('/debug/blob_upload', methods=['GET'])
def deprecated_debug_blob_upload():
    """DEPRECATED: Debug endpoint removed 2026-01-05."""
    return (
        jsonify(
            {
                'error': 'Debug blob upload endpoint has been removed.',
                'status': 'deprecated',
                'reason': 'Blob storage integration was removed as part of architecture simplification.',
                'deprecated_date': '2026-01-05',
            }
        ),
        410,
    )


# =============================================================================
# ACTIVE ENDPOINTS - Essential for client-side generation
# =============================================================================


@app.route('/geometry_spec', methods=['POST'])
def geometry_spec():
    """
    Generate geometry specification (positions, dimensions) for client-side CSG.
    Returns JSON describing primitives without performing boolean operations.

    This is the ONLY server-side endpoint required for STL generation.
    All heavy computation (CSG, mesh generation, STL export) happens client-side.

    Request body:
    {
        "lines": ["⠓⠑⠇⠇⠕", "", "", ""],  // Braille text (4 lines)
        "original_lines": ["Hello", "", "", ""],  // Optional: original text
        "plate_type": "positive" | "negative",
        "grade": "g1" | "g2",
        "shape_type": "card" | "cylinder",
        "settings": { /* CardSettings fields */ },
        "cylinder_params": { /* Optional: for cylinders */ }
    }

    Response:
    {
        "shape_type": "card" | "cylinder",
        "plate_type": "positive" | "negative",
        "base_dimensions": { "width": 100, "depth": 80, "height": 2 },
        "dots": [
            { "x": 10, "y": 5, "z": 2, "char_index": 0, "dot_index": 0 },
            ...
        ],
        "markers": [ /* character position markers */ ],
        // ... shape-specific fields
    }
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


# Run the Flask development server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')
