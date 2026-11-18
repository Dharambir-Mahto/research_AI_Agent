#!/usr/bin/env python3
"""Revert/restore pages into a target PDF from a source/original PDF document.
Usage: python doc_scripts/revert_pages.py <target_pdf> <source_pdf> <page_numbers...>
Example: python doc_scripts/revert_pages.py uploads/trimmed_Ajay.pdf uploads/Ajay.pdf 3
"""
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz


def revert_pages(target_path: str, source_path: str, pages: list[int]) -> str:
    t = Path(target_path)
    if not t.is_file() and (Path("uploads") / t.name).is_file():
        t = Path("uploads") / t.name

    s = Path(source_path)
    if not s.is_file() and (Path("uploads") / s.name).is_file():
        s = Path("uploads") / s.name

    if not t.is_file():
        raise FileNotFoundError(f"Target PDF not found: {target_path}")
    if not s.is_file():
        raise FileNotFoundError(f"Source PDF not found: {source_path}")

    target_doc = fitz.open(t)
    source_doc = fitz.open(s)

    for p_num in sorted(pages):
        idx = p_num - 1
        if 0 <= idx < source_doc.page_count:
            pos = min(idx, target_doc.page_count)
            target_doc.insert_pdf(source_doc, from_page=idx, to_page=idx, start_at=pos)

    clean_name = t.name
    for prefix in ["trimmed_", "edited_", "signed_"]:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]

    out = Path("uploads") / f"reverted_{clean_name}"
    target_doc.save(out)
    target_doc.close()
    source_doc.close()
    return str(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: revert_pages.py <target_pdf> [source_pdf] <page1> [page2 ...]")
        sys.exit(1)
    tgt = sys.argv[1]
    if len(sys.argv) >= 4 and (sys.argv[2].lower().endswith(".pdf") or not sys.argv[2].isdigit()):
        src = sys.argv[2]
        p_nums = [int(x) for x in sys.argv[3:] if x.isdigit()]
    else:
        # Inferred source_pdf
        p_nums = [int(x) for x in sys.argv[2:] if x.isdigit()]
        clean = Path(tgt).name
        for prefix in ["trimmed_", "reverted_", "signed_"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        cand = Path("uploads") / clean
        if cand.is_file():
            src = str(cand)
        else:
            base_cand = Path("uploads") / clean.replace("edited_", "")
            if base_cand.is_file():
                src = str(base_cand)
            else:
                src = tgt

    out_file = revert_pages(tgt, src, p_nums)
    print(f"SAVED: {out_file}")
