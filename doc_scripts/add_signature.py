#!/usr/bin/env python3
"""Stamp a signature image onto a PDF document page.
Usage: python doc_scripts/add_signature.py <pdf_path> <image_path> [page_num] [x] [y]
"""
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    fitz = None


def add_signature(pdf_path: str, image_path: str, page: int = 1, x: float = 100, y: float = 650) -> str:
    p = Path(pdf_path)
    if not p.is_file() and (Path("uploads") / p.name).is_file():
        p = Path("uploads") / p.name
    sig = Path(image_path)
    if not sig.is_file() and (Path("uploads") / sig.name).is_file():
        sig = Path("uploads") / sig.name

    if not p.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not sig.is_file():
        raise FileNotFoundError(f"Signature image not found: {image_path}")

    doc = fitz.open(p)
    page_idx = max(0, min(page - 1, doc.page_count - 1))
    pg = doc[page_idx]
    rect = fitz.Rect(x, y, x + 150, y + 60)
    pg.insert_image(rect, filename=str(sig))
    out = Path("uploads") / f"signed_{p.name}"
    doc.save(out)
    doc.close()
    return str(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: add_signature.py <pdf_path> <image_path> [page_num] [x] [y]")
        sys.exit(1)
    pg = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 1
    px = float(sys.argv[4]) if len(sys.argv) > 4 else 100.0
    py = float(sys.argv[5]) if len(sys.argv) > 5 else 650.0
    out_file = add_signature(sys.argv[1], sys.argv[2], pg, px, py)
    print(f"SAVED: {out_file}")
