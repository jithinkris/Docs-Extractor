"""Stage 8: JSON 'database' (one file per document). Swap for SQLite/Postgres JSONB later."""
import json, uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent / "data"
(ROOT / "docs").mkdir(parents=True, exist_ok=True)

def save(record: dict) -> str:
    doc_id = record.setdefault("id", uuid.uuid4().hex[:12])
    (ROOT / "docs" / f"{doc_id}.json").write_text(json.dumps(record, indent=2, default=str))
    return doc_id

def get(doc_id: str) -> dict | None:
    p = ROOT / "docs" / f"{doc_id}.json"
    return json.loads(p.read_text()) if p.exists() else None

def list_all() -> list[dict]:
    return sorted((json.loads(p.read_text()) for p in (ROOT / "docs").glob("*.json")),
                  key=lambda r: r["created_at"], reverse=True)
