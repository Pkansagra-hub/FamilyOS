from __future__ import annotations
import uuid
def short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"
