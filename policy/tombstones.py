"""
Tombstone management for Family AI Policy Engine.

Handles marking and tracking deleted/withdrawn content
for GDPR compliance and consent management.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Tombstone:
    """A record marking deleted/withdrawn content."""

    content_id: str
    content_type: str
    space_id: str
    actor_id: str
    reason: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tombstone":
        """Create from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class TombstoneStore:
    """Manages tombstone records for policy compliance."""

    def __init__(self, store_path: Optional[Path] = None):
        """Initialize tombstone store."""
        if store_path is None:
            self.store_path = Path("workspace/policy/tombstones.json")
        else:
            self.store_path = (
                Path(store_path) if isinstance(store_path, str) else store_path
            )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._tombstones: Dict[str, Tombstone] = {}
        self._load_tombstones()

    def _load_tombstones(self):
        """Load tombstones from storage."""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._tombstones = {}
                    for content_id, tomb_data in data.items():
                        # Ensure tomb_data is a dict before processing
                        if isinstance(tomb_data, dict):
                            self._tombstones[content_id] = Tombstone.from_dict(
                                tomb_data
                            )
                        # Skip invalid entries silently
            except (json.JSONDecodeError, KeyError, TypeError):
                # If corrupt, start fresh
                self._tombstones = {}

    def _save_tombstones(self):
        """Save tombstones to storage."""
        data = {
            content_id: tomb.to_dict() for content_id, tomb in self._tombstones.items()
        }
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def create_tombstone(
        self,
        content_id: str,
        content_type: str,
        space_id: str,
        actor_id: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tombstone:
        """Create a new tombstone record."""
        tombstone = Tombstone(
            content_id=content_id,
            content_type=content_type,
            space_id=space_id,
            actor_id=actor_id,
            reason=reason,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        self._tombstones[content_id] = tombstone
        self._save_tombstones()
        return tombstone

    def get_tombstone(self, content_id: str) -> Optional[Tombstone]:
        """Get tombstone by content ID."""
        return self._tombstones.get(content_id)

    def is_tombstoned(self, content_id: str) -> bool:
        """Check if content is tombstoned."""
        return content_id in self._tombstones

    def list_tombstones(
        self,
        space_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> List[Tombstone]:
        """List tombstones with optional filtering."""
        tombstones = list(self._tombstones.values())

        if space_id:
            tombstones = [t for t in tombstones if t.space_id == space_id]
        if actor_id:
            tombstones = [t for t in tombstones if t.actor_id == actor_id]
        if content_type:
            tombstones = [t for t in tombstones if t.content_type == content_type]

        return sorted(tombstones, key=lambda t: t.timestamp, reverse=True)

    def remove_tombstone(self, content_id: str) -> bool:
        """Remove a tombstone record."""
        if content_id in self._tombstones:
            del self._tombstones[content_id]
            self._save_tombstones()
            return True
        return False

    def cleanup_old_tombstones(self, days_old: int = 365) -> int:
        """Remove tombstones older than specified days."""
        cutoff = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        old_ids = [
            content_id
            for content_id, tomb in self._tombstones.items()
            if tomb.timestamp.timestamp() < cutoff
        ]

        for content_id in old_ids:
            del self._tombstones[content_id]

        if old_ids:
            self._save_tombstones()

        return len(old_ids)
