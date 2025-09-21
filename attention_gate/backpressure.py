"""
Backpressure Management for Attention Gate

Monitors system capacity and triggers flow control decisions
to maintain performance under load.

Future-ready for adaptive thresholds:
- Phase 1: Static thresholds from configuration
- Phase 2: Calibrated thresholds based on performance
- Phase 3: Learning-based threshold adaptation
- Phase 4: Predictive capacity management
"""

import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional

from .config import get_config
from .types import GateAction, GateRequest


class BackpressureResult(NamedTuple):
    """Result of backpressure capacity check"""

    should_defer: bool
    should_drop: bool
    reasons: List[str]
    current_load: float
    estimated_delay_ms: int


class BackpressureManager:
    """
    Manages system capacity and flow control for attention gate.

    Monitors resource utilization and enforces admission limits
    to prevent system overload and maintain performance SLOs.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

        # Capacity tracking
        self.recent_requests: deque = deque(maxlen=1000)
        self.processing_queue_size = 0
        self.error_rate_tracker: deque = deque(maxlen=100)

        # Load tracking windows
        self.load_1min: List[float] = []
        self.load_5min: List[float] = []
        self.last_load_calculation = time.time()

        # Performance tracking
        self.response_times: deque = deque(maxlen=500)
        self.memory_usage_samples: deque = deque(maxlen=100)

        # Learning integration (Phase 3)
        self.adaptive_thresholds = False
        self.threshold_history: List[Dict[str, Any]] = []

    def check_capacity(self, request: GateRequest) -> BackpressureResult:
        """
        Check system capacity and determine if request should be deferred/dropped.

        Returns backpressure decision with reasoning and estimated delays.
        """
        self._update_metrics()

        config = get_config()
        reasons = []
        current_load = self._calculate_current_load()

        # Check various capacity limits
        queue_result = self._check_queue_capacity(config)
        load_result = self._check_load_capacity(current_load, config)
        error_result = self._check_error_rate(config)
        latency_result = self._check_latency_capacity(config)

        # Combine results for decision
        should_defer = False
        should_drop = False

        # Queue capacity
        if queue_result["should_defer"]:
            should_defer = True
            reasons.extend(queue_result["reasons"])

        if queue_result["should_drop"]:
            should_drop = True
            reasons.extend(queue_result["reasons"])

        # Load capacity
        if load_result["should_defer"]:
            should_defer = True
            reasons.extend(load_result["reasons"])

        if load_result["should_drop"]:
            should_drop = True
            reasons.extend(load_result["reasons"])

        # Error rate
        if error_result["should_defer"]:
            should_defer = True
            reasons.extend(error_result["reasons"])

        if error_result["should_drop"]:
            should_drop = True
            reasons.extend(error_result["reasons"])

        # Latency
        if latency_result["should_defer"]:
            should_defer = True
            reasons.extend(latency_result["reasons"])

        # Calculate estimated delay
        estimated_delay = self._estimate_processing_delay(current_load)

        return BackpressureResult(
            should_defer=should_defer,
            should_drop=should_drop,
            reasons=reasons,
            current_load=current_load,
            estimated_delay_ms=estimated_delay,
        )

    def _update_metrics(self) -> None:
        """Update internal metrics and tracking"""
        now = time.time()

        # Clean old requests (older than 5 minutes)
        cutoff = now - 300
        while self.recent_requests and self.recent_requests[0]["timestamp"] < cutoff:
            self.recent_requests.popleft()

        # Update load calculations every 10 seconds
        if now - self.last_load_calculation > 10:
            self._update_load_metrics()
            self.last_load_calculation = now

    def _calculate_current_load(self) -> float:
        """Calculate current system load (0.0 to 1.0+)"""
        now = time.time()

        # Count requests in last minute
        recent_count = sum(
            1 for req in self.recent_requests if req["timestamp"] > now - 60
        )

        # Normalize by expected capacity (requests per minute)
        config = get_config()
        max_capacity = config.backpressure.get("max_requests_per_minute", 1000)

        return recent_count / max_capacity

    def _check_queue_capacity(self, config: Any) -> Dict[str, Any]:
        """Check processing queue capacity"""
        reasons = []
        should_defer = False
        should_drop = False

        max_queue_size = config.backpressure.get("max_queue_size", 100)
        critical_queue_size = config.backpressure.get("critical_queue_size", 200)

        if self.processing_queue_size >= critical_queue_size:
            should_drop = True
            reasons.append(f"queue_size_critical_{self.processing_queue_size}")
        elif self.processing_queue_size >= max_queue_size:
            should_defer = True
            reasons.append(f"queue_size_high_{self.processing_queue_size}")

        return {
            "should_defer": should_defer,
            "should_drop": should_drop,
            "reasons": reasons,
        }

    def _check_load_capacity(self, current_load: float, config: Any) -> Dict[str, Any]:
        """Check overall system load"""
        reasons = []
        should_defer = False
        should_drop = False

        defer_threshold = config.backpressure.get("load_defer_threshold", 0.8)
        drop_threshold = config.backpressure.get("load_drop_threshold", 0.95)

        if current_load >= drop_threshold:
            should_drop = True
            reasons.append(f"load_critical_{current_load:.2f}")
        elif current_load >= defer_threshold:
            should_defer = True
            reasons.append(f"load_high_{current_load:.2f}")

        return {
            "should_defer": should_defer,
            "should_drop": should_drop,
            "reasons": reasons,
        }

    def _check_error_rate(self, config: Any) -> Dict[str, Any]:
        """Check error rate capacity"""
        reasons = []
        should_defer = False
        should_drop = False

        if len(self.error_rate_tracker) < 10:
            return {"should_defer": False, "should_drop": False, "reasons": []}

        error_rate = sum(self.error_rate_tracker) / len(self.error_rate_tracker)

        max_error_rate = config.backpressure.get("max_error_rate", 0.1)
        critical_error_rate = config.backpressure.get("critical_error_rate", 0.2)

        if error_rate >= critical_error_rate:
            should_drop = True
            reasons.append(f"error_rate_critical_{error_rate:.3f}")
        elif error_rate >= max_error_rate:
            should_defer = True
            reasons.append(f"error_rate_high_{error_rate:.3f}")

        return {
            "should_defer": should_defer,
            "should_drop": should_drop,
            "reasons": reasons,
        }

    def _check_latency_capacity(self, config: Any) -> Dict[str, Any]:
        """Check response time capacity"""
        reasons = []
        should_defer = False
        should_drop = False

        if len(self.response_times) < 10:
            return {"should_defer": False, "should_drop": False, "reasons": []}

        # Calculate p95 response time
        sorted_times = sorted(self.response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_latency = sorted_times[p95_index]

        max_p95_latency = config.backpressure.get("max_p95_latency_ms", 500)
        critical_p95_latency = config.backpressure.get("critical_p95_latency_ms", 1000)

        if p95_latency >= critical_p95_latency:
            should_drop = True
            reasons.append(f"latency_critical_p95_{p95_latency:.0f}ms")
        elif p95_latency >= max_p95_latency:
            should_defer = True
            reasons.append(f"latency_high_p95_{p95_latency:.0f}ms")

        return {
            "should_defer": should_defer,
            "should_drop": should_drop,
            "reasons": reasons,
        }

    def _estimate_processing_delay(self, current_load: float) -> int:
        """Estimate processing delay in milliseconds"""
        base_delay = 1000  # 1 second base

        # Scale delay based on load
        if current_load > 0.8:
            load_multiplier = (current_load - 0.8) * 10  # Exponential growth
            delay = base_delay * (1 + load_multiplier)
        else:
            delay = base_delay

        # Add queue delay
        queue_delay = self.processing_queue_size * 50  # 50ms per queued item

        return int(min(delay + queue_delay, 60000))  # Cap at 1 minute

    def _update_load_metrics(self) -> None:
        """Update load calculation windows"""
        current_load = self._calculate_current_load()

        # Update 1-minute window
        self.load_1min.append(current_load)
        if len(self.load_1min) > 6:  # Keep last 6 samples (1 minute at 10s intervals)
            self.load_1min.pop(0)

        # Update 5-minute window
        self.load_5min.append(current_load)
        if len(self.load_5min) > 30:  # Keep last 30 samples (5 minutes)
            self.load_5min.pop(0)

    # Instrumentation methods

    def record_request(self, request_id: str, action: GateAction) -> None:
        """Record a processed request for capacity tracking"""
        self.recent_requests.append(
            {"request_id": request_id, "action": action.value, "timestamp": time.time()}
        )

        # Update queue size based on action
        if action == GateAction.ADMIT or action == GateAction.BOOST:
            self.processing_queue_size += 1
        elif action == GateAction.DEFER:
            # Deferred requests don't enter processing queue immediately
            pass

    def record_completion(
        self, request_id: str, success: bool, latency_ms: float
    ) -> None:
        """Record request completion for metrics"""
        if success:
            self.processing_queue_size = max(0, self.processing_queue_size - 1)
            self.error_rate_tracker.append(0.0)
        else:
            self.error_rate_tracker.append(1.0)

        self.response_times.append(latency_ms)

    def get_capacity_metrics(self) -> Dict[str, Any]:
        """Get current capacity and performance metrics"""
        current_load = self._calculate_current_load()

        metrics = {
            "current_load": current_load,
            "queue_size": self.processing_queue_size,
            "requests_last_minute": len(
                [r for r in self.recent_requests if r["timestamp"] > time.time() - 60]
            ),
            "requests_last_5_minutes": len(
                [r for r in self.recent_requests if r["timestamp"] > time.time() - 300]
            ),
        }

        if self.response_times:
            sorted_times = sorted(self.response_times)
            metrics.update(
                {
                    "latency_p50": sorted_times[len(sorted_times) // 2],
                    "latency_p95": sorted_times[int(len(sorted_times) * 0.95)],
                    "average_latency": sum(self.response_times)
                    / len(self.response_times),
                }
            )

        if self.error_rate_tracker:
            metrics["error_rate"] = sum(self.error_rate_tracker) / len(
                self.error_rate_tracker
            )

        if self.load_1min:
            metrics["load_1min_avg"] = sum(self.load_1min) / len(self.load_1min)

        if self.load_5min:
            metrics["load_5min_avg"] = sum(self.load_5min) / len(self.load_5min)

        return metrics

    # Learning Integration Methods (Future Phases)

    def enable_adaptive_thresholds(self) -> None:
        """Enable adaptive threshold learning (Phase 3)"""
        self.adaptive_thresholds = True

    def calibrate_thresholds(self, performance_feedback: Dict[str, float]) -> None:
        """Calibrate thresholds based on performance feedback (Phase 3)"""
        if not self.adaptive_thresholds:
            return

        # TODO: Implement threshold adaptation based on SLO violations
        # and successful completions under various load conditions
        self.threshold_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "feedback": performance_feedback,
                "current_metrics": self.get_capacity_metrics(),
            }
        )
