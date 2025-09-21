"""
Receipt retrieval handler - GET /v1/receipts/{envelope_id}
From MMD diagram: h_receipt → ING → QRY
"""

import logging

from fastapi import HTTPException, Request

from ..ingress.adapter import get_ingress_adapter
from ..schemas.core import Envelope
from ..schemas.responses import Receipt

logger = logging.getLogger(__name__)


async def get_receipt(envelope_id: str, request: Request) -> Receipt:
    """
    Get receipt for a specific envelope ID.

    From MMD: ep_receipt → APP → MW_AUTH → ... → h_receipt → ING → QRY
    """
    logger.info(f"Getting receipt for envelope: {envelope_id}")

    try:
        # Get ingress adapter
        adapter = get_ingress_adapter()

        # Create envelope (simplified for now)
        envelope = Envelope(envelope_id=envelope_id, operation="receipt_get")

        # Route to query facade via ingress adapter
        result = await adapter.route_query(
            operation="receipt_get",
            params={"envelope_id": envelope_id},
            envelope=envelope,
            request=request,
        )

        return Receipt(**result)

    except Exception as e:
        logger.error(f"Failed to get receipt {envelope_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get receipt: {e}")
