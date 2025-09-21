"""Tests for IndexHealthMonitor."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from ward import test

from storage import (
    HealthMetrics,
    HealthStatus,
    HealthThresholds,
    IndexHealth,
    IndexHealthMonitor,
)


@test("healthy when metrics under thresholds")
async def _():
    mon = IndexHealthMonitor()
    metrics: Dict[str, object] = {
        "size_mb": 50,
        "document_count": 1000,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "refresh_latency_ms": 100,
        "error_rate": 0.0,
        "rebuild_in_progress": False,
    }
    thresholds: HealthThresholds = {
        "max_size_mb": 100,
        "max_refresh_latency_ms": 500,
        "max_error_rate": 0.05,
        "max_stale_minutes": 60,
    }

    h = mon.evaluate(
        index_name="idx",
        space_id="shared:household",
        metrics=metrics,
        thresholds=thresholds,
    )
    assert h.status == HealthStatus.HEALTHY
    assert h.reasons == []


@test("degraded when stale and slow refresh")
async def _():
    mon = IndexHealthMonitor()
    metrics: Dict[str, object] = {
        "size_mb": 10,
        "document_count": 100,
        "last_updated": (
            datetime.now(timezone.utc) - timedelta(minutes=90)
        ).isoformat(),
        "refresh_latency_ms": 1200,
        "error_rate": 0.0,
    }
    thresholds: HealthThresholds = {
        "max_size_mb": 100,
        "max_refresh_latency_ms": 500,
        "max_error_rate": 0.05,
        "max_stale_minutes": 60,
    }

    h = mon.evaluate(
        index_name="idx",
        space_id="shared:household",
        metrics=metrics,
        thresholds=thresholds,
    )
    assert h.status == HealthStatus.DEGRADED
    assert "stale_index_exceeds_max_stale" in h.reasons
    assert "refresh_latency_over_threshold" in h.reasons


@test("unhealthy when error rate and size breach")
async def _():
    mon = IndexHealthMonitor()
    metrics: Dict[str, object] = {
        "size_mb": 200,
        "document_count": 500,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "refresh_latency_ms": 100,
        "error_rate": 0.2,
    }
    thresholds: HealthThresholds = {
        "max_size_mb": 100,
        "max_refresh_latency_ms": 500,
        "max_error_rate": 0.05,
        "max_stale_minutes": 60,
    }

    h = mon.evaluate(
        index_name="idx",
        space_id="shared:household",
        metrics=metrics,
        thresholds=thresholds,
    )
    assert h.status == HealthStatus.UNHEALTHY
    assert "error_rate_over_threshold" in h.reasons
    assert "size_over_max" in h.reasons


@test("degraded when rebuild in progress even if otherwise healthy")
async def _():
    mon = IndexHealthMonitor()
    metrics = HealthMetrics(
        size_mb=1,
        document_count=1,
        last_updated=datetime.now(timezone.utc),
        refresh_latency_ms=1,
        error_rate=0.0,
        rebuild_in_progress=True,
    ).to_dict()

    thresholds: HealthThresholds = {
        "max_size_mb": 10,
        "max_refresh_latency_ms": 100,
        "max_error_rate": 0.5,
        "max_stale_minutes": 10,
    }
    h = mon.evaluate(
        index_name="idx",
        space_id="shared:household",
        metrics=metrics,
        thresholds=thresholds,
    )
    assert h.status == HealthStatus.DEGRADED
    assert "rebuild_in_progress" in h.reasons


@test("unknown when last_updated missing and stale threshold present")
async def _():
    mon = IndexHealthMonitor()
    metrics: Dict[str, object] = {"size_mb": 1, "document_count": 1}
    thresholds: HealthThresholds = {"max_stale_minutes": 10}
    h = mon.evaluate(
        index_name="idx",
        space_id="shared:household",
        metrics=metrics,
        thresholds=thresholds,
    )
    assert h.status == HealthStatus.UNKNOWN
    assert "missing_last_updated" in h.reasons


@test("alert callbacks are invoked on degraded/unhealthy")
async def _():
    mon = IndexHealthMonitor()
    called: List[str] = []

    def cb(health: IndexHealth) -> None:
        called.append(str(health.status))

    mon.add_alert_callback(cb)

    metrics: Dict[str, object] = {
        "size_mb": 200,
        "document_count": 500,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "refresh_latency_ms": 100,
        "error_rate": 0.0,
    }
    thresholds: HealthThresholds = {"max_size_mb": 100}
    h = mon.evaluate(
        index_name="idx",
        space_id="shared:household",
        metrics=metrics,
        thresholds=thresholds,
    )

    assert h.status == HealthStatus.DEGRADED
    assert called == [HealthStatus.DEGRADED]
