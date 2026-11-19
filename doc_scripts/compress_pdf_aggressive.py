import sys
import fitz
import os

input_pdf = sys.argv[1]
output_pdf = sys.argv[2]

doc = fitz.open(input_pdf)
new_doc = fitz.open()

for page in doc:
    pix = page.get_pixmap(dpi=30, alpha=False)
    img_data = pix.tobytes("jpeg", jpg_quality=15)
    
    page_rect = page.rect
    new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
    new_page.insert_image(page_rect, stream=img_data)

new_doc.save(output_pdf, garbage=4, deflate=True)
new_doc.close()
doc.close()

file_size = os.path.getsize(output_pdf)
print(f"Compressed size: {file_size} bytes")
print(f"SAVED: {output_pdf}")
