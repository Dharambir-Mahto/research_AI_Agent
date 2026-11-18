import sys
import fitz  # PyMuPDF

pdf_path = "uploads/ClaimShield_RAG_Architecture_Updated.pdf"
doc = fitz.open(pdf_path)

text = ""
for page in doc:
    text += page.get_text() + "\n"

print("--- EXTRACTED TEXT ---")
print(text[:2000])
