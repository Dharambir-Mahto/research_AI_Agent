import fitz # PyMuPDF is installed!
from docx import Document

pdf_path = "uploads/AI_Governance_Compliance_Report.pdf"
docx_path = "uploads/Ajay_Pandey_2.docx"
output_docx_path = "uploads/merged_AI_Governance_Ajay_Pandey.docx"

# Load the docx document
doc = Document(docx_path)

# Add a section break or page break
doc.add_page_break()
doc.add_heading("AI Governance Compliance Report", level=1)

# Extract text from PDF using PyMuPDF and append to docx
pdf_doc = fitz.open(pdf_path)
for page_num in range(len(pdf_doc)):
    page = pdf_doc[page_num]
    text = page.get_text()
    if text.strip():
        doc.add_paragraph(text)

doc.save(output_docx_path)
print(f"SAVED: {output_docx_path}")
