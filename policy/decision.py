from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Literal

Decision = Literal["ALLOW","DENY","ALLOW_REDACTED"]

@dataclass
class Obligation:
    """Obligations that must be enforced by callers when applying a decision."""
    redact: List[str] = field(default_factory=list)
    band_min: Optional[str] = None
    log_audit: bool = True
    reason_tags: List[str] = field(default_factory=list)

@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""
    decision: Decision
    reasons: List[str] = field(default_factory=list)
    obligations: Obligation = field(default_factory=Obligation)
    effective_caps: List[str] = field(default_factory=list)
    model_version: str = "v0.9.4"
