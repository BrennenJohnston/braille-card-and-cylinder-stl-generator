# Vercel Deployment Fix Summary

## Issue
The Vercel deployment was failing with the error:
```
src/geos.h:15:10: fatal error: geos_c.h: No such file or directory
```

This occurred because:
1. Shapely 2.0.4 doesn't have pre-built wheels for Python 3.12
2. Vercel was defaulting to Python 3.12 due to version constraint mismatches
3. Without pre-built wheels, pip tried to build shapely from source, which requires GEOS C libraries that aren't available in Vercel's build environment

## Solution

### 1. Updated Python Version Configuration
- Set Python runtime to 3.9 across all configuration files for consistency
- Updated `vercel.json`: `"runtime": "python3.9"`
- Created `.python-version` file with `3.9`
- Created `runtime.txt` file with `python-3.9`
- Updated `pyproject.toml`: `requires-python = ">=3.9,<3.13"`

### 2. Updated Shapely Version
- Upgraded shapely from 2.0.4 to 2.0.6 for better pre-built wheel support
- Updated in all requirements files: `requirements.txt`, `requirements_vercel.txt`, and `pyproject.toml`

### 3. Forced Binary Package Installation
- Added environment variable in `vercel.json`: `"PIP_ONLY_BINARY": "shapely"`
- This prevents pip from attempting to build shapely from source

## Changes Made
1. `pyproject.toml`: Updated Python version constraint and shapely version
2. `vercel.json`: Set Python 3.9 runtime and added PIP_ONLY_BINARY env var
3. `requirements.txt` & `requirements_vercel.txt`: Updated shapely to 2.0.6
4. `.python-version`: New file specifying Python 3.9
5. `runtime.txt`: New file for additional Python version specification

## Testing
- Local smoke tests pass successfully with the updated dependencies
- All 9 tests in `test_smoke.py` pass

## Next Steps
1. Push these changes to the repository
2. Trigger a new deployment on Vercel
3. Monitor the build logs to ensure shapely installs from pre-built wheels
4. Verify all endpoints work correctly after deployment

## Expected Behavior
With these changes, Vercel should:
1. Use Python 3.9 runtime
2. Install shapely 2.0.6 from pre-built wheels without needing GEOS C libraries
3. Successfully complete the build and deployment process
