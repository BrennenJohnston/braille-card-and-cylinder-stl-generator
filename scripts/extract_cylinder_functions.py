"""
Helper script to extract all cylinder-related functions from backend.py
and prepare them for app/geometry/cylinder.py
"""

import re
from pathlib import Path

# Read backend.py
backend_path = Path(__file__).parent.parent / 'backend.py'
content = backend_path.read_text(encoding='utf-8')
lines = content.splitlines(keepends=True)

# Functions to extract (in order they appear)
cylinder_functions = [
    'create_cylinder_shell',
    'create_cylinder_triangle_marker',
    'create_cylinder_line_end_marker',
    'create_cylinder_character_shape',
    'create_cylinder_braille_dot',
    'generate_cylinder_stl',
    'generate_cylinder_counter_plate',
]

# Extract each function
extracted = []
for func_name in cylinder_functions:
    # Find function start
    pattern = rf'^def {re.escape(func_name)}\('
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            # Find function end (next def/class/@app.route/if __name__)
            func_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # Check if we've hit the next top-level definition
                if re.match(r'^(def |class |@app\.route|if __name__)', next_line):
                    break
                func_lines.append(next_line)
                j += 1

            # Join and store
            func_text = ''.join(func_lines)
            extracted.append((func_name, i + 1, j + 1, len(func_lines), func_text))
            print(f'✓ Extracted {func_name}: lines {i + 1}-{j}, {len(func_lines)} lines')
            break

# Write summary
print(f'\nTotal functions extracted: {len(extracted)}')
print(f'Total lines: {sum(e[3] for e in extracted)}')

# Save extracted functions to a temporary file
output_path = Path(__file__).parent.parent / 'scripts' / 'extracted_cylinder_funcs.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n\n# ' + '=' * 80 + '\n\n')
    for name, start, end, count, text in extracted:
        f.write(f'# {name} (lines {start}-{end}, {count} lines)\n')
        f.write('# ' + '=' * 80 + '\n\n')
        f.write(text)
        f.write('\n\n')

print(f'\nExtracted functions saved to: {output_path}')
