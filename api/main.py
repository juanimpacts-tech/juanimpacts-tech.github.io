import io, json, tempfile, os, uuid
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from engine.extract import pdf_pages_text
from engine.detect import build_manifest
from engine.redact import apply_redactions_pdf
from engine.manifest import save_manifest, load_manifest
from policies.evaluate import evaluate_manifest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from docx import Document
import fitz  # PyMuPDF

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="PrivyPress")

@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html>
<html><body style="font-family:system-ui;padding:2rem;max-width:720px">
<h2>PrivyPress – Upload for Redaction</h2>
<form action="/upload" method="post" enctype="multipart/form-data">
  <p><input type="file" name="file" required></p>
  <p>
    Policy profile:
    <select name="policy_profile">
      <option value="strict">strict</option>
      <option value="balanced">balanced</option>
    </select>
  </p>
  <button type="submit">Upload & Process</button>
</form>
<p>Supported: PDF, DOCX, TXT</p>
</body></html>"""

def _pdf_from_text(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    x, y = 54, height - 54
    max_width = width - 108
    for line in text.splitlines() or [""]:
        # naive wrap: split long lines into chunks
        while line:
            chunk = line
            # reportlab doesn't measure easily without stringWidth; keep it simple:
            if len(chunk) > 100:
                chunk, line = chunk[:100], chunk[100:]
            else:
                line = ""
            c.drawString(x, y, chunk)
            y -= 14
            if y < 72:
                c.showPage()
                y = height - 54
    c.save()
    return buf.getvalue()

def _convert_to_pdf_bytes(content: bytes, content_type: str) -> bytes:
    if content_type == "application/pdf":
        return content
    if content_type in ("text/plain", "text/markdown"):
        txt = content.decode("utf-8", errors="ignore")
        return _pdf_from_text(txt)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        tmp = io.BytesIO(content)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "in.docx")
            with open(path, "wb") as f: f.write(tmp.getvalue())
            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return _pdf_from_text(text)
    raise HTTPException(400, "Unsupported file type.")

class UploadOut(BaseModel):
    job_id: str
    status: str
    policy: Dict[str, Any]

@app.post("/upload", response_model=UploadOut)
async def upload(file: UploadFile = File(...), policy_profile: str = "strict"):
    if file.content_type not in {
        "application/pdf",
        "text/plain", "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }:
        raise HTTPException(400, f"Unsupported content type: {file.content_type}")

    job_id = str(uuid.uuid4())
    raw_pdf_path = os.path.join(DATA_DIR, f"{job_id}_raw.pdf")
    red_pdf_path = os.path.join(DATA_DIR, f"{job_id}_redacted.pdf")

    content = await file.read()
    pdf_bytes = _convert_to_pdf_bytes(content, file.content_type)
    with open(raw_pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # build manifest (search on each page)
    doc = fitz.open(raw_pdf_path)
    detections = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_text = page.get_text()
        page_hits = build_manifest(page_index+1, page, page_text, rules_dir="rules")
        detections.extend(page_hits)

    # stats (very simple coverage proxy)
    stats = {"total": len(detections), "coverage_estimate": 1.0 if detections else 1.0}
    manifest = {"doc_id": job_id, "detections": detections, "stats": stats}
    decision = evaluate_manifest(manifest, profile=policy_profile)
    save_manifest(job_id, manifest, decision)

    if not decision.get("allow", False):
        return UploadOut(job_id=job_id, status="blocked", policy=decision)

    apply_redactions_pdf(raw_pdf_path, manifest, red_pdf_path)
    return UploadOut(job_id=job_id, status="ready", policy=decision)

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    m = load_manifest(job_id)
    if not m: raise HTTPException(404, "Not found")
    return JSONResponse(m)

@app.get("/jobs/{job_id}/pdf")
def get_pdf(job_id: str):
    red = os.path.join(DATA_DIR, f"{job_id}_redacted.pdf")
    m = load_manifest(job_id)
    if not m or not os.path.exists(red):
        raise HTTPException(404, "Redacted PDF not found or job blocked.")
    # Double-check policy allow
    if not m.get("decision", {}).get("allow", False):
        raise HTTPException(403, "Policy gate blocked PDF release.")
    return FileResponse(red, media_type="application/pdf", filename=f"{job_id}_redacted.pdf")
