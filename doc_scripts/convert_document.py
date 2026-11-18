#!/usr/bin/env python3
"""Convert document between PDF, DOCX, and Markdown formats.
Usage: python doc_scripts/convert_document.py <source_path> <target_format>
"""
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    fitz = None
from docx import Document


def convert_document(source_path: str, target_format: str) -> str:
    p = Path(source_path)
    if not p.is_file() and (Path("uploads") / p.name).is_file():
        p = Path("uploads") / p.name
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {source_path}")

    tgt = target_format.lower().lstrip(".")
    out = Path("uploads") / f"{p.stem}.{tgt}"

    if p.suffix == ".pdf" and tgt == "docx":
        doc = fitz.open(p)
        d = Document()
        for page in doc:
            d.add_paragraph(page.get_text())
        d.save(out)
        doc.close()
    elif p.suffix == ".docx" and tgt == "pdf":
        d = Document(p)
        doc = fitz.open()
        page = doc.new_page()
        y = 50
        for para in d.paragraphs:
            page.insert_text((50, y), para.text[:90])
            y += 15
            if y > 780:
                page = doc.new_page()
                y = 50
        doc.save(out)
        doc.close()
    elif p.suffix in {".md", ".txt"} and tgt == "pdf":
        doc = fitz.open()
        page = doc.new_page()
        y = 50
        for line in p.read_text(encoding="utf-8").splitlines():
            page.insert_text((50, y), line[:90])
            y += 15
            if y > 780:
                page = doc.new_page()
                y = 50
        doc.save(out)
        doc.close()
    elif p.suffix in {".md", ".txt"} and tgt == "docx":
        d = Document()
        for line in p.read_text(encoding="utf-8").splitlines():
            d.add_paragraph(line)
        d.save(out)
    else:
        raise ValueError(f"No converter available for: {p.suffix} -> {tgt}")

    return str(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: convert_document.py <source_path> <target_format>")
        sys.exit(1)
    out_file = convert_document(sys.argv[1], sys.argv[2])
    print(f"SAVED: {out_file}")
