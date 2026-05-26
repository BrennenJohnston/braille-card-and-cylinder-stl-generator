"""Extract text from the BANA Business Cards Fact Sheet PDF and convert
braille-encoded lines (in North American Braille ASCII / BRF) into Unicode
braille (U+2800..U+283F) for use in the verified-source transcription.

This is a one-shot working tool. Run after fetch_bana_business_cards.py.

Output: docs/guides/_bana_source/_extracted_unicode.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium

# Canonical Library of Congress / ICEB BRF mapping (ASCII char -> dots tuple).
# Dot numbering: 1=top-left, 2=mid-left, 3=bottom-left, 4=top-right, 5=mid-right,
# 6=bottom-right. Unicode codepoint = 0x2800 + sum(1<<(d-1) for d in dots).
_BRF: dict[str, tuple[int, ...]] = {
    ' ': (),
    'A': (1,),
    'B': (1, 2),
    'C': (1, 4),
    'D': (1, 4, 5),
    'E': (1, 5),
    'F': (1, 2, 4),
    'G': (1, 2, 4, 5),
    'H': (1, 2, 5),
    'I': (2, 4),
    'J': (2, 4, 5),
    'K': (1, 3),
    'L': (1, 2, 3),
    'M': (1, 3, 4),
    'N': (1, 3, 4, 5),
    'O': (1, 3, 5),
    'P': (1, 2, 3, 4),
    'Q': (1, 2, 3, 4, 5),
    'R': (1, 2, 3, 5),
    'S': (2, 3, 4),
    'T': (2, 3, 4, 5),
    'U': (1, 3, 6),
    'V': (1, 2, 3, 6),
    'W': (2, 4, 5, 6),
    'X': (1, 3, 4, 6),
    'Y': (1, 3, 4, 5, 6),
    'Z': (1, 3, 5, 6),
    '1': (2,),
    '2': (2, 3),
    '3': (2, 5),
    '4': (2, 5, 6),
    '5': (2, 6),
    '6': (2, 3, 5),
    '7': (2, 3, 5, 6),
    '8': (2, 3, 6),
    '9': (3, 5),
    '0': (3, 5, 6),
    '&': (1, 2, 3, 4, 6),
    '=': (1, 2, 3, 4, 5, 6),
    '(': (1, 2, 3, 5, 6),
    '!': (2, 3, 4, 6),
    ')': (2, 3, 4, 5, 6),
    '*': (1, 6),
    '<': (1, 2, 6),
    '%': (1, 4, 6),
    '?': (1, 4, 5, 6),
    ':': (1, 5, 6),
    '$': (1, 2, 4, 6),
    ']': (1, 2, 4, 5, 6),
    '\\': (1, 2, 5, 6),
    '[': (2, 4, 6),
    '.': (4, 6),
    '+': (3, 4, 6),
    ',': (6,),
    ';': (5, 6),
    '-': (3, 6),
    "'": (3,),
    '`': (4,),
    '"': (5,),
    '^': (4, 5),
    '_': (4, 5, 6),
    '@': (4,),
    '#': (3, 4, 5, 6),
    '>': (3, 4, 5),
    '/': (3, 4),
}


def _dots_to_codepoint(dots: tuple[int, ...]) -> int:
    cp = 0x2800
    for d in dots:
        cp |= 1 << (d - 1)
    return cp


_NABT_TO_UNICODE: dict[str, str] = {ch: chr(_dots_to_codepoint(dots)) for ch, dots in _BRF.items()}


def to_unicode_braille(line: str) -> str:
    out: list[str] = []
    has_brf = False
    for ch in line:
        upper = ch.upper()
        if upper in _NABT_TO_UNICODE and upper != ' ':
            out.append(_NABT_TO_UNICODE[upper])
            has_brf = True
        elif ch == ' ':
            out.append('\u2800')  # blank braille cell (visible spacer)
        else:
            out.append(ch)
    return ''.join(out) if has_brf else line


def main() -> int:
    pdf_path = Path('docs/guides/_bana_source/Business_Cards_Fact_Sheet.pdf')
    out_path = Path('docs/guides/_bana_source/_extracted_unicode.txt')
    pdf = pdfium.PdfDocument(str(pdf_path))
    out_lines: list[str] = []
    for i, page in enumerate(pdf, start=1):
        out_lines.append(f'=== PAGE {i} ===')
        raw = page.get_textpage().get_text_range()
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                out_lines.append('')
                continue
            converted = to_unicode_braille(line)
            if converted != line:
                out_lines.append(f'NABT: {line.rstrip()}')
                out_lines.append(f'BRL : {converted.rstrip()}')
            else:
                out_lines.append(line.rstrip())
    out_path.write_text('\n'.join(out_lines) + '\n', encoding='utf-8')
    print(f'wrote {out_path} ({sum(1 for _ in out_lines)} lines)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
