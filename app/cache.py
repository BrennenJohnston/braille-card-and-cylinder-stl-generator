"""
Caching utilities for STL generation.

This module handles blob storage caching (Vercel Blob) and Redis-based
cache key mapping.
"""

import hashlib
import json
import os

# Conditional imports for deployment environments
try:
    import redis as _redis_mod
except ImportError:
    _redis_mod = None

try:
    import requests
except ImportError:
    requests = None

# Global Redis client singleton
_redis_client_singleton = None


def _get_redis_client():
    """Get or create Redis client singleton."""
    global _redis_client_singleton
    if _redis_client_singleton is not None:
        return _redis_client_singleton
    if _redis_mod is None:
        return None
    try:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            return None
        # from_url handles rediss:// and ssl automatically
        _redis_client_singleton = _redis_mod.from_url(redis_url, decode_responses=True)
        return _redis_client_singleton
    except Exception:
        return None


def _blob_url_cache_get(cache_key: str) -> str:
    """Get cached blob URL from Redis."""
    try:
        r = _get_redis_client()
        if not r:
            return ''
        return r.get(f'blob-url:{cache_key}') or ''
    except Exception:
        return ''


def _blob_url_cache_set(cache_key: str, url: str) -> None:
    """Set cached blob URL in Redis with TTL."""
    try:
        r = _get_redis_client()
        if not r:
            return
        ttl = int(os.environ.get('BLOB_URL_TTL_SEC', '31536000'))
        r.setex(f'blob-url:{cache_key}', ttl, url)
    except Exception:
        return


def _canonical_json(obj):
    """Convert object to canonical JSON string for stable hashing."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(',', ':'))
    except Exception:
        return str(obj)


def compute_cache_key(payload: dict) -> str:
    """Compute a stable SHA-256 key from request payload for content-addressable caching."""
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


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
        'hemi_counter_dot_base_diameter': getattr(
            settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', None)
        ),
        'bowl_counter_dot_base_diameter': getattr(
            settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', None)
        ),
        'counter_dot_depth': getattr(settings, 'counter_dot_depth', None),
        'cone_counter_dot_base_diameter': getattr(
            settings, 'cone_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', None)
        ),
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
    """Normalize cylinder parameters for cache key generation."""
    if not isinstance(cylinder_params, dict):
        return {}
    keys = ['diameter_mm', 'height_mm', 'polygonal_cutout_radius_mm', 'polygonal_cutout_sides', 'seam_offset_deg']
    out = {}
    for k in keys:
        out[k] = _normalize_number(cylinder_params.get(k))
    return out


def _blob_public_base_url() -> str:
    """Get the public base URL for blob storage."""
    # Public base like: https://<store>.public.blob.vercel-storage.com
    return os.environ.get('BLOB_PUBLIC_BASE_URL') or ''


def _build_blob_public_url(cache_key: str) -> str:
    """Build the public URL for a blob given its cache key."""
    base = _blob_public_base_url().rstrip('/')
    if not base:
        return ''
    # namespace STLs under /stl/
    return f'{base}/stl/{cache_key}.stl'


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
        headers = {'Range': 'bytes=0-0'}
        resp = requests.get(public_url, headers=headers, timeout=6, stream=True, allow_redirects=True)
        try:
            resp.close()
        except Exception:
            pass
        return resp.status_code in (200, 206)
    except Exception:
        return False


def _blob_upload(cache_key: str, stl_bytes: bytes, logger=None) -> str:
    """Upload STL to Vercel Blob via REST if configured. Returns public URL or empty string."""
    if requests is None:
        return ''
    # Support both token names
    token = os.environ.get('BLOB_STORE_WRITE_TOKEN') or os.environ.get('BLOB_READ_WRITE_TOKEN')
    if not token:
        return ''
    # Use filename path to group under /stl/
    pathname = f'stl/{cache_key}.stl'
    # First, try deterministic PUT to the exact pathname (no suffix)
    try:
        direct_base = os.environ.get('BLOB_DIRECT_UPLOAD_URL', 'https://blob.vercel-storage.com')
        put_url = f'{direct_base.rstrip("/")}/{pathname}'
        headers = {
            'Authorization': f'Bearer {token}',
            'x-vercel-blob-access': 'public',
            'x-vercel-blobs-access': 'public',
            'x-vercel-blob-add-random-suffix': '0',
            'x-vercel-blobs-add-random-suffix': '0',
            'content-type': 'application/octet-stream',
        }
        store_id = os.environ.get('BLOB_STORE_ID')
        if store_id:
            headers['x-vercel-store-id'] = store_id
        max_age = os.environ.get('BLOB_CACHE_MAX_AGE')
        if max_age:
            headers['x-vercel-cache-control-max-age'] = str(max_age)
        resp = requests.put(put_url, data=stl_bytes, headers=headers, timeout=30)
        if 200 <= resp.status_code < 300 or resp.status_code == 409:
            # Prefer URL returned by API if present
            try:
                j = resp.json()
                url_from_api = j.get('url') or ''
                if url_from_api:
                    if logger:
                        logger.info(f'Blob direct upload OK; using API URL for key={cache_key}')
                    return url_from_api
            except Exception:
                pass
            # Fallback to constructed public URL
            public_url = _build_blob_public_url(cache_key)
            if public_url:
                if logger:
                    logger.info(f'Blob direct upload OK; using constructed public URL for key={cache_key}')
                return public_url
        else:
            try:
                if logger:
                    logger.warning(f'Blob direct upload failed status={resp.status_code} body={resp.text}')
            except Exception:
                if logger:
                    logger.warning(f'Blob direct upload failed status={resp.status_code}')
    except Exception as e:
        if logger:
            logger.warning(f'Blob direct upload exception for key={cache_key}: {e}')

    # Fallback: POST to root with x-vercel-filename (let service route it)
    try:
        post_url = os.environ.get('BLOB_DIRECT_UPLOAD_URL', 'https://blob.vercel-storage.com').rstrip('/')
        headers = {
            'Authorization': f'Bearer {token}',
            'x-vercel-filename': pathname,
            'x-vercel-blob-access': 'public',
            'x-vercel-blobs-access': 'public',
            'x-vercel-blob-add-random-suffix': '0',
            'x-vercel-blobs-add-random-suffix': '0',
            'content-type': 'application/octet-stream',
        }
        store_id = os.environ.get('BLOB_STORE_ID')
        if store_id:
            headers['x-vercel-store-id'] = store_id
        resp = requests.post(post_url, data=stl_bytes, headers=headers, timeout=30)
        if 200 <= resp.status_code < 300 or resp.status_code == 409:
            try:
                j = resp.json()
                url_from_api = j.get('url') or ''
                if url_from_api:
                    return url_from_api
            except Exception:
                pass
            public_url = _build_blob_public_url(cache_key)
            return public_url
        return ''
    except Exception:
        return ''
