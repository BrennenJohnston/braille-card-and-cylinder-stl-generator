"""
Braille layout and marker functions.

This module contains functions for creating 2D and 3D marker shapes
(triangles, lines, characters) used on braille cards, as well as helper
functions for character rendering.
"""

import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.models import CardSettings
from app.utils import get_logger

logger = get_logger(__name__)


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
    2 * settings.dot_spacing

    # Triangle height (horizontal extension) = dot_spacing (to reach middle-right dot)
    triangle_width = settings.dot_spacing

    # Triangle vertices:
    # Base is centered between top-left and bottom-left dots
    base_x = x - settings.dot_spacing / 2  # Left column position

    # Create triangle vertices
    vertices = [
        (base_x, y - settings.dot_spacing),  # Bottom of base
        (base_x, y + settings.dot_spacing),  # Top of base
        (base_x + triangle_width, y),  # Apex (at middle-right dot height)
    ]

    # Create and return the triangle polygon
    return Polygon(vertices)


def create_line_marker_polygon(x, y, settings: CardSettings):
    """
    Create a 2D rectangle polygon for the end-of-row line marker at the first cell.

    The rectangle height equals the cell height (2 * dot_spacing) and the
    width equals one dot spacing, centered at the right column of the first cell.

    Args:
        x: X position of the cell center
        y: Y position of the cell center
        settings: CardSettings object with braille dimensions

    Returns:
        Shapely Polygon representing the rectangle
    """
    line_width = settings.dot_spacing
    line_x = x + settings.dot_spacing / 2
    vertices = [
        (line_x - line_width / 2, y - settings.dot_spacing),  # Bottom left
        (line_x + line_width / 2, y - settings.dot_spacing),  # Bottom right
        (line_x + line_width / 2, y + settings.dot_spacing),  # Top right
        (line_x - line_width / 2, y + settings.dot_spacing),  # Top left
    ]
    return Polygon(vertices)


def _build_character_polygon(char_upper: str, target_width: float, target_height: float):
    """
    Build a 2D character outline as a shapely polygon, scaled to fit within
    the provided target width/height, centered at origin. Uses matplotlib if
    available; returns None on failure so callers can fall back gracefully.
    """
    try:
        # Lazy import to keep serverless light
        try:
            from matplotlib.font_manager import FontProperties  # type: ignore
            from matplotlib.path import Path  # type: ignore
            from matplotlib.textpath import TextPath  # type: ignore
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


def create_character_shape_polygon(character, x, y, settings: CardSettings):
    """
    Create a 2D character polygon for the beginning-of-row indicator.
    This is used for creating recesses in embossing plates using 2D operations.

    Args:
        character: Single character (A-Z or 0-9)
        x: X position of the cell center
        y: Y position of the cell center
        settings: CardSettings object with braille dimensions

    Returns:
        Shapely Polygon representing the character, or None if character cannot be created
    """
    # Define character size (same as in create_character_shape_3d)
    char_height = 2 * settings.dot_spacing + 4.375  # 9.375mm for default 2.5mm dot spacing
    char_width = settings.dot_spacing * 0.8 + 2.6875  # 4.6875mm for default 2.5mm dot spacing

    # Position character at the right column of the cell
    char_x = x + settings.dot_spacing / 2
    char_y = y

    # Get the character definition
    char_upper = character.upper()
    if not (char_upper.isalpha() or char_upper.isdigit()):
        # Fall back to rectangle for undefined characters
        return create_line_marker_polygon(x, y, settings)

    try:
        # Build character polygon using shared helper
        char_2d = _build_character_polygon(char_upper, char_width, char_height)
        if char_2d is None:
            return create_line_marker_polygon(x, y, settings)

        # Translate to desired position
        from shapely import affinity as _affinity

        char_2d = _affinity.translate(char_2d, xoff=char_x, yoff=char_y)

        return char_2d
    except Exception as e:
        logger.warning(f'Failed to create character polygon: {e}')
        return create_line_marker_polygon(x, y, settings)


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
    2 * settings.dot_spacing
    triangle_width = settings.dot_spacing

    # Triangle vertices (same as 2D version)
    base_x = x - settings.dot_spacing / 2  # Left column position

    vertices = [
        (base_x, y - settings.dot_spacing),  # Bottom of base
        (base_x, y + settings.dot_spacing),  # Top of base
        (base_x + triangle_width, y),  # Apex (at middle-right dot height)
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
    2 * settings.dot_spacing  # Vertical extent (same as cell height)
    line_width = settings.dot_spacing  # Horizontal extent

    # Position line at the right column of the cell
    # The line should be centered on the right column dot positions
    line_x = x + settings.dot_spacing / 2  # Right column position

    # Create rectangle vertices
    vertices = [
        (line_x - line_width / 2, y - settings.dot_spacing),  # Bottom left
        (line_x + line_width / 2, y - settings.dot_spacing),  # Bottom right
        (line_x + line_width / 2, y + settings.dot_spacing),  # Top right
        (line_x - line_width / 2, y + settings.dot_spacing),  # Top left
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
        logger.warning(f'Failed to create character shape using matplotlib: {e}')
        logger.info('Falling back to rectangle marker')
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
                    logger.warning('Character mesh is not a valid volume')
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
        logger.warning(f'Failed to extrude character shape: {e}')
        return create_card_line_end_marker_3d(x, y, settings, height, for_subtraction)

    # Debug: character marker generated
    return char_prism
