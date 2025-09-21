"""
Attention Gate Configuration System

Future-ready configuration management supporting:
- Static configuration for production safety
- Dynamic adaptation for learning integration
- A/B testing and experimentation
- Rollback and safety mechanisms
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..types import (
    BackpressureConfig,
    ConfigurationError,
    LearningConfig,
    SalienceWeights,
    ThresholdConfig,
)


@dataclass
class AttentionGateConfig:
    """
    Main configuration class with future learning support.

    Designed to be easily serializable and support hot-reloading
    for learning adaptations.
    """

    # Core decision parameters
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    salience_weights: SalienceWeights = field(default_factory=SalienceWeights)

    # System behavior
    backpressure: BackpressureConfig = field(default_factory=BackpressureConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)

    # Intent derivation
    intent_patterns: Dict[str, list] = field(default_factory=dict)
    intent_confidence_thresholds: Dict[str, float] = field(default_factory=dict)

    # Policy integration
    band_modifiers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # QoS and performance
    performance_targets: Dict[str, float] = field(default_factory=dict)
    resource_budgets: Dict[str, float] = field(default_factory=dict)

    # Observability
    observability_config: Dict[str, Any] = field(default_factory=dict)

    # Development and testing
    debug_enabled: bool = False
    testing_mode: bool = False
    feature_flags: Dict[str, bool] = field(default_factory=dict)

    # Learning metadata
    config_version: str = "1.0.0"
    last_adaptation: Optional[str] = None
    adaptation_count: int = 0

    @classmethod
    def from_yaml(cls, config_path: str) -> "AttentionGateConfig":
        """Load configuration from YAML file with validation"""
        path = Path(config_path)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            return cls._from_dict(config_data)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    @classmethod
    def _from_dict(cls, config_data: Dict[str, Any]) -> "AttentionGateConfig":
        """Convert dictionary to configuration object"""
        config = cls()

        # Load thresholds
        if "thresholds" in config_data:
            thresh_data = config_data["thresholds"]
            config.thresholds = ThresholdConfig(
                admit=thresh_data.get("admit", 0.6),
                boost=thresh_data.get("boost", 0.8),
                drop=thresh_data.get("drop", 0.2),
                adaptive_enabled=thresh_data.get("adaptive", {}).get("enabled", False),
                adaptation_rate=thresh_data.get("adaptive", {}).get(
                    "adaptation_rate", 0.01
                ),
            )

        # Load salience weights
        if "salience" in config_data:
            sal_data = config_data["salience"]
            weights_data = sal_data.get("weights", {})
            cal_data = sal_data.get("calibration", {})

            config.salience_weights = SalienceWeights(
                urgency=weights_data.get("urgency", 1.0),
                novelty=weights_data.get("novelty", 0.8),
                value=weights_data.get("value", 0.9),
                risk=abs(
                    weights_data.get("risk", -0.7)
                ),  # Convert to positive for internal use
                cost=abs(weights_data.get("cost", -0.6)),
                social_risk=abs(weights_data.get("social_risk", -0.5)),
                affect_arousal=weights_data.get("affect_arousal", 0.4),
                affect_valence=weights_data.get("affect_valence", 0.2),
                context_bump=weights_data.get("context_bump", 0.3),
                temporal_fit=weights_data.get("temporal_fit", 0.3),
                personal_relevance=weights_data.get("personal_relevance", 0.0),
                goal_alignment=weights_data.get("goal_alignment", 0.0),
                bias=sal_data.get("bias", 0.0),
                temperature=cal_data.get("temperature", 1.0),
                platt_a=cal_data.get("platt_a", 1.0),
                platt_b=cal_data.get("platt_b", 0.0),
            )

        # Load backpressure config
        if "backpressure" in config_data:
            bp_data = config_data["backpressure"]
            config.backpressure = BackpressureConfig(
                enabled=bp_data.get("enabled", True),
                token_bucket_rate=bp_data.get("token_bucket", {}).get("rate", 10),
                token_bucket_burst=bp_data.get("token_bucket", {}).get("burst", 20),
                circuit_breaker_threshold=bp_data.get("circuit_breaker", {}).get(
                    "failure_threshold", 5
                ),
                circuit_breaker_timeout_ms=bp_data.get("circuit_breaker", {}).get(
                    "timeout_ms", 30000
                ),
            )

        # Load learning config
        if "learning" in config_data:
            learn_data = config_data["learning"]
            config.learning = LearningConfig(
                enabled=learn_data.get("enabled", False),
                learning_rate=learn_data.get("parameters", {}).get(
                    "learning_rate", 0.01
                ),
                adaptation_frequency=learn_data.get("parameters", {}).get(
                    "adaptation_frequency", "hourly"
                ),
                min_samples=learn_data.get("parameters", {}).get("min_samples", 100),
                safety_checks=learn_data.get("safety", {}).get("enabled", True),
                rollback_threshold=learn_data.get("safety", {}).get(
                    "rollback_threshold", 0.1
                ),
            )

        # Load intent patterns
        config.intent_patterns = config_data.get("intent_rules", {}).get("patterns", {})
        config.intent_confidence_thresholds = config_data.get("intent_rules", {}).get(
            "confidence", {}
        )

        # Load band modifiers
        config.band_modifiers = config_data.get("policy", {}).get("band_modifiers", {})

        # Load performance targets
        config.performance_targets = config_data.get("qos", {}).get("targets", {})
        config.resource_budgets = config_data.get("qos", {}).get("budgets", {})

        # Load observability config
        config.observability_config = config_data.get("observability", {})

        # Load development settings
        dev_data = config_data.get("development", {})
        config.debug_enabled = dev_data.get("debug", {}).get("enabled", False)
        config.testing_mode = dev_data.get("testing", {}).get(
            "deterministic_mode", False
        )
        config.feature_flags = dev_data.get("features", {})

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            "thresholds": {
                "admit": self.thresholds.admit,
                "boost": self.thresholds.boost,
                "drop": self.thresholds.drop,
                "adaptive": {
                    "enabled": self.thresholds.adaptive_enabled,
                    "adaptation_rate": self.thresholds.adaptation_rate,
                },
            },
            "salience": {
                "weights": self.salience_weights.to_dict(),
                "calibration": {
                    "temperature": self.salience_weights.temperature,
                    "platt_a": self.salience_weights.platt_a,
                    "platt_b": self.salience_weights.platt_b,
                },
                "bias": self.salience_weights.bias,
            },
            "backpressure": {
                "enabled": self.backpressure.enabled,
                "token_bucket": {
                    "rate": self.backpressure.token_bucket_rate,
                    "burst": self.backpressure.token_bucket_burst,
                },
                "circuit_breaker": {
                    "failure_threshold": self.backpressure.circuit_breaker_threshold,
                    "timeout_ms": self.backpressure.circuit_breaker_timeout_ms,
                },
            },
            "learning": {
                "enabled": self.learning.enabled,
                "parameters": {
                    "learning_rate": self.learning.learning_rate,
                    "adaptation_frequency": self.learning.adaptation_frequency,
                    "min_samples": self.learning.min_samples,
                },
                "safety": {
                    "enabled": self.learning.safety_checks,
                    "rollback_threshold": self.learning.rollback_threshold,
                },
            },
            "intent_rules": {
                "patterns": self.intent_patterns,
                "confidence": self.intent_confidence_thresholds,
            },
            "policy": {"band_modifiers": self.band_modifiers},
            "qos": {
                "targets": self.performance_targets,
                "budgets": self.resource_budgets,
            },
            "observability": self.observability_config,
            "development": {
                "debug": {"enabled": self.debug_enabled},
                "testing": {"deterministic_mode": self.testing_mode},
                "features": self.feature_flags,
            },
            "config_version": self.config_version,
            "last_adaptation": self.last_adaptation,
            "adaptation_count": self.adaptation_count,
        }

    def save(self, config_path: str) -> None:
        """Save configuration to YAML file"""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def apply_adaptation(self, adaptation_update: Dict[str, Any]) -> None:
        """
        Apply learning adaptation update with safety checks.

        This method supports future learning integration while maintaining
        production safety through validation and rollback capabilities.
        """
        if not self.learning.enabled:
            raise ConfigurationError("Learning adaptations disabled in configuration")

        # Validate adaptation update
        self._validate_adaptation(adaptation_update)

        # Apply weight updates
        if "weight_deltas" in adaptation_update:
            self._apply_weight_deltas(adaptation_update["weight_deltas"])

        # Apply calibration updates
        if "calibration_updates" in adaptation_update:
            self._apply_calibration_updates(adaptation_update["calibration_updates"])

        # Update metadata
        self.adaptation_count += 1
        self.last_adaptation = adaptation_update.get("timestamp", "unknown")

    def _validate_adaptation(self, adaptation_update: Dict[str, Any]) -> None:
        """Validate adaptation update for safety"""
        if "weight_deltas" in adaptation_update:
            weight_deltas = adaptation_update["weight_deltas"]

            # Check maximum weight change constraint
            max_change = max(abs(delta) for delta in weight_deltas.values())
            max_allowed = 0.1  # Configurable safety limit

            if max_change > max_allowed:
                raise ConfigurationError(
                    f"Weight change {max_change} exceeds safety limit {max_allowed}"
                )

    def _apply_weight_deltas(self, weight_deltas: Dict[str, float]) -> None:
        """Apply weight delta updates with bounds checking"""
        for weight_name, delta in weight_deltas.items():
            if hasattr(self.salience_weights, weight_name):
                current_value = getattr(self.salience_weights, weight_name)
                new_value = current_value + delta

                # Apply bounds
                new_value = max(0.0, min(2.0, new_value))  # Reasonable bounds

                setattr(self.salience_weights, weight_name, new_value)

    def _apply_calibration_updates(self, calibration_updates: Dict[str, float]) -> None:
        """Apply calibration parameter updates"""
        for param_name, new_value in calibration_updates.items():
            if param_name == "temperature":
                # Temperature must be positive
                self.salience_weights.temperature = max(0.1, new_value)
            elif param_name in ["platt_a", "platt_b"]:
                setattr(self.salience_weights, param_name, new_value)


class ConfigurationManager:
    """
    Configuration manager with hot-reloading and adaptation support.

    Designed for production use with learning integration capabilities.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = AttentionGateConfig.from_yaml(config_path)
        self._config_mtime = os.path.getmtime(config_path)

    def get_config(self) -> AttentionGateConfig:
        """Get current configuration, checking for file updates"""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self._config_mtime:
                # Configuration file updated, reload
                self.config = AttentionGateConfig.from_yaml(self.config_path)
                self._config_mtime = current_mtime
        except (OSError, ConfigurationError):
            # File access error or invalid config, keep current config
            pass

        return self.config

    def apply_adaptation(self, adaptation_update: Dict[str, Any]) -> None:
        """Apply learning adaptation and save to disk"""
        self.config.apply_adaptation(adaptation_update)
        self.config.save(self.config_path)
        self._config_mtime = os.path.getmtime(self.config_path)

    def rollback_adaptation(self, backup_config: AttentionGateConfig) -> None:
        """Rollback to previous configuration for safety"""
        self.config = backup_config
        self.config.save(self.config_path)
        self._config_mtime = os.path.getmtime(self.config_path)


# Global configuration instance (lazy-loaded)
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager

    if _config_manager is None:
        if config_path is None:
            # Default configuration path
            default_path = Path(__file__).parent / "attention_gate.yaml"
            config_path = str(default_path)

        _config_manager = ConfigurationManager(config_path)

    return _config_manager


def get_config() -> AttentionGateConfig:
    """Get current attention gate configuration"""
    return get_config_manager().get_config()
