#!/usr/bin/env python3
"""Remove specified 1-indexed pages from a PDF document.
Usage: python doc_scripts/remove_pages.py <pdf_path> <page_numbers...>
Example: python doc_scripts/remove_pages.py uploads/sample.pdf 3
"""
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz


def remove_pages(pdf_path: str, pages: list[int]) -> str:
    p = Path(pdf_path)
    if not p.is_file():
        p_up = Path("uploads") / p.name
        if p_up.is_file():
            p = p_up
        else:
            raise FileNotFoundError(f"File not found: {pdf_path}")

    doc = fitz.open(p)
    total = doc.page_count
    valid = [n for n in sorted(set(pages), reverse=True) if 1 <= n <= total]
    if not valid:
        doc.close()
        raise ValueError(f"No valid pages to remove. Total pages: {total}")
    if len(valid) >= total:
        doc.close()
        raise ValueError(f"Cannot remove all {total} pages.")

    for n in valid:
        doc.delete_page(n - 1)

    out = Path("uploads") / f"trimmed_{p.name}"
    doc.save(out)
    doc.close()
    return str(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: remove_pages.py <pdf_path> <page1> [page2 ...]")
        sys.exit(1)
    target = sys.argv[1]
    page_nums = [int(x) for x in sys.argv[2:] if x.isdigit()]
    out_file = remove_pages(target, page_nums)
    print(f"SAVED: {out_file}")
