"""
Event acknowledgment handler - POST /v1/events/ack
From MMD diagram: h_events_ack → ING → CMD
"""

import logging

from fastapi import Request

from ..ingress.adapter import get_ingress_adapter
from ..schemas.core import Envelope
from ..schemas.requests import EventAckRequest
from ..schemas.responses import StandardResponse

logger = logging.getLogger(__name__)


async def acknowledge_event(
    ack_request: EventAckRequest, request: Request
) -> StandardResponse:
    """
    Acknowledge event processing.

    From MMD: ep_ack → APP → MW_AUTH → ... → h_events_ack → ING → CMD
    """
    logger.info(f"Acknowledging event: {ack_request.event_id}")

    try:
        # Get ingress adapter
        adapter = get_ingress_adapter()

        # Create envelope
        envelope = Envelope(
            envelope_id=f"ack_{ack_request.event_id}", operation="event_ack"
        )

        # Route to command bus via ingress adapter
        result = await adapter.route_command(
            operation="event_ack",
            payload={
                "event_id": ack_request.event_id,
                "status": ack_request.status,
                "metadata": ack_request.metadata,
            },
            envelope=envelope,
            request=request,
        )

        return StandardResponse(
            success=True, message="Event acknowledged successfully", data=result
        )

    except Exception as e:
        logger.error(f"Failed to acknowledge event {ack_request.event_id}: {e}")
        return StandardResponse(
            success=False, message=f"Failed to acknowledge event: {e}"
        )
