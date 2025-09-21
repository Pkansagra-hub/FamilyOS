"""
Privacy DSAR handler - create | status | cancel
From MMD diagram: h_dsar → ING → CMD/QRY
"""

import logging

from fastapi import HTTPException, Request

from ..ingress.adapter import get_ingress_adapter
from ..schemas.core import Envelope
from ..schemas.requests import DSARRequest
from ..schemas.responses import JobAccepted, JobStatus

logger = logging.getLogger(__name__)


async def create_dsar_request(
    dsar_request: DSARRequest, request: Request
) -> JobAccepted:
    """
    Create DSAR request for GDPR compliance.

    From MMD: ep_dsar_create → CTRL → MW_AUTH → ... → h_dsar → ING → CMD
    """
    logger.info(f"Creating DSAR request: {dsar_request.request_type}")

    try:
        # Get ingress adapter
        adapter = get_ingress_adapter()

        # Create envelope
        envelope = Envelope(
            envelope_id=f"dsar_{dsar_request.request_type}", operation="dsar_create"
        )

        # Route to command bus via ingress adapter
        result = await adapter.route_command(
            operation="dsar_create",
            payload={
                "request_type": dsar_request.request_type,
                "user_id": dsar_request.user_id,
                "space_id": dsar_request.space_id,
                "data_categories": dsar_request.data_categories,
            },
            envelope=envelope,
            request=request,
        )

        return JobAccepted(
            job_id=result["job_id"],
            status="queued",
            estimated_duration=result.get("estimated_duration", "unknown"),
        )

    except Exception as e:
        logger.error(f"Failed to create DSAR request: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create DSAR request: {e}"
        )


async def get_dsar_status(job_id: str, request: Request) -> JobStatus:
    """
    Get DSAR request status.

    From MMD: ep_dsar_status → CTRL → MW_AUTH → ... → h_dsar → ING → QRY
    """
    logger.info(f"Getting DSAR status for job: {job_id}")

    try:
        # Get ingress adapter
        adapter = get_ingress_adapter()

        # Create envelope
        envelope = Envelope(
            envelope_id=f"dsar_status_{job_id}", operation="dsar_status"
        )

        # Route to query facade via ingress adapter
        result = await adapter.route_query(
            operation="dsar_status",
            params={"job_id": job_id},
            envelope=envelope,
            request=request,
        )

        return JobStatus(**result)

    except Exception as e:
        logger.error(f"Failed to get DSAR status {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get DSAR status: {e}")


async def cancel_dsar_request(job_id: str, request: Request) -> JobStatus:
    """
    Cancel DSAR request.

    From MMD: ep_dsar_cancel → CTRL → MW_AUTH → ... → h_dsar → ING → CMD
    """
    logger.info(f"Cancelling DSAR job: {job_id}")

    try:
        # Get ingress adapter
        adapter = get_ingress_adapter()

        # Create envelope
        envelope = Envelope(
            envelope_id=f"dsar_cancel_{job_id}", operation="dsar_cancel"
        )

        # Route to command bus via ingress adapter
        result = await adapter.route_command(
            operation="dsar_cancel",
            payload={"job_id": job_id},
            envelope=envelope,
            request=request,
        )

        return JobStatus(**result)

    except Exception as e:
        logger.error(f"Failed to cancel DSAR {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel DSAR: {e}")
