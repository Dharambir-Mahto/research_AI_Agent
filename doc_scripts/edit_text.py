#!/usr/bin/env python3
"""Find and replace text in a PDF or DOCX file.
Usage: python doc_scripts/edit_text.py <file_path> <find_text> <replace_text>
"""
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    fitz = None
from docx import Document


def edit_text(file_path: str, find: str, replace: str) -> str:
    p = Path(file_path)
    if not p.is_file() and (Path("uploads") / p.name).is_file():
        p = Path("uploads") / p.name
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = p.suffix.lower()
    out = Path("uploads") / f"edited_{p.name}"

    if ext == ".pdf":
        doc = fitz.open(p)
        for page in doc:
            page = doc[page.number]
            hits = page.search_for(find)
            for r in hits:
                page.add_redact_annot(r, text=replace)
            page.apply_redactions()
        doc.save(out)
        doc.close()
        return str(out)

    elif ext == ".docx":
        d = Document(p)
        for para in d.paragraphs:
            if find in para.text:
                para.text = para.text.replace(find, replace)
        d.save(out)
        return str(out)
    else:
        raise ValueError(f"Unsupported format: {ext}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: edit_text.py <file_path> <find_text> <replace_text>")
        sys.exit(1)
    out_file = edit_text(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"SAVED: {out_file}")
