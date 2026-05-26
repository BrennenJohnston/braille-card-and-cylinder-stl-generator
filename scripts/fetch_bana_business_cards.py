"""Download and rasterize the BANA Business Cards Fact Sheet (approved March 2024).

Output:
    docs/guides/_bana_source/Business_Cards_Fact_Sheet.pdf
    docs/guides/_bana_source/page_01.png ... page_NN.png

Run once (per BANA revision):
    python scripts/fetch_bana_business_cards.py

The rasterized PNGs are the visual source of truth for the verified-source
transcription at docs/guides/_bana_business_cards_verified_source.md.
Do not consume the PDF's hidden text layer (it is North American Braille
ASCII, which looks like garbled punctuation to anyone who is not a braillist
and has caused prior rewrites of our docs to drift from BANA).
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

PDF_URL = 'https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf'

DEFAULT_OUT_DIR = Path('docs/guides/_bana_source')
DEFAULT_DPI = 200


def download_pdf(url: str, dest: Path) -> None:
    if dest.exists():
        print(f'[skip] PDF already present at {dest}')
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f'[fetch] {url}')
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'braille-card-and-cylinder-stl-generator/fetch_bana'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f'[ok] wrote {len(data):,} bytes -> {dest}')


def rasterize(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    import pypdfium2 as pdfium

    scale = dpi / 72.0
    pdf = pdfium.PdfDocument(str(pdf_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, page in enumerate(pdf, start=1):
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        out_path = out_dir / f'page_{i:02d}.png'
        image.save(out_path)
        written.append(out_path)
        print(f'[ok] page {i} -> {out_path} ({image.width}x{image.height})')
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--out-dir',
        type=Path,
        default=DEFAULT_OUT_DIR,
        help='Output directory for the PDF and rasterized PNGs.',
    )
    parser.add_argument('--dpi', type=int, default=DEFAULT_DPI)
    parser.add_argument(
        '--url',
        default=PDF_URL,
        help='Override the source URL (use to pin a previously downloaded revision).',
    )
    args = parser.parse_args(argv)

    pdf_path = args.out_dir / 'Business_Cards_Fact_Sheet.pdf'
    download_pdf(args.url, pdf_path)
    pages = rasterize(pdf_path, args.out_dir, args.dpi)
    print(f'[done] {len(pages)} page(s) written to {args.out_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
