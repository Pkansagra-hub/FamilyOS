"""
Common types and enums for middleware components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SecurityLevel(Enum):
    """Security levels for requests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QoSPriority(Enum):
    """Quality of Service priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class SafetyLevel(Enum):
    """Safety assessment levels."""

    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class MiddlewareMetrics:
    """Middleware execution metrics."""

    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "pending"
    errors: List[str] = field(default_factory=list)


@dataclass
class SecurityContext:
    """Security context for requests."""

    user_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    security_level: SecurityLevel = SecurityLevel.LOW
    threat_indicators: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QoSContext:
    """Quality of Service context."""

    priority: QoSPriority = QoSPriority.NORMAL
    max_execution_time: Optional[float] = None
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    performance_requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyContext:
    """Safety assessment context."""

    safety_level: SafetyLevel = SafetyLevel.SAFE
    risk_factors: List[str] = field(default_factory=list)
    safety_checks: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
