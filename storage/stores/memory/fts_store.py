"""Full-Text Search Store Implementation

Provides SQLite FTS5-based full-text search capabilities with:
- Multi-language support with stemming
- Advanced search features (phrase queries, faceted search)
- TF-IDF scoring and ranking
- Performance optimization and caching
- Integration with UnitOfWork and MLS security

Contract: contracts/storage/schemas/fts_document.schema.json
"""

import hashlib
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from storage.core.base_store import BaseStore, StoreConfig
from storage.core.sqlite_util import create_optimized_connection

logger = logging.getLogger(__name__)


@dataclass
class FTSDocument:
    """FTS document structure matching contract schema."""

    doc_id: str  # ULID format
    space_id: str
    text: str
    lang: str
    ts: datetime
    band: str  # GREEN, AMBER, RED, BLACK
    source: Optional[str] = None
    tokens_count: Optional[int] = None
    segments: Optional[List[Dict[str, Any]]] = None


@dataclass
class SearchQuery:
    """Search query parameters."""

    text: str
    limit: int = 20
    offset: int = 0
    languages: Optional[List[str]] = None
    bands: Optional[List[str]] = None
    space_ids: Optional[List[str]] = None
    highlight: bool = False
    min_score: float = 0.0


@dataclass
class SearchResult:
    """Search result with metadata and scoring."""

    doc_id: str
    text: str
    score: float
    highlights: List[Tuple[int, int]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FTSStore(BaseStore):
    """Full-text search store using SQLite FTS5."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = False
        self._query_cache: Dict[str, Tuple[List[SearchResult], float]] = {}
        self._stats_cache: Optional[Dict[str, Any]] = None

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
                "segments": {"type": "array"},
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize FTS schema and tables."""
        # Create main FTS table with FTS5
        conn.execute(
            """
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
        """
        )

        # Create metadata table for exact matches and structured queries
        conn.execute(
            """
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
        """
        )

        # Create indexes for metadata queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fts_metadata_space_band
            ON fts_metadata(space_id, band)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fts_metadata_lang
            ON fts_metadata(lang)
        """
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new FTS record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        doc_id = data["doc_id"]

        # Insert into FTS table
        self._connection.execute(
            """
            INSERT INTO fts_documents (doc_id, space_id, text, lang, ts, band, source, tokens_count, segments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                doc_id,
                data["space_id"],
                data["text"],
                data["lang"],
                data["ts"],
                data["band"],
                data.get("source"),
                data.get("tokens_count"),
                json.dumps(data.get("segments")) if data.get("segments") else None,
            ),
        )

        # Insert into metadata table
        self._connection.execute(
            """
            INSERT INTO fts_metadata (doc_id, space_id, lang, ts, band, source, tokens_count, segments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                doc_id,
                data["space_id"],
                data["lang"],
                data["ts"],
                data["band"],
                data.get("source"),
                data.get("tokens_count"),
                json.dumps(data.get("segments")) if data.get("segments") else None,
            ),
        )

        return data

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read an FTS record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT m.doc_id, m.space_id, f.text, m.lang, m.ts, m.band,
                   m.source, m.tokens_count, m.segments
            FROM fts_metadata m
            JOIN fts_documents f ON m.doc_id = f.doc_id
            WHERE m.doc_id = ?
        """,
            (record_id,),
        )

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
            "segments": json.loads(row[8]) if row[8] else None,
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing FTS record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build update query for metadata table
        set_clauses: List[str] = []
        params: List[Any] = []

        for fieldname in ["space_id", "lang", "ts", "band", "source", "tokens_count"]:
            if fieldname in data:
                set_clauses.append(f"{fieldname} = ?")
                params.append(data[fieldname])

        if "segments" in data:
            set_clauses.append("segments = ?")
            params.append(json.dumps(data["segments"]) if data["segments"] else None)

        if set_clauses:
            params.append(record_id)
            self._connection.execute(
                f"""
                UPDATE fts_metadata
                SET {', '.join(set_clauses)}
                WHERE doc_id = ?
            """,
                params,
            )

        # Update FTS table if text changed
        if "text" in data:
            self._connection.execute(
                """
                UPDATE fts_documents
                SET text = ?, space_id = ?, lang = ?, ts = ?, band = ?, source = ?, tokens_count = ?, segments = ?
                WHERE doc_id = ?
            """,
                (
                    data["text"],
                    data.get("space_id", ""),
                    data.get("lang", ""),
                    data.get("ts", ""),
                    data.get("band", ""),
                    data.get("source", ""),
                    data.get("tokens_count", 0),
                    json.dumps(data.get("segments")) if data.get("segments") else None,
                    record_id,
                ),
            )

        # Return updated record
        return self._read_record(record_id) or data

    def _delete_record(self, record_id: str) -> bool:
        """Delete an FTS record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Delete from FTS table
        cursor = self._connection.execute(
            """
            DELETE FROM fts_documents WHERE doc_id = ?
        """,
            (record_id,),
        )

        if cursor.rowcount == 0:
            return False

        # Delete from metadata table
        self._connection.execute(
            """
            DELETE FROM fts_metadata WHERE doc_id = ?
        """,
            (record_id,),
        )

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

        cursor = self._connection.execute(
            f"""
            SELECT m.doc_id, m.space_id, f.text, m.lang, m.ts, m.band,
                   m.source, m.tokens_count, m.segments
            FROM fts_metadata m
            JOIN fts_documents f ON m.doc_id = f.doc_id
            {where_clause}
            ORDER BY m.ts DESC
            {limit_clause}{offset_clause}
        """,
            params,
        )

        results: List[Dict[str, Any]] = []
        for row in cursor.fetchall():
            results.append(
                {
                    "doc_id": row[0],
                    "space_id": row[1],
                    "text": row[2],
                    "lang": row[3],
                    "ts": row[4],
                    "band": row[5],
                    "source": row[6],
                    "tokens_count": row[7],
                    "segments": json.loads(row[8]) if row[8] else None,
                }
            )

        return results

    # Public API methods

    def store_document(self, document: FTSDocument) -> bool:
        """Store a document in the FTS index."""
        try:
            # Validate document against schema
            doc_data = {
                "doc_id": document.doc_id,
                "space_id": document.space_id,
                "text": document.text,
                "lang": document.lang,
                "ts": document.ts.isoformat(),
                "band": document.band,
                "source": document.source,
                "tokens_count": document.tokens_count,
                "segments": document.segments,
            }

            if self.config.schema_validation:
                validation = self.validate_data(doc_data)
                if not validation.is_valid:
                    raise ValueError(f"Document validation failed: {validation.errors}")

            self.create(doc_data)

            # Clear relevant caches
            self._stats_cache = None

            return True
        except Exception as e:
            logger.error(f"Failed to store document {document.doc_id}: {e}")
            return False

    def search(
        self, query: SearchQuery, space_filter: Optional[Set[str]] = None
    ) -> List[SearchResult]:
        """Search documents using FTS5."""
        try:
            # Check cache first
            cache_key = self._build_cache_key(query, space_filter)
            if cache_key in self._query_cache:
                cached_results, timestamp = self._query_cache[cache_key]
                # Cache TTL check (5 minutes)
                if datetime.now(timezone.utc).timestamp() - timestamp < 300:
                    return cached_results[query.offset : query.offset + query.limit]

            # Build FTS query
            fts_query = self._build_fts_query(query.text)

            # Build conditions
            conditions: List[str] = []
            params: List[Any] = [fts_query]

            # Add space filter
            if space_filter:
                space_placeholders = ",".join("?" * len(space_filter))
                conditions.append(f"m.space_id IN ({space_placeholders})")
                params.extend(space_filter)

            # Add language filter
            if query.languages:
                lang_placeholders = ",".join("?" * len(query.languages))
                conditions.append(f"m.lang IN ({lang_placeholders})")
                params.extend(query.languages)

            # Add band filter
            if query.bands:
                band_placeholders = ",".join("?" * len(query.bands))
                conditions.append(f"m.band IN ({band_placeholders})")
                params.extend(query.bands)

            where_clause = " AND " + " AND ".join(conditions) if conditions else ""

            # Execute search
            cursor = self._connection.execute(
                f"""
                SELECT f.doc_id, f.text, m.space_id, m.lang, m.ts, m.band, m.source,
                       snippet(fts_documents, 2, '<mark>', '</mark>', '...', 32) as snippet,
                       bm25(fts_documents) as score
                FROM fts_documents f
                JOIN fts_metadata m ON f.doc_id = m.doc_id
                WHERE fts_documents MATCH ?{where_clause}
                ORDER BY score
                LIMIT ? OFFSET ?
            """,
                params + [query.limit, query.offset],
            )

            results: List[SearchResult] = []
            for row in cursor.fetchall():
                # Calculate custom score
                score = self._calculate_custom_score(
                    row[8], row[3], query.languages, row[5], query.bands
                )

                # Extract highlights if requested
                highlights = (
                    self._extract_highlights(row[1], query.text.split())
                    if query.highlight
                    else []
                )

                result = SearchResult(
                    doc_id=row[0],
                    text=row[1],
                    score=score,
                    highlights=highlights,
                    metadata={
                        "space_id": row[2],
                        "lang": row[3],
                        "ts": row[4],
                        "band": row[5],
                        "source": row[6],
                        "snippet": row[7],
                    },
                )
                results.append(result)

            # Cache results
            self._query_cache[cache_key] = (
                results,
                datetime.now(timezone.utc).timestamp(),
            )
            self._cleanup_cache()

            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query.text}': {e}")
            return []

    def get_document(
        self, doc_id: str, space_filter: Optional[Set[str]] = None
    ) -> Optional[FTSDocument]:
        """Get a document by ID with optional space filtering."""
        try:
            doc_data = self.read(doc_id)
            if not doc_data:
                return None

            # Check space filter
            if space_filter and doc_data["space_id"] not in space_filter:
                return None

            return FTSDocument(
                doc_id=doc_data["doc_id"],
                space_id=doc_data["space_id"],
                text=doc_data["text"],
                lang=doc_data["lang"],
                ts=datetime.fromisoformat(doc_data["ts"]),
                band=doc_data["band"],
                source=doc_data["source"],
                tokens_count=doc_data["tokens_count"],
                segments=doc_data["segments"],
            )

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    def list_documents(
        self, space_filter: Optional[Set[str]] = None, limit: int = 100, offset: int = 0
    ) -> List[FTSDocument]:
        """List documents with optional space filtering."""
        try:
            filters = {}
            if space_filter and len(space_filter) == 1:
                filters["space_id"] = next(iter(space_filter))

            docs_data = self.list(filters, limit, offset)

            documents = []
            for doc_data in docs_data:
                # Apply space filter for multiple spaces
                if space_filter and doc_data["space_id"] not in space_filter:
                    continue

                documents.append(
                    FTSDocument(
                        doc_id=doc_data["doc_id"],
                        space_id=doc_data["space_id"],
                        text=doc_data["text"],
                        lang=doc_data["lang"],
                        ts=datetime.fromisoformat(doc_data["ts"]),
                        band=doc_data["band"],
                        source=doc_data["source"],
                        tokens_count=doc_data["tokens_count"],
                        segments=doc_data["segments"],
                    )
                )

            return documents

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get FTS index statistics."""
        if self._stats_cache:
            return self._stats_cache

        try:
            cursor = self._connection.execute(
                """
                SELECT
                    COUNT(*) as total_documents,
                    COUNT(DISTINCT space_id) as unique_spaces,
                    COUNT(DISTINCT lang) as unique_languages
                FROM fts_metadata
            """
            )
            row = cursor.fetchone()

            # Language distribution
            cursor = self._connection.execute(
                """
                SELECT lang, COUNT(*)
                FROM fts_metadata
                GROUP BY lang
            """
            )
            lang_dist = dict(cursor.fetchall())

            # Band distribution
            cursor = self._connection.execute(
                """
                SELECT band, COUNT(*)
                FROM fts_metadata
                GROUP BY band
            """
            )
            band_dist = dict(cursor.fetchall())

            stats = {
                "total_documents": row[0],
                "unique_spaces": row[1],
                "unique_languages": row[2],
                "language_distribution": lang_dist,
                "band_distribution": band_dist,
                "cache_size": len(self._query_cache),
            }

            self._stats_cache = stats
            return stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def rebuild_index(self) -> None:
        """Rebuild the FTS index."""
        try:
            self._connection.execute(
                "INSERT INTO fts_documents(fts_documents) VALUES('rebuild')"
            )
            logger.info("FTS index rebuilt successfully")
        except Exception as e:
            logger.error(f"Failed to rebuild FTS index: {e}")

    def optimize(self) -> None:
        """Optimize the FTS index."""
        try:
            self._connection.execute(
                "INSERT INTO fts_documents(fts_documents) VALUES('optimize')"
            )
            logger.info("FTS index optimized successfully")
        except Exception as e:
            logger.error(f"Failed to optimize FTS index: {e}")

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._query_cache.clear()

    # Private helper methods

    def _build_fts_query(self, text: str) -> str:
        """Build FTS5 query string with proper escaping."""
        # Basic sanitization - escape special FTS5 characters
        escaped_text = re.sub(r'["\*\(\)]', "", text)

        # Handle phrase queries (text in quotes)
        if '"' in text:
            # Extract phrases and individual terms
            phrases = re.findall(r'"([^"]*)"', text)
            remaining = re.sub(r'"[^"]*"', "", text)

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

        # Default: treat as AND query for better precision
        terms = escaped_text.split()
        return " AND ".join(f'"{term}"' for term in terms if term)

    def _extract_highlights(
        self, text: str, query_terms: List[str]
    ) -> List[Tuple[int, int]]:
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

    def _calculate_custom_score(
        self,
        base_score: float,
        doc_lang: str,
        query_langs: Optional[List[str]],
        doc_band: str,
        query_bands: Optional[List[str]],
    ) -> float:
        """Calculate custom relevance score."""
        score = base_score

        # Boost for language match
        if query_langs and doc_lang in query_langs:
            score *= 1.2

        # Boost for band preference
        if query_bands and doc_band in query_bands:
            score *= 1.1

        # Boost for higher security bands (more authoritative)
        band_weights = {"GREEN": 1.0, "AMBER": 1.1, "RED": 1.2, "BLACK": 1.3}
        score *= band_weights.get(doc_band, 1.0)

        return score

    def _build_cache_key(
        self, query: SearchQuery, space_filter: Optional[Set[str]]
    ) -> str:
        """Build cache key for query."""
        key_parts = [
            query.text,
            str(sorted(space_filter) if space_filter else ""),
            str(sorted(query.languages) if query.languages else ""),
            str(sorted(query.bands) if query.bands else ""),
            str(query.limit),
            str(query.offset),
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

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

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if not self._connection:
            self._connection = create_optimized_connection(self.config.db_path)
            if not self._initialized:
                self._initialize_schema(self._connection)
                self._initialized = True
        return self._connection
