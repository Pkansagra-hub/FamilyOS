"""
Port Abstractions for MemoryOS
==============================

This package contains port abstractions that provide clean interfaces between
the HTTP layer and backend services, following the adapter pattern from the MMD diagram.

Available Ports:
- CommandBusPort: Write operations → Pipeline system
- QueryFacadePort: Read operations → Data services
- SSEHubPort: Real-time streaming → Event system
- ObservabilityPort: Monitoring operations → Observability services

Usage:
    from api.ports import CommandBusPort, QueryFacadePort, SSEHubPort, ObservabilityPort
    from api.ports.command_bus import default_command_bus
    from api.ports.query_facade import default_query_facade
    from api.ports.event_hub import default_sse_hub
    from api.ports.observability import default_observability
"""

from .command_bus import CommandBusImplementation, CommandBusPort, default_command_bus
from .event_hub import SSEHubImplementation, SSEHubPort, default_sse_hub
from .observability import (
    ObservabilityImplementation,
    ObservabilityPort,
    default_observability,
)
from .query_facade import (
    QueryFacadeImplementation,
    QueryFacadePort,
    default_query_facade,
)

__all__ = [
    # Abstract base classes
    "CommandBusPort",
    "QueryFacadePort",
    "SSEHubPort",
    "ObservabilityPort",
    # Implementations
    "CommandBusImplementation",
    "QueryFacadeImplementation",
    "SSEHubImplementation",
    "ObservabilityImplementation",
    # Default instances
    "default_command_bus",
    "default_query_facade",
    "default_sse_hub",
    "default_observability",
]
