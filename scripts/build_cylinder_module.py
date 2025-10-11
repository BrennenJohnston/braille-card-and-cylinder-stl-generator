"""
Build complete app/geometry/cylinder.py module from extracted functions
"""

from pathlib import Path

# Read extracted functions
extracted_path = Path(__file__).parent / 'extracted_cylinder_funcs.txt'
extracted_content = extracted_path.read_text(encoding='utf-8')

# Remove comment headers
lines = extracted_content.split('\n')
clean_lines = []
for line in lines:
    # Skip separator comments and line number comments
    if line.strip().startswith('# ===') or (line.strip().startswith('# ') and '(lines' in line):
        continue
    clean_lines.append(line)

functions_code = '\n'.join(clean_lines).strip()

# Build complete module with header and imports
module_content = '''"""
Cylinder geometry generation.

This module handles generation of cylindrical braille surfaces, including
shell creation, dot mapping, and recess operations.
"""

import json
from datetime import datetime

import numpy as np
import trimesh
from shapely.geometry import Polygon as ShapelyPolygon
from trimesh.creation import extrude_polygon

# Note: These functions have dependencies that will be resolved via imports in backend.py:
# - create_braille_dot from app.geometry.dot_shapes
# - braille_to_dots from app.utils
# - _build_character_polygon from backend (temporary, will move in next batch)
# - CardSettings from app.models


'''

module_content += functions_code

# Write to app/geometry/cylinder.py
output_path = Path(__file__).parent.parent / 'app' / 'geometry' / 'cylinder.py'
output_path.write_text(module_content, encoding='utf-8')

print(f'✓ Built complete cylinder.py module')
print(f'  Total size: {len(module_content)} characters')
print(f'  Total lines: {len(module_content.splitlines())}')
print(f'  Location: {output_path}')

