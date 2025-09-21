from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime, timezone
from .adapters.json_doc import JsonDocStore

SCHEMA_VERSION = 1

@dataclass
class ConsentRecord:
    from_space: str
    to_space: str
    purpose: str
    granted_by: str
    granted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    expires_at: Optional[str] = None

class ConsentStore:
    """Consent store with grant, revoke, list, and check operations."""
    def __init__(self, path: str):
        self.store = JsonDocStore(path, schema_version=SCHEMA_VERSION, init_data={"records": []})

    def _read(self) -> Dict[str, object]:
        return self.store.read()

    def _write(self, data: Dict[str, object]) -> None:
        self.store.write(data)

    def grant(self, rec: ConsentRecord) -> None:
        def _mut(doc):
            rs: List[Dict[str, object]] = doc.setdefault("records", [])
            # De-dup
            for r in rs:
                if r["from_space"] == rec.from_space and r["to_space"] == rec.to_space and r["purpose"] == rec.purpose:
                    r["granted_by"] = rec.granted_by
                    r["granted_at"] = rec.granted_at
                    r["expires_at"] = rec.expires_at
                    return
            rs.append(rec.__dict__)
        self.store.update(_mut)

    def revoke(self, from_space: str, to_space: str, purpose: str) -> None:
        def _mut(doc):
            doc["records"] = [r for r in doc.get("records", []) if not (
                r.get("from_space") == from_space and r.get("to_space") == to_space and r.get("purpose") == purpose
            )]
        self.store.update(_mut)

    def has_consent(self, from_space: str, to_space: str, purpose: str) -> bool:
        data = self._read()
        for r in data.get("records", []):
            if r.get("from_space") == from_space and r.get("to_space") == to_space and r.get("purpose") == purpose:
                exp = r.get("expires_at")
                if exp:
                    try:
                        t = datetime.fromisoformat(exp)
                        if datetime.now(timezone.utc) > t.replace(tzinfo=timezone.utc):
                            continue
                    except Exception:
                        pass
                return True
        return False

    def list(self) -> List[Dict[str, object]]:
        return self._read().get("records", [])
