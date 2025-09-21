"""
Tiered Memory Service - Memory tier management and location tracking.

This module implements storage for tiered memory location tracking following the
tiered_locator.schema.json contract. Manages memory items across different
storage tiers (hot, warm, cold, archive) with location references.

Key Features:
- Memory tier management (hot, warm, cold, archive)
- Location reference tracking across tiers
- Tier migration and promotion/demotion
- Space-scoped access control
- BaseStore compliance for transaction management
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class TierLocation:
    """Individual tier location within a tiered memory item."""

    tier: str  # hot, warm, cold, archive
    ref: str  # Reference to item in that tier


@dataclass
class TieredLocator:
    """
    Tiered memory locator following tiered_locator.schema.json contract.

    Represents memory item locations across different storage tiers.
    """

    id: str  # ULID
    tiers: List[TierLocation] = field(default_factory=list)


class TieredMemoryService(BaseStore):
    """
    Tiered memory management service.

    Provides memory tier management with:
    - Memory location tracking across hot/warm/cold/archive tiers
    - Tier migration and promotion/demotion operations
    - Location reference management
    - Space-scoped access controls
    - Tier utilization and statistics

    Storage Model:
    - tiered_locators table: Memory location metadata
    - tier_locations table: Individual tier references
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        """Initialize tiered memory service with locator tables schema."""
        super().__init__(config)
        logger.info("TieredMemoryService initialized for memory tier management")

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tiered locator validation."""
        return {
            "type": "object",
            "required": ["id", "tiers"],
            "properties": {
                "id": {"type": "string"},
                "tiers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["tier", "ref"],
                        "properties": {
                            "tier": {
                                "type": "string",
                                "enum": ["hot", "warm", "cold", "archive"],
                            },
                            "ref": {"type": "string"},
                        },
                    },
                },
            },
        }

    def _initialize_schema(self, conn: Any) -> None:
        """Initialize tiered memory service database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS tiered_locators (
            id TEXT PRIMARY KEY,
            tiers TEXT NOT NULL,  -- JSON array of tier locations
            created_ts TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_ts TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tier_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            locator_id TEXT NOT NULL,
            tier TEXT NOT NULL,
            ref TEXT NOT NULL,
            created_ts TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (locator_id) REFERENCES tiered_locators(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tiered_locators_id ON tiered_locators(id);
        CREATE INDEX IF NOT EXISTS idx_tier_locations_locator_id ON tier_locations(locator_id);
        CREATE INDEX IF NOT EXISTS idx_tier_locations_tier ON tier_locations(tier);
        CREATE INDEX IF NOT EXISTS idx_tier_locations_ref ON tier_locations(ref);
        CREATE INDEX IF NOT EXISTS idx_tier_locations_locator_tier
            ON tier_locations(locator_id, tier);
        """

        conn.executescript(schema_sql)
        logger.info("Tiered memory service schema initialized")

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a generic record (converts to TieredLocator and calls create_locator)."""
        tier_locations = []
        for tier_data in data.get("tiers", []):
            tier_locations.append(
                TierLocation(tier=tier_data["tier"], ref=tier_data["ref"])
            )

        locator = TieredLocator(
            id=data["id"],
            tiers=tier_locations,
        )
        self.create_locator(locator)
        return asdict(locator)

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a generic record (calls get_locator and converts to dict)."""
        locator = self.get_locator(record_id)
        return asdict(locator) if locator else None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a generic record (calls update_locator and returns updated record)."""
        tier_locations = []
        for tier_data in data.get("tiers", []):
            tier_locations.append(
                TierLocation(tier=tier_data["tier"], ref=tier_data["ref"])
            )

        self.update_locator(record_id, tier_locations)
        updated_locator = self.get_locator(record_id)
        if not updated_locator:
            raise ValueError(f"Failed to update tiered locator {record_id}")
        return asdict(updated_locator)

    def _delete_record(self, record_id: str) -> bool:
        """Delete a generic record (calls delete_locator)."""
        try:
            self.delete_locator(record_id)
            return True
        except Exception:
            return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List generic records (returns tiered locators as dicts)."""
        tier_filter = filters.get("tier") if filters else None

        locators = self.list_locators(tier_filter, limit)

        # Apply offset if specified
        if offset and offset > 0:
            locators = locators[offset:]

        return [asdict(locator) for locator in locators]

    # Tiered Memory Management
    def create_locator(self, locator: TieredLocator) -> str:
        """
        Create a new tiered memory locator.

        Args:
            locator: TieredLocator instance to store

        Returns:
            locator_id: The ID of the created locator
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Serialize tiers for main table
        tiers_json = json.dumps([{"tier": t.tier, "ref": t.ref} for t in locator.tiers])

        # Insert main locator record
        self._connection.execute(
            """
            INSERT INTO tiered_locators (id, tiers)
            VALUES (?, ?)
        """,
            (locator.id, tiers_json),
        )

        # Insert individual tier location records for queries
        for tier_location in locator.tiers:
            self._connection.execute(
                """
                INSERT INTO tier_locations (locator_id, tier, ref)
                VALUES (?, ?, ?)
            """,
                (locator.id, tier_location.tier, tier_location.ref),
            )

        logger.info(
            f"Created tiered locator {locator.id} with {len(locator.tiers)} tier locations"
        )
        return locator.id

    def get_locator(self, locator_id: str) -> Optional[TieredLocator]:
        """
        Retrieve a tiered locator by ID.

        Args:
            locator_id: The locator ID to retrieve

        Returns:
            TieredLocator instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        cursor = self._connection.execute(
            "SELECT id, tiers FROM tiered_locators WHERE id = ?",
            (locator_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        tiers_data = json.loads(row[1])
        tier_locations = [
            TierLocation(tier=t["tier"], ref=t["ref"]) for t in tiers_data
        ]

        return TieredLocator(
            id=row[0],
            tiers=tier_locations,
        )

    def update_locator(self, locator_id: str, tiers: List[TierLocation]) -> None:
        """
        Update a tiered locator's tier locations.

        Args:
            locator_id: The locator ID to update
            tiers: New list of tier locations
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Serialize tiers for main table
        tiers_json = json.dumps([{"tier": t.tier, "ref": t.ref} for t in tiers])

        # Update main locator record
        self._connection.execute(
            """
            UPDATE tiered_locators
            SET tiers = ?, updated_ts = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (tiers_json, locator_id),
        )

        # Delete old tier location records
        self._connection.execute(
            "DELETE FROM tier_locations WHERE locator_id = ?",
            (locator_id,),
        )

        # Insert new tier location records
        for tier_location in tiers:
            self._connection.execute(
                """
                INSERT INTO tier_locations (locator_id, tier, ref)
                VALUES (?, ?, ?)
            """,
                (locator_id, tier_location.tier, tier_location.ref),
            )

        logger.info(
            f"Updated tiered locator {locator_id} with {len(tiers)} tier locations"
        )

    def delete_locator(self, locator_id: str) -> None:
        """
        Delete a tiered locator and all its tier locations.

        Args:
            locator_id: The locator ID to delete
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Delete tier locations (cascade will handle this, but explicit for clarity)
        self._connection.execute(
            "DELETE FROM tier_locations WHERE locator_id = ?",
            (locator_id,),
        )

        # Delete main locator
        self._connection.execute(
            "DELETE FROM tiered_locators WHERE id = ?",
            (locator_id,),
        )

        logger.info(f"Deleted tiered locator {locator_id}")

    def add_tier_location(self, locator_id: str, tier: str, ref: str) -> None:
        """
        Add a new tier location to an existing locator.

        Args:
            locator_id: The locator ID to update
            tier: Tier name (hot, warm, cold, archive)
            ref: Reference to item in that tier
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Get current locator
        locator = self.get_locator(locator_id)
        if not locator:
            raise ValueError(f"Locator {locator_id} not found")

        # Check if tier already exists
        for existing_tier in locator.tiers:
            if existing_tier.tier == tier:
                # Update existing tier reference
                existing_tier.ref = ref
                self.update_locator(locator_id, locator.tiers)
                return

        # Add new tier location
        locator.tiers.append(TierLocation(tier=tier, ref=ref))
        self.update_locator(locator_id, locator.tiers)

        logger.info(f"Added {tier} tier location to locator {locator_id}")

    def remove_tier_location(self, locator_id: str, tier: str) -> None:
        """
        Remove a tier location from an existing locator.

        Args:
            locator_id: The locator ID to update
            tier: Tier name to remove
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Get current locator
        locator = self.get_locator(locator_id)
        if not locator:
            raise ValueError(f"Locator {locator_id} not found")

        # Remove tier location
        original_count = len(locator.tiers)
        locator.tiers = [t for t in locator.tiers if t.tier != tier]

        if len(locator.tiers) < original_count:
            self.update_locator(locator_id, locator.tiers)
            logger.info(f"Removed {tier} tier location from locator {locator_id}")

    def get_tier_reference(self, locator_id: str, tier: str) -> Optional[str]:
        """
        Get the reference for a specific tier in a locator.

        Args:
            locator_id: The locator ID
            tier: Tier name to get reference for

        Returns:
            Reference string or None if tier not found
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        cursor = self._connection.execute(
            "SELECT ref FROM tier_locations WHERE locator_id = ? AND tier = ?",
            (locator_id, tier),
        )

        row = cursor.fetchone()
        return row[0] if row else None

    def list_locators(
        self,
        tier_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[TieredLocator]:
        """
        List tiered locators, optionally filtered by tier.

        Args:
            tier_filter: Optional tier filter (only locators with this tier)
            limit: Optional result limit

        Returns:
            List of TieredLocator instances
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        if tier_filter:
            # Get locator IDs that have the specified tier
            cursor = self._connection.execute(
                """
                SELECT DISTINCT tl.id, tl.tiers
                FROM tiered_locators tl
                JOIN tier_locations tloc ON tl.id = tloc.locator_id
                WHERE tloc.tier = ?
                ORDER BY tl.created_ts DESC
            """,
                (tier_filter,),
            )
        else:
            cursor = self._connection.execute(
                """
                SELECT id, tiers FROM tiered_locators
                ORDER BY created_ts DESC
            """,
            )

        if limit:
            rows = cursor.fetchmany(limit)
        else:
            rows = cursor.fetchall()

        locators = []
        for row in rows:
            tiers_data = json.loads(row[1])
            tier_locations = [
                TierLocation(tier=t["tier"], ref=t["ref"]) for t in tiers_data
            ]
            locator = TieredLocator(
                id=row[0],
                tiers=tier_locations,
            )
            locators.append(locator)

        return locators

    def get_tier_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tier utilization.

        Returns:
            Dictionary with tier counts and statistics
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Get total locators
        cursor = self._connection.execute("SELECT COUNT(*) FROM tiered_locators")
        total_locators = cursor.fetchone()[0]

        # Get tier breakdown
        cursor = self._connection.execute(
            """
            SELECT tier, COUNT(*) FROM tier_locations GROUP BY tier ORDER BY tier
        """
        )

        tier_counts = {}
        for row in cursor.fetchall():
            tier_counts[row[0]] = row[1]

        # Get locators with multiple tiers
        cursor = self._connection.execute(
            """
            SELECT locator_id, COUNT(*) as tier_count
            FROM tier_locations
            GROUP BY locator_id
            HAVING tier_count > 1
        """
        )
        multi_tier_locators = len(cursor.fetchall())

        return {
            "total_locators": total_locators,
            "tier_counts": tier_counts,
            "multi_tier_locators": multi_tier_locators,
            "tier_distribution": {
                tier: count / total_locators if total_locators > 0 else 0
                for tier, count in tier_counts.items()
            },
        }

    def migrate_tier(
        self, locator_id: str, from_tier: str, to_tier: str, new_ref: str
    ) -> None:
        """
        Migrate a memory item from one tier to another.

        Args:
            locator_id: The locator ID to migrate
            from_tier: Source tier name
            to_tier: Destination tier name
            new_ref: New reference in destination tier
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Get current locator
        locator = self.get_locator(locator_id)
        if not locator:
            raise ValueError(f"Locator {locator_id} not found")

        # Update tier locations
        for tier_location in locator.tiers:
            if tier_location.tier == from_tier:
                tier_location.tier = to_tier
                tier_location.ref = new_ref
                break
        else:
            raise ValueError(
                f"Source tier {from_tier} not found in locator {locator_id}"
            )

        self.update_locator(locator_id, locator.tiers)

        logger.info(f"Migrated locator {locator_id} from {from_tier} to {to_tier} tier")

    def cleanup_broken_references(self, tier: str, valid_refs: List[str]) -> int:
        """
        Clean up tier locations with broken references.

        Args:
            tier: Tier to check for broken references
            valid_refs: List of valid references in that tier

        Returns:
            Number of broken references cleaned up
        """
        if not self._connection:
            raise RuntimeError("TieredMemoryService not in transaction")

        # Find tier locations with broken references
        placeholders = ",".join("?" * len(valid_refs))
        cursor = self._connection.execute(
            f"""
            SELECT locator_id, ref FROM tier_locations
            WHERE tier = ? AND ref NOT IN ({placeholders})
        """,
            [tier] + valid_refs,
        )

        broken_refs = cursor.fetchall()
        cleanup_count = 0

        for locator_id, broken_ref in broken_refs:
            # Remove the broken tier location
            self.remove_tier_location(locator_id, tier)
            cleanup_count += 1
            logger.warning(
                f"Cleaned up broken {tier} reference {broken_ref} "
                f"from locator {locator_id}"
            )

        logger.info(f"Cleaned up {cleanup_count} broken references in {tier} tier")
        return cleanup_count
