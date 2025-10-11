"""
Data models and classes for braille STL generation.

This module defines typed models for request parameters, settings, and configuration,
replacing magic numbers and untyped dictionaries with explicit, validated structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# Enums for typed models
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


class PlacementMode(str, Enum):
    """Placement mode for braille text."""

    MANUAL = 'manual'
    AUTO = 'auto'


@dataclass
class CylinderParams:
    """
    Parameters specific to cylinder generation.

    Provides typed, validated cylinder parameters with sensible defaults.
    """

    diameter_mm: float = 31.35
    height_mm: Optional[float] = None  # If None, uses card_height from settings
    wall_thickness: float = 2.0
    seam_offset_deg: float = 355.0
    polygonal_cutout_radius_mm: float = 13.0
    polygonal_cutout_sides: int = 12

    @staticmethod
    def from_dict(data: dict, card_height: float = 52.0) -> 'CylinderParams':
        """Create CylinderParams from dictionary with defaults."""
        return CylinderParams(
            diameter_mm=float(data.get('diameter_mm', data.get('diameter', 31.35))),
            height_mm=float(data.get('height_mm', data.get('height', card_height))),
            wall_thickness=float(data.get('wall_thickness', 2.0)),
            seam_offset_deg=float(data.get('seam_offset_deg', data.get('seam_offset_degrees', 355.0))),
            polygonal_cutout_radius_mm=float(data.get('polygonal_cutout_radius_mm', 13.0)),
            polygonal_cutout_sides=int(data.get('polygonal_cutout_sides', 12)),
        )


@dataclass
class GenerateBrailleRequest:
    """
    Complete typed request for braille STL generation.

    Centralizes all request parameters with type safety and defaults.
    """

    # Required text input
    lines: list[str] = field(default_factory=lambda: ['', '', '', ''])

    # Shape and plate configuration
    shape_type: ShapeType = ShapeType.CARD
    plate_type: PlateType = PlateType.POSITIVE
    grade: BrailleGrade = BrailleGrade.G2
    placement_mode: PlacementMode = PlacementMode.MANUAL

    # Settings and parameters
    settings: Optional[dict] = None  # Will be converted to CardSettings
    cylinder_params: Optional[dict] = None  # Will be converted to CylinderParams

    # Optional metadata
    original_lines: Optional[list[str]] = None
    per_line_language_tables: Optional[list[str]] = None

    @staticmethod
    def from_request_data(data: dict) -> 'GenerateBrailleRequest':
        """
        Parse request JSON into typed GenerateBrailleRequest.

        Args:
            data: Request JSON dictionary

        Returns:
            GenerateBrailleRequest with validated types
        """
        # Parse enum fields with validation
        shape_type_str = str(data.get('shape_type', 'card')).lower()
        shape_type = ShapeType(shape_type_str) if shape_type_str in ['card', 'cylinder'] else ShapeType.CARD

        plate_type_str = str(data.get('plate_type', 'positive')).lower()
        plate_type = PlateType(plate_type_str) if plate_type_str in ['positive', 'negative'] else PlateType.POSITIVE

        grade_str = str(data.get('grade', 'g2')).lower()
        grade = BrailleGrade(grade_str) if grade_str in ['g1', 'g2'] else BrailleGrade.G2

        placement_mode_str = str(data.get('placement_mode', 'manual')).lower()
        placement_mode = (
            PlacementMode(placement_mode_str) if placement_mode_str in ['manual', 'auto'] else PlacementMode.MANUAL
        )

        return GenerateBrailleRequest(
            lines=data.get('lines', ['', '', '', '']),
            shape_type=shape_type,
            plate_type=plate_type,
            grade=grade,
            placement_mode=placement_mode,
            settings=data.get('settings', {}),
            cylinder_params=data.get('cylinder_params'),
            original_lines=data.get('original_lines'),
            per_line_language_tables=data.get('per_line_language_tables'),
        )


@dataclass
class GenerateCounterPlateRequest:
    """
    Typed request for counter plate generation (standalone endpoint).

    Counter plates don't need text input - they create all dot positions.
    """

    settings: Optional[dict] = None  # Will be converted to CardSettings

    @staticmethod
    def from_request_data(data: dict) -> 'GenerateCounterPlateRequest':
        """Parse request JSON into typed GenerateCounterPlateRequest."""
        return GenerateCounterPlateRequest(settings=data.get('settings', {}))


# CardSettings class (moved from backend.py)
class CardSettings:
    def __init__(self, **kwargs):
        # Default values matching project brief
        defaults = {
            # Card parameters
            'card_width': 90,
            'card_height': 52,
            'card_thickness': 2.0,
            # Grid parameters
            'grid_columns': 14,
            'grid_rows': 4,
            'cell_spacing': 6.5,  # Project brief default
            'line_spacing': 10.0,
            'dot_spacing': 2.5,
            # Emboss plate dot parameters (as per project brief)
            'emboss_dot_base_diameter': 1.8,  # Updated default: 1.8 mm
            'emboss_dot_height': 1.0,  # Project brief default: 1.0 mm
            'emboss_dot_flat_hat': 0.4,  # Updated default: 0.4 mm
            # Rounded dome dot parameters (optional alternative to cone)
            'use_rounded_dots': 0,  # 0 = cone (default), 1 = rounded dome
            # Legacy names kept for backward compatibility
            'rounded_dot_diameter': 1.5,  # Legacy: base diameter for rounded dome (mm)
            'rounded_dot_height': 0.6,  # Legacy: total height or dome height
            # New explicit parameters for rounded dot with cone base
            'rounded_dot_base_diameter': 2.0,  # Cone base diameter at surface
            'rounded_dot_dome_diameter': 1.5,  # Cone flat top diameter and dome base
            'rounded_dot_base_height': 0.2,  # Cone base height (from surface)
            'rounded_dot_cylinder_height': 0.2,  # Legacy alias: cylinder base height
            'rounded_dot_dome_height': 0.6,  # Dome height above cone flat top
            # Offset adjustments
            'braille_y_adjust': 0.0,  # Default to center
            'braille_x_adjust': 0.0,  # Default to center
            # Counter plate specific parameters
            'hemisphere_subdivisions': 1,  # For mesh density control
            'cone_segments': 16,  # Default cone polygon count (8-32 range)
            'counter_plate_dot_size_offset': 0.0,  # Legacy: offset from emboss dot diameter
            'counter_dot_base_diameter': 1.6,  # Deprecated: kept for back-compat
            # Separate diameters for hemisphere and bowl recesses
            'hemi_counter_dot_base_diameter': 1.6,
            'bowl_counter_dot_base_diameter': 1.8,
            # Bowl recess controls
            'use_bowl_recess': 1,  # 0 = hemisphere, 1 = bowl (spherical cap)
            # New tri-state recess shape selector: 0=hemisphere, 1=bowl, 2=cone
            'recess_shape': 1,
            # Cone recess default parameters
            'cone_counter_dot_base_diameter': 1.6,
            'cone_counter_dot_height': 0.8,
            'cone_counter_dot_flat_hat': 0.4,
            'counter_dot_depth': 0.8,  # Bowl recess depth (mm)
            # Legacy parameters (for backward compatibility)
            'dot_base_diameter': 1.8,  # Updated default: 1.8 mm
            'dot_height': 1.0,  # Project brief default: 1.0 mm
            'dot_hat_size': 0.4,  # Updated default: 0.4 mm
            'negative_plate_offset': 0.4,  # Legacy name for backward compatibility
            'emboss_dot_base_diameter_mm': 1.8,  # Updated default: 1.8 mm
            'plate_thickness_mm': 2.0,
            'epsilon_mm': 0.001,
            # Cylinder counter plate robustness (how much the sphere crosses the outer surface)
            'cylinder_counter_plate_overcut_mm': 0.05,
            # Indicator shapes (row start/end markers) toggle
            'indicator_shapes': 1,
        }

        # Set attributes from kwargs or defaults, while being tolerant of "empty" inputs
        for key, default_val in defaults.items():
            raw_val = kwargs.get(key)

            # Treat None, empty string or string with only whitespace as "use default"
            if raw_val is None or (isinstance(raw_val, str) and raw_val.strip() == ''):
                val = default_val
            else:
                # Attempt to cast to float – this will still raise if an invalid value
                # is supplied, which is desirable as it surfaces bad input early.
                val = float(raw_val)

            setattr(self, key, val)

        # Ensure attributes that represent counts are integers
        self.grid_columns = int(self.grid_columns)
        self.grid_rows = int(self.grid_rows)
        # Normalize boolean-like toggles stored as numbers
        try:
            self.use_rounded_dots = int(float(kwargs.get('use_rounded_dots', self.use_rounded_dots)))
        except Exception:
            self.use_rounded_dots = int(self.use_rounded_dots)
        try:
            self.indicator_shapes = int(float(kwargs.get('indicator_shapes', getattr(self, 'indicator_shapes', 1))))
        except Exception:
            self.indicator_shapes = int(getattr(self, 'indicator_shapes', 1))
        try:
            self.use_bowl_recess = int(float(kwargs.get('use_bowl_recess', getattr(self, 'use_bowl_recess', 0))))
        except Exception:
            self.use_bowl_recess = int(getattr(self, 'use_bowl_recess', 0))
        # Normalize recess_shape (0=hemi,1=bowl,2=cone)
        try:
            self.recess_shape = int(float(kwargs.get('recess_shape', getattr(self, 'recess_shape', 1))))
        except Exception:
            self.recess_shape = int(getattr(self, 'recess_shape', 1))

        # Map dot_shape to use_rounded_dots for backend compatibility
        try:
            dot_shape = kwargs.get('dot_shape', 'rounded')
            if dot_shape == 'rounded':
                self.use_rounded_dots = 1
            elif dot_shape == 'cone':
                self.use_rounded_dots = 0
        except Exception:
            pass  # Keep existing use_rounded_dots value

        # Calculate grid dimensions first
        self.grid_width = (self.grid_columns - 1) * self.cell_spacing
        self.grid_height = (self.grid_rows - 1) * self.line_spacing

        # Center the grid on the card with calculated margins
        self.left_margin = (self.card_width - self.grid_width) / 2
        self.right_margin = (self.card_width - self.grid_width) / 2
        self.top_margin = (self.card_height - self.grid_height) / 2
        self.bottom_margin = (self.card_height - self.grid_height) / 2

        # Safety margin minimum (½ of cell spacing)
        self.min_safe_margin = self.cell_spacing / 2

        # Validate that braille dots stay within solid surface boundaries (if not in initialization)
        try:
            self._validate_margins()
        except Exception as e:
            # Don't fail initialization due to validation issues
            print(f'Note: Margin validation skipped during initialization: {e}')

        # Map new parameter names to legacy ones for backward compatibility
        if 'emboss_dot_base_diameter' in kwargs:
            self.dot_base_diameter = self.emboss_dot_base_diameter
        if 'emboss_dot_height' in kwargs:
            self.dot_height = self.emboss_dot_height
        if 'emboss_dot_flat_hat' in kwargs:
            self.dot_hat_size = self.emboss_dot_flat_hat

        # Handle legacy parameter name for backward compatibility
        if 'negative_plate_offset' in kwargs and 'counter_plate_dot_size_offset' not in kwargs:
            self.counter_plate_dot_size_offset = self.negative_plate_offset

        # If independent counter base diameter is supplied, derive offset to keep legacy paths working
        # Otherwise, derive counter base from emboss + offset
        # Normalize legacy unified base diameter into the new split fields when provided
        try:
            provided_hemi = getattr(self, 'hemi_counter_dot_base_diameter', None)
            provided_bowl = getattr(self, 'bowl_counter_dot_base_diameter', None)
            provided_unified = getattr(self, 'counter_dot_base_diameter', None)
            if provided_unified is not None and (provided_hemi is None or provided_bowl is None):
                v = float(provided_unified)
                if provided_hemi is None:
                    self.hemi_counter_dot_base_diameter = v
                if provided_bowl is None:
                    self.bowl_counter_dot_base_diameter = v
            # Maintain legacy offset for code paths still referencing it
            base_for_offset = (
                provided_unified if provided_unified is not None else float(self.hemi_counter_dot_base_diameter)
            )
            self.counter_plate_dot_size_offset = float(base_for_offset) - float(self.emboss_dot_base_diameter)
        except Exception:
            pass

        # Ensure consistency between parameter names
        self.dot_top_diameter = self.emboss_dot_flat_hat
        self.emboss_dot_base_diameter_mm = self.emboss_dot_base_diameter

        # Recessed dot parameters (adjusted by offset) - for legacy functions
        self.recessed_dot_base_diameter = self.emboss_dot_base_diameter + (self.negative_plate_offset * 2)
        self.recessed_dot_top_diameter = self.emboss_dot_flat_hat + (self.negative_plate_offset * 2)
        self.recessed_dot_height = self.emboss_dot_height + self.negative_plate_offset

        # Counter plate specific parameters (not used in hemisphere approach)
        self.counter_plate_dot_base_diameter = self.emboss_dot_base_diameter + (self.negative_plate_offset * 2)
        self.counter_plate_dot_top_diameter = self.emboss_dot_flat_hat + (self.negative_plate_offset * 2)
        self.counter_plate_dot_height = self.emboss_dot_height + self.negative_plate_offset

        # Hemispherical recess parameters (as per project brief)
        # Hemisphere radius is based on the actual counter base diameter
        self.hemisphere_radius = (
            float(getattr(self, 'hemi_counter_dot_base_diameter', getattr(self, 'counter_dot_base_diameter', 1.6))) / 2
        )
        # Bowl (spherical cap) parameters
        self.bowl_base_radius = (
            float(getattr(self, 'bowl_counter_dot_base_diameter', getattr(self, 'counter_dot_base_diameter', 1.8))) / 2
        )
        # Clamp depth to safe bounds (0..plate_thickness)
        try:
            depth = float(getattr(self, 'counter_dot_depth', 0.8))
        except Exception:
            depth = 0.6
        self.counter_dot_depth = max(0.0, min(depth, self.card_thickness - self.epsilon_mm))
        self.plate_thickness = self.card_thickness
        self.epsilon = self.epsilon_mm
        self.cylinder_counter_plate_overcut_mm = self.cylinder_counter_plate_overcut_mm

        # Derived: active dot dimensions depending on shape selection
        if getattr(self, 'use_rounded_dots', 0):
            # Backward compatibility and alias mapping
            if not hasattr(self, 'rounded_dot_base_diameter') or self.rounded_dot_base_diameter is None:
                self.rounded_dot_base_diameter = self.rounded_dot_diameter
            if not hasattr(self, 'rounded_dot_dome_height') or self.rounded_dot_dome_height is None:
                # If only legacy rounded_dot_height provided, treat it as dome height
                self.rounded_dot_dome_height = self.rounded_dot_height
            # Prefer new base height, fall back to legacy cylinder height
            base_height = getattr(self, 'rounded_dot_base_height', None)
            if base_height is None:
                base_height = getattr(self, 'rounded_dot_cylinder_height', 0.2)
                self.rounded_dot_base_height = base_height
            else:
                # Keep legacy alias in sync when provided new param
                self.rounded_dot_cylinder_height = base_height

            # Prefer explicit dome diameter; fall back to base diameter for back-compat
            dome_diameter = getattr(self, 'rounded_dot_dome_diameter', None)
            if dome_diameter is None:
                dome_diameter = getattr(self, 'rounded_dot_base_diameter', 1.5)
                self.rounded_dot_dome_diameter = dome_diameter

            # Active dimensions for placement on surfaces
            self.active_dot_base_diameter = float(self.rounded_dot_base_diameter)
            self.active_dot_height = float(self.rounded_dot_base_height) + float(self.rounded_dot_dome_height)
        else:
            self.active_dot_height = self.emboss_dot_height
            self.active_dot_base_diameter = self.emboss_dot_base_diameter

    def _validate_margins(self):
        """
        Validate that the centered margins provide enough space for braille dots
        and meet the minimum safety margin requirements.
        """
        try:
            # Ensure all required attributes exist
            required_attrs = [
                'dot_spacing',
                'left_margin',
                'right_margin',
                'top_margin',
                'bottom_margin',
                'grid_width',
                'grid_height',
                'card_width',
                'card_height',
                'cell_spacing',
                'min_safe_margin',
            ]
            for attr in required_attrs:
                if not hasattr(self, attr):
                    return  # Skip validation if attributes are missing

            # Check if margins meet minimum safety requirements
            margin_warnings = []
            if self.left_margin < self.min_safe_margin:
                margin_warnings.append(
                    f'Left margin ({self.left_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)'
                )
            if self.right_margin < self.min_safe_margin:
                margin_warnings.append(
                    f'Right margin ({self.right_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)'
                )
            if self.top_margin < self.min_safe_margin:
                margin_warnings.append(
                    f'Top margin ({self.top_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)'
                )
            if self.bottom_margin < self.min_safe_margin:
                margin_warnings.append(
                    f'Bottom margin ({self.bottom_margin:.2f}mm) is less than minimum safe margin ({self.min_safe_margin:.2f}mm)'
                )

            # Calculate the actual space needed for the braille grid with dots
            # Each braille cell is cell_spacing wide, dot spacing extends ±dot_spacing/2 from center
            max_dot_extension = self.dot_spacing / 2

            # Check if outermost dots will be within boundaries
            # Consider that dots extend ±dot_spacing/2 from their centers
            left_edge_clearance = self.left_margin - max_dot_extension
            right_edge_clearance = self.right_margin - max_dot_extension
            top_edge_clearance = self.top_margin - max_dot_extension
            bottom_edge_clearance = self.bottom_margin - max_dot_extension

            if margin_warnings:
                print('⚠ WARNING: Margins below minimum safe values:')
                for warning in margin_warnings:
                    print(f'  - {warning}')
                print(
                    f'  - Recommended minimum margin: {self.min_safe_margin:.2f}mm (½ of {self.cell_spacing:.1f}mm cell spacing)'
                )
                print('  - Consider reducing grid size or increasing card dimensions')

            # Check if dots will extend beyond card edges
            edge_warnings = []
            if left_edge_clearance < 0:
                edge_warnings.append(f'Left edge dots will extend {-left_edge_clearance:.2f}mm beyond card edge')
            if right_edge_clearance < 0:
                edge_warnings.append(f'Right edge dots will extend {-right_edge_clearance:.2f}mm beyond card edge')
            if top_edge_clearance < 0:
                edge_warnings.append(f'Top edge dots will extend {-top_edge_clearance:.2f}mm beyond card edge')
            if bottom_edge_clearance < 0:
                edge_warnings.append(f'Bottom edge dots will extend {-bottom_edge_clearance:.2f}mm beyond card edge')

            if edge_warnings:
                print('⚠ CRITICAL WARNING: Braille dots will extend beyond card boundaries!')
                for warning in edge_warnings:
                    print(f'  - {warning}')

            # Log successful validation if all is well
            if not margin_warnings and not edge_warnings:
                print('✓ Grid centering validation passed: Braille grid is centered with safe margins')
                print(f'  - Grid dimensions: {self.grid_width:.2f}mm × {self.grid_height:.2f}mm')
                print(f'  - Card dimensions: {self.card_width:.2f}mm × {self.card_height:.2f}mm')
                print(f'  - Centered margins: L/R={self.left_margin:.2f}mm, T/B={self.top_margin:.2f}mm')
                print(
                    f'  - Minimum safe margin: {self.min_safe_margin:.2f}mm (½ of {self.cell_spacing:.1f}mm cell spacing)'
                )
        except Exception:
            # Silently skip validation if there are any issues
            pass
