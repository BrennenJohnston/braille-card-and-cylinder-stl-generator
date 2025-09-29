from flask import Flask, request, send_file, jsonify, render_template, send_from_directory, redirect, make_response
from werkzeug.exceptions import HTTPException
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
from shapely import affinity
from functools import wraps
import time
import hashlib
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

# Flask-Limiter setup (Phase 4.1/4.2) - DISABLED for baseline debugging
# redis_url = os.environ.get('REDIS_URL')
# storage_uri = redis_url if redis_url else 'memory://'
# if Limiter is not None:
#     limiter = Limiter(
#         key_func=get_remote_address,
#         storage_uri=storage_uri,
#         default_limits=["10 per minute"],
#     )
#     limiter.init_app(app)
# else:
#     class _NoopLimiter:
#         def limit(self, *_args, **_kwargs):
#             def decorator(f):
#                 return f
#             return decorator
#     limiter = _NoopLimiter()
limiter = None

# Helper functions for caching and security

def _canonical_json(obj):
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(obj)

def compute_cache_key(payload: dict) -> str:
    """Compute a stable SHA-256 key from request payload for content-addressable caching."""
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _normalize_number(value):
    """Normalize numbers and numeric strings to a stable JSON-friendly form.
    - Convert numeric strings to float
    - Round floats to 5 decimals
    - Convert near-integers to int to avoid 1 vs 1.0 mismatches
    """
    try:
        if isinstance(value, str):
            # Empty string shouldn't appear for numeric fields
            value = float(value)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int,)):
            return value
        if isinstance(value, float):
            rounded = round(value, 5)
            if abs(rounded - round(rounded)) < 1e-9:
                return int(round(rounded))
            return rounded
    except Exception:
        pass
    return value

def _normalize_settings_for_cache(settings) -> dict:
    """Return a normalized dict of geometry-affecting settings for cache keys."""
    # Only include fields that change output geometry
    fields = {
        # Card geometry
        'card_width': settings.card_width,
        'card_height': settings.card_height,
        'card_thickness': settings.card_thickness,
        # Grid
        'grid_columns': settings.grid_columns,
        'grid_rows': settings.grid_rows,
        'cell_spacing': settings.cell_spacing,
        'line_spacing': settings.line_spacing,
        'dot_spacing': settings.dot_spacing,
        # Offsets
        'braille_x_adjust': settings.braille_x_adjust,
        'braille_y_adjust': settings.braille_y_adjust,
        # Recess/dot shapes
        'recess_shape': int(getattr(settings, 'recess_shape', 1)),
        'hemisphere_subdivisions': int(getattr(settings, 'hemisphere_subdivisions', 2)),
        'cone_segments': int(getattr(settings, 'cone_segments', 16)),
        # Emboss dot params (for positive plates)
        'emboss_dot_base_diameter': getattr(settings, 'emboss_dot_base_diameter', None),
        'emboss_dot_height': getattr(settings, 'emboss_dot_height', None),
        'emboss_dot_flat_hat': getattr(settings, 'emboss_dot_flat_hat', None),
        # Counter plate specific base diameters/depths
        'hemi_counter_dot_base_diameter': getattr(settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', None)),
        'bowl_counter_dot_base_diameter': getattr(settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', None)),
        'counter_dot_depth': getattr(settings, 'counter_dot_depth', None),
        'cone_counter_dot_base_diameter': getattr(settings, 'cone_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', None)),
        'cone_counter_dot_flat_hat': getattr(settings, 'cone_counter_dot_flat_hat', None),
        'cone_counter_dot_height': getattr(settings, 'cone_counter_dot_height', None),
        # Indicator shapes flag
        'indicator_shapes': int(getattr(settings, 'indicator_shapes', 1)),
    }
    # Normalize numeric values
    norm = {}
    for k, v in fields.items():
        norm[k] = _normalize_number(v)
    return norm

def _normalize_cylinder_params_for_cache(cylinder_params: dict) -> dict:
    if not isinstance(cylinder_params, dict):
        return {}
    keys = ['diameter_mm', 'height_mm', 'polygonal_cutout_radius_mm', 'polygonal_cutout_sides', 'seam_offset_deg']
    out = {}
    for k in keys:
        out[k] = _normalize_number(cylinder_params.get(k))
    return out

def _blob_public_base_url() -> str:
    # Public base like: https://<store>.public.blob.vercel-storage.com
    return os.environ.get('BLOB_PUBLIC_BASE_URL') or ''

def _build_blob_public_url(cache_key: str) -> str:
    base = _blob_public_base_url().rstrip('/')
    if not base:
        return ''
    # namespace STLs under /stl/
    return f"{base}/stl/{cache_key}.stl"

def _blob_check_exists(public_url: str) -> bool:
    """Return True if the blob appears to exist and is retrievable.

    Some CDNs/storage frontends may not support HEAD consistently or may
    require following redirects. Fall back to a minimal Range GET.
    """
    if not public_url or requests is None:
        return False
    # First try HEAD and follow redirects
    try:
        resp = requests.head(public_url, timeout=4, allow_redirects=True)
        if 200 <= resp.status_code < 300:
            return True
    except Exception:
        pass
    # Fallback: minimal GET with a 1-byte range
    try:
        headers = {"Range": "bytes=0-0"}
        resp = requests.get(public_url, headers=headers, timeout=6, stream=True, allow_redirects=True)
        try:
            resp.close()
        except Exception:
            pass
        return resp.status_code in (200, 206)
    except Exception:
        return False

def _blob_upload(cache_key: str, stl_bytes: bytes) -> str:
    """Upload STL to Vercel Blob via REST if configured. Returns public URL or empty string."""
    if requests is None:
        return ''
    # Support both token names
    token = os.environ.get('BLOB_STORE_WRITE_TOKEN') or os.environ.get('BLOB_READ_WRITE_TOKEN')
    if not token:
        return ''
    # Use filename path to group under /stl/
    pathname = f"stl/{cache_key}.stl"
    # First, try direct upload endpoint which works with store-level tokens
    try:
        direct_base = os.environ.get('BLOB_DIRECT_UPLOAD_URL', 'https://blob.vercel-storage.com')
        direct_url = f"{direct_base.rstrip('/')}/{pathname}"
        headers = {
            'Authorization': f"Bearer {token}",
            # Prefer deterministic filename without random suffix
            'x-vercel-blob-add-random-suffix': '0',
            'x-vercel-blobs-add-random-suffix': '0',
            # Make publicly accessible
            'x-vercel-blob-access': 'public',
            'x-vercel-blobs-access': 'public',
            # Binary content type
            'content-type': 'application/octet-stream',
        }
        # Optional cache control header for CDN
        max_age = os.environ.get('BLOB_CACHE_MAX_AGE')
        if max_age:
            headers['x-vercel-cache-control-max-age'] = str(max_age)
        resp = requests.put(direct_url, data=stl_bytes, headers=headers, timeout=30)
        if 200 <= resp.status_code < 300 or resp.status_code == 409:
            # Prefer URL returned by API if present
            try:
                j = resp.json()
                url_from_api = j.get('url') or ''
                if url_from_api:
                    app.logger.info(f"Blob direct upload OK; using API URL for key={cache_key}")
                    return url_from_api
            except Exception:
                pass
            # Fallback to constructed public URL
            public_url = _build_blob_public_url(cache_key)
            if public_url:
                app.logger.info(f"Blob direct upload OK; using constructed public URL for key={cache_key}")
                return public_url
        else:
            try:
                app.logger.warning(f"Blob direct upload failed status={resp.status_code} body={resp.text}")
            except Exception:
                app.logger.warning(f"Blob direct upload failed status={resp.status_code}")
    except Exception as e:
        app.logger.warning(f"Blob direct upload exception for key={cache_key}: {e}")

    # Fallback: API v2 multipart upload (may require project-scoped tokens)
    try:
        # As of latest docs, the API route for server uploads is project-bound (Next.js),
        # and store tokens are intended for direct PUTs. Keep this as last-resort noop.
        return ''
    except Exception:
        return ''

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

        test_key = f"debug_{int(time.time())}"
        pathname = f"stl/{test_key}.bin"
        payload = b"x"

        # Direct upload
        direct_headers = {
            'Authorization': f"Bearer {token}",
            'x-vercel-filename': pathname,
            # support both header spellings seen in docs
            'x-vercel-blob-add-random-suffix': '0',
            'x-vercel-blobs-add-random-suffix': '0',
            'x-vercel-blob-access': 'public',
            'x-vercel-blobs-access': 'public',
            'content-type': 'application/octet-stream',
        }
        try:
            d_resp = requests.put(f"{direct_base.rstrip('/')}/{pathname}", data=payload, headers=direct_headers, timeout=20)
            info['direct'] = {
                'status': d_resp.status_code,
                'text': d_resp.text[:800] if hasattr(d_resp, 'text') else '<no text>'
            }
            try:
                info['direct']['json'] = d_resp.json()
            except Exception:
                pass
        except Exception as e:
            info['direct'] = {'exception': str(e)}

        # API upload
        api_url = f"{api_base.rstrip('/')}/v2/blobs"
        files = {'file': (pathname, payload, 'application/octet-stream')}
        data = {
            'pathname': pathname,
            'contentType': 'application/octet-stream',
            'cacheControlMaxAge': os.environ.get('BLOB_CACHE_MAX_AGE', '31536000'),
            'access': 'public',
            'addRandomSuffix': 'false',
        }
        api_headers = {'Authorization': f"Bearer {token}"}
        try:
            a_resp = requests.post(api_url, files=files, data=data, headers=api_headers, timeout=20)
            info['api'] = {
                'status': a_resp.status_code,
                'text': a_resp.text[:800] if hasattr(a_resp, 'text') else '<no text>'
            }
            try:
                info['api']['json'] = a_resp.json()
            except Exception:
                pass
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
        f"connect-src {' '.join(connect_sources)}; "
        "object-src 'none'; "
        "base-uri 'self'; worker-src 'self' blob:"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

## Removed legacy in-memory rate limiting in favor of Flask-Limiter

# Input validation functions
def validate_lines(lines):
    """Validate the lines input for security and correctness"""
    if not isinstance(lines, list):
        raise ValueError("Lines must be a list")
    
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

def validate_braille_lines(lines, plate_type='positive'):
    """
    Validate that lines contain valid braille Unicode characters.
    Only validates non-empty lines for positive plates.
    """
    if plate_type != 'positive':
        return True  # Counter plates don't need braille validation
    
    # Define valid braille Unicode range (U+2800 to U+28FF)
    BRAILLE_START = 0x2800
    BRAILLE_END = 0x28FF
    
    errors = []
    
    for i, line in enumerate(lines):
        if line.strip():  # Only validate non-empty lines
            # Check each character in the line
            for j, char in enumerate(line):
                # Allow standard ASCII space characters which represent blank braille cells in our pipeline
                if char == ' ':
                    continue
                char_code = ord(char)
                if char_code < BRAILLE_START or char_code > BRAILLE_END:
                    errors.append({
                        'line': i + 1,
                        'position': j + 1,
                        'character': char,
                        'char_code': f'U+{char_code:04X}'
                    })
    
    if errors:
        error_details = []
        for err in errors[:5]:  # Show first 5 errors to avoid spam
            error_details.append(
                f"Line {err['line']}, position {err['position']}: "
                f"'{err['character']}' ({err['char_code']}) is not a valid braille character"
            )
        
        if len(errors) > 5:
            error_details.append(f"... and {len(errors) - 5} more errors")
        
        raise ValueError(
            "Invalid braille characters detected. Translation may have failed.\n" + 
            "\n".join(error_details) + 
            "\n\nPlease ensure text is properly translated to braille before generating STL."
        )
    
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
        'grid_rows': (int, 1, 200),
        'cell_spacing': (float, 2, 15),
        'line_spacing': (float, 5, 25),
        'dot_spacing': (float, 1, 5),
        'emboss_dot_base_diameter': (float, 0.5, 3),
        'emboss_dot_height': (float, 0.3, 2),
        'emboss_dot_flat_hat': (float, 0.1, 2),
        # Rounded dome
        'use_rounded_dots': (int, 0, 1),
        'rounded_dot_diameter': (float, 0.5, 3),
        'rounded_dot_height': (float, 0.2, 2),
        # New rounded dot with cone base params
        'rounded_dot_base_diameter': (float, 0.5, 3),
        'rounded_dot_cylinder_height': (float, 0.0, 2.0),
        'rounded_dot_base_height': (float, 0.0, 2.0),
        'rounded_dot_dome_height': (float, 0.1, 2.0),
        'rounded_dot_dome_diameter': (float, 0.5, 3.0),
        'braille_x_adjust': (float, -10, 10),
        'braille_y_adjust': (float, -10, 10),
        # Support legacy offset and new independent counter base diameter.
        # If both are provided, counter base diameter takes precedence.
        'counter_plate_dot_size_offset': (float, 0, 2),
        'counter_dot_base_diameter': (float, 0.1, 5.0),
        'hemi_counter_dot_base_diameter': (float, 0.1, 5.0),
        'bowl_counter_dot_base_diameter': (float, 0.1, 5.0),
        'hemisphere_subdivisions': (int, 1, 3),
        'cone_segments': (int, 8, 32),  # Control polygon count for cone shapes
        # Counter recess shape and depth
        'use_bowl_recess': (int, 0, 1),
        # New tri-state recess selector: 0=hemisphere, 1=bowl, 2=cone
        'recess_shape': (int, 0, 2),
        # New cone (recess) parameters
        'cone_counter_dot_base_diameter': (float, 0.1, 5.0),
        'cone_counter_dot_height': (float, 0.0, 5.0),
        'cone_counter_dot_flat_hat': (float, 0.0, 5.0),
        'counter_dot_depth': (float, 0.0, 5.0),
        # Indicator shapes toggle (1 = on, 0 = off)
        'indicator_shapes': (int, 0, 1)
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
    # Pass through HTTPExceptions (e.g., 404) so they keep their original status codes
    if isinstance(e, HTTPException):
        return e
    # Log unexpected errors for debugging in production
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
            "grid_columns": 14,
            "grid_rows": 4,
            "cell_spacing": 6.5,  # Project brief default
            "line_spacing": 10.0,
            "dot_spacing": 2.5,
            # Emboss plate dot parameters (as per project brief)
            "emboss_dot_base_diameter": 1.8,  # Updated default: 1.8 mm
            "emboss_dot_height": 1.0,  # Project brief default: 1.0 mm
            "emboss_dot_flat_hat": 0.4,  # Updated default: 0.4 mm
            # Rounded dome dot parameters (optional alternative to cone)
            "use_rounded_dots": 0,  # 0 = cone (default), 1 = rounded dome
            # Legacy names kept for backward compatibility
            "rounded_dot_diameter": 1.5,  # Legacy: base diameter for rounded dome (mm)
            "rounded_dot_height": 0.6,    # Legacy: total height or dome height
            # New explicit parameters for rounded dot with cone base
            "rounded_dot_base_diameter": 2.0,   # Cone base diameter at surface
            "rounded_dot_dome_diameter": 1.5,   # Cone flat top diameter and dome base
            "rounded_dot_base_height": 0.2,     # Cone base height (from surface)
            "rounded_dot_cylinder_height": 0.2, # Legacy alias: cylinder base height
            "rounded_dot_dome_height": 0.6,     # Dome height above cone flat top
            # Offset adjustments
            "braille_y_adjust": 0.0,  # Default to center
            "braille_x_adjust": 0.0,  # Default to center
            # Counter plate specific parameters
            "hemisphere_subdivisions": 1,  # For mesh density control
            "cone_segments": 16,  # Default cone polygon count (8-32 range)
            "counter_plate_dot_size_offset": 0.0,  # Legacy: offset from emboss dot diameter
            "counter_dot_base_diameter": 1.6,      # Deprecated: kept for back-compat
            # Separate diameters for hemisphere and bowl recesses
            "hemi_counter_dot_base_diameter": 1.6,
            "bowl_counter_dot_base_diameter": 1.8,
            # Bowl recess controls
            "use_bowl_recess": 1,                 # 0 = hemisphere, 1 = bowl (spherical cap)
            # New tri-state recess shape selector: 0=hemisphere, 1=bowl, 2=cone
            "recess_shape": 1,
            # Cone recess default parameters
            "cone_counter_dot_base_diameter": 1.6,
            "cone_counter_dot_height": 0.8,
            "cone_counter_dot_flat_hat": 0.4,
            "counter_dot_depth": 0.8,             # Bowl recess depth (mm)
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
            # Indicator shapes (row start/end markers) toggle
            "indicator_shapes": 1,
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
        # Normalize boolean-like toggles stored as numbers
        try:
            self.use_rounded_dots = int(float(kwargs.get('use_rounded_dots', self.use_rounded_dots)))
        except Exception:
            self.use_rounded_dots = int(self.use_rounded_dots)
        try:
            self.indicator_shapes = int(float(kwargs.get('indicator_shapes', getattr(self, 'indicator_shapes', 1))))
        except Exception:
            self.indicator_shapes = int(getattr(self, 'indicator_shapes', 1))
        try:
            self.use_bowl_recess = int(float(kwargs.get('use_bowl_recess', getattr(self, 'use_bowl_recess', 0))))
        except Exception:
            self.use_bowl_recess = int(getattr(self, 'use_bowl_recess', 0))
        # Normalize recess_shape (0=hemi,1=bowl,2=cone)
        try:
            self.recess_shape = int(float(kwargs.get('recess_shape', getattr(self, 'recess_shape', 1))))
        except Exception:
            self.recess_shape = int(getattr(self, 'recess_shape', 1))
        
        # Map dot_shape to use_rounded_dots for backend compatibility
        try:
            dot_shape = kwargs.get('dot_shape', 'rounded')
            if dot_shape == 'rounded':
                self.use_rounded_dots = 1
            elif dot_shape == 'cone':
                self.use_rounded_dots = 0
        except Exception:
            pass  # Keep existing use_rounded_dots value
        
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
        
        # If independent counter base diameter is supplied, derive offset to keep legacy paths working
        # Otherwise, derive counter base from emboss + offset
        # Normalize legacy unified base diameter into the new split fields when provided
        try:
            provided_hemi = getattr(self, 'hemi_counter_dot_base_diameter', None)
            provided_bowl = getattr(self, 'bowl_counter_dot_base_diameter', None)
            provided_unified = getattr(self, 'counter_dot_base_diameter', None)
            if provided_unified is not None and (provided_hemi is None or provided_bowl is None):
                v = float(provided_unified)
                if provided_hemi is None:
                    self.hemi_counter_dot_base_diameter = v
                if provided_bowl is None:
                    self.bowl_counter_dot_base_diameter = v
            # Maintain legacy offset for code paths still referencing it
            base_for_offset = provided_unified if provided_unified is not None else float(self.hemi_counter_dot_base_diameter)
            self.counter_plate_dot_size_offset = float(base_for_offset) - float(self.emboss_dot_base_diameter)
        except Exception:
            pass
            
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
        # Hemisphere radius is based on the actual counter base diameter
        self.hemisphere_radius = float(getattr(self, 'hemi_counter_dot_base_diameter', getattr(self, 'counter_dot_base_diameter', 1.6))) / 2
        # Bowl (spherical cap) parameters
        self.bowl_base_radius = float(getattr(self, 'bowl_counter_dot_base_diameter', getattr(self, 'counter_dot_base_diameter', 1.8))) / 2
        # Clamp depth to safe bounds (0..plate_thickness)
        try:
            depth = float(getattr(self, 'counter_dot_depth', 0.8))
        except Exception:
            depth = 0.6
        self.counter_dot_depth = max(0.0, min(depth, self.card_thickness - self.epsilon_mm))
        self.plate_thickness = self.card_thickness
        self.epsilon = self.epsilon_mm
        self.cylinder_counter_plate_overcut_mm = self.cylinder_counter_plate_overcut_mm

        # Derived: active dot dimensions depending on shape selection
        if getattr(self, 'use_rounded_dots', 0):
            # Backward compatibility and alias mapping
            if not hasattr(self, 'rounded_dot_base_diameter') or self.rounded_dot_base_diameter is None:
                self.rounded_dot_base_diameter = self.rounded_dot_diameter
            if not hasattr(self, 'rounded_dot_dome_height') or self.rounded_dot_dome_height is None:
                # If only legacy rounded_dot_height provided, treat it as dome height
                self.rounded_dot_dome_height = self.rounded_dot_height
            # Prefer new base height, fall back to legacy cylinder height
            base_height = getattr(self, 'rounded_dot_base_height', None)
            if base_height is None:
                base_height = getattr(self, 'rounded_dot_cylinder_height', 0.2)
                self.rounded_dot_base_height = base_height
            else:
                # Keep legacy alias in sync when provided new param
                self.rounded_dot_cylinder_height = base_height

            # Prefer explicit dome diameter; fall back to base diameter for back-compat
            dome_diameter = getattr(self, 'rounded_dot_dome_diameter', None)
            if dome_diameter is None:
                dome_diameter = getattr(self, 'rounded_dot_base_diameter', 1.5)
                self.rounded_dot_dome_diameter = dome_diameter

            # Active dimensions for placement on surfaces
            self.active_dot_base_diameter = float(self.rounded_dot_base_diameter)
            self.active_dot_height = float(self.rounded_dot_base_height) + float(self.rounded_dot_dome_height)
        else:
            self.active_dot_height = self.emboss_dot_height
            self.active_dot_base_diameter = self.emboss_dot_base_diameter

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
    Create a braille dot mesh at the origin, then translate to (x, y, z).
    - Default: cone frustum using emboss parameters
    - Optional: rounded dome (spherical cap) using rounded parameters
    """
    if getattr(settings, 'use_rounded_dots', 0):
        # Cone frustum base + spherical cap dome (dome diameter equals cone flat-top diameter)
        base_diameter = float(getattr(settings, 'rounded_dot_base_diameter', getattr(settings, 'rounded_dot_diameter', 2.0)))
        dome_diameter = float(getattr(settings, 'rounded_dot_dome_diameter', getattr(settings, 'rounded_dot_base_diameter', 1.5)))
        base_radius = max(0.0, base_diameter / 2.0)
        top_radius = max(0.0, dome_diameter / 2.0)
        base_h = float(getattr(settings, 'rounded_dot_base_height', getattr(settings, 'rounded_dot_cylinder_height', 0.2)))
        dome_h = float(getattr(settings, 'rounded_dot_dome_height', getattr(settings, 'rounded_dot_height', 0.6)))
        if base_radius > 0 and base_h >= 0 and dome_h > 0:
            parts = []
            # Build a conical frustum by scaling the top ring of a cylinder
            if base_h > 0:
                frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h, sections=48)
                # Scale top vertices in XY so top radius equals top_radius
                if base_radius > 0:
                    scale_factor = (top_radius / base_radius) if base_radius > 1e-9 else 1.0
                else:
                    scale_factor = 1.0
                top_z = frustum.vertices[:, 2].max()
                is_top = np.isclose(frustum.vertices[:, 2], top_z)
                frustum.vertices[is_top, :2] *= scale_factor
                parts.append(frustum)

            # Spherical cap dome starting at top of frustum; base radius = top_radius
            R = (top_radius * top_radius + dome_h * dome_h) / (2.0 * dome_h)
            zc = (base_h / 2.0) + (dome_h - R)  # center so cap base lies at z = base_h/2
            sphere = trimesh.creation.icosphere(radius=R, subdivisions=max(2, int(getattr(settings, 'hemisphere_subdivisions', 1)) + 2))
            sphere.apply_translation([0.0, 0.0, zc])
            # Intersect with a slab to keep only z >= base_h/2
            slab_height = 2.0 * R + base_h + dome_h
            slab = trimesh.creation.box(extents=(4.0 * R + base_diameter, 4.0 * R + base_diameter, slab_height))
            slab.apply_translation([0.0, 0.0, (base_h / 2.0) + (slab_height / 2.0)])
            try:
                cap = trimesh.boolean.intersection([sphere, slab], engine='manifold')
            except Exception:
                cap = trimesh.boolean.intersection([sphere, slab])
            parts.append(cap)

            # Combine, recenter by shifting down half of dome height, then translate to (x, y, z)
            dot = trimesh.util.concatenate(parts)
            dot.apply_translation([0.0, 0.0, -dome_h / 2.0])
            dot.apply_translation((x, y, z))
            return dot
    
    # Default cone frustum path
    cylinder = trimesh.creation.cylinder(
        radius=settings.emboss_dot_base_diameter / 2,
        height=settings.emboss_dot_height,
        sections=16
    )
    
    if settings.emboss_dot_base_diameter > 0:
        scale_factor = settings.emboss_dot_flat_hat / settings.emboss_dot_base_diameter
        top_surface_z = cylinder.vertices[:, 2].max()
        is_top_vertex = np.isclose(cylinder.vertices[:, 2], top_surface_z)
        cylinder.vertices[is_top_vertex, :2] *= scale_factor
    
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


def _build_character_polygon(char_upper: str, target_width: float, target_height: float):
    """
    Build a 2D character outline as a shapely polygon, scaled to fit within
    the provided target width/height, centered at origin. Uses matplotlib if
    available; returns None on failure so callers can fall back gracefully.
    """
    try:
        # Lazy import to keep serverless light
        try:
            from matplotlib.textpath import TextPath  # type: ignore
            from matplotlib.font_manager import FontProperties  # type: ignore
            from matplotlib.path import Path  # type: ignore
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


def _compute_cylinder_frame(x_arc: float, cylinder_diameter_mm: float, seam_offset_deg: float = 0.0):
    """
    Compute local orthonormal frame and geometry parameters for a point on a
    cylinder given arc-length position and seam offset.
    Returns (r_hat, t_hat, z_hat, radius, circumference, theta).
    """
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm
    theta = (x_arc / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])
    z_hat = np.array([0.0, 0.0, 1.0])
    return r_hat, t_hat, z_hat, radius, circumference, theta


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
        print(f"WARNING: Failed to create character shape using matplotlib: {e}")
        print(f"Falling back to rectangle marker")
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
    
    # Debug: character marker generated
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

    # Add end-of-row text/number indicators and triangle markers for ALL rows (not just those with content)
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        if getattr(settings, 'indicator_shapes', 1):
            # Add end-of-row text/number indicator at the first cell position (column 0)
            # Calculate X position for the first column
            x_pos_first = settings.left_margin + settings.braille_x_adjust
            
            # Determine which character to use for beginning-of-row indicator
            # In manual mode: first character from the corresponding manual line
            # In auto mode: original_lines is an array of per-row indicator characters
            print(f"DEBUG: Row {row_num}, original_lines provided: {original_lines is not None}, length: {len(original_lines) if original_lines else 0}")
            if original_lines and row_num < len(original_lines):
                orig = (original_lines[row_num] or '').strip()
                # If auto supplied a single indicator character per row, just use it
                indicator_char = orig[0] if orig else ''
                print(f"DEBUG: Row {row_num} indicator candidate: '{indicator_char}'")
                if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
                    print(f"DEBUG: Creating character shape for '{indicator_char}' at first cell")
                    line_end_mesh = create_character_shape_3d(indicator_char, x_pos_first, y_pos, settings, height=1.0, for_subtraction=True)
                else:
                    print(f"DEBUG: Indicator not alphanumeric or empty, using rectangle for row {row_num}")
                    line_end_mesh = create_card_line_end_marker_3d(x_pos_first, y_pos, settings, height=0.5, for_subtraction=True)
            else:
                # No indicator info; default to rectangle
                print(f"DEBUG: No indicator info for row {row_num}, using rectangle")
                line_end_mesh = create_card_line_end_marker_3d(x_pos_first, y_pos, settings, height=0.5, for_subtraction=True)
            
            marker_meshes.append(line_end_mesh)
            
            # Add triangle marker at the last cell position (grid_columns - 1)
            # Calculate X position for the last column
            x_pos_last = settings.left_margin + ((settings.grid_columns - 1) * settings.cell_spacing) + settings.braille_x_adjust
            
            # Create triangle marker for this row (recessed for embossing plate)
            triangle_mesh = create_card_triangle_marker_3d(x_pos_last, y_pos, settings, height=0.6, for_subtraction=True)
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
            error_msg = f"Line {row_num + 1} does not contain proper braille Unicode characters. Frontend must translate text to braille before sending."
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Check if braille text exceeds grid capacity
        reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
        available_columns = settings.grid_columns - reserved
        if len(braille_text) > available_columns:
            # Warn and truncate instead of failing hard
            over = len(braille_text) - available_columns
            print(
                f"WARNING: Line {row_num + 1} exceeds available columns by {over} cells. "
                f"Truncating to {available_columns} cells to continue generation."
            )
            braille_text = braille_text[:available_columns]
        
        # Calculate Y position for this row (top-down)
        y_pos = settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process each braille character in the line
        for col_num, braille_char in enumerate(braille_text):
            if col_num >= available_columns:
                break
                
            dots = braille_to_dots(braille_char)
            
            # Calculate X position for this column. Shift by one cell if indicators are enabled.
            x_pos = settings.left_margin + ((col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)) * settings.cell_spacing) + settings.braille_x_adjust
            
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
        print(f"Created positive plate with {len(meshes)-1} braille dots, {settings.grid_rows} text/number indicators, and {settings.grid_rows} triangle markers")
    else:
        print(f"Created positive plate with {len(meshes)-1} braille dots and no indicator shapes")
    
    # Combine all positive meshes (base + dots)
    combined_mesh = trimesh.util.concatenate(meshes)
    
    # Subtract marker recesses from the combined mesh
    if getattr(settings, 'indicator_shapes', 1) and marker_meshes:
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
    
    # Calculate vertical centering
    # The braille content spans from the top dot of the first row to the bottom dot of the last row
    # Each cell has dots at offsets [+dot_spacing, 0, -dot_spacing] from cell center
    # So a cell spans 2 * dot_spacing vertically
    
    # Total content height calculation:
    # - Distance between first and last row centers: (grid_rows - 1) * line_spacing
    # - Half cell height above first row center: dot_spacing
    # - Half cell height below last row center: dot_spacing
    braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
    
    # Calculate where to position the first row's center
    # We want the content centered, so:
    # - Space above content = space below content = (cylinder_height - content_height) / 2
    # - First row center = cylinder_height - space_above - dot_spacing
    space_above = (cylinder_height_mm - braille_content_height) / 2.0
    first_row_center_y = cylinder_height_mm - space_above - settings.dot_spacing
    
    # Process up to grid_rows lines
    for row_num in range(min(settings.grid_rows, len(braille_lines))):
        line = braille_lines[row_num].strip()
        if not line:
            continue
            
        # Check if input contains proper braille Unicode
        has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line)
        if not has_braille_chars:
            continue
        
        # Calculate Y position for this row with vertical centering
        y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process each character up to available columns (reserve 2 if indicators enabled)
        reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
        max_cols = settings.grid_columns - reserved
        for col_num, braille_char in enumerate(line[:max_cols]):
            # Calculate angular position for this column (shift by one if indicators enabled)
            angle = start_angle + ((col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)) * cell_spacing_angle)
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

def create_cylinder_shell(diameter_mm, height_mm, polygonal_cutout_radius_mm, polygonal_cutout_sides=12, align_vertex_theta_rad=None):
    """
    Create a cylinder with an N-point polygonal cutout along its length.
    
    Args:
        diameter_mm: Outer diameter of the cylinder
        height_mm: Height of the cylinder
        polygonal_cutout_radius_mm: Inscribed radius of the polygonal cutout
        polygonal_cutout_sides: Number of sides/points of the polygonal cutout (>= 3)
        align_vertex_theta_rad: Optional absolute angle (radians) around Z to rotate
            the polygonal cutout so that one of its vertices aligns with this angle.
            Useful to align a cutout vertex with the triangle indicator column
            (including seam offset) on the cylinder surface.
    """
    outer_radius = diameter_mm / 2
    
    # Create the main solid cylinder
    main_cylinder = trimesh.creation.cylinder(radius=outer_radius, height=height_mm, sections=64)
    
    # If no cutout is specified, return the solid cylinder
    if polygonal_cutout_radius_mm <= 0:
        return main_cylinder
    
    # Create an N-point polygonal prism for the cutout
    # The prism extends the full height of the cylinder
    # Calculate the circumscribed radius from the inscribed radius
    # For a regular N-gon: circumscribed_radius = inscribed_radius / cos(pi/N)
    # Clamp the number of sides for safety
    polygonal_cutout_sides = max(3, int(polygonal_cutout_sides))
    circumscribed_radius = polygonal_cutout_radius_mm / np.cos(np.pi / polygonal_cutout_sides)
    
    # Create the polygon vertices
    angles = np.linspace(0, 2*np.pi, polygonal_cutout_sides, endpoint=False)
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
    
    # Optionally rotate the cutout so a vertex aligns with a target angle around Z
    # By construction, one vertex initially lies along +X (theta = 0). Rotating by
    # align_vertex_theta_rad moves that vertex to the desired absolute angle.
    if align_vertex_theta_rad is not None:
        Rz = trimesh.transformations.rotation_matrix(align_vertex_theta_rad, [0.0, 0.0, 1.0])
        cutout_prism.apply_transform(Rz)
    
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

def create_cylinder_triangle_marker(x_arc, y_local, settings: CardSettings, cylinder_diameter_mm, seam_offset_deg=0, height_mm=0.6, for_subtraction=True, point_left=False):
    """
    Create a triangular prism for cylinder surface marking.
    
    Args:
        x_arc: Arc length position along circumference (same units as mm on the card)
        y_local: Z position relative to cylinder center (card Y minus height/2)
        settings: CardSettings object
        cylinder_diameter_mm: Cylinder diameter
        seam_offset_deg: Rotation offset for seam
        height_mm: Depth/height of the triangle marker (default 0.6mm)
        for_subtraction: If True, creates a tool for boolean subtraction to make recesses
        point_left: If True, mirror triangle so apex points toward negative tangent (left in unrolled view)
    """
    r_hat, t_hat, z_hat, radius, circumference, theta = _compute_cylinder_frame(x_arc, cylinder_diameter_mm, seam_offset_deg)
    
    # Triangle dimensions - standard guide triangle shape
    base_height = 2.0 * settings.dot_spacing  # Vertical extent
    triangle_width = settings.dot_spacing     # Horizontal extent (pointing right in tangent direction)
    
    # Build 2D triangle in local tangent (X=t) and vertical (Y=z) plane
    # Vertices: base on left, apex pointing right
    from shapely.geometry import Polygon as ShapelyPolygon
    if point_left:
        # Mirror along vertical axis so apex points left (negative tangent)
        tri_2d = ShapelyPolygon([
            (0.0, -settings.dot_spacing),    # Bottom of base (right side)
            (0.0,  settings.dot_spacing),    # Top of base (right side)
            (-triangle_width, 0.0)           # Apex (pointing left)
        ])
    else:
        tri_2d = ShapelyPolygon([
            (0.0, -settings.dot_spacing),    # Bottom of base
            (0.0,  settings.dot_spacing),    # Top of base
            (triangle_width, 0.0)            # Apex (pointing right/tangentially)
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
        # For extruded triangle (outward from cylinder surface)
        tri_prism_local = trimesh.creation.extrude_polygon(tri_2d, height=height_mm)
        
        # Build transform for outward extrusion
        T = np.eye(4)
        T[:3, 0] = t_hat   # X axis (tangential)
        T[:3, 1] = z_hat   # Y axis (vertical)
        T[:3, 2] = r_hat   # Z axis (radial outward)
        
        # Slightly embed the triangle into the cylinder so union attaches robustly
        embed = max(getattr(settings, 'epsilon', 0.001), 0.05)
        # Place the base of the prism just inside the surface (radius - embed), extruding outward
        center_pos = r_hat * (radius - embed) + z_hat * y_local
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


def create_cylinder_character_shape(character, x_arc, y_local, settings: CardSettings, cylinder_diameter_mm, seam_offset_deg=0, height_mm=1.0, for_subtraction=True):
    """
    Create a 3D character shape (capital letter A-Z or number 0-9) for end of row marking on cylinder surface.
    Uses matplotlib's TextPath for proper font rendering.
    
    Args:
        character: Single character (A-Z or 0-9)
        x_arc: Arc length position along circumference (same units as mm on the card)
        y_local: Z position relative to cylinder center (card Y minus height/2)
        settings: CardSettings object
        cylinder_diameter_mm: Cylinder diameter
        seam_offset_deg: Seam rotation offset in degrees
        height_mm: Depth of the character recess (default 1.0mm)
        for_subtraction: If True, creates a tool for boolean subtraction
    
    Returns:
        Trimesh object representing the 3D character marker transformed to cylinder
    """
    # Debug: cylinder character marker generation
    
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm
    
    # Angle around cylinder for planar x position
    theta = (x_arc / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)
    
    # Local orthonormal frame at theta
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])      # radial outward
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])     # tangential
    z_hat = np.array([0.0, 0.0, 1.0])                          # cylinder axis
    
    # Define character size based on braille cell dimensions (scaled 56.25% bigger than original)
    char_height = 2 * settings.dot_spacing + 4.375  # 9.375mm for default 2.5mm dot spacing
    char_width = settings.dot_spacing * 0.8 + 2.6875  # 4.6875mm for default 2.5mm dot spacing
    
    # Get the character definition
    char_upper = character.upper()
    if not (char_upper.isalpha() or char_upper.isdigit()):
        # Fall back to rectangle for undefined characters
        return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
    
    try:
        # Build character polygon using shared helper
        char_2d = _build_character_polygon(char_upper, char_width, char_height)
        if char_2d is None:
            return create_cylinder_line_end_marker(x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction)
        
    except Exception as e:
        print(f"WARNING: Failed to create character shape using matplotlib: {e}")
        print(f"Falling back to rectangle marker")
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
    
    # Debug: cylinder character marker generated
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
    # Use active height (cone or rounded)
    dot_height = settings.active_dot_height
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
            - polygonal_cutout_radius_mm: Inscribed radius of polygonal cutout (0 = no cutout)
            - polygonal_cutout_sides: Number of sides for polygonal cutout (>=3)
            - seam_offset_deg: Rotation offset for seam
        original_lines: List of original text lines (before braille conversion) for character indicators
    """
    if settings is None:
        settings = CardSettings()
    
    if cylinder_params is None:
        cylinder_params = {
            'diameter_mm': 31.35,
            'height_mm': settings.card_height,
            'polygonal_cutout_radius_mm': 13,
            'polygonal_cutout_sides': 12,
            'seam_offset_deg': 355
        }
    
    diameter = float(cylinder_params.get('diameter_mm', 31.35))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 355))
    
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
    
    # Compute triangle column absolute angle (including seam) to align polygon cutout vertex
    seam_offset_rad = np.radians(seam_offset)
    grid_angle = grid_width / radius
    start_angle = -grid_angle / 2
    triangle_angle = start_angle + ((settings.grid_columns - 1) * settings.cell_spacing / radius)
    cutout_align_theta = triangle_angle + seam_offset_rad
    
    # Create cylinder shell with polygon cutout aligned to triangle marker column
    cylinder_shell = create_cylinder_shell(
        diameter,
        height,
        polygonal_cutout_radius,
        polygonal_cutout_sides,
        align_vertex_theta_rad=cutout_align_theta
    )
    meshes = [cylinder_shell]
    
    # Layout braille cells on cylinder
    cells, cells_per_row = layout_cylindrical_cells(lines, settings, diameter, height)
    
    # Calculate vertical centering for markers
    # The braille content spans from the top dot of the first row to the bottom dot of the last row
    # Each cell has dots at offsets [+dot_spacing, 0, -dot_spacing] from cell center
    # So a cell spans 2 * dot_spacing vertically
    
    # Total content height calculation:
    # - Distance between first and last row centers: (grid_rows - 1) * line_spacing
    # - Half cell height above first row center: dot_spacing
    # - Half cell height below last row center: dot_spacing
    braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
    
    # Calculate where to position the first row's center
    # We want the content centered, so:
    # - Space above content = space below content = (cylinder_height - content_height) / 2
    # - First row center = cylinder_height - space_above - dot_spacing
    space_above = (height - braille_content_height) / 2.0
    first_row_center_y = height - space_above - settings.dot_spacing
    
    # Add end-of-row text/number indicators and triangle recess markers for ALL rows (not just those with content)
    text_number_meshes = []
    triangle_meshes = []
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row with vertical centering
        y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # The grid is centered, so start angle is -grid_angle/2
        grid_width = (settings.grid_columns - 1) * settings.cell_spacing
        grid_angle = grid_width / radius
        start_angle = -grid_angle / 2
        
        # Y position in local cylinder coordinates
        y_local = y_pos - (height / 2.0)
        
        if getattr(settings, 'indicator_shapes', 1):
            # Add end-of-row text/number indicator at the first cell position (column 0)
            text_number_x = start_angle * radius
            
            # Determine which character to use for end-of-row indicator
            if original_lines and row_num < len(original_lines):
                original_text = original_lines[row_num].strip()
                if original_text:
                    # Get the first character (letter or number)
                    first_char = original_text[0]
                    if first_char.isalpha() or first_char.isdigit():
                        # Create character shape for end-of-row indicator (1.0mm deep)
                        text_number_mesh = create_cylinder_character_shape(
                            first_char, text_number_x, y_local, settings, diameter, seam_offset, height_mm=1.0, for_subtraction=True
                        )
                    else:
                        # Fall back to rectangle for non-alphanumeric first characters
                        text_number_mesh = create_cylinder_line_end_marker(
                            text_number_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
                        )
                else:
                    # Empty line, use rectangle
                    text_number_mesh = create_cylinder_line_end_marker(
                        text_number_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
                    )
            else:
                # No original text provided, use rectangle as fallback
                text_number_mesh = create_cylinder_line_end_marker(
                    text_number_x, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
                )
            
            text_number_meshes.append(text_number_mesh)
            
            # Add triangle marker at the last cell position (grid_columns - 1)
            # Calculate X position for the last column
            triangle_angle = start_angle + ((settings.grid_columns - 1) * settings.cell_spacing / radius)
            triangle_x = triangle_angle * radius
            
            # Create triangle marker for subtraction (will create recess)
            triangle_mesh = create_cylinder_triangle_marker(
                triangle_x, y_local, settings, diameter, seam_offset, height_mm=0.6, for_subtraction=True
            )
            triangle_meshes.append(triangle_mesh)
    
    # Subtract text/number indicators and triangle markers to recess them into the surface
    print(f"DEBUG: Creating {len(text_number_meshes)} text/number recesses and {len(triangle_meshes)} triangle recesses on emboss cylinder")
    
    # Combine all markers (text/number indicators and triangles) for efficient boolean operations
    all_markers = (text_number_meshes + triangle_meshes) if getattr(settings, 'indicator_shapes', 1) else []
    
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
    
    # Check for overflow based on grid dimensions (accounting for reserved columns when indicators enabled)
    total_cells_needed = sum(len(line.strip()) for line in lines if line.strip())
    reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
    total_cells_available = (settings.grid_columns - reserved) * settings.grid_rows
    
    if total_cells_needed > total_cells_available:
        print(f"Warning: Text requires {total_cells_needed} cells but grid has {total_cells_available} cells ({settings.grid_columns-reserved}×{settings.grid_rows} after row markers)")
    
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
                z = polygonal_cutout_radius + settings.active_dot_height / 2  # unused in transform now
                
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
            - polygonal_cutout_radius_mm: Inscribed radius of polygonal cutout (0 = no cutout)
            - polygonal_cutout_sides: Number of sides for polygonal cutout (>=3)
            - seam_offset_deg: Rotation offset for seam
    """
    if cylinder_params is None:
        cylinder_params = {
            'diameter_mm': 31.35,
            'height_mm': settings.card_height,
            'polygonal_cutout_radius_mm': 13,
            'polygonal_cutout_sides': 12,
            'seam_offset_deg': 355
        }
    
    diameter = float(cylinder_params.get('diameter_mm', 31.35))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 355))
    
    print(f"Creating cylinder counter plate - Diameter: {diameter}mm, Height: {height}mm, Cutout Radius: {polygonal_cutout_radius}mm")

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

    # Compute first-column triangle absolute angle (including seam) to align polygon cutout vertex
    # Counter plate uses triangle at the first column
    seam_offset_rad = np.radians(seam_offset)
    first_col_angle = start_angle
    cutout_align_theta = first_col_angle + seam_offset_rad

    # Create cylinder shell with polygon cutout aligned to triangle marker column
    cylinder_shell = create_cylinder_shell(
        diameter,
        height,
        polygonal_cutout_radius,
        polygonal_cutout_sides,
        align_vertex_theta_rad=cutout_align_theta
    )
    
    # Use grid_rows from settings
    rows_on_cylinder = settings.grid_rows
    
    # Convert dot spacing to angular measurements
    dot_spacing_angle = settings.dot_spacing / radius
    
    # Dot positioning with angular offsets for columns, linear for rows
    dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]  # Vertical stays linear
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    
    # Calculate vertical centering
    # The braille content spans from the top dot of the first row to the bottom dot of the last row
    # Each cell has dots at offsets [+dot_spacing, 0, -dot_spacing] from cell center
    # So a cell spans 2 * dot_spacing vertically
    
    # Total content height calculation:
    # - Distance between first and last row centers: (grid_rows - 1) * line_spacing
    # - Half cell height above first row center: dot_spacing
    # - Half cell height below last row center: dot_spacing
    braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
    
    # Calculate where to position the first row's center
    # We want the content centered, so:
    # - Space above content = space below content = (cylinder_height - content_height) / 2
    # - First row center = cylinder_height - space_above - dot_spacing
    space_above = (height - braille_content_height) / 2.0
    first_row_center_y = height - space_above - settings.dot_spacing
    
    # Create row markers (triangle and line) for ALL rows
    line_end_meshes = []
    triangle_meshes = []
    
    # Create line ends and triangles for ALL rows in the grid to match embossing plate layout
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row with vertical centering
        y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
        y_local = y_pos - (height / 2.0)
        
        if getattr(settings, 'indicator_shapes', 1):
            # For counter plate: triangle at first column (apex pointing left), line at last column
            # First column (triangle):
            triangle_x_first = start_angle * radius
            triangle_mesh = create_cylinder_triangle_marker(
                triangle_x_first, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True, point_left=True
            )
            triangle_meshes.append(triangle_mesh)

            # Last column (line end):
            last_col_angle = start_angle + ((settings.grid_columns - 1) * cell_spacing_angle)
            line_end_x_last = last_col_angle * radius
            line_end_mesh = create_cylinder_line_end_marker(
                line_end_x_last, y_local, settings, diameter, seam_offset, height_mm=0.5, for_subtraction=True
            )
            line_end_meshes.append(line_end_mesh)
    
    # Create recess tools for ALL dot positions in ALL cells (universal counter plate)
    sphere_meshes = []
    
    # Get recess shape once outside the loop
    recess_shape = int(getattr(settings, 'recess_shape', 1))
    
    # Process ALL cells in the grid (not just those with braille content)
    # Mirror horizontally (right-to-left) so the counter plate reads R→L when printed
    num_text_cols = settings.grid_columns - 2
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row with vertical centering
        y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
        
        # Process ALL columns mirrored (minus two for first cell indicator and last cell triangle)
        for col_num in range(num_text_cols):
            # Mirror column index across row so cells are placed right-to-left
            mirrored_idx = (num_text_cols - 1) - col_num
            # Calculate cell position (shifted by one cell due to first cell indicator)
            cell_angle = start_angle + ((mirrored_idx + 1) * cell_spacing_angle)
            cell_x = cell_angle * radius  # Convert to arc length
            
            # Create recess tool for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                # Use angular offset for horizontal spacing, converted back to arc length
                dot_x = cell_x + (dot_col_angle_offsets[dot_pos[1]] * radius)
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                if recess_shape == 2:
                    # Cone frustum on cylinder surface oriented along radial direction
                    base_d = float(getattr(settings, 'cone_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.6)))
                    hat_d = float(getattr(settings, 'cone_counter_dot_flat_hat', 0.4))
                    h_cone = float(getattr(settings, 'cone_counter_dot_height', 0.8))
                    base_r = max(settings.epsilon_mm, base_d / 2.0)
                    hat_r = max(settings.epsilon_mm, hat_d / 2.0)
                    # Ensure recess height exceeds radial overcut so it properly intersects the outer surface
                    radial_overcut = max(settings.epsilon_mm, getattr(settings, 'cylinder_counter_plate_overcut_mm', 0.05))
                    h_cone = max(settings.epsilon_mm, h_cone + radial_overcut)
                    segments = 24
                    # Build local frustum along +Z with base at z=0 and bottom at z=-h_cone
                    angles = np.linspace(0, 2*np.pi, segments, endpoint=False)
                    top_ring = np.column_stack([base_r*np.cos(angles), base_r*np.sin(angles), np.zeros_like(angles)])
                    bot_ring = np.column_stack([hat_r*np.cos(angles), hat_r*np.sin(angles), -h_cone*np.ones_like(angles)])
                    vertices = np.vstack([top_ring, bot_ring, [[0,0,0]], [[0,0,-h_cone]]])
                    top_center_index = 2*segments
                    bot_center_index = 2*segments + 1
                    faces = []
                    for i in range(segments):
                        j = (i + 1) % segments
                        # indices
                        ti = i
                        tj = j
                        bi = segments + i
                        bj = segments + j
                        # side quad as two triangles (ensure correct orientation for outward normals)
                        faces.append([ti, bi, tj])
                        faces.append([bi, bj, tj])
                        # top cap - outward normal pointing up
                        faces.append([top_center_index, ti, tj])
                        # bottom cap - outward normal pointing down
                        faces.append([bot_center_index, bj, bi])
                    frustum = trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)
                    if not frustum.is_volume:
                        try:
                            frustum.fix_normals()
                            # Ensure the mesh is watertight and has proper orientation
                            if not frustum.is_watertight:
                                frustum.fill_holes()
                            # Force recomputation of volume properties
                            frustum._cache.clear()
                            if not frustum.is_volume:
                                # If still not a volume, try to repair it
                                frustum = frustum.repair()
                        except Exception:
                            pass
                    # Transform to cylinder surface with local frame
                    outer_radius = diameter / 2
                    theta = (dot_x / (np.pi * diameter)) * 2 * np.pi + np.radians(seam_offset)
                    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])
                    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])
                    z_hat = np.array([0.0, 0.0, 1.0])
                    # Base center on cylinder surface
                    overcut = max(settings.epsilon, getattr(settings, 'cylinder_counter_plate_overcut_mm', 0.05))
                    base_center = r_hat * (outer_radius + overcut) + z_hat * (dot_y - (height / 2.0))
                    T = np.eye(4)
                    T[:3, 0] = t_hat
                    T[:3, 1] = z_hat
                    T[:3, 2] = r_hat
                    T[:3, 3] = base_center
                    frustum.apply_transform(T)
                    sphere_meshes.append(frustum)
                else:
                    # Create sphere for hemisphere or bowl cap
                    # Choose base diameter based on selected recess shape
                    use_bowl = (recess_shape == 1)
                    try:
                        if use_bowl:
                            counter_base = float(getattr(settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
                        else:
                            counter_base = float(getattr(settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
                    except Exception:
                        counter_base = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
                    a = counter_base / 2.0
                    if use_bowl:
                        h = float(getattr(settings, 'counter_dot_depth', 0.6))
                        # Guard minimum
                        h = max(settings.epsilon_mm, h)
                        sphere_radius = (a * a + h * h) / (2.0 * h)
                    else:
                        sphere_radius = a
                    sphere = trimesh.creation.icosphere(subdivisions=settings.hemisphere_subdivisions, radius=sphere_radius)
                    if not sphere.is_volume:
                        sphere.fix_normals()
                    outer_radius = diameter / 2
                    theta = (dot_x / (np.pi * diameter)) * 2 * np.pi + np.radians(seam_offset)
                    overcut = max(settings.epsilon, getattr(settings, 'cylinder_counter_plate_overcut_mm', 0.05))
                    if use_bowl:
                        h = float(getattr(settings, 'counter_dot_depth', 0.6))
                        h = max(settings.epsilon_mm, h)
                        center_radius = outer_radius + (sphere_radius - h)
                    else:
                        center_radius = outer_radius + overcut
                    cyl_x = center_radius * np.cos(theta)
                    cyl_y = center_radius * np.sin(theta)
                    cyl_z = dot_y - (height / 2.0)
                    sphere.apply_translation([cyl_x, cyl_y, cyl_z])
                    sphere_meshes.append(sphere)
    
    print(f"DEBUG: Creating {len(sphere_meshes)} recess tools on cylinder counter plate (recess_shape={recess_shape})")
    
    if not sphere_meshes:
        print("WARNING: No spheres were generated for cylinder counter plate. Returning base shell.")
        # The cylinder is already created with vertical axis (along Z)
        # No rotation needed - it should stand upright
        # Just ensure the base is at Z=0
        min_z = cylinder_shell.bounds[0][2]
        cylinder_shell.apply_translation([0, 0, -min_z])
        
        return cylinder_shell
    
    # Special-case: for cone frusta, prefer individual subtraction for robustness
    if recess_shape == 2 and sphere_meshes:
        try:
            print("DEBUG: Cylinder cone mode - subtracting frusta individually for robustness...")
            result_shell = cylinder_shell.copy()
            for i, tool in enumerate(sphere_meshes):
                try:
                    print(f"DEBUG: Cylinder subtract recess tool {i+1}/{len(sphere_meshes)}")
                    result_shell = trimesh.boolean.difference([result_shell, tool])
                except Exception as e_tool:
                    print(f"WARNING: Cylinder cone subtraction failed for tool {i+1}: {e_tool}")
                    continue
            for i, triangle in enumerate(triangle_meshes):
                try:
                    result_shell = trimesh.boolean.difference([result_shell, triangle])
                except Exception as e_tri:
                    print(f"WARNING: Cylinder triangle subtraction failed {i+1}: {e_tri}")
                    continue
            for i, line_end in enumerate(line_end_meshes):
                try:
                    result_shell = trimesh.boolean.difference([result_shell, line_end])
                except Exception as e_line:
                    print(f"WARNING: Cylinder line-end subtraction failed {i+1}: {e_line}")
                    continue
            if not result_shell.is_watertight:
                result_shell.fill_holes()
            min_z = result_shell.bounds[0][2]
            result_shell.apply_translation([0, 0, -min_z])
            print(f"DEBUG: Cylinder cone plate completed: {len(result_shell.vertices)} vertices")
            return result_shell
        except Exception as e_cyl_cone:
            print(f"ERROR: Cylinder cone individual subtraction failed: {e_cyl_cone}")
            # Fall through to robust boolean strategy below as a last attempt

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
            
            # Union all triangles (for subtraction into the cylinder shell)
            union_triangles = None
            if triangle_meshes:
                print(f"DEBUG: Cylinder boolean - union triangles for subtraction with {engine_name}...")
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
            
            # Combine cutouts (spheres and line ends) for subtraction
            print(f"DEBUG: Cylinder boolean - combining cutouts for subtraction with {engine_name}...")
            cutouts_list = [union_spheres]
            if line_end_meshes:
                cutouts_list.append(union_line_ends)
            if union_triangles is not None:
                cutouts_list.append(union_triangles)
            
            if len(cutouts_list) > 1:
                all_cutouts = trimesh.boolean.union(cutouts_list, engine=engine)
            else:
                all_cutouts = cutouts_list[0]
            
            print(f"DEBUG: Cylinder boolean - subtract cutouts from cylinder shell with {engine_name}...")
            final_shell = trimesh.boolean.difference([cylinder_shell, all_cutouts], engine=engine)
            
            # Triangles are recessed via subtraction; no union back
            
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
        
        # Subtract triangles individually (recess them)
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
    - Hemisphere radius r = counter_dot_base_diameter / 2 (or legacy: (emboss_dot_base_diameter + counter_plate_dot_size_offset) / 2).
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
    try:
        counter_base = float(getattr(params, 'hemi_counter_dot_base_diameter', getattr(params, 'counter_dot_base_diameter')))
    except Exception:
        counter_base = params.emboss_dot_base_diameter + params.counter_plate_dot_size_offset
    hemisphere_radius = counter_base / 2
    print(f"DEBUG: Hemisphere radius: {hemisphere_radius:.3f}mm (base: {params.emboss_dot_base_diameter}mm + offset: {params.counter_plate_dot_size_offset}mm)")
    
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
            x_pos = params.left_margin + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing) + params.braille_x_adjust
            
            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]
                
                # Create an icosphere with the calculated hemisphere radius
                # Use hemisphere_subdivisions parameter to control mesh density
                sphere = trimesh.creation.icosphere(subdivisions=params.hemisphere_subdivisions, radius=hemisphere_radius)
                # Position the sphere so its equator lies at the top surface (z = plate_thickness)
                z_pos = params.plate_thickness
                sphere.apply_translation((dot_x, dot_y, z_pos))
                sphere_meshes.append(sphere)
                total_spheres += 1
    
    print(f"DEBUG: Created {total_spheres} hemispheres for counter plate")
    
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
            
            # Union all triangles (these will be used for subtraction into the plate)
            union_triangles = None
            if triangle_meshes:
                print(f"DEBUG: Unioning {len(triangle_meshes)} triangles (for subtraction)...")
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
            
            # Combine cutouts (spheres and line ends) for subtraction
            print("DEBUG: Combining cutouts for subtraction...")
            cutouts_list = [union_spheres]
            if line_end_meshes:
                cutouts_list.append(union_line_ends)
            if union_triangles is not None:
                cutouts_list.append(union_triangles)
            
            if len(cutouts_list) > 1:
                all_cutouts = trimesh.boolean.union(cutouts_list, engine=engine)
            else:
                all_cutouts = cutouts_list[0]
            
            print("DEBUG: Subtracting cutouts from plate...")
            # Subtract the cutouts (spheres, line ends, and triangles) from the plate
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
        
        # Subtract triangles individually (recess them)
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
    plate_mesh.apply_translation((params.card_width/2, params.card_height/2, params.plate_thickness/2))

    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Inputs
    a = float(getattr(params, 'bowl_counter_dot_base_diameter', getattr(params, 'counter_dot_base_diameter', 1.6))) / 2.0
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
            x_pos = params.left_margin + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing) + params.braille_x_adjust
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

    print(f"DEBUG: Created {total_spheres} bowl caps for counter plate (a={a:.3f}mm, h={h:.3f}mm, R={R:.3f}mm)")

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
        print("WARNING: No spheres were generated. Returning base plate.")
        return plate_mesh

    # Boolean operations
    engines_to_try = ['manifold', 'blender', None]
    for engine in engines_to_try:
        try:
            engine_name = engine if engine else "trimesh-default"
            print(f"DEBUG: Bowl boolean ops with {engine_name}...")

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
            print(f"DEBUG: Counter plate with bowl recess completed: {len(counter_plate_mesh.vertices)} verts")
            return counter_plate_mesh
        except Exception as e:
            print(f"ERROR: Bowl boolean with {engine_name} failed: {e}")
            if engine == engines_to_try[-1]:
                print("WARNING: Falling back to simple negative plate method.")
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
    plate_mesh.apply_translation((params.card_width/2, params.card_height/2, params.plate_thickness/2))

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
    angles = np.linspace(0, 2*np.pi, segments, endpoint=False)
    cos_angles = np.cos(angles)
    sin_angles = np.sin(angles)
    
    # Create conical frustum solids for subtraction using optimized approach
    recess_meshes = []
    total_recess = 0
    for row in range(params.grid_rows):
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust
        reserved = 2 if getattr(params, 'indicator_shapes', 1) else 0
        for col in range(params.grid_columns - reserved):
            x_pos = params.left_margin + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing) + params.braille_x_adjust
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]

                # OPTIMIZATION: Use pre-calculated trigonometric values
                top_ring = np.column_stack([base_r*cos_angles, base_r*sin_angles, np.zeros_like(angles)])
                bot_ring = np.column_stack([hat_r*cos_angles, hat_r*sin_angles, -height_h*np.ones_like(angles)])
                vertices = np.vstack([top_ring, bot_ring, [[0,0,0]], [[0,0,-height_h]]])
                top_center_index = 2*segments
                bot_center_index = 2*segments + 1
                
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
        print("WARNING: No cone recesses were generated. Returning base plate.")
        return plate_mesh

    print(f"DEBUG: Created {total_recess} cone frusta for counter plate (base_d={base_d:.3f}mm, hat_d={hat_d:.3f}mm, h={height_h:.3f}mm)")

    # OPTIMIZATION: Use union operations like bowl/hemisphere for better performance
    try:
        # Union all recess meshes first (like bowl/hemisphere approach)
        if len(recess_meshes) == 1:
            union_recesses = recess_meshes[0]
        else:
            # Try different engines for better performance
            engines_to_try = ['manifold', 'blender', None]
            union_recesses = None
            for engine in engines_to_try:
                try:
                    engine_name = engine if engine else "trimesh-default"
                    print(f"DEBUG: Cone union with {engine_name}...")
                    union_recesses = trimesh.boolean.union(recess_meshes, engine=engine)
                    break
                except Exception as e:
                    print(f"WARNING: Failed to union with {engine_name}: {e}")
                    continue
            
            if union_recesses is None:
                raise Exception("All union engines failed")

        # Union markers
        union_triangles = None
        if triangle_meshes:
            if len(triangle_meshes) == 1:
                union_triangles = triangle_meshes[0]
            else:
                union_triangles = trimesh.boolean.union(triangle_meshes, engine='manifold')

        union_line_ends = None
        if line_end_meshes:
            if len(line_end_meshes) == 1:
                union_line_ends = line_end_meshes[0]
            else:
                union_line_ends = trimesh.boolean.union(line_end_meshes, engine='manifold')

        # Combine all cutouts
        cutouts_list = [union_recesses]
        if union_line_ends is not None:
            cutouts_list.append(union_line_ends)
        if union_triangles is not None:
            cutouts_list.append(union_triangles)

        # Single difference operation (much faster than individual subtractions)
        if len(cutouts_list) > 1:
            union_cutouts = trimesh.boolean.union(cutouts_list, engine='manifold')
        else:
            union_cutouts = cutouts_list[0]

        result_mesh = trimesh.boolean.difference([plate_mesh, union_cutouts], engine='manifold')
        
        if not result_mesh.is_watertight:
            result_mesh.fill_holes()
        print(f"DEBUG: Cone recess (optimized union approach) completed: {len(result_mesh.vertices)} verts")
        return result_mesh
        
    except Exception as e_final:
        print(f"ERROR: Cone recess union approach failed: {e_final}")
        print("WARNING: Falling back to individual subtraction method.")
        
        # Fallback to individual subtraction if union approach fails
        try:
            result_mesh = plate_mesh.copy()
            for i, recess in enumerate(recess_meshes):
                try:
                    if (i % 50) == 0:
                        print(f"DEBUG: Subtracting cone frustum {i+1}/{len(recess_meshes)}...")
                    result_mesh = trimesh.boolean.difference([result_mesh, recess])
                except Exception as e_sub:
                    print(f"WARNING: Failed to subtract frustum {i+1}: {e_sub}")
                    continue
            for i, triangle in enumerate(triangle_meshes):
                try:
                    result_mesh = trimesh.boolean.difference([result_mesh, triangle])
                except Exception as e_tri:
                    print(f"WARNING: Failed to subtract triangle {i+1}: {e_tri}")
                    continue
            for i, line_end in enumerate(line_end_meshes):
                try:
                    result_mesh = trimesh.boolean.difference([result_mesh, line_end])
                except Exception as e_line:
                    print(f"WARNING: Failed to subtract line end {i+1}: {e_line}")
                    continue
            if not result_mesh.is_watertight:
                result_mesh.fill_holes()
            print(f"DEBUG: Cone recess (fallback individual subtraction) completed: {len(result_mesh.vertices)} verts")
            return result_mesh
        except Exception as e_fallback:
            print(f"ERROR: All cone recess methods failed: {e_fallback}")
            print("WARNING: Returning simple negative plate method.")
            return create_simple_negative_plate(params)


# @app.route('/health')
# def health_check():
#     return jsonify({'status': 'ok', 'message': 'Vercel backend is running'})




@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
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
        app.logger.error(f"Failed to serve favicon: {e}")
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
            app.logger.error("Static directory not found")
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
# @limiter.limit("10 per minute")  # disabled for baseline
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
        app.logger.error(f"Validation error in generate_braille_stl: {e}")
        return jsonify({'error': 'Invalid request data'}), 400
    
    # Character limit validation is now done on frontend after braille translation
    # Backend expects lines to already be within limits
    
    try:
        allow_blob_cache = (plate_type == 'negative')
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
                early_public = _build_blob_public_url(early_cache_key)
                if _blob_check_exists(early_public):
                    app.logger.info(f"BLOB CACHE EARLY HIT (counter plate) key={early_cache_key}")
                    resp = redirect(early_public, code=302)
                    resp.headers['X-Blob-Cache-Key'] = early_cache_key
                    resp.headers['X-Blob-URL'] = early_public
                    resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
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
                    print("DEBUG: Generating counter plate with bowl (spherical cap) recesses (all positions)")
                    mesh = build_counter_plate_bowl(settings)
                elif recess_shape == 0:
                    print("DEBUG: Generating counter plate with hemispherical recesses (all positions)")
                    mesh = build_counter_plate_hemispheres(settings)
                elif recess_shape == 2:
                    print("DEBUG: Generating counter plate with conical (frustum) recesses (all positions)")
                    mesh = build_counter_plate_cone(settings)
                else:
                    print("WARNING: Unknown recess_shape value, defaulting to bowl")
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
            cached_public = _build_blob_public_url(cache_key)
            if _blob_check_exists(cached_public):
                app.logger.info(f"BLOB CACHE HIT (pre-export) key={cache_key}")
                resp = redirect(cached_public, code=302)
                resp.headers['X-Blob-Cache-Key'] = cache_key
                resp.headers['X-Blob-URL'] = cached_public
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
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
        config_dump = {
            "timestamp": datetime.now().isoformat(),
            "plate_type": plate_type,
            "shape_type": shape_type,
            "grade": grade if plate_type == 'positive' else "n/a",
            "text_lines": lines if plate_type == 'positive' else ["Counter plate - all positions"],
            "cylinder_params": cylinder_params if shape_type == 'cylinder' else "n/a",
            "per_line_language_tables": per_line_language_tables if per_line_language_tables else "n/a",
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
                "hemisphere_subdivisions": settings.hemisphere_subdivisions if plate_type == 'negative' else "n/a",
                "cone_segments": settings.cone_segments if plate_type == 'negative' else "n/a",
                "hemi_counter_dot_base_diameter": getattr(settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 'n/a')) if plate_type == 'negative' else "n/a",
                "bowl_counter_dot_base_diameter": getattr(settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 'n/a')) if plate_type == 'negative' else "n/a",
                "use_bowl_recess": int(getattr(settings, 'use_bowl_recess', 0)) if plate_type == 'negative' else "n/a",
                "counter_dot_depth": float(getattr(settings, 'counter_dot_depth', 0.6)) if (plate_type == 'negative' and int(getattr(settings, 'use_bowl_recess', 0)) == 1) else ("n/a" if plate_type != 'negative' else 0.0)
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
            # For counter plates, include actual counter base diameter in filename
            try:
                if int(getattr(settings, 'use_bowl_recess', 0)) == 1:
                    total_diameter = float(getattr(settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
                else:
                    total_diameter = float(getattr(settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
            except Exception:
                total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
            filename = f'braille_counter_plate_{total_diameter}mm-{shape_type}'
        
        # Additional filename sanitization for security
        filename = re.sub(r'[^\w\-_]', '', filename)[:60]  # Allow longer names to accommodate shape type
        
        # Attempt to persist to Blob store and redirect if successful (only for card counter plates)
        if allow_blob_cache:
            public_url = _blob_upload(cache_key, stl_bytes)
            if public_url:
                app.logger.info(f"BLOB CACHE MISS -> UPLOAD OK key={cache_key}")
                resp = redirect(public_url, code=302)
                resp.headers['ETag'] = etag
                resp.headers['X-Blob-Cache-Key'] = cache_key
                resp.headers['X-Blob-URL'] = public_url
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                resp.headers['X-Blob-Cache'] = 'miss'
                resp.headers['X-Blob-Cache-Reason'] = 'uploaded-now'
                return resp

        # Build response with headers
        resp = make_response(send_file(io.BytesIO(stl_bytes), mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl'))
        resp.headers['ETag'] = etag
        resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
        resp.headers['X-Blob-Cache'] = 'miss' if allow_blob_cache else 'bypass'
        resp.headers['X-Blob-Cache-Reason'] = 'no-upload-url' if allow_blob_cache else 'embossing-disabled'
        resp.headers['X-Blob-Cache-Key'] = cache_key
        resp.headers['X-Blob-URL'] = _build_blob_public_url(cache_key)
        return resp
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate STL: {str(e)}'}), 500

@app.route('/generate_counter_plate_stl', methods=['POST'])
# @limiter.limit("10 per minute")  # disabled for baseline
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
                app.logger.info(f"BLOB CACHE EARLY HIT (counter plate standalone) key={early_cache_key}")
                resp = redirect(early_public, code=302)
                resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                resp.headers['X-Blob-Cache'] = 'hit'
                resp.headers['X-Blob-Cache-Reason'] = 'early-exists'
                return resp
        except Exception:
            pass

        # Counter plate: choose recess shape
        # It does NOT depend on text input - always creates ALL 6 dots per cell
        recess_shape = int(getattr(settings, 'recess_shape', 1))
        if recess_shape == 1:
            print("DEBUG: Generating counter plate with bowl (spherical cap) recesses (all positions)")
            mesh = build_counter_plate_bowl(settings)
        elif recess_shape == 0:
            print("DEBUG: Generating counter plate with hemispherical recesses (all positions)")
            mesh = build_counter_plate_hemispheres(settings)
        elif recess_shape == 2:
            print("DEBUG: Generating counter plate with conical (frustum) recesses (all positions)")
            mesh = build_counter_plate_cone(settings)
        else:
            print(f"WARNING: Unknown recess_shape={recess_shape}, defaulting to hemisphere")
            mesh = build_counter_plate_hemispheres(settings)
        
        # Compute content-addressable cache key from request payload
        cache_payload = {
            'plate_type': 'negative',
            'settings': _normalize_settings_for_cache(settings),
            'shape_type': 'card',
        }
        cache_key = compute_cache_key(cache_payload)

        # If a public base is configured and the blob already exists, redirect
        cached_public = _build_blob_public_url(cache_key)
        if _blob_check_exists(cached_public):
            app.logger.info(f"BLOB CACHE HIT (pre-export standalone) key={cache_key}")
            resp = redirect(cached_public, code=302)
            resp.headers['X-Blob-Cache-Key'] = cache_key
            resp.headers['X-Blob-URL'] = cached_public
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
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
                total_diameter = float(getattr(settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
            elif recess_shape == 2:  # Cone
                total_diameter = float(getattr(settings, 'cone_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
            else:  # Hemisphere (recess_shape == 0)
                total_diameter = float(getattr(settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter')))
        except Exception:
            total_diameter = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        filename = f"braille_counter_plate_{total_diameter}mm"
        # Attempt to persist to Blob store and redirect if successful
        public_url = _blob_upload(cache_key, stl_bytes)
        if public_url and _blob_check_exists(public_url):
            app.logger.info(f"BLOB CACHE MISS -> UPLOAD OK (standalone) key={cache_key}")
            resp = redirect(public_url, code=302)
            resp.headers['ETag'] = etag
            resp.headers['X-Blob-Cache-Key'] = cache_key
            resp.headers['X-Blob-URL'] = public_url
            resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
            resp.headers['X-Blob-Cache'] = 'miss'
            resp.headers['X-Blob-Cache-Reason'] = 'uploaded-now'
            return resp

        # Build response with headers
        resp = make_response(send_file(io.BytesIO(stl_bytes), mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl'))
        resp.headers['ETag'] = etag
        resp.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
        resp.headers['X-Blob-Cache'] = 'miss'
        resp.headers['X-Blob-Cache-Reason'] = 'no-upload-url'
        return resp
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate counter plate: {str(e)}'}), 500


if __name__ == '__main__':
    
    app.run(debug=True, port=5001)

# For Vercel deployment - DISABLED for baseline
# app.debug = False