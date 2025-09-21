"""
Memory Recall Handler - HTTP Query Routing Example
=================================================

Simple implementation for Sub-issue #4.2: HTTP request routing logic for queries.
Shows the query flow: HTTP → Middleware → Adapter → QueryFacadePort → Backend.

From MMD diagram: h_recall → ING → QRY → Pipeline P03
"""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, Request

from ...ingress.adapter import IngressAdapter
from ...schemas.core import Envelope, SecurityContext
from ...schemas.requests import RecallRequest
from ...schemas.responses import RecallResponse

logger = logging.getLogger(__name__)


class MemoryRecallHandler:
    """
    HTTP query routing logic example for memory recall.

    Demonstrates complete query routing flow:
    HTTP Request → Middleware → IngressAdapter → QueryFacadePort → Backend Pipeline
    """

    def __init__(self, adapter: IngressAdapter):
        self.adapter = adapter

    async def handle_memory_recall(
        self,
        request: RecallRequest,
        security_context: SecurityContext,
        http_request: Request,
    ) -> RecallResponse:
        """
        Complete HTTP query routing logic implementation.

        Demonstrates Sub-issue #4.2 routing patterns:
        1. Envelope creation with query context
        2. Query parameter preparation
        3. Adapter routing to QueryFacadePort
        4. Result transformation and response
        """
        try:
            # Step 1: Create query envelope
            envelope_id = (
                f"qry_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            )

            envelope = Envelope(
                envelope_id=envelope_id,
                operation="recall_memory",
                timestamp=datetime.now(),
                trace_id=uuid4().hex,
                user_id=security_context.user_id,
                space_id=request.space_id or "default",
                metadata={
                    "handler": "memory_recall",
                    "query_length": len(request.query),
                    "k": request.k or 10,
                },
            )

            logger.info(f"Processing recall query: {envelope_id}")

            # Step 2: Route through adapter
            query_result = await self.adapter.route_query(
                operation="recall_memory",
                params={
                    "query": request.query,
                    "space_id": request.space_id,
                    "k": request.k or 10,
                    "filters": request.filters or {},
                    "return_trace": request.return_trace or False,
                },
                metadata={"envelope_id": envelope_id},
                envelope=envelope,
            )

            # Step 3: Log observability
            await self.adapter.route_observability(
                operation="memory_recalled",
                data={
                    "envelope_id": envelope_id,
                    "status": "success",
                    "result_count": (
                        len(query_result.get("items", [])) if query_result else 0
                    ),
                },
                metadata={"handler": "memory_recall"},
                envelope=envelope,
            )

            logger.info(f"Recall completed: {envelope_id}")

            # Step 4: Return response
            items = query_result.get("items", []) if query_result else []
            trace = query_result.get("trace") if query_result else None

            return RecallResponse(items=items, trace=trace)

        except Exception as e:
            logger.error(f"Recall routing error: {e}")

            raise HTTPException(
                status_code=500, detail=f"Memory recall failed: {str(e)}"
            )


# Factory function
def create_memory_recall_handler(adapter: IngressAdapter) -> MemoryRecallHandler:
    """Create recall handler with adapter dependency."""
    return MemoryRecallHandler(adapter)


# Standalone function for router integration
async def handle_memory_recall(
    request: RecallRequest,
    security_context: SecurityContext,
    http_request: Request,
    adapter: IngressAdapter,
) -> RecallResponse:
    """
    Standalone handler demonstrating Sub-issue #4.2 HTTP routing logic.

    This shows the complete flow from HTTP request to backend pipeline routing.
    """
    handler = MemoryRecallHandler(adapter)

    return await handler.handle_memory_recall(
        request=request,
        security_context=security_context,
        http_request=http_request,
    )
