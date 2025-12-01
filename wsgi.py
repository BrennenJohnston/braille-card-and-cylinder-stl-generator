import logging
import platform
import sys

# Configure basic logging for startup diagnostics
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_startup_logger = logging.getLogger('wsgi_startup')


def _log_platform_info():
    """Log platform information to help diagnose binary compatibility issues."""
    _startup_logger.info(f'Python version: {sys.version}')
    _startup_logger.info(f'Platform: {platform.platform()}')
    _startup_logger.info(f'Machine: {platform.machine()}')
    try:
        import subprocess

        result = subprocess.run(['ldd', '--version'], capture_output=True, text=True)
        glibc_info = result.stdout.split('\n')[0] if result.stdout else result.stderr.split('\n')[0]
        _startup_logger.info(f'glibc version: {glibc_info}')
    except Exception as e:
        _startup_logger.info(f'Could not determine glibc version: {e}')


def _check_manifold3d():
    """Check if manifold3d is importable and log detailed diagnostics."""
    try:
        import manifold3d

        _startup_logger.info(f'manifold3d AVAILABLE - version: {getattr(manifold3d, "__version__", "unknown")}')
        return True
    except ImportError as e:
        _startup_logger.error(f'manifold3d IMPORT FAILED (ImportError): {e}')
        # Try to get more details about the import failure
        try:
            import importlib.util

            spec = importlib.util.find_spec('manifold3d')
            if spec is None:
                _startup_logger.error('manifold3d package is not installed')
            else:
                _startup_logger.error(f'manifold3d found at: {spec.origin}')
        except Exception as spec_e:
            _startup_logger.error(f'Could not check manifold3d spec: {spec_e}')
        return False
    except Exception as e:
        _startup_logger.error(f'manifold3d IMPORT FAILED ({type(e).__name__}): {e}')
        return False


# Run diagnostics at module load
_log_platform_info()
_manifold_available = _check_manifold3d()
_startup_logger.info(f'Boolean backend status: manifold3d={"available" if _manifold_available else "NOT available"}')

from backend import app  # noqa: E402

# For Vercel deployment - DISABLED for baseline
# app.debug = False

if __name__ == '__main__':
    app.run()
