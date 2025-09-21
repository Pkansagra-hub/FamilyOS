"""
Integration tests for CA3 Pattern Completer with storage backends.

These tests verify the complete integration between:
- CA3PatternCompleter
- HippocampusStore (with new find_codes_in_space method)
- VectorStore (with new get_embedding method)
- SDRProcessor for coding operations

Tests follow contracts-first approach ensuring storage compliance.
"""

import asyncio
import tempfile
from pathlib import Path

from ward import fixture, test

from hippocampus.completer import CA3PatternCompleter, CompletionConfig
from hippocampus.sdr import SDRProcessor
from hippocampus.types import CompletionCandidate
from storage.base_store import StoreConfig
from storage.hippocampus_store import HippocampusStore
from storage.vector_store import VectorRow, VectorStore


@fixture
def temp_db_config():
    """Create temporary database configuration for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_hippocampus.db"
        yield StoreConfig(db_path=str(db_path))


@fixture
def hippocampus_store(temp_db_config=temp_db_config):
    """Create test hippocampus store."""
    store = HippocampusStore(temp_db_config)
    yield store
    store.close()


@fixture
def vector_store(temp_db_config=temp_db_config):
    """Create test vector store."""
    # Use different DB for vector store
    vector_config = StoreConfig(
        db_path=str(Path(temp_db_config.db_path).parent / "test_vector.db")
    )
    store = VectorStore(vector_config)
    yield store
    store.close()


@fixture
def sdr_processor():
    """Create SDR processor for testing."""
    return SDRProcessor()


@fixture
def ca3_completer(
    sdr_processor=sdr_processor,
    hippocampus_store=hippocampus_store,
    vector_store=vector_store,
):
    """Create CA3 completer with test stores."""
    config = CompletionConfig(lambda_weight=0.7, max_candidates=100, min_score=0.1)
    return CA3PatternCompleter(
        sdr_processor=sdr_processor,
        config=config,
        hippocampus_store=hippocampus_store,
        vector_store=vector_store,
    )


@test("CA3PatternCompleter initializes with storage backends")
def test_ca3_initialization(ca3_completer=ca3_completer):
    """Test that CA3 completer initializes properly with storage."""
    assert ca3_completer.sdr_processor is not None
    assert ca3_completer.hippocampus_store is not None
    assert ca3_completer.vector_store is not None
    assert ca3_completer.config.lambda_weight == 0.7


@test("HippocampusStore.find_codes_in_space returns correct format")
def test_hippocampus_find_codes_contract(
    hippocampus_store=hippocampus_store, sdr_processor=sdr_processor
):
    """Test that find_codes_in_space follows the storage contract."""
    space_id = "personal:test_user"

    # Create sample trace data following hippocampus_trace.schema.json
    sample_text = "The quick brown fox jumps over the lazy dog"
    tokens = sdr_processor.tokenize_to_shingles(sample_text)
    simhash_bits, simhash_hex = sdr_processor.compute_simhash(tokens)
    minhash = sdr_processor.compute_minhash(tokens)

    trace_data = {
        "id": "01HN2QF8M0J7K9E8D6C4B5A3Z2",  # Sample ULID
        "space_id": space_id,
        "ts": "2024-01-15T10:30:00Z",
        "simhash_hex": simhash_hex,
        "minhash32": minhash,
        "novelty": 0.85,
        "meta": {"test": True},
    }

    # Store the trace
    created_trace = hippocampus_store.create(trace_data)
    assert created_trace["id"] == trace_data["id"]

    # Test find_codes_in_space returns expected format
    codes = hippocampus_store.find_codes_in_space(space_id, limit=10)

    assert len(codes) == 1
    code = codes[0]

    # Verify contract compliance
    assert "id" in code
    assert "simhash_hex" in code
    assert "minhash32" in code
    assert "novelty" in code

    assert code["id"] == trace_data["id"]
    assert code["simhash_hex"] == simhash_hex
    assert code["minhash32"] == minhash
    assert code["novelty"] == 0.85


@test("VectorStore.get_embedding returns correct format")
def test_vector_store_get_embedding_contract(vector_store=vector_store):
    """Test that get_embedding follows the expected interface."""
    space_id = "personal:test_user"
    event_id = "01HN2QF8M0J7K9E8D6C4B5A3Z2"

    # Create sample vector data following vector_row.schema.json
    vector_data = VectorRow(
        vec_id="01HN2QF8M0J7K9E8D6C4B5A3Z3",
        doc_id=event_id,  # event_id maps to doc_id
        space_id=space_id,
        model_id="text-embedding-ada-002",
        dim=1536,
        vector=[0.1, 0.2, 0.3, 0.4, 0.5] * 307 + [0.1],  # 1536 dimensions
        dtype="f32",
        norm=1.0,
    )

    # Store the vector
    stored_vec_id = vector_store.store_vector(vector_data)
    assert stored_vec_id == vector_data.vec_id

    # Test get_embedding returns expected format
    embedding = vector_store.get_embedding(event_id)

    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 1536
    assert all(isinstance(x, (int, float)) for x in embedding)
    assert embedding[0] == 0.1
    assert embedding[1] == 0.2


@test("CA3 pattern completion with SDR-only mode")
def test_ca3_sdr_only_completion(
    ca3_completer=ca3_completer,
    hippocampus_store=hippocampus_store,
    sdr_processor=sdr_processor,
):
    """Test CA3 pattern completion using only SDR similarity."""
    space_id = "personal:test_user"

    # Store multiple memory traces
    sample_texts = [
        "The quick brown fox jumps over the lazy dog",
        "A fast brown fox leaps across the sleepy dog",
        "The cat sat on the mat",
        "Machine learning models process text data",
    ]

    stored_traces = []
    for i, text in enumerate(sample_texts):
        tokens = sdr_processor.tokenize_to_shingles(text)
        simhash_bits, simhash_hex = sdr_processor.compute_simhash(tokens)
        minhash = sdr_processor.compute_minhash(tokens)

        trace_data = {
            "id": f"01HN2QF8M0J7K9E8D6C4B5A{i:02d}",
            "space_id": space_id,
            "ts": f"2024-01-15T10:3{i}:00Z",
            "simhash_hex": simhash_hex,
            "minhash32": minhash,
            "novelty": 0.8 - (i * 0.1),  # Decreasing novelty
            "meta": {"text": text},
        }

        stored_trace = hippocampus_store.create(trace_data)
        stored_traces.append(stored_trace)

    # Test pattern completion with similar cue
    cue_text = "The brown fox jumps"  # Similar to first two texts

    # Run completion (SDR-only mode since no embedding provided)
    candidates = asyncio.run(
        ca3_completer.complete_pattern(
            space_id=space_id,
            cue_text=cue_text,
            k=3,
            cue_embedding=None,  # SDR-only mode
        )
    )

    # Verify results
    assert len(candidates) >= 1  # Should find at least one match
    assert len(candidates) <= 3  # Respects k limit

    # Check candidate structure
    for candidate in candidates:
        assert isinstance(candidate, CompletionCandidate)
        assert hasattr(candidate, "event_id")
        assert hasattr(candidate, "score")
        assert hasattr(candidate, "explanation")
        assert 0.0 <= candidate.score <= 1.0
        assert len(candidate.explanation) > 0
        assert "sdr" in candidate.explanation[0]  # Should indicate SDR mode

    # Top candidate should be most similar (likely first or second text)
    top_candidate = candidates[0]
    assert top_candidate.event_id in [stored_traces[0]["id"], stored_traces[1]["id"]]


@test("CA3 pattern completion with hybrid vector+SDR mode")
def test_ca3_hybrid_completion(
    ca3_completer=ca3_completer,
    hippocampus_store=hippocampus_store,
    vector_store=vector_store,
    sdr_processor=sdr_processor,
):
    """Test CA3 pattern completion using hybrid vector+SDR scoring."""
    space_id = "personal:test_user"

    # Create memory with both hippocampus trace and vector embedding
    text = "Machine learning processes natural language data"
    tokens = sdr_processor.tokenize_to_shingles(text)
    simhash_bits, simhash_hex = sdr_processor.compute_simhash(tokens)
    minhash = sdr_processor.compute_minhash(tokens)

    event_id = "01HN2QF8M0J7K9E8D6C4B5A0"

    # Store hippocampus trace
    trace_data = {
        "id": event_id,
        "space_id": space_id,
        "ts": "2024-01-15T10:30:00Z",
        "simhash_hex": simhash_hex,
        "minhash32": minhash,
        "novelty": 0.9,
        "meta": {"text": text},
    }
    hippocampus_store.create(trace_data)

    # Store vector embedding
    vector_data = VectorRow(
        vec_id="01HN2QF8M0J7K9E8D6C4B5A1",
        doc_id=event_id,  # Links to the same event
        space_id=space_id,
        model_id="text-embedding-ada-002",
        dim=5,  # Simplified for testing
        vector=[0.8, 0.6, 0.4, 0.2, 0.1],  # Mock embedding
        dtype="f32",
        norm=1.0,
    )
    vector_store.store_vector(vector_data)

    # Test completion with cue embedding
    cue_text = "AI models analyze text"
    cue_embedding = [0.7, 0.5, 0.3, 0.1, 0.2]  # Similar mock embedding

    candidates = asyncio.run(
        ca3_completer.complete_pattern(
            space_id=space_id, cue_text=cue_text, k=1, cue_embedding=cue_embedding
        )
    )

    # Verify hybrid mode results
    assert len(candidates) == 1
    candidate = candidates[0]

    assert candidate.event_id == event_id
    assert candidate.score > 0.1  # Should have reasonable score
    assert "vector" in candidate.explanation[0]  # Should indicate vector mode
    assert "fusion" in candidate.explanation[0]  # Should indicate fusion scoring


@test("CA3 handles empty space gracefully")
def test_ca3_empty_space(ca3_completer=ca3_completer):
    """Test CA3 behavior when no memories exist in space."""
    empty_space_id = "personal:empty_user"

    candidates = asyncio.run(
        ca3_completer.complete_pattern(
            space_id=empty_space_id, cue_text="Any text", k=5
        )
    )

    assert candidates == []


@test("CA3 respects minimum score threshold")
def test_ca3_min_score_filtering(
    ca3_completer=ca3_completer,
    hippocampus_store=hippocampus_store,
    sdr_processor=sdr_processor,
):
    """Test that CA3 filters out candidates below minimum score."""
    space_id = "personal:test_user"

    # Store a very dissimilar memory
    dissimilar_text = "xyz abc def random words"
    tokens = sdr_processor.tokenize_to_shingles(dissimilar_text)
    simhash_bits, simhash_hex = sdr_processor.compute_simhash(tokens)
    minhash = sdr_processor.compute_minhash(tokens)

    trace_data = {
        "id": "01HN2QF8M0J7K9E8D6C4B5A0",
        "space_id": space_id,
        "ts": "2024-01-15T10:30:00Z",
        "simhash_hex": simhash_hex,
        "minhash32": minhash,
        "novelty": 0.5,
        "meta": {"text": dissimilar_text},
    }
    hippocampus_store.create(trace_data)

    # Test with high minimum score threshold
    ca3_completer.config.min_score = 0.8  # High threshold

    candidates = asyncio.run(
        ca3_completer.complete_pattern(
            space_id=space_id,
            cue_text="The quick brown fox",  # Very different from stored text
            k=10,
        )
    )

    # Should filter out the dissimilar candidate
    assert len(candidates) == 0  # No candidates above threshold


# Additional test cases for edge conditions and performance would go here
# Following WARD's recommendation for comprehensive testing


# TODO: Add performance tests for P95 targets
# TODO: Add contract validation tests against storage schemas
# TODO: Add error handling tests for storage failures
# TODO: Add space isolation tests for privacy compliance
