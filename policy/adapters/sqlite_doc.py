from __future__ import annotations
import sqlite3, json, os
from typing import Dict, Any, Callable
from ..errors import StorageError

SCHEMA = """
CREATE TABLE IF NOT EXISTS jsondoc (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  schema_version INTEGER NOT NULL,
  data TEXT NOT NULL
);
INSERT OR IGNORE INTO jsondoc (id, schema_version, data) VALUES (1, ?, ?);
"""

class SqliteDocStore:
    """Single-row JSON document in SQLite with versioning."""
    def __init__(self, path: str, schema_version: int = 1, init_data: Dict[str, Any] | None = None):
        init_data = init_data or {}
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.schema_version = schema_version
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.executescript(SCHEMA)
            cur = conn.execute("SELECT data FROM jsondoc WHERE id=1")
            row = cur.fetchone()
            if row is None or not row[0]:
                conn.execute("UPDATE jsondoc SET schema_version=?, data=? WHERE id=1",
                             (schema_version, json.dumps(init_data, ensure_ascii=False)))
                conn.commit()

    def read(self) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.path) as conn:
                cur = conn.execute("SELECT schema_version, data FROM jsondoc WHERE id=1")
                row = cur.fetchone()
                if not row:
                    return {"schema_version": self.schema_version}
                ver, data = row
                doc = json.loads(data)
                doc["schema_version"] = ver
                return doc
        except Exception as e:
            raise StorageError(f"SQLite read failed: {e}") from e

    def write(self, data: Dict[str, Any]) -> None:
        try:
            with sqlite3.connect(self.path) as conn:
                conn.execute("UPDATE jsondoc SET schema_version=?, data=? WHERE id=1",
                             (data.get("schema_version", self.schema_version),
                              json.dumps(data, ensure_ascii=False)))
                conn.commit()
        except Exception as e:
            raise StorageError(f"SQLite write failed: {e}") from e

    def update(self, mutator: Callable[[Dict[str, Any]], Dict[str, Any] | None]) -> Dict[str, Any]:
        with sqlite3.connect(self.path) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                cur = conn.execute("SELECT schema_version, data FROM jsondoc WHERE id=1")
                row = cur.fetchone()
                ver = row[0] if row else self.schema_version
                data = json.loads(row[1]) if row and row[1] else {}
                data["schema_version"] = ver
                res = mutator(data) or data
                if "schema_version" not in res:
                    res["schema_version"] = self.schema_version
                conn.execute("UPDATE jsondoc SET schema_version=?, data=? WHERE id=1",
                             (res["schema_version"], json.dumps(res, ensure_ascii=False)))
                conn.commit()
                return res
            except Exception as e:
                conn.rollback()
                raise StorageError(f"SQLite update failed: {e}") from e
