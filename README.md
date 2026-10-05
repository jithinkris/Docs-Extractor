# DocExtract

Upload an invoice or receipt (PDF/JPG/PNG) -> OCR -> classify -> sections -> LLM extraction -> Pydantic validation -> confidence -> JSON store -> REST API + UI.

## Setup
    sudo apt install tesseract-ocr        # or: brew install tesseract
    pip install -r requirements.txt
    export GROQ_API_KEY=...
    streamlit run streamlit_app.py        # Streamlit UI (side-by-side review)
    uvicorn app.main:app --reload         # or the REST API + HTML UI on :8000

## API
    POST /api/documents        multipart file -> full record
    GET  /api/documents        list
    GET  /api/documents/{id}   one record
    PUT  /api/documents/{id}   human-corrected data (clears needs_review)

## Pipeline files
    app/processing.py   PDF render, text layer / Tesseract OCR, section split
    app/llm.py          invoice/receipt classification + extraction with validation-error retry loop
    app/schemas.py      Pydantic models + totals cross-check
    app/confidence.py   OCR conf + grounding checks + retry penalty
    app/db.py           JSON file store (swap for SQLite/Postgres JSONB)
