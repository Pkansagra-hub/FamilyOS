"""
SSE Hub Port - Real-time Streaming Operations
=============================================

Port abstraction for managing Server-Sent Events (SSE) and real-time streaming.
From MMD diagram: Streams → SSEHubPort → Event System

This port handles all streaming operations:
- Event streaming: events_stream (GET /v1/events/stream)
- Real-time notifications and updates
- Topic-based subscription management with policy filtering
- Connection lifecycle management with backpressure
- Access control integration with ABAC/RBAC

Architecture:
HTTP Handler → IngressAdapter → SSEHubPort → Event System → SSE Response

Features implemented:
- Sub-issue #24.1: Real-time connection management with circuit breaker patterns
- Sub-issue #24.2: Topic subscription handling with ABAC filtering
- Sub-issue #24.3: Backpressure and connection scaling with adaptive throttling
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict, Optional, Set
from uuid import uuid4

from ..schemas.core import Envelope, SecurityBand, SecurityContext

logger = logging.getLogger(__name__)


# Exception classes for SSE operations
class SSEHubError(Exception):
    """Base exception for SSE Hub operations."""

    pass


class StreamValidationError(SSEHubError):
    """Raised when stream validation fails."""

    pass


class AccessDeniedError(SSEHubError):
    """Raised when access control fails."""

    pass


class ConnectionError(SSEHubError):
    """Raised when connection setup fails."""

    pass


class BackpressureError(SSEHubError):
    """Raised when backpressure limits are exceeded."""

    pass


# Data structures for connection management
class ConnectionState(str, Enum):
    """Connection state enumeration."""

    CONNECTING = "connecting"
    ACTIVE = "active"
    THROTTLED = "throttled"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class ConnectionMetrics:
    """Metrics for a single connection."""

    created_at: float
    last_activity: float
    events_sent: int
    bytes_sent: int
    subscription_count: int
    throttle_count: int
    error_count: int


@dataclass
class ConnectionInfo:
    """Comprehensive connection information."""

    connection_id: str
    stream_type: str
    params: Dict[str, Any]
    envelope: Envelope
    metadata: Dict[str, Any]
    security_context: SecurityContext
    state: ConnectionState
    subscribed_topics: Set[str]
    metrics: ConnectionMetrics
    event_queue: "asyncio.Queue[Dict[str, Any]]"
    last_heartbeat: float
    circuit_breaker_failures: int


@dataclass
class TopicFilter:
    """Topic filtering and access control information."""

    topic: str
    security_band: SecurityBand
    space_patterns: Set[str]
    required_capabilities: Set[str]


@dataclass
class SystemMetrics:
    """System-wide SSE metrics."""

    total_connections: int
    active_connections: int
    throttled_connections: int
    total_topics: int
    events_per_second: float
    bytes_per_second: float
    avg_latency_ms: float
    circuit_breaker_trips: int


class SSEHubPort(ABC):
    """
    Abstract base class for SSE hub implementations.

    The SSE hub is responsible for:
    1. Managing client connections and subscriptions (Sub-issue #24.1)
    2. Broadcasting events to subscribed clients
    3. Handling connection lifecycle (connect, disconnect, reconnect)
    4. Managing topic-based subscriptions with ABAC filtering (Sub-issue #24.2)
    5. Providing backpressure and connection scaling (Sub-issue #24.3)
    """

    @abstractmethod
    async def create_stream(
        self,
        stream_type: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        Create a new SSE stream for a client.

        Args:
            stream_type: Type of stream (e.g., "events_stream")
            params: Stream parameters (filters, topics, etc.)
            envelope: Request envelope with security context
            metadata: Additional metadata (trace_id, security_context, etc.)

        Yields:
            SSE formatted event strings

        Raises:
            StreamValidationError: If stream validation fails
            AccessDeniedError: If access control fails
            ConnectionError: If connection setup fails
            BackpressureError: If system is overloaded
        """
        pass

    @abstractmethod
    async def subscribe_to_topics(
        self,
        connection_id: str,
        topics: Set[str],
        envelope: Envelope,
    ) -> bool:
        """
        Subscribe a connection to specific topics with access control.

        Args:
            connection_id: Unique connection identifier
            topics: Set of topic names to subscribe to
            envelope: Request envelope with security context

        Returns:
            True if subscription successful

        Raises:
            AccessDeniedError: If access control fails for any topic
        """
        pass

    @abstractmethod
    async def broadcast_event(
        self,
        topic: str,
        event_data: Dict[str, Any],
        target_connections: Optional[Set[str]] = None,
        security_band: SecurityBand = SecurityBand.GREEN,
    ) -> int:
        """
        Broadcast an event to subscribed connections with band filtering.

        Args:
            topic: Topic name
            event_data: Event payload
            target_connections: Optional set of specific connection IDs
            security_band: Security band of the event

        Returns:
            Number of connections that received the event
        """
        pass

    @abstractmethod
    async def disconnect_client(self, connection_id: str) -> bool:
        """
        Disconnect a client and clean up resources.

        Args:
            connection_id: Connection ID to disconnect

        Returns:
            True if disconnection successful
        """
        pass

    @abstractmethod
    async def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """
        Get detailed information about a connection.

        Args:
            connection_id: Connection ID to query

        Returns:
            ConnectionInfo if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_system_metrics(self) -> SystemMetrics:
        """
        Get system-wide SSE metrics.

        Returns:
            Current system metrics
        """
        pass


class SSEHubImplementation(SSEHubPort):
    """
    Production implementation of SSEHubPort with comprehensive features.

    This implementation provides:
    - Sub-issue #24.1: Real-time connection management with circuit breaker patterns
    - Sub-issue #24.2: Topic subscription handling with ABAC filtering
    - Sub-issue #24.3: Backpressure and connection scaling with adaptive throttling

    Features:
    - Connection lifecycle management with health monitoring
    - Topic-based subscription system with security filtering
    - Event broadcasting with band-aware access control
    - Backpressure handling with adaptive throttling
    - Circuit breaker patterns for connection resilience
    - Comprehensive metrics and monitoring
    """

    def __init__(
        self,
        max_connections: int = 10000,
        max_events_per_sec: int = 1000,
        heartbeat_interval: float = 30.0,
        circuit_breaker_threshold: int = 5,
        queue_size: int = 1000,
        event_bus: Optional[Any] = None,  # Will be injected during startup
    ):
        """Initialize SSE Hub with configurable limits and events integration."""
        # Connection management (Sub-issue #24.1)
        self._connections: Dict[str, ConnectionInfo] = {}
        self._topic_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._topic_filters: Dict[str, TopicFilter] = {}

        # Backpressure and scaling (Sub-issue #24.3)
        self._max_connections = max_connections
        self._max_events_per_sec = max_events_per_sec
        self._heartbeat_interval = heartbeat_interval
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._queue_size = queue_size

        # Metrics tracking
        self._event_counter: deque[float] = deque(maxlen=60)  # Last 60 seconds
        self._byte_counter: deque[int] = deque(maxlen=60)
        self._start_time = time.time()

        # Background tasks
        self._cleanup_task: Optional["asyncio.Task[None]"] = None
        self._metrics_task: Optional["asyncio.Task[None]"] = None

        # Phase 2: Events Bus Integration
        self._event_bus: Optional[Any] = event_bus
        self._bus_subscription: Optional[Any] = None
        self._event_handler_active = False

        # Phase 2: Service integration
        from services import default_service_registry

        self.service_registry = default_service_registry
        self.observability_service = self.service_registry.get_observability_service()

        logger.info(
            f"SSEHubImplementation initialized with max_connections={max_connections} and events integration"
        )

        # Background tasks (will be started when first needed)
        self._background_tasks_started = False

    async def _ensure_background_tasks_started(self) -> None:
        """Ensure background tasks are started (lazy initialization)."""
        if not self._background_tasks_started:
            self._cleanup_task = asyncio.create_task(self._connection_cleanup_loop())
            self._metrics_task = asyncio.create_task(self._metrics_update_loop())
            self._background_tasks_started = True

    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        self._cleanup_task = asyncio.create_task(self._connection_cleanup_loop())
        self._metrics_task = asyncio.create_task(self._metrics_update_loop())

    async def create_stream(
        self,
        stream_type: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """Create SSE stream with comprehensive connection management."""
        connection_id = str(uuid4())
        current_time = time.time()

        logger.info(
            f"Creating SSE stream: {stream_type} for connection {connection_id}"
        )

        # Sub-issue #24.3: Check backpressure limits
        await self._check_backpressure_limits()

        # Ensure background tasks are running
        await self._ensure_background_tasks_started()

        # Sub-issue #24.1: Validate stream and extract security context
        security_context = await self._validate_stream_request(
            stream_type, params, envelope, metadata
        )

        # Sub-issue #24.2: Setup topic subscriptions with access control
        allowed_topics = await self._get_allowed_topics(security_context, params)

        try:
            # Initialize connection info
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                stream_type=stream_type,
                params=params,
                envelope=envelope,
                metadata=metadata,
                security_context=security_context,
                state=ConnectionState.CONNECTING,
                subscribed_topics=set(),
                metrics=ConnectionMetrics(
                    created_at=current_time,
                    last_activity=current_time,
                    events_sent=0,
                    bytes_sent=0,
                    subscription_count=0,
                    throttle_count=0,
                    error_count=0,
                ),
                event_queue=asyncio.Queue(maxsize=self._queue_size),
                last_heartbeat=current_time,
                circuit_breaker_failures=0,
            )

            # Register connection
            self._connections[connection_id] = connection_info
            connection_info.state = ConnectionState.ACTIVE

            # Subscribe to allowed topics
            await self.subscribe_to_topics(connection_id, allowed_topics, envelope)

            # Send initial connection event
            initial_event = {
                "event": "connected",
                "connection_id": connection_id,
                "stream_type": stream_type,
                "subscribed_topics": list(allowed_topics),
                "timestamp": current_time,
            }
            yield f"data: {json.dumps(initial_event)}\n\n"

            # Main streaming loop with circuit breaker pattern
            async for event_str in self._stream_events_loop(connection_id):
                yield event_str

        except Exception as e:
            logger.error(f"Stream error for connection {connection_id}: {e}")
            await self._handle_connection_error(connection_id, str(e))
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Clean up connection
            await self.disconnect_client(connection_id)

    async def _stream_events_loop(self, connection_id: str) -> AsyncIterator[str]:
        """Main event streaming loop with adaptive throttling."""
        connection = self._connections.get(connection_id)
        if not connection:
            return

        try:
            while connection.state == ConnectionState.ACTIVE:
                try:
                    # Wait for event with timeout for heartbeat
                    event_data: Dict[str, Any] = await asyncio.wait_for(
                        connection.event_queue.get(), timeout=self._heartbeat_interval
                    )

                    # Send event
                    event_str = f"data: {json.dumps(event_data)}\n\n"
                    yield event_str

                    # Update metrics
                    connection.metrics.events_sent += 1
                    connection.metrics.bytes_sent += len(event_str)
                    connection.metrics.last_activity = time.time()

                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat: Dict[str, Any] = {
                        "event": "heartbeat",
                        "connection_id": connection_id,
                        "timestamp": time.time(),
                        "metrics": {
                            "events_sent": connection.metrics.events_sent,
                            "uptime": time.time() - connection.metrics.created_at,
                        },
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                    connection.last_heartbeat = time.time()

                except Exception as e:
                    connection.metrics.error_count += 1
                    connection.circuit_breaker_failures += 1

                    # Circuit breaker pattern
                    if (
                        connection.circuit_breaker_failures
                        >= self._circuit_breaker_threshold
                    ):
                        logger.warning(
                            f"Circuit breaker triggered for connection {connection_id}"
                        )
                        connection.state = ConnectionState.DISCONNECTING
                        break

                    logger.error(f"Event streaming error: {e}")

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for connection {connection_id}")
        except Exception as e:
            logger.error(f"Fatal streaming error for connection {connection_id}: {e}")
            await self._handle_connection_error(connection_id, str(e))

    async def subscribe_to_topics(
        self,
        connection_id: str,
        topics: Set[str],
        envelope: Envelope,
    ) -> bool:
        """Subscribe connection to topics with ABAC filtering."""
        logger.debug(f"Subscribing connection {connection_id} to topics: {topics}")

        connection = self._connections.get(connection_id)
        if not connection:
            logger.warning(f"Connection {connection_id} not found for subscription")
            return False

        # Sub-issue #24.2: Apply access control filtering
        allowed_topics = await self._filter_topics_by_access_control(
            topics, connection.security_context, envelope
        )

        if not allowed_topics:
            logger.warning(f"No topics allowed for connection {connection_id}")
            return False

        # Subscribe to allowed topics
        for topic in allowed_topics:
            if topic not in self._topic_subscriptions:
                self._topic_subscriptions[topic] = set()
            self._topic_subscriptions[topic].add(connection_id)
            connection.subscribed_topics.add(topic)

        connection.metrics.subscription_count = len(connection.subscribed_topics)
        logger.info(
            f"Connection {connection_id} subscribed to {len(allowed_topics)} topics"
        )

        return True

    async def broadcast_event(
        self,
        topic: str,
        event_data: Dict[str, Any],
        target_connections: Optional[Set[str]] = None,
        security_band: SecurityBand = SecurityBand.GREEN,
    ) -> int:
        """Broadcast event with band filtering and throttling."""
        logger.debug(f"Broadcasting event to topic: {topic} with band: {security_band}")

        if topic not in self._topic_subscriptions:
            return 0

        # Get target connections
        connections_to_notify = self._topic_subscriptions[topic].copy()
        if target_connections:
            connections_to_notify = connections_to_notify.intersection(
                target_connections
            )

        successful_deliveries = 0

        # Sub-issue #24.2: Apply security band filtering
        for connection_id in connections_to_notify:
            connection = self._connections.get(connection_id)
            if not connection:
                continue

            # Check if connection can receive events with this security band
            if not await self._can_receive_band(connection, security_band):
                continue

            # Sub-issue #24.3: Check connection throttling
            if connection.state == ConnectionState.THROTTLED:
                connection.metrics.throttle_count += 1
                continue

            try:
                # Add event to connection queue (non-blocking)
                enriched_event: Dict[str, Any] = {
                    **event_data,
                    "topic": topic,
                    "security_band": security_band.value,
                    "timestamp": time.time(),
                    "connection_id": connection_id,
                }

                connection.event_queue.put_nowait(enriched_event)
                successful_deliveries += 1

            except asyncio.QueueFull:
                # Queue full - throttle connection
                logger.warning(
                    f"Queue full for connection {connection_id}, applying throttle"
                )
                connection.state = ConnectionState.THROTTLED
                connection.metrics.throttle_count += 1

                # Schedule throttle release
                asyncio.create_task(self._release_throttle_after_delay(connection_id))

            except Exception as e:
                logger.error(
                    f"Failed to queue event for connection {connection_id}: {e}"
                )
                connection.metrics.error_count += 1

        # Update system metrics
        self._event_counter.append(time.time())
        self._byte_counter.append(len(json.dumps(event_data)))

        logger.debug(
            f"Successfully delivered event to {successful_deliveries} connections"
        )
        return successful_deliveries

    async def disconnect_client(self, connection_id: str) -> bool:
        """Disconnect client with comprehensive cleanup."""
        logger.info(f"Disconnecting client: {connection_id}")

        connection = self._connections.get(connection_id)
        if connection:
            connection.state = ConnectionState.DISCONNECTING

        # Remove from connections
        if connection_id in self._connections:
            del self._connections[connection_id]

        # Remove from topic subscriptions
        for subscribers in self._topic_subscriptions.values():
            subscribers.discard(connection_id)

        # Clean up empty topic sets
        empty_topics = [
            topic
            for topic, subscribers in self._topic_subscriptions.items()
            if not subscribers
        ]
        for topic in empty_topics:
            del self._topic_subscriptions[topic]

        return True

    async def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get detailed connection information."""
        return self._connections.get(connection_id)

    async def get_system_metrics(self) -> SystemMetrics:
        """Get comprehensive system metrics."""
        current_time = time.time()

        # Calculate real-time metrics
        current_time = time.time()
        total_connections = len(self._connections)
        active_connections = sum(
            1
            for conn in self._connections.values()
            if conn.state == ConnectionState.ACTIVE
        )
        throttled_connections = sum(
            1
            for conn in self._connections.values()
            if conn.state == ConnectionState.THROTTLED
        )

        # Events per second (last 60 seconds)
        recent_events = [t for t in self._event_counter if current_time - t <= 60]
        events_per_second = len(recent_events) / 60.0 if recent_events else 0.0

        # Bytes per second (last 60 seconds)
        recent_bytes = [b for b in self._byte_counter if current_time - b <= 60]
        bytes_per_second = sum(recent_bytes) / 60.0 if recent_bytes else 0.0

        # Average latency calculation (simplified)
        avg_latency_ms = 5.0  # Placeholder - would calculate from actual timing data

        # Circuit breaker trips
        circuit_breaker_trips = sum(
            conn.circuit_breaker_failures for conn in self._connections.values()
        )

        return SystemMetrics(
            total_connections=total_connections,
            active_connections=active_connections,
            throttled_connections=throttled_connections,
            total_topics=len(self._topic_subscriptions),
            events_per_second=events_per_second,
            bytes_per_second=bytes_per_second,
            avg_latency_ms=avg_latency_ms,
            circuit_breaker_trips=circuit_breaker_trips,
        )

    # Helper methods for access control and validation

    async def _validate_stream_request(
        self,
        stream_type: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> SecurityContext:
        """Validate stream request and extract security context."""
        if stream_type not in ["events_stream", "notifications_stream"]:
            raise StreamValidationError(f"Unsupported stream type: {stream_type}")

        # Extract security context from metadata
        security_context = metadata.get("security_context")
        if not security_context:
            raise AccessDeniedError("Security context required for SSE streams")

        # Basic validation
        if not security_context.authenticated:
            raise AccessDeniedError("Authentication required for SSE streams")

        return security_context

    async def _get_allowed_topics(
        self, security_context: SecurityContext, params: Dict[str, Any]
    ) -> Set[str]:
        """Get topics allowed for security context."""
        # Extract requested topics from parameters
        requested_topics = set(params.get("topics", []))

        # Default topics based on stream type and security level
        default_topics = {
            "memory",
            "policy",
            "security",
            "system",
            "notifications",
            "updates",
            "alerts",
        }

        if not requested_topics:
            requested_topics = default_topics

        # Sub-issue #24.2: Apply ABAC filtering based on capabilities
        allowed_topics: Set[str] = set()
        capabilities = security_context.capabilities or []

        for topic in requested_topics:
            if await self._can_access_topic(topic, capabilities, security_context):
                allowed_topics.add(topic)

        return allowed_topics

    async def _can_access_topic(
        self, topic: str, capabilities: Any, security_context: SecurityContext
    ) -> bool:
        """Check if security context can access topic."""
        # Implement ABAC logic for topic access
        # This would integrate with the policy engine

        # Basic capability-based filtering
        topic_capability_map = {
            "memory": "RECALL",
            "policy": "RECALL",
            "security": "RECALL",
            "system": "RECALL",
            "notifications": "RECALL",
            "updates": "RECALL",
            "alerts": "RECALL",
        }

        required_capability = topic_capability_map.get(topic)
        if required_capability and hasattr(capabilities, "__iter__"):
            return any(str(cap) == required_capability for cap in capabilities)

        return True  # Default allow for now

    async def _filter_topics_by_access_control(
        self, topics: Set[str], security_context: SecurityContext, envelope: Envelope
    ) -> Set[str]:
        """Filter topics by access control policies."""
        allowed_topics: Set[str] = set()
        capabilities = security_context.capabilities or []

        for topic in topics:
            if await self._can_access_topic(topic, capabilities, security_context):
                allowed_topics.add(topic)

        return allowed_topics

    async def _can_receive_band(
        self, connection: ConnectionInfo, security_band: SecurityBand
    ) -> bool:
        """Check if connection can receive events with security band."""
        # Map trust levels to allowed bands
        trust_to_bands: Dict[str, list[SecurityBand]] = {
            "green": [
                SecurityBand.GREEN,
                SecurityBand.AMBER,
                SecurityBand.RED,
                SecurityBand.BLACK,
            ],
            "amber": [SecurityBand.GREEN, SecurityBand.AMBER],
            "red": [SecurityBand.GREEN],
            "black": [],
        }

        trust_level = connection.security_context.trust_level
        if not trust_level:
            return security_band == SecurityBand.GREEN

        allowed_bands: list[SecurityBand] = trust_to_bands.get(
            str(trust_level), [SecurityBand.GREEN]
        )
        return security_band in allowed_bands

    async def _check_backpressure_limits(self) -> None:
        """Check system backpressure limits."""
        if len(self._connections) >= self._max_connections:
            raise BackpressureError(
                f"Maximum connections limit reached: {self._max_connections}"
            )

        # Check events per second
        current_time = time.time()
        recent_events = [t for t in self._event_counter if current_time - t <= 1.0]
        if len(recent_events) >= self._max_events_per_sec:
            raise BackpressureError(
                f"Maximum events per second limit reached: {self._max_events_per_sec}"
            )

    async def _handle_connection_error(self, connection_id: str, error: str) -> None:
        """Handle connection errors with circuit breaker logic."""
        connection = self._connections.get(connection_id)
        if connection:
            connection.metrics.error_count += 1
            connection.circuit_breaker_failures += 1

            if connection.circuit_breaker_failures >= self._circuit_breaker_threshold:
                logger.warning(
                    f"Circuit breaker triggered for connection {connection_id}"
                )
                connection.state = ConnectionState.DISCONNECTING

    async def _release_throttle_after_delay(
        self, connection_id: str, delay: float = 5.0
    ) -> None:
        """Release connection throttle immediately - no artificial delays in production."""
        # TODO: Implement proper resource-based throttle release instead of time delays
        connection = self._connections.get(connection_id)
        if connection and connection.state == ConnectionState.THROTTLED:
            connection.state = ConnectionState.ACTIVE
            logger.info(f"Released throttle for connection {connection_id}")

    async def _connection_cleanup_loop(self) -> None:
        """Background task for connection cleanup."""
        while True:
            try:
                # TODO: Use event-driven cleanup instead of polling
                await asyncio.sleep(30)  # Reduced from 60s for better responsiveness
                current_time = time.time()

                # Find stale connections
                stale_connections: list[str] = []
                for connection_id, connection in self._connections.items():
                    if (current_time - connection.last_heartbeat) > (
                        self._heartbeat_interval * 3
                    ):
                        stale_connections.append(connection_id)

                # Clean up stale connections
                for connection_id in stale_connections:
                    logger.info(f"Cleaning up stale connection: {connection_id}")
                    await self.disconnect_client(connection_id)

            except Exception as e:
                logger.error(f"Error in connection cleanup loop: {e}")

    async def _metrics_update_loop(self) -> None:
        """Background task for metrics updates."""
        while True:
            try:
                # TODO: Use event-driven metrics updates instead of polling
                await asyncio.sleep(5)  # Reduced from 10s for better metrics accuracy

                # Clean old metric data
                current_time = time.time()
                cutoff_time = current_time - 60

                # Remove events older than 60 seconds
                while self._event_counter and self._event_counter[0] < cutoff_time:
                    self._event_counter.popleft()

                while self._byte_counter and self._byte_counter[0] < cutoff_time:
                    self._byte_counter.popleft()

            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")

    # Phase 2: Events Bus Integration Methods
    async def set_event_bus(self, event_bus: Any) -> None:
        """
        Set the events bus and start subscribing to events for live streaming.

        This method completes the SSE → Events Bus integration for real-time event streaming.
        Called during service startup to inject the events bus dependency.
        """
        if self._event_bus is not None:
            logger.warning("Event bus already set, skipping re-initialization")
            return

        self._event_bus = event_bus

        # Subscribe to all events for live streaming
        if self._event_bus and not self._event_handler_active:
            try:
                # Use wildcard pattern to capture all events
                self._bus_subscription = await self._event_bus.subscribe(
                    topic_pattern="*",  # Subscribe to all events
                    handler=self._handle_event_for_streaming,
                    priority=5,  # Medium priority for SSE delivery
                    filters={"source": "not_sse_hub"},  # Avoid feedback loops
                )
                self._event_handler_active = True
                logger.info(
                    "SSE Hub successfully subscribed to events bus for live streaming"
                )

            except Exception as e:
                logger.error(f"Failed to subscribe SSE Hub to events bus: {e}")

    async def _handle_event_for_streaming(self, event: Any) -> None:
        """
        Handle events from the bus and route them to appropriate SSE connections.

        This is the core integration point that converts events bus events
        into SSE streams for connected clients.
        """
        try:
            # Extract event information
            event_topic = getattr(event, "topic", "unknown")
            event_data: Dict[str, Any] = {
                "event": "live_event",
                "topic": event_topic,
                "timestamp": time.time(),
                "data": getattr(event, "payload", {}),
                "metadata": {
                    "event_id": getattr(event, "id", "unknown"),
                    "event_type": str(type(event).__name__),
                    "source": "events_bus",
                },
            }

            # Determine security band from event
            security_band = SecurityBand.GREEN  # Default
            if hasattr(event, "envelope") and event.envelope:
                band_str = getattr(event.envelope, "band", "GREEN")
                try:
                    security_band = SecurityBand(band_str)
                except ValueError:
                    security_band = SecurityBand.GREEN

            # Broadcast to subscribed connections with band filtering
            delivered_count = await self.broadcast_event(
                topic=event_topic,
                event_data=event_data,
                target_connections=None,  # All eligible connections
                security_band=security_band,
            )

            if delivered_count > 0:
                logger.debug(
                    f"Live event {event_topic} delivered to {delivered_count} SSE connections"
                )

        except Exception as e:
            logger.error(f"Error handling event for SSE streaming: {e}", exc_info=True)

    async def get_events_bus_status(self) -> Dict[str, Any]:
        """Get the current status of events bus integration."""
        return {
            "events_bus_connected": self._event_bus is not None,
            "event_handler_active": self._event_handler_active,
            "subscription_id": (
                getattr(self._bus_subscription, "subscription_id", None)
                if self._bus_subscription
                else None
            ),
            "integration_status": (
                "ready"
                if (self._event_bus and self._event_handler_active)
                else "pending"
            ),
        }

    async def disconnect_from_events_bus(self) -> None:
        """Disconnect from events bus and clean up subscription."""
        if self._bus_subscription and self._event_bus:
            try:
                # Unsubscribe from events bus (not async)
                if hasattr(self._event_bus, "unsubscribe"):
                    self._event_bus.unsubscribe(self._bus_subscription)

                self._bus_subscription = None
                self._event_handler_active = False
                logger.info("SSE Hub disconnected from events bus")

            except Exception as e:
                logger.error(f"Error disconnecting from events bus: {e}")


# Default instance for dependency injection
default_sse_hub = SSEHubImplementation()
