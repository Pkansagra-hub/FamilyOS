"""Tests for redaction functionality in storage layer."""

from unittest.mock import Mock

from ward import test

from storage.base_store import MockStore, StoreConfig

# Redaction tests for read operations


@test("GREEN band reads without redaction")
def test_green_band_no_redaction():
    """GREEN band should return data without redaction."""
    # Disable schema validation for testing
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create test data with potential PII
    data = {
        "data": "Contact john@example.com for details. Call 555-123-4567 for support.",
        "metadata": {"type": "note", "sensitivity": "low"},
    }
    record = store.create(data)

    # GREEN band context
    context = {"policy_band": "GREEN", "user_role": "user"}

    # Read should return original data
    result = store.read(record["id"], context)
    assert result is not None
    assert "john@example.com" in result["data"]
    assert "555-123-4567" in result["data"]


@test("AMBER band applies light redaction for non-privileged users")
def test_amber_band_light_redaction():
    """AMBER band should apply light redaction for non-privileged users."""
    # Disable schema validation for testing
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create test data with PII
    data = {
        "data": "Contact john@example.com for details. Call 555-123-4567 for support.",
        "metadata": {"type": "note", "sensitivity": "medium"},
    }
    record = store.create(data)

    # AMBER band context for regular user
    context = {"policy_band": "AMBER", "user_role": "user"}

    # Read should return redacted data
    result = store.read(record["id"], context)
    assert result is not None
    assert "[REDACT:EMAIL]" in result["data"]
    assert "[REDACT:PHONE]" in result["data"]

    # Admin should see unredacted data
    admin_context = {"policy_band": "AMBER", "user_role": "admin"}
    admin_result = store.read(record["id"], admin_context)
    assert admin_result is not None
    assert "john@example.com" in admin_result["data"]


@test("RED band applies heavy redaction for most users")
def test_red_band_heavy_redaction():
    """RED band should apply heavy redaction for most users."""
    # Disable schema validation for testing
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create test data with various PII types
    data = {
        "data": "Email: john@example.com Phone: 555-123-4567 SSN: 123-45-6789 CC: 4111-1111-1111-1111",
        "metadata": {"type": "sensitive", "sensitivity": "high"},
    }
    record = store.create(data)

    # RED band context for regular user
    context = {"policy_band": "RED", "user_role": "user"}

    # Read should return heavily redacted data
    result = store.read(record["id"], context)
    assert result is not None
    assert "[REDACT:EMAIL]" in result["data"]
    assert "[REDACT:PHONE]" in result["data"]
    assert "[REDACT:SSN]" in result["data"]
    assert "[REDACT:CC]" in result["data"]

    # Admin should see unredacted data
    admin_context = {"policy_band": "RED", "user_role": "admin"}
    admin_result = store.read(record["id"], admin_context)
    assert admin_result is not None
    assert "john@example.com" in admin_result["data"]


@test("BLACK band returns minimal record for non-system users")
def test_black_band_complete_redaction():
    """BLACK band should return minimal record for non-system users."""
    # Disable schema validation for testing
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create test data
    data = {
        "data": "Highly sensitive information with secrets",
        "metadata": {"type": "classified", "sensitivity": "black"},
    }
    record = store.create(data)

    # BLACK band context for regular user
    context = {"policy_band": "BLACK", "user_role": "user"}

    # Read should return minimal redacted record
    result = store.read(record["id"], context)
    assert result is not None
    assert result["id"] == record["id"]
    assert result.get("redacted") is True
    assert result.get("message") == "Content redacted due to security policy"
    # For BLACK band, original data should be completely removed
    assert "sensitive information" not in str(result.get("data", ""))

    # System user should see original data
    system_context = {"policy_band": "BLACK", "user_role": "system"}
    system_result = store.read(record["id"], system_context)
    assert system_result is not None
    assert "Highly sensitive information" in system_result["data"]


@test("List operations apply redaction to all records")
def test_list_with_redaction():
    """List operations should apply redaction to all returned records."""
    # Disable schema validation for testing
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create multiple test records
    for i in range(3):
        data = {
            "data": f"Email contact-{i}@example.com Phone: 555-123-456{i}",
            "metadata": {"type": "note", "index": i},
        }
        store.create(data)

    # AMBER band context
    context = {"policy_band": "AMBER", "user_role": "user"}

    # List should return redacted records
    results = store.list(context=context)
    assert len(results) == 3

    for result in results:
        assert "[REDACT:EMAIL]" in result["data"]
        assert "[REDACT:PHONE]" in result["data"]


@test("Reads without context do not apply redaction")
def test_context_free_reads_no_redaction():
    """Reads without context should not apply redaction."""
    # Disable schema validation for testing
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create test data with PII
    data = {
        "data": "Contact john@example.com for details",
        "metadata": {"type": "note", "sensitivity": "low"},
    }
    record = store.create(data)

    # Read without context should return original data
    result = store.read(record["id"])
    assert result is not None
    assert "john@example.com" in result["data"]

    # List without context should return original data
    results = store.list()
    assert len(results) == 1
    assert "john@example.com" in results[0]["data"]
