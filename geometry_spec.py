"""
Geometry specification extraction for client-side CSG.

This module extracts geometry specifications (positions, dimensions) from
braille layouts without performing boolean operations, for use by client-side
CSG workers.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def extract_card_geometry_spec(
    lines: list[str],
    grade: str,
    settings: Any,
    original_lines: list[str] | None = None,
    plate_type: str = 'positive',
    braille_to_dots_func: Callable[[str], list[int]] | None = None,
) -> dict[str, Any]:
    """
    Extract geometry specification for a braille card without performing CSG.

    Returns a dict with:
    - plate: dimensions and position of base plate
    - dots: list of dot specifications with positions and parameters
    - markers: list of marker specifications (triangles, rectangles, characters)
    """
    if braille_to_dots_func is None:
        raise ValueError('braille_to_dots_func is required')

    spec = {
        'shape_type': 'card',
        'plate_type': plate_type,
        'plate': {
            'width': settings.card_width,
            'height': settings.card_height,
            'thickness': settings.card_thickness,
            'center_x': settings.card_width / 2,
            'center_y': settings.card_height / 2,
            'center_z': settings.card_thickness / 2,
        },
        'dots': [],
        'markers': [],
    }

    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # For negative plates (counter plates), generate all dots for all cells
    if plate_type == 'negative':
        for row_num in range(settings.grid_rows):
            y_pos = (
                settings.card_height
                - settings.top_margin
                - (row_num * settings.line_spacing)
                + settings.braille_y_adjust
            )

            # Add markers if enabled
            if getattr(settings, 'indicator_shapes', 1):
                x_pos_first = settings.left_margin + settings.braille_x_adjust

                # Determine marker type
                if original_lines and row_num < len(original_lines):
                    orig = (original_lines[row_num] or '').strip()
                    indicator_char = orig[0] if orig else ''
                    if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
                        spec['markers'].append(
                            {
                                'type': 'character',
                                'char': indicator_char,
                                'x': x_pos_first,
                                'y': y_pos,
                                'z': settings.card_thickness,
                                'size': settings.dot_spacing * 1.5,
                                'depth': 1.0,
                            }
                        )
                    else:
                        spec['markers'].append(
                            {
                                'type': 'rect',
                                'x': x_pos_first + settings.dot_spacing / 2,
                                'y': y_pos,
                                'z': settings.card_thickness,
                                'width': settings.dot_spacing,
                                'height': 2 * settings.dot_spacing,
                                'depth': 0.5,
                            }
                        )
                else:
                    spec['markers'].append(
                        {
                            'type': 'rect',
                            'x': x_pos_first + settings.dot_spacing / 2,
                            'y': y_pos,
                            'z': settings.card_thickness,
                            'width': settings.dot_spacing,
                            'height': 2 * settings.dot_spacing,
                            'depth': 0.5,
                        }
                    )

            # Add all dots for all columns
            for col_num in range(settings.grid_columns):
                x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust

                # All 6 dots per cell
                for dot_idx in range(6):
                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_x = x_pos + dot_col_offsets[col_off_idx]
                    dot_y = y_pos + dot_row_offsets[row_off_idx]

                    # Choose recess shape based on settings
                    recess_shape = getattr(settings, 'counter_plate_recess_shape', 'hemisphere')

                    dot_spec = _create_dot_spec(dot_x, dot_y, settings, recess_shape, plate_type)
                    spec['dots'].append(dot_spec)

    else:
        # Positive plate: only add dots that are present in the braille text
        for row_num, line in enumerate(lines):
            if row_num >= settings.grid_rows:
                break

            y_pos = (
                settings.card_height
                - settings.top_margin
                - (row_num * settings.line_spacing)
                + settings.braille_y_adjust
            )

            # Add markers
            if getattr(settings, 'indicator_shapes', 1):
                x_pos_first = settings.left_margin + settings.braille_x_adjust

                # Triangle marker at end of row
                spec['markers'].append(
                    {
                        'type': 'triangle',
                        'x': x_pos_first,
                        'y': y_pos,
                        'z': settings.card_thickness,
                        'size': settings.dot_spacing,
                        'depth': 0.5,
                    }
                )

            # Process each character in the line
            chars = list(line)
            for col_num, char in enumerate(chars):
                if col_num >= settings.grid_columns:
                    break

                x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust

                # Get dots for this character
                dots = braille_to_dots_func(char)

                # braille_to_dots returns a 6-length list of 0/1 indicators.
                for dot_idx, dot_val in enumerate(dots):
                    if dot_val != 1:
                        continue
                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_x = x_pos + dot_col_offsets[col_off_idx]
                    dot_y = y_pos + dot_row_offsets[row_off_idx]

                    dot_spec = _create_dot_spec(dot_x, dot_y, settings, 'standard', plate_type)
                    spec['dots'].append(dot_spec)

    return spec


def _create_dot_spec(
    x: float, y: float, settings: Any, shape_type: str = 'standard', plate_type: str = 'positive'
) -> dict[str, Any]:
    """Create a dot specification dict."""
    z = settings.card_thickness

    if shape_type == 'hemisphere':
        # Hemisphere for counter plates
        radius = getattr(settings, 'counter_hemisphere_radius', 1.0)
        return {
            'type': 'rounded',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': 0,
                'top_radius': 0,
                'base_height': 0,
                'dome_height': radius,
                'dome_radius': radius,
            },
        }
    elif shape_type == 'bowl':
        # Bowl (spherical cap) for counter plates
        radius = getattr(settings, 'counter_bowl_radius', 1.5)
        depth = getattr(settings, 'counter_bowl_depth', 0.8)
        return {
            'type': 'rounded',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': 0,
                'top_radius': 0,
                'base_height': 0,
                'dome_height': depth,
                'dome_radius': (radius * radius + depth * depth) / (2.0 * depth),
            },
        }
    elif shape_type == 'cone':
        # Cone frustum for counter plates
        base_dia = getattr(settings, 'counter_cone_base_diameter', 2.0)
        top_dia = getattr(settings, 'counter_cone_top_diameter', 0.5)
        height = getattr(settings, 'counter_cone_depth', 1.0)
        return {
            'type': 'standard',
            'x': x,
            'y': y,
            'z': z,
            'params': {'base_radius': base_dia / 2, 'top_radius': top_dia / 2, 'height': height},
        }
    elif getattr(settings, 'use_rounded_dots', 0):
        # Rounded dots for positive plates
        base_dia = float(getattr(settings, 'rounded_dot_base_diameter', 2.0))
        dome_dia = float(getattr(settings, 'rounded_dot_dome_diameter', 1.5))
        base_h = float(getattr(settings, 'rounded_dot_base_height', 0.2))
        dome_h = float(getattr(settings, 'rounded_dot_dome_height', 0.6))
        R = (dome_dia / 2) ** 2 / (2.0 * dome_h) if dome_h > 0 else 1.0
        return {
            'type': 'rounded',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': base_dia / 2,
                'top_radius': dome_dia / 2,
                'base_height': base_h,
                'dome_height': dome_h,
                'dome_radius': R,
            },
        }
    else:
        # Standard cone frustum (default)
        return {
            'type': 'standard',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': settings.emboss_dot_base_diameter / 2,
                'top_radius': settings.emboss_dot_flat_hat / 2,
                'height': settings.emboss_dot_height,
            },
        }


def extract_cylinder_geometry_spec(
    lines: list[str],
    grade: str,
    settings: Any,
    cylinder_params: dict[str, Any] | None = None,
    original_lines: list[str] | None = None,
    plate_type: str = 'positive',
    braille_to_dots_func: Callable[[str], list[int]] | None = None,
) -> dict[str, Any]:
    """
    Extract geometry specification for a braille cylinder without performing CSG.

    Returns a dict with:
    - cylinder: shell dimensions and cutout polygon
    - dots: list of dot specifications with 3D positions on cylinder surface
    - markers: list of marker specifications
    """
    if braille_to_dots_func is None:
        raise ValueError('braille_to_dots_func is required')

    if cylinder_params is None:
        cylinder_params = {}

    diameter = float(cylinder_params.get('diameter', cylinder_params.get('diameter_mm', 60.0)))
    height = float(cylinder_params.get('height', cylinder_params.get('height_mm', settings.card_height)))
    thickness = float(cylinder_params.get('thickness', 3.0))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 0))

    radius = diameter / 2

    # Compute polygon cutout points if specified
    polygon_points = []
    if polygonal_cutout_radius > 0:
        circumscribed_radius = polygonal_cutout_radius / math.cos(math.pi / polygonal_cutout_sides)
        for i in range(polygonal_cutout_sides):
            angle = 2 * math.pi * i / polygonal_cutout_sides
            polygon_points.append(
                {'x': circumscribed_radius * math.cos(angle), 'y': circumscribed_radius * math.sin(angle)}
            )

    spec: dict[str, Any] = {
        'shape_type': 'cylinder',
        'plate_type': plate_type,
        'cylinder': {
            'radius': radius,
            'height': height,
            'thickness': thickness,
            'polygon_points': polygon_points,
        },
        'dots': [],
        'markers': [],
    }

    # Calculate grid layout parameters
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_angle = grid_width / radius
    start_angle = -grid_angle / 2
    cell_spacing_angle = settings.cell_spacing / radius
    dot_spacing_angle = settings.dot_spacing / radius

    # Dot positioning with angular offsets for columns, linear for rows
    dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Calculate vertical centering
    braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
    space_above = (height - braille_content_height) / 2.0
    first_row_center_y = height - space_above - settings.dot_spacing

    seam_offset_rad = math.radians(seam_offset)

    if plate_type == 'negative':
        # Counter plate: generate all 6 dots per cell for all cells
        for row_num in range(settings.grid_rows):
            y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
            y_local = y_pos - (height / 2.0)

            # Add markers
            if getattr(settings, 'indicator_shapes', 1):
                # Triangle marker at first column
                triangle_angle = start_angle + seam_offset_rad
                marker_spec = _create_cylinder_marker_spec(
                    triangle_angle,
                    y_local,
                    radius,
                    settings,
                    'triangle',
                    original_lines,
                    row_num,
                    plate_type='negative',
                )
                spec['markers'].append(marker_spec)

                # Character/rect marker at last column
                last_col_angle = start_angle + ((settings.grid_columns - 1) * cell_spacing_angle) + seam_offset_rad
                if original_lines and row_num < len(original_lines):
                    orig = (original_lines[row_num] or '').strip()
                    first_char = orig[0] if orig else ''
                    if first_char and (first_char.isalpha() or first_char.isdigit()):
                        marker_spec = _create_cylinder_marker_spec(
                            last_col_angle,
                            y_local,
                            radius,
                            settings,
                            'character',
                            original_lines,
                            row_num,
                            char=first_char,
                            plate_type='negative',
                        )
                    else:
                        marker_spec = _create_cylinder_marker_spec(
                            last_col_angle,
                            y_local,
                            radius,
                            settings,
                            'rect',
                            original_lines,
                            row_num,
                            plate_type='negative',
                        )
                else:
                    marker_spec = _create_cylinder_marker_spec(
                        last_col_angle,
                        y_local,
                        radius,
                        settings,
                        'rect',
                        original_lines,
                        row_num,
                        plate_type='negative',
                    )
                spec['markers'].append(marker_spec)

            # Generate all 6 dots for all cells
            for col_num in range(settings.grid_columns):
                col_angle = start_angle + (col_num * cell_spacing_angle) + seam_offset_rad

                for dot_idx in range(6):
                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_angle = col_angle + dot_col_angle_offsets[col_off_idx]
                    dot_y = y_local + dot_row_offsets[row_off_idx]

                    # Transform to 3D cylindrical coordinates
                    dot_spec = _create_cylinder_dot_spec(dot_angle, dot_y, radius, settings, plate_type='negative')
                    spec['dots'].append(dot_spec)

    else:
        # Positive plate: only generate dots that exist in the braille text
        for row_num, line in enumerate(lines):
            if row_num >= settings.grid_rows:
                break
            if not line.strip():
                continue

            # Check for braille Unicode
            has_braille = any(0x2800 <= ord(c) <= 0x28FF for c in line)
            if not has_braille:
                continue

            y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
            y_local = y_pos - (height / 2.0)

            # Add markers
            if getattr(settings, 'indicator_shapes', 1):
                # End-of-row indicator at first column
                first_col_angle = start_angle + seam_offset_rad
                if original_lines and row_num < len(original_lines):
                    orig = (original_lines[row_num] or '').strip()
                    first_char = orig[0] if orig else ''
                    if first_char and (first_char.isalpha() or first_char.isdigit()):
                        marker_spec = _create_cylinder_marker_spec(
                            first_col_angle,
                            y_local,
                            radius,
                            settings,
                            'character',
                            original_lines,
                            row_num,
                            char=first_char,
                            plate_type='positive',
                        )
                    else:
                        marker_spec = _create_cylinder_marker_spec(
                            first_col_angle,
                            y_local,
                            radius,
                            settings,
                            'rect',
                            original_lines,
                            row_num,
                            plate_type='positive',
                        )
                else:
                    marker_spec = _create_cylinder_marker_spec(
                        first_col_angle,
                        y_local,
                        radius,
                        settings,
                        'rect',
                        original_lines,
                        row_num,
                        plate_type='positive',
                    )
                spec['markers'].append(marker_spec)

                # Triangle marker at last column
                last_col_angle = start_angle + ((settings.grid_columns - 1) * cell_spacing_angle) + seam_offset_rad
                marker_spec = _create_cylinder_marker_spec(
                    last_col_angle,
                    y_local,
                    radius,
                    settings,
                    'triangle',
                    original_lines,
                    row_num,
                    plate_type='positive',
                )
                spec['markers'].append(marker_spec)

            # Process braille characters
            reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
            max_cols = settings.grid_columns - reserved
            chars = list(line.strip())[:max_cols]

            for col_num, braille_char in enumerate(chars):
                # Shift column by 1 if indicators are enabled (first col is for indicator)
                actual_col = col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)
                col_angle = start_angle + (actual_col * cell_spacing_angle) + seam_offset_rad

                # Get dot pattern for this braille character
                dots = braille_to_dots_func(braille_char)

                for dot_idx, dot_val in enumerate(dots):
                    if dot_val != 1:
                        continue

                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_angle = col_angle + dot_col_angle_offsets[col_off_idx]
                    dot_y = y_local + dot_row_offsets[row_off_idx]

                    # Transform to 3D cylindrical coordinates
                    dot_spec = _create_cylinder_dot_spec(dot_angle, dot_y, radius, settings, plate_type='positive')
                    spec['dots'].append(dot_spec)

    logger.info(f'Cylinder geometry spec: {len(spec["dots"])} dots, {len(spec["markers"])} markers')
    return spec


def _create_cylinder_dot_spec(
    theta: float, y_local: float, radius: float, settings: Any, plate_type: str = 'positive'
) -> dict[str, Any]:
    """
    Create a dot spec with 3D position on cylinder surface.

    Args:
        theta: Angle around cylinder (radians)
        y_local: Height position relative to cylinder center (becomes Z in Three.js Y-up coords)
        radius: Cylinder radius
        settings: CardSettings
        plate_type: 'positive' or 'negative'
    """
    # Convert cylindrical to 3D Cartesian
    # Server code uses Z-up, Three.js uses Y-up, so we swap Y and Z
    x = radius * math.cos(theta)
    z = radius * math.sin(theta)  # This becomes Z in Three.js (which is depth)
    y = y_local  # Height becomes Y in Three.js

    dot_height = settings.active_dot_height

    if plate_type == 'negative':
        # Counter plate - use recess shape
        recess_shape = getattr(settings, 'counter_plate_recess_shape', 'hemisphere')

        if recess_shape == 'hemisphere':
            recess_radius = getattr(settings, 'counter_hemisphere_radius', 1.0)
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': True,
                'params': {
                    'shape': 'hemisphere',
                    'recess_radius': recess_radius,
                },
            }
        elif recess_shape == 'bowl':
            bowl_radius = getattr(settings, 'counter_bowl_radius', 1.5)
            bowl_depth = getattr(settings, 'counter_bowl_depth', 0.8)
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': True,
                'params': {
                    'shape': 'bowl',
                    'bowl_radius': bowl_radius,
                    'bowl_depth': bowl_depth,
                },
            }
        else:
            # Cone
            base_dia = getattr(settings, 'counter_cone_base_diameter', 2.0)
            top_dia = getattr(settings, 'counter_cone_top_diameter', 0.5)
            cone_depth = getattr(settings, 'counter_cone_depth', 1.0)
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': True,
                'params': {
                    'shape': 'cone',
                    'base_radius': base_dia / 2,
                    'top_radius': top_dia / 2,
                    'height': cone_depth,
                },
            }
    else:
        # Positive plate - embossed dots
        if getattr(settings, 'use_rounded_dots', 0):
            base_dia = float(getattr(settings, 'rounded_dot_base_diameter', 2.0))
            dome_dia = float(getattr(settings, 'rounded_dot_dome_diameter', 1.5))
            base_h = float(getattr(settings, 'rounded_dot_base_height', 0.2))
            dome_h = float(getattr(settings, 'rounded_dot_dome_height', 0.6))
            R = (dome_dia / 2) ** 2 / (2.0 * dome_h) if dome_h > 0 else 1.0
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': False,
                'params': {
                    'shape': 'rounded',
                    'base_radius': base_dia / 2,
                    'top_radius': dome_dia / 2,
                    'base_height': base_h,
                    'dome_height': dome_h,
                    'dome_radius': R,
                },
            }
        else:
            # Standard cone frustum
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': False,
                'params': {
                    'shape': 'standard',
                    'base_radius': settings.emboss_dot_base_diameter / 2,
                    'top_radius': settings.emboss_dot_flat_hat / 2,
                    'height': dot_height,
                },
            }


def _create_cylinder_marker_spec(
    theta: float,
    y_local: float,
    radius: float,
    settings: Any,
    marker_type: str,
    original_lines: list[str] | None = None,
    row_num: int = 0,
    char: str | None = None,
    plate_type: str = 'positive',
) -> dict[str, Any]:
    """
    Create a marker spec with 3D position on cylinder surface.

    Note: Markers (triangles, characters, rectangles) are ALWAYS recessed
    (subtracted) on both positive and negative cylinder plates. The is_recess
    flag should always be True for markers - this differs from dots which
    are only recessed on negative (counter) plates.
    """
    # Convert cylindrical to 3D Cartesian (Y-up for Three.js)
    x = radius * math.cos(theta)
    z = radius * math.sin(theta)
    y = y_local
    # Markers are ALWAYS recessed (subtracted) regardless of plate type
    # This matches the local Python behavior in generate_cylinder_stl()
    # where markers are subtracted using mesh_difference()
    is_recess = True

    if marker_type == 'triangle':
        return {
            'type': 'cylinder_triangle',
            'x': x,
            'y': y,
            'z': z,
            'theta': theta,
            'radius': radius,
            'size': settings.dot_spacing,
            'depth': 0.6,
            'is_recess': is_recess,
        }
    elif marker_type == 'character':
        return {
            'type': 'cylinder_character',
            'x': x,
            'y': y,
            'z': z,
            'theta': theta,
            'radius': radius,
            'char': char or 'A',
            'size': settings.dot_spacing * 1.5,
            'depth': 1.0,
            'is_recess': is_recess,
        }
    else:  # rect
        return {
            'type': 'cylinder_rect',
            'x': x,
            'y': y,
            'z': z,
            'theta': theta,
            'radius': radius,
            'width': settings.dot_spacing,
            'height': 2 * settings.dot_spacing,
            'depth': 0.5,
            'is_recess': is_recess,
        }
