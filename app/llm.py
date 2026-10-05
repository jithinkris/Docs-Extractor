"""Stages 4 & 6: classification + structured extraction with validation retry.
LLM provider: Groq (OpenAI-compatible API)."""
import json, os
from openai import OpenAI
from pydantic import ValidationError
from .schemas import Invoice

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("MODEL", "openai/gpt-oss-20b")

def _ask(system: str, user: str) -> str:
    r = client.responses.create(model=MODEL, instructions=system, input=user)
    return r.output_text.strip().removeprefix("```json").removesuffix("```").strip()

def classify(text: str) -> str:
    out = _ask("Classify the document. Reply with exactly one word: invoice, receipt, or other.",
               text[:4000]).lower().strip(" .\n")
    return out if out in {"invoice", "receipt", "other"} else "other"

def extract_invoice(sections: dict[str, str], retries: int = 2) -> tuple[Invoice | None, list[str]]:
    schema = json.dumps(Invoice.model_json_schema())
    system = ("Extract invoice or receipt (bill) data as JSON matching this schema. Output JSON only, no prose. "
              "Map a bill/receipt number to invoice_number, its transaction date to invoice_date, "
              "and its grand total or amount paid to total. Extract listed purchased items as line_items. "
              "Use null for fields not present or dates that cannot be resolved from the document; never guess. "
              "Do not infer currency from location. Dates must be ISO-8601.\n" + schema)
    body = "\n\n".join(f"[{k.upper()}]\n{v}" for k, v in sections.items())
    errors: list[str] = []
    prompt = body
    for _ in range(retries + 1):
        raw = _ask(system, prompt)
        try:
            return Invoice.model_validate_json(raw), errors
        except (ValidationError, ValueError) as e:
            errors.append(str(e))
            prompt = f"{body}\n\nYour previous output failed validation:\n{e}\nFix it. JSON only."
    return None, errors