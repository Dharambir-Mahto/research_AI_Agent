import sys
from pypdf import PdfReader

pdf_path = "uploads/ClaimShield_RAG_Architecture_Updated.pdf"
reader = PdfReader(pdf_path)

text = ""
for page in reader.pages[:3]:
    text += page.extract_text() + "\n"

print("--- EXRACTED TEXT SUMMARY ---")
print(text[:1500])
