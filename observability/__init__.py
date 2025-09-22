"""
Memory-Centric Observability System
===================================

Comprehensive observability for Family AI's Memory Backbone architecture.
Tracks envelope lifecycle through Memory Operations, Cognitive Processing, 
and Family Memory Network with real-time dashboard visualization.

Architecture Components:
- Memory Backbone: Central nervous system for family intelligence
- API Planes: Agent (LLM), Tool (Apps), Control (Admin)
- 20 Specialized Pipelines: P01-P20 for memory processing
- Cognitive Architecture: Attention, Working Memory, Hippocampus, Global Workspace
- Family Memory Network: Device-local storage with E2EE sync

Envelope Tracking:
- Request → API Plane → Memory Engine → Cognitive Processing → Storage → Family Sync
- Real-time transformations and memory operations
- Cross-device family intelligence coordination
"""

from .envelope import EnvelopeTracker, MemoryEnvelope
from .memory_trace import MemoryTracer, CognitiveSpan
from .metrics import PipelineMetrics, MemoryMetrics
from .dashboard import ObservabilityDashboard
from .middleware import MemoryTracingMiddleware

__all__ = [
    "EnvelopeTracker",
    "MemoryEnvelope", 
    "MemoryTracer",
    "CognitiveSpan",
    "PipelineMetrics",
    "MemoryMetrics",
    "ObservabilityDashboard",
    "MemoryTracingMiddleware"
]

__version__ = "1.0.0"