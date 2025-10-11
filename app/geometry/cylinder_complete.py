"""
Cylinder geometry generation.

This module handles generation of cylindrical braille surfaces, including
shell creation, dot mapping, and recess operations.

Dependencies:
- trimesh for 3D mesh operations
- numpy for mathematical operations  
- shapely for 2D polygon operations
- app.models.CardSettings for settings
- app.geometry.dot_shapes.create_braille_dot for dot creation
- app.utils.braille_to_dots for braille conversion
- _build_character_polygon from backend.py (will be migrated in next batch)
"""

import json
from datetime import datetime

import numpy as np
import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from trimesh.creation import extrude_polygon

# Note: These imports will need to be adjusted based on where functions are located
# For now, assuming they will be imported when this module is used


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


def layout_cylindrical_cells(braille_lines, settings, cylinder_diameter_mm: float, cylinder_height_mm: float):
    """
    Calculate positions for braille cells on a cylinder surface.
    Returns a list of (braille_char, x_theta, y_z) tuples where:
    - x_theta is the position along the circumference (will be converted to angle)
    - y_z is the vertical position on the cylinder

    Note: Requires CardSettings to be imported where this is used.
    """
    cells = []
    radius = cylinder_diameter_mm / 2

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
            angle = start_angle + (
                (col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)) * cell_spacing_angle
            )
            x_pos = angle * radius  # Convert to arc length for compatibility
            cells.append((braille_char, x_pos, y_pos))

    return cells, cells_per_row

