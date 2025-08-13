import fitz  # PyMuPDF

def apply_redactions_pdf(pdf_in: str, manifest: dict, pdf_out: str):
    doc = fitz.open(pdf_in)
    for d in manifest.get("detections", []):
        if d.get("action") != "redact": 
            continue
        page = doc[d["page"] - 1]
        x0, y0, x1, y1 = d["bbox"]
        rect = fitz.Rect(x0, y0, x1, y1)
        page.add_redact_annot(rect, text="", fill=(0,0,0))
    for p in doc:
        p.apply_redactions()
    doc.save(pdf_out, deflate=True, garbage=4, clean=True)
