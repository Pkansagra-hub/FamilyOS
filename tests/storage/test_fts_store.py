"""Tests for FTS Store Implementation"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ward import raises, test

from storage.base_store import StoreConfig
from storage.fts_store import FTSDocument, FTSStore, SearchQuery


@test("FTSStore: Basic document storage and retrieval")
def test_fts_store_basic_operations():
    """Test basic FTS store operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Create test document
        doc = FTSDocument(
            doc_id="01HX3V6MFTSVEEVDEERY79QQT4",
            space_id="shared:household",
            text="SSA appointment booked for Thursday 2:30pm.",
            lang="en",
            ts=datetime.now(timezone.utc),
            band="GREEN",
            source="episodic",
            tokens_count=7,
        )

        # Store document
        result = store.store_document(doc)
        assert result is True

        # Retrieve document
        retrieved = store.get_document(doc.doc_id)
        assert retrieved is not None
        assert retrieved.doc_id == doc.doc_id
        assert retrieved.text == doc.text
        assert retrieved.space_id == doc.space_id

        store.close()


@test("FTSStore: Contract validation")
def test_fts_store_contract_validation():
    """Test that FTS store validates against contract schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Test invalid ULID
        with raises(ValueError):
            invalid_doc = FTSDocument(
                doc_id="invalid-ulid",  # Invalid ULID format
                space_id="shared:household",
                text="Test text",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            )
            store.store_document(invalid_doc)

        # Test invalid space_id
        with raises(ValueError):
            invalid_doc = FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT4",
                space_id="invalid-space",  # Invalid space format
                text="Test text",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            )
            store.store_document(invalid_doc)

        # Test invalid band
        with raises(ValueError):
            invalid_doc = FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT4",
                space_id="shared:household",
                text="Test text",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="INVALID",  # Invalid band
            )
            store.store_document(invalid_doc)

        store.close()


@test("FTSStore: Full-text search functionality")
def test_fts_search():
    """Test full-text search capabilities."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Store multiple documents
        docs = [
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT1",
                space_id="shared:household",
                text="Doctor appointment scheduled for Monday morning",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
                source="episodic",
            ),
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT2",
                space_id="shared:household",
                text="Dentist appointment booked for Thursday afternoon",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
                source="episodic",
            ),
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT3",
                space_id="personal:alice",
                text="Meeting with project team scheduled",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="AMBER",
                source="action",
            ),
        ]

        for doc in docs:
            store.store_document(doc)

        # Test search for "appointment"
        query = SearchQuery(text="appointment", limit=10)
        results = store.search(query)

        assert len(results) == 2  # Only household docs should match
        assert all("appointment" in result.text.lower() for result in results)

        # Test space filtering
        space_filter = {"shared:household"}
        results = store.search(query, space_filter)
        assert len(results) == 2
        assert all(result.space_id == "shared:household" for result in results)

        # Test band filtering
        query_amber = SearchQuery(text="meeting", bands=["AMBER"])
        results = store.search(query_amber)
        assert len(results) == 1
        assert results[0].metadata["band"] == "AMBER"

        store.close()


@test("FTSStore: Document segments support")
def test_fts_segments():
    """Test document segments functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Create document with segments
        doc = FTSDocument(
            doc_id="01HX3V6MFTSVEEVDEERY79QQT4",
            space_id="shared:household",
            text="This is a long document with multiple sections. Section 1 contains important information.",
            lang="en",
            ts=datetime.now(timezone.utc),
            band="GREEN",
            segments=[
                {"offset": 0, "length": 54, "section": "intro"},
                {"offset": 55, "length": 42, "section": "details"},
            ],
        )

        result = store.store_document(doc)
        assert result is True

        # Retrieve and verify segments
        retrieved = store.get_document(doc.doc_id)
        assert retrieved is not None
        assert retrieved.segments is not None
        assert len(retrieved.segments) == 2
        assert retrieved.segments[0]["section"] == "intro"
        assert retrieved.segments[1]["section"] == "details"

        store.close()


@test("FTSStore: Space-scoped security")
def test_fts_space_security():
    """Test space-scoped access control."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Store documents in different spaces
        docs = [
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT1",
                space_id="personal:alice",
                text="Private note about personal matters",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="RED",
            ),
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT2",
                space_id="shared:household",
                text="Family grocery list",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            ),
        ]

        for doc in docs:
            store.store_document(doc)

        # Test access with space filter
        household_filter = {"shared:household"}

        # Should only access household document
        household_doc = store.get_document(
            "01HX3V6MFTSVEEVDEERY79QQT2", household_filter
        )
        assert household_doc is not None
        assert household_doc.space_id == "shared:household"

        # Should not access personal document with household filter
        personal_doc = store.get_document(
            "01HX3V6MFTSVEEVDEERY79QQT1", household_filter
        )
        assert personal_doc is None

        # Test search with space filtering
        query = SearchQuery(text="note")
        results = store.search(query, household_filter)
        assert len(results) == 0  # Personal note not accessible

        store.close()


@test("FTSStore: Performance and caching")
def test_fts_performance():
    """Test FTS performance and caching features."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Store multiple documents for performance testing
        for i in range(50):
            doc = FTSDocument(
                doc_id=f"01HX3V6MFTSVEEVDEERY79QQ{i:02d}",
                space_id="shared:household",
                text=f"Test document number {i} with some searchable content about topic {i % 5}",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            )
            store.store_document(doc)

        # Test search performance
        query = SearchQuery(text="searchable", limit=20)
        results = store.search(query)
        assert len(results) == 20  # Limited by query limit

        # Test caching by running same query twice
        results2 = store.search(query)
        assert len(results2) == 20

        # Test statistics
        stats = store.get_stats()
        assert stats["total_documents"] == 50
        assert stats["language_distribution"]["en"] == 50
        assert "cache_size" in stats

        store.close()


@test("FTSStore: Advanced search features")
def test_fts_advanced_search():
    """Test advanced search features like phrase queries and proximity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Store documents with specific phrases
        docs = [
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT1",
                space_id="shared:household",
                text="The quick brown fox jumps over the lazy dog",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            ),
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT2",
                space_id="shared:household",
                text="A brown fox and a lazy cat in the garden",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            ),
        ]

        for doc in docs:
            store.store_document(doc)

        # Test phrase query
        phrase_query = SearchQuery(text='"brown fox"')
        results = store.search(phrase_query)
        assert len(results) >= 1

        # Test individual terms
        term_query = SearchQuery(text="brown AND fox")
        results = store.search(term_query)
        assert len(results) >= 1

        # Test with highlighting
        highlight_query = SearchQuery(text="fox", highlight=True)
        results = store.search(highlight_query)
        assert len(results) >= 1
        assert len(results[0].highlights) > 0  # Should have highlight positions

        store.close()


@test("FTSStore: Multi-language support")
def test_fts_multilingual():
    """Test multi-language support and filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Store documents in different languages
        docs = [
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT1",
                space_id="shared:household",
                text="Hello world, this is an English document",
                lang="en",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            ),
            FTSDocument(
                doc_id="01HX3V6MFTSVEEVDEERY79QQT2",
                space_id="shared:household",
                text="Hola mundo, este es un documento en español",
                lang="es",
                ts=datetime.now(timezone.utc),
                band="GREEN",
            ),
        ]

        for doc in docs:
            store.store_document(doc)

        # Test language filtering
        en_query = SearchQuery(text="document", languages=["en"])
        results = store.search(en_query)
        assert len(results) == 1
        assert results[0].metadata["lang"] == "en"

        es_query = SearchQuery(text="documento", languages=["es"])
        results = store.search(es_query)
        assert len(results) == 1
        assert results[0].metadata["lang"] == "es"

        # Test statistics by language
        stats = store.get_stats()
        assert stats["language_distribution"]["en"] == 1
        assert stats["language_distribution"]["es"] == 1

        store.close()


@test("FTSStore: Index management")
def test_fts_index_management():
    """Test FTS index management operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StoreConfig(db_path=str(Path(tmpdir) / "test.db"))
        store = FTSStore(config)

        # Store some documents
        doc = FTSDocument(
            doc_id="01HX3V6MFTSVEEVDEERY79QQT4",
            space_id="shared:household",
            text="Test document for index management",
            lang="en",
            ts=datetime.now(timezone.utc),
            band="GREEN",
        )
        store.store_document(doc)

        # Test index rebuild
        store.rebuild_index()  # Should not raise an error

        # Test index optimization
        store.optimize()  # Should not raise an error

        # Verify search still works after rebuild
        query = SearchQuery(text="index")
        results = store.search(query)
        assert len(results) == 1

        store.close()
