"""Full-Text Search Store Implementation

Provides SQLite FTS5-based full-text search capabilities with:
- Multi-language support with stemming
- Advanced search features (phrase queries, faceted search)
- TF-IDF scoring and ranking
- Performance optimization and caching
- Integration with UnitOfWork and MLS security

Contract: contracts/storage/schemas/fts_document.schema.json
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import hashlib
import re

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult
from storage.core.sqlite_util import create_optimized_connection
from storage.core.unit_of_work import WriteReceipt

logger = logging.getLogger(__name__)


@dataclass
class FTSDocument:
    """FTS Document data structure following the contract schema."""

    doc_id: str
    space_id: str
    text: str
    lang: str
    ts: datetime
    band: str
    source: Optional[str] = None
    tokens_count: Optional[int] = None
    payload_ref: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result: Dict[str, Any] = {
            "doc_id": self.doc_id,
            "space_id": self.space_id,
            "text": self.text,
            "lang": self.lang,
            "ts": self.ts.isoformat(),
            "band": self.band,
        }
        if self.source:
            result["source"] = self.source
        if self.tokens_count is not None:
            result["tokens_count"] = self.tokens_count
        if self.payload_ref:
            result["payload_ref"] = self.payload_ref
        if self.segments:
            result["segments"] = self.segments
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FTSDocument":
        """Create from dictionary."""
        ts = datetime.fromisoformat(data["ts"].replace("Z", "+00:00"))
        return cls(
            doc_id=data["doc_id"],
            space_id=data["space_id"],
            text=data["text"],
            lang=data["lang"],
            ts=ts,
            band=data["band"],
            source=data.get("source"),
            tokens_count=data.get("tokens_count"),
            payload_ref=data.get("payload_ref"),
            segments=data.get("segments"),
        )


@dataclass
class SearchResult:
    """Search result with ranking information."""

    doc_id: str
    space_id: str
    text: str
    score: float
    snippet: str
    highlights: List[Tuple[int, int]]  # (start, end) positions
    metadata: Dict[str, Any] = field(default_factory=lambda: {})


@dataclass
class SearchQuery:
    """Structured search query."""

    text: str
    space_ids: Optional[List[str]] = None
    bands: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    limit: int = 50
    offset: int = 0
    highlight: bool = True
    facets: Optional[List[str]] = None


class FTSStore(BaseStore):
    """
    Full-Text Search Store Implementation

    Features:
    - SQLite FTS5 backend with advanced tokenizers
    - Multi-language stemming support
    - Phrase queries and proximity search
    - TF-IDF ranking and custom scoring
    - Faceted search capabilities
    - Result highlighting and snippets
    - Space-scoped security integration
    - Performance optimization with caching
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._connection: Optional[sqlite3.Connection] = None
        self._cache: Dict[str, Any] = {}
        self._max_cache_size = 1000

        # Language-specific stemmer mapping
        self._stemmers = {
            "en": "porter",
            "es": "spanish",
            "fr": "french",
            "de": "german",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
        }

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for validation."""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["doc_id", "space_id", "text", "lang", "ts", "band"],
            "properties": {
                "doc_id": {"type": "string", "pattern": "^[0-7][0-9A-HJKMNP-TV-Z]{25}$"},
                "space_id": {"type": "string", "pattern": "^(personal|selective|shared|extended|interfamily):[A-Za-z0-9_\\-\\.]+$"},
                "text": {"type": "string"},
                "lang": {"type": "string", "pattern": "^[A-Za-z]{2}(-[A-Za-z]{2})?$"},
                "ts": {"type": "string", "format": "date-time"},
                "band": {"type": "string", "enum": ["GREEN", "AMBER", "RED", "BLACK"]},
                "source": {"type": "string", "enum": ["episodic", "tool", "import", "action", "kg", "other"]},
                "tokens_count": {"type": "integer", "minimum": 0},
                "payload_ref": {"type": "string"},
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["offset", "length"],
                        "properties": {
                            "offset": {"type": "integer", "minimum": 0},
                            "length": {"type": "integer", "minimum": 0},
                            "section": {"type": "string"}
                        }
                    }
                }
            }
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if not self._connection:
            self._connection = create_optimized_connection(
                self.config.db_path
            )
            self._initialize_custom_schema()
        return self._connection

    def _initialize_custom_schema(self) -> None:
        """Initialize FTS tables and indexes."""
        conn = self._get_connection()

        # Main documents table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fts_documents (
                doc_id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL,
                text TEXT NOT NULL,
                lang TEXT NOT NULL,
                ts TEXT NOT NULL,
                band TEXT NOT NULL,
                source TEXT,
                tokens_count INTEGER,
                payload_ref TEXT,
                segments TEXT,  -- JSON array
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # FTS5 virtual table for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_search USING fts5(
                doc_id UNINDEXED,
                space_id UNINDEXED,
                text,
                lang UNINDEXED,
                band UNINDEXED,
                source UNINDEXED,
                content='fts_documents',
                content_rowid='rowid',
                tokenize='porter unicode61 remove_diacritics 2'
            )
        """)

        # Triggers to keep FTS5 table in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_documents_ai AFTER INSERT ON fts_documents BEGIN
                INSERT INTO fts_search(rowid, doc_id, space_id, text, lang, band, source)
                VALUES (new.rowid, new.doc_id, new.space_id, new.text, new.lang, new.band, new.source);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_documents_ad AFTER DELETE ON fts_documents BEGIN
                INSERT INTO fts_search(fts_search, rowid, doc_id, space_id, text, lang, band, source)
                VALUES ('delete', old.rowid, old.doc_id, old.space_id, old.text, old.lang, old.band, old.source);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_documents_au AFTER UPDATE ON fts_documents BEGIN
                INSERT INTO fts_search(fts_search, rowid, doc_id, space_id, text, lang, band, source)
                VALUES ('delete', old.rowid, old.doc_id, old.space_id, old.text, old.lang, old.band, old.source);
                INSERT INTO fts_search(rowid, doc_id, space_id, text, lang, band, source)
                VALUES (new.rowid, new.doc_id, new.space_id, new.text, new.lang, new.band, new.source);
            END
        """)

        # Indexes for common queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fts_space_id ON fts_documents(space_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fts_band ON fts_documents(band)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fts_lang ON fts_documents(lang)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fts_source ON fts_documents(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fts_ts ON fts_documents(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fts_composite ON fts_documents(space_id, band, lang)")

        conn.commit()

    def begin_transaction(self) -> None:
        """Begin transaction (called by UnitOfWork)."""
        conn = self._get_connection()
        conn.execute("BEGIN IMMEDIATE")
        logger.debug(f"{self._store_name}: Transaction begun")

    def commit_transaction(self) -> None:
        """Commit transaction (called by UnitOfWork)."""
        if self._connection:
            self._connection.commit()
            logger.debug(f"{self._store_name}: Transaction committed")

    def rollback_transaction(self) -> None:
        """Rollback transaction (called by UnitOfWork)."""
        if self._connection:
            self._connection.rollback()
            logger.debug(f"{self._store_name}: Transaction rolled back")

    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """Validate record against FTS document schema."""
        if not self.config.schema_validation:
            return ValidationResult(is_valid=True, errors=[])

        errors: List[str] = []
        warnings: List[str] = []

        # Check required fields
        required = ["doc_id", "space_id", "text", "lang", "ts", "band"]
        for field in required:
            if field not in record:
                errors.append(f"Missing required field: {field}")

        # Validate ULID format for doc_id
        if "doc_id" in record:
            if not re.match(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$", record["doc_id"]):
                errors.append(f"Invalid ULID format for doc_id: {record['doc_id']}")

        # Validate space_id format
        if "space_id" in record:
            if not re.match(r"^(personal|selective|shared|extended|interfamily):[A-Za-z0-9_\-\.]+$", record["space_id"]):
                errors.append(f"Invalid space_id format: {record['space_id']}")

        # Validate band
        if "band" in record:
            if record["band"] not in ["GREEN", "AMBER", "RED", "BLACK"]:
                errors.append(f"Invalid band value: {record['band']}")

        # Validate language code
        if "lang" in record:
            if not re.match(r"^[A-Za-z]{2}(-[A-Za-z]{2})?$", record["lang"]):
                errors.append(f"Invalid language code: {record['lang']}")

        # Validate source if provided
        if "source" in record and record["source"]:
            valid_sources = ["episodic", "tool", "import", "action", "kg", "other"]
            if record["source"] not in valid_sources:
                errors.append(f"Invalid source value: {record['source']}")

        # Validate tokens_count if provided
        if "tokens_count" in record and record["tokens_count"] is not None:
            if not isinstance(record["tokens_count"], int) or record["tokens_count"] < 0:
                errors.append("tokens_count must be a non-negative integer")

        # Validate segments if provided
        if "segments" in record and record["segments"]:
            if not isinstance(record["segments"], list):
                errors.append("segments must be an array")
            else:
                segments = record["segments"]
                for i, segment in enumerate(segments):
                    if not isinstance(segment, dict):
                        errors.append(f"segments[{i}] must be an object")
                        continue
                    if "offset" not in segment or "length" not in segment:
                        errors.append(f"segments[{i}] missing required fields offset/length")
                    offset = segment.get("offset")
                    if not isinstance(offset, int) or (offset is not None and offset < 0):
                        errors.append(f"segments[{i}].offset must be non-negative integer")
                    length = segment.get("length")
                    if not isinstance(length, int) or (length is not None and length < 0):
                        errors.append(f"segments[{i}].length must be non-negative integer")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def store_document(self, document: FTSDocument) -> bool:
        """Store a document for full-text search."""
        # Validate document
        doc_dict = document.to_dict()
        validation = self.validate_record(doc_dict)
        if not validation.is_valid:
            raise ValueError(f"Document validation failed: {validation.errors}")

        conn = self._get_connection()

        # Calculate tokens count if not provided
        if document.tokens_count is None:
            document.tokens_count = len(document.text.split())

        # Serialize segments as JSON
        segments_json = json.dumps(document.segments) if document.segments else None

        # Insert or replace document
        conn.execute("""
            INSERT OR REPLACE INTO fts_documents
            (doc_id, space_id, text, lang, ts, band, source, tokens_count, payload_ref, segments, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            document.doc_id,
            document.space_id,
            document.text,
            document.lang,
            document.ts.isoformat(),
            document.band,
            document.source,
            document.tokens_count,
            document.payload_ref,
            segments_json
        ))

        # Clear cache entries that might be affected
        self._invalidate_cache_for_space(document.space_id)

        logger.info(f"Stored FTS document {document.doc_id} in space {document.space_id}")
        return True

    def search(self, query: SearchQuery, space_filter: Optional[Set[str]] = None) -> List[SearchResult]:
        """
        Perform full-text search with advanced features.

        Args:
            query: Structured search query
            space_filter: Optional space IDs to filter by (for MLS security)

        Returns:
            List of search results with ranking and highlighting
        """
        # Build cache key
        cache_key = self._build_cache_key(query, space_filter)
        if cache_key in self._cache:
            logger.debug(f"FTS cache hit for query: {query.text[:50]}...")
            return self._cache[cache_key]

        conn = self._get_connection()

        # Build FTS query
        fts_query = self._build_fts_query(query.text, query.languages)

        # Build WHERE conditions
        conditions: List[str] = []
        params: List[Any] = [fts_query]

        # Space filtering (MLS security)
        if space_filter:
            space_list = list(space_filter)
        elif query.space_ids:
            space_list = query.space_ids
        else:
            space_list = None

        if space_list:
            placeholders = ",".join("?" * len(space_list))
            conditions.append(f"d.space_id IN ({placeholders})")
            params.extend(space_list)

        # Band filtering
        if query.bands:
            placeholders = ",".join("?" * len(query.bands))
            conditions.append(f"d.band IN ({placeholders})")
            params.extend(query.bands)

        # Language filtering
        if query.languages:
            placeholders = ",".join("?" * len(query.languages))
            conditions.append(f"d.lang IN ({placeholders})")
            params.extend(query.languages)

        # Source filtering
        if query.sources:
            placeholders = ",".join("?" * len(query.sources))
            conditions.append(f"d.source IN ({placeholders})")
            params.extend(query.sources)

        # Date range filtering
        if query.date_range:
            conditions.append("d.ts BETWEEN ? AND ?")
            params.extend([query.date_range[0].isoformat(), query.date_range[1].isoformat()])

        # Build full SQL query
        where_clause = " AND " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT
                d.doc_id,
                d.space_id,
                d.text,
                d.lang,
                d.band,
                d.source,
                f.rank,
                snippet(fts_search, 2, '<mark>', '</mark>', '...', 64) as snippet
            FROM fts_search f
            JOIN fts_documents d ON d.rowid = f.rowid
            WHERE fts_search MATCH ?{where_clause}
            ORDER BY f.rank
            LIMIT ? OFFSET ?
        """

        params.extend([query.limit, query.offset])

        try:
            cursor = conn.execute(sql, params)
            results: List[SearchResult] = []

            for row in cursor.fetchall():
                # Calculate custom score (combining FTS rank with other factors)
                base_score = abs(row[6])  # FTS rank (negative value, higher is better)
                score = self._calculate_custom_score(
                    base_score, row[3], query.languages, row[4], query.bands
                )

                # Extract highlights from snippet
                highlights = self._extract_highlights(row[7]) if query.highlight else []

                result = SearchResult(
                    doc_id=row[0],
                    space_id=row[1],
                    text=row[2],
                    score=score,
                    snippet=row[7],
                    highlights=highlights,
                    metadata={
                        "lang": row[3],
                        "band": row[4],
                        "source": row[5] or "unknown"
                    }
                )
                results.append(result)

            # Cache results if reasonable size
            if len(results) <= 100:
                self._cache[cache_key] = results
                if len(self._cache) > self._max_cache_size:
                    # Simple LRU: remove oldest entry
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]

            logger.info(f"FTS search returned {len(results)} results for query: {query.text[:50]}...")
            return results

        except sqlite3.Error as e:
            logger.error(f"FTS search failed: {e}")
            raise

    def get_document(self, doc_id: str, space_filter: Optional[Set[str]] = None) -> Optional[FTSDocument]:
        """Retrieve a specific document by ID."""
        conn = self._get_connection()

        # Build query with optional space filtering
        if space_filter:
            placeholders = ",".join("?" * len(space_filter))
            sql = f"""
                SELECT doc_id, space_id, text, lang, ts, band, source, tokens_count, payload_ref, segments
                FROM fts_documents
                WHERE doc_id = ? AND space_id IN ({placeholders})
            """
            params = [doc_id] + list(space_filter)
        else:
            sql = """
                SELECT doc_id, space_id, text, lang, ts, band, source, tokens_count, payload_ref, segments
                FROM fts_documents
                WHERE doc_id = ?
            """
            params = [doc_id]

        cursor = conn.execute(sql, params)
        row = cursor.fetchone()

        if not row:
            return None

        # Parse segments JSON
        segments = json.loads(row[9]) if row[9] else None

        return FTSDocument(
            doc_id=row[0],
            space_id=row[1],
            text=row[2],
            lang=row[3],
            ts=datetime.fromisoformat(row[4].replace("Z", "+00:00")),
            band=row[5],
            source=row[6],
            tokens_count=row[7],
            payload_ref=row[8],
            segments=segments
        )

    def delete_document(self, doc_id: str, space_filter: Optional[Set[str]] = None) -> bool:
        """Delete a document."""
        conn = self._get_connection()

        # Verify document exists and space access
        if space_filter:
            placeholders = ",".join("?" * len(space_filter))
            check_sql = f"SELECT space_id FROM fts_documents WHERE doc_id = ? AND space_id IN ({placeholders})"
            check_params = [doc_id] + list(space_filter)
        else:
            check_sql = "SELECT space_id FROM fts_documents WHERE doc_id = ?"
            check_params = [doc_id]

        cursor = conn.execute(check_sql, check_params)
        row = cursor.fetchone()

        if not row:
            return False

        space_id = row[0]

        # Delete document (triggers will handle FTS cleanup)
        conn.execute("DELETE FROM fts_documents WHERE doc_id = ?", (doc_id,))

        # Clear cache
        self._invalidate_cache_for_space(space_id)

        return True

    def list_documents(
        self,
        space_id: Optional[str] = None,
        band: Optional[str] = None,
        lang: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        space_filter: Optional[Set[str]] = None
    ) -> List[FTSDocument]:
        """List documents with optional filtering."""
        conn = self._get_connection()

        conditions: List[str] = []
        params: List[Any] = []

        # Space filtering
        if space_filter:
            space_list = list(space_filter)
            if space_id and space_id in space_list:
                conditions.append("space_id = ?")
                params.append(space_id)
            else:
                placeholders = ",".join("?" * len(space_list))
                conditions.append(f"space_id IN ({placeholders})")
                params.extend(space_list)
        elif space_id:
            conditions.append("space_id = ?")
            params.append(space_id)

        # Other filters
        if band:
            conditions.append("band = ?")
            params.append(band)

        if lang:
            conditions.append("lang = ?")
            params.append(lang)

        # Build query
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT doc_id, space_id, text, lang, ts, band, source, tokens_count, payload_ref, segments
            FROM fts_documents{where_clause}
            ORDER BY ts DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = conn.execute(sql, params)
        documents: List[FTSDocument] = []

        for row in cursor.fetchall():
            segments = json.loads(row[9]) if row[9] else None
            doc = FTSDocument(
                doc_id=row[0],
                space_id=row[1],
                text=row[2],
                lang=row[3],
                ts=datetime.fromisoformat(row[4].replace("Z", "+00:00")),
                band=row[5],
                source=row[6],
                tokens_count=row[7],
                payload_ref=row[8],
                segments=segments
            )
            documents.append(doc)

        return documents

    def get_stats(self, space_filter: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Get search statistics."""
        conn = self._get_connection()

        # Build space filter
        if space_filter:
            space_list = list(space_filter)
            placeholders = ",".join("?" * len(space_list))
            where_clause = f" WHERE space_id IN ({placeholders})"
            params = space_list
        else:
            where_clause = ""
            params = []

        # Get document counts
        cursor = conn.execute(f"SELECT COUNT(*) FROM fts_documents{where_clause}", params)
        total_docs = cursor.fetchone()[0]

        # Get counts by band
        cursor = conn.execute(f"SELECT band, COUNT(*) FROM fts_documents{where_clause} GROUP BY band", params)
        band_counts = dict(cursor.fetchall())

        # Get counts by language
        cursor = conn.execute(f"SELECT lang, COUNT(*) FROM fts_documents{where_clause} GROUP BY lang", params)
        lang_counts = dict(cursor.fetchall())

        # Get counts by source
        cursor = conn.execute(f"SELECT source, COUNT(*) FROM fts_documents{where_clause} GROUP BY source", params)
        source_counts = dict(cursor.fetchall())

        # Get total tokens
        cursor = conn.execute(f"SELECT SUM(tokens_count) FROM fts_documents{where_clause}", params)
        total_tokens = cursor.fetchone()[0] or 0

        return {
            "total_documents": total_docs,
            "total_tokens": total_tokens,
            "band_distribution": band_counts,
            "language_distribution": lang_counts,
            "source_distribution": source_counts,
            "cache_size": len(self._cache),
            "supported_languages": list(self._stemmers.keys())
        }

    def rebuild_index(self) -> None:
        """Rebuild the FTS index."""
        conn = self._get_connection()

        # Rebuild FTS index
        conn.execute("INSERT INTO fts_search(fts_search) VALUES('rebuild')")
        conn.commit()

        # Clear cache
        self._cache.clear()

        logger.info("FTS index rebuilt successfully")

    def optimize(self) -> None:
        """Optimize the FTS index."""
        conn = self._get_connection()

        # Optimize FTS index
        conn.execute("INSERT INTO fts_search(fts_search) VALUES('optimize')")
        conn.commit()

        logger.info("FTS index optimized")

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for FTS documents."""
        return {
            "type": "object",
            "required": ["doc_id", "space_id", "text", "lang", "ts", "band"],
            "properties": {
                "doc_id": {"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"},
                "space_id": {"type": "string"},
                "text": {"type": "string"},
                "lang": {"type": "string"},
                "ts": {"type": "string", "format": "date-time"},
                "band": {"enum": ["GREEN", "AMBER", "RED", "BLACK"]},
                "source": {"type": "string"},
                "tokens_count": {"type": "integer"},
                "segments": {"type": "array"}
            }
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize FTS schema and tables."""
        # Create main FTS table with FTS5
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
                doc_id UNINDEXED,
                space_id UNINDEXED,
                text,
                lang UNINDEXED,
                ts UNINDEXED,
                band UNINDEXED,
                source UNINDEXED,
                tokens_count UNINDEXED,
                segments UNINDEXED,
                content='',
                contentless_delete=1,
                tokenize='porter unicode61'
            )
        """)

        # Create metadata table for exact matches and structured queries
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fts_metadata (
                doc_id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL,
                lang TEXT NOT NULL,
                ts TEXT NOT NULL,
                band TEXT NOT NULL,
                source TEXT,
                tokens_count INTEGER,
                segments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES fts_documents(doc_id)
            )
        """)

        # Create indexes for metadata queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fts_metadata_space_band
            ON fts_metadata(space_id, band)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fts_metadata_lang
            ON fts_metadata(lang)
        """)

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new FTS record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        doc_id = data["doc_id"]

        # Insert into FTS table
        self._connection.execute("""
            INSERT INTO fts_documents (doc_id, space_id, text, lang, ts, band, source, tokens_count, segments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            data["space_id"],
            data["text"],
            data["lang"],
            data["ts"],
            data["band"],
            data.get("source"),
            data.get("tokens_count"),
            json.dumps(data.get("segments")) if data.get("segments") else None
        ))

        # Insert into metadata table
        self._connection.execute("""
            INSERT INTO fts_metadata (doc_id, space_id, lang, ts, band, source, tokens_count, segments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            data["space_id"],
            data["lang"],
            data["ts"],
            data["band"],
            data.get("source"),
            data.get("tokens_count"),
            json.dumps(data.get("segments")) if data.get("segments") else None
        ))

        return data

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read an FTS record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute("""
            SELECT m.doc_id, m.space_id, f.text, m.lang, m.ts, m.band,
                   m.source, m.tokens_count, m.segments
            FROM fts_metadata m
            JOIN fts_documents f ON m.doc_id = f.doc_id
            WHERE m.doc_id = ?
        """, (record_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "doc_id": row[0],
            "space_id": row[1],
            "text": row[2],
            "lang": row[3],
            "ts": row[4],
            "band": row[5],
            "source": row[6],
            "tokens_count": row[7],
            "segments": json.loads(row[8]) if row[8] else None
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing FTS record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build update query for metadata table
        set_clauses: List[str] = []
        params: List[Any] = []

        for field in ["space_id", "lang", "ts", "band", "source", "tokens_count"]:
            if field in data:
                set_clauses.append(f"{field} = ?")
                params.append(data[field])

        if "segments" in data:
            set_clauses.append("segments = ?")
            params.append(json.dumps(data["segments"]) if data["segments"] else None)

        if set_clauses:
            params.append(record_id)
            self._connection.execute(f"""
                UPDATE fts_metadata
                SET {', '.join(set_clauses)}
                WHERE doc_id = ?
            """, params)

        # Update FTS table if text changed
        if "text" in data:
            self._connection.execute("""
                UPDATE fts_documents
                SET text = ?, space_id = ?, lang = ?, ts = ?, band = ?, source = ?, tokens_count = ?, segments = ?
                WHERE doc_id = ?
            """, (
                data["text"],
                data.get("space_id", ""),
                data.get("lang", ""),
                data.get("ts", ""),
                data.get("band", ""),
                data.get("source", ""),
                data.get("tokens_count", 0),
                json.dumps(data.get("segments")) if data.get("segments") else None,
                record_id
            ))

        # Return updated record
        return self._read_record(record_id) or data

    def _delete_record(self, record_id: str) -> bool:
        """Delete an FTS record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Delete from FTS table
        cursor = self._connection.execute("""
            DELETE FROM fts_documents WHERE doc_id = ?
        """, (record_id,))

        if cursor.rowcount == 0:
            return False

        # Delete from metadata table
        self._connection.execute("""
            DELETE FROM fts_metadata WHERE doc_id = ?
        """, (record_id,))

        return True

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List FTS records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No active connection")

        conditions: List[str] = []
        params: List[Any] = []

        if filters:
            for field, value in filters.items():
                if field in ["space_id", "lang", "band", "source"]:
                    conditions.append(f"m.{field} = ?")
                    params.append(value)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        limit_clause = f" LIMIT {limit}" if limit else ""
        offset_clause = f" OFFSET {offset}" if offset else ""

        cursor = self._connection.execute(f"""
            SELECT m.doc_id, m.space_id, f.text, m.lang, m.ts, m.band,
                   m.source, m.tokens_count, m.segments
            FROM fts_metadata m
            JOIN fts_documents f ON m.doc_id = f.doc_id
            {where_clause}
            ORDER BY m.ts DESC
            {limit_clause}{offset_clause}
        """, params)

        results: List[Dict[str, Any]] = []
        for row in cursor.fetchall():
            results.append({
                "doc_id": row[0],
                "space_id": row[1],
                "text": row[2],
                "lang": row[3],
                "ts": row[4],
                "band": row[5],
                "source": row[6],
                "tokens_count": row[7],
                "segments": json.loads(row[8]) if row[8] else None
            })

        return results

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._query_cache.clear()

    # Private helper methods

    def _build_fts_query(self, text: str, languages: Optional[List[str]] = None) -> str:
        """Build FTS5 query string with proper escaping."""
        # Basic sanitization - escape special FTS5 characters
        escaped_text = re.sub(r'["\*\(\)]', '', text)

        # Handle phrase queries (text in quotes)
        if '"' in text:
            # Extract phrases and individual terms
            phrases = re.findall(r'"([^"]*)"', text)
            remaining = re.sub(r'"[^"]*"', '', text)

            query_parts: List[str] = []
            for phrase in phrases:
                if phrase.strip():
                    query_parts.append(f'"{phrase.strip()}"')

            # Add individual terms
            terms = remaining.split()
            for term in terms:
                if term.strip():
                    query_parts.append(term.strip())

            return " AND ".join(query_parts)

        # Handle proximity searches (NEAR operator)
        if " NEAR " in text.upper():
            return escaped_text

        # Default: treat as AND query for better precision
        terms = escaped_text.split()
        return " AND ".join(f'"{term}"' for term in terms if term)

    def _extract_highlights(self, text: str, query_terms: List[str]) -> List[Tuple[int, int]]:
        """Extract highlight positions from search text."""
        highlights: List[Tuple[int, int]] = []
        text_lower = text.lower()

        for term in query_terms:
            term_lower = term.lower().strip('"')
            start = 0
            while True:
                pos = text_lower.find(term_lower, start)
                if pos == -1:
                    break

                # Adjust for word boundaries
                actual_start = pos
                actual_end = pos + len(term_lower)
                highlights.append((actual_start, actual_end))
                start = actual_end

        return sorted(highlights)

    def _cleanup_cache(self) -> None:
        """Remove old entries from cache based on TTL."""
        current_time = datetime.now(timezone.utc).timestamp()
        ttl_seconds = 300  # 5 minutes

        keys_to_remove: List[str] = []
        for key, (_, timestamp) in self._query_cache.items():
            if current_time - timestamp > ttl_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._query_cache[key]
            str(sorted(query.space_ids) if query.space_ids else ""),
            str(sorted(query.bands) if query.bands else ""),
            str(sorted(query.languages) if query.languages else ""),
            str(sorted(query.sources) if query.sources else ""),
            str(query.date_range),
            str(query.limit),
            str(query.offset),
            str(sorted(space_filter) if space_filter else "")
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _invalidate_cache_for_space(self, space_id: str) -> None:
        """Invalidate cache entries for a specific space."""
        keys_to_remove: List[str] = []
        for key in self._cache.keys():
            # Simple heuristic - if space_id is in the key, remove it
            # This is conservative but safe
            if space_id in str(self._cache[key]):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
import hashlib
import re

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult
from storage.core.sqlite_util import create_optimized_connection
from storage.core.unit_of_work import WriteReceipt

logger = logging.getLogger(__name__)
