from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import os, json

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # Optional dependency

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None

@dataclass
class PolicyConfig:
    roles: Dict[str, List[str]] = field(default_factory=dict)
    redaction_categories: List[str] = field(default_factory=lambda: ["pii.email","pii.phone","pii.cc","url"])
    band_defaults: Dict[str, str] = field(default_factory=lambda: {"shared:household":"GREEN"})
    minor_night_curfew_hours: List[int] = field(default_factory=lambda: list(range(22,24))+list(range(0,6)))

def _expand_env(text: str) -> str:
    return os.path.expandvars(text)

def load_policy_config(path: str | Path) -> PolicyConfig:
    p = Path(path)
    text = _expand_env(p.read_text(encoding="utf-8"))
    data = {}
    # Try YAML, then TOML, then JSON
    if yaml is not None:
        try:
            data = yaml.safe_load(text) or {}
        except Exception:
            data = {}
    if not data and tomllib is not None and p.suffix.lower() in {".toml"}:
        try:
            data = tomllib.loads(text)
        except Exception:
            data = {}
    if not data:
        try:
            data = json.loads(text)
        except Exception:
            data = {}
    return PolicyConfig(
        roles=data.get("roles", {}),
        redaction_categories=data.get("redaction_categories", ["pii.email","pii.phone","pii.cc","url"]),
        band_defaults=data.get("band_defaults", {"shared:household":"GREEN"}),
        minor_night_curfew_hours=data.get("minor_night_curfew_hours", list(range(22,24))+list(range(0,6))),
    )

def resolve_band_for_space(space_id: str, band_defaults: Dict[str, str]) -> Optional[str]:
    """Resolve band by exact match or simple wildcard 'prefix:*'"""
    if space_id in band_defaults:
        return band_defaults[space_id]
    for key, band in band_defaults.items():
        if key.endswith(":*") and space_id.startswith(key[:-1]):
            return band
    return None
