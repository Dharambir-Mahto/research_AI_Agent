import pymupdf

pdf_path = "uploads/reverted_Ajay_Pandey_2.pdf"
doc = pymupdf.open(pdf_path)

find_str = "Responsibilities at smartData"

for page_num in range(len(doc)):
    page = doc[page_num]
    text_instances = page.search_for(find_str)
    if text_instances:
        rect = text_instances[0]
        page_rect = page.rect
        redact_rect = pymupdf.Rect(0, rect.y0 - 5, page_rect.width, page_rect.height)
        page.add_redact_annot(redact_rect)
        page.apply_redactions()
        break

output_path = "uploads/edited_Ajay_Pandey_2.pdf"
doc.save(output_path)
doc.close()
print("SAVED:", output_path)
