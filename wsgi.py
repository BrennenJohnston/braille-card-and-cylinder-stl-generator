import logging
import os
import sys

# Configure basic logging for startup diagnostics
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_startup_logger = logging.getLogger('wsgi_startup')

# Ensure Vercel's installed site-packages are on sys.path
# Try common builder locations under /var/task and /var/lang
_candidates = [
    '/var/task/.python_packages/lib/site-packages',
    '/var/task/python_modules/lib/site-packages',
    '/var/task/venv/lib/python3.12/site-packages',  # keep 3.12 in case runtime mismatch
    '/var/task/venv/lib/python3.11/site-packages',
    '/var/task/venv/lib/python3.10/site-packages',
    '/var/task/venv/lib/python3.9/site-packages',
    '/var/lang/lib/python3.12/site-packages',  # keep 3.12 in case runtime mismatch
    '/var/lang/lib/python3.11/site-packages',
    '/var/lang/lib/python3.10/site-packages',
    '/var/lang/lib/python3.9/site-packages',
]
for p in _candidates:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.append(p)

# Add vendored dependencies (installed to ./python during buildCommand)
_vendor = os.path.join(os.path.dirname(__file__), 'python')
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)


# Diagnostic: Check manifold3d availability at startup
def _check_manifold3d():
    """Check if manifold3d is importable and log the result."""
    try:
        import manifold3d

        _startup_logger.info(f'manifold3d AVAILABLE - version: {getattr(manifold3d, "__version__", "unknown")}')
        return True
    except ImportError as e:
        _startup_logger.error(f'manifold3d IMPORT FAILED (ImportError): {e}')
        return False
    except Exception as e:
        _startup_logger.error(f'manifold3d IMPORT FAILED ({type(e).__name__}): {e}')
        return False


# Run diagnostic at module load
_manifold_available = _check_manifold3d()
_startup_logger.info(f'Boolean backend status: manifold3d={"available" if _manifold_available else "NOT available"}')

from backend import app  # noqa: E402

# For Vercel deployment - DISABLED for baseline
# app.debug = False

if __name__ == '__main__':
    app.run()
