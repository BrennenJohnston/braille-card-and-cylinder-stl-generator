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


def setup_logging(name: str = None, level: int = None) -> logging.Logger:
    """
    Configure application logging with proper formatting.

    Args:
        name: Logger name (module name). If None, returns root logger
        level: Logging level. If None, reads from LOG_LEVEL env var or defaults to INFO

    Returns:
        Configured logger instance
    """
    import os
    
    # Determine log level from environment or parameter
    if level is None:
        env_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, env_level, logging.INFO)
    
    # Configure root logger if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Return named logger or root logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(level)
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance configured for the module
    """
    return setup_logging(name)


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


def braille_to_dots(braille_char: str) -> list:
    """
    Convert a braille character to dot pattern.

    Braille dots are arranged as:
    1 4
    2 5
    3 6

    Args:
        braille_char: Single braille Unicode character

    Returns:
        List of 6 integers (0 or 1) representing dot pattern
    """
    # Braille Unicode block starts at U+2800
    # Each braille character is represented by 8 bits (dots 1-8)
    if not braille_char or braille_char == ' ':
        return [0, 0, 0, 0, 0, 0]  # Empty cell

    # Get the Unicode code point
    code_point = ord(braille_char)

    # Check if it's in the braille Unicode block (U+2800 to U+28FF)
    if code_point < 0x2800 or code_point > 0x28FF:
        return [0, 0, 0, 0, 0, 0]  # Not a braille character

    # Extract the dot pattern (bits 0-7 for dots 1-8)
    # The bit order is dot 1, 2, 3, 4, 5, 6, 7, 8
    dot_pattern = code_point - 0x2800

    # Convert to 6-dot pattern (dots 1-6)
    dots = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        if dot_pattern & (1 << i):
            dots[i] = 1

    return dots
