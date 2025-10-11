"""
Remove all cylinder functions from backend.py and replace with import comments
"""

import re
from pathlib import Path

# Read backend.py
backend_path = Path(__file__).parent.parent / 'backend.py'
lines = backend_path.read_text(encoding='utf-8').splitlines(keepends=True)

# Functions to remove (in order)
funcs_to_remove = [
    ('create_cylinder_shell', 101),
    ('create_cylinder_triangle_marker', 103),
    ('create_cylinder_line_end_marker', 85),
    ('create_cylinder_character_shape', 125),
    ('create_cylinder_braille_dot', 32),
    ('generate_cylinder_stl', 242),
    ('generate_cylinder_counter_plate', 442),
]

# Find and mark functions for removal
removed_count = 0
for func_name, expected_lines in funcs_to_remove:
    # Find function start
    pattern = rf'^def {re.escape(func_name)}\('
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            # Replace function with comment
            comment = f'# {func_name} now imported from app.geometry.cylinder\n\n'

            # Find next function/class/route
            j = i + 1
            while j < len(lines):
                if re.match(r'^(def |class |@app\.route)', lines[j]):
                    break
                j += 1

            actual_lines = j - i
            print(f'✓ Found {func_name}: line {i + 1}, removing {actual_lines} lines (expected ~{expected_lines})')

            # Remove the function (replace lines i to j with comment)
            lines = lines[:i] + [comment] + lines[j:]
            removed_count += 1
            break

# Write updated backend.py
backend_path.write_text(''.join(lines), encoding='utf-8')

print(f'\n✓ Removed {removed_count} functions from backend.py')
print(f'Updated file: {backend_path}')
