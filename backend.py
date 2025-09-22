"""
Backend module for Braille STL Generator
This imports the Flask app from the original implementation
"""

# Import everything from the old implementation
from backend_old_python_implementation import *

# Export the Flask app for deployment
__all__ = ['app']
