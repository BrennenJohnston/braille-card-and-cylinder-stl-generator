"""
Input validation for braille STL generation.

This module provides validation functions for incoming requests,
ensuring security, correctness, and helpful error messages.
"""

from typing import Any, Dict, List, Optional

from app.utils import get_logger, is_braille_char

# Configure logging
logger = get_logger(__name__)

# Validation constants
MAX_LINE_LENGTH = 50
MAX_LINES = 4
BRAILLE_UNICODE_START = 0x2800
BRAILLE_UNICODE_END = 0x28FF


class ValidationError(ValueError):
    """Custom exception for validation errors with structured details."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


def validate_lines(lines: Any) -> bool:
    """
    Validate the lines input for security and correctness.
    
    Args:
        lines: Input lines to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If validation fails with details
    """
    if not isinstance(lines, list):
        raise ValidationError('Lines must be a list', {'type': type(lines).__name__})

    if len(lines) > MAX_LINES:
        raise ValidationError(
            f'Too many lines provided. Maximum is {MAX_LINES} lines.', {'provided': len(lines), 'max': MAX_LINES}
        )

    for i, line in enumerate(lines):
        if not isinstance(line, str):
            raise ValidationError(f'Line {i + 1} must be a string', {'line_number': i + 1, 'type': type(line).__name__})

        # Check length to prevent extremely long inputs
        if len(line) > MAX_LINE_LENGTH:
            raise ValidationError(
                f'Line {i + 1} is too long (max {MAX_LINE_LENGTH} characters)',
                {'line_number': i + 1, 'length': len(line), 'max': MAX_LINE_LENGTH},
            )

        # Basic sanitization - check for potentially harmful characters
        harmful_chars = ['<', '>', '&', '"', "'", '\x00']
        found_harmful = [char for char in harmful_chars if char in line]
        if found_harmful:
            raise ValidationError(
                f'Line {i + 1} contains invalid characters: {found_harmful}',
                {'line_number': i + 1, 'invalid_chars': found_harmful},
            )

    return True


def validate_braille_lines(lines: List[str], plate_type: str = 'positive') -> bool:
    """
    Validate that lines contain valid braille Unicode characters.
    
    Only validates non-empty lines for positive plates (counter plates generate all dots).
    
    Args:
        lines: List of text lines
        plate_type: 'positive' or 'negative'
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If invalid braille characters found
    """
    if plate_type != 'positive':
        return True  # Counter plates don't need braille validation

    errors = []

    for i, line in enumerate(lines):
        if line.strip():  # Only validate non-empty lines
            # Check each character in the line
            for j, char in enumerate(line):
                # Allow standard ASCII space characters which represent blank braille cells
                if char == ' ':
                    continue
                    
                char_code = ord(char)
                if char_code < BRAILLE_UNICODE_START or char_code > BRAILLE_UNICODE_END:
                    errors.append({
                        'line': i + 1,
                        'position': j + 1,
                        'character': char,
                        'char_code': f'U+{char_code:04X}',
                        'expected': f'U+{BRAILLE_UNICODE_START:04X} to U+{BRAILLE_UNICODE_END:04X}',
                    })

    if errors:
        error_details = []
        for err in errors[:5]:  # Show first 5 errors to avoid spam
            error_details.append(
                f'Line {err["line"]}, position {err["position"]}: '
                f"'{err['character']}' ({err['char_code']}) is not a valid braille character"
            )

        if len(errors) > 5:
            error_details.append(f'... and {len(errors) - 5} more errors')

        raise ValidationError(
            'Invalid braille characters detected. Translation may have failed.\n'
            + '\n'.join(error_details)
            + '\n\nPlease ensure text is properly translated to braille before generating STL.',
            {'error_count': len(errors), 'errors': errors[:10]},  # Include up to 10 errors in details
        )

    return True


def validate_settings(settings_data: Any) -> bool:
    """
    Validate settings data for security and correctness.
    
    Args:
        settings_data: Settings dictionary from request
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(settings_data, dict):
        raise ValidationError('Settings must be a dictionary', {'type': type(settings_data).__name__})

    # Define allowed settings keys and their types/ranges
    allowed_settings = {
        'card_width': (float, 50, 200),
        'card_height': (float, 30, 150),
        'card_thickness': (float, 1, 10),
        'grid_columns': (int, 1, 20),
        'grid_rows': (int, 1, 200),
        'cell_spacing': (float, 2, 15),
        'line_spacing': (float, 5, 25),
        'dot_spacing': (float, 1, 5),
        'emboss_dot_base_diameter': (float, 0.5, 3),
        'emboss_dot_height': (float, 0.3, 2),
        'emboss_dot_flat_hat': (float, 0.1, 2),
        # Rounded dome
        'use_rounded_dots': (int, 0, 1),
        'rounded_dot_diameter': (float, 0.5, 3),
        'rounded_dot_height': (float, 0.2, 2),
        # New rounded dot with cone base params
        'rounded_dot_base_diameter': (float, 0.5, 3),
        'rounded_dot_cylinder_height': (float, 0.0, 2.0),
        'rounded_dot_base_height': (float, 0.0, 2.0),
        'rounded_dot_dome_height': (float, 0.1, 2.0),
        'rounded_dot_dome_diameter': (float, 0.5, 3.0),
        'braille_x_adjust': (float, -10, 10),
        'braille_y_adjust': (float, -10, 10),
        # Counter plate parameters
        'counter_plate_dot_size_offset': (float, 0, 2),
        'counter_dot_base_diameter': (float, 0.1, 5.0),
        'hemi_counter_dot_base_diameter': (float, 0.1, 5.0),
        'bowl_counter_dot_base_diameter': (float, 0.1, 5.0),
        'hemisphere_subdivisions': (int, 1, 3),
        'cone_segments': (int, 8, 32),
        'use_bowl_recess': (int, 0, 1),
        'recess_shape': (int, 0, 2),
        'cone_counter_dot_base_diameter': (float, 0.1, 5.0),
        'cone_counter_dot_height': (float, 0.0, 5.0),
        'cone_counter_dot_flat_hat': (float, 0.0, 5.0),
        'counter_dot_depth': (float, 0.0, 5.0),
        'indicator_shapes': (int, 0, 1),
    }

    for key, value in settings_data.items():
        if key not in allowed_settings:
            continue  # Ignore unknown settings (CardSettings will use defaults)

        expected_type, min_val, max_val = allowed_settings[key]

        # Type validation with better error messages
        try:
            if expected_type is int:  # Use 'is' for type comparison
                value = int(float(value))  # Allow "2.0" to become int 2
            else:
                value = float(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Setting '{key}' must be a number", {'key': key, 'value': value, 'expected_type': 'number'}
            ) from e

        # Range validation
        if not (min_val <= value <= max_val):
            raise ValidationError(
                f"Setting '{key}' must be between {min_val} and {max_val}",
                {'key': key, 'value': value, 'min': min_val, 'max': max_val},
            )

    return True


def validate_shape_type(shape_type: str) -> str:
    """
    Validate and normalize shape_type parameter.
    
    Args:
        shape_type: Shape type string
        
    Returns:
        Normalized shape type
        
    Raises:
        ValidationError: If invalid
    """
    normalized = str(shape_type).lower().strip()
    if normalized not in ['card', 'cylinder']:
        raise ValidationError(
            f"Invalid shape_type: '{shape_type}'. Must be 'card' or 'cylinder'.",
            {'provided': shape_type, 'valid_options': ['card', 'cylinder']},
        )
    return normalized


def validate_plate_type(plate_type: str) -> str:
    """
    Validate and normalize plate_type parameter.
    
    Args:
        plate_type: Plate type string
        
    Returns:
        Normalized plate type
        
    Raises:
        ValidationError: If invalid
    """
    normalized = str(plate_type).lower().strip()
    if normalized not in ['positive', 'negative']:
        raise ValidationError(
            f"Invalid plate_type: '{plate_type}'. Must be 'positive' or 'negative'.",
            {'provided': plate_type, 'valid_options': ['positive', 'negative']},
        )
    return normalized


def validate_grade(grade: str) -> str:
    """
    Validate and normalize braille grade parameter.
    
    Args:
        grade: Grade string
        
    Returns:
        Normalized grade
        
    Raises:
        ValidationError: If invalid
    """
    normalized = str(grade).lower().strip()
    if normalized not in ['g1', 'g2']:
        raise ValidationError(
            f"Invalid grade: '{grade}'. Must be 'g1' or 'g2'.",
            {'provided': grade, 'valid_options': ['g1', 'g2']},
        )
    return normalized


def validate_request_has_content(lines: List[str], plate_type: str) -> bool:
    """
    Validate that positive plates have at least some text content.
    
    Args:
        lines: List of text lines
        plate_type: 'positive' or 'negative'
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If positive plate has no content
    """
    if plate_type == 'positive' and all(not line.strip() for line in lines):
        raise ValidationError(
            'Please enter text in at least one line',
            {'plate_type': plate_type, 'lines_provided': len(lines), 'non_empty': 0},
        )
    return True

