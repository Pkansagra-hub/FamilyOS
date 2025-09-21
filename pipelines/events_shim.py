"""
Events Shim - Sub-issue #22.2 Pipeline Integration
==================================================

Integration layer between the pipeline system and the cognitive event system.
Provides event bridging, format conversion, and seamless event flow.

Features:
- Event format conversion between pipelines and cognitive events
- Seamless integration with event bus
- Event enrichment and metadata handling
- Performance optimization for event routing
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventDirection(Enum):
    """Event flow directions."""

    PIPELINE_TO_COGNITIVE = "pipeline_to_cognitive"
    COGNITIVE_TO_PIPELINE = "cognitive_to_pipeline"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class EventBridgeMessage:
    """Message format for event bridge."""

    id: str
    direction: EventDirection
    source_system: str
    target_system: str
    event_type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float
    correlation_id: Optional[str] = None


class EventFormatConverter:
    """Converts events between pipeline and cognitive formats."""

    def __init__(self):
        self.conversion_rules: Dict[str, str] = {
            # Pipeline events -> Cognitive events
            "pipeline_command_executed": "COMMAND_EXECUTED",
            "pipeline_command_failed": "COMMAND_FAILED",
            "pipeline_data_processed": "DATA_PROCESSED",
            "pipeline_health_changed": "PIPELINE_HEALTH_CHANGED",
            # Cognitive events -> Pipeline events
            "MEMORY_CREATED": "memory_event",
            "MEMORY_RECALLED": "memory_event",
            "AFFECT_CHANGED": "affect_event",
            "TRIGGER_FIRED": "trigger_event",
        }

    async def convert_pipeline_to_cognitive(
        self, pipeline_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert pipeline event to cognitive event format."""
        event_type = pipeline_event.get("type", "unknown")
        cognitive_type = self.conversion_rules.get(event_type, event_type.upper())

        # Standard cognitive event envelope
        cognitive_event: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": cognitive_type,
            "timestamp": time.time(),
            "source": "pipeline_system",
            "correlation_id": pipeline_event.get("correlation_id"),
            "metadata": {
                "pipeline_id": pipeline_event.get("pipeline_id"),
                "operation": pipeline_event.get("operation"),
                "original_event_type": event_type,
                **pipeline_event.get("metadata", {}),
            },
            "payload": pipeline_event.get("payload", {}),
        }

        # Add pipeline-specific enrichments
        if "execution_time" in pipeline_event:
            cognitive_event["metadata"]["performance"] = {
                "execution_time": pipeline_event["execution_time"],
                "timestamp": pipeline_event.get("timestamp", time.time()),
            }

        return cognitive_event

    async def convert_cognitive_to_pipeline(
        self, cognitive_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert cognitive event to pipeline event format."""
        event_type = cognitive_event.get("type", "UNKNOWN")
        pipeline_type = self.conversion_rules.get(event_type, event_type.lower())

        # Standard pipeline event format
        pipeline_event: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": pipeline_type,
            "timestamp": time.time(),
            "source": "cognitive_system",
            "correlation_id": cognitive_event.get("correlation_id"),
            "pipeline_id": cognitive_event.get("metadata", {}).get("target_pipeline"),
            "operation": cognitive_event.get("metadata", {}).get("operation"),
            "payload": cognitive_event.get("payload", {}),
            "metadata": {
                "original_event_type": event_type,
                "cognitive_source": cognitive_event.get("source"),
                **cognitive_event.get("metadata", {}),
            },
        }

        return pipeline_event


class EventShim:
    """
    Event integration shim between pipeline and cognitive systems.

    Provides seamless event flow and format conversion between
    the pipeline system and the cognitive event architecture.
    """

    def __init__(self):
        self.converter = EventFormatConverter()
        self.active_bridges: Dict[str, EventBridgeMessage] = {}
        self.event_metrics: Dict[str, Union[int, float]] = {
            "events_bridged": 0,
            "conversion_errors": 0,
            "average_latency": 0.0,
        }

        # Initialize connections
        self._pipeline_bus: Optional[Any] = None
        self._cognitive_bus: Optional[Any] = None

        logger.info("EventShim initialized for pipeline-cognitive integration")

    async def initialize(self):
        """Initialize connections to both event systems."""
        try:
            # Connect to pipeline bus
            from .bus import pipeline_bus

            self._pipeline_bus = pipeline_bus

            # Connect to cognitive event bus (might not exist yet)
            try:
                from events.bus import event_bus  # type: ignore

                self._cognitive_bus = event_bus
            except ImportError:
                logger.warning("Cognitive event bus not available yet")
                self._cognitive_bus = None

            # Set up bidirectional event routing
            await self._setup_event_routing()

            logger.info("EventShim connections established")

        except Exception as e:
            logger.error(f"Failed to initialize EventShim: {e}")
            raise

    async def _setup_event_routing(self):
        """Set up bidirectional event routing between systems."""
        if not self._pipeline_bus:
            raise RuntimeError("Pipeline bus not initialized")

        # Subscribe to pipeline events
        await self._pipeline_bus.subscribe(
            pipeline_id="event_shim",
            handler=self._handle_pipeline_event,
            operations=["*"],  # All operations
        )

        # Subscribe to cognitive events that need pipeline routing (if available)
        if self._cognitive_bus:
            cognitive_event_types = [
                "MEMORY_CREATED",
                "MEMORY_RECALLED",
                "AFFECT_CHANGED",
                "TRIGGER_FIRED",
                "ARBITER_DECISION",
            ]

            for event_type in cognitive_event_types:
                await self._cognitive_bus.subscribe(  # type: ignore
                    event_type, self._handle_cognitive_event
                )

        logger.info("Event routing configured for bidirectional flow")

    async def _handle_pipeline_event(self, pipeline_message: Any) -> None:
        """Handle events from pipeline system and bridge to cognitive."""
        start_time = time.time()

        try:
            # Extract event data from pipeline message
            event_data: Dict[str, Any] = {
                "type": f"pipeline_{pipeline_message.operation}",
                "pipeline_id": pipeline_message.source_pipeline,
                "operation": pipeline_message.operation,
                "payload": pipeline_message.payload,
                "metadata": pipeline_message.metadata,
                "timestamp": pipeline_message.timestamp,
                "correlation_id": pipeline_message.correlation_id,
            }

            # Convert to cognitive format
            cognitive_event = await self.converter.convert_pipeline_to_cognitive(
                event_data
            )

            # Bridge to cognitive system
            await self._bridge_to_cognitive(cognitive_event)

            # Update metrics
            latency = time.time() - start_time
            self._update_metrics(latency, success=True)

            logger.debug(
                f"Bridged pipeline event {pipeline_message.operation} "
                f"to cognitive in {latency:.3f}s"
            )

        except Exception as e:
            latency = time.time() - start_time
            self._update_metrics(latency, success=False)
            logger.error(f"Failed to bridge pipeline event: {e}")

    async def _handle_cognitive_event(self, cognitive_event: Dict[str, Any]) -> None:
        """Handle events from cognitive system and bridge to pipelines."""
        start_time = time.time()

        try:
            # Convert to pipeline format
            pipeline_event = await self.converter.convert_cognitive_to_pipeline(
                cognitive_event
            )

            # Bridge to pipeline system
            await self._bridge_to_pipeline(pipeline_event)

            # Update metrics
            latency = time.time() - start_time
            self._update_metrics(latency, success=True)

            logger.debug(
                f"Bridged cognitive event {cognitive_event.get('type')} "
                f"to pipeline in {latency:.3f}s"
            )

        except Exception as e:
            latency = time.time() - start_time
            self._update_metrics(latency, success=False)
            logger.error(f"Failed to bridge cognitive event: {e}")

    async def _bridge_to_cognitive(self, cognitive_event: Dict[str, Any]) -> None:
        """Bridge event to cognitive system."""
        if not self._cognitive_bus:
            logger.debug("Cognitive event bus not available, skipping bridge")
            return

        await self._cognitive_bus.publish(  # type: ignore
            topic=cognitive_event["type"],
            event=cognitive_event,
        )

    async def _bridge_to_pipeline(self, pipeline_event: Dict[str, Any]) -> None:
        """Bridge event to pipeline system."""
        if not self._pipeline_bus:
            raise RuntimeError("Pipeline event bus not available")

        from .bus import MessagePriority, MessageType

        await self._pipeline_bus.emit(
            message_type=MessageType.EVENT,
            operation=pipeline_event["operation"],
            payload=pipeline_event["payload"],
            source_pipeline="cognitive_system",
            target_pipeline=pipeline_event.get("pipeline_id"),
            priority=MessagePriority.NORMAL,
            metadata=pipeline_event["metadata"],
            correlation_id=pipeline_event.get("correlation_id"),
        )

    def _update_metrics(self, latency: float, success: bool) -> None:
        """Update shim performance metrics."""
        self.event_metrics["events_bridged"] = (
            int(self.event_metrics["events_bridged"]) + 1
        )
        if not success:
            self.event_metrics["conversion_errors"] = (
                int(self.event_metrics["conversion_errors"]) + 1
            )

        # Update average latency with exponential moving average
        alpha = 0.1
        current_avg = float(self.event_metrics["average_latency"])
        self.event_metrics["average_latency"] = (
            1 - alpha
        ) * current_avg + alpha * latency

    async def bridge_manual_event(
        self,
        event_data: Dict[str, Any],
        direction: EventDirection,
        source_system: str,
        target_system: str,
    ) -> str:
        """Manually bridge an event between systems."""
        bridge_id = str(uuid4())

        try:
            bridge_message = EventBridgeMessage(
                id=bridge_id,
                direction=direction,
                source_system=source_system,
                target_system=target_system,
                event_type=event_data.get("type", "unknown"),
                payload=event_data.get("payload", {}),
                metadata=event_data.get("metadata", {}),
                timestamp=time.time(),
                correlation_id=event_data.get("correlation_id"),
            )

            self.active_bridges[bridge_id] = bridge_message

            # Route based on direction
            if direction == EventDirection.PIPELINE_TO_COGNITIVE:
                cognitive_event = await self.converter.convert_pipeline_to_cognitive(
                    event_data
                )
                await self._bridge_to_cognitive(cognitive_event)
            elif direction == EventDirection.COGNITIVE_TO_PIPELINE:
                pipeline_event = await self.converter.convert_cognitive_to_pipeline(
                    event_data
                )
                await self._bridge_to_pipeline(pipeline_event)

            logger.info(
                f"Manual event bridge {bridge_id} completed ({direction.value})"
            )
            return bridge_id

        except Exception as e:
            logger.error(f"Manual event bridge {bridge_id} failed: {e}")
            raise
        finally:
            # Clean up bridge record
            self.active_bridges.pop(bridge_id, None)

    def get_metrics(self) -> Dict[str, Any]:
        """Get event shim performance metrics."""
        total_events = int(self.event_metrics["events_bridged"])
        error_rate = int(self.event_metrics["conversion_errors"]) / max(total_events, 1)

        return {
            "events_bridged": total_events,
            "conversion_errors": int(self.event_metrics["conversion_errors"]),
            "error_rate": error_rate,
            "average_latency_ms": float(self.event_metrics["average_latency"]) * 1000,
            "active_bridges": len(self.active_bridges),
            "is_initialized": self._pipeline_bus is not None
            and self._cognitive_bus is not None,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the event shim."""
        status = "healthy"
        issues: list[str] = []

        if not self._pipeline_bus:
            status = "unhealthy"
            issues.append("Pipeline bus not connected")

        if not self._cognitive_bus:
            status = "degraded"
            issues.append("Cognitive bus not connected")

        total_events = int(self.event_metrics["events_bridged"])
        error_rate = int(self.event_metrics["conversion_errors"]) / max(total_events, 1)
        if error_rate > 0.05:  # More than 5% error rate
            status = "degraded"
            issues.append(f"High error rate: {error_rate:.2%}")

        return {
            "status": status,
            "issues": issues,
            "metrics": self.get_metrics(),
            "connections": {
                "pipeline_bus": self._pipeline_bus is not None,
                "cognitive_bus": self._cognitive_bus is not None,
            },
        }


# Global shim instance for system-wide use
event_shim = EventShim()
