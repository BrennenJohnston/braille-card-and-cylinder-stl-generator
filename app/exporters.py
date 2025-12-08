"""
STL export utilities.

This module handles conversion of trimesh objects to STL bytes with
appropriate headers for HTTP responses.
"""

import hashlib
import io
import time

import trimesh
from flask import Response, make_response, send_file


def mesh_to_stl_bytes(mesh: trimesh.Trimesh) -> tuple[bytes, int]:
    """
    Export a trimesh object to STL bytes with timing.

    Args:
        mesh: Trimesh object to export

    Returns:
        Tuple of (binary STL data, export time in milliseconds)
    """
    t0 = time.time()
    stl_io = io.BytesIO()
    mesh.export(stl_io, file_type='stl')
    stl_io.seek(0)
    stl_bytes = stl_io.getvalue()
    compute_ms = int((time.time() - t0) * 1000)
    return stl_bytes, compute_ms


def compute_etag(stl_bytes: bytes) -> str:
    """
    Compute ETag hash for STL bytes.

    Args:
        stl_bytes: Binary STL data

    Returns:
        SHA-256 hash as ETag
    """
    return hashlib.sha256(stl_bytes).hexdigest()


def create_stl_response(
    stl_bytes: bytes,
    filename: str,
    etag: str | None = None,
    cache_control: str = 'public, max-age=3600, stale-while-revalidate=86400',
    extra_headers: dict | None = None,
) -> Response:
    """
    Create Flask response for STL file download.

    Args:
        stl_bytes: Binary STL data
        filename: Download filename (without .stl extension)
        etag: Optional ETag for caching
        cache_control: Cache-Control header value
        extra_headers: Optional additional headers

    Returns:
        Flask Response object
    """
    resp = make_response(
        send_file(io.BytesIO(stl_bytes), mimetype='model/stl', as_attachment=True, download_name=f'{filename}.stl')
    )

    if etag:
        resp.headers['ETag'] = etag

    resp.headers['Cache-Control'] = cache_control

    if extra_headers:
        for key, value in extra_headers.items():
            resp.headers[key] = value

    return resp


def create_304_response(etag: str, cache_control: str = 'public, max-age=3600', extra_headers: dict | None = None):
    """
    Create 304 Not Modified response for conditional requests.

    Args:
        etag: ETag to include in response
        cache_control: Cache-Control header
        extra_headers: Optional additional headers

    Returns:
        Flask Response with 304 status
    """
    resp = make_response('', 304)
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = cache_control

    if extra_headers:
        for key, value in extra_headers.items():
            resp.headers[key] = value

    return resp


def should_return_304(request_headers: dict, etag: str) -> bool:
    """
    Check if request has matching ETag for 304 response.

    Args:
        request_headers: Flask request.headers
        etag: Current ETag

    Returns:
        True if should return 304 Not Modified
    """
    client_etag = request_headers.get('If-None-Match')
    return client_etag is not None and client_etag == etag
