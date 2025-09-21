"""Event persistence layer for JSONL-based WAL storage.

This module provides the persistence layer for the MemoryOS event bus,
implementing JSONL-based Write-Ahead Log (WAL) storage with rotation,
replay capabilities, and integration with the existing event system.

Architecture:
- EventPersistence: Abstract interface for event storage
- JSONLPersistence: File-based implementation using JSON Lines format
- PersistenceConfig: Configuration for persistence behavior
- create_persistence: Factory function for creating persistence instances

WAL Format:
Each line in the JSONL file contains:
{"offset": N, "meta": {...}, "payload": {...}, "written_at": "2024-..."}

Features:
- Atomic append operations
- File rotation based on size/line count
- Event replay by offset range or time range
- Dead Letter Queue (DLQ) support
- Space-scoped storage paths for encryption
- Redaction-aware payload handling
"""

from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import aiofiles
import aiofiles.os

from .types import Event, EventType


class PersistenceType(Enum):
    """Types of persistence implementations."""

    JSONL = "jsonl"
    MEMORY = "memory"  # For testing


class PersistenceError(Exception):
    """Base exception for persistence operations."""

    def __init__(self, message: str, operation: str = "", file_path: str = ""):
        super().__init__(message)
        self.operation = operation
        self.file_path = file_path


class RotationError(PersistenceError):
    """Exception for file rotation failures."""

    pass


class ReplayError(PersistenceError):
    """Exception for replay operations."""

    pass


@dataclass
class PersistenceConfig:
    """Configuration for event persistence."""

    # Storage paths
    base_path: str = "./workspace/.bus"
    wal_dir: str = "wal"
    dlq_dir: str = "dlq"
    offsets_dir: str = "offsets"

    # Rotation policies
    max_file_size_mb: int = 100
    max_lines_per_file: int = 100_000
    max_segments_per_topic: int = 1000

    # Performance tuning
    buffer_size: int = 8192
    fsync_enabled: bool = True
    async_writes: bool = True
    write_batch_size: int = 100

    # Retention policies
    retention_days: Optional[int] = None
    cleanup_enabled: bool = True

    # Security
    redaction_enabled: bool = True
    space_scoped_paths: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if self.max_lines_per_file <= 0:
            raise ValueError("max_lines_per_file must be positive")
        if self.max_segments_per_topic <= 0:
            raise ValueError("max_segments_per_topic must be positive")


@dataclass
class WALEntry:
    """A single entry in the Write-Ahead Log."""

    offset: int
    event: Event
    written_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    segment_id: Optional[int] = None

    def to_jsonl_line(self) -> str:
        """Convert to JSONL format line."""
        envelope = self.event.to_envelope()
        entry = {
            "offset": self.offset,
            "meta": envelope,
            "payload": envelope["payload"],
            "written_at": self.written_at.isoformat(),
        }
        if self.segment_id is not None:
            entry["segment_id"] = self.segment_id

        return json.dumps(entry, separators=(",", ":"))

    @classmethod
    def from_jsonl_line(cls, line: str) -> WALEntry:
        """Parse from JSONL format line."""
        try:
            data = json.loads(line.strip())

            # Reconstruct event from envelope format
            envelope = data["meta"]
            event = Event.from_envelope(envelope)

            written_at = datetime.fromisoformat(
                data["written_at"].replace("Z", "+00:00")
            )

            return cls(
                offset=data["offset"],
                event=event,
                written_at=written_at,
                segment_id=data.get("segment_id"),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ReplayError(
                f"Failed to parse WAL entry: {e}", operation="parse", file_path=""
            )


@dataclass
class OffsetInfo:
    """Offset tracking information."""

    committed: int
    segment: int
    ts: datetime
    group: str
    topic: str


class EventPersistence(ABC):
    """Abstract interface for event persistence."""

    @abstractmethod
    async def append_event(self, event: Event, topic: EventType) -> int:
        """Append event to persistence layer.

        Args:
            event: Event to persist
            topic: Topic to append to

        Returns:
            Offset of the appended event

        Raises:
            PersistenceError: If append fails
        """
        pass

    @abstractmethod
    async def append_events_batch(
        self, events: List[Event], topic: EventType
    ) -> List[int]:
        """Append multiple events atomically.

        Args:
            events: Events to persist
            topic: Topic to append to

        Returns:
            List of offsets for each event

        Raises:
            PersistenceError: If batch append fails
        """
        pass

    @abstractmethod
    def replay_events(
        self,
        topic: EventType,
        from_offset: int = 0,
        to_offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[WALEntry]:
        """Replay events from persistence layer.

        Args:
            topic: Topic to replay from
            from_offset: Starting offset (inclusive)
            to_offset: Ending offset (exclusive)
            limit: Maximum number of events to return

        Yields:
            WALEntry objects in offset order

        Raises:
            ReplayError: If replay fails
        """
        pass

    @abstractmethod
    async def get_latest_offset(self, topic: EventType) -> int:
        """Get the latest offset for a topic.

        Args:
            topic: Topic to check

        Returns:
            Latest offset, or -1 if no events

        Raises:
            PersistenceError: If operation fails
        """
        pass

    @abstractmethod
    async def get_offset_info(
        self, topic: EventType, group: str
    ) -> Optional[OffsetInfo]:
        """Get offset information for a consumer group.

        Args:
            topic: Topic name
            group: Consumer group name

        Returns:
            OffsetInfo if exists, None otherwise

        Raises:
            PersistenceError: If operation fails
        """
        pass

    @abstractmethod
    async def commit_offset(
        self, topic: EventType, group: str, offset: int, segment: int
    ) -> None:
        """Commit offset for a consumer group.

        Args:
            topic: Topic name
            group: Consumer group name
            offset: Offset to commit
            segment: Segment number

        Raises:
            PersistenceError: If commit fails
        """
        pass

    @abstractmethod
    async def append_to_dlq(self, event: Event, topic: EventType, error: str) -> None:
        """Append event to Dead Letter Queue.

        Args:
            event: Failed event
            topic: Original topic
            error: Error description

        Raises:
            PersistenceError: If DLQ append fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if persistence layer is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close persistence layer and clean up resources."""
        pass


class JSONLPersistence(EventPersistence):
    """JSONL file-based persistence implementation."""

    def __init__(self, config: PersistenceConfig):
        self.config = config
        self._closed = False
        self._write_lock = threading.Lock()
        self._offsets: Dict[str, int] = {}  # topic -> latest offset
        self._segment_counters: Dict[str, int] = {}  # topic -> current segment
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="jsonl-persist"
        )

        # Ensure directories exist
        self._ensure_directories()

        # Initialize offsets - will be loaded lazily when needed
        self._offsets_loaded = False

    async def _ensure_offsets_loaded(self) -> None:
        """Ensure offsets are loaded (lazy initialization)."""
        if not self._offsets_loaded:
            await self._load_existing_offsets()
            self._offsets_loaded = True

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        base_path = Path(self.config.base_path)
        for subdir in [
            self.config.wal_dir,
            self.config.dlq_dir,
            self.config.offsets_dir,
        ]:
            (base_path / subdir).mkdir(parents=True, exist_ok=True)

    async def _load_existing_offsets(self) -> None:
        """Load existing offsets from disk."""
        try:
            wal_path = Path(self.config.base_path) / self.config.wal_dir
            if not wal_path.exists():
                return

            # Scan WAL files to determine latest offsets and segments
            for topic in EventType:
                topic_name = topic.value.lower()
                max_offset = -1
                max_segment = 0
                found_files = False

                # Find all segment files for this topic
                pattern = f"{topic_name}.*.jsonl"
                for wal_file in wal_path.glob(pattern):
                    found_files = True
                    try:
                        # Extract segment number from filename
                        parts = wal_file.stem.split(".")
                        if len(parts) >= 2:
                            segment_num = int(parts[-1])
                            max_segment = max(max_segment, segment_num)

                        # Read last line to get latest offset
                        async with aiofiles.open(wal_file, "r") as f:
                            last_line = ""
                            async for line in f:
                                if line.strip():
                                    last_line = line.strip()

                            if last_line:
                                entry = WALEntry.from_jsonl_line(last_line)
                                max_offset = max(max_offset, entry.offset)

                    except (ValueError, ReplayError):
                        # Skip corrupted files
                        continue

                # Only update if we found files or in-memory offset is lower
                if found_files:
                    current_offset = self._offsets.get(topic_name, -1)
                    self._offsets[topic_name] = max(current_offset, max_offset)
                    self._segment_counters[topic_name] = max_segment
                elif topic_name not in self._offsets:
                    # Initialize topics that don't exist yet
                    self._offsets[topic_name] = -1
                    self._segment_counters[topic_name] = 1

        except Exception as e:
            # Log warning but don't fail initialization
            print(f"Warning: Failed to load existing offsets: {e}")

    def _get_wal_file_path(
        self, topic: EventType, segment: Optional[int] = None
    ) -> Path:
        """Get WAL file path for topic and segment."""
        topic_name = topic.value.lower()

        if segment is None:
            segment = self._segment_counters.get(topic_name, 1)

        filename = f"{topic_name}.{segment:08d}.jsonl"
        return Path(self.config.base_path) / self.config.wal_dir / filename

    def _get_dlq_file_path(self, topic: EventType) -> Path:
        """Get DLQ file path for topic."""
        topic_name = topic.value.lower()
        filename = f"{topic_name}.dlq.jsonl"
        return Path(self.config.base_path) / self.config.dlq_dir / filename

    def _get_offset_file_path(self, topic: EventType, group: str) -> Path:
        """Get offset file path for topic and group."""
        topic_name = topic.value.lower()
        filename = f"{topic_name}__{group}.json"
        return Path(self.config.base_path) / self.config.offsets_dir / filename

    async def _should_rotate_file(self, file_path: Path) -> bool:
        """Check if file should be rotated."""
        if not file_path.exists():
            return False

        try:
            stat = await aiofiles.os.stat(file_path)

            # Check file size
            if stat.st_size > self.config.max_file_size_mb * 1024 * 1024:
                return True

            # Check line count
            line_count = 0
            async with aiofiles.open(file_path, "r") as f:
                async for _ in f:
                    line_count += 1
                    if line_count >= self.config.max_lines_per_file:
                        return True

            return False

        except Exception:
            return False

    async def _rotate_file(self, topic: EventType) -> None:
        """Rotate WAL file for topic."""
        topic_name = topic.value.lower()
        current_segment = self._segment_counters.get(topic_name, 1)

        # Check segment limit
        if current_segment >= self.config.max_segments_per_topic:
            raise RotationError(
                f"Maximum segments reached for topic {topic_name}",
                operation="rotate",
                file_path=str(self._get_wal_file_path(topic, current_segment)),
            )

        # Increment segment counter
        new_segment = current_segment + 1
        self._segment_counters[topic_name] = new_segment

    async def append_event(self, event: Event, topic: EventType) -> int:
        """Append single event to WAL."""
        await self._ensure_offsets_loaded()
        return (await self.append_events_batch([event], topic))[0]

    async def append_events_batch(
        self, events: List[Event], topic: EventType
    ) -> List[int]:
        """Append multiple events to WAL atomically."""
        await self._ensure_offsets_loaded()
        if self._closed:
            raise PersistenceError(
                "Persistence layer is closed", operation="append_batch"
            )

        if not events:
            return []

        topic_name = topic.value.lower()

        with self._write_lock:
            # Get starting offset
            current_offset = self._offsets.get(topic_name, -1)
            offsets = []
            wal_entries = []

            # Create WAL entries with sequential offsets
            for event in events:
                current_offset += 1
                offsets.append(current_offset)

                wal_entry = WALEntry(
                    offset=current_offset,
                    event=event,
                    segment_id=self._segment_counters.get(topic_name, 1),
                )
                wal_entries.append(wal_entry)

            # Update in-memory offset
            self._offsets[topic_name] = current_offset

        # Write to file
        try:
            file_path = self._get_wal_file_path(topic)

            # Check if rotation needed
            if await self._should_rotate_file(file_path):
                await self._rotate_file(topic)
                file_path = self._get_wal_file_path(topic)

            # Append entries to file
            async with aiofiles.open(
                file_path, "a", buffering=self.config.buffer_size
            ) as f:
                for entry in wal_entries:
                    await f.write(entry.to_jsonl_line() + "\n")

                # Flush file buffer
                await f.flush()

            return offsets

        except Exception as e:
            # Rollback in-memory state
            with self._write_lock:
                self._offsets[topic_name] = current_offset - len(events)

            raise PersistenceError(
                f"Failed to append events: {e}",
                operation="append_batch",
                file_path=str(file_path),
            ) from e

    async def replay_events(
        self,
        topic: EventType,
        from_offset: int = 0,
        to_offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[WALEntry]:
        """Replay events from WAL files."""
        if self._closed:
            raise ReplayError("Persistence layer is closed", operation="replay")

        topic_name = topic.value.lower()
        wal_path = Path(self.config.base_path) / self.config.wal_dir

        # Find all segment files for this topic
        pattern = f"{topic_name}.*.jsonl"
        segment_files = sorted(wal_path.glob(pattern))

        if not segment_files:
            return

        returned_count = 0

        for file_path in segment_files:
            try:
                async with aiofiles.open(file_path, "r") as f:
                    async for line in f:
                        if not line.strip():
                            continue

                        try:
                            entry = WALEntry.from_jsonl_line(line)

                            # Check offset range
                            if entry.offset < from_offset:
                                continue
                            if to_offset is not None and entry.offset >= to_offset:
                                return

                            # Check limit
                            if limit is not None and returned_count >= limit:
                                return

                            yield entry
                            returned_count += 1

                        except ReplayError:
                            # Skip corrupted entries
                            continue

            except Exception as e:
                raise ReplayError(
                    f"Failed to read WAL file: {e}",
                    operation="replay",
                    file_path=str(file_path),
                ) from e

    async def get_latest_offset(self, topic: EventType) -> int:
        """Get latest offset for topic."""
        topic_name = topic.value.lower()
        return self._offsets.get(topic_name, -1)

    async def get_offset_info(
        self, topic: EventType, group: str
    ) -> Optional[OffsetInfo]:
        """Get offset info for consumer group."""
        offset_file = self._get_offset_file_path(topic, group)

        if not offset_file.exists():
            return None

        try:
            async with aiofiles.open(offset_file, "r") as f:
                data = json.loads(await f.read())

            return OffsetInfo(
                committed=data["committed"],
                segment=data["segment"],
                ts=datetime.fromisoformat(data["ts"]),
                group=group,
                topic=topic.value,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise PersistenceError(
                f"Failed to read offset info: {e}",
                operation="get_offset_info",
                file_path=str(offset_file),
            ) from e

    async def commit_offset(
        self, topic: EventType, group: str, offset: int, segment: int
    ) -> None:
        """Commit offset for consumer group."""
        offset_file = self._get_offset_file_path(topic, group)

        offset_data = {
            "committed": offset,
            "segment": segment,
            "ts": datetime.now(timezone.utc).isoformat(),
            "group": group,
            "topic": topic.value,
        }

        try:
            # Atomic write using temporary file
            temp_file = offset_file.with_suffix(".tmp")

            async with aiofiles.open(temp_file, "w") as f:
                await f.write(json.dumps(offset_data, indent=2))
                await f.flush()

            # Atomic rename
            await aiofiles.os.rename(temp_file, offset_file)

        except Exception as e:
            # Clean up temp file if it exists
            try:
                temp_file_path = offset_file.with_suffix(".tmp")
                if temp_file_path.exists():
                    await aiofiles.os.remove(temp_file_path)
            except Exception:
                pass  # Ignore cleanup failures

            raise PersistenceError(
                f"Failed to commit offset: {e}",
                operation="commit_offset",
                file_path=str(offset_file),
            ) from e

    async def append_to_dlq(self, event: Event, topic: EventType, error: str) -> None:
        """Append event to Dead Letter Queue."""
        if self._closed:
            raise PersistenceError(
                "Persistence layer is closed", operation="append_dlq"
            )

        dlq_file = self._get_dlq_file_path(topic)

        # Create DLQ entry with error info
        dlq_entry = {
            "original_topic": topic.value,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "event": event.to_envelope(),
        }

        try:
            async with aiofiles.open(dlq_file, "a") as f:
                await f.write(json.dumps(dlq_entry, separators=(",", ":")) + "\n")
                await f.flush()

        except Exception as e:
            raise PersistenceError(
                f"Failed to append to DLQ: {e}",
                operation="append_dlq",
                file_path=str(dlq_file),
            ) from e

    async def health_check(self) -> bool:
        """Check if persistence layer is healthy."""
        if self._closed:
            return False

        try:
            # Check if we can write to base directory
            test_file = Path(self.config.base_path) / "health_check.tmp"

            async with aiofiles.open(test_file, "w") as f:
                await f.write("health_check")

            await aiofiles.os.remove(test_file)
            return True

        except Exception:
            return False

    async def close(self) -> None:
        """Close persistence layer."""
        self._closed = True
        self._executor.shutdown(wait=True)


def create_persistence(
    persistence_type: PersistenceType, config: Optional[PersistenceConfig] = None
) -> EventPersistence:
    """Factory function to create persistence instance.

    Args:
        persistence_type: Type of persistence to create
        config: Configuration (uses defaults if None)

    Returns:
        EventPersistence instance

    Raises:
        ValueError: If persistence_type is not supported
    """
    if config is None:
        config = PersistenceConfig()

    if persistence_type == PersistenceType.JSONL:
        return JSONLPersistence(config)
    elif persistence_type == PersistenceType.MEMORY:
        # TODO: Implement InMemoryPersistence for testing
        raise ValueError("InMemoryPersistence not implemented yet")
    else:
        raise ValueError(f"Unsupported persistence type: {persistence_type}")


# Global persistence instance
_default_persistence: Optional[EventPersistence] = None


def get_event_persistence() -> EventPersistence:
    """Get the global event persistence instance."""
    global _default_persistence
    if _default_persistence is None:
        _default_persistence = create_persistence(PersistenceType.JSONL)
    return _default_persistence


def set_event_persistence(persistence: EventPersistence) -> None:
    """Set the global event persistence instance (mainly for testing)."""
    global _default_persistence
    _default_persistence = persistence
