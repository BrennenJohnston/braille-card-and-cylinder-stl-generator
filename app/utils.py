"""
Utility functions and constants.

This module contains shared utilities, constants, and helper functions
used across the application.
"""

import logging
from typing import Any

# Constants
EPSILON = 1e-6  # Small value for floating point comparisons
MM_TO_INCHES = 0.0393701  # Conversion factor

# Braille Unicode range
BRAILLE_UNICODE_START = 0x2800  # ⠀
BRAILLE_UNICODE_END = 0x28FF  # ⣿


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)


def is_braille_char(char: str) -> bool:
    """
    Check if a character is a braille Unicode character.

    Args:
        char: Single character to check

    Returns:
        True if character is in braille Unicode range
    """
    if not char or len(char) != 1:
        return False
    code = ord(char)
    return BRAILLE_UNICODE_START <= code <= BRAILLE_UNICODE_END


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float with fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
