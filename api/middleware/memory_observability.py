"""
Memory Flow Observability Middleware
====================================

This middleware traces memory integration through all 6 layers:
1. Working Memory (L1/L2/L3 cache)
2. Episodic Memory (temporal events)
3. Semantic Memory (knowledge graph)
4. Procedural Memory (habits/scripts)
5. Social Memory (relationships)
6. Long-term Memory (consolidated)

Integrates with:
- Hippocampus (DG/CA3/CA1 processing)
- Memory Steward (orchestration)
- Events Bus (event-driven flow)
- Storage Layer (persistence)
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MemoryFlowTracker:
    """Tracks memory flow through 6 layers"""

    def __init__(self):
        self.active_flows = {}
        self.memory_stats = {
            "requests_processed": 0,
            "memory_writes_detected": 0,
            "hippocampus_activations": 0,
            "events_published": 0,
            "storage_updates": 0,
        }

        # Memory layer paths to monitor
        self.layer_paths = {
            "working_memory": "workspace/working_memory.db",
            "episodic": "workspace/episodic.db",
            "semantic": "workspace/semantic.db",
            "procedural": "workspace/procedural.db",
            "social": "workspace/social.db",
            "longterm": "workspace/longterm.db",
            "rbac": "data/rbac.json",
            "hippocampus": "workspace/hippocampus",
        }

    def start_flow_tracking(self, request_id: str, endpoint: str) -> Dict[str, Any]:
        """Start tracking a memory flow"""
        flow_data = {
            "request_id": request_id,
            "endpoint": endpoint,
            "start_time": time.time(),
            "layers_activated": [],
            "memory_operations": [],
            "hippocampus_processing": [],
            "events_emitted": [],
            "storage_changes": {},
        }

        # Capture baseline state
        for layer, path in self.layer_paths.items():
            file_path = Path(path)
            if file_path.exists():
                stat = file_path.stat()
                flow_data["storage_changes"][f"{layer}_baseline"] = {
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }

        self.active_flows[request_id] = flow_data
        return flow_data

    def track_memory_operation(
        self, request_id: str, operation: str, layer: str, details: Dict[str, Any]
    ):
        """Track a memory operation"""
        if request_id in self.active_flows:
            self.active_flows[request_id]["memory_operations"].append(
                {
                    "timestamp": time.time(),
                    "operation": operation,
                    "layer": layer,
                    "details": details,
                }
            )

            if layer not in self.active_flows[request_id]["layers_activated"]:
                self.active_flows[request_id]["layers_activated"].append(layer)

    def track_hippocampus_activity(
        self, request_id: str, component: str, activity: str
    ):
        """Track hippocampus processing activity"""
        if request_id in self.active_flows:
            self.active_flows[request_id]["hippocampus_processing"].append(
                {
                    "timestamp": time.time(),
                    "component": component,  # DG, CA3, CA1
                    "activity": activity,
                }
            )
            self.memory_stats["hippocampus_activations"] += 1

    def track_event_emission(
        self, request_id: str, event_type: str, payload: Dict[str, Any]
    ):
        """Track event emissions"""
        if request_id in self.active_flows:
            self.active_flows[request_id]["events_emitted"].append(
                {
                    "timestamp": time.time(),
                    "event_type": event_type,
                    "payload_size": len(str(payload)),
                }
            )
            self.memory_stats["events_published"] += 1

    def finalize_flow_tracking(self, request_id: str) -> Dict[str, Any]:
        """Finalize flow tracking and detect storage changes"""
        if request_id not in self.active_flows:
            return {}

        flow_data = self.active_flows[request_id]
        flow_data["end_time"] = time.time()
        flow_data["duration"] = flow_data["end_time"] - flow_data["start_time"]

        # Check for storage changes
        storage_changes_detected = 0
        for layer, path in self.layer_paths.items():
            file_path = Path(path)
            baseline_key = f"{layer}_baseline"

            if file_path.exists():
                stat = file_path.stat()
                current = {"size": stat.st_size, "modified": stat.st_mtime}

                if baseline_key in flow_data["storage_changes"]:
                    baseline = flow_data["storage_changes"][baseline_key]
                    if (
                        current["size"] != baseline["size"]
                        or current["modified"] != baseline["modified"]
                    ):
                        flow_data["storage_changes"][f"{layer}_change"] = {
                            "size_change": current["size"] - baseline["size"],
                            "time_change": current["modified"] - baseline["modified"],
                            "detected": True,
                        }
                        storage_changes_detected += 1
                else:
                    # New file created
                    flow_data["storage_changes"][f"{layer}_new"] = {
                        "size": current["size"],
                        "created": True,
                    }
                    storage_changes_detected += 1

        # Calculate integration score
        score = 0
        if len(flow_data["layers_activated"]) > 0:
            score += min(
                len(flow_data["layers_activated"]) * 10, 60
            )  # Max 60 for all 6 layers
        if len(flow_data["hippocampus_processing"]) > 0:
            score += 20
        if len(flow_data["events_emitted"]) > 0:
            score += 10
        if storage_changes_detected > 0:
            score += 10

        flow_data["integration_score"] = score
        flow_data["storage_changes_detected"] = storage_changes_detected

        # Update global stats
        self.memory_stats["requests_processed"] += 1
        if storage_changes_detected > 0:
            self.memory_stats["memory_writes_detected"] += 1
            self.memory_stats["storage_updates"] += storage_changes_detected

        # Clean up
        del self.active_flows[request_id]

        return flow_data


# Global tracker instance
memory_tracker = MemoryFlowTracker()


class MemoryObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware to observe memory flow through 6 layers"""

    async def dispatch(self, request: Request, call_next):
        # Only track memory-related endpoints
        memory_endpoints = ["/v1/rbac", "/v1/memory", "/v1/recall", "/v1/write"]

        if not any(
            request.url.path.startswith(endpoint) for endpoint in memory_endpoints
        ):
            return await call_next(request)

        # Generate request ID
        request_id = f"mem_{int(time.time())}_{id(request)}"

        # Start flow tracking
        memory_tracker.start_flow_tracking(request_id, request.url.path)

        # Store in request state for access by other middleware/handlers
        request.state.memory_flow_id = request_id
        request.state.memory_tracker = memory_tracker

        try:
            # Process request
            response = await call_next(request)

            # Track response
            memory_tracker.track_memory_operation(
                request_id,
                "http_response",
                "api",
                {
                    "status_code": response.status_code,
                    "endpoint": request.url.path,
                    "method": request.method,
                },
            )

            # Finalize tracking
            final_data = memory_tracker.finalize_flow_tracking(request_id)

            # Add memory flow headers for debugging
            response.headers["X-Memory-Flow-ID"] = request_id
            response.headers["X-Memory-Layers-Activated"] = str(
                len(final_data.get("layers_activated", []))
            )
            response.headers["X-Memory-Integration-Score"] = str(
                final_data.get("integration_score", 0)
            )
            response.headers["X-Memory-Storage-Changes"] = str(
                final_data.get("storage_changes_detected", 0)
            )

            # Log comprehensive flow data
            if final_data.get("integration_score", 0) > 0:
                logger.info(
                    f"Memory flow completed - ID: {request_id}, Score: {final_data.get('integration_score')}/100, "
                    f"Layers: {len(final_data.get('layers_activated', []))}, "
                    f"Storage changes: {final_data.get('storage_changes_detected', 0)}"
                )

                # Save detailed flow data for analysis
                self._save_flow_data(request_id, final_data)

            return response

        except Exception as e:
            logger.error(f"Memory flow tracking error for {request_id}: {e}")
            # Still finalize tracking even on error
            memory_tracker.finalize_flow_tracking(request_id)
            raise

    def _save_flow_data(self, request_id: str, flow_data: Dict[str, Any]):
        """Save flow data for analysis"""
        try:
            flows_dir = Path("workspace/memory_flows")
            flows_dir.mkdir(exist_ok=True)

            flow_file = flows_dir / f"{request_id}.json"
            with open(flow_file, "w") as f:
                json.dump(flow_data, f, indent=2, default=str)

        except Exception as e:
            logger.warning(f"Failed to save flow data for {request_id}: {e}")


# Helper functions for other components to use


def track_hippocampus_activity(request: Request, component: str, activity: str):
    """Track hippocampus activity from other components"""
    if hasattr(request.state, "memory_flow_id") and hasattr(
        request.state, "memory_tracker"
    ):
        request.state.memory_tracker.track_hippocampus_activity(
            request.state.memory_flow_id, component, activity
        )


def track_memory_operation(
    request: Request, operation: str, layer: str, details: Dict[str, Any]
):
    """Track memory operation from other components"""
    if hasattr(request.state, "memory_flow_id") and hasattr(
        request.state, "memory_tracker"
    ):
        request.state.memory_tracker.track_memory_operation(
            request.state.memory_flow_id, operation, layer, details
        )


def track_event_emission(request: Request, event_type: str, payload: Dict[str, Any]):
    """Track event emission from other components"""
    if hasattr(request.state, "memory_flow_id") and hasattr(
        request.state, "memory_tracker"
    ):
        request.state.memory_tracker.track_event_emission(
            request.state.memory_flow_id, event_type, payload
        )


def get_memory_stats() -> Dict[str, Any]:
    """Get global memory statistics"""
    return memory_tracker.memory_stats.copy()
