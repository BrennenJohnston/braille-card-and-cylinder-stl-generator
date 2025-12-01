"""
Cylinder geometry generation.

This module handles generation of cylindrical braille surfaces, including
shell creation, dot mapping, and recess operations.
"""

from __future__ import annotations

import os as _os
from typing import TYPE_CHECKING

import numpy as np
import trimesh
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from trimesh.creation import extrude_polygon

from app.geometry.booleans import batch_union, has_boolean_backend, mesh_difference, mesh_union
from app.geometry.dot_shapes import create_braille_dot
from app.utils import allow_serverless_booleans, braille_to_dots, get_logger

if TYPE_CHECKING:
    from app.models import CardSettings

# Configure logging for this module
logger = get_logger(__name__)


def _build_character_polygon_proxy(char_upper: str, target_width: float, target_height: float):
    """Lazy import helper to avoid circular dependency on backend module."""
    from app.geometry.braille_layout import _build_character_polygon

    return _build_character_polygon(char_upper, target_width, target_height)


def _is_serverless_env() -> bool:
    """Detect serverless runtimes (e.g., Vercel/Lambda)."""
    try:
        return bool(
            _os.environ.get('VERCEL') or _os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or _os.environ.get('NOW_REGION')
        )
    except Exception:
        return False


def _booleans_enabled() -> bool:
    """Feature flag to enable/disable 3D boolean operations at runtime."""
    try:
        val = _os.environ.get('ENABLE_3D_BOOLEANS', '1')
        return str(val).lower() not in ('0', 'false', 'no')
    except Exception:
        return True


def _booleans_available() -> bool:
    """Return True when boolean operations are enabled and a backend is actually available."""
    if not _booleans_enabled():
        logger.debug('Booleans disabled via ENABLE_3D_BOOLEANS env var')
        return False

    # Check if we actually have a working boolean backend (manifold3d)
    # Trimesh's default engine requires blender/openscad which aren't on serverless
    if not has_boolean_backend():
        logger.debug('No boolean backend available (manifold3d not installed) - using 2D approach')
        return False

    if not _is_serverless_env():
        logger.debug('Booleans available (not serverless environment, manifold3d installed)')
        return True

    result = allow_serverless_booleans()
    if result:
        logger.debug('Booleans available in serverless (manifold3d installed and allowed)')
    else:
        logger.debug('Booleans disabled in serverless (ALLOW_SERVERLESS_BOOLEANS not set)')
    return result


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

    Note: settings is a CardSettings object.
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
    braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
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


def create_cylinder_shell(
    diameter_mm, height_mm, polygonal_cutout_radius_mm, polygonal_cutout_sides=12, align_vertex_theta_rad=None
):
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

    # If no cutout is specified, return a solid cylinder mesh
    if polygonal_cutout_radius_mm <= 0:
        return trimesh.creation.cylinder(radius=outer_radius, height=height_mm, sections=96)

    # Build 2D cross-section using Shapely: circle minus N-gon, then extrude once (serverless-friendly)
    try:
        # High-resolution circular boundary for smooth outer wall
        outer_circle = ShapelyPoint(0.0, 0.0).buffer(outer_radius, resolution=128)

        # Regular N-gon from inscribed radius
        polygonal_cutout_sides = max(3, int(polygonal_cutout_sides))
        circumscribed_radius = polygonal_cutout_radius_mm / np.cos(np.pi / polygonal_cutout_sides)
        angles = np.linspace(0.0, 2.0 * np.pi, polygonal_cutout_sides, endpoint=False)
        vertices_2d = [(circumscribed_radius * np.cos(a), circumscribed_radius * np.sin(a)) for a in angles]
        inner_ngon = ShapelyPolygon(vertices_2d)

        if align_vertex_theta_rad is not None:
            from shapely import affinity as _affinity

            inner_ngon = _affinity.rotate(inner_ngon, align_vertex_theta_rad * 180.0 / np.pi, origin=(0.0, 0.0))

        # Ring shape: outer minus inner polygon
        ring_shape = outer_circle.difference(inner_ngon)
        if ring_shape.is_empty:
            logger.warning('Cylinder cross-section difference produced empty geometry; falling back to solid')
            return trimesh.creation.cylinder(radius=outer_radius, height=height_mm, sections=96)

        # Extrude to 3D shell
        shell = extrude_polygon(ring_shape, height=height_mm)
        # Center along Z to match other geometry conventions ([-H/2, +H/2])
        shell.apply_translation([0.0, 0.0, -height_mm / 2.0])
        return shell
    except Exception as e:
        logger.warning(f'2D extrusion for cylinder shell failed: {e}')
        # Fallback to solid cylinder to avoid 500s
        return trimesh.creation.cylinder(radius=outer_radius, height=height_mm, sections=96)


def create_cylinder_triangle_marker(
    x_arc,
    y_local,
    settings: CardSettings,
    cylinder_diameter_mm,
    seam_offset_deg=0,
    height_mm=0.6,
    for_subtraction=True,
    point_left=False,
):
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
    r_hat, t_hat, z_hat, radius, circumference, theta = _compute_cylinder_frame(
        x_arc, cylinder_diameter_mm, seam_offset_deg
    )

    # Triangle dimensions - standard guide triangle shape
    2.0 * settings.dot_spacing  # Vertical extent
    triangle_width = settings.dot_spacing  # Horizontal extent (pointing right in tangent direction)

    # Build 2D triangle in local tangent (X=t) and vertical (Y=z) plane
    # Vertices: base on left, apex pointing right

    if point_left:
        # Mirror along vertical axis so apex points left (negative tangent)
        tri_2d = ShapelyPolygon(
            [
                (0.0, -settings.dot_spacing),  # Bottom of base (right side)
                (0.0, settings.dot_spacing),  # Top of base (right side)
                (-triangle_width, 0.0),  # Apex (pointing left)
            ]
        )
    else:
        tri_2d = ShapelyPolygon(
            [
                (0.0, -settings.dot_spacing),  # Bottom of base
                (0.0, settings.dot_spacing),  # Top of base
                (triangle_width, 0.0),  # Apex (pointing right/tangentially)
            ]
        )

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
        T[:3, 0] = t_hat  # X axis (tangential)
        T[:3, 1] = z_hat  # Y axis (vertical)
        T[:3, 2] = r_hat  # Z axis (radial outward)

        # Position so the prism starts outside the cylinder and cuts inward
        # The prism's Z=0 should be at radius (cylinder surface)
        center_pos = r_hat * radius + z_hat * y_local
        T[:3, 3] = center_pos

        # Apply the transform
        tri_prism_local.apply_transform(T)

        # Debug output - only print for first triangle to avoid spam
        if abs(y_local) < settings.line_spacing:  # First row
            logger.debug(f'Triangle at theta={np.degrees(theta):.1f}°, y_local={y_local:.1f}mm')
            logger.debug(f'Triangle bounds after transform: {tri_prism_local.bounds}')
            logger.debug(f'Cylinder radius: {radius}mm')
    else:
        # For extruded triangle (outward from cylinder surface)
        tri_prism_local = trimesh.creation.extrude_polygon(tri_2d, height=height_mm)

        # Build transform for outward extrusion
        T = np.eye(4)
        T[:3, 0] = t_hat  # X axis (tangential)
        T[:3, 1] = z_hat  # Y axis (vertical)
        T[:3, 2] = r_hat  # Z axis (radial outward)

        # Slightly embed the triangle into the cylinder so union attaches robustly
        embed = max(getattr(settings, 'epsilon', 0.001), 0.05)
        # Place the base of the prism just inside the surface (radius - embed), extruding outward
        center_pos = r_hat * (radius - embed) + z_hat * y_local
        T[:3, 3] = center_pos

        tri_prism_local.apply_transform(T)

    return tri_prism_local


def create_cylinder_line_end_marker(
    x_arc,
    y_local,
    settings: CardSettings,
    cylinder_diameter_mm,
    seam_offset_deg=0,
    height_mm=0.5,
    for_subtraction=True,
):
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
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])  # radial outward
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])  # tangential
    z_hat = np.array([0.0, 0.0, 1.0])  # cylinder axis

    # Line dimensions - vertical line at end of row
    2.0 * settings.dot_spacing  # Vertical extent (same as cell height)
    line_width = settings.dot_spacing  # Horizontal extent in tangent direction

    # Build 2D rectangle in local tangent (X=t) and vertical (Y=z) plane
    # Rectangle centered at origin, extending in both directions

    line_2d = ShapelyPolygon(
        [
            (-line_width / 2, -settings.dot_spacing),  # Bottom left
            (line_width / 2, -settings.dot_spacing),  # Bottom right
            (line_width / 2, settings.dot_spacing),  # Top right
            (-line_width / 2, settings.dot_spacing),  # Top left
        ]
    )

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
        T[:3, 0] = t_hat  # X axis (tangential)
        T[:3, 1] = z_hat  # Y axis (vertical)
        T[:3, 2] = r_hat  # Z axis (radial outward)

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
        T[:3, 0] = t_hat  # X axis
        T[:3, 1] = z_hat  # Y axis
        T[:3, 2] = -r_hat  # Z axis (inward)

        # Position recessed into surface
        center_pos = r_hat * (radius - height_mm / 2.0) + z_hat * y_local
        T[:3, 3] = center_pos

        line_prism_local.apply_transform(T)

    return line_prism_local


def create_cylinder_character_shape(
    character,
    x_arc,
    y_local,
    settings: CardSettings,
    cylinder_diameter_mm,
    seam_offset_deg=0,
    height_mm=1.0,
    for_subtraction=True,
):
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
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])  # radial outward
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])  # tangential
    z_hat = np.array([0.0, 0.0, 1.0])  # cylinder axis

    # Define character size based on braille cell dimensions (scaled 56.25% bigger than original)
    char_height = 2 * settings.dot_spacing + 4.375  # 9.375mm for default 2.5mm dot spacing
    char_width = settings.dot_spacing * 0.8 + 2.6875  # 4.6875mm for default 2.5mm dot spacing

    # Get the character definition
    char_upper = character.upper()
    if not (char_upper.isalpha() or char_upper.isdigit()):
        # Fall back to rectangle for undefined characters
        return create_cylinder_line_end_marker(
            x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction
        )

    try:
        # Build character polygon using shared helper
        char_2d = _build_character_polygon_proxy(char_upper, char_width, char_height)
        if char_2d is None:
            return create_cylinder_line_end_marker(
                x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction
            )

    except Exception as e:
        logger.warning(f'Failed to create character shape using matplotlib: {e}')
        logger.info('Falling back to rectangle marker')
        return create_cylinder_line_end_marker(
            x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction
        )

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
                    logger.warning('Character mesh is not a valid volume')
                    return create_cylinder_line_end_marker(
                        x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction
                    )

            # The prism is created with Z from 0 to extrude_height
            # We need to center it so it extends from -0.5 to (height_mm + 0.5)
            char_prism_local.apply_translation([0, 0, -0.5])

            # Build transform: map local coords to cylinder coords
            T = np.eye(4)
            T[:3, 0] = t_hat  # X axis (tangential)
            T[:3, 1] = z_hat  # Y axis (vertical)
            T[:3, 2] = r_hat  # Z axis (radial outward)

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
            T[:3, 0] = t_hat  # X axis
            T[:3, 1] = z_hat  # Y axis
            T[:3, 2] = -r_hat  # Z axis (inward)

            # Position recessed into surface
            center_pos = r_hat * (radius - height_mm / 2.0) + z_hat * y_local
            T[:3, 3] = center_pos

            char_prism_local.apply_transform(T)
    except Exception as e:
        logger.warning(f'Failed to extrude character shape: {e}')
        return create_cylinder_line_end_marker(
            x_arc, y_local, settings, cylinder_diameter_mm, seam_offset_deg, height_mm, for_subtraction
        )

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


def generate_cylinder_stl(lines, grade='g1', settings=None, cylinder_params=None, original_lines=None):
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
        from app.models import CardSettings

        settings = CardSettings()

    if cylinder_params is None:
        cylinder_params = {
            'diameter_mm': 31.35,
            'height_mm': settings.card_height,
            'polygonal_cutout_radius_mm': 13,
            'polygonal_cutout_sides': 12,
            'seam_offset_deg': 355,
        }

    diameter = float(cylinder_params.get('diameter_mm', 31.35))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 355))

    logger.info(
        f'Creating cylinder mesh - Diameter: {diameter}mm, Height: {height}mm, Cutout Radius: {polygonal_cutout_radius}mm'
    )

    # Print grid and angular spacing information
    radius = diameter / 2
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_angle_deg = np.degrees(grid_width / radius)
    cell_spacing_angle_deg = np.degrees(settings.cell_spacing / radius)
    dot_spacing_angle_deg = np.degrees(settings.dot_spacing / radius)

    logger.info('Grid configuration:')
    logger.info(f'  - Grid: {settings.grid_columns} columns × {settings.grid_rows} rows')
    logger.info(f'  - Grid width: {grid_width:.1f}mm → {grid_angle_deg:.1f}° arc on cylinder')
    logger.info('Angular spacing calculations:')
    logger.info(f'  - Cell spacing: {settings.cell_spacing}mm → {cell_spacing_angle_deg:.2f}° on cylinder')
    logger.info(f'  - Dot spacing: {settings.dot_spacing}mm → {dot_spacing_angle_deg:.2f}° on cylinder')

    # Compute triangle column absolute angle (including seam) to align polygon cutout vertex
    seam_offset_rad = np.radians(seam_offset)
    grid_angle = grid_width / radius
    start_angle = -grid_angle / 2
    triangle_angle = start_angle + ((settings.grid_columns - 1) * settings.cell_spacing / radius)
    cutout_align_theta = triangle_angle + seam_offset_rad

    # Create cylinder shell with polygon cutout aligned to triangle marker column
    cylinder_shell = create_cylinder_shell(
        diameter, height, polygonal_cutout_radius, polygonal_cutout_sides, align_vertex_theta_rad=cutout_align_theta
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
                            first_char,
                            text_number_x,
                            y_local,
                            settings,
                            diameter,
                            seam_offset,
                            height_mm=1.0,
                            for_subtraction=True,
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
    logger.debug(
        f'Creating {len(text_number_meshes)} text/number recesses and {len(triangle_meshes)} triangle recesses on emboss cylinder'
    )

    # Combine all markers (text/number indicators and triangles) for efficient boolean operations
    all_markers = (text_number_meshes + triangle_meshes) if getattr(settings, 'indicator_shapes', 1) else []

    markers_applied = False
    if all_markers and _booleans_available():
        try:
            # Union all markers first
            union_markers = mesh_union(all_markers)

            logger.debug('Marker union successful, subtracting from cylinder shell...')
            # Subtract from shell to recess (serverless-compatible)
            cylinder_shell = mesh_difference([cylinder_shell, union_markers])
            logger.debug('Marker subtraction successful')
            markers_applied = True
        except Exception as e:
            logger.error(f'Union approach failed for marker cutouts: {e}')

    # If union approach failed or we're in serverless, try individual subtraction
    if all_markers and not markers_applied and _booleans_available():
        try:
            logger.debug('Attempting individual marker subtraction...')
            for i, marker in enumerate(all_markers):
                try:
                    cylinder_shell = mesh_difference([cylinder_shell, marker])
                except Exception as marker_err:
                    logger.warning(f'Failed to subtract marker {i + 1}: {marker_err}')
                    continue
            markers_applied = True
            logger.debug('Individual marker subtraction completed')
        except Exception as e:
            logger.error(f'Individual marker subtraction failed: {e}')

    # If all 3D approaches failed, create markers using 2D cross-section approach
    # This approach creates horizontal slices with inward notches at marker positions
    if all_markers and not markers_applied:
        logger.warning(
            '3D marker subtraction failed. Using 2D slicing approach for indicator recesses on outer surface.'
        )
        try:
            # Collect all marker positions: (z_local, angle, angular_half_width, marker_height)
            marker_positions = []
            recess_depth = 0.6  # How deep the notches go into the surface
            marker_vertical_extent = settings.dot_spacing * 2  # Vertical extent of each marker

            for row_num in range(settings.grid_rows):
                y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
                z_local = y_pos - (height / 2.0)

                # First column (text/number indicator) - wider for character shape
                first_angle = start_angle + seam_offset_rad
                indicator_angular_half_width = (settings.dot_spacing * 0.6) / radius
                marker_positions.append((z_local, first_angle, indicator_angular_half_width, marker_vertical_extent))

                # Last column (triangle marker)
                last_angle = (
                    start_angle + ((settings.grid_columns - 1) * settings.cell_spacing / radius) + seam_offset_rad
                )
                triangle_angular_half_width = (settings.dot_spacing * 0.6) / radius
                marker_positions.append((z_local, last_angle, triangle_angular_half_width, marker_vertical_extent))

            # Create inner polygon for cutout (used in all slices)
            inner_polygon = None
            if polygonal_cutout_radius > 0:
                circumscribed_radius = polygonal_cutout_radius / np.cos(np.pi / polygonal_cutout_sides)
                angles_poly = np.linspace(0, 2 * np.pi, polygonal_cutout_sides, endpoint=False)
                vertices_2d = [
                    (
                        circumscribed_radius * np.cos(a + cutout_align_theta),
                        circumscribed_radius * np.sin(a + cutout_align_theta),
                    )
                    for a in angles_poly
                ]
                inner_polygon = ShapelyPolygon(vertices_2d)

            # Helper function to create cross-section with notches at specific angles
            def create_ring_with_notches(notch_angles, notch_half_widths, outer_r, notch_depth_val, resolution=128):
                """Create a ring cross-section with inward notches at specified angles."""
                angles = np.linspace(0, 2 * np.pi, resolution, endpoint=False)
                vertices = []
                for a in angles:
                    # Check if this angle is within any notch
                    r = outer_r
                    for notch_angle, half_width in zip(notch_angles, notch_half_widths, strict=False):
                        # Handle wraparound at 2π
                        angle_diff = abs((a - notch_angle + np.pi) % (2 * np.pi) - np.pi)
                        if angle_diff < half_width:
                            r = outer_r - notch_depth_val
                            break
                    vertices.append((r * np.cos(a), r * np.sin(a)))
                outer_shape = ShapelyPolygon(vertices)
                if inner_polygon is not None and not inner_polygon.is_empty:
                    return outer_shape.difference(inner_polygon)
                return outer_shape

            # Create normal ring (without notches) for non-marker sections
            outer_circle = ShapelyPoint(0, 0).buffer(radius, resolution=128)
            if inner_polygon is not None:
                ring_normal = outer_circle.difference(inner_polygon)
            else:
                ring_normal = outer_circle

            # Build cylinder as horizontal slices
            # Group markers by their Z position to create slices
            slices = []

            # Define Z bounds
            z_bottom = -height / 2.0
            z_top = height / 2.0

            # Collect Z ranges that need notched cross-sections
            notched_ranges = []  # (z_start, z_end, [(angle, half_width), ...])
            for z_local, angle, half_width, vert_extent in marker_positions:
                z_start = z_local - vert_extent / 2
                z_end = z_local + vert_extent / 2
                # Find or create a range for this Z
                found = False
                for i, (r_start, r_end, angle_list) in enumerate(notched_ranges):
                    # Check if overlaps with existing range
                    if not (z_end < r_start or z_start > r_end):
                        # Merge ranges
                        new_start = min(z_start, r_start)
                        new_end = max(z_end, r_end)
                        angle_list.append((angle, half_width))
                        notched_ranges[i] = (new_start, new_end, angle_list)
                        found = True
                        break
                if not found:
                    notched_ranges.append((z_start, z_end, [(angle, half_width)]))

            # Sort ranges by z_start
            notched_ranges.sort(key=lambda r: r[0])

            # Build slices: alternate between normal and notched sections
            current_z = z_bottom
            for range_start, range_end, angle_list in notched_ranges:
                # Normal section before this notched range
                if current_z < range_start:
                    slice_height = range_start - current_z
                    if slice_height > 0.01:  # Skip very thin slices
                        normal_slice = extrude_polygon(ring_normal, height=slice_height)
                        normal_slice.apply_translation([0, 0, current_z])
                        slices.append(normal_slice)
                    current_z = range_start

                # Notched section
                if current_z < range_end:
                    slice_height = range_end - current_z
                    if slice_height > 0.01:
                        notch_angles = [a for a, _ in angle_list]
                        notch_widths = [w for _, w in angle_list]
                        ring_notched = create_ring_with_notches(notch_angles, notch_widths, radius, recess_depth)
                        notched_slice = extrude_polygon(ring_notched, height=slice_height)
                        notched_slice.apply_translation([0, 0, current_z])
                        slices.append(notched_slice)
                    current_z = range_end

            # Final normal section after all notched ranges
            if current_z < z_top:
                slice_height = z_top - current_z
                if slice_height > 0.01:
                    normal_slice = extrude_polygon(ring_normal, height=slice_height)
                    normal_slice.apply_translation([0, 0, current_z])
                    slices.append(normal_slice)

            if slices:
                cylinder_shell = trimesh.util.concatenate(slices)
                logger.debug(f'2D slicing approach successful: created {len(slices)} slices for indicator recesses')

        except Exception as e2d:
            logger.error(f'2D slicing approach for indicator recesses failed: {e2d}')

    meshes = [cylinder_shell]

    # Check for overflow based on grid dimensions (accounting for reserved columns when indicators enabled)
    total_cells_needed = sum(len(line.strip()) for line in lines if line.strip())
    reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
    total_cells_available = (settings.grid_columns - reserved) * settings.grid_rows

    if total_cells_needed > total_cells_available:
        logger.warning(
            f'Text requires {total_cells_needed} cells but grid has {total_cells_available} cells ({settings.grid_columns - reserved}×{settings.grid_rows} after row markers)'
        )

    # Check if grid wraps too far around cylinder
    if grid_angle_deg > 360:
        logger.warning(f'Warning: Grid width ({grid_angle_deg:.1f}°) exceeds cylinder circumference (360°)')

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

    logger.info(f'Created cylinder with {len(meshes) - 1} braille dots')

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
            'seam_offset_deg': 355,
        }

    diameter = float(cylinder_params.get('diameter_mm', 31.35))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 355))

    logger.info(
        f'Creating cylinder counter plate - Diameter: {diameter}mm, Height: {height}mm, Cutout Radius: {polygonal_cutout_radius}mm'
    )

    # Use grid dimensions from settings (same as card)
    radius = diameter / 2
    np.pi * diameter

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
        diameter, height, polygonal_cutout_radius, polygonal_cutout_sides, align_vertex_theta_rad=cutout_align_theta
    )

    # Respect feature flag; use 2D approach when booleans are disabled or in serverless
    if not _booleans_available():
        logger.info('Using 2D approach for cylinder counter plate (booleans disabled or serverless environment)')
        return create_cylinder_counter_plate_2d(settings, cylinder_params)

    # Use grid_rows from settings

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
                triangle_x_first,
                y_local,
                settings,
                diameter,
                seam_offset,
                height_mm=0.5,
                for_subtraction=True,
                point_left=True,
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
                    base_d = float(
                        getattr(
                            settings,
                            'cone_counter_dot_base_diameter',
                            getattr(settings, 'counter_dot_base_diameter', 1.6),
                        )
                    )
                    hat_d = float(getattr(settings, 'cone_counter_dot_flat_hat', 0.4))
                    h_cone = float(getattr(settings, 'cone_counter_dot_height', 0.8))
                    base_r = max(settings.epsilon_mm, base_d / 2.0)
                    hat_r = max(settings.epsilon_mm, hat_d / 2.0)
                    # Ensure recess height exceeds radial overcut so it properly intersects the outer surface
                    radial_overcut = max(
                        settings.epsilon_mm, getattr(settings, 'cylinder_counter_plate_overcut_mm', 0.05)
                    )
                    h_cone = max(settings.epsilon_mm, h_cone + radial_overcut)
                    segments = 24
                    # Build local frustum along +Z with base at z=0 and bottom at z=-h_cone
                    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
                    top_ring = np.column_stack(
                        [base_r * np.cos(angles), base_r * np.sin(angles), np.zeros_like(angles)]
                    )
                    bot_ring = np.column_stack(
                        [hat_r * np.cos(angles), hat_r * np.sin(angles), -h_cone * np.ones_like(angles)]
                    )
                    vertices = np.vstack([top_ring, bot_ring, [[0, 0, 0]], [[0, 0, -h_cone]]])
                    top_center_index = 2 * segments
                    bot_center_index = 2 * segments + 1
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
                    use_bowl = recess_shape == 1
                    try:
                        if use_bowl:
                            counter_base = float(
                                getattr(settings, 'bowl_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                            )
                        else:
                            counter_base = float(
                                getattr(settings, 'hemi_counter_dot_base_diameter', settings.counter_dot_base_diameter)
                            )
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
                    sphere = trimesh.creation.icosphere(
                        subdivisions=settings.hemisphere_subdivisions, radius=sphere_radius
                    )
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

    logger.debug(f'Creating {len(sphere_meshes)} recess tools on cylinder counter plate (recess_shape={recess_shape})')

    if not sphere_meshes:
        logger.warning('No spheres were generated for cylinder counter plate. Returning base shell.')
        # The cylinder is already created with vertical axis (along Z)
        # No rotation needed - it should stand upright
        # Just ensure the base is at Z=0
        min_z = cylinder_shell.bounds[0][2]
        cylinder_shell.apply_translation([0, 0, -min_z])

        return cylinder_shell

    # Special-case: for cone frusta, prefer individual subtraction for robustness
    if recess_shape == 2 and sphere_meshes:
        try:
            logger.debug('Cylinder cone mode - subtracting frusta individually for robustness...')
            result_shell = cylinder_shell.copy()
            for i, tool in enumerate(sphere_meshes):
                try:
                    logger.debug(f'Cylinder subtract recess tool {i + 1}/{len(sphere_meshes)}')
                    result_shell = mesh_difference([result_shell, tool])
                except Exception as e_tool:
                    logger.warning(f'Cylinder cone subtraction failed for tool {i + 1}: {e_tool}')
                    continue
            for i, triangle in enumerate(triangle_meshes):
                try:
                    result_shell = mesh_difference([result_shell, triangle])
                except Exception as e_tri:
                    logger.warning(f'Cylinder triangle subtraction failed {i + 1}: {e_tri}')
                    continue
            for i, line_end in enumerate(line_end_meshes):
                try:
                    result_shell = mesh_difference([result_shell, line_end])
                except Exception as e_line:
                    logger.warning(f'Cylinder line-end subtraction failed {i + 1}: {e_line}')
                    continue
            if not result_shell.is_watertight:
                result_shell.fill_holes()
            min_z = result_shell.bounds[0][2]
            result_shell.apply_translation([0, 0, -min_z])
            logger.debug(f'Cylinder cone plate completed: {len(result_shell.vertices)} vertices')
            return result_shell
        except Exception as e_cyl_cone:
            logger.error(f'Cylinder cone individual subtraction failed: {e_cyl_cone}')
            # Fall through to robust boolean strategy below as a last attempt

    # More robust boolean strategy:
    # 1) Start with the cylinder shell (which already has the polygonal cutout)
    # 2) Subtract the union of all spheres and triangles to create outer recesses

    try:
        # Batch union to reduce complexity, then single subtract
        logger.debug('Cylinder boolean - batch union spheres...')
        union_spheres = batch_union(sphere_meshes, batch_size=64)

        union_triangles = None
        if triangle_meshes:
            logger.debug('Cylinder boolean - batch union triangles...')
            union_triangles = batch_union(triangle_meshes, batch_size=32)

        union_line_ends = None
        if line_end_meshes:
            logger.debug('Cylinder boolean - batch union line ends...')
            union_line_ends = batch_union(line_end_meshes, batch_size=32)

        cutouts_list = [union_spheres]
        if union_line_ends is not None:
            cutouts_list.append(union_line_ends)
        if union_triangles is not None:
            cutouts_list.append(union_triangles)

        all_cutouts = mesh_union(cutouts_list)

        logger.debug('Cylinder boolean - subtracting all cutouts from shell...')
        final_shell = mesh_difference([cylinder_shell, all_cutouts])

        if not final_shell.is_watertight:
            logger.debug('Cylinder final shell not watertight, attempting to fill holes...')
            final_shell.fill_holes()

        logger.debug(
            f'Cylinder counter plate completed: {len(final_shell.vertices)} vertices, {len(final_shell.faces)} faces'
        )

        min_z = final_shell.bounds[0][2]
        final_shell.apply_translation([0, 0, -min_z])
        return final_shell
    except Exception as e:
        logger.error(f'Cylinder robust boolean failed: {e}')

    # Fallback: subtract spheres individually from cylinder shell
    try:
        logger.debug('Fallback - individual subtraction from cylinder shell...')
        result_shell = cylinder_shell.copy()
        for i, sphere in enumerate(sphere_meshes):
            try:
                logger.debug(f'Subtracting sphere {i + 1}/{len(sphere_meshes)} from cylinder shell...')
                result_shell = mesh_difference([result_shell, sphere])
            except Exception as sphere_error:
                logger.warning(f'Failed to subtract sphere {i + 1}: {sphere_error}')
                continue

        # Subtract triangles individually (recess them)
        for i, triangle in enumerate(triangle_meshes):
            try:
                logger.debug(f'Subtracting triangle {i + 1}/{len(triangle_meshes)} from cylinder shell...')
                result_shell = mesh_difference([result_shell, triangle])
            except Exception as triangle_error:
                logger.warning(f'Failed to subtract triangle {i + 1}: {triangle_error}')
                continue

        # Subtract line end markers individually
        for i, line_end in enumerate(line_end_meshes):
            try:
                logger.debug(f'Subtracting line end marker {i + 1}/{len(line_end_meshes)} from cylinder shell...')
                result_shell = mesh_difference([result_shell, line_end])
            except Exception as line_error:
                logger.warning(f'Failed to subtract line end marker {i + 1}: {line_error}')
                continue

        final_shell = result_shell
        if not final_shell.is_watertight:
            final_shell.fill_holes()
        logger.debug(f'Fallback completed: {len(final_shell.vertices)} vertices, {len(final_shell.faces)} faces')

        # The cylinder is already created with vertical axis (along Z)
        # No rotation needed - it should stand upright
        # Just ensure the base is at Z=0
        min_z = final_shell.bounds[0][2]
        final_shell.apply_translation([0, 0, -min_z])

        return final_shell
    except Exception as final_error:
        logger.error(f'Cylinder fallback boolean failed: {final_error}')
        logger.warning('Using 2D approach for cylinder counter plate.')
        # Use 2D approach as final fallback
        return create_cylinder_counter_plate_2d(settings, cylinder_params)


def create_cylinder_counter_plate_2d(settings, cylinder_params=None):
    """
    Create a cylinder counter plate using 2D Shapely operations (serverless-compatible).

    This creates a cylinder with through-holes at all dot positions using 2D
    cross-section operations, which avoids 3D boolean operations entirely.

    Args:
        settings: CardSettings object
        cylinder_params: Dictionary with cylinder parameters

    Returns:
        Trimesh object representing the cylinder counter plate
    """
    from shapely.ops import unary_union as _unary_union

    if cylinder_params is None:
        cylinder_params = {
            'diameter_mm': 31.35,
            'height_mm': settings.card_height,
            'polygonal_cutout_radius_mm': 13,
            'polygonal_cutout_sides': 12,
            'seam_offset_deg': 355,
        }

    diameter = float(cylinder_params.get('diameter_mm', 31.35))
    height = float(cylinder_params.get('height_mm', settings.card_height))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 355))

    logger.info(f'Creating cylinder counter plate using 2D approach - Diameter: {diameter}mm, Height: {height}mm')

    radius = diameter / 2
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_angle = grid_width / radius
    start_angle = -grid_angle / 2
    cell_spacing_angle = settings.cell_spacing / radius
    seam_offset_rad = np.radians(seam_offset)

    # Calculate hole radius for dot recesses
    recess_shape = int(getattr(settings, 'recess_shape', 1))
    if recess_shape == 2:  # Cone
        hole_radius = float(getattr(settings, 'cone_counter_dot_base_diameter', settings.counter_dot_base_diameter)) / 2
    elif recess_shape == 1:  # Bowl
        hole_radius = float(getattr(settings, 'bowl_counter_dot_base_diameter', settings.counter_dot_base_diameter)) / 2
    else:  # Hemisphere
        try:
            counter_base = float(
                getattr(settings, 'hemi_counter_dot_base_diameter', settings.counter_dot_base_diameter)
            )
        except Exception:
            counter_base = settings.emboss_dot_base_diameter + settings.counter_plate_dot_size_offset
        hole_radius = counter_base / 2

    hole_radius = max(0.3, hole_radius)

    # Create outer circle for cylinder surface
    outer_circle = ShapelyPoint(0, 0).buffer(radius, resolution=128)

    # Create inner polygon for cutout
    if polygonal_cutout_radius > 0:
        polygonal_cutout_sides = max(3, polygonal_cutout_sides)
        circumscribed_radius = polygonal_cutout_radius / np.cos(np.pi / polygonal_cutout_sides)
        angles = np.linspace(0, 2 * np.pi, polygonal_cutout_sides, endpoint=False)

        # Align to first column position
        first_col_angle = start_angle
        align_angle = first_col_angle + seam_offset_rad

        vertices_2d = [
            (circumscribed_radius * np.cos(a + align_angle), circumscribed_radius * np.sin(a + align_angle))
            for a in angles
        ]
        inner_polygon = ShapelyPolygon(vertices_2d)
        cross_section = outer_circle.difference(inner_polygon)
    else:
        cross_section = outer_circle

    # Create holes in the 2D cross-section for all dot positions
    dot_spacing_angle = settings.dot_spacing / radius
    dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
    num_text_cols = settings.grid_columns - reserved

    # Create circular holes at each dot position on the outer surface
    outer_holes = []
    for _row in range(settings.grid_rows):
        for col in range(num_text_cols):
            mirrored_idx = (num_text_cols - 1) - col
            cell_angle = start_angle + ((mirrored_idx + 1) * cell_spacing_angle) + seam_offset_rad

            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_angle = cell_angle + dot_col_angle_offsets[dot_pos[1]]

                # Create hole on the outer circle at this angle
                hole_x = radius * np.cos(dot_angle)
                hole_y = radius * np.sin(dot_angle)
                hole = ShapelyPoint(hole_x, hole_y).buffer(hole_radius, resolution=16)
                outer_holes.append(hole)

    # Add indicator shape holes
    if getattr(settings, 'indicator_shapes', 1):
        for _row_num in range(settings.grid_rows):
            # Triangle at first column
            first_angle = start_angle + seam_offset_rad
            tri_x = radius * np.cos(first_angle)
            tri_y = radius * np.sin(first_angle)
            tri_hole = ShapelyPoint(tri_x, tri_y).buffer(settings.dot_spacing * 0.8, resolution=16)
            outer_holes.append(tri_hole)

            # Line at last column
            last_angle = start_angle + ((settings.grid_columns - 1) * cell_spacing_angle) + seam_offset_rad
            line_x = radius * np.cos(last_angle)
            line_y = radius * np.sin(last_angle)
            line_hole = ShapelyPoint(line_x, line_y).buffer(settings.dot_spacing * 0.5, resolution=16)
            outer_holes.append(line_hole)

    # Combine holes and subtract from cross-section
    if outer_holes:
        try:
            combined_holes = _unary_union(outer_holes)
            cross_section = cross_section.difference(combined_holes)
        except Exception as e:
            logger.warning(f'Failed to create hole pattern: {e}')

    # Extrude the 2D cross-section to 3D
    try:
        if cross_section.is_empty:
            logger.error('Cross-section is empty, returning simple shell')
            shell = create_cylinder_shell(diameter, height, polygonal_cutout_radius, polygonal_cutout_sides)
            min_z = shell.bounds[0][2]
            shell.apply_translation([0, 0, -min_z])
            return shell

        # Handle MultiPolygon
        if hasattr(cross_section, 'geoms'):
            parts = [extrude_polygon(g, height=height) for g in cross_section.geoms if g.area > 0.01]
            if parts:
                cylinder_mesh = trimesh.util.concatenate(parts)
            else:
                cylinder_mesh = create_cylinder_shell(diameter, height, polygonal_cutout_radius, polygonal_cutout_sides)
        else:
            cylinder_mesh = extrude_polygon(cross_section, height=height)

        # Center the cylinder
        cylinder_mesh.apply_translation([0, 0, -height / 2])

        # Ensure base is at Z=0
        min_z = cylinder_mesh.bounds[0][2]
        cylinder_mesh.apply_translation([0, 0, -min_z])

        logger.info(f'Created cylinder counter plate with 2D approach: {len(cylinder_mesh.vertices)} vertices')
        return cylinder_mesh

    except Exception as e:
        logger.error(f'Failed to extrude cylinder cross-section: {e}')
        shell = create_cylinder_shell(diameter, height, polygonal_cutout_radius, polygonal_cutout_sides)
        min_z = shell.bounds[0][2]
        shell.apply_translation([0, 0, -min_z])
        return shell
