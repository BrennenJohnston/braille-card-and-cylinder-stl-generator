"""
Data models and enums for braille STL generation.

This module defines typed models for request parameters and settings,
replacing magic numbers and untyped dictionaries.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ShapeType(str, Enum):
    """Shape type for braille output."""

    CARD = 'card'
    CYLINDER = 'cylinder'


class PlateType(str, Enum):
    """Plate type: positive (embossed) or negative (counter/recess)."""

    POSITIVE = 'positive'
    NEGATIVE = 'negative'


class BrailleGrade(str, Enum):
    """Braille grade: G1 (uncontracted) or G2 (contracted)."""

    G1 = 'g1'
    G2 = 'g2'


class RecessShape(int, Enum):
    """Recess shape for counter plates."""

    HEMISPHERE = 0
    BOWL = 1  # Spherical cap
    CONE = 2  # Frustum


@dataclass
class CardSettings:
    """
    Settings for braille card generation.

    This will replace the current CardSettings class in backend.py.
    """

    # Card dimensions
    card_width: float = 90.0
    card_height: float = 52.0
    card_thickness: float = 2.0

    # Grid layout
    grid_columns: int = 14
    grid_rows: int = 4

    # Spacing
    cell_spacing: float = 6.5  # Horizontal spacing between braille cells
    line_spacing: float = 10.0  # Vertical spacing between braille lines
    dot_spacing: float = 2.5  # Spacing between dots within a cell

    # Embossed dot parameters
    emboss_dot_base_diameter: float = 1.8
    emboss_dot_height: float = 1.0
    emboss_dot_flat_hat: float = 0.4

    # Counter plate dot parameters
    hemi_counter_dot_base_diameter: float = 1.6
    bowl_counter_dot_base_diameter: float = 1.8
    counter_dot_depth: float = 0.8

    # Recess shape
    recess_shape: int = 1  # Default to bowl

    # Mesh quality
    hemisphere_subdivisions: int = 1
    cone_segments: int = 16

    # Adjustments
    braille_x_adjust: float = 0.0
    braille_y_adjust: float = 0.0


@dataclass
class CylinderParams:
    """
    Parameters specific to cylinder generation.
    """

    diameter: float = 60.0
    wall_thickness: float = 2.0
    seam_offset_degrees: float = 0.0

    # Polygonal cutout (optional)
    polygonal_cutout_radius_mm: float = 0.0
    polygonal_cutout_sides: int = 0


@dataclass
class GenerateRequest:
    """
    Complete request for STL generation.

    This will replace the ad-hoc request parsing in routes.
    """

    lines: list[str]
    shape_type: ShapeType = ShapeType.CARD
    plate_type: PlateType = PlateType.POSITIVE
    grade: BrailleGrade = BrailleGrade.G1
    settings: Optional[CardSettings] = None
    cylinder_params: Optional[CylinderParams] = None
    original_lines: Optional[list[str]] = None
    placement_mode: str = 'manual'
    per_line_language_tables: Optional[list[str]] = None
