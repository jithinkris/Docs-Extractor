"""Run: streamlit run streamlit_app.py"""
import pandas as pd
import streamlit as st
from app import db, processing
from app.pipeline import run_pipeline

st.set_page_config(page_title="DocExtract", layout="wide")
st.title("Bill reader")
st.caption("Upload a bill or receipt. Check the details we found, make corrections, and save.")

# ---------- sidebar: saved bills ----------
with st.sidebar:
    st.subheader("Saved bills")
    docs = db.list_all()
    if not docs:
        st.caption("No documents yet. Upload one to start.")
    for d in docs:
        review = d.get("quality", {}).get("needs_review")
        name = (d.get("data") or {}).get("vendor_name") or d["filename"]
        if st.button(f"{'⚠️' if review else '✅'} {name}", key=d["id"], width="stretch"):
            st.session_state.current = d["id"]

# ---------- upload ----------
up = st.file_uploader("Choose a bill photo or PDF", type=["pdf", "jpg", "jpeg", "png"])
if up and st.session_state.get("last_upload") != (up.name, up.size):
    with st.spinner("Reading your bill and finding its details..."):
        data = up.getvalue()
        rec = run_pipeline(data, up.name)
        rec["id"] = db.save(rec)
        st.session_state.update(last_upload=(up.name, up.size), current=rec["id"],
                                file_bytes={rec["id"]: (data, up.name)})
    st.rerun()

# ---------- review ----------
cur = st.session_state.get("current")
rec = db.get(cur) if cur else None
if not rec:
    st.info("Start by choosing a bill photo or PDF above. We’ll read it and show the details here.")
    st.stop()

q = rec["quality"]
st.subheader(rec["filename"])
x = rec.get("data")
if not x:
    st.warning("We couldn’t read bill details from this file. Try a clearer, well-lit photo.")
else:
    if q["needs_review"]:
        st.info("Please check the details below. You can edit anything that doesn’t look right.")
    else:
        st.success("Bill details found. Check them and save when ready.")

    with st.form("review"):
        seller = st.text_input("Seller", x.get("vendor_name") or "")
        bill_number = st.text_input("Bill number", x.get("invoice_number") or "")
        bill_date = st.text_input("Date", str(x.get("invoice_date") or ""))
        total = st.text_input("Total", str(x.get("total") or ""))
        st.caption("Items")
        items = pd.DataFrame(x.get("line_items") or [],
                             columns=["description", "quantity", "unit_price", "amount"])
        edited_items = st.data_editor(items, num_rows="dynamic", width="stretch")
        with st.expander("More details"):
            due_date = st.text_input("Due date", x.get("due_date") or "")
            currency = st.text_input("Currency", x.get("currency") or "")
            subtotal = st.text_input("Subtotal", str(x.get("subtotal") or ""))
            tax = st.text_input("Tax", str(x.get("tax") or ""))

        if st.form_submit_button("Save bill details", type="primary"):
            x.update(
                vendor_name=seller,
                invoice_number=bill_number or None,
                invoice_date=bill_date or None,
                due_date=due_date or None,
                currency=currency or None,
                subtotal=subtotal or None,
                tax=tax or None,
                total=total or None,
                line_items=edited_items.where(edited_items.notna(), None).to_dict("records"),
            )
            rec["data"] = x
            q.update(needs_review=False, reviewed=True)
            db.save(rec)
            st.success("Bill details saved.")
            st.rerun()

with st.expander("Troubleshooting details"):
    st.caption(
        f"Detected as {rec['doc_type']}. Text-reading confidence: "
        f"{rec['ocr_confidence']:.0%}. Flags: "
        f"{', '.join(flag.replace('_', ' ') for flag in q['flags']) or 'none'}."
    )
    if rec.get("validation_errors"):
        st.caption("The extracted values did not pass validation:")
        for error in rec["validation_errors"]:
            st.code(error)
    with st.expander("Text read from the bill"):
        st.text(rec["raw_text"])
    preview = st.session_state.get("file_bytes", {}).get(rec["id"])
    if preview:
        with st.expander("Original bill"):
            for page in processing.render_pages(*preview):
                st.image(page, width="stretch")

if x:
    st.download_button("Download details as JSON", data=pd.Series(rec).to_json(indent=2),
                       file_name=f"{rec['id']}.json", mime="application/json")
