"""Comprehensive tests for complete policy band enforcement system."""

from unittest.mock import Mock

from ward import test

from storage.base_store import MockStore, StoreConfig
from storage.policy_enforcement import PolicyViolation

# Comprehensive end-to-end policy enforcement tests


@test("End-to-end GREEN band allows all operations without restrictions")
def test_green_band_end_to_end():
    """GREEN band should allow all operations and return unredacted data."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Test data with various PII types
    sensitive_data = {
        "data": "Contact: john@example.com Phone: 555-123-4567 SSN: 123-45-6789 CC: 4111-1111-1111-1111",
        "metadata": {"type": "sensitive", "classification": "internal"},
    }

    context = {"policy_band": "GREEN", "user_role": "user"}

    # Create should succeed
    record = store.create(sensitive_data, context)
    assert record["id"] is not None

    # Read should return original unredacted data
    result = store.read(record["id"], context)
    assert result is not None
    assert "john@example.com" in result["data"]
    assert "555-123-4567" in result["data"]
    assert "123-45-6789" in result["data"]
    assert "4111-1111-1111-1111" in result["data"]

    # Update should succeed
    updated_data = {"data": "Updated with new-email@domain.com"}
    updated_record = store.update(record["id"], updated_data, context)
    assert "new-email@domain.com" in updated_record["data"]

    # Delete should succeed
    deleted = store.delete(record["id"], context)
    assert deleted is True


@test("End-to-end AMBER band restricts read access but allows writes")
def test_amber_band_end_to_end():
    """AMBER band should allow writes but apply redaction on reads for non-privileged users."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    sensitive_data = {
        "data": "Personal info: alice@company.com Phone: 555-987-6543",
        "metadata": {"type": "personal", "classification": "amber"},
    }

    # Regular user context
    user_context = {"policy_band": "AMBER", "user_role": "user"}

    # Create should succeed for AMBER band
    record = store.create(sensitive_data, user_context)
    assert record["id"] is not None

    # Read should return redacted data for regular user
    result = store.read(record["id"], user_context)
    assert result is not None
    assert "[REDACT:EMAIL]" in result["data"]
    assert "[REDACT:PHONE]" in result["data"]

    # Admin should see unredacted data
    admin_context = {"policy_band": "AMBER", "user_role": "admin"}
    admin_result = store.read(record["id"], admin_context)
    assert admin_result is not None
    assert "alice@company.com" in admin_result["data"]
    assert "555-987-6543" in admin_result["data"]

    # Update should work for admin
    update_data = {"data": "Updated by admin with secret@internal.com"}
    store.update(record["id"], update_data, admin_context)

    # List operations should also apply redaction
    results = store.list(context=user_context)
    assert len(results) >= 1
    for result in results:
        assert "[REDACT:EMAIL]" in result["data"]


@test("End-to-end RED band requires override tokens for writes")
def test_red_band_end_to_end():
    """RED band should require override tokens for writes and apply heavy redaction."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    top_secret_data = {
        "data": "Top Secret: agent@secret.gov Phone: 555-001-0001 SSN: 987-65-4321 Payment: 5555-4444-3333-2222",
        "metadata": {"type": "classified", "level": "red"},
    }

    # Regular user without override token
    user_context = {"policy_band": "RED", "user_role": "user"}

    # Create should fail without override token
    try:
        store.create(top_secret_data, user_context)
        assert False, "Should have raised PolicyViolation"
    except PolicyViolation as e:
        assert "RED band requires override token" in str(e)
        assert e.band == "RED"

    # Create should succeed with override token
    user_with_override = {
        "policy_band": "RED",
        "user_role": "user",
        "override_token": "OVERRIDE_123",
    }
    record = store.create(top_secret_data, user_with_override)
    assert record["id"] is not None

    # Read should apply heavy redaction for regular user
    result = store.read(record["id"], user_context)
    assert result is not None
    assert "[REDACT:EMAIL]" in result["data"]
    assert "[REDACT:PHONE]" in result["data"]
    assert "[REDACT:SSN]" in result["data"]
    assert "[REDACT:CC]" in result["data"]

    # Admin should see original data
    admin_context = {"policy_band": "RED", "user_role": "admin"}
    admin_result = store.read(record["id"], admin_context)
    assert admin_result is not None
    assert "agent@secret.gov" in admin_result["data"]
    assert "555-001-0001" in admin_result["data"]

    # Update should require override token
    try:
        store.update(
            record["id"], {"data": "Attempting unauthorized update"}, user_context
        )
        assert False, "Should have raised PolicyViolation"
    except PolicyViolation:
        pass


@test("End-to-end BLACK band blocks most operations")
def test_black_band_end_to_end():
    """BLACK band should block writes and return minimal data for non-system users."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    ultra_secret_data = {
        "data": "Ultra classified: director@agency.gov Phone: 555-000-0000 Key: ABC-123-XYZ",
        "metadata": {"type": "ultra_secret", "level": "black"},
    }

    # Regular user context
    user_context = {"policy_band": "BLACK", "user_role": "user"}

    # Create should fail for regular user
    try:
        store.create(ultra_secret_data, user_context)
        assert False, "Should have raised PolicyViolation"
    except PolicyViolation as e:
        assert "BLACK band - writes prohibited" in str(e)
        assert e.band == "BLACK"

    # System user can create
    system_context = {"policy_band": "BLACK", "user_role": "system"}
    record = store.create(ultra_secret_data, system_context)
    assert record["id"] is not None

    # Regular user read should return minimal record
    result = store.read(record["id"], user_context)
    assert result is not None
    assert result["id"] == record["id"]
    assert result.get("redacted") is True
    assert result.get("message") == "Content redacted due to security policy"
    assert "director@agency.gov" not in str(result.get("data", ""))

    # System user should see full data
    system_result = store.read(record["id"], system_context)
    assert system_result is not None
    assert "director@agency.gov" in system_result["data"]

    # Regular user updates should fail
    try:
        store.update(record["id"], {"data": "Unauthorized"}, user_context)
        assert False, "Should have raised PolicyViolation"
    except PolicyViolation:
        pass

    # Regular user deletes should fail
    try:
        store.delete(record["id"], user_context)
        assert False, "Should have raised PolicyViolation"
    except PolicyViolation:
        pass


@test("Policy enforcement handles multiple records with different bands")
def test_mixed_policy_bands():
    """Test system behavior with records under different policy bands."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create records under different bands
    green_data = {"data": "Public info: info@public.com", "metadata": {"band": "green"}}
    amber_data = {"data": "Internal: staff@company.com", "metadata": {"band": "amber"}}

    green_context = {"policy_band": "GREEN", "user_role": "user"}
    amber_context = {"policy_band": "AMBER", "user_role": "user"}
    red_context = {
        "policy_band": "RED",
        "user_role": "user",
        "override_token": "OVERRIDE_456",
    }

    # Create records
    green_record = store.create(green_data, green_context)
    amber_record = store.create(amber_data, amber_context)

    # List should respect individual record contexts
    # Note: This is a simplified test - in practice, list operations would
    # need more sophisticated context handling per record
    green_results = store.list(context=green_context)
    assert len(green_results) >= 2

    # Check that GREEN band reads work correctly
    green_read = store.read(green_record["id"], green_context)
    assert "info@public.com" in green_read["data"]

    # Check that AMBER band applies redaction
    amber_read = store.read(amber_record["id"], amber_context)
    assert "[REDACT:EMAIL]" in amber_read["data"]


@test("Policy enforcement caching works correctly")
def test_redaction_caching():
    """Test that redaction caching improves performance without affecting correctness."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create test record
    data = {
        "data": "Test caching: test@example.com Phone: 555-111-2222",
        "metadata": {"type": "cache_test"},
    }

    context = {"policy_band": "AMBER", "user_role": "user"}
    record = store.create(data, context)

    # First read should populate cache
    result1 = store.read(record["id"], context)
    assert "[REDACT:EMAIL]" in result1["data"]

    # Second read should use cache (same result)
    result2 = store.read(record["id"], context)
    assert result1["data"] == result2["data"]

    # Different context should bypass cache
    admin_context = {"policy_band": "AMBER", "user_role": "admin"}
    admin_result = store.read(record["id"], admin_context)
    assert "test@example.com" in admin_result["data"]
    assert admin_result["data"] != result1["data"]

    # Clear cache and verify functionality still works
    store._clear_redaction_cache()
    result3 = store.read(record["id"], context)
    assert "[REDACT:EMAIL]" in result3["data"]


@test("Context-free operations bypass policy enforcement")
def test_context_free_operations():
    """Test that operations without context bypass policy enforcement."""
    config = StoreConfig(schema_validation=False)
    store = MockStore("test", config)
    mock_conn = Mock()
    store.begin_transaction(mock_conn)

    # Create with context for comparison
    data = {
        "data": "Context test: admin@system.com Phone: 555-777-8888",
        "metadata": {"type": "context_test"},
    }

    # Context-free create should work (no policy checks)
    record = store.create(data)
    assert record["id"] is not None

    # Context-free read should return unredacted data
    result = store.read(record["id"])
    assert result is not None
    assert "admin@system.com" in result["data"]
    assert "555-777-8888" in result["data"]

    # Context-free list should return unredacted data
    results = store.list()
    assert len(results) >= 1
    found_record = next(r for r in results if r["id"] == record["id"])
    assert "admin@system.com" in found_record["data"]

    # Context-free update should work
    store.update(record["id"], {"data": "Updated without context"})

    # Context-free delete should work
    deleted = store.delete(record["id"])
    assert deleted is True
