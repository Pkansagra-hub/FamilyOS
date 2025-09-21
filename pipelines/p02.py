"""
P02 Pipeline - Write/Ingest Memory Formation
===========================================

Event-driven hippocampal memory formation pipeline following biological architecture.
Subscribes to HIPPO_ENCODE events from EventBus after Attention Gate admission control.

Architecture Flow:
CommandBus → Intent Router → Attention Gate → EventBus → P02 Pipeline

P02 implements hippocampal memory formation using the HippocampusAPI, which orchestrates:
1. DG (Dentate Gyrus): Pattern separation and sparse encoding
2. CA3 (Cornu Ammonis): Content-addressable memory and pattern completion
3. CA1 (Hippocampal Output): Memory consolidation and multi-store persistence

All stages and multi-store persistence are handled by HippocampusAPI.encode_event(),
which coordinates UnitOfWork, semantic extraction, and event emission as per contracts.

Event Integration:
- Subscribes to: HIPPO_ENCODE, WORKSPACE_BROADCAST, SENSORY_FRAME
- Publishes: HIPPO_ENCODED, MEMORY_RECEIPT_CREATED, WORKFLOW_UPDATE
- Storage: Multi-store coordination via UnitOfWork pattern
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

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
from hippocampus.api import HippocampusAPI
from pipelines.bus import MessageType, PipelineMessage

logger = logging.getLogger(__name__)


class ProcessingLane(Enum):
    """Processing lane for hippocampal encoding."""

    FAST = "fast"
    SMART = "smart"


class EncodingStage(Enum):
    """Hippocampal encoding stages."""

    DG_PATTERN_SEPARATION = "dg_pattern_separation"
    CA3_PATTERN_COMPLETION = "ca3_pattern_completion"
    CA1_CONSOLIDATION = "ca1_consolidation"
    MULTI_STORE_PERSISTENCE = "multi_store_persistence"


@dataclass
class P02Result:
    """Result of P02 pipeline processing."""

    success: bool
    event_id: str
    processing_time_ms: float
    lane: ProcessingLane
    stage_completed: Optional[EncodingStage] = None
    memory_receipt_id: Optional[str] = None
    error: Optional[str] = None


class P02Pipeline:
    """
    P02 Write/Ingest Pipeline - Hippocampal Memory Formation

    Event-driven pipeline that subscribes to HIPPO_ENCODE events and performs
    biologically-inspired memory formation through DG→CA3→CA1 architecture.

    Responsibilities:
    - Subscribe to HIPPO_ENCODE events from EventBus
    - Determine processing lane (FAST/SMART) from event metadata
    - Execute hippocampal encoding and storage via HippocampusAPI.encode_event()
    - All DG, CA3, CA1, and multi-store persistence logic is handled by HippocampusAPI
    - Publish completion events (HIPPO_ENCODED, MEMORY_RECEIPT_CREATED)
    """

    def __init__(
        self,
        event_bus: Optional[Any] = None,
        pipeline_bus: Optional[Any] = None,
        hippocampus_api: Optional[HippocampusAPI] = None,
        uow_db_path: str = "family.db",
    ):
        """Initialize P02 pipeline with event subscriptions and hippocampus integration."""
        self.event_bus = event_bus
        self.pipeline_bus = pipeline_bus
        self.hippocampus_api = hippocampus_api or HippocampusAPI()
        self.uow_db_path = uow_db_path
        self.pipeline_id = "P02"
        self.subscriptions: List[Any] = []
        self._processing_stats: Dict[str, Any] = {
            "events_processed": 0,
            "fast_lane_count": 0,
            "smart_lane_count": 0,
            "errors": 0,
            "avg_processing_time_ms": 0.0,
        }

    async def start(self) -> None:
        """Start P02 pipeline and subscribe to events."""
        logger.info("Starting %s pipeline...", self.pipeline_id)

        # Subscribe to EventBus for HIPPO_ENCODE events
        if self.event_bus:
            await self._subscribe_to_events()

        # Subscribe to PipelineBus for internal messages
        if self.pipeline_bus:
            await self._subscribe_to_pipeline_bus()

        logger.info("%s pipeline started successfully", self.pipeline_id)

    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events from EventBus."""
        try:
            # Primary event: HIPPO_ENCODE for memory formation
            subscription_id = await self.event_bus.subscribe(
                EventType.HIPPO_ENCODE.value, self._handle_hippo_encode_event
            )
            self.subscriptions.append(subscription_id)

            # Secondary events: WORKSPACE_BROADCAST, SENSORY_FRAME
            workspace_sub = await self.event_bus.subscribe(
                EventType.WORKSPACE_BROADCAST.value, self._handle_workspace_event
            )
            self.subscriptions.append(workspace_sub)

            sensory_sub = await self.event_bus.subscribe(
                EventType.SENSORY_FRAME.value, self._handle_sensory_event
            )
            self.subscriptions.append(sensory_sub)

            logger.info(
                "P02 subscribed to events: %s", [str(s) for s in self.subscriptions]
            )

        except Exception as e:
            logger.error("Failed to subscribe P02 to events: %s", e)
            raise

    async def _subscribe_to_pipeline_bus(self) -> None:
        """Subscribe to PipelineBus for internal pipeline messages."""
        try:
            await self.pipeline_bus.subscribe(
                pipeline_id=self.pipeline_id,
                handler=self._handle_pipeline_message,
                operations=["memory_submit", "hippocampus_encode"],
                message_types=[MessageType.COMMAND, MessageType.EVENT],
            )
            logger.info("P02 subscribed to PipelineBus")

        except Exception as e:
            logger.error("Failed to subscribe P02 to PipelineBus: %s", e)
            raise

    async def _handle_hippo_encode_event(self, event: Event) -> None:
        """Handle HIPPO_ENCODE event - main memory formation entry point."""
        start_time = time.perf_counter()

        try:
            # Extract processing lane from event metadata
            lane = self._determine_processing_lane(event)

            # Execute hippocampal encoding pipeline
            result = await self._execute_hippocampal_encoding(event, lane)

            # Update statistics
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_processing_stats(
                lane, processing_time_ms, success=result.success
            )

            # Publish completion event
            if result.success:
                await self._publish_completion_event(event, result)

            logger.info(
                "P02 processed HIPPO_ENCODE %s: success=%s, lane=%s, time=%.2fms",
                getattr(event, "id", "unknown"),
                result.success,
                lane.value,
                processing_time_ms,
            )

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_processing_stats(
                ProcessingLane.SMART, processing_time_ms, success=False
            )
            logger.error(
                "P02 failed to process HIPPO_ENCODE %s: %s",
                getattr(event, "id", "unknown"),
                e,
            )

    async def _handle_workspace_event(self, event: Event) -> None:
        """Handle WORKSPACE_BROADCAST event."""
        # TODO: Implement workspace event handling
        logger.debug(
            "P02 received WORKSPACE_BROADCAST %s", getattr(event, "id", "unknown")
        )

    async def _handle_sensory_event(self, event: Event) -> None:
        """Handle SENSORY_FRAME event."""
        # TODO: Implement sensory frame handling
        logger.debug("P02 received SENSORY_FRAME %s", getattr(event, "id", "unknown"))

    async def _handle_pipeline_message(self, message: PipelineMessage) -> None:
        """Handle internal pipeline messages."""
        try:
            if message.operation == "memory_submit":
                # Convert pipeline message to event for processing
                event = self._message_to_event(message)
                await self._handle_hippo_encode_event(event)
            else:
                logger.debug("P02 received pipeline message: %s", message.operation)

        except Exception as e:
            logger.error("P02 failed to handle pipeline message %s: %s", message.id, e)

    def _determine_processing_lane(self, event: Event) -> ProcessingLane:
        """Determine FAST vs SMART processing lane from event metadata."""
        # Check for explicit lane assignment from Intent Router/Attention Gate
        metadata = getattr(event, "metadata", {})
        routing_decision = metadata.get("routing_decision", {})

        if routing_decision.get("decision") == "fast":
            return ProcessingLane.FAST

        # Default to SMART lane for comprehensive processing
        return ProcessingLane.SMART

    async def _execute_hippocampal_encoding(
        self, event: Event, lane: ProcessingLane
    ) -> P02Result:
        """
        Execute hippocampal encoding pipeline using HippocampusAPI.
        All stages (DG, CA3, CA1, storage) are handled by encode_event().
        """
        start_time = time.perf_counter()
        event_id = getattr(event, "id", "unknown")
        try:
            # Extract required parameters from event
            space_id = getattr(event.meta, "space_id", "default")
            event_id = event.meta.id
            # Extract text content from event payload
            text_content = ""
            if hasattr(event, "payload") and event.payload:
                if isinstance(event.payload, str):
                    text_content = event.payload
                elif hasattr(event.payload, "get"):
                    text_content = event.payload.get("content", str(event.payload))
                else:
                    text_content = str(event.payload)
            # Prepare metadata including processing lane
            metadata = {
                "processing_lane": lane.value,
                "pipeline_id": self.pipeline_id,
            }
            # Use HippocampusAPI for full encoding and storage coordination
            await self.hippocampus_api.encode_event(
                space_id=space_id,
                event_id=event_id,
                text=text_content,
                metadata=metadata,
            )
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            # Update statistics
            self._processing_stats["events_processed"] += 1
            if lane == ProcessingLane.FAST:
                self._processing_stats["fast_lane_count"] += 1
            else:
                self._processing_stats["smart_lane_count"] += 1
            current_avg = self._processing_stats["avg_processing_time_ms"]
            events_count = self._processing_stats["events_processed"]
            self._processing_stats["avg_processing_time_ms"] = (
                current_avg * (events_count - 1) + processing_time_ms
            ) / events_count
            return P02Result(
                success=True,
                event_id=event_id,
                processing_time_ms=processing_time_ms,
                lane=lane,
                stage_completed=EncodingStage.MULTI_STORE_PERSISTENCE,
            )
        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Hippocampal encoding failed for %s: %s", event_id, e)
            self._processing_stats["errors"] += 1
            return P02Result(
                success=False,
                event_id=event_id,
                processing_time_ms=processing_time_ms,
                lane=lane,
                error=str(e),
            )

    # All DG, CA3, CA1, and multi-store persistence logic
    # is now handled by HippocampusAPI.encode_event().
    # These methods are deprecated and removed to avoid
    # code duplication and ensure contract compliance.

    def create_event_meta(self, event_id: str, topic: EventType) -> EventMeta:
        """Public method for creating EventMeta."""
        return self._create_event_meta(event_id, topic)

    def _create_event_meta(self, event_id: str, topic: EventType) -> EventMeta:
        """Create EventMeta with default values for P02 pipeline events."""
        return EventMeta(
            topic=topic,
            actor=Actor(user_id="system", caps=[Capability.WRITE]),
            device=Device(device_id="p02_pipeline"),
            space_id="system:pipeline",
            band=SecurityBand.GREEN,
            policy_version="1.0",
            qos=QoS(priority=1, latency_budget_ms=100),
            obligations=[],
            id=event_id,
            ts=datetime.now(timezone.utc),
        )

    async def _publish_completion_event(
        self, original_event: Event, result: P02Result
    ) -> None:
        """Publish HIPPO_ENCODED and MEMORY_RECEIPT_CREATED events."""
        if not self.event_bus:
            return

        try:
            original_event_id = getattr(original_event, "id", "unknown")

            # Publish HIPPO_ENCODED event
            encoded_meta = self._create_event_meta(
                f"encoded_{original_event_id}", EventType.HIPPO_ENCODED
            )
            encoded_event = Event(
                meta=encoded_meta,
                payload={
                    "original_event_id": original_event_id,
                    "processing_lane": result.lane.value,
                    "processing_time_ms": result.processing_time_ms,
                    "stage_completed": (
                        result.stage_completed.value if result.stage_completed else None
                    ),
                },
            )

            await self.event_bus.publish(encoded_event, EventType.HIPPO_ENCODED.value)

            # Publish MEMORY_RECEIPT_CREATED event if receipt was created
            if result.memory_receipt_id:
                receipt_meta = self._create_event_meta(
                    f"receipt_{original_event_id}", EventType.MEMORY_RECEIPT_CREATED
                )
                receipt_event = Event(
                    meta=receipt_meta,
                    payload={
                        "receipt_id": result.memory_receipt_id,
                        "original_event_id": original_event_id,
                        "processing_lane": result.lane.value,
                    },
                )

                await self.event_bus.publish(
                    receipt_event, EventType.MEMORY_RECEIPT_CREATED.value
                )

            logger.debug("P02 published completion events for %s", original_event_id)

        except Exception as e:
            logger.error("Failed to publish P02 completion events: %s", e)

    def _message_to_event(self, message: PipelineMessage) -> Event:
        """Convert PipelineMessage to Event for processing."""
        event_meta = self._create_event_meta(message.id, EventType.HIPPO_ENCODE)
        return Event(
            meta=event_meta,
            payload=message.payload,
        )

    async def execute_hippocampal_encoding(
        self, event: Event, lane: ProcessingLane
    ) -> P02Result:
        """Public method for executing hippocampal encoding."""
        return await self._execute_hippocampal_encoding(event, lane)

    def _update_processing_stats(
        self, lane: ProcessingLane, processing_time_ms: float, success: bool
    ) -> None:
        """Update pipeline processing statistics."""
        self._processing_stats["events_processed"] += 1

        if lane == ProcessingLane.FAST:
            self._processing_stats["fast_lane_count"] += 1
        else:
            self._processing_stats["smart_lane_count"] += 1

        if not success:
            self._processing_stats["errors"] += 1

        # Update rolling average processing time
        current_avg = self._processing_stats["avg_processing_time_ms"]
        event_count = self._processing_stats["events_processed"]
        new_avg = ((current_avg * (event_count - 1)) + processing_time_ms) / event_count
        self._processing_stats["avg_processing_time_ms"] = new_avg

    async def shutdown(self) -> None:
        """Shutdown P02 pipeline and cleanup subscriptions."""
        logger.info("Shutting down %s pipeline...", self.pipeline_id)

        # Unsubscribe from events
        if self.event_bus:
            for subscription_id in self.subscriptions:
                try:
                    await self.event_bus.unsubscribe(subscription_id)
                except Exception as e:
                    logger.warning("Failed to unsubscribe %s: %s", subscription_id, e)

        # Log final statistics
        logger.info("P02 pipeline statistics: %s", self._processing_stats)
        logger.info("%s pipeline shutdown complete", self.pipeline_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get current pipeline processing statistics."""
        return self._processing_stats.copy()


# Factory function for creating P02 pipeline
def create_p02_pipeline(
    event_bus: Optional[Any] = None,
    pipeline_bus: Optional[Any] = None,
) -> P02Pipeline:
    """Create and configure P02 pipeline instance."""
    return P02Pipeline(event_bus=event_bus, pipeline_bus=pipeline_bus)


# Legacy compatibility
class P02Flow:
    """Legacy compatibility wrapper for P02Flow."""

    def __init__(self):
        self.pipeline = create_p02_pipeline()

    async def run(
        self,
        operation: str,
        payload: Dict[str, Any],
        envelope: Any,
        metadata: Dict[str, Any],
    ) -> P02Result:
        """Legacy run method for backward compatibility."""
        # Convert to event and process
        event_meta = self.pipeline.create_event_meta(
            f"legacy_{int(time.time())}", EventType.HIPPO_ENCODE
        )
        event = Event(
            meta=event_meta,
            payload=payload,
        )

        # Determine lane from payload QoS
        qos = payload.get("qos", {})
        latency_budget = qos.get("latency_budget_ms", 100)
        lane = ProcessingLane.FAST if latency_budget < 50 else ProcessingLane.SMART

        # Execute hippocampal encoding
        return await self.pipeline.execute_hippocampal_encoding(event, lane)
