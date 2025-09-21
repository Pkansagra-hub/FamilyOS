"""
Test suite for VectorStore contract compliance and functionality.

This test suite validates the VectorStore implementation against:
1. vector_row.schema.json contract requirements
2. Vector operations and similarity search
3. Serialization and data type support
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

from ward import fixture, test

from storage.base_store import StoreConfig
from storage.vector_store import VectorRow, VectorStore


@fixture
def temp_store():
    """Create a temporary VectorStore for testing."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()
    config = StoreConfig(db_path=temp_db.name)
    store = VectorStore(config)

    yield store

    # Cleanup - close any connections first
    if hasattr(store, "_connection") and store._connection:
        store._connection.close()
    try:
        Path(temp_db.name).unlink(missing_ok=True)
    except PermissionError:
        # On Windows, files may still be locked, ignore
        pass


@test("VectorRow dataclass matches contract required fields")
def test_vector_row_contract_required_fields():
    """Test VectorRow dataclass matches vector_row.schema.json contract."""
    vector = [0.1, 0.2, 0.3, 0.4]

    row = VectorRow(
        vec_id="vec_01H8F9CQXK4YZJK0QWERTY1234",
        doc_id="doc_12345",
        space_id="personal:alice",
        model_id="text-embedding-ada-002",
        dim=4,
        vector=vector,
    )

    # Verify required fields are present
    assert row.vec_id == "vec_01H8F9CQXK4YZJK0QWERTY1234"
    assert row.doc_id == "doc_12345"
    assert row.space_id == "personal:alice"
    assert row.model_id == "text-embedding-ada-002"
    assert row.dim == 4
    assert row.vector == vector


@test("VectorRow dataclass supports optional fields")
def test_vector_row_contract_optional_fields():
    """Test VectorRow optional fields from contract."""
    vector = [0.1, 0.2, 0.3, 0.4]

    row = VectorRow(
        vec_id="vec_01H8F9CQXK4YZJK0QWERTY5678",
        doc_id="doc_67890",
        space_id="shared:household",
        model_id="all-mpnet-base-v2",
        dim=4,
        vector=vector,
        dtype="f32",
        norm=0.5477,
        index_name="main_index",
        timestamp="2023-09-12T10:30:00Z",
    )

    assert row.dtype == "f32"
    assert row.norm == 0.5477
    assert row.index_name == "main_index"
    assert row.timestamp == "2023-09-12T10:30:00Z"


@test("All data types from contract are supported")
def test_data_types_enum_compliance():
    """Test that all data types from contract are supported."""
    valid_dtypes = ["f32", "f16", "q8", "bfloat16"]
    vector = [0.1, 0.2, 0.3, 0.4]

    for dtype in valid_dtypes:
        row_data: Dict[str, Any] = {
            "vec_id": f"vec_{dtype}_test",
            "doc_id": "doc_test",
            "space_id": "personal:alice",
            "model_id": "test-model",
            "dim": 4,
            "vector": vector,
            "dtype": dtype,
        }
        row = VectorRow.from_dict(row_data)
        assert row.dtype == dtype


@test("to_dict output matches contract structure")
def test_to_dict_contract_compliance():
    """Test that to_dict output matches contract structure."""
    vector = [0.1, 0.2, 0.3, 0.4]

    row = VectorRow(
        vec_id="vec_01H8F9CQXK4YZJK0QWERTY1234",
        doc_id="doc_12345",
        space_id="personal:alice",
        model_id="text-embedding-ada-002",
        dim=4,
        vector=vector,
        dtype="f32",
        norm=0.5477,
        index_name="main_index",
        timestamp="2023-09-12T10:30:00Z",
    )

    result = row.to_dict()

    # Required fields must be present
    assert "vec_id" in result
    assert "doc_id" in result
    assert "space_id" in result
    assert "model_id" in result
    assert "dim" in result
    assert "vector" in result

    # Optional fields must be present when set
    assert "dtype" in result
    assert "norm" in result
    assert "index_name" in result
    assert "timestamp" in result

    # Values must match
    assert result["vec_id"] == "vec_01H8F9CQXK4YZJK0QWERTY1234"
    assert result["doc_id"] == "doc_12345"
    assert result["space_id"] == "personal:alice"
    assert result["model_id"] == "text-embedding-ada-002"
    assert result["dim"] == 4
    assert result["vector"] == vector
    assert result["dtype"] == "f32"
    assert result["norm"] == 0.5477
    assert result["index_name"] == "main_index"
    assert result["timestamp"] == "2023-09-12T10:30:00Z"


@test("from_dict handles contract-compliant data")
def test_from_dict_contract_compliance():
    """Test that from_dict handles contract-compliant data."""
    vector = [0.1, 0.2, 0.3, 0.4, 0.5]

    data: Dict[str, Any] = {
        "vec_id": "vec_01H8F9CQXK4YZJK0QWERTY1234",
        "doc_id": "doc_12345",
        "space_id": "personal:alice",
        "model_id": "text-embedding-ada-002",
        "dim": 5,
        "vector": vector,
        "dtype": "f32",
        "norm": 0.7416,
        "index_name": "semantic_index",
        "timestamp": "2023-09-12T10:30:00Z",
    }

    row = VectorRow.from_dict(data)

    assert row.vec_id == "vec_01H8F9CQXK4YZJK0QWERTY1234"
    assert row.doc_id == "doc_12345"
    assert row.space_id == "personal:alice"
    assert row.model_id == "text-embedding-ada-002"
    assert row.dim == 5
    assert row.vector == vector
    assert row.dtype == "f32"
    assert row.norm == 0.7416
    assert row.index_name == "semantic_index"
    assert row.timestamp == "2023-09-12T10:30:00Z"


@test("from_dict works with minimal required fields")
def test_from_dict_minimal_required_fields():
    """Test from_dict with only required fields."""
    vector = [0.1, 0.2, 0.3]

    data: Dict[str, Any] = {
        "vec_id": "vec_minimal",
        "doc_id": "doc_minimal",
        "space_id": "personal:alice",
        "model_id": "minimal-model",
        "dim": 3,
        "vector": vector,
    }

    row = VectorRow.from_dict(data)

    assert row.vec_id == "vec_minimal"
    assert row.doc_id == "doc_minimal"
    assert row.space_id == "personal:alice"
    assert row.model_id == "minimal-model"
    assert row.dim == 3
    assert row.vector == vector
    assert row.dtype is None
    assert row.norm is None
    assert row.index_name is None
    assert row.timestamp is None


@test("Store and retrieve vector rows")
def test_store_and_get_vector(temp_store=temp_store):
    """Test storing and retrieving vector rows."""
    vector = [0.1, 0.2, 0.3, 0.4, 0.5]

    row = VectorRow(
        vec_id="vec_test_001",
        doc_id="doc_test_001",
        space_id="personal:alice",
        model_id="text-embedding-ada-002",
        dim=5,
        vector=vector,
        dtype="f32",
        norm=0.7416,
    )

    # Store the vector
    vec_id = temp_store.store_vector(row)
    assert vec_id == "vec_test_001"

    # Retrieve the vector
    retrieved_row = temp_store.get_vector("vec_test_001")

    assert retrieved_row is not None
    assert retrieved_row.vec_id == row.vec_id
    assert retrieved_row.doc_id == row.doc_id
    assert retrieved_row.space_id == row.space_id
    assert retrieved_row.model_id == row.model_id
    assert retrieved_row.dim == row.dim

    # Use approximate equality for floating point vectors
    import math

    assert len(retrieved_row.vector) == len(row.vector)
    for i, (a, b) in enumerate(zip(retrieved_row.vector, row.vector)):
        assert math.isclose(a, b, rel_tol=1e-6), f"Vector element {i}: {a} != {b}"

    assert retrieved_row.dtype == row.dtype
    assert retrieved_row.norm == row.norm


@test("Filter vectors by model")
def test_get_vectors_by_model(temp_store=temp_store):
    """Test filtering vectors by model."""
    vectors = [
        VectorRow(
            vec_id="vec_ada_001",
            doc_id="doc_001",
            space_id="personal:alice",
            model_id="text-embedding-ada-002",
            dim=3,
            vector=[0.1, 0.2, 0.3],
        ),
        VectorRow(
            vec_id="vec_mpnet_001",
            doc_id="doc_002",
            space_id="personal:alice",
            model_id="all-mpnet-base-v2",
            dim=3,
            vector=[0.4, 0.5, 0.6],
        ),
        VectorRow(
            vec_id="vec_ada_002",
            doc_id="doc_003",
            space_id="personal:alice",
            model_id="text-embedding-ada-002",
            dim=3,
            vector=[0.7, 0.8, 0.9],
        ),
    ]

    for vector in vectors:
        temp_store.store_vector(vector)

    # Get Ada vectors only
    ada_vectors = temp_store.get_vectors_by_model(
        "text-embedding-ada-002", space_id="personal:alice"
    )
    assert len(ada_vectors) == 2
    for vector in ada_vectors:
        assert vector.model_id == "text-embedding-ada-002"

    # Get MPNet vectors only
    mpnet_vectors = temp_store.get_vectors_by_model(
        "all-mpnet-base-v2", space_id="personal:alice"
    )
    assert len(mpnet_vectors) == 1
    assert mpnet_vectors[0].model_id == "all-mpnet-base-v2"


@test("Vector similarity search")
def test_similarity_search(temp_store=temp_store):
    """Test vector similarity search functionality."""
    # Store test vectors
    vectors = [
        VectorRow(
            vec_id="vec_similar_001",
            doc_id="doc_001",
            space_id="personal:alice",
            model_id="test-model",
            dim=3,
            vector=[1.0, 0.0, 0.0],  # Unit vector along x-axis
        ),
        VectorRow(
            vec_id="vec_similar_002",
            doc_id="doc_002",
            space_id="personal:alice",
            model_id="test-model",
            dim=3,
            vector=[0.9, 0.1, 0.0],  # Close to x-axis
        ),
        VectorRow(
            vec_id="vec_different_001",
            doc_id="doc_003",
            space_id="personal:alice",
            model_id="test-model",
            dim=3,
            vector=[0.0, 1.0, 0.0],  # Unit vector along y-axis
        ),
    ]

    for vector in vectors:
        temp_store.store_vector(vector)

    # Search for vectors similar to [1.0, 0.0, 0.0]
    query_vector = [1.0, 0.0, 0.0]
    results = temp_store.similarity_search(
        query_vector, "test-model", space_id="personal:alice", limit=2
    )

    assert len(results) == 2

    # Results should be ordered by similarity (highest first)
    assert results[0][0].vec_id == "vec_similar_001"  # Exact match
    assert results[0][1] == 1.0  # Cosine similarity = 1.0

    assert results[1][0].vec_id == "vec_similar_002"  # Close match
    assert results[1][1] > 0.9  # High similarity


@test("Vector serialization and deserialization")
def test_vector_serialization():
    """Test vector serialization and deserialization."""
    vector_store = VectorStore(StoreConfig(db_path=":memory:"))

    # Test f32 serialization
    f32_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    serialized = vector_store._serialize_vector(f32_vector, "f32")
    deserialized = vector_store._deserialize_vector(serialized, 5, "f32")

    # Check that values are close (floating point precision)
    for orig, deser in zip(f32_vector, deserialized):
        assert abs(orig - deser) < 1e-6

    # Test f16 serialization
    f16_vector = [0.1, 0.2, 0.3]
    serialized_f16 = vector_store._serialize_vector(f16_vector, "f16")
    deserialized_f16 = vector_store._deserialize_vector(serialized_f16, 3, "f16")

    # f16 has lower precision
    for orig, deser in zip(f16_vector, deserialized_f16):
        assert abs(orig - deser) < 1e-3


@test("Cosine similarity calculation")
def test_cosine_similarity():
    """Test cosine similarity calculation."""
    vector_store = VectorStore(StoreConfig(db_path=":memory:"))

    # Test identical vectors
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    similarity = vector_store.cosine_similarity(vec1, vec2)
    assert abs(similarity - 1.0) < 1e-10

    # Test orthogonal vectors
    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    similarity = vector_store.cosine_similarity(vec3, vec4)
    assert abs(similarity - 0.0) < 1e-10

    # Test opposite vectors
    vec5 = [1.0, 0.0, 0.0]
    vec6 = [-1.0, 0.0, 0.0]
    similarity = vector_store.cosine_similarity(vec5, vec6)
    assert abs(similarity - (-1.0)) < 1e-10


@test("Filter vectors by index name")
def test_get_index_vectors(temp_store=temp_store):
    """Test filtering vectors by index name."""
    vectors = [
        VectorRow(
            vec_id="vec_main_001",
            doc_id="doc_001",
            space_id="personal:alice",
            model_id="test-model",
            dim=3,
            vector=[0.1, 0.2, 0.3],
            index_name="main_index",
        ),
        VectorRow(
            vec_id="vec_secondary_001",
            doc_id="doc_002",
            space_id="personal:alice",
            model_id="test-model",
            dim=3,
            vector=[0.4, 0.5, 0.6],
            index_name="secondary_index",
        ),
        VectorRow(
            vec_id="vec_main_002",
            doc_id="doc_003",
            space_id="personal:alice",
            model_id="test-model",
            dim=3,
            vector=[0.7, 0.8, 0.9],
            index_name="main_index",
        ),
    ]

    for vector in vectors:
        temp_store.store_vector(vector)

    # Get main index vectors
    main_vectors = temp_store.get_index_vectors("main_index", space_id="personal:alice")
    assert len(main_vectors) == 2
    for vector in main_vectors:
        assert vector.index_name == "main_index"

    # Get secondary index vectors
    secondary_vectors = temp_store.get_index_vectors(
        "secondary_index", space_id="personal:alice"
    )
    assert len(secondary_vectors) == 1
    assert secondary_vectors[0].index_name == "secondary_index"


@test("Update and delete vector rows")
def test_update_and_delete_vectors(temp_store=temp_store):
    """Test updating and deleting vector rows."""
    row = VectorRow(
        vec_id="vec_update_test",
        doc_id="doc_update",
        space_id="personal:alice",
        model_id="test-model",
        dim=3,
        vector=[0.1, 0.2, 0.3],
        index_name="original_index",
    )

    # Store the vector
    temp_store.store_vector(row)

    # Update the vector
    updated_row = VectorRow(
        vec_id="vec_update_test",
        doc_id="doc_update",
        space_id="personal:alice",
        model_id="test-model",
        dim=3,
        vector=[0.4, 0.5, 0.6],
        index_name="updated_index",
        norm=0.8775,
    )

    update_result = temp_store.update_vector("vec_update_test", updated_row)
    assert update_result is True

    # Verify the update
    retrieved_row = temp_store.get_vector("vec_update_test")
    assert retrieved_row is not None

    # Use approximate equality for floating point vectors
    import math

    expected_vector = [0.4, 0.5, 0.6]
    assert len(retrieved_row.vector) == len(expected_vector)
    for i, (a, b) in enumerate(zip(retrieved_row.vector, expected_vector)):
        assert math.isclose(a, b, rel_tol=1e-6), f"Vector element {i}: {a} != {b}"

    assert retrieved_row.index_name == "updated_index"
    assert retrieved_row.norm == 0.8775

    # Delete the vector
    delete_result = temp_store.delete_vector("vec_update_test")
    assert delete_result is True

    # Verify deletion
    deleted_row = temp_store.get_vector("vec_update_test")
    assert deleted_row is None


@test("List vectors with filters and limits")
def test_list_all_vectors(temp_store=temp_store):
    """Test listing all vectors in the store."""
    vectors = [
        VectorRow(
            vec_id="vec_list_001",
            doc_id="doc_001",
            space_id="personal:alice",
            model_id="test-model",
            dim=2,
            vector=[0.1, 0.2],
        ),
        VectorRow(
            vec_id="vec_list_002",
            doc_id="doc_002",
            space_id="personal:alice",
            model_id="test-model",
            dim=2,
            vector=[0.3, 0.4],
        ),
        VectorRow(
            vec_id="vec_list_003",
            doc_id="doc_003",
            space_id="shared:household",
            model_id="test-model",
            dim=2,
            vector=[0.5, 0.6],
        ),
    ]

    for vector in vectors:
        temp_store.store_vector(vector)

    # List all vectors
    all_vectors = temp_store.list_vectors()
    assert len(all_vectors) >= 3

    # List vectors with space filter
    alice_vectors = temp_store.list_vectors(space_id="personal:alice")
    assert len(alice_vectors) == 2

    # List vectors with limit
    limited_vectors = temp_store.list_vectors(limit=1)
    assert len(limited_vectors) == 1


@test("Large vector handling")
def test_large_vector_handling(temp_store=temp_store):
    """Test handling of large vectors."""
    # Create a large vector (1536 dimensions like OpenAI embeddings)
    large_vector = [i * 0.001 for i in range(1536)]

    row = VectorRow(
        vec_id="vec_large_test",
        doc_id="doc_large",
        space_id="personal:alice",
        model_id="text-embedding-ada-002",
        dim=1536,
        vector=large_vector,
        dtype="f32",
    )

    # Store and retrieve the large vector
    vec_id = temp_store.store_vector(row)
    assert vec_id == "vec_large_test"

    retrieved_row = temp_store.get_vector("vec_large_test")
    assert retrieved_row is not None
    assert retrieved_row.dim == 1536
    assert len(retrieved_row.vector) == 1536

    # Verify first and last elements
    assert abs(retrieved_row.vector[0] - 0.0) < 1e-6
    assert abs(retrieved_row.vector[-1] - 1.535) < 1e-3
