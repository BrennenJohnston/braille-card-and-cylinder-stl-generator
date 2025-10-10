"""
STL export utilities.

This module handles conversion of trimesh objects to STL bytes with
appropriate headers for HTTP responses.
"""

import io
from typing import Optional

import trimesh


def mesh_to_stl_bytes(mesh: trimesh.Trimesh) -> bytes:
    """
    Export a trimesh object to STL bytes.

    Args:
        mesh: Trimesh object to export

    Returns:
        Binary STL data
    """
    stl_io = io.BytesIO()
    mesh.export(stl_io, file_type='stl')
    stl_io.seek(0)
    return stl_io.getvalue()


def create_stl_headers(filename: Optional[str] = None, etag: Optional[str] = None) -> dict:
    """
    Create appropriate HTTP headers for STL file response.

    Args:
        filename: Optional filename for Content-Disposition
        etag: Optional ETag for caching

    Returns:
        Dictionary of headers
    """
    headers = {'Content-Type': 'application/sla', 'Cache-Control': 'no-cache'}

    if filename:
        headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    if etag:
        headers['ETag'] = etag

    return headers
