# Keeping extraction inside api.main (we already use PyMuPDF there).
# This file can host advanced extraction later (tables/images/ocr).
def pdf_pages_text(pdf_path: str):
    import fitz
    doc = fitz.open(pdf_path)
    return [page.get_text() for page in doc]
