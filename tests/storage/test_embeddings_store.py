"""Tests for EmbeddingsStore implementation.

Comprehensive testing of vector embeddings storage and similarity search,
following contracts-first validation patterns.
"""

import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.base_store import StoreConfig
from storage.embeddings_store import EmbeddingRecord, EmbeddingsStore, SimilarityQuery


class TestEmbeddingsStore:
    """Test EmbeddingsStore functionality with real vector data."""

    def setup_method(self):
        """Set up test environment with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_embeddings.db")

        self.config = StoreConfig(db_path=self.db_path, schema_validation=True)

        self.store = EmbeddingsStore(self.config)

        # Test data
        self.test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        self.test_embedding = EmbeddingRecord(
            embedding_id="01HTEST0000000000000000000",
            doc_id="01HDOC00000000000000000000",
            model_id="text-embedding-3-small",
            dim=5,
            sha256="a" * 64,  # Mock hash
            vector_ref="01HVEC00000000000000000000",
            quantized=False,
            metadata={"type": "test"},
        )

    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, "store"):
            self.store.close()

        # Clean up temp files
        if hasattr(self, "temp_dir"):
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_and_retrieve_embedding(self):
        """Test storing and retrieving embeddings with vectors."""
        # Register model first
        success = self.store.register_model(
            "text-embedding-3-small", 5, "cosine", "Test model"
        )
        assert success

        # Store embedding with vector
        success = self.store.store_embedding(
            self.test_embedding, self.test_vector, "shared:household", "GREEN"
        )
        assert success

        # Retrieve embedding record
        retrieved = self.store.get_embedding(self.test_embedding.embedding_id)
        assert retrieved is not None
        assert retrieved.embedding_id == self.test_embedding.embedding_id
        assert retrieved.doc_id == self.test_embedding.doc_id
        assert retrieved.model_id == self.test_embedding.model_id
        assert retrieved.dim == 5

        # Retrieve vector data
        vector_data = self.store.get_vector_data(self.test_embedding.vector_ref)
        assert vector_data is not None
        assert len(vector_data) == 5
        # Check approximate equality for float values
        for i, val in enumerate(vector_data):
            assert abs(val - self.test_vector[i]) < 0.001

    def test_similarity_search(self):
        """Test vector similarity search functionality."""
        # Register model
        self.store.register_model("test-model", 3, "cosine")

        # Store multiple embeddings
        embeddings = [
            (
                [1.0, 0.0, 0.0],
                "01HTEST0000000000000000001",
                "01HDOC00000000000000000001",
                "01HVEC00000000000000000001",
            ),
            (
                [0.0, 1.0, 0.0],
                "01HTEST0000000000000000002",
                "01HDOC00000000000000000002",
                "01HVEC00000000000000000002",
            ),
            (
                [0.0, 0.0, 1.0],
                "01HTEST0000000000000000003",
                "01HDOC00000000000000000003",
                "01HVEC00000000000000000003",
            ),
            (
                [0.7, 0.7, 0.0],
                "01HTEST0000000000000000004",
                "01HDOC00000000000000000004",
                "01HVEC00000000000000000004",
            ),
        ]

        for vector, emb_id, doc_id, vec_ref in embeddings:
            embedding = EmbeddingRecord(
                embedding_id=emb_id,
                doc_id=doc_id,
                model_id="test-model",
                dim=3,
                sha256="b" * 64,
                vector_ref=vec_ref,
                quantized=False,
            )

            success = self.store.store_embedding(
                embedding, vector, "shared:household", "GREEN"
            )
            assert success

        # Test similarity search
        query = SimilarityQuery(
            vector=[1.0, 0.0, 0.0],  # Should be most similar to first vector
            model_id="test-model",
            limit=3,
            distance_metric="cosine",
        )

        results = self.store.similarity_search(query)
        assert len(results) > 0

        # First result should be the exact match
        assert results[0].embedding_id == "01HTEST0000000000000000001"
        assert results[0].score > 0.9  # High cosine similarity

    def test_model_registration(self):
        """Test embedding model registration and retrieval."""
        # Register multiple models
        models = [
            ("text-embedding-3-small", 1536, "cosine", "OpenAI small model"),
            ("text-embedding-3-large", 3072, "cosine", "OpenAI large model"),
            ("all-MiniLM-L6-v2", 384, "cosine", "Sentence transformers model"),
        ]

        for model_id, dim, metric, desc in models:
            success = self.store.register_model(model_id, dim, metric, desc)
            assert success

        # Get all models
        registered_models = self.store.get_models()
        assert len(registered_models) == 3

        for model_id, _, _, _ in models:
            assert model_id in registered_models
            model_info = registered_models[model_id]
            assert "dim" in model_info
            assert "distance_metric" in model_info
            assert "description" in model_info

    def test_stats_collection(self):
        """Test statistics collection functionality."""
        # Register model and store some embeddings
        self.store.register_model("stats-test-model", 2, "cosine")

        # Store multiple embeddings
        for i in range(5):
            embedding = EmbeddingRecord(
                embedding_id=f"01HTEST000000000000000000{i}",
                doc_id=f"01HDOC0000000000000000000{i}",
                model_id="stats-test-model",
                dim=2,
                sha256="c" * 64,
                vector_ref=f"01HVEC0000000000000000000{i}",
                quantized=(i % 2 == 0),  # Mix of quantized/unquantized
            )

            vector = [float(i), float(i * 2)]
            success = self.store.store_embedding(
                embedding, vector, "shared:household", "GREEN"
            )
            assert success

        # Get statistics
        stats = self.store.get_stats()
        assert "total_embeddings" in stats
        assert "unique_models" in stats
        assert "unique_documents" in stats
        assert "model_distribution" in stats
        assert "quantization_distribution" in stats

        # Verify counts
        assert int(stats["total_embeddings"]) == 5
        assert int(stats["unique_models"]) >= 1
        assert int(stats["unique_documents"]) == 5

    def test_space_filtering(self):
        """Test space-based access filtering."""
        # Register model
        self.store.register_model("space-test-model", 2, "cosine")

        # Store embeddings in different spaces
        spaces = ["shared:household", "personal:alice", "personal:bob"]

        for i, space in enumerate(spaces):
            embedding = EmbeddingRecord(
                embedding_id=f"01HTEST00000000000000000{i}0",
                doc_id=f"01HDOC000000000000000000{i}0",
                model_id="space-test-model",
                dim=2,
                sha256="d" * 64,
                vector_ref=f"01HVEC000000000000000000{i}0",
            )

            vector = [float(i), float(i)]
            success = self.store.store_embedding(embedding, vector, space, "GREEN")
            assert success

        # Test space filtering in similarity search
        query = SimilarityQuery(
            vector=[0.0, 0.0], model_id="space-test-model", limit=10
        )

        # Search with space filter
        allowed_spaces = {"shared:household", "personal:alice"}
        results = self.store.similarity_search(query, allowed_spaces)

        # Should only return results from allowed spaces
        assert len(results) == 2
        for result in results:
            if result.metadata:
                assert result.metadata["space_id"] in allowed_spaces

    def test_vector_distance_metrics(self):
        """Test different distance metrics."""
        # Register model
        self.store.register_model("metric-test-model", 3, "cosine")

        # Store test vectors
        test_vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],  # This should be similar to both above
        ]

        for i, vector in enumerate(test_vectors):
            embedding = EmbeddingRecord(
                embedding_id=f"01HTEST0000000000000000{i:03d}",
                doc_id=f"01HDOC00000000000000000{i:03d}",
                model_id="metric-test-model",
                dim=3,
                sha256="e" * 64,
                vector_ref=f"01HVEC00000000000000000{i:03d}",
            )

            success = self.store.store_embedding(
                embedding, vector, "shared:household", "GREEN"
            )
            assert success

        # Test cosine similarity
        query_cosine = SimilarityQuery(
            vector=[1.0, 1.0, 0.0],
            model_id="metric-test-model",
            distance_metric="cosine",
            limit=3,
        )

        results_cosine = self.store.similarity_search(query_cosine)
        assert len(results_cosine) == 3

        # Test euclidean distance
        query_euclidean = SimilarityQuery(
            vector=[1.0, 1.0, 0.0],
            model_id="metric-test-model",
            distance_metric="euclidean",
            limit=3,
        )

        results_euclidean = self.store.similarity_search(query_euclidean)
        assert len(results_euclidean) == 3

    def test_privacy_bands(self):
        """Test privacy band filtering."""
        # Register model
        self.store.register_model("band-test-model", 2, "cosine")

        # Store embeddings with different privacy bands
        bands = ["GREEN", "AMBER", "RED"]

        for i, band in enumerate(bands):
            embedding = EmbeddingRecord(
                embedding_id=f"01HTEST00000000000000000{i}B",
                doc_id=f"01HDOC000000000000000000{i}B",
                model_id="band-test-model",
                dim=2,
                sha256="f" * 64,
                vector_ref=f"01HVEC000000000000000000{i}B",
            )

            vector = [float(i), float(i)]
            success = self.store.store_embedding(
                embedding, vector, "shared:household", band
            )
            assert success

        # Test band filtering
        query = SimilarityQuery(
            vector=[0.0, 0.0],
            model_id="band-test-model",
            bands=["GREEN", "AMBER"],  # Exclude RED
            limit=10,
        )

        results = self.store.similarity_search(query)
        assert len(results) == 2  # Should exclude RED band

        for result in results:
            if result.metadata:
                assert result.metadata["privacy_band"] in ["GREEN", "AMBER"]

    def test_error_handling(self):
        """Test error handling and edge cases."""
        # Test storing embedding with mismatched dimensions
        bad_embedding = EmbeddingRecord(
            embedding_id="01HTEST0000000000000000BAD",
            doc_id="01HDOC00000000000000000BAD",
            model_id="test-model",
            dim=5,  # Says 5 dimensions
            sha256="g" * 64,
            vector_ref="01HVEC00000000000000000BAD",
        )

        bad_vector = [1.0, 2.0, 3.0]  # Only 3 dimensions

        # This should fail due to dimension mismatch
        success = self.store.store_embedding(
            bad_embedding, bad_vector, "shared:household", "GREEN"
        )
        assert not success

        # Test retrieving non-existent embedding
        result = self.store.get_embedding("01HTEST0000000000000000XXX")
        assert result is None

        # Test similarity search with non-existent model
        query = SimilarityQuery(vector=[1.0, 2.0, 3.0], model_id="non-existent-model")

        results = self.store.similarity_search(query)
        assert len(results) == 0


if __name__ == "__main__":
    # Run basic functionality test
    test = TestEmbeddingsStore()
    test.setup_method()

    try:
        test.test_store_and_retrieve_embedding()
        test.test_similarity_search()
        test.test_model_registration()
        print("✅ All EmbeddingsStore tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        test.teardown_method()
