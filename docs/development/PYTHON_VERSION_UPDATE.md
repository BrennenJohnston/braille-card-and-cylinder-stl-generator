# Python Version Update for Vercel

## Issue
Vercel no longer supports Python 3.9. The build was failing with:
- "Warning: Python version "3.9" detected in pyproject.toml is not installed and will be ignored"
- "Falling back to latest installed version: 3.12"
- scipy 1.10.1 was incompatible with Python 3.12

## Solution
Updated the entire project to use Python 3.12:

### Configuration Changes
1. **vercel.json**: `"runtime": "python3.12"`
2. **pyproject.toml**:
   - `requires-python = ">=3.12"`
   - `target-version = "py312"`
   - `python_version = "3.12"` (mypy)
3. **.python-version**: `3.12`
4. **runtime.txt**: `python-3.12`

### Dependency Updates
- **scipy**: Updated from 1.10.1 to 1.11.4 (supports Python 3.12)
- All other dependencies remain compatible with Python 3.12

## Impact
- The application now uses Python 3.12 consistently across all environments
- All dependencies are compatible with Python 3.12
- Vercel deployment should now succeed

## Important Note
This change means the project now requires Python 3.12 or later for local development as well.
