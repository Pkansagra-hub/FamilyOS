"""Tests for storage metrics instrumentation."""

import sqlite3
import time
from unittest.mock import Mock, patch

from ward import test
from ward.expect import assert_equal

from storage.base_store import instrument_storage_operation


@test("instrument_storage_operation decorator tracks timing")
def test_decorator_tracks_timing():
    """Test that the decorator tracks operation timing."""
    with patch("storage.base_store.record_storage") as mock_record:
        with patch("storage.base_store._metrics_available", True):
            # Create a mock function to decorate
            @instrument_storage_operation("test_operation")
            def mock_function(self):
                time.sleep(0.001)  # Small delay to test timing
                return "success"

            # Create a mock object with name attribute
            mock_obj = Mock()
            mock_obj.name = "test_store"

            # Call the decorated function
            result = mock_function(mock_obj)

            # Verify the function executed correctly
            assert_equal(result, "success")

            # Verify metrics were recorded
            assert_equal(mock_record.call_count, 1)
            call_args = mock_record.call_args[0]
            assert_equal(call_args[0], "test_store")  # store_name
            assert_equal(call_args[1], "test_operation")  # operation
            assert_equal(call_args[3], True)  # success


@test("instrument_storage_operation handles exceptions")
def test_decorator_handles_exceptions():
    """Test that the decorator handles and classifies exceptions."""
    with patch("observability.metrics.record_storage_error") as mock_error_record:
        with patch("storage.base_store.record_storage") as mock_record:
            with patch("storage.base_store._metrics_available", True):
                # Create a mock function that raises an exception
                @instrument_storage_operation("test_operation")
                def failing_function(self):
                    raise ValueError("Test error")

                mock_obj = Mock()
                mock_obj.name = "test_store"

                # Verify exception is re-raised
                try:
                    failing_function(mock_obj)
                    assert False, "Should have raised ValueError"
                except ValueError:
                    pass  # Expected

                # Verify error metrics were recorded
                assert_equal(mock_error_record.call_count, 1)
                call_args = mock_error_record.call_args[0]
                assert_equal(call_args[0], "test_store")  # store_name
                assert_equal(call_args[1], "test_operation")  # operation
                assert_equal(call_args[2], "valueerror")  # error_type


@test("instrument_storage_operation handles sqlite integrity errors")
def test_decorator_handles_sqlite_errors():
    """Test that the decorator classifies SQLite integrity errors correctly."""
    with patch("observability.metrics.record_storage_error") as mock_error_record:
        with patch("storage.base_store.record_storage") as mock_record:
            with patch("storage.base_store._metrics_available", True):

                @instrument_storage_operation("create")
                def failing_create(self):
                    raise sqlite3.IntegrityError("UNIQUE constraint failed")

                mock_obj = Mock()
                mock_obj.name = "test_store"

                try:
                    failing_create(mock_obj)
                except sqlite3.IntegrityError:
                    pass  # Expected

                # Verify error classification
                assert_equal(mock_error_record.call_count, 1)
                call_args = mock_error_record.call_args[0]
                assert_equal(call_args[2], "integrity_error")  # error_type


@test("instrument_storage_operation gracefully handles unavailable metrics")
def test_decorator_handles_unavailable_metrics():
    """Test that the decorator works when metrics are unavailable."""
    with patch("storage.base_store._metrics_available", False):

        @instrument_storage_operation("test_operation")
        def test_function(self):
            return "success"

        mock_obj = Mock()
        mock_obj.name = "test_store"

        # Should work without errors
        result = test_function(mock_obj)
        assert_equal(result, "success")


@test("instrument_storage_operation uses class name when no name attribute")
def test_decorator_uses_class_name_fallback():
    """Test that the decorator falls back to class name when name attribute missing."""
    with patch("storage.base_store.record_storage") as mock_record:
        with patch("storage.base_store._metrics_available", True):

            @instrument_storage_operation("test_operation")
            def test_function(self):
                return "success"

            # Mock object without name attribute
            mock_obj = Mock()
            mock_obj.__class__.__name__ = "TestClass"
            del mock_obj.name  # Remove name attribute

            result = test_function(mock_obj)
            assert_equal(result, "success")

            # Verify class name was used
            call_args = mock_record.call_args[0]
            assert_equal(call_args[0], "TestClass")  # store_name from class
