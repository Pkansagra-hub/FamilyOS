"""
Index Health Monitoring & Alerts.

Evaluates index health using metrics and thresholds, produces a status with
reasons, and can emit alerts via registered callbacks. Designed to compose
with IndexLifecycleManager and IndexConfigStore but is standalone/testable.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, TypedDict, cast

logger = logging.getLogger(__name__)


class HealthStatus:
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class HealthThresholds(TypedDict, total=False):
    max_size_mb: float
    max_refresh_latency_ms: float
    max_error_rate: float
    max_stale_minutes: float


def _empty_str_any_dict() -> Dict[str, Any]:
    return {}


def _empty_str_list() -> List[str]:
    return []


def _empty_thresholds() -> "HealthThresholds":
    return cast(HealthThresholds, {})


@dataclass
class HealthMetrics:
    size_mb: float | None = None
    document_count: int | None = None
    last_updated: Optional[datetime] = None
    refresh_latency_ms: float | None = None
    error_rate: float | None = None
    rebuild_in_progress: bool = False
    # Allow extra vendor metrics without type noise
    extra: Dict[str, Any] = field(default_factory=_empty_str_any_dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HealthMetrics":
        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(
                    last_updated.replace("Z", "+00:00")
                )
            except Exception:
                last_updated = None
        return cls(
            size_mb=data.get("size_mb"),
            document_count=data.get("document_count"),
            last_updated=last_updated,
            refresh_latency_ms=data.get("refresh_latency_ms"),
            error_rate=data.get("error_rate"),
            rebuild_in_progress=bool(data.get("rebuild_in_progress", False)),
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "size_mb",
                    "document_count",
                    "last_updated",
                    "refresh_latency_ms",
                    "error_rate",
                    "rebuild_in_progress",
                }
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "size_mb": self.size_mb,
            "document_count": self.document_count,
            "last_updated": (
                self.last_updated.isoformat()
                if isinstance(self.last_updated, datetime)
                else None
            ),
            "refresh_latency_ms": self.refresh_latency_ms,
            "error_rate": self.error_rate,
            "rebuild_in_progress": self.rebuild_in_progress,
        }
        d.update(self.extra)
        return d


@dataclass
class IndexHealth:
    index_name: str
    space_id: str
    status: str
    checked_at: datetime
    reasons: List[str] = field(default_factory=_empty_str_list)
    metrics: HealthMetrics = field(default_factory=HealthMetrics)
    thresholds: HealthThresholds = field(default_factory=_empty_thresholds)

    def to_contract(self) -> Dict[str, Any]:
        return {
            "index_name": self.index_name,
            "space_id": self.space_id,
            "status": self.status,
            "checked_at": self.checked_at.isoformat(),
            "reasons": self.reasons,
            "metrics": self.metrics.to_dict(),
            "thresholds": dict(self.thresholds),
        }


class IndexHealthMonitor:
    """Monitors index health and dispatches alerts on threshold breaches."""

    def __init__(self):
        self._alert_callbacks: List[Callable[[IndexHealth], None]] = []
        self._running = False

    def add_alert_callback(self, cb: Callable[[IndexHealth], None]) -> None:
        self._alert_callbacks.append(cb)

    def evaluate(
        self,
        *,
        index_name: str,
        space_id: str,
        metrics: Dict[str, Any],
        thresholds: Optional[HealthThresholds] = None,
    ) -> IndexHealth:
        """Evaluate health based on provided metrics and thresholds.

        Rules (order matters):
        - If rebuild_in_progress: status at most DEGRADED (unless hard failures).
        - Any hard breach (error_rate > max, refresh latency > max, stale > max) ⇒ DEGRADED/UNHEALTHY based on magnitude.
        - Size over max ⇒ DEGRADED.
        - Missing metrics ⇒ UNKNOWN.
        """

        thresholds = thresholds or {}
        m = HealthMetrics.from_dict(metrics)
        reasons: List[str] = []

        # Unknown if critical fields are missing
        if m.last_updated is None and thresholds.get("max_stale_minutes") is not None:
            health = IndexHealth(
                index_name,
                space_id,
                HealthStatus.UNKNOWN,
                datetime.now(timezone.utc),
                ["missing_last_updated"],
                m,
                thresholds,
            )
            return health

        status = HealthStatus.HEALTHY

        # Staleness check
        if m.last_updated and ("max_stale_minutes" in thresholds):
            stale_for = datetime.now(timezone.utc) - m.last_updated
            max_stale = timedelta(minutes=float(thresholds["max_stale_minutes"]))
            if stale_for > max_stale:
                reasons.append("stale_index_exceeds_max_stale")
                status = HealthStatus.DEGRADED

        # Refresh latency
        if m.refresh_latency_ms is not None and (
            "max_refresh_latency_ms" in thresholds
        ):
            if float(m.refresh_latency_ms) > float(
                thresholds["max_refresh_latency_ms"]
            ):
                reasons.append("refresh_latency_over_threshold")
                status = HealthStatus.DEGRADED

        # Error rate
        if m.error_rate is not None and ("max_error_rate" in thresholds):
            if float(m.error_rate) > float(thresholds["max_error_rate"]):
                reasons.append("error_rate_over_threshold")
                status = HealthStatus.UNHEALTHY

        # Size
        if m.size_mb is not None and ("max_size_mb" in thresholds):
            if float(m.size_mb) > float(thresholds["max_size_mb"]):
                reasons.append("size_over_max")
                # Prefer worse between current and DEGRADED
                status = (
                    HealthStatus.UNHEALTHY
                    if status == HealthStatus.UNHEALTHY
                    else HealthStatus.DEGRADED
                )

        # Rebuild in progress caps the status at DEGRADED unless UNHEALTHY already
        if m.rebuild_in_progress and status == HealthStatus.HEALTHY:
            status = HealthStatus.DEGRADED
            reasons.append("rebuild_in_progress")

        health = IndexHealth(
            index_name=index_name,
            space_id=space_id,
            status=status,
            checked_at=datetime.now(timezone.utc),
            reasons=reasons,
            metrics=m,
            thresholds=thresholds,
        )

        # Alerting
        if status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY):
            for cb in list(self._alert_callbacks):
                try:
                    cb(health)
                except Exception as e:
                    logger.error(f"Health alert callback failed: {e}")

        return health

    async def poll(
        self,
        provider: Callable[[], "asyncio.Future[Dict[str, Any]]"],
        *,
        index_name: str,
        space_id: str,
        thresholds: Optional[HealthThresholds] = None,
        interval_sec: int = 60,
    ) -> None:
        """Run a polling loop that fetches metrics from an async provider and evaluates health."""
        if self._running:
            return
        self._running = True
        try:
            while self._running:
                try:
                    metrics = await provider()
                    self.evaluate(
                        index_name=index_name,
                        space_id=space_id,
                        metrics=metrics,
                        thresholds=thresholds,
                    )
                except Exception as e:
                    logger.error(f"Health polling error: {e}")
                # TODO: Use event-driven monitoring instead of sleep polling
                await asyncio.sleep(min(interval_sec, 10))  # Cap at 10s max
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
