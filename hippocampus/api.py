"""
Hippocampus API - Unified Interface

This module provides the main API for the hippocampus system, orchestrating:
- DG Pattern Separation (encoding)
- CA3 Pattern Completion (recall)
- CA1 Semantic Bridge (knowledge graph projection)
- Storage coordination via UnitOfWork

The HippocampusAPI class provides a unified interface for memory operations
while coordinating all the individual components and handling storage transactions.

Main Operations:
- encode_event() - Full DG→CA1→Storage pipeline for new memories
- recall_by_cue() - CA3 completion with optional semantic enhancement
- get_encoding() - Retrieve stored hippocampal codes
- project_semantics() - Extract and store semantic facts

Integration Points:
- UnitOfWork for atomic storage operations
- Event bus for HIPPO_ENCODE emissions
- Embeddings service for vector operations
- Configurable storage backends
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hippocampus.bridge import CA1SemanticBridge, ExtractionConfig
from hippocampus.completer import CA3PatternCompleter, CompletionConfig
from hippocampus.sdr import SDRProcessor
from hippocampus.separator import DentateGyrusSeparator
from hippocampus.types import (
    CompletionCandidate,
    HippocampalEncoding,
    SemanticProjection,
)
from observability.logging import get_json_logger

logger = get_json_logger(__name__)


@dataclass
class HippocampusConfig:
    """Configuration for the unified hippocampus system."""

    # Component-specific configs
    completion_config: Optional[CompletionConfig] = None
    extraction_config: Optional[ExtractionConfig] = None

    # API behavior
    auto_extract_semantics: bool = True  # Automatically run CA1 bridge on encoding
    enable_vector_fusion: bool = True  # Use vector + SDR fusion for recall
    storage_timeout: float = 5.0  # Timeout for storage operations


class HippocampusAPI:
    """
    Unified Hippocampus API.

    Orchestrates the complete hippocampal memory system including
    encoding (DG), completion (CA3), semantic extraction (CA1),
    and storage coordination.
    """

    def __init__(
        self,
        config: Optional[HippocampusConfig] = None,
        # Storage dependencies (injected for testability)
        hippocampus_store=None,
        vector_store=None,
        semantic_store=None,
        unit_of_work=None,
        event_bus=None,
    ):
        self.config = config or HippocampusConfig()

        # Storage components
        self.hippocampus_store = hippocampus_store
        self.vector_store = vector_store
        self.semantic_store = semantic_store
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus

        # Initialize hippocampus components
        self.sdr_processor = SDRProcessor()

        self.dg_separator = DentateGyrusSeparator()

        self.ca3_completer = CA3PatternCompleter(
            self.sdr_processor,
            config=self.config.completion_config,
            hippocampus_store=hippocampus_store,
            vector_store=vector_store,
        )

        self.ca1_bridge = CA1SemanticBridge(
            config=self.config.extraction_config, semantic_store=semantic_store
        )

        logger.info(
            "HippocampusAPI initialized",
            extra={
                "auto_extract_semantics": self.config.auto_extract_semantics,
                "enable_vector_fusion": self.config.enable_vector_fusion,
                "has_hippocampus_store": hippocampus_store is not None,
                "has_vector_store": vector_store is not None,
                "has_semantic_store": semantic_store is not None,
                "has_unit_of_work": unit_of_work is not None,
                "has_event_bus": event_bus is not None,
            },
        )

    async def encode_event(
        self,
        space_id: str,
        event_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HippocampalEncoding:
        """
        Encode a new event through the full hippocampal pipeline.

        Flow: DG Encoding → CA1 Semantic Extraction → Storage Commit → Event Emission

        Args:
            space_id: Space identifier for the event
            event_id: Unique event identifier
            text: Text content to encode
            metadata: Optional metadata for the event

        Returns:
            HippocampalEncoding with codes and extracted semantics

        Raises:
            ValueError: If encoding fails
        """
        logger.info(
            "Starting event encoding",
            extra={
                "space_id": space_id,
                "event_id": event_id,
                "text_length": len(text),
                "has_metadata": metadata is not None,
            },
        )

        try:
            # Step 1: DG Pattern Separation
            encoding = await self.dg_separator.encode_event(
                space_id=space_id, event_id=event_id, text=text, metadata=metadata
            )

            # Step 2: CA1 Semantic Extraction (if enabled)
            semantic_projection = None
            if self.config.auto_extract_semantics:
                semantic_projection = await self.ca1_bridge.extract_semantics(
                    encoding, text
                )

                # Store semantic facts
                if self.semantic_store:
                    await self.ca1_bridge.project_to_storage(semantic_projection)

            # Step 3: Storage coordination via UnitOfWork
            if self.unit_of_work:
                async with self.unit_of_work:
                    # Hippocampus codes already stored by DG separator
                    # Semantic facts already stored by CA1 bridge
                    # Commit all changes atomically
                    await self.unit_of_work.commit()

            # Step 4: Event emission
            if self.event_bus:
                await self._emit_hippo_encode_event(encoding, semantic_projection)

            logger.info(
                "Event encoding complete",
                extra={
                    "event_id": event_id,
                    "novelty": encoding.novelty,
                    "near_duplicates": len(encoding.near_duplicates),
                    "semantic_facts": (
                        len(semantic_projection.facts) if semantic_projection else 0
                    ),
                },
            )

            return encoding

        except Exception as e:
            logger.error(
                "Event encoding failed",
                extra={"event_id": event_id, "space_id": space_id, "error": str(e)},
            )
            raise

    async def recall_by_cue(
        self,
        space_id: str,
        cue_text: str,
        k: int = 10,
        use_vectors: Optional[bool] = None,
    ) -> List[CompletionCandidate]:
        """
        Recall memories using CA3 pattern completion.

        Args:
            space_id: Space to search within
            cue_text: Text cue for memory recall
            k: Number of results to return
            use_vectors: Override vector fusion setting

        Returns:
            List of completion candidates ranked by relevance
        """
        logger.info(
            "Starting memory recall",
            extra={
                "space_id": space_id,
                "cue_text": cue_text[:100],  # Truncate for logging
                "k": k,
                "use_vectors": use_vectors,
            },
        )

        try:
            # Generate embedding if vector fusion enabled
            cue_embedding = None
            if (
                use_vectors
                or (use_vectors is None and self.config.enable_vector_fusion)
            ) and self.vector_store:
                # For now, create a stub embedding
                # TODO: Replace with actual embedding service integration
                logger.debug(
                    "Vector fusion enabled, using stub embedding",
                    extra={"cue_text": cue_text[:50]},
                )
                # Use a simple hash-based stub embedding for now
                import hashlib

                hash_digest = hashlib.sha256(cue_text.encode()).digest()
                cue_embedding = [int(b) for b in hash_digest[:64]]  # 64-dim stub

            # CA3 pattern completion
            candidates = await self.ca3_completer.complete_pattern(
                space_id=space_id, cue_text=cue_text, k=k, cue_embedding=cue_embedding
            )

            logger.info(
                "Memory recall complete",
                extra={
                    "space_id": space_id,
                    "candidates_found": len(candidates),
                    "top_score": candidates[0].score if candidates else 0.0,
                },
            )

            return candidates

        except Exception as e:
            logger.error(
                "Memory recall failed", extra={"space_id": space_id, "error": str(e)}
            )
            raise

    async def get_encoding(self, event_id: str) -> Optional[HippocampalEncoding]:
        """Retrieve stored hippocampal encoding by event ID."""
        if not self.hippocampus_store:
            return None

        try:
            # Get raw record from store
            record = await self.hippocampus_store.get_encoding(event_id)
            if not record:
                return None

            # Convert to HippocampalEncoding
            encoding = HippocampalEncoding(
                event_id=record["id"],
                space_id=record["space_id"],
                simhash_hex=record["simhash_hex"],
                minhash32=record["minhash32"],
                novelty=record["novelty"],
                near_duplicates=[],  # Not stored in DB, would need separate query
                length=record.get("meta", {}).get("length", 0),
                ts=datetime.fromisoformat(record["ts"]),
                metadata=record.get("meta", {}),
            )

            logger.debug("Retrieved encoding", extra={"event_id": event_id})
            return encoding

        except Exception as e:
            logger.error(
                "Failed to retrieve encoding",
                extra={"event_id": event_id, "error": str(e)},
            )
            return None

    async def _emit_hippo_encode_event(
        self,
        encoding: HippocampalEncoding,
        semantic_projection: Optional[SemanticProjection],
    ) -> None:
        """Emit HIPPO_ENCODED event to the event bus."""
        if not self.event_bus:
            logger.debug("No event bus configured, skipping event emission")
            return

        try:
            # Import here to avoid circular imports
            from events.types import (
                Actor,
                Capability,
                Device,
                Event,
                EventMeta,
                EventType,
                QoS,
                SecurityBand,
            )

            # Create event payload with encoding results
            event_data = {
                "event_id": encoding.event_id,
                "space_id": encoding.space_id,
                "simhash_hex": encoding.simhash_hex,
                "novelty": encoding.novelty,
                "near_duplicates": len(encoding.near_duplicates),
                "semantic_facts": (
                    len(semantic_projection.facts) if semantic_projection else 0
                ),
                "timestamp": encoding.ts.isoformat(),
                "source": "hippocampus_api",
                "pipeline": "P02",
            }

            # Create event metadata
            event_meta = EventMeta(
                topic=EventType.HIPPO_ENCODED,
                actor=Actor(user_id="system", caps=[Capability.WRITE]),
                device=Device(device_id="hippocampus_api"),
                space_id=encoding.space_id,
                band=SecurityBand.GREEN,
                policy_version="1.0",
                qos=QoS(priority=1, latency_budget_ms=100),
                obligations=[],
                id=f"hippo_encoded_{encoding.event_id}",
                ts=datetime.now(timezone.utc),
            )

            # Create event
            event = Event(meta=event_meta, payload=event_data)

            # Publish to event bus
            await self.event_bus.publish(event, EventType.HIPPO_ENCODED.value)

            logger.info(
                "HIPPO_ENCODED event emitted",
                extra={
                    "event_id": encoding.event_id,
                    "space_id": encoding.space_id,
                    "novelty": encoding.novelty,
                },
            )

        except Exception as e:
            logger.warning(
                "Failed to emit HIPPO_ENCODED event",
                extra={"event_id": encoding.event_id, "error": str(e)},
            )


# TODO: Production integration points
# - Replace stub embedding with actual embedding service integration
# - Add comprehensive error handling and retries
# - Add performance monitoring and metrics
# - Add configuration validation and defaults
# - Implement proper vector similarity search in recall operations
