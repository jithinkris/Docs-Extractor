"""Shared orchestration used by both the Streamlit UI and the REST API."""
import datetime as dt, json
from . import processing, llm, confidence

def run_pipeline(data: bytes, filename: str) -> dict:
    text, ocr_conf, _ = processing.extract_text(data, filename)
    doc_type = llm.classify(text)
    record = {"filename": filename, "doc_type": doc_type, "ocr_confidence": ocr_conf,
              "created_at": dt.datetime.now(dt.UTC).isoformat(), "raw_text": text}
    if doc_type in {"invoice", "receipt"}:
        sections = processing.detect_sections(text)
        inv, errs = llm.extract_invoice(sections)
        record["data"] = json.loads(inv.model_dump_json()) if inv else None
        record["validation_errors"] = errs
        record["quality"] = confidence.score(inv, ocr_conf, len(errs), text)
    else:
        record["data"] = None
        record["quality"] = {"overall": 0, "needs_review": True, "flags": ["unsupported_doc_type"]}
    return record
