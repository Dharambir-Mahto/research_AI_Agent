"""
Compress a PDF file using PyMuPDF stream optimization, deflation, and garbage collection.
Usage: python compress_pdf.py <input_pdf> [output_pdf]
"""
import sys
from pathlib import Path
import fitz


def compress_pdf(input_path: str, output_path: str = None) -> str:
    inp = Path(input_path)
    if not inp.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not output_path:
        output_path = inp.parent / f"compressed_{inp.name}"
    else:
        output_path = Path(output_path)

    doc = fitz.open(str(inp))
    doc.save(str(output_path), garbage=4, deflate=True, clean=True)
    doc.close()

    orig_size = inp.stat().st_size
    new_size = output_path.stat().st_size
    print(f"Compressed {inp.name} ({orig_size} bytes -> {new_size} bytes)")
    print(f"SAVED: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compress_pdf.py <input_pdf> [output_pdf]")
        sys.exit(1)
    in_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    compress_pdf(in_file, out_file)
