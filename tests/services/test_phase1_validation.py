"""
Phase 1 Validation Test - Service Interface Implementation
==========================================================

Quick validation test for the service interfaces and mock implementations.
Ensures basic functionality works before connecting to ports.

Usage:
    python -m ward test --path tests/services/test_phase1_validation.py
"""

import os
import sys

from ward import fixture

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services import (
    IndexingService,
    RetrievalService,
    WriteService,
    default_service_registry,
)


@fixture
def mock_envelope():
    """Mock memory envelope for testing."""
    return {
        "content": "This is a test memory for validation",
        "content_type": "text/plain",
        "metadata": {"tags": ["test", "validation"], "source": "test_suite"},
        "band": "GREEN",
    }


@fixture
def mock_security_context():
    """Mock security context for testing."""
    return {
        "user_id": "test_user_123",
        "device_id": "test_device_456",
        "capabilities": ["READ", "WRITE"],
        "authenticated": True,
        "trust_level": "GREEN",
    }

    async def test_write_service_submit_memory(
        self, mock_envelope, mock_security_context
    ):
        """Test WriteService.submit_memory functionality."""
        write_service = WriteService()

        result = await write_service.submit_memory(
            envelope=mock_envelope,
            space_id="personal:default",
            security_context=mock_security_context,
        )

        # Validate response structure
        assert result["status"] == "accepted"
        assert "envelope_id" in result
        assert "receipt_url" in result
        assert "processing_info" in result
        assert result["space_id"] == "personal:default"

        # Validate envelope was stored
        envelope_id = result["envelope_id"]
        assert envelope_id in write_service.submitted_memories

        # Test receipt retrieval
        receipt = await write_service.get_receipt(envelope_id, mock_security_context)
        assert receipt["envelope_id"] == envelope_id
        assert receipt["status"] in ["accepted", "processing", "completed"]

    async def test_retrieval_service_recall_memories(self, mock_security_context):
        """Test RetrievalService.recall_memories functionality."""
        retrieval_service = RetrievalService()

        query = {
            "query": "test memory",
            "k": 5,
            "return_trace": True,
            "mode": "semantic",
        }

        result = await retrieval_service.recall_memories(
            query=query,
            space_id="personal:default",
            security_context=mock_security_context,
        )

        # Validate response structure
        assert "items" in result
        assert "total_count" in result
        assert "query_info" in result
        assert "trace" in result
        assert isinstance(result["items"], list)

        # Validate query info
        assert result["query_info"]["query"] == "test memory"
        assert result["query_info"]["space_id"] == "personal:default"

        # Validate trace info (requested)
        assert result["trace"] is not None
        assert "search_mode" in result["trace"]
        assert "ranking" in result["trace"]

    async def test_indexing_service_index_content(self, mock_security_context):
        """Test IndexingService.index_content functionality."""
        indexing_service = IndexingService()

        content = {
            "id": "test_content_123",
            "text": "This is test content for indexing validation",
            "type": "text/plain",
            "metadata": {"source": "test", "tags": ["indexing", "test"]},
        }

        result = await indexing_service.index_content(
            content=content,
            space_id="personal:default",
            security_context=mock_security_context,
        )

        # Validate response structure
        assert result["status"] == "completed"
        assert "index_id" in result
        assert "processing_info" in result
        assert "search_readiness" in result

        # Validate processing info
        processing_info = result["processing_info"]
        assert "content_length" in processing_info
        assert "embedding_model" in processing_info
        assert "embedding_dimensions" in processing_info

        # Validate search readiness
        search_readiness = result["search_readiness"]
        assert search_readiness["indexed"] is True
        assert search_readiness["searchable"] is True

    async def test_service_registry_functionality(self):
        """Test ServiceRegistry functionality."""
        registry = default_service_registry

        # Test service retrieval
        write_service = registry.get_write_service()
        retrieval_service = registry.get_retrieval_service()
        indexing_service = registry.get_indexing_service()

        assert write_service is not None
        assert retrieval_service is not None
        assert indexing_service is not None

        # Test health check
        health = await registry.health_check()
        assert health["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert health["mode"] == "mock"
        assert "services" in health
        assert "registry_info" in health

    async def test_full_workflow_integration(
        self, mock_envelope, mock_security_context
    ):
        """Test complete workflow: submit → index → recall."""
        registry = default_service_registry

        write_service = registry.get_write_service()
        indexing_service = registry.get_indexing_service()
        retrieval_service = registry.get_retrieval_service()

        # Step 1: Submit memory
        submit_result = await write_service.submit_memory(
            envelope=mock_envelope,
            space_id="personal:default",
            security_context=mock_security_context,
        )

        assert submit_result["status"] == "accepted"
        envelope_id = submit_result["envelope_id"]

        # Step 2: Index content
        index_content = {
            "id": envelope_id,
            "text": mock_envelope["content"],
            "type": mock_envelope["content_type"],
        }

        index_result = await indexing_service.index_content(
            content=index_content,
            space_id="personal:default",
            security_context=mock_security_context,
        )

        assert index_result["status"] == "completed"

        # Step 3: Recall memory
        recall_query = {"query": "test memory validation", "k": 10, "mode": "semantic"}

        recall_result = await retrieval_service.recall_memories(
            query=recall_query,
            space_id="personal:default",
            security_context=mock_security_context,
        )

        assert "items" in recall_result
        assert recall_result["total_count"] >= 0

        print("✅ Full workflow test completed:")
        print(f"   - Submitted: {envelope_id}")
        print(f"   - Indexed: {index_result['index_id']}")
        print(f"   - Recalled: {recall_result['total_count']} memories")


if __name__ == "__main__":
    # Quick validation run
    import asyncio

    async def run_validation():
        """Run quick validation tests."""
        test_instance = TestServiceImplementations()

        # Mock fixtures
        mock_envelope = {
            "content": "This is a test memory for validation",
            "content_type": "text/plain",
            "metadata": {"tags": ["test", "validation"]},
            "band": "GREEN",
        }

        mock_security_context = {
            "user_id": "test_user_123",
            "device_id": "test_device_456",
            "capabilities": ["READ", "WRITE"],
            "authenticated": True,
            "trust_level": "GREEN",
        }

        print("🧪 Running Phase 1 validation tests...")

        try:
            # Test individual services
            await test_instance.test_write_service_submit_memory(
                mock_envelope, mock_security_context
            )
            print("✅ WriteService test passed")

            await test_instance.test_retrieval_service_recall_memories(
                mock_security_context
            )
            print("✅ RetrievalService test passed")

            await test_instance.test_indexing_service_index_content(
                mock_security_context
            )
            print("✅ IndexingService test passed")

            await test_instance.test_service_registry_functionality()
            print("✅ ServiceRegistry test passed")

            await test_instance.test_full_workflow_integration(
                mock_envelope, mock_security_context
            )
            print("✅ Full workflow integration test passed")

            print("\n🎉 All Phase 1 validation tests PASSED!")
            print("📋 Ready for Phase 2: Port Integration")

        except Exception as e:
            print(f"❌ Validation test failed: {e}")
            raise

    # Run validation
    asyncio.run(run_validation())
