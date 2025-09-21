"""
Memory Submit Handler - HTTP Request Routing Logic
=================================================

Complete implementation for Sub-issue #4.2: HTTP request routing logic.
Shows the full flow: HTTP → Middleware → Adapter → Ports → Backend Pipeline.

From MMD diagram: h_submit → ING → CMD → Pipeline P02
"""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, Request

from ...ingress.adapter import IngressAdapter
from ...schemas.core import Envelope, SecurityContext
from ...schemas.requests import SubmitRequest
from ...schemas.responses import SubmitAccepted

logger = logging.getLogger(__name__)


class MemorySubmitHandler:
    """
    Complete implementation of HTTP request routing logic for memory submission.

    Demonstrates the full flow from Sub-issue #4.2:
    HTTP Request → Middleware Chain → IngressAdapter → Port Abstractions → Backend
    """

    def __init__(self, adapter: IngressAdapter):
        self.adapter = adapter

    async def handle_memory_submit(
        self,
        request: SubmitRequest,
        security_context: SecurityContext,
        http_request: Request,
    ) -> SubmitAccepted:
        """
        Complete HTTP request routing logic implementation.

        Step-by-step routing flow:
        1. Validate and prepare request envelope
        2. Apply middleware processing (security, policy, QoS)
        3. Route through IngressAdapter to appropriate port
        4. Handle backend pipeline routing (P01-P20)
        5. Return structured response

        Args:
            request: Validated SubmitRequest from HTTP body
            security_context: Applied by middleware chain
            http_request: FastAPI request with middleware state

        Returns:
            SubmitAccepted response with envelope tracking
        """
        try:
            # Step 1: Create request envelope with metadata
            envelope_id = (
                f"env_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            )

            envelope = Envelope(
                envelope_id=envelope_id,
                operation="submit_memory",
                timestamp=datetime.now(),
                trace_id=uuid4().hex,
                user_id=security_context.user_id,
                space_id=request.space_id,
                metadata={
                    "handler": "memory_submit",
                    "client_ip": (
                        str(http_request.client.host)
                        if http_request.client
                        else "unknown"
                    ),
                    "user_agent": http_request.headers.get("user-agent", "unknown"),
                },
            )

            logger.info(f"Processing memory submit for envelope: {envelope_id}")

            # Step 2: Prepare command payload with SubmitRequest fields
            command_payload = {
                "operation": "submit_memory",
                "data": {
                    "space_id": request.space_id,
                    "text": request.text,
                    "attachments": request.attachments or [],
                    "payload": request.payload or {},
                },
                "pipeline_routing": {
                    "target": "P02",  # Memory submission pipeline
                    "priority": request.qos.priority if request.qos else 5,
                    "routing_context": "memory_submit",
                },
                "metadata": {
                    "submission_time": datetime.now().isoformat(),
                    "envelope_id": envelope_id,
                },
            }

            # Step 3: Route through IngressAdapter to CommandBusPort
            logger.info(f"Routing command through adapter for envelope {envelope_id}")

            command_result = await self.adapter.route_command(
                operation="submit_memory",
                payload=command_payload,
                envelope=envelope,
                request=http_request,
            )

            # Step 4: Route observability event
            await self.adapter.route_observability(
                event_type="memory_submitted",
                data={
                    "envelope_id": envelope_id,
                    "space_id": request.space_id,
                    "status": "accepted",
                    "pipeline": "P02",
                    "command_result": command_result,
                },
                envelope=envelope,
                request=http_request,
            )

            # Step 5: Return structured response
            logger.info(f"Memory submission accepted: {envelope_id}")

            return SubmitAccepted(
                status="accepted",
                envelope_id=envelope_id,
                receipt_url=f"https://api.memoryos.local/v1/receipts/{envelope_id}",
            )

        except Exception as e:
            logger.error(f"Memory submit routing error: {e}")

            # Error observability
            if "envelope" in locals():
                await self.adapter.route_observability(
                    event_type="memory_submit_error",
                    data={
                        "envelope_id": envelope.envelope_id,
                        "error": str(e),
                        "space_id": request.space_id,
                    },
                    envelope=envelope,
                    request=http_request,
                )

            raise HTTPException(
                status_code=500, detail=f"Memory submission failed: {str(e)}"
            )


# Factory function for dependency injection
def create_memory_submit_handler(adapter: IngressAdapter) -> MemorySubmitHandler:
    """Create memory submit handler with injected adapter dependency."""
    return MemorySubmitHandler(adapter)


# Standalone function for backwards compatibility
async def handle_memory_submit(
    request: SubmitRequest,
    envelope: Envelope,
    http_request: Request,
    adapter: IngressAdapter,
) -> SubmitAccepted:
    """
    Standalone handler function showing HTTP request routing logic.

    This function demonstrates Sub-issue #4.2 complete implementation:
    - HTTP request processing
    - Middleware chain integration points
    - IngressAdapter routing
    - Port abstraction usage
    - Backend pipeline targeting
    - Observability integration
    """
    handler = MemorySubmitHandler(adapter)

    # Extract security context from envelope
    security_context = envelope.security_context

    return await handler.handle_memory_submit(
        request=request,
        security_context=security_context,
        http_request=http_request,
    )
