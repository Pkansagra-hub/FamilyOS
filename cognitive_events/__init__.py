"""
Cognitive Event Router - Smart-Path Processing for Brain-Inspired Coordination
==============================================================================

This module implements the cognitive event routing system that coordinates
cross-namespace cognitive processing using brain-inspired patterns. It provides
sophisticated dispatching, consumer group management, backpressure handling,
and dead letter queues for failed cognitive processing.

**Key Components:**
- CognitiveDispatcher: Central routing for cognitive.* events
- ConsumerGroups: Pipeline consumer management with load balancing
- BackpressureHandler: Cross-module flow control with adaptive throttling
- DLQManager: Failed cognitive processing with retry strategies
- IdempotencyLedger: Global operation deduplication

**Architecture:**
- Event-driven cognitive coordination across memory, attention, learning
- Brain-inspired processing patterns with neuroplasticity
- Production-ready with ACID transactions and comprehensive observability
- Hierarchical routing: cognitive.memory.* ↔ cognitive.attention.* ↔ cognitive.learning.*

The router enables seamless cognitive event flow while maintaining system
stability through adaptive backpressure and comprehensive error handling.
"""

# Import main types first to avoid circular dependencies
from .types import (
    CognitiveError,
    CognitiveEvent,
    CognitiveEventType,
    CognitiveProcessingResult,
    RoutingDecision,
    create_attention_event,
    create_cognitive_event,
    create_memory_write_event,
    create_recall_request_event,
    create_working_memory_event,
)

# Import main components
try:
    from .dispatcher import CognitiveDispatcher
except ImportError:
    # Handle missing dependencies gracefully
    CognitiveDispatcher = None

try:
    from .consumer_groups import CognitiveConsumerManager
except ImportError:
    CognitiveConsumerManager = None

try:
    from .backpressure_handler import CognitiveBackpressureHandler
except ImportError:
    CognitiveBackpressureHandler = None

try:
    from .dlq_manager import CognitiveDLQManager
except ImportError:
    CognitiveDLQManager = None

__all__ = [
    # Core types
    "CognitiveEventType",
    "CognitiveEvent",
    "CognitiveProcessingResult",
    "CognitiveError",
    "RoutingDecision",
    # Factory functions
    "create_cognitive_event",
    "create_memory_write_event",
    "create_recall_request_event",
    "create_attention_event",
    "create_working_memory_event",
    # Main components (if available)
    "CognitiveDispatcher",
    "CognitiveConsumerManager",
    "CognitiveBackpressureHandler",
    "CognitiveDLQManager",
]
