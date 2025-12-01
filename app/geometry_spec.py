"""
Geometry specification extraction for client-side CSG.

This module extracts geometry specifications (positions, dimensions) from
braille layouts without performing boolean operations, for use by client-side
CSG workers.
"""

from app.models import CardSettings
from app.utils import braille_to_dots, get_logger

logger = get_logger(__name__)


def extract_card_geometry_spec(lines, grade, settings: CardSettings, original_lines=None, plate_type='positive'):
    """
    Extract geometry specification for a braille card without performing CSG.

    Returns a dict with:
    - plate: dimensions and position of base plate
    - dots: list of dot specifications with positions and parameters
    - markers: list of marker specifications (triangles, rectangles, characters)
    """
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
                dots = braille_to_dots(char)

                for dot_idx in dots:
                    if dot_idx < 0 or dot_idx >= 6:
                        continue
                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_x = x_pos + dot_col_offsets[col_off_idx]
                    dot_y = y_pos + dot_row_offsets[row_off_idx]

                    dot_spec = _create_dot_spec(dot_x, dot_y, settings, 'standard', plate_type)
                    spec['dots'].append(dot_spec)

    return spec


def _create_dot_spec(x, y, settings, shape_type='standard', plate_type='positive'):
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
    lines, grade, settings: CardSettings, cylinder_params=None, original_lines=None, plate_type='positive'
):
    """
    Extract geometry specification for a braille cylinder without performing CSG.

    Returns a dict with:
    - cylinder: shell dimensions and cutout polygon
    - dots: list of dot specifications with positions and parameters
    - markers: list of marker specifications
    """
    if cylinder_params is None:
        cylinder_params = {}

    diameter = float(cylinder_params.get('diameter', 60.0))
    height = float(cylinder_params.get('height', 100.0))
    thickness = float(cylinder_params.get('thickness', 3.0))
    radius = diameter / 2

    spec = {
        'shape_type': 'cylinder',
        'plate_type': plate_type,
        'cylinder': {
            'radius': radius,
            'height': height,
            'thickness': thickness,
            'polygon_points': [],  # TODO: Add polygon cutout points if needed
        },
        'dots': [],
        'markers': [],
    }

    # Similar logic to card spec extraction but with cylindrical positioning
    # For now, return basic structure
    # Full implementation would compute curved positions on cylinder surface

    logger.warning('Cylinder geometry spec extraction not fully implemented yet')

    return spec
