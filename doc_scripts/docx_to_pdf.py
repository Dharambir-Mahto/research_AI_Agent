import fitz # PyMuPDF
from docx import Document
import subprocess
import os

docx_path = "uploads/merged_AI_Governance_Ajay_Pandey.docx"
output_pdf_path = "uploads/merged_AI_Governance_Ajay_Pandey.pdf"

# Convert docx to pdf using libreoffice
try:
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", docx_path, "--outdir", "uploads"], check=True)
    print(f"SAVED: {output_pdf_path}")
except Exception as e:
    print("Libreoffice conversion error:", e)
    # Fallback: using reportlab or another method if needed, but libreoffice is usually available.
    # Let's verify if the file was created
    if os.path.exists(output_pdf_path):
        print(f"SAVED: {output_pdf_path}")
    else:
        # If libreoffice output filename differs slightly
        base = os.path.splitext(os.path.basename(docx_path))[0]
        gen = os.path.join("uploads", base + ".pdf")
        if os.path.exists(gen):
            if gen != output_pdf_path:
                os.rename(gen, output_pdf_path)
            print(f"SAVED: {output_pdf_path}")
        else:
            raise RuntimeError("Could not convert docx to pdf")
