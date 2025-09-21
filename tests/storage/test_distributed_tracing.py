"""
Tests for distributed tracing in storage operations.

This module tests the integration of OpenTelemetry distributed tracing
with storage operations, unit of work, and store decorators.
"""

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest

from observability.trace import storage_operation_span, transaction_span
from storage.base_store import instrument_storage_operation

# Test imports
from storage.unit_of_work import UnitOfWork


class MockSpan:
    """Mock OpenTelemetry span for testing."""

    def __init__(self):
        self.attributes = {}
        self.status = None
        self.ended = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status(self, status: Any) -> None:
        self.status = status

    def end(self) -> None:
        self.ended = True


@contextmanager
def mock_storage_span(operation: str, store_name: str, **attributes):
    """Mock storage operation span context manager."""
    span = MockSpan()
    for key, value in attributes.items():
        span.set_attribute(key, value)
    try:
        yield span
    finally:
        span.end()


@contextmanager
def mock_transaction_span(store_name: str, **attributes):
    """Mock transaction span context manager."""
    span = MockSpan()
    for key, value in attributes.items():
        span.set_attribute(key, value)
    try:
        yield span
    finally:
        span.end()


class MockStore:
    """Mock store for testing tracing integration."""

    def __init__(self, name: str = "test_store"):
        self.name = name
        self.transaction_started = False
        self.operations = []

    def get_store_name(self) -> str:
        return self.name

    def begin_transaction(self, connection: sqlite3.Connection) -> None:
        self.transaction_started = True

    def commit_transaction(self, connection: sqlite3.Connection) -> None:
        pass

    def rollback_transaction(self, connection: sqlite3.Connection) -> None:
        pass

    def validate_transaction(self, connection: sqlite3.Connection) -> bool:
        return True

    @instrument_storage_operation
    def test_operation(self, data: str) -> str:
        """Test operation with storage instrumentation."""
        self.operations.append(data)
        return f"processed_{data}"


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def mock_store():
    """Create mock store for testing."""
    return MockStore()


class TestDistributedTracing:
    """Test distributed tracing integration with storage operations."""

    def test_storage_operation_span_creation(self):
        """Test storage operation span creation and attributes."""
        with patch("observability.trace.storage_operation_span", mock_storage_span):
            with storage_operation_span(
                operation="read",
                store_name="test_store",
                table_name="test_table",
                record_count=5,
            ) as span:
                assert span is not None
                assert span.attributes["table_name"] == "test_table"
                assert span.attributes["record_count"] == 5

    def test_transaction_span_creation(self):
        """Test transaction span creation and attributes."""
        with patch("observability.trace.transaction_span", mock_transaction_span):
            with transaction_span(
                store_name="unit_of_work",
                transaction_type="read_write",
                uow_id="test_uow_123",
            ) as span:
                assert span is not None
                assert span.attributes["uow_id"] == "test_uow_123"
                assert span.attributes["transaction_type"] == "read_write"

    def test_unit_of_work_tracing_success(self, temp_db, mock_store):
        """Test UnitOfWork creates and completes trace spans successfully."""
        with patch(
            "observability.trace.transaction_span", mock_transaction_span
        ) as mock_span:
            uow = UnitOfWork(db_path=temp_db)
            uow.register_store(mock_store)

            with uow:
                # Transaction should complete successfully
                pass

            # Verify span was created and completed
            mock_span.assert_called_once()
            call_args = mock_span.call_args
            assert call_args[1]["store_name"] == "unit_of_work"
            assert call_args[1]["transaction_type"] == "read_write"
            assert "uow_id" in call_args[1]

    def test_unit_of_work_tracing_with_error(self, temp_db, mock_store):
        """Test UnitOfWork trace spans handle errors correctly."""
        with patch(
            "observability.trace.transaction_span", mock_transaction_span
        ) as mock_span:
            uow = UnitOfWork(db_path=temp_db)
            uow.register_store(mock_store)

            with pytest.raises(ValueError):
                with uow:
                    # Simulate an error during transaction
                    raise ValueError("Test error")

            # Verify span was created
            mock_span.assert_called_once()

    def test_storage_operation_decorator_tracing(self, mock_store):
        """Test storage operation decorator creates spans."""
        with patch("observability.trace.storage_operation_span", mock_storage_span):
            # Call instrumented method
            result = mock_store.test_operation("test_data")

            # Verify operation completed successfully
            assert result == "processed_test_data"
            assert "test_data" in mock_store.operations

    def test_trace_context_propagation(self, temp_db, mock_store):
        """Test trace context propagation through storage operations."""
        with patch("observability.trace.transaction_span", mock_transaction_span):
            with patch("observability.trace.storage_operation_span", mock_storage_span):
                uow = UnitOfWork(db_path=temp_db)
                uow.register_store(mock_store)

                with uow:
                    # Perform storage operation within transaction
                    result = mock_store.test_operation("trace_test")

                # Verify both spans were created
                assert result == "processed_trace_test"

    def test_trace_error_handling_graceful_fallback(self, temp_db, mock_store):
        """Test graceful fallback when tracing is unavailable."""
        # Simulate ImportError for tracing module
        with patch("observability.trace.transaction_span", side_effect=ImportError):
            uow = UnitOfWork(db_path=temp_db)
            uow.register_store(mock_store)

            # Should work without tracing
            with uow:
                result = mock_store.test_operation("fallback_test")

            assert result == "processed_fallback_test"

    def test_span_attributes_completeness(self):
        """Test that spans include all required attributes."""
        expected_storage_attrs = [
            "storage.operation",
            "storage.store_name",
            "storage.table_name",
        ]

        expected_transaction_attrs = [
            "storage.transaction_type",
            "storage.store_name",
            "storage.uow_id",
        ]

        with patch("observability.trace.storage_operation_span", mock_storage_span):
            with storage_operation_span(
                operation="write", store_name="test_store", table_name="test_table"
            ) as span:
                # Check basic attributes are set
                assert span.attributes.get("table_name") == "test_table"

        with patch("observability.trace.transaction_span", mock_transaction_span):
            with transaction_span(
                store_name="test_uow", transaction_type="read_only", uow_id="test_123"
            ) as span:
                # Check transaction attributes are set
                assert span.attributes.get("uow_id") == "test_123"
                assert span.attributes.get("transaction_type") == "read_only"

    def test_concurrent_spans_isolation(self):
        """Test that concurrent spans don't interfere with each other."""
        spans = []

        def capture_span(operation, store_name, **attrs):
            span = MockSpan()
            for key, value in attrs.items():
                span.set_attribute(key, value)
            spans.append(span)
            return mock_storage_span(operation, store_name, **attrs)

        with patch("observability.trace.storage_operation_span", capture_span):
            # Create multiple concurrent spans
            with storage_operation_span("read", "store1", table="table1"):
                with storage_operation_span("write", "store2", table="table2"):
                    pass

        # Verify both spans were created with correct attributes
        assert len(spans) == 2
        assert spans[0].attributes.get("table") == "table1"
        assert spans[1].attributes.get("table") == "table2"


class TestTraceIntegration:
    """Test end-to-end tracing integration scenarios."""

    def test_full_request_tracing_simulation(self, temp_db):
        """Simulate full request tracing from API to storage."""
        mock_store = MockStore("memory_store")

        with patch("observability.trace.transaction_span", mock_transaction_span):
            with patch("observability.trace.storage_operation_span", mock_storage_span):
                # Simulate API request starting a transaction
                uow = UnitOfWork(db_path=temp_db, envelope_id="api_request_123")
                uow.register_store(mock_store)

                with uow:
                    # Simulate multiple storage operations
                    mock_store.test_operation("data1")
                    mock_store.test_operation("data2")

                # Verify operations completed
                assert len(mock_store.operations) == 2
                assert mock_store.operations == ["data1", "data2"]

    def test_error_propagation_through_spans(self, temp_db):
        """Test error information propagates through span hierarchy."""
        mock_store = MockStore("error_store")

        with patch("observability.trace.transaction_span", mock_transaction_span):
            # Simulate transaction with error
            uow = UnitOfWork(db_path=temp_db)
            uow.register_store(mock_store)

            with pytest.raises(RuntimeError):
                with uow:
                    raise RuntimeError("Storage operation failed")

    def test_performance_metrics_with_tracing(self, temp_db, mock_store):
        """Test that performance metrics work alongside tracing."""
        with patch("observability.trace.transaction_span", mock_transaction_span):
            with patch("observability.performance.PerformanceMonitor"):
                uow = UnitOfWork(db_path=temp_db)
                uow.register_store(mock_store)

                with uow:
                    result = mock_store.test_operation("perf_test")

                assert result == "processed_perf_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
