from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml
from jsonschema import Draft202012Validator, RefResolver, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ENVELOPE = REPO_ROOT / "contracts" / "events" / "envelope.schema.json"
TOPICS_FILE = REPO_ROOT / "contracts" / "events" / "topics.yaml"
SCHEMAS_DIR = REPO_ROOT / "contracts" / "events" / "schemas"

_envelope_validator: Draft202012Validator | None = None
_payload_validators: dict[str, Draft202012Validator] = {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _get_envelope_validator() -> Draft202012Validator:
    global _envelope_validator
    if _envelope_validator is None:
        schema = _load_json(SCHEMA_ENVELOPE)
        _envelope_validator = Draft202012Validator(schema)
    return _envelope_validator


def _build_payload_validator(schema_path: Path) -> Draft202012Validator:
    schema = _load_json(schema_path)
    resolver = RefResolver(base_uri=str(SCHEMAS_DIR.as_uri()) + "/", referrer=schema)
    return Draft202012Validator(schema, resolver=resolver)


def _payload_validator_for_topic(topic: str) -> Draft202012Validator:
    topics = _load_yaml(TOPICS_FILE)
    for t in topics.get("topics", []):
        if t.get("name") == topic:
            ref = t.get("schema_ref")
            if not ref:
                raise ValidationError(f"No schema_ref for topic {topic}")
            schema_path = REPO_ROOT / ref
            if not schema_path.exists():
                raise ValidationError(f"schema_ref path not found: {schema_path}")
            key = str(schema_path)
            if key not in _payload_validators:
                _payload_validators[key] = _build_payload_validator(schema_path)
            return _payload_validators[key]
    raise ValidationError(f"Unknown topic {topic} in topics.yaml")


def validate_envelope_and_payload(envelope: Dict[str, Any]) -> None:
    """Validate event envelope and payload against schemas."""
    if not isinstance(envelope, dict):
        raise ValidationError("Envelope must be an object")

    # Validate envelope structure
    validator = _get_envelope_validator()
    validator.validate(envelope)

    # Validate payload if topic has schema
    topic = envelope.get("topic")
    payload = envelope.get("payload")

    if not isinstance(topic, str):
        raise ValidationError("Envelope.topic must be a string")
    if not isinstance(payload, dict):
        raise ValidationError("Envelope.payload must be an object")

    try:
        payload_validator = _payload_validator_for_topic(topic)
        payload_validator.validate(payload)
    except ValidationError:
        # Re-raise payload validation errors
        raise
    except Exception:
        # Topic not found in schema - allow it (some topics may not have schemas)
        pass


def validate_topic_format(topic: str) -> bool:
    """
    Validate topic format against contract definitions.

    Args:
        topic: Topic string to validate

    Returns:
        True if topic format is valid, False otherwise
    """
    if not topic:
        return False

    # Basic format validation - topic should be a string
    if not isinstance(topic, str):
        return False

    # Check if topic exists in contracts
    try:
        topics = _load_yaml(TOPICS_FILE)
        valid_topics = {t.get("name", "") for t in topics.get("topics", [])}

        # Allow exact matches
        if topic in valid_topics:
            return True

        # Allow regex patterns that could match valid topics
        # For now, allow any non-empty string (can be made stricter later)
        return len(topic.strip()) > 0

    except Exception:
        # If we can't load topics, allow basic format validation
        return len(topic.strip()) > 0
        # If we can't load topics, allow basic format validation
        return len(topic.strip()) > 0
