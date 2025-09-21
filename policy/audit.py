from __future__ import annotations
import json, os
from datetime import datetime, timezone
from typing import Any, Dict

class AuditLogger:
    """Simple JSON Lines audit logger with daily rotation and no external deps."""
    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _path_for_today(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return os.path.join(self.directory, f"audit-{ts}.log")

    def log(self, event: Dict[str, Any]) -> None:
        path = self._path_for_today()
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **event}
        line = json.dumps(record, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
