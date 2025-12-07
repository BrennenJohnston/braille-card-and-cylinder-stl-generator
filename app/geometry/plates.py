"""
Braille plate generation for flat cards.

This module handles generation of both embossed (positive) and counter (negative)
plates for flat braille cards.
"""

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from app.geometry.booleans import mesh_difference, mesh_union
from app.geometry.braille_layout import (
    create_card_line_end_marker_3d,
    create_card_triangle_marker_3d,
    create_character_shape_3d,
    create_character_shape_polygon,
    create_line_marker_polygon,
    create_triangle_marker_polygon,
)
from app.geometry.dot_shapes import create_braille_dot
from app.models import CardSettings
from app.utils import braille_to_dots, get_logger

logger = get_logger(__name__)


def create_positive_plate_mesh(lines, grade='g1', settings=None, original_lines=None):
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

    grade_name = f'Grade {grade.upper()}' if grade in ['g1', 'g2'] else 'Grade 1'
    logger.info(f'Creating positive plate mesh with {grade_name} characters')
    logger.info(f'Grid: {settings.grid_columns} columns × {settings.grid_rows} rows')
    logger.info(f'Centered margins: L/R={settings.left_margin:.2f}mm, T/B={settings.top_margin:.2f}mm')
    logger.info(
        f'Spacing: Cell-to-cell {settings.cell_spacing}mm, Line-to-line {settings.line_spacing}mm, Dot-to-dot {settings.dot_spacing}mm'
    )

    # Create card base
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width / 2, settings.card_height / 2, settings.card_thickness / 2))

    meshes = [base]
    marker_meshes = []  # Store markers separately for subtraction

    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]

    # Add end-of-row text/number indicators and triangle markers for ALL rows (not just those with content)
    for row_num in range(settings.grid_rows):
        # Calculate Y position for this row
        y_pos = (
            settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        )

        if getattr(settings, 'indicator_shapes', 1):
            # Add end-of-row text/number indicator at the first cell position (column 0)
            # Calculate X position for the first column
            x_pos_first = settings.left_margin + settings.braille_x_adjust

            # Determine which character to use for beginning-of-row indicator
            # In manual mode: first character from the corresponding manual line
            # In auto mode: original_lines is an array of per-row indicator characters
            logger.debug(
                f'Row {row_num}, original_lines provided: {original_lines is not None}, length: {len(original_lines) if original_lines else 0}'
            )
            if original_lines and row_num < len(original_lines):
                orig = (original_lines[row_num] or '').strip()
                # If auto supplied a single indicator character per row, just use it
                indicator_char = orig[0] if orig else ''
                logger.debug(f"Row {row_num} indicator candidate: '{indicator_char}'")
                if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
                    logger.debug(f"Creating character shape for '{indicator_char}' at first cell")
                    line_end_mesh = create_character_shape_3d(
                        indicator_char, x_pos_first, y_pos, settings, height=1.0, for_subtraction=True
                    )
                else:
                    logger.debug(f'Indicator not alphanumeric or empty, using rectangle for row {row_num}')
                    line_end_mesh = create_card_line_end_marker_3d(
                        x_pos_first, y_pos, settings, height=0.5, for_subtraction=True
                    )
            else:
                # No indicator info; default to rectangle
                logger.debug(f'No indicator info for row {row_num}, using rectangle')
                line_end_mesh = create_card_line_end_marker_3d(
                    x_pos_first, y_pos, settings, height=0.5, for_subtraction=True
                )

            marker_meshes.append(line_end_mesh)

            # Add triangle marker at the last cell position (grid_columns - 1)
            # Calculate X position for the last column
            x_pos_last = (
                settings.left_margin + ((settings.grid_columns - 1) * settings.cell_spacing) + settings.braille_x_adjust
            )

            # Create triangle marker for this row (recessed for embossing plate)
            triangle_mesh = create_card_triangle_marker_3d(
                x_pos_last, y_pos, settings, height=0.6, for_subtraction=True
            )
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
            error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters. Frontend must translate text to braille before sending.'
            logger.error(f'{error_msg}')
            raise RuntimeError(error_msg)

        # Check if braille text exceeds grid capacity
        reserved = 2 if getattr(settings, 'indicator_shapes', 1) else 0
        available_columns = settings.grid_columns - reserved
        if len(braille_text) > available_columns:
            # Warn and truncate instead of failing hard
            over = len(braille_text) - available_columns
            logger.warning(
                f'Line {row_num + 1} exceeds available columns by {over} cells. '
                f'Truncating to {available_columns} cells to continue generation.'
            )
            braille_text = braille_text[:available_columns]

        # Calculate Y position for this row (top-down)
        y_pos = (
            settings.card_height - settings.top_margin - (row_num * settings.line_spacing) + settings.braille_y_adjust
        )

        # Process each braille character in the line
        for col_num, braille_char in enumerate(braille_text):
            if col_num >= available_columns:
                break

            dots = braille_to_dots(braille_char)

            # Calculate X position for this column. Shift by one cell if indicators are enabled.
            x_pos = (
                settings.left_margin
                + ((col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)) * settings.cell_spacing)
                + settings.braille_x_adjust
            )

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
        logger.info(
            f'Created positive plate with {len(meshes) - 1} braille dots, {settings.grid_rows} text/number indicators, and {settings.grid_rows} triangle markers'
        )
    else:
        logger.info(f'Created positive plate with {len(meshes) - 1} braille dots and no indicator shapes')

    # Indicator recess creation using 2D operations (works in all environments)
    # This approach creates recesses by doing 2D boolean operations then extruding
    if getattr(settings, 'indicator_shapes', 1) and marker_meshes:
        try:
            # 1) Build 2D base rectangle
            base_2d = Polygon(
                [
                    (0.0, 0.0),
                    (settings.card_width, 0.0),
                    (settings.card_width, settings.card_height),
                    (0.0, settings.card_height),
                ]
            )

            # 2) Build 2D marker polygons for all rows (beginning indicator + triangle)
            from shapely.ops import unary_union as _unary_union

            subtractors = []
            for row_num in range(settings.grid_rows):
                y_pos = (
                    settings.card_height
                    - settings.top_margin
                    - (row_num * settings.line_spacing)
                    + settings.braille_y_adjust
                )
                x_first = settings.left_margin + settings.braille_x_adjust
                x_last = (
                    settings.left_margin
                    + ((settings.grid_columns - 1) * settings.cell_spacing)
                    + settings.braille_x_adjust
                )

                # Determine which beginning-of-row indicator to use (character or rectangle)
                # This logic matches lines 739-759 where 3D meshes are created
                if original_lines and row_num < len(original_lines):
                    orig = (original_lines[row_num] or '').strip()
                    indicator_char = orig[0] if orig else ''
                    if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
                        # Use character shape
                        char_polygon = create_character_shape_polygon(indicator_char, x_first, y_pos, settings)
                        if char_polygon is not None:
                            subtractors.append(char_polygon)
                        else:
                            subtractors.append(create_line_marker_polygon(x_first, y_pos, settings))
                    else:
                        # Use rectangle
                        subtractors.append(create_line_marker_polygon(x_first, y_pos, settings))
                else:
                    # No indicator info; default to rectangle
                    subtractors.append(create_line_marker_polygon(x_first, y_pos, settings))

                # Add triangle marker at the end of row
                subtractors.append(create_triangle_marker_polygon(x_last, y_pos, settings))

            subtractors_2d = _unary_union(subtractors)

            # 3) Create two-layer plate: bottom slab + top sheet with 2D holes (recess depth)
            # Use 1.0mm depth to accommodate character indicators (which are deeper than triangles)
            recess_h = 1.0  # mm; matches character indicator depth
            bottom_h = max(0.1, settings.card_thickness - recess_h)

            # Bottom slab: full rectangle, no holes
            bottom_slab = trimesh.creation.extrude_polygon(base_2d, height=bottom_h)

            # Top sheet: base minus markers, extruded to recess depth
            top_sheet_2d = base_2d.difference(subtractors_2d)

            def _extrude_multipolygon(shape_2d, height):
                if hasattr(shape_2d, 'geoms'):
                    parts = [trimesh.creation.extrude_polygon(g, height=height) for g in shape_2d.geoms]
                    return trimesh.util.concatenate(parts) if parts else None
                return trimesh.creation.extrude_polygon(shape_2d, height=height)

            top_sheet = _extrude_multipolygon(top_sheet_2d, recess_h)
            if top_sheet is None:
                raise RuntimeError('Top sheet extrusion produced no geometry')
            # Position the top sheet above the bottom slab
            top_sheet.apply_translation((0.0, 0.0, bottom_h))

            # 4) Combine bottom slab + top sheet + dots
            full_meshes = [bottom_slab, top_sheet] + meshes[1:]
            return trimesh.util.concatenate(full_meshes)
        except Exception as e2:
            logger.warning(f'2D marker recess approach failed: {e2}')

    # Default path: combine (no marker recesses)
    return trimesh.util.concatenate(meshes)


def create_simple_negative_plate(settings: CardSettings, lines=None):
    """
    Create a negative plate with recessed holes using 2D Shapely operations for Vercel compatibility.
    This creates a counter plate with holes that match the embossing plate dimensions and positioning.
    """

    # Create base rectangle for the card
    base_polygon = Polygon(
        [(0, 0), (settings.card_width, 0), (settings.card_width, settings.card_height), (0, settings.card_height)]
    )

    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Create holes for the actual text content (not all possible positions)
    holes = []
    total_dots = 0

    # Calculate hole radius based on dot dimensions plus offset
    # Counter plate holes should be slightly larger than embossing dots for proper alignment
    hole_radius = settings.recessed_dot_base_diameter / 2

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
                logger.warning(f'Line {row_num + 1} does not contain proper braille Unicode, skipping')
                continue

            # Calculate Y position for this row (same as embossing plate, using safe margin)
            y_pos = (
                settings.card_height
                - settings.top_margin
                - (row_num * settings.line_spacing)
                + settings.braille_y_adjust
            )

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
        logger.warning('No holes were created! Creating a plate with all possible holes as fallback')
        # Fallback: create holes for all possible positions
        return create_universal_counter_plate_fallback(settings)

    # Combine all holes into one multi-polygon
    try:
        all_holes = unary_union(holes)

        # Subtract holes from base to create the plate with holes
        plate_with_holes = base_polygon.difference(all_holes)

    except Exception as e:
        logger.error(f'Failed to combine holes or subtract from base: {e}')
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
        logger.error(f'Failed to extrude polygon: {e}')
        # Fallback to simple base plate if extrusion fails
        return create_fallback_plate(settings)


def create_universal_counter_plate_fallback(settings: CardSettings):
    """Create a counter plate with all possible holes as fallback when text-based holes fail"""

    # Create base rectangle for the card
    base_polygon = Polygon(
        [(0, 0), (settings.card_width, 0), (settings.card_width, settings.card_height), (0, settings.card_height)]
    )

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
        logger.error(f'Fallback counter plate creation failed: {e}')
        return create_fallback_plate(settings)


def create_fallback_plate(settings: CardSettings):
    """Create a simple fallback plate when hole creation fails"""
    logger.warning('Creating fallback plate without holes')
    base = trimesh.creation.box(extents=(settings.card_width, settings.card_height, settings.card_thickness))
    base.apply_translation((settings.card_width / 2, settings.card_height / 2, settings.card_thickness / 2))
    return base


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
    - Subtracts all spheres in one operation using trimesh.boolean.difference with built-in engine.
    - Generates dot centers from a full grid using the same layout parameters as the Embossing Plate.
    - Always places all 6 dots per cell (does not consult per-character translation).
    """

    # Create the base plate as a box aligned to z=[0, TH], x=[0, W], y=[0, H]
    plate_mesh = trimesh.creation.box(extents=(params.card_width, params.card_height, params.plate_thickness))
    plate_mesh.apply_translation((params.card_width / 2, params.card_height / 2, params.plate_thickness / 2))

    logger.debug(
        f'Creating counter plate base: {params.card_width}mm x {params.card_height}mm x {params.plate_thickness}mm'
    )

    # Dot positioning constants (same as embossing plate)
    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]  # Map dot index (0-5) to [row, col]

    # Calculate hemisphere radius including the counter plate offset
    try:
        counter_base = float(getattr(params, 'hemi_counter_dot_base_diameter', params.counter_dot_base_diameter))
    except Exception:
        counter_base = params.emboss_dot_base_diameter + params.counter_plate_dot_size_offset
    hemisphere_radius = counter_base / 2
    logger.debug(
        f'Hemisphere radius: {hemisphere_radius:.3f}mm (base: {params.emboss_dot_base_diameter}mm + offset: {params.counter_plate_dot_size_offset}mm)'
    )

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
            x_pos = (
                params.left_margin
                + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing)
                + params.braille_x_adjust
            )

            # Create spheres for ALL 6 dots in this cell
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]

                # Create an icosphere with the calculated hemisphere radius
                # Use hemisphere_subdivisions parameter to control mesh density
                sphere = trimesh.creation.icosphere(
                    subdivisions=params.hemisphere_subdivisions, radius=hemisphere_radius
                )
                # Position the sphere so its equator lies at the top surface (z = plate_thickness)
                z_pos = params.plate_thickness
                sphere.apply_translation((dot_x, dot_y, z_pos))
                sphere_meshes.append(sphere)
                total_spheres += 1

    logger.debug(f'Created {total_spheres} hemispheres for counter plate')

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

    logger.debug(
        f'Created {len(triangle_meshes)} triangle markers and {len(line_end_meshes)} line end markers for counter plate'
    )

    if not sphere_meshes:
        logger.warning('No spheres were generated. Returning base plate.')
        return plate_mesh

    # Perform boolean operations - try trimesh default first (serverless-compatible)
    engines_to_try = [None]  # None uses trimesh built-in boolean engine (no external dependencies)

    for engine in engines_to_try:
        try:
            engine_name = engine if engine else 'trimesh-default'
            logger.debug(f'Attempting boolean operations with {engine_name} engine...')

            # Union all spheres together for more efficient subtraction
            if len(sphere_meshes) == 1:
                union_spheres = sphere_meshes[0]
            else:
                logger.debug('Unioning spheres...')
                union_spheres = mesh_union(sphere_meshes)

            # Union all triangles (these will be used for subtraction into the plate)
            union_triangles = None
            if triangle_meshes:
                logger.debug(f'Unioning {len(triangle_meshes)} triangles (for subtraction)...')
                if len(triangle_meshes) == 1:
                    union_triangles = triangle_meshes[0]
                else:
                    union_triangles = mesh_union(triangle_meshes)

            # Union all line end markers
            if line_end_meshes:
                logger.debug(f'Unioning {len(line_end_meshes)} line end markers...')
                if len(line_end_meshes) == 1:
                    union_line_ends = line_end_meshes[0]
                else:
                    union_line_ends = mesh_union(line_end_meshes)

            # Combine cutouts (spheres and line ends) for subtraction
            logger.debug('Combining cutouts for subtraction...')
            cutouts_list = [union_spheres]
            if line_end_meshes:
                cutouts_list.append(union_line_ends)
            if union_triangles is not None:
                cutouts_list.append(union_triangles)

            if len(cutouts_list) > 1:
                all_cutouts = mesh_union(cutouts_list)
            else:
                all_cutouts = cutouts_list[0]

            logger.debug('Subtracting cutouts from plate...')
            # Subtract the cutouts (spheres, line ends, and triangles) from the plate
            counter_plate_mesh = mesh_difference([plate_mesh, all_cutouts])

            # Verify the mesh is watertight
            if not counter_plate_mesh.is_watertight:
                logger.debug('Counter plate mesh not watertight, attempting to fix...')
                counter_plate_mesh.fill_holes()
                if counter_plate_mesh.is_watertight:
                    logger.debug('Successfully fixed counter plate mesh')

            logger.debug(
                f'Counter plate completed with {engine_name} engine: {len(counter_plate_mesh.vertices)} vertices, {len(counter_plate_mesh.faces)} faces'
            )
            return counter_plate_mesh

        except Exception as e:
            logger.error(f'Boolean operations with {engine_name} failed: {e}')
            if engine == engines_to_try[-1]:  # Last engine failed
                logger.warning(
                    'All boolean engines failed. Creating hemisphere counter plate with individual subtraction...'
                )
                break
            else:
                logger.warning('Trying next engine...')
                continue

    # Final fallback: subtract spheres and triangles one by one (slower but more reliable)
    try:
        logger.debug('Attempting individual sphere and triangle subtraction...')
        counter_plate_mesh = plate_mesh.copy()

        for i, sphere in enumerate(sphere_meshes):
            try:
                logger.debug(f'Subtracting sphere {i + 1}/{len(sphere_meshes)}...')
                counter_plate_mesh = mesh_difference([counter_plate_mesh, sphere])
            except Exception as sphere_error:
                logger.warning(f'Failed to subtract sphere {i + 1}: {sphere_error}')
                continue

        # Subtract triangles individually (recess them)
        for i, triangle in enumerate(triangle_meshes):
            try:
                logger.debug(f'Subtracting triangle {i + 1}/{len(triangle_meshes)}...')
                counter_plate_mesh = mesh_difference([counter_plate_mesh, triangle])
            except Exception as triangle_error:
                logger.warning(f'Failed to subtract triangle {i + 1}: {triangle_error}')
                continue

        # Subtract line end markers individually
        for i, line_end in enumerate(line_end_meshes):
            try:
                logger.debug(f'Subtracting line end marker {i + 1}/{len(line_end_meshes)}...')
                counter_plate_mesh = mesh_difference([counter_plate_mesh, line_end])
            except Exception as line_error:
                logger.warning(f'Failed to subtract line end marker {i + 1}: {line_error}')
                continue

        # Try to fix the mesh
        if not counter_plate_mesh.is_watertight:
            counter_plate_mesh.fill_holes()

        logger.debug(
            f'Individual subtraction completed: {len(counter_plate_mesh.vertices)} vertices, {len(counter_plate_mesh.faces)} faces'
        )
        return counter_plate_mesh

    except Exception as final_error:
        logger.error(f'Individual sphere subtraction failed: {final_error}')
        logger.warning('Falling back to simple negative plate method.')
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
    plate_mesh.apply_translation((params.card_width / 2, params.card_height / 2, params.plate_thickness / 2))

    dot_col_offsets = [-params.dot_spacing / 2, params.dot_spacing / 2]
    dot_row_offsets = [params.dot_spacing, 0, -params.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Inputs
    a = (
        float(getattr(params, 'bowl_counter_dot_base_diameter', getattr(params, 'counter_dot_base_diameter', 1.6)))
        / 2.0
    )
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
            x_pos = (
                params.left_margin
                + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing)
                + params.braille_x_adjust
            )
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

    logger.debug(f'Created {total_spheres} bowl caps for counter plate (a={a:.3f}mm, h={h:.3f}mm, R={R:.3f}mm)')

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
        logger.warning('No spheres were generated. Returning base plate.')
        return plate_mesh

    # Boolean operations - use trimesh default (serverless-compatible)
    engines_to_try = [None]  # None uses trimesh built-in boolean engine
    for engine in engines_to_try:
        try:
            engine_name = engine if engine else 'trimesh-default'
            logger.debug(f'Bowl boolean ops with {engine_name}...')

            if len(sphere_meshes) == 1:
                union_spheres = sphere_meshes[0]
            else:
                union_spheres = mesh_union(sphere_meshes)

            union_triangles = None
            if triangle_meshes:
                if len(triangle_meshes) == 1:
                    union_triangles = triangle_meshes[0]
                else:
                    union_triangles = mesh_union(triangle_meshes)

            if line_end_meshes:
                if len(line_end_meshes) == 1:
                    union_line_ends = line_end_meshes[0]
                else:
                    union_line_ends = mesh_union(line_end_meshes)

            cutouts_list = [union_spheres]
            if line_end_meshes:
                cutouts_list.append(union_line_ends)
            if union_triangles is not None:
                cutouts_list.append(union_triangles)

            if len(cutouts_list) > 1:
                all_cutouts = mesh_union(cutouts_list)
            else:
                all_cutouts = cutouts_list[0]

            counter_plate_mesh = mesh_difference([plate_mesh, all_cutouts])
            if not counter_plate_mesh.is_watertight:
                counter_plate_mesh.fill_holes()
            logger.debug(f'Counter plate with bowl recess completed: {len(counter_plate_mesh.vertices)} verts')
            return counter_plate_mesh
        except Exception as e:
            logger.error(f'Bowl boolean with {engine_name} failed: {e}')
            if engine == engines_to_try[-1]:
                logger.warning('Falling back to simple negative plate method.')
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
    plate_mesh.apply_translation((params.card_width / 2, params.card_height / 2, params.plate_thickness / 2))

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
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    cos_angles = np.cos(angles)
    sin_angles = np.sin(angles)

    # Create conical frustum solids for subtraction using optimized approach
    recess_meshes = []
    total_recess = 0
    for row in range(params.grid_rows):
        y_pos = params.card_height - params.top_margin - (row * params.line_spacing) + params.braille_y_adjust
        reserved = 2 if getattr(params, 'indicator_shapes', 1) else 0
        for col in range(params.grid_columns - reserved):
            x_pos = (
                params.left_margin
                + ((col + (1 if getattr(params, 'indicator_shapes', 1) else 0)) * params.cell_spacing)
                + params.braille_x_adjust
            )
            for dot_idx in range(6):
                dot_pos = dot_positions[dot_idx]
                dot_x = x_pos + dot_col_offsets[dot_pos[1]]
                dot_y = y_pos + dot_row_offsets[dot_pos[0]]

                # OPTIMIZATION: Use pre-calculated trigonometric values
                top_ring = np.column_stack([base_r * cos_angles, base_r * sin_angles, np.zeros_like(angles)])
                bot_ring = np.column_stack([hat_r * cos_angles, hat_r * sin_angles, -height_h * np.ones_like(angles)])
                vertices = np.vstack([top_ring, bot_ring, [[0, 0, 0]], [[0, 0, -height_h]]])
                top_center_index = 2 * segments
                bot_center_index = 2 * segments + 1

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
        logger.warning('No cone recesses were generated. Returning base plate.')
        return plate_mesh

    logger.debug(
        f'Created {total_recess} cone frusta for counter plate (base_d={base_d:.3f}mm, hat_d={hat_d:.3f}mm, h={height_h:.3f}mm)'
    )

    # OPTIMIZATION: Use union operations like bowl/hemisphere for better performance
    try:
        # Union all recess meshes first (like bowl/hemisphere approach)
        if len(recess_meshes) == 1:
            union_recesses = recess_meshes[0]
        else:
            # Use trimesh default engine (serverless-compatible)
            engines_to_try = [None]  # None uses trimesh built-in boolean engine
            union_recesses = None
            for engine in engines_to_try:
                try:
                    engine_name = engine if engine else 'trimesh-default'
                    logger.debug(f'Cone union with {engine_name}...')
                    union_recesses = mesh_union(recess_meshes)
                    break
                except Exception as e:
                    logger.warning(f'Failed to union with {engine_name}: {e}')
                    continue

            if union_recesses is None:
                raise Exception('All union engines failed')

        # Union markers
        union_triangles = None
        if triangle_meshes:
            if len(triangle_meshes) == 1:
                union_triangles = triangle_meshes[0]
            else:
                union_triangles = mesh_union(triangle_meshes)

        union_line_ends = None
        if line_end_meshes:
            if len(line_end_meshes) == 1:
                union_line_ends = line_end_meshes[0]
            else:
                union_line_ends = mesh_union(line_end_meshes)

        # Combine all cutouts
        cutouts_list = [union_recesses]
        if union_line_ends is not None:
            cutouts_list.append(union_line_ends)
        if union_triangles is not None:
            cutouts_list.append(union_triangles)

        # Single difference operation (much faster than individual subtractions)
        if len(cutouts_list) > 1:
            union_cutouts = mesh_union(cutouts_list)
        else:
            union_cutouts = cutouts_list[0]

        result_mesh = mesh_difference([plate_mesh, union_cutouts])

        if not result_mesh.is_watertight:
            result_mesh.fill_holes()
        logger.debug(f'Cone recess (optimized union approach) completed: {len(result_mesh.vertices)} verts')
        return result_mesh

    except Exception as e_final:
        logger.error(f'Cone recess union approach failed: {e_final}')
        logger.warning('Falling back to individual subtraction method.')

        # Fallback to individual subtraction if union approach fails
        try:
            result_mesh = plate_mesh.copy()
            for i, recess in enumerate(recess_meshes):
                try:
                    if (i % 50) == 0:
                        logger.debug(f'Subtracting cone frustum {i + 1}/{len(recess_meshes)}...')
                    result_mesh = mesh_difference([result_mesh, recess])
                except Exception as e_sub:
                    logger.warning(f'Failed to subtract frustum {i + 1}: {e_sub}')
                    continue
            for i, triangle in enumerate(triangle_meshes):
                try:
                    result_mesh = mesh_difference([result_mesh, triangle])
                except Exception as e_tri:
                    logger.warning(f'Failed to subtract triangle {i + 1}: {e_tri}')
                    continue
            for i, line_end in enumerate(line_end_meshes):
                try:
                    result_mesh = mesh_difference([result_mesh, line_end])
                except Exception as e_line:
                    logger.warning(f'Failed to subtract line end {i + 1}: {e_line}')
                    continue
            if not result_mesh.is_watertight:
                result_mesh.fill_holes()
            logger.debug(f'Cone recess (fallback individual subtraction) completed: {len(result_mesh.vertices)} verts')
            return result_mesh
        except Exception as e_fallback:
            logger.error(f'All cone recess methods failed: {e_fallback}')
            logger.warning('Returning simple negative plate method.')
            return create_simple_negative_plate(params)
