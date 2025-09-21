"""
Memory Commit Manager - CA1 Output with ACID Transactions
=========================================================

This module implements transactional memory commitment for the Memory Steward,
coordinating atomic storage operations with the UnitOfWork pattern and
reliable event publishing via outbox pattern. It ensures ACID properties
for memory formation operations.

**Neuroscience Inspiration:**
The CA1 region of the hippocampus serves as the primary output of hippocampal
processing, consolidating information from DG and CA3 and transmitting it to
cortical areas for long-term storage. This commit manager mirrors CA1 function
by ensuring that all memory formation results are atomically committed and
reliably transmitted to downstream systems.

**Research Backing:**
- Squire & Alvarez (1995): Retrograde amnesia and memory consolidation
- Frankland & Bontempi (2005): Organization of recent and remote memories
- Teyler & DiScenna (1986): Hippocampal memory indexing theory
- Buckner & Carroll (2007): Self-projection and the brain

The implementation follows the UnitOfWork pattern for transactional integrity
and the outbox pattern for reliable event delivery, ensuring that memory
formation operations are atomic and observable.
"""

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hippocampus.types import HippocampalEncoding
from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class MemoryCommitRequest:
    """
    Request for atomic memory commitment.
    """

    memory_id: str
    encoding: HippocampalEncoding
    deduplication: Dict[str, Any]
    space_id: str
    actor: Dict[str, Any]
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OutboxEvent:
    """
    Event for reliable delivery via outbox pattern.
    """

    event_id: str
    topic: str
    payload: Dict[str, Any]
    trace_id: str
    scheduled_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CommitResult:
    """
    Result of memory commitment operation.
    """

    memory_id: str
    committed: bool
    storage_refs: Dict[str, str]  # References to stored objects
    outbox_events: List[str]  # Event IDs added to outbox
    transaction_id: str
    commit_timestamp: datetime
    error_details: Optional[str] = None


class MemoryCommitManager:
    """
    Manages atomic memory commitment with ACID guarantees.

    Implements CA1-like output processing by coordinating transactional
    storage of memory formation results and reliable event publishing.

    **Key Functions:**
    - ACID transaction coordination via UnitOfWork
    - Atomic storage of memory artifacts
    - Reliable event publishing via outbox pattern
    - Rollback and compensation for failed operations
    - Cross-system consistency guarantees
    """

    def __init__(
        self,
        # Storage dependencies
        unit_of_work=None,
        memory_store=None,
        hippocampus_store=None,
        outbox_store=None,
        event_bus=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Dependencies (injected for testability)
        self.unit_of_work = unit_of_work
        self.memory_store = memory_store
        self.hippocampus_store = hippocampus_store
        self.outbox_store = outbox_store
        self.event_bus = event_bus

        # Configuration with defaults
        self.config = config or {}
        self.enable_outbox = self.config.get("enable_outbox", True)
        self.enable_rollback = self.config.get("enable_rollback", True)
        self.commit_timeout_ms = self.config.get("commit_timeout_ms", 5000)
        self.event_retry_count = self.config.get("event_retry_count", 3)

        logger.info(
            "MemoryCommitManager initialized",
            extra={
                "config": self.config,
                "enable_outbox": self.enable_outbox,
                "enable_rollback": self.enable_rollback,
                "commit_timeout_ms": self.commit_timeout_ms,
                "dependencies": {
                    "has_unit_of_work": self.unit_of_work is not None,
                    "has_memory_store": self.memory_store is not None,
                    "has_hippocampus_store": self.hippocampus_store is not None,
                    "has_outbox_store": self.outbox_store is not None,
                    "has_event_bus": self.event_bus is not None,
                },
            },
        )

    async def commit_memory_formation(
        self,
        encoding: HippocampalEncoding,
        deduplication: Dict[str, Any],
        space_id: str,
        request,
    ) -> str:
        """
        Commit memory formation with ACID guarantees.

        Implements CA1-like output processing by atomically storing all
        memory formation artifacts and publishing events reliably.

        Args:
            encoding: Hippocampal encoding to commit
            deduplication: Deduplication results to store
            space_id: Target memory space
            request: Original memory write request

        Returns:
            Committed memory ID

        Raises:
            CommitError: If atomic commitment fails
        """
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        memory_id = f"mem_{uuid.uuid4().hex}"

        with start_span(
            "memory_steward.commit_manager.commit_memory_formation"
        ) as span:
            span.set_attribute("memory_id", memory_id)
            span.set_attribute("space_id", space_id)
            span.set_attribute("transaction_id", transaction_id)

            try:
                logger.info(
                    "Starting memory formation commitment",
                    extra={
                        "memory_id": memory_id,
                        "transaction_id": transaction_id,
                        "space_id": space_id,
                        "event_id": encoding.event_id,
                        "deduplication_strategy": deduplication.get("strategy", "none"),
                    },
                )

                # Create commit request
                commit_request = MemoryCommitRequest(
                    memory_id=memory_id,
                    encoding=encoding,
                    deduplication=deduplication,
                    space_id=space_id,
                    actor=request.actor,
                    content=request.write_intent,
                    metadata={
                        "transaction_id": transaction_id,
                        "request_id": request.request_id,
                        "trace_id": request.trace_id,
                    },
                )

                # Execute atomic transaction
                if self.unit_of_work:
                    result = await self._commit_with_unit_of_work(commit_request)
                else:
                    result = await self._commit_without_unit_of_work(commit_request)

                if not result.committed:
                    raise CommitError(
                        f"Memory commitment failed: {result.error_details}",
                        transaction_id=transaction_id,
                        memory_id=memory_id,
                    )

                span.set_attribute("committed", True)
                span.set_attribute("storage_refs_count", len(result.storage_refs))
                span.set_attribute("outbox_events_count", len(result.outbox_events))

                logger.info(
                    "Memory formation commitment completed",
                    extra={
                        "memory_id": memory_id,
                        "transaction_id": transaction_id,
                        "storage_refs": result.storage_refs,
                        "outbox_events": result.outbox_events,
                        "commit_timestamp": result.commit_timestamp.isoformat(),
                    },
                )

                return memory_id

            except Exception as e:
                logger.error(
                    "Memory formation commitment failed",
                    extra={
                        "memory_id": memory_id,
                        "transaction_id": transaction_id,
                        "error": str(e),
                    },
                )
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

    async def _commit_with_unit_of_work(
        self, commit_request: MemoryCommitRequest
    ) -> CommitResult:
        """Commit using UnitOfWork pattern for full ACID guarantees."""

        storage_refs = {}
        outbox_events = []

        async with self.unit_of_work.begin() as transaction:
            try:
                # Step 1: Store hippocampal encoding
                if self.hippocampus_store:
                    hippo_ref = await self._store_hippocampal_encoding(
                        commit_request.encoding, transaction
                    )
                    storage_refs["hippocampus"] = hippo_ref

                # Step 2: Store memory record
                if self.memory_store:
                    memory_ref = await self._store_memory_record(
                        commit_request, transaction
                    )
                    storage_refs["memory"] = memory_ref

                # Step 3: Handle deduplication results
                if commit_request.deduplication.get("merged_with"):
                    dedup_ref = await self._handle_deduplication_merge(
                        commit_request, transaction
                    )
                    storage_refs["deduplication"] = dedup_ref

                # Step 4: Add outbox events
                if self.enable_outbox and self.outbox_store:
                    outbox_event_ids = await self._add_outbox_events(
                        commit_request, transaction
                    )
                    outbox_events.extend(outbox_event_ids)

                # Step 5: Commit transaction
                await transaction.commit()

                return CommitResult(
                    memory_id=commit_request.memory_id,
                    committed=True,
                    storage_refs=storage_refs,
                    outbox_events=outbox_events,
                    transaction_id=commit_request.metadata.get(
                        "transaction_id", "unknown"
                    ),
                    commit_timestamp=datetime.now(timezone.utc),
                )

            except Exception as e:
                # Rollback transaction
                if self.enable_rollback:
                    await transaction.rollback()

                return CommitResult(
                    memory_id=commit_request.memory_id,
                    committed=False,
                    storage_refs={},
                    outbox_events=[],
                    transaction_id=commit_request.metadata.get(
                        "transaction_id", "unknown"
                    ),
                    commit_timestamp=datetime.now(timezone.utc),
                    error_details=str(e),
                )

    async def _commit_without_unit_of_work(
        self, commit_request: MemoryCommitRequest
    ) -> CommitResult:
        """Commit without UnitOfWork (fallback with reduced guarantees)."""

        storage_refs = {}
        outbox_events = []

        try:
            # Store components individually (no transaction guarantees)

            # Store hippocampal encoding
            if self.hippocampus_store:
                hippo_ref = await self._store_hippocampal_encoding_direct(
                    commit_request.encoding
                )
                storage_refs["hippocampus"] = hippo_ref

            # Store memory record
            if self.memory_store:
                memory_ref = await self._store_memory_record_direct(commit_request)
                storage_refs["memory"] = memory_ref

            # Handle deduplication
            if commit_request.deduplication.get("merged_with"):
                dedup_ref = await self._handle_deduplication_merge_direct(
                    commit_request
                )
                storage_refs["deduplication"] = dedup_ref

            # Publish events directly
            if self.event_bus:
                event_ids = await self._publish_events_direct(commit_request)
                outbox_events.extend(event_ids)

            return CommitResult(
                memory_id=commit_request.memory_id,
                committed=True,
                storage_refs=storage_refs,
                outbox_events=outbox_events,
                transaction_id=commit_request.metadata.get("transaction_id", "unknown"),
                commit_timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            return CommitResult(
                memory_id=commit_request.memory_id,
                committed=False,
                storage_refs=storage_refs,
                outbox_events=outbox_events,
                transaction_id=commit_request.metadata.get("transaction_id", "unknown"),
                commit_timestamp=datetime.now(timezone.utc),
                error_details=str(e),
            )

    async def _store_hippocampal_encoding(
        self, encoding: HippocampalEncoding, transaction
    ) -> str:
        """Store hippocampal encoding within transaction."""
        # Convert encoding to storage format
        encoding_record = {
            "id": encoding.event_id,
            "space_id": encoding.space_id,
            "simhash_hex": encoding.simhash_hex,
            "minhash32": encoding.minhash32,
            "novelty": encoding.novelty,
            "near_duplicates": encoding.near_duplicates,
            "ts": encoding.ts.isoformat(),
            "meta": encoding.metadata or {},
        }

        # Store via transaction
        ref = await transaction.hippocampus_store.add(encoding_record)
        return f"hippo:{ref}"

    async def _store_memory_record(
        self, commit_request: MemoryCommitRequest, transaction
    ) -> str:
        """Store memory record within transaction."""
        memory_record = {
            "id": commit_request.memory_id,
            "space_id": commit_request.space_id,
            "actor": commit_request.actor,
            "content": commit_request.content,
            "hippocampus_event_id": commit_request.encoding.event_id,
            "deduplication": commit_request.deduplication,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": commit_request.metadata or {},
        }

        ref = await transaction.memory_store.add(memory_record)
        return f"mem:{ref}"

    async def _handle_deduplication_merge(
        self, commit_request: MemoryCommitRequest, transaction
    ) -> str:
        """Handle deduplication merge operations within transaction."""
        merged_with = commit_request.deduplication.get("merged_with", [])

        for merged_memory_id in merged_with:
            # Update merged memory to reference new memory
            merge_record = {
                "source_memory_id": merged_memory_id,
                "target_memory_id": commit_request.memory_id,
                "merge_timestamp": datetime.now(timezone.utc).isoformat(),
                "merge_strategy": commit_request.deduplication.get(
                    "strategy", "unknown"
                ),
            }

            await transaction.memory_store.add_merge_record(merge_record)

        return f"dedup:{len(merged_with)}_merged"

    async def _add_outbox_events(
        self, commit_request: MemoryCommitRequest, transaction
    ) -> List[str]:
        """Add events to outbox within transaction."""
        outbox_event_ids = []

        # Create memory formation events
        events = self._create_memory_formation_events(commit_request)

        for event_data in events:
            outbox_event = OutboxEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                topic=event_data["topic"],
                payload=event_data["payload"],
                trace_id=commit_request.metadata.get("trace_id", "unknown"),
                scheduled_at=datetime.now(timezone.utc),
                max_retries=self.event_retry_count,
            )

            # Add to outbox
            await transaction.outbox_store.add(asdict(outbox_event))
            outbox_event_ids.append(outbox_event.event_id)

        return outbox_event_ids

    async def _store_hippocampal_encoding_direct(
        self, encoding: HippocampalEncoding
    ) -> str:
        """Store hippocampal encoding directly (fallback)."""
        # This would directly call the hippocampus store
        # For now, return a placeholder reference
        return f"hippo:{encoding.event_id}"

    async def _store_memory_record_direct(
        self, commit_request: MemoryCommitRequest
    ) -> str:
        """Store memory record directly (fallback)."""
        # This would directly call the memory store
        # For now, return a placeholder reference
        return f"mem:{commit_request.memory_id}"

    async def _handle_deduplication_merge_direct(
        self, commit_request: MemoryCommitRequest
    ) -> str:
        """Handle deduplication merge directly (fallback)."""
        merged_count = len(commit_request.deduplication.get("merged_with", []))
        return f"dedup:{merged_count}_merged"

    async def _publish_events_direct(
        self, commit_request: MemoryCommitRequest
    ) -> List[str]:
        """Publish events directly (fallback)."""
        if not self.event_bus:
            return []

        events = self._create_memory_formation_events(commit_request)
        event_ids = []

        for event_data in events:
            try:
                event_id = f"evt_{uuid.uuid4().hex[:12]}"
                await self.event_bus.publish(event_data["topic"], event_data["payload"])
                event_ids.append(event_id)
            except Exception as e:
                logger.warning(
                    "Failed to publish event directly",
                    extra={"topic": event_data["topic"], "error": str(e)},
                )

        return event_ids

    def _create_memory_formation_events(
        self, commit_request: MemoryCommitRequest
    ) -> List[Dict[str, Any]]:
        """Create memory formation events for publishing."""
        events = []

        # Memory committed event
        events.append(
            {
                "topic": "cognitive.memory.write.committed",
                "payload": {
                    "memory_id": commit_request.memory_id,
                    "event_id": commit_request.encoding.event_id,
                    "space_id": commit_request.space_id,
                    "actor": commit_request.actor,
                    "novelty": commit_request.encoding.novelty,
                    "near_duplicates": len(commit_request.encoding.near_duplicates),
                    "deduplication": commit_request.deduplication,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trace_id": commit_request.metadata.get("trace_id", "unknown"),
                },
            }
        )

        # Deduplication event (if applicable)
        if commit_request.deduplication.get("merged_with"):
            events.append(
                {
                    "topic": "cognitive.memory.deduplication.merged",
                    "payload": {
                        "memory_id": commit_request.memory_id,
                        "merged_with": commit_request.deduplication["merged_with"],
                        "strategy": commit_request.deduplication.get(
                            "strategy", "unknown"
                        ),
                        "similarity_score": commit_request.deduplication.get(
                            "similarity_score", 0.0
                        ),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "trace_id": commit_request.metadata.get("trace_id", "unknown"),
                    },
                }
            )

        return events

    async def publish_cognitive_events(self, events: List[Dict[str, Any]]) -> None:
        """Publish cognitive events via outbox pattern."""
        if not self.enable_outbox or not self.outbox_store:
            logger.debug("Outbox not enabled, skipping event publication")
            return

        for event_data in events:
            outbox_event = OutboxEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                topic=event_data["topic"],
                payload=event_data["payload"],
                trace_id=event_data.get("trace_id", "unknown"),
                scheduled_at=datetime.now(timezone.utc),
                max_retries=self.event_retry_count,
            )

            # Add to outbox for reliable delivery
            await self.outbox_store.add(asdict(outbox_event))

            logger.debug(
                "Added event to outbox",
                extra={
                    "event_id": outbox_event.event_id,
                    "topic": outbox_event.topic,
                    "trace_id": outbox_event.trace_id,
                },
            )


class CommitError(Exception):
    """Exception raised when memory commitment fails."""

    def __init__(self, message: str, transaction_id: str, memory_id: str):
        super().__init__(message)
        self.transaction_id = transaction_id
        self.memory_id = memory_id


# TODO: Production enhancements needed:
# - Implement distributed transaction coordination (2PC/3PC)
# - Add compensation patterns for complex failure scenarios
# - Implement outbox pattern with reliable event drainer
# - Add transaction performance monitoring and SLA tracking
# - Implement saga pattern for long-running transactions
# - Add transaction replay capability for audit and debugging
# - Implement optimistic concurrency control for high throughput
