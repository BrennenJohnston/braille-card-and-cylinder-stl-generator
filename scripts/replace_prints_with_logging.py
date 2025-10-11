"""
Replace print statements with appropriate logging calls.

This script intelligently replaces print() with logger calls based on content:
- print('DEBUG: ...') → logger.debug('...')
- print('WARNING: ...') → logger.warning('...')
- print('ERROR: ...') → logger.error('...')
- print('INFO: ...') or success messages → logger.info('...')
- Others → logger.info(...)
"""

import re
from pathlib import Path


def classify_print(content: str) -> str:
    """Determine appropriate log level based on print content."""
    content_upper = content.upper()
    
    if 'DEBUG:' in content_upper or content.startswith('DEBUG:'):
        return 'debug'
    elif 'WARNING:' in content_upper or 'WARN' in content_upper or '⚠' in content:
        return 'warning'
    elif 'ERROR:' in content_upper or 'FAIL' in content_upper:
        return 'error'
    elif '✓' in content or 'SUCCESS' in content_upper or 'COMPLETED' in content_upper:
        return 'info'
    elif 'Creating' in content or 'Generated' in content or 'Grid' in content:
        return 'info'
    else:
        return 'info'  # Default


def replace_print_in_line(line: str) -> tuple[str, bool]:
    """
    Replace a print statement with logging call.
    Returns (new_line, was_replaced).
    """
    # Match print('...')  or print(f'...')
    match = re.match(r'^(\s*)print\((f?[\'"])(.*?)([\'"])\)(.*)$', line)
    if not match:
        return line, False
    
    indent, quote_prefix, content, quote_suffix, rest = match.groups()
    
    # Determine log level
    level = classify_print(content)
    
    # Remove DEBUG:/WARNING:/ERROR: prefixes as they're redundant with log level
    clean_content = content
    for prefix in ['DEBUG: ', 'WARNING: ', 'ERROR: ', 'INFO: ', '⚠ ', '✓ ']:
        if clean_content.startswith(prefix):
            clean_content = clean_content[len(prefix):]
            break
    
    # Build new line
    new_line = f'{indent}logger.{level}({quote_prefix}{clean_content}{quote_suffix}){rest}\n'
    return new_line, True


def process_file(filepath: Path) -> int:
    """
    Process a file and replace print statements with logging.
    Returns count of replacements.
    """
    lines = filepath.read_text(encoding='utf-8').splitlines(keepends=True)
    new_lines = []
    replacements = 0
    
    for line in lines:
        new_line, replaced = replace_print_in_line(line)
        new_lines.append(new_line)
        if replaced:
            replacements += 1
    
    if replacements > 0:
        filepath.write_text(''.join(new_lines), encoding='utf-8')
    
    return replacements


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    
    files_to_process = [
        project_root / 'backend.py',
        project_root / 'app' / 'geometry' / 'cylinder.py',
        project_root / 'app' / 'models.py',
    ]
    
    total_replacements = 0
    for filepath in files_to_process:
        if filepath.exists():
            count = process_file(filepath)
            print(f'✓ {filepath.name}: {count} print statements replaced')
            total_replacements += count
        else:
            print(f'✗ {filepath.name}: not found')
    
    print(f'\nTotal: {total_replacements} print statements replaced with logging')

