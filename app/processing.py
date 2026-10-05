"""Stages 1-3: PDF/image processing, OCR/text extraction, layout detection."""
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

def render_pages(data: bytes, filename: str) -> list[Image.Image]:
    if filename.lower().endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        return [Image.open(io.BytesIO(p.get_pixmap(dpi=200).tobytes("png"))) for p in doc]
    return [Image.open(io.BytesIO(data)).convert("RGB")]

def extract_text(data: bytes, filename: str) -> tuple[str, float, list[Image.Image]]:
    """Returns (text, ocr_confidence 0-1, page images). Digital PDFs skip OCR."""
    images = render_pages(data, filename)
    if filename.lower().endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n\f\n".join(p.get_text("text") for p in doc)
        if len(text.strip()) > 50:           # real text layer -> no OCR needed
            return text, 1.0, images
    texts, confs = [], []
    for img in images:
        d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = [(w, int(c)) for w, c in zip(d["text"], d["conf"]) if w.strip() and int(c) >= 0]
        texts.append(pytesseract.image_to_string(img))
        confs += [c for _, c in words]
    conf = (sum(confs) / len(confs) / 100) if confs else 0.0
    return "\n\f\n".join(texts), conf, images

def detect_sections(text: str) -> dict[str, str]:
    """Cheap layout pass: split header / line-item table / totals by keywords.
    Swap for LayoutLMv3 / Docling / Azure Layout when you need real geometry."""
    lines = text.splitlines()
    low = [l.lower() for l in lines]
    def find(keys):
        return next((i for i, l in enumerate(low) if any(k in l for k in keys)), None)
    t_start = find(["description", "qty", "item"])
    t_end = find(["subtotal", "total", "amount due"])
    if t_start is None or t_end is None or t_end <= t_start:
        return {"full": text}
    return {"header": "\n".join(lines[:t_start]),
            "items": "\n".join(lines[t_start:t_end]),
            "totals": "\n".join(lines[t_end:])}
