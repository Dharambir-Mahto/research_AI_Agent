import fitz # PyMuPDF
import subprocess
import os

pdf_original = "uploads/AI_Governance_Compliance_Report.pdf"
docx_original = "uploads/Ajay_Pandey_2.docx"
temp_pdf_from_docx = "uploads/temp_ajay_pandey.pdf"
output_pdf_path = "uploads/merged_AI_Governance_Ajay_Pandey_direct.pdf"

# Convert docx to pdf using libreoffice without any modifications
subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", docx_original, "--outdir", "uploads"], check=True)
base = os.path.splitext(os.path.basename(docx_original))[0]
generated_pdf = os.path.join("uploads", base + ".pdf")
if generated_pdf != temp_pdf_from_docx:
    if os.path.exists(temp_pdf_from_docx):
        os.remove(temp_pdf_from_docx)
    os.rename(generated_pdf, temp_pdf_from_docx)

# Now merge the original AI_Governance_Compliance_Report.pdf and the generated temp_pdf_from_docx using PyMuPDF
merged_pdf = fitz.open()

doc1 = fitz.open(pdf_original)
doc2 = fitz.open(temp_pdf_from_docx)

merged_pdf.insert_pdf(doc1)
merged_pdf.insert_pdf(doc2)

merged_pdf.save(output_pdf_path)
merged_pdf.close()
doc1.close()
doc2.close()

if os.path.exists(temp_pdf_from_docx):
    os.remove(temp_pdf_from_docx)

print(f"SAVED: {output_pdf_path}")
