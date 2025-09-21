"""
Ingress Adapter - HTTP handlers → Ports
Central routing component (ING) from MMD diagram.

This adapter serves as the critical bridge between HTTP endpoints and backend services,
routing requests through the PEP middleware chain to appropriate port abstractions.

Architecture Flow:
HTTP Request → Router → PEP Chain → IngressAdapter → Port → Backend Service

PEP Chain Order (from MMD diagram):
1. MW_AUTH (SecurityContext, mTLS/JWT)
2. MW_PEP (RBAC/ABAC policy decisions)
3. MW_SEC (Security controls, MLS, keys)
4. MW_SAF (Safety filters, abuse detection)
5. MW_QOS (Quality of Service, rate limiting)
6. MW_OBS (Observability, audit, receipts)
→ IngressAdapter → Ports

Supported Operations:
- Commands: submit, project, detach, undo, dsar_create, security operations
- Queries: recall, receipt_get, dsar_status, tools, roles, sync_status
- Streams: events_sse (Server-Sent Events)
- Observability: metrics, health, audit operations
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from intent.router import IntentRouter
from intent.router import RoutingDecision as IntentRoutingDecision

from ..ports.command_bus import CommandBusPort
from ..ports.event_hub import SSEHubPort
from ..ports.observability import ObservabilityPort
from ..ports.query_facade import QueryFacadePort
from ..schemas.core import Envelope

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """Operation types for routing decisions."""

    COMMAND = "command"  # Write operations → CommandBusPort
    QUERY = "query"  # Read operations → QueryFacadePort
    STREAM = "stream"  # Real-time operations → SSEHubPort
    OBSERVABILITY = "observability"  # Monitoring operations → ObservabilityPort


class RoutingDecision:
    """Encapsulates routing decision with metadata."""

    def __init__(
        self,
        operation_type: OperationType,
        operation_name: str,
        target_pipeline: Optional[str] = None,
        requires_auth: bool = True,
        requires_admin: bool = False,
        qos_priority: Optional[str] = None,
    ):
        self.operation_type = operation_type
        self.operation_name = operation_name
        self.target_pipeline = target_pipeline
        self.requires_auth = requires_auth
        self.requires_admin = requires_admin
        self.qos_priority = qos_priority


class IngressAdapter:
    """
    Central ingress adapter that routes HTTP handlers to port abstractions.

    From MMD diagram: All handlers → ING → CMD/QRY/SSE/OBS ports
    This is the critical bridge between HTTP layer and business logic.

    The adapter receives requests that have already passed through the PEP chain:
    MW_AUTH → MW_PEP → MW_SEC → MW_SAF → MW_QOS → MW_OBS → IngressAdapter

    At this point, the request has:
    - Valid SecurityContext attached to request.state
    - Policy decisions made and authorized
    - Security controls applied
    - Safety filters passed
    - QoS headers processed
    - Observability context established
    """

    # Operation routing map: operation_name → RoutingDecision
    ROUTING_MAP = {
        # Memory operations (Commands)
        "memory_submit": RoutingDecision(OperationType.COMMAND, "memory_submit", "P02"),
        "memory_project": RoutingDecision(
            OperationType.COMMAND, "memory_project", "P01"
        ),
        "memory_refer": RoutingDecision(OperationType.COMMAND, "memory_refer", "P01"),
        "memory_detach": RoutingDecision(OperationType.COMMAND, "memory_detach", "P01"),
        "memory_undo": RoutingDecision(OperationType.COMMAND, "memory_undo", "P01"),
        # Privacy operations (Commands)
        "dsar_create": RoutingDecision(OperationType.COMMAND, "dsar_create", "P11"),
        "dsar_cancel": RoutingDecision(OperationType.COMMAND, "dsar_cancel", "P11"),
        # Security operations (Commands)
        "mls_join": RoutingDecision(OperationType.COMMAND, "mls_join", "P12"),
        "rotate_keys": RoutingDecision(OperationType.COMMAND, "rotate_keys", "P12"),
        "ratchet_advance": RoutingDecision(
            OperationType.COMMAND, "ratchet_advance", "P12"
        ),
        # Index operations (Commands)
        "index_rebuild": RoutingDecision(OperationType.COMMAND, "index_rebuild", "P03"),
        "index_cancel": RoutingDecision(OperationType.COMMAND, "index_cancel", "P03"),
        # RBAC operations (Commands)
        "rbac_bind": RoutingDecision(
            OperationType.COMMAND, "rbac_bind", "P15", requires_admin=True
        ),
        # Sync operations (Commands)
        "sync_peers": RoutingDecision(OperationType.COMMAND, "sync_peers", "P05"),
        # Connector operations (Commands)
        "connector_authorize": RoutingDecision(
            OperationType.COMMAND, "connector_authorize", "P16"
        ),
        # Thing operations (Commands)
        "thing_command": RoutingDecision(OperationType.COMMAND, "thing_command", "P12"),
        # Webhook operations (Commands)
        "webhook_process": RoutingDecision(
            OperationType.COMMAND, "webhook_process", "P16"
        ),
        # Memory operations (Queries)
        "memory_recall": RoutingDecision(OperationType.QUERY, "memory_recall", "P01"),
        "receipt_get": RoutingDecision(OperationType.QUERY, "receipt_get"),
        # Privacy operations (Queries)
        "dsar_status": RoutingDecision(OperationType.QUERY, "dsar_status", "P11"),
        # Index operations (Queries)
        "index_status": RoutingDecision(OperationType.QUERY, "index_status", "P03"),
        # Registry operations (Queries)
        "registry_tools": RoutingDecision(OperationType.QUERY, "registry_tools"),
        "registry_prompts": RoutingDecision(OperationType.QUERY, "registry_prompts"),
        # RBAC operations (Queries)
        "rbac_roles": RoutingDecision(
            OperationType.QUERY, "rbac_roles", requires_admin=True
        ),
        # Sync operations (Queries)
        "sync_status": RoutingDecision(OperationType.QUERY, "sync_status", "P05"),
        # System operations (Queries)
        "flags_get": RoutingDecision(OperationType.QUERY, "flags_get", "P16"),
        "connectors_list": RoutingDecision(
            OperationType.QUERY, "connectors_list", "P16"
        ),
        "things_list": RoutingDecision(OperationType.QUERY, "things_list", "P12"),
        "thing_get": RoutingDecision(OperationType.QUERY, "thing_get", "P12"),
        # Event operations (Streams)
        "events_stream": RoutingDecision(OperationType.STREAM, "events_stream"),
        # Event acknowledgment (Commands)
        "events_ack": RoutingDecision(OperationType.COMMAND, "events_ack"),
    }

    def __init__(
        self,
        command_bus: "CommandBusPort",
        query_facade: "QueryFacadePort",
        sse_hub: "SSEHubPort",
        observability: "ObservabilityPort",
        intent_router: "IntentRouter",
    ):
        self.command_bus = command_bus
        self.query_facade = query_facade
        self.sse_hub = sse_hub
        self.observability = observability
        self.intent_router = intent_router
        logger.info("IngressAdapter initialized with all ports and intent router")

    async def route_request(
        self,
        operation: str,
        data: Any,
        envelope: Envelope,
        request: Request,
    ) -> Any:
        """
        Central routing method that determines operation type and delegates to appropriate port.

        Enhanced with Intent Router integration for fast/smart path routing:
        1. Extract intent from request
        2. Route through intent router for fast/smart path decision
        3. If fast path → direct to port
        4. If smart path → route through attention gate first

        Args:
            operation: Operation name (e.g., "memory_submit", "memory_recall")
            data: Request payload or query parameters
            envelope: Request envelope with metadata
            request: FastAPI request object with middleware state

        Returns:
            Operation result from the appropriate port

        Raises:
            HTTPException: If operation is unknown or routing fails
        """
        if operation not in self.ROUTING_MAP:
            logger.error(f"Unknown operation: {operation}")
            raise HTTPException(
                status_code=400, detail=f"Unknown operation: {operation}"
            )

        routing_decision = self.ROUTING_MAP[operation]

        # Extract context from request state (set by middleware)
        security_context = getattr(request.state, "security_context", None)
        trace_id = getattr(request.state, "trace_id", None)
        qos_priority = getattr(request.state, "qos_priority", None)

        # Build operation metadata
        metadata = {
            "trace_id": trace_id,
            "security_context": security_context,
            "qos_priority": qos_priority or routing_decision.qos_priority,
            "target_pipeline": routing_decision.target_pipeline,
            "requires_admin": routing_decision.requires_admin,
        }

        # PHASE 1: Intent Router Integration - Fast/Smart Path Decision
        try:
            # Prepare request for intent router
            intent_request = {
                "operation": operation,
                "data": data,
                "headers": dict(request.headers) if hasattr(request, "headers") else {},
                "agent_intent": getattr(request.state, "agent_intent", None),
                "confidence": getattr(request.state, "confidence", 0.5),
            }

            # Route through intent router
            intent_result = self.intent_router.route(intent_request, metadata)

            # Add intent routing info to metadata
            metadata["intent_routing"] = {
                "decision": intent_result.decision.value,
                "reason": intent_result.reason.code,
                "confidence": intent_result.confidence,
                "execution_time_us": intent_result.execution_time_us,
            }

            logger.info(
                f"Intent routing: {operation} → {intent_result.decision.value} "
                f"(reason: {intent_result.reason.code}, confidence: {intent_result.confidence})"
            )

            # Smart path routing (through attention gate) will be implemented in Phase 2
            if intent_result.decision == IntentRoutingDecision.SMART_PATH:
                logger.info(
                    f"Smart path routing for {operation} - TODO: Connect attention gate"
                )
                # For now, continue to normal routing
                # TODO Phase 2: Route through attention gate first

        except Exception as e:
            logger.warning(
                f"Intent router error for {operation}: {e}, falling back to normal routing"
            )
            # Continue with normal routing if intent router fails

        logger.info(
            f"Routing {routing_decision.operation_type.value}: {operation} → {routing_decision.target_pipeline}"
        )

        # Route to appropriate port based on operation type
        try:
            if routing_decision.operation_type == OperationType.COMMAND:
                result = await self.route_command(operation, data, envelope, metadata)
            elif routing_decision.operation_type == OperationType.QUERY:
                result = await self.route_query(operation, data, envelope, metadata)
            elif routing_decision.operation_type == OperationType.STREAM:
                result = await self.route_stream(operation, data, envelope, metadata)
            elif routing_decision.operation_type == OperationType.OBSERVABILITY:
                result = await self.route_observability(
                    operation, data, envelope, metadata
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unsupported operation type: {routing_decision.operation_type}",
                )

            # Log successful operation to observability
            await self.observability.log_operation(
                operation=operation,
                result_type=type(result).__name__,
                envelope=envelope,
                metadata=metadata,
            )

            return result

        except Exception as e:
            # Log error to observability
            await self.observability.log_error(
                operation=operation, error=str(e), envelope=envelope, metadata=metadata
            )
            raise

    async def route_command(
        self,
        operation: str,
        payload: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """
        Route write operations to command bus.
        Used by: submit, project, detach, undo, dsar_create, etc.
        """
        logger.info(f"Routing command: {operation}")

        # Send to command bus (pipelines P01-P20)
        result = await self.command_bus.execute_command(
            operation=operation,
            payload=payload,
            envelope=envelope,
            metadata=metadata,
        )

        return result

    async def route_query(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """
        Route read operations to query facade.
        Used by: recall, receipt_get, dsar_status, tools, roles, etc.
        """
        logger.info(f"Routing query: {operation}")

        # Send to query facade
        result = await self.query_facade.execute_query(
            operation=operation,
            params=params,
            envelope=envelope,
            metadata=metadata,
        )

        return result

    async def route_stream(
        self,
        stream_type: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """
        Route streaming operations to SSE hub.
        Used by: events_sse
        """
        logger.info(f"Routing stream: {stream_type}")

        # Send to SSE hub
        result = await self.sse_hub.create_stream(
            stream_type=stream_type,
            params=params,
            envelope=envelope,
            metadata=metadata,
        )

        return result

    async def route_observability(
        self, operation: str, data: Any, envelope: Envelope, metadata: Dict[str, Any]
    ) -> Any:
        """
        Route observability operations to observability port.
        Used by: metrics, health checks, audit logs
        """
        logger.info(f"Routing observability: {operation}")

        return await self.observability.handle_operation(
            operation=operation,
            data=data,
            envelope=envelope,
            metadata=metadata,
        )


# Global ingress adapter instance (dependency injection)
ingress_adapter: Optional[IngressAdapter] = None


def get_ingress_adapter() -> IngressAdapter:
    """Dependency for FastAPI routes."""
    if ingress_adapter is None:
        raise RuntimeError("Ingress adapter not initialized")
    return ingress_adapter


def initialize_ingress_adapter(
    command_bus: "CommandBusPort",
    query_facade: "QueryFacadePort",
    sse_hub: "SSEHubPort",
    observability: "ObservabilityPort",
    intent_router: "IntentRouter",
) -> None:
    """Initialize the global ingress adapter."""
    global ingress_adapter
    ingress_adapter = IngressAdapter(
        command_bus=command_bus,
        query_facade=query_facade,
        sse_hub=sse_hub,
        observability=observability,
        intent_router=intent_router,
    )
    logger.info("Ingress adapter initialized with intent router")
