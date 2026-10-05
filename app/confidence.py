"""Stage 7: confidence + error detection."""
from .schemas import Invoice

def score(inv: Invoice | None, ocr_conf: float, retries_used: int, source_text: str) -> dict:
    if inv is None:
        return {"overall": 0.0, "needs_review": True, "flags": ["validation_failed"]}
    flags = []
    # Grounding check: extracted values should literally appear in the source text.
    checks = {"invoice_number": inv.invoice_number, "vendor_name": inv.vendor_name,
              "total": f"{inv.total:,.2f}"}
    grounded = 0
    for k, v in checks.items():
        if v is None:
            flags.append(f"{k}_missing")
            continue
        if str(v).lower().replace(",", "") in source_text.lower().replace(",", ""):
            grounded += 1
        else:
            flags.append(f"{k}_not_found_in_text")
    if ocr_conf < 0.80: flags.append("low_ocr_confidence")
    if not inv.line_items: flags.append("no_line_items")
    if inv.subtotal is None: flags.append("totals_unverifiable")
    overall = round(0.4 * ocr_conf + 0.4 * grounded / len(checks) + 0.2 * (1 - retries_used / 3), 3)
    return {"overall": overall, "needs_review": overall < 0.85 or bool(flags), "flags": flags}
