import json
import threading
import uuid

from ..config import settings

_LOCK = threading.Lock()
_STORE_FILE = settings.DATA_DIR / "documents.json"


def _load() -> dict:
    if not _STORE_FILE.exists():
        return {}
    with _STORE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    _STORE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def new_id() -> str:
    return f"doc_{uuid.uuid4().hex[:8]}"


def save_document(document_id: str, metadata: dict, chunks: list[dict]) -> None:
    with _LOCK:
        data = _load()
        data[document_id] = {"metadata": metadata, "chunks": chunks}
        _save(data)


def get_document(document_id: str) -> dict | None:
    with _LOCK:
        return _load().get(document_id)


def update_metadata(document_id: str, metadata: dict) -> dict | None:
    with _LOCK:
        data = _load()
        if document_id not in data:
            return None
        data[document_id]["metadata"] = metadata
        _save(data)
        return data[document_id]["metadata"]