"""
SSE event streaming handler - GET /v1/events/stream
From MMD diagram: h_events_sse → ING → SSE
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import Request
from fastapi.responses import StreamingResponse

from ..ingress.adapter import get_ingress_adapter
from ..schemas.core import Envelope

logger = logging.getLogger(__name__)


async def get_event_stream(request: Request) -> StreamingResponse:
    """
    Create Server-Sent Events stream.

    From MMD: ep_sse → APP → MW_AUTH → ... → h_events_sse → ING → SSE
    """
    logger.info("Creating SSE event stream")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        try:
            # Get ingress adapter
            adapter = get_ingress_adapter()

            # Create envelope
            envelope = Envelope(envelope_id="sse_stream", operation="events_stream")

            # Route to SSE hub via ingress adapter
            stream = await adapter.route_stream(
                stream_type="events",
                params={
                    "user_id": getattr(request.state, "user_id", None),
                    "space_id": getattr(request.state, "space_id", None),
                },
                envelope=envelope,
                request=request,
            )

            # Stream events to client
            async for event in stream:
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
