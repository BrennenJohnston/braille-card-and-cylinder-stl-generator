"""
Pytest configuration and fixtures for smoke tests.
"""

import os
import sys

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope='session')
def app():
    """
    Provide a Flask app instance for testing.
    """
    import backend

    # Disable rate limiting for tests
    backend.limiter.enabled = False
    return backend.app


@pytest.fixture(scope='session')
def client(app):
    """
    Provide a Flask test client.
    """
    return app.test_client()
