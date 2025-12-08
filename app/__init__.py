"""
Braille STL Generator Application Package.

This package contains the Flask application factory and modular components
for generating braille cards and cylinders as STL files.
"""

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# Planned for future use: Flask application factory pattern
# Currently unused - application uses backend.py directly
# These functions are reserved for future refactoring to improve modularity
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

    # Setup rate limiting
    limiter = Limiter(app=app, key_func=get_remote_address, default_limits=['100 per hour'], storage_uri='memory://')

    # Store limiter on app for access in routes
    app.limiter = limiter

    return app


# For backward compatibility, create a default app instance
# This will be replaced by create_app() during refactoring
app = None
limiter = None


# Planned for future use: Initialize default app instance
def init_app():
    """Initialize the default app instance."""
    global app, limiter
    app = create_app()
    limiter = app.limiter
    return app
