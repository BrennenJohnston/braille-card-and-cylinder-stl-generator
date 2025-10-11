import os
import sys

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

from backend import app  # noqa: E402

# For Vercel deployment - DISABLED for baseline
# app.debug = False

if __name__ == '__main__':
    app.run()
