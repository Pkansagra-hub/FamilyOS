"""
Feature Flag Configuration Management
====================================

Core configuration management for the MemoryOS feature flag system.
Handles flag definitions, environment management, and validation.

This module provides the foundational configuration layer that supports
brain-inspired cognitive processing with environment-aware flag evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


class Environment(Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class FlagType(Enum):
    """Feature flag data types."""

    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    LIST = "list"
    DICT = "dict"


@dataclass
class CognitiveContext:
    """Cognitive system context for brain-inspired flag evaluation."""

    brain_region: Optional[str] = None
    neural_pathway: Optional[str] = None
    load_aware: bool = False
    cognitive_load_threshold: float = 0.8
    performance_impact: str = "low"  # low, medium, high


@dataclass
class FlagDefinition:
    """Complete feature flag definition with metadata."""

    name: str
    description: str
    flag_type: FlagType
    default_value: Any

    # Environment-specific values
    environments: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    category: str = "general"
    owner: str = "unknown"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Cognitive integration
    cognitive_context: Optional[CognitiveContext] = None

    # Validation rules
    allowed_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None

    # Operational metadata
    enabled: bool = True
    deprecated: bool = False
    deprecation_message: Optional[str] = None

    def get_value(self, environment: Environment) -> Any:
        """Get flag value for specific environment."""
        env_value = self.environments.get(environment.value)
        if env_value is not None:
            return env_value
        return self.default_value

    def is_cognitive_aware(self) -> bool:
        """Check if flag has cognitive processing context."""
        return self.cognitive_context is not None

    def validate_value(self, value: Any) -> bool:
        """Validate if value is acceptable for this flag."""
        # Type validation
        if self.flag_type == FlagType.BOOLEAN and not isinstance(value, bool):
            return False
        elif self.flag_type == FlagType.STRING and not isinstance(value, str):
            return False
        elif self.flag_type == FlagType.INTEGER and not isinstance(value, int):
            return False
        elif self.flag_type == FlagType.FLOAT and not isinstance(value, (int, float)):
            return False
        elif self.flag_type == FlagType.LIST and not isinstance(value, list):
            return False
        elif self.flag_type == FlagType.DICT and not isinstance(value, dict):
            return False

        # Range validation
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False

        # Allowed values validation
        if self.allowed_values is not None and value not in self.allowed_values:
            return False

        return True


@dataclass
class FlagConfig:
    """Main configuration container for feature flags."""

    flags: Dict[str, FlagDefinition] = field(default_factory=dict)
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_flag(self, flag: FlagDefinition) -> None:
        """Add a new flag definition."""
        self.flags[flag.name] = flag

    def get_flag(self, name: str) -> Optional[FlagDefinition]:
        """Get flag definition by name."""
        return self.flags.get(name)

    def get_flags_by_category(self, category: str) -> Dict[str, FlagDefinition]:
        """Get all flags in a specific category."""
        return {
            name: flag for name, flag in self.flags.items() if flag.category == category
        }

    def get_cognitive_flags(self) -> Dict[str, FlagDefinition]:
        """Get all flags with cognitive context."""
        return {
            name: flag for name, flag in self.flags.items() if flag.is_cognitive_aware()
        }

    def validate_all_flags(self) -> Dict[str, List[str]]:
        """Validate all flag configurations."""
        errors = {}

        for name, flag in self.flags.items():
            flag_errors = []

            # Validate default value
            if not flag.validate_value(flag.default_value):
                flag_errors.append(f"Invalid default value: {flag.default_value}")

            # Validate environment values
            for env, value in flag.environments.items():
                if not flag.validate_value(value):
                    flag_errors.append(f"Invalid {env} value: {value}")

            # Check for deprecated flags without messages
            if flag.deprecated and not flag.deprecation_message:
                flag_errors.append("Deprecated flag missing deprecation message")

            if flag_errors:
                errors[name] = flag_errors

        return errors


class ConfigLoader:
    """Configuration loader for YAML-based flag definitions."""

    @staticmethod
    def load_from_yaml(config_path: Path) -> FlagConfig:
        """Load flag configuration from YAML file."""
        if not config_path.exists():
            return FlagConfig()

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = FlagConfig()
        config.metadata = data.get("metadata", {})
        config.environments = data.get("environments", {})

        # Load flag definitions
        flags_data = data.get("flags", {})
        for flag_name, flag_data in flags_data.items():
            flag = ConfigLoader._create_flag_definition(flag_name, flag_data)
            config.add_flag(flag)

        return config

    @staticmethod
    def save_to_yaml(config: FlagConfig, config_path: Path) -> None:
        """Save flag configuration to YAML file."""
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        data = {
            "metadata": config.metadata,
            "environments": config.environments,
            "flags": {},
        }

        for flag_name, flag in config.flags.items():
            flag_data = {
                "description": flag.description,
                "type": flag.flag_type.value,
                "default_value": flag.default_value,
                "category": flag.category,
                "owner": flag.owner,
                "enabled": flag.enabled,
                "deprecated": flag.deprecated,
            }

            if flag.environments:
                flag_data["environments"] = flag.environments

            if flag.cognitive_context:
                flag_data["cognitive_context"] = {
                    "brain_region": flag.cognitive_context.brain_region,
                    "neural_pathway": flag.cognitive_context.neural_pathway,
                    "load_aware": flag.cognitive_context.load_aware,
                    "cognitive_load_threshold": flag.cognitive_context.cognitive_load_threshold,
                    "performance_impact": flag.cognitive_context.performance_impact,
                }

            if flag.allowed_values:
                flag_data["allowed_values"] = flag.allowed_values

            if flag.min_value is not None:
                flag_data["min_value"] = flag.min_value

            if flag.max_value is not None:
                flag_data["max_value"] = flag.max_value

            if flag.deprecation_message:
                flag_data["deprecation_message"] = flag.deprecation_message

            data["flags"][flag_name] = flag_data

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)

    @staticmethod
    def _create_flag_definition(
        flag_name: str, flag_data: Dict[str, Any]
    ) -> FlagDefinition:
        """Create FlagDefinition from YAML data."""
        flag_type = FlagType(flag_data.get("type", "boolean"))

        # Create cognitive context if present
        cognitive_context = None
        if "cognitive_context" in flag_data:
            cog_data = flag_data["cognitive_context"]
            cognitive_context = CognitiveContext(
                brain_region=cog_data.get("brain_region"),
                neural_pathway=cog_data.get("neural_pathway"),
                load_aware=cog_data.get("load_aware", False),
                cognitive_load_threshold=cog_data.get("cognitive_load_threshold", 0.8),
                performance_impact=cog_data.get("performance_impact", "low"),
            )

        return FlagDefinition(
            name=flag_name,
            description=flag_data.get("description", ""),
            flag_type=flag_type,
            default_value=flag_data.get("default_value", False),
            environments=flag_data.get("environments", {}),
            category=flag_data.get("category", "general"),
            owner=flag_data.get("owner", "unknown"),
            cognitive_context=cognitive_context,
            allowed_values=flag_data.get("allowed_values"),
            min_value=flag_data.get("min_value"),
            max_value=flag_data.get("max_value"),
            enabled=flag_data.get("enabled", True),
            deprecated=flag_data.get("deprecated", False),
            deprecation_message=flag_data.get("deprecation_message"),
        )


# Default cognitive-aware flag definitions
DEFAULT_COGNITIVE_FLAGS = {
    # Working Memory Flags
    "working_memory.enable_hierarchical_cache": FlagDefinition(
        name="working_memory.enable_hierarchical_cache",
        description="Enable L1/L2/L3 hierarchical cache system",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        category="working_memory",
        cognitive_context=CognitiveContext(
            brain_region="prefrontal_cortex",
            neural_pathway="executive_control",
            load_aware=True,
            performance_impact="high",
        ),
    ),
    # Attention Gate Flags
    "attention_gate.enable_admission_control": FlagDefinition(
        name="attention_gate.enable_admission_control",
        description="Enable thalamic admission control (ADMIT/DEFER/BOOST/DROP)",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        category="attention_gate",
        cognitive_context=CognitiveContext(
            brain_region="thalamus",
            neural_pathway="attention_relay",
            load_aware=True,
            performance_impact="medium",
        ),
    ),
    # Memory Steward Flags
    "memory_steward.enable_hippocampus_integration": FlagDefinition(
        name="memory_steward.enable_hippocampus_integration",
        description="Enable hippocampal memory formation integration",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        category="memory_steward",
        cognitive_context=CognitiveContext(
            brain_region="hippocampus",
            neural_pathway="memory_formation",
            load_aware=False,
            performance_impact="high",
        ),
    ),
    # Context Bundle Flags
    "context_bundle.enable_mmr_diversification": FlagDefinition(
        name="context_bundle.enable_mmr_diversification",
        description="Enable Maximal Marginal Relevance diversification",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        category="context_bundle",
        cognitive_context=CognitiveContext(
            brain_region="hippocampus",
            neural_pathway="recall_assembly",
            load_aware=True,
            cognitive_load_threshold=0.7,
            performance_impact="high",
        ),
    ),
    # Cognitive Events Flags
    "cognitive_events.enable_neural_pathway_routing": FlagDefinition(
        name="cognitive_events.enable_neural_pathway_routing",
        description="Enable brain region-specific event routing",
        flag_type=FlagType.BOOLEAN,
        default_value=True,
        category="cognitive_events",
        cognitive_context=CognitiveContext(
            brain_region="corpus_callosum",
            neural_pathway="inter_hemispheric",
            load_aware=True,
            performance_impact="medium",
        ),
    ),
}


def create_default_config() -> FlagConfig:
    """Create default configuration with cognitive flags."""
    config = FlagConfig()

    # Add metadata
    config.metadata = {
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "MemoryOS Feature Flag Configuration",
        "cognitive_integration": True,
    }

    # Add environment defaults
    config.environments = {
        "development": {
            "experimental_flags_enabled": True,
            "detailed_logging": True,
            "performance_profiling": True,
        },
        "testing": {
            "experimental_flags_enabled": True,
            "detailed_logging": False,
            "load_testing": True,
        },
        "production": {
            "experimental_flags_enabled": False,
            "detailed_logging": False,
            "performance_monitoring": True,
        },
    }

    # Add default cognitive flags
    for flag in DEFAULT_COGNITIVE_FLAGS.values():
        config.add_flag(flag)

    return config
