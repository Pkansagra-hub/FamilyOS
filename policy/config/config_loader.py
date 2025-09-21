from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml


@dataclass
class PolicyBandConfig:
    """Configuration for a specific policy band (GREEN/AMBER/RED/BLACK)."""

    write_allowed: bool = True
    read_redaction: List[str] = field(default_factory=list)
    override_required: bool = False
    system_only: bool = False
    description: str = ""


@dataclass
class PolicyConfig:
    roles: Dict[str, List[str]] = field(default_factory=dict)
    redaction_categories: List[str] = field(
        default_factory=lambda: ["pii.email", "pii.phone", "pii.cc", "url"]
    )
    band_defaults: Dict[str, str] = field(
        default_factory=lambda: {"shared:household": "GREEN"}
    )
    policy_bands: Dict[str, PolicyBandConfig] = field(default_factory=dict)
    minor_night_curfew_hours: List[int] = field(
        default_factory=lambda: list(range(22, 24)) + list(range(0, 6))
    )


def load_policy_config(path: str | Path) -> PolicyConfig:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)

    # Load policy bands configuration
    policy_bands = {}
    if "policy_bands" in data:
        for band_name, band_config in data["policy_bands"].items():
            policy_bands[band_name] = PolicyBandConfig(
                write_allowed=band_config.get("write_allowed", True),
                read_redaction=band_config.get("read_redaction", []),
                override_required=band_config.get("override_required", False),
                system_only=band_config.get("system_only", False),
                description=band_config.get("description", ""),
            )

    return PolicyConfig(
        roles=data.get("roles", {}),
        redaction_categories=data.get(
            "redaction_categories", ["pii.email", "pii.phone", "pii.cc", "url"]
        ),
        band_defaults=data.get("band_defaults", {"shared:household": "GREEN"}),
        policy_bands=policy_bands,
        minor_night_curfew_hours=data.get(
            "minor_night_curfew_hours", list(range(22, 24)) + list(range(0, 6))
        ),
    )
