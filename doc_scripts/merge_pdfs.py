import os
import fitz  # PyMuPDF

pdf1 = "uploads/04_fictional_followup_labs_medication_record.pdf"
pdf2 = "uploads/20260617_090239_NIST.AI.600-1.pdf"
output_path = "uploads/merged_medication_record_nist.pdf"

merged_doc = fitz.open()

for pdf_path in [pdf1, pdf2]:
    with fitz.open(pdf_path) as doc:
        merged_doc.insert_pdf(doc)

os.makedirs("uploads", exist_ok=True)
merged_doc.save(output_path)
merged_doc.close()

print(f"SAVED: {output_path}")
