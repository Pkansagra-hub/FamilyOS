"""
Knowledge Graph Store - Entity and relationship storage with BaseStore compliance.

Implements dual-model storage for KG entities and edges following:
- kg_entity.schema.json contract for entity storage
- kg_edge.schema.json contract for relationship storage
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from storage.core.base_store import BaseStore

logger = logging.getLogger(__name__)


@dataclass
class KGEntity:
    """
    Knowledge graph entity following kg_entity.schema.json contract.

    Represents nodes in the knowledge graph with types, labels, and properties.
    """

    id: str  # ULID
    space_id: str
    types: List[str] = field(default_factory=list)
    labels: Dict[str, Any] = field(default_factory=dict)
    created_ts: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    props: Optional[Dict[str, Any]] = None


@dataclass
class KGEdge:
    """
    Knowledge graph edge following kg_edge.schema.json contract.

    Represents relationships between entities in the knowledge graph.
    """

    id: str  # ULID
    space_id: str
    src: str  # Source entity ULID
    dst: str  # Destination entity ULID
    pred: str  # Predicate/relationship type
    created_ts: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    weight: Optional[float] = None


class KGStore(BaseStore):
    """
    Knowledge Graph Store for entities and relationships.

    Provides dual-model storage supporting both entities and edges with:
    - Entity management (create, read, update, delete)
    - Relationship management (connect, query, traverse)
    - Space-scoped access controls
    - Graph query capabilities

    Storage Model:
    - kg_entities table: Entity storage with JSON props
    - kg_edges table: Edge storage with relationship metadata
    """

    def __init__(self, config: Any) -> None:
        """Initialize KG store with dual table schema."""
        super().__init__(config)
        logger.info("KGStore initialized with dual entity/edge storage")

    def _get_schema(self) -> str:
        """Return SQL schema for KG tables."""
        return """
        CREATE TABLE IF NOT EXISTS kg_entities (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            types TEXT NOT NULL,  -- JSON array
            labels TEXT NOT NULL,  -- JSON object
            created_ts TEXT NOT NULL,
            props TEXT,  -- JSON object (optional)
            updated_ts TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_kg_entities_space_id ON kg_entities(space_id);
        CREATE INDEX IF NOT EXISTS idx_kg_entities_types ON kg_entities(types);
        CREATE INDEX IF NOT EXISTS idx_kg_entities_created_ts ON kg_entities(created_ts);

        CREATE TABLE IF NOT EXISTS kg_edges (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            src TEXT NOT NULL,  -- Source entity ID
            dst TEXT NOT NULL,  -- Destination entity ID
            pred TEXT NOT NULL,  -- Predicate/relationship type
            created_ts TEXT NOT NULL,
            weight REAL,  -- Optional weight
            updated_ts TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (src) REFERENCES kg_entities(id),
            FOREIGN KEY (dst) REFERENCES kg_entities(id)
        );

        CREATE INDEX IF NOT EXISTS idx_kg_edges_space_id ON kg_edges(space_id);
        CREATE INDEX IF NOT EXISTS idx_kg_edges_src ON kg_edges(src);
        CREATE INDEX IF NOT EXISTS idx_kg_edges_dst ON kg_edges(dst);
        CREATE INDEX IF NOT EXISTS idx_kg_edges_pred ON kg_edges(pred);
        CREATE INDEX IF NOT EXISTS idx_kg_edges_created_ts ON kg_edges(created_ts);
        CREATE INDEX IF NOT EXISTS idx_kg_edges_src_pred ON kg_edges(src, pred);
        CREATE INDEX IF NOT EXISTS idx_kg_edges_dst_pred ON kg_edges(dst, pred);
        """

    def _initialize_schema(self, conn: Any) -> None:
        """Initialize KG database schema."""
        conn.executescript(self._get_schema())
        logger.info("KG store schema initialized with entities and edges tables")

    def _create_record(self, record: Dict[str, Any]) -> str:
        """Create a generic record (not used directly)."""
        raise NotImplementedError("Use create_entity() or create_edge() instead")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a generic record (not used directly)."""
        raise NotImplementedError("Use get_entity() or get_edge() instead")

    def _update_record(self, record_id: str, record: Dict[str, Any]) -> None:
        """Update a generic record (not used directly)."""
        raise NotImplementedError("Use update_entity() or update_edge() instead")

    def _delete_record(self, record_id: str) -> None:
        """Delete a generic record (not used directly)."""
        raise NotImplementedError("Use delete_entity() or delete_edge() instead")

    def _list_records(
        self, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List generic records (returns combined entities and edges)."""
        entities = self.list_entities(space_id, limit)
        edges = self.list_edges(space_id, limit)

        records = []
        for entity in entities:
            entity_dict = asdict(entity)
            entity_dict["_type"] = "entity"
            records.append(entity_dict)

        for edge in edges:
            edge_dict = asdict(edge)
            edge_dict["_type"] = "edge"
            records.append(edge_dict)

        return records

    # Entity Management
    def create_entity(self, entity: KGEntity) -> str:
        """
        Create a new KG entity.

        Args:
            entity: KGEntity instance to store

        Returns:
            entity_id: The ID of the created entity
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        self._connection.execute(
            """
            INSERT INTO kg_entities (id, space_id, types, labels, created_ts, props)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                entity.id,
                entity.space_id,
                json.dumps(entity.types),
                json.dumps(entity.labels),
                entity.created_ts,
                json.dumps(entity.props) if entity.props else None,
            ),
        )

        logger.info(f"Created KG entity {entity.id} in space {entity.space_id}")
        return entity.id

    def get_entity(self, entity_id: str) -> Optional[KGEntity]:
        """
        Retrieve a KG entity by ID.

        Args:
            entity_id: The entity ID to retrieve

        Returns:
            KGEntity instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        cursor = self._connection.execute(
            """
            SELECT id, space_id, types, labels, created_ts, props
            FROM kg_entities WHERE id = ?
        """,
            (entity_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return KGEntity(
            id=row[0],
            space_id=row[1],
            types=json.loads(row[2]),
            labels=json.loads(row[3]),
            created_ts=row[4],
            props=json.loads(row[5]) if row[5] else None,
        )

    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a KG entity.

        Args:
            entity_id: The entity ID to update
            updates: Dictionary of fields to update
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        # Build dynamic update query
        update_fields: List[str] = []
        values: List[Any] = []

        if "types" in updates:
            update_fields.append("types = ?")
            values.append(json.dumps(updates["types"]))

        if "labels" in updates:
            update_fields.append("labels = ?")
            values.append(json.dumps(updates["labels"]))

        if "props" in updates:
            update_fields.append("props = ?")
            values.append(json.dumps(updates["props"]) if updates["props"] else None)

        if not update_fields:
            return

        update_fields.append("updated_ts = CURRENT_TIMESTAMP")
        values.append(entity_id)

        self._connection.execute(
            f"""
            UPDATE kg_entities SET {', '.join(update_fields)}
            WHERE id = ?
        """,
            values,
        )

        logger.info(f"Updated KG entity {entity_id}")

    def delete_entity(self, entity_id: str) -> None:
        """
        Delete a KG entity and all associated edges.

        Args:
            entity_id: The entity ID to delete
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        # First delete all edges involving this entity
        self._connection.execute(
            """
            DELETE FROM kg_edges WHERE src = ? OR dst = ?
        """,
            (entity_id, entity_id),
        )

        # Then delete the entity
        self._connection.execute("DELETE FROM kg_entities WHERE id = ?", (entity_id,))

        logger.info(f"Deleted KG entity {entity_id} and associated edges")

    def list_entities(
        self, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[KGEntity]:
        """
        List KG entities, optionally filtered by space.

        Args:
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of KGEntity instances
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if space_id:
            query = """
                SELECT id, space_id, types, labels, created_ts, props
                FROM kg_entities WHERE space_id = ?
                ORDER BY created_ts DESC
            """
            params = (space_id,)
        else:
            query = """
                SELECT id, space_id, types, labels, created_ts, props
                FROM kg_entities
                ORDER BY created_ts DESC
            """
            params = ()

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        entities = []
        for row in rows:
            entity = KGEntity(
                id=row[0],
                space_id=row[1],
                types=json.loads(row[2]),
                labels=json.loads(row[3]),
                created_ts=row[4],
                props=json.loads(row[5]) if row[5] else None,
            )
            entities.append(entity)

        return entities

    # Edge/Relationship Management
    def create_edge(self, edge: KGEdge) -> str:
        """
        Create a new KG edge (relationship).

        Args:
            edge: KGEdge instance to store

        Returns:
            edge_id: The ID of the created edge
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        self._connection.execute(
            """
            INSERT INTO kg_edges (id, space_id, src, dst, pred, created_ts, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                edge.id,
                edge.space_id,
                edge.src,
                edge.dst,
                edge.pred,
                edge.created_ts,
                edge.weight,
            ),
        )

        logger.info(
            f"Created KG edge {edge.id}: {edge.src} --{edge.pred}--> {edge.dst}"
        )
        return edge.id

    def get_edge(self, edge_id: str) -> Optional[KGEdge]:
        """
        Retrieve a KG edge by ID.

        Args:
            edge_id: The edge ID to retrieve

        Returns:
            KGEdge instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        cursor = self._connection.execute(
            """
            SELECT id, space_id, src, dst, pred, created_ts, weight
            FROM kg_edges WHERE id = ?
        """,
            (edge_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return KGEdge(
            id=row[0],
            space_id=row[1],
            src=row[2],
            dst=row[3],
            pred=row[4],
            created_ts=row[5],
            weight=row[6],
        )

    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a KG edge.

        Args:
            edge_id: The edge ID to update
            updates: Dictionary of fields to update
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        # Build dynamic update query
        update_fields: List[str] = []
        values: List[Any] = []

        if "weight" in updates:
            update_fields.append("weight = ?")
            values.append(updates["weight"])

        if "pred" in updates:
            update_fields.append("pred = ?")
            values.append(updates["pred"])

        if not update_fields:
            return

        update_fields.append("updated_ts = CURRENT_TIMESTAMP")
        values.append(edge_id)

        self._connection.execute(
            f"""
            UPDATE kg_edges SET {', '.join(update_fields)}
            WHERE id = ?
        """,
            values,
        )

        logger.info(f"Updated KG edge {edge_id}")

    def delete_edge(self, edge_id: str) -> None:
        """
        Delete a KG edge.

        Args:
            edge_id: The edge ID to delete
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        self._connection.execute("DELETE FROM kg_edges WHERE id = ?", (edge_id,))

        logger.info(f"Deleted KG edge {edge_id}")

    def list_edges(
        self, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[KGEdge]:
        """
        List KG edges, optionally filtered by space.

        Args:
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of KGEdge instances
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if space_id:
            query = """
                SELECT id, space_id, src, dst, pred, created_ts, weight
                FROM kg_edges WHERE space_id = ?
                ORDER BY created_ts DESC
            """
            params = (space_id,)
        else:
            query = """
                SELECT id, space_id, src, dst, pred, created_ts, weight
                FROM kg_edges
                ORDER BY created_ts DESC
            """
            params = ()

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        edges = []
        for row in rows:
            edge = KGEdge(
                id=row[0],
                space_id=row[1],
                src=row[2],
                dst=row[3],
                pred=row[4],
                created_ts=row[5],
                weight=row[6],
            )
            edges.append(edge)

        return edges

    # Graph Query Methods
    def get_entity_edges(
        self, entity_id: str, direction: str = "both", predicate: Optional[str] = None
    ) -> List[KGEdge]:
        """
        Get all edges connected to an entity.

        Args:
            entity_id: The entity ID
            direction: "incoming", "outgoing", or "both"
            predicate: Optional predicate filter

        Returns:
            List of connected edges
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if direction == "incoming":
            where_clause = "dst = ?"
            params: List[Any] = [entity_id]
        elif direction == "outgoing":
            where_clause = "src = ?"
            params = [entity_id]
        else:  # both
            where_clause = "src = ? OR dst = ?"
            params = [entity_id, entity_id]

        if predicate:
            where_clause += " AND pred = ?"
            params.append(predicate)

        cursor = self._connection.execute(
            f"""
            SELECT id, space_id, src, dst, pred, created_ts, weight
            FROM kg_edges WHERE {where_clause}
            ORDER BY created_ts DESC
        """,
            params,
        )

        rows = cursor.fetchall()
        edges = []
        for row in rows:
            edge = KGEdge(
                id=row[0],
                space_id=row[1],
                src=row[2],
                dst=row[3],
                pred=row[4],
                created_ts=row[5],
                weight=row[6],
            )
            edges.append(edge)

        return edges

    def get_connected_entities(
        self, entity_id: str, predicate: Optional[str] = None, depth: int = 1
    ) -> Set[str]:
        """
        Get entities connected to the given entity within specified depth.

        Args:
            entity_id: Starting entity ID
            predicate: Optional predicate filter
            depth: Traversal depth (1 = direct neighbors)

        Returns:
            Set of connected entity IDs
        """
        if depth <= 0:
            return set()

        # Get direct neighbors
        edges = self.get_entity_edges(entity_id, "both", predicate)
        connected = set()

        for edge in edges:
            if edge.src == entity_id:
                connected.add(edge.dst)
            else:
                connected.add(edge.src)

        # Recursive traversal for deeper levels
        if depth > 1:
            all_connected = connected.copy()
            for neighbor_id in connected:
                deeper = self.get_connected_entities(neighbor_id, predicate, depth - 1)
                all_connected.update(deeper)
            return all_connected

        return connected

    def find_path(
        self, start_id: str, end_id: str, max_depth: int = 3
    ) -> Optional[List[str]]:
        """
        Find shortest path between two entities using BFS.

        Args:
            start_id: Starting entity ID
            end_id: Target entity ID
            max_depth: Maximum search depth

        Returns:
            List of entity IDs forming the path, or None if no path found
        """
        if start_id == end_id:
            return [start_id]

        # BFS for shortest path
        queue: List[Tuple[str, List[str]]] = [(start_id, [start_id])]
        visited = {start_id}

        while queue:
            current_id, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            # Get neighbors
            neighbors = self.get_connected_entities(current_id, depth=1)

            for neighbor_id in neighbors:
                if neighbor_id == end_id:
                    return path + [neighbor_id]

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None

    def get_predicates(self, space_id: Optional[str] = None) -> List[str]:
        """
        Get all unique predicates in the knowledge graph.

        Args:
            space_id: Optional space filter

        Returns:
            List of unique predicate strings
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if space_id:
            cursor = self._connection.execute(
                """
                SELECT DISTINCT pred FROM kg_edges WHERE space_id = ?
                ORDER BY pred
            """,
                (space_id,),
            )
        else:
            cursor = self._connection.execute(
                "SELECT DISTINCT pred FROM kg_edges ORDER BY pred"
            )

        return [row[0] for row in cursor.fetchall()]

    def get_entity_types(self, space_id: Optional[str] = None) -> List[str]:
        """
        Get all unique entity types in the knowledge graph.

        Args:
            space_id: Optional space filter

        Returns:
            List of unique type strings
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if space_id:
            cursor = self._connection.execute(
                """
                SELECT DISTINCT types FROM kg_entities WHERE space_id = ?
            """,
                (space_id,),
            )
        else:
            cursor = self._connection.execute("SELECT DISTINCT types FROM kg_entities")

        all_types = set()
        for row in cursor.fetchall():
            types_list = json.loads(row[0])
            all_types.update(types_list)

        return sorted(list(all_types))

    def find_entities_by_type(
        self, entity_type: str, space_id: Optional[str] = None
    ) -> List[KGEntity]:
        """
        Find entities by type.

        Args:
            entity_type: The entity type to search for
            space_id: Optional space filter

        Returns:
            List of matching entities
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if space_id:
            cursor = self._connection.execute(
                """
                SELECT id, space_id, types, labels, created_ts, props
                FROM kg_entities
                WHERE space_id = ? AND JSON_EXTRACT(types, '$') LIKE ?
                ORDER BY created_ts DESC
            """,
                (space_id, f'%"{entity_type}"%'),
            )
        else:
            cursor = self._connection.execute(
                """
                SELECT id, space_id, types, labels, created_ts, props
                FROM kg_entities
                WHERE JSON_EXTRACT(types, '$') LIKE ?
                ORDER BY created_ts DESC
            """,
                (f'%"{entity_type}"%',),
            )

        rows = cursor.fetchall()
        entities = []
        for row in rows:
            entity = KGEntity(
                id=row[0],
                space_id=row[1],
                types=json.loads(row[2]),
                labels=json.loads(row[3]),
                created_ts=row[4],
                props=json.loads(row[5]) if row[5] else None,
            )
            # Verify type match (JSON_EXTRACT LIKE is imprecise)
            if entity_type in entity.types:
                entities.append(entity)

        return entities

    def get_stats(self, space_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get knowledge graph statistics.

        Args:
            space_id: Optional space filter

        Returns:
            Dictionary with entity/edge counts and other stats
        """
        if not self._connection:
            raise RuntimeError("KGStore not in transaction")

        if space_id:
            cursor = self._connection.execute(
                "SELECT COUNT(*) FROM kg_entities WHERE space_id = ?", (space_id,)
            )
            entity_count = cursor.fetchone()[0]

            cursor = self._connection.execute(
                "SELECT COUNT(*) FROM kg_edges WHERE space_id = ?", (space_id,)
            )
            edge_count = cursor.fetchone()[0]
        else:
            cursor = self._connection.execute("SELECT COUNT(*) FROM kg_entities")
            entity_count = cursor.fetchone()[0]

            cursor = self._connection.execute("SELECT COUNT(*) FROM kg_edges")
            edge_count = cursor.fetchone()[0]

        return {
            "entity_count": entity_count,
            "edge_count": edge_count,
            "predicates": self.get_predicates(space_id),
            "entity_types": self.get_entity_types(space_id),
        }
