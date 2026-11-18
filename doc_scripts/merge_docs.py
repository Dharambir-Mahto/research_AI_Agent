import os
from pypdf import PdfReader, PdfWriter
from docx import Document
from pdf2docx import Converter
import tempfile

pdf_path = "uploads/AI_Governance_Compliance_Report.pdf"
docx_path = "uploads/Ajay_Pandey_2.docx"
output_pdf_path = "uploads/merged_AI_Governance_Ajay_Pandey.pdf"

# We can merge them into a single PDF. First, convert the docx to pdf using pdf2docx or similar, or convert both to a unified format.
# Let's convert docx to a temporary pdf, then merge the two pdfs.

temp_docx_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
temp_docx_pdf_path = temp_docx_pdf.name
temp_docx_pdf.close()

# Convert docx to pdf using python-docx/libreoffice or reportlab, or pdf2docx isn't docx->pdf directly (pdf2docx is pdf->docx).
# Wait, docx2pdf works on Windows/macOS, but on Linux we can use libreoffice or python-docx to generate text/elements into a reportlab PDF, OR convert pdf to docx? Wait, we have pdf and docx. Let's convert the pdf to docx and merge docx, OR convert docx to pdf.
# Let's check if libreoffice is available.
import subprocess

def convert_docx_to_pdf(docx_in, pdf_out):
    try:
        subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", docx_in, "--outdir", os.path.dirname(pdf_out)], check=True)
        # libreoffice names the output same as input but .pdf
        base = os.path.splitext(os.path.basename(docx_in))[0]
        generated = os.path.join(os.path.dirname(pdf_out), base + ".pdf")
        if generated != pdf_out:
            os.rename(generated, pdf_out)
        return True
    except Exception as e:
        print("Libreoffice conversion failed:", e)
        return False

success = convert_docx_to_pdf(docx_path, temp_docx_pdf_path)

if success:
    writer = PdfWriter()
    # Read first PDF
    reader1 = PdfReader(pdf_path)
    for page in reader1.pages:
        writer.add_page(page)
    
    # Read converted docx PDF
    reader2 = PdfReader(temp_docx_pdf_path)
    for page in reader2.pages:
        writer.add_page(page)
        
    with open(output_pdf_path, "wb") as f:
        writer.write(f)
    
    os.remove(temp_docx_pdf_path)
    print(f"SAVED: {output_pdf_path}")
else:
    # Fallback: convert PDF to docx or combine text using python-docx
    print("Fallback: combining into Word document instead")
    output_docx_path = "uploads/merged_AI_Governance_Ajay_Pandey.docx"
    doc_target = Document(docx_path)
    
    # Extract text from PDF and add to docx
    reader = PdfReader(pdf_path)
    doc_target.add_page_break()
    doc_target.add_heading("AI Governance Compliance Report", level=1)
    for page in reader.pages:
        text = page.extract_text()
        if text:
            doc_target.add_paragraph(text)
            
    doc_target.save(output_docx_path)
    print(f"SAVED: {output_docx_path}")
