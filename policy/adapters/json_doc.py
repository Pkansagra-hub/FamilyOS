from __future__ import annotations
import json, os, tempfile
from typing import Dict, Any, Callable
from ..utils.locking import file_lock
from ..errors import StorageError

class JsonDocStore:
    """A single-file JSON document store with atomic writes and basic locking."""
    def __init__(self, path: str, schema_version: int = 1, init_data: Dict[str, Any] | None = None):
        self.path = path
        self.schema_version = schema_version
        if not os.path.exists(path):
            self._atomic_write({"schema_version": schema_version, **(init_data or {})})

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(prefix=".tmp_jsondoc_", dir=os.path.dirname(self.path) or ".")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
        except Exception as e:
            raise StorageError(f"Atomic write failed: {e}") from e
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def read(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"schema_version": self.schema_version}
        except Exception as e:
            raise StorageError(f"Read failed: {e}") from e

    def write(self, data: Dict[str, Any]) -> None:
        with file_lock(self.path):
            self._atomic_write(data)

    def update(self, mutator: Callable[[Dict[str, Any]], Dict[str, Any] | None]) -> Dict[str, Any]:
        with file_lock(self.path):
            current = self.read()
            res = mutator(current) or current
            if "schema_version" not in res:
                res["schema_version"] = self.schema_version
            self._atomic_write(res)
            return res
