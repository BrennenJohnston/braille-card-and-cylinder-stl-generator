"""
Braille STL Generator Application Package.

This package contains the Flask application factory and modular components
for generating braille cards and cylinders as STL files.
"""

from flask import Flask
from flask_cors import CORS


def create_app(config=None):
    """
    Flask application factory.

    Args:
        config: Optional configuration dictionary to override defaults

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, static_folder='../static', template_folder='../templates')

    # Default configuration
    app.config.update(
        {
            'JSON_SORT_KEYS': False,
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max request size
        }
    )

    # Apply custom config if provided
    if config:
        app.config.update(config)

    # Setup CORS
    CORS(app)

    return app


# For backward compatibility, create a default app instance placeholder
# The actual app instance is created in backend.py
app = None


def init_app():
    """Initialize the default app instance."""
    global app
    app = create_app()
    return app
