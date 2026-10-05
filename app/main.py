"""Stage 0 + REST API. Run: uvicorn app.main:app --reload"""
import datetime as dt, json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from . import db
from .pipeline import run_pipeline

app = FastAPI(title="DocExtract")
UPLOADS = Path(__file__).parent.parent / "data" / "uploads"
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png"}

@app.post("/api/documents")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type {ext}")
    data = await file.read()
    record = run_pipeline(data, file.filename)
    doc_id = db.save(record)
    (UPLOADS / f"{doc_id}{ext}").write_bytes(data)
    return db.get(doc_id)

@app.get("/api/documents")
def list_docs():
    return [{k: r.get(k) for k in ("id", "filename", "doc_type", "created_at", "quality")}
            | {"vendor": (r.get("data") or {}).get("vendor_name"),
               "total": (r.get("data") or {}).get("total")} for r in db.list_all()]

@app.get("/api/documents/{doc_id}")
def get_doc(doc_id: str):
    r = db.get(doc_id)
    if not r: raise HTTPException(404, "Not found")
    return r

@app.put("/api/documents/{doc_id}")
def correct(doc_id: str, data: dict):
    """Human review: save corrected data and clear the review flag."""
    r = db.get(doc_id)
    if not r: raise HTTPException(404, "Not found")
    r["data"] = data
    r["quality"]["needs_review"] = False
    r["quality"]["reviewed"] = True
    db.save(r)
    return r

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
