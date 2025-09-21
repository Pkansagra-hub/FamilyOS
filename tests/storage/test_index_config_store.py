"""
Test suite for IndexConfigStore using Ward framework.

Tests:
- CRUD operations for index configurations
- Configuration validation and constraints
- Space and band-based filtering
- UnitOfWork integration
- Error handling and edge cases
"""

import tempfile
from pathlib import Path

from ward import raises, test

from storage import (
    EmbeddingsConfig,
    FTSConfig,
    IndexConfig,
    IndexConfigStore,
    StoreConfig,
    UnitOfWork,
)


def create_temp_db():
    """Create a temporary database for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return temp_file.name


def create_sample_fts_config():
    """Create a sample FTS index configuration."""
    return IndexConfig(
        index_name="test_fts_index",
        type="fts",
        space_id="shared:household",
        band_min="GREEN",
        fts_config=FTSConfig(
            analyzer="porter",
            tokenizer="unicode61",
            stemming=True,
            languages=["en", "es"],
        ),
        refresh_interval=120,
        max_size_mb=500,
        metadata={"test": True, "purpose": "search"},
    )


def create_sample_embeddings_config():
    """Create a sample embeddings index configuration."""
    return IndexConfig(
        index_name="test_embeddings_index",
        type="embeddings",
        space_id="shared:household",
        band_min="AMBER",
        embeddings_config=EmbeddingsConfig(
            model_id="sentence-transformers/all-MiniLM-L6-v2",
            dimensions=384,
            similarity_metric="cosine",
            quantization=False,
        ),
        refresh_interval=300,
        max_size_mb=2000,
        metadata={"model_version": "2.0", "domain": "text"},
    )


@test("IndexConfigStore can be created and initialized")
def test_config_store_creation():
    """Test that IndexConfigStore can be created and properly initialized."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)

        # Register store before starting transaction
        uow.register_store(config_store)

        with uow:
            # Store should initialize its schema without error
            assert config_store.get_store_name() == "indexconfig"
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("FTS index configuration can be created and retrieved")
def test_create_and_get_fts_config():
    """Test creating and retrieving an FTS index configuration."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_fts_config = create_sample_fts_config()

        # Register store before starting transaction
        uow.register_store(config_store)

        with uow:
            # Create the configuration
            index_name = config_store.create_config(sample_fts_config)
            assert index_name == "test_fts_index"

            # Retrieve the configuration
            retrieved = config_store.get_config("test_fts_index")
            assert retrieved is not None
            assert retrieved.index_name == "test_fts_index"
            assert retrieved.type == "fts"
            assert retrieved.space_id == "shared:household"
            assert retrieved.band_min == "GREEN"
            assert retrieved.fts_config is not None
            assert retrieved.fts_config.analyzer == "porter"
            assert retrieved.fts_config.languages == ["en", "es"]
            assert retrieved.embeddings_config is None
            assert retrieved.metadata["test"] is True
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Embeddings index configuration can be created and retrieved")
def test_create_and_get_embeddings_config():
    """Test creating and retrieving an embeddings index configuration."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_embeddings_config = create_sample_embeddings_config()

        with uow:
            uow.register_store(config_store)

            # Create the configuration
            index_name = config_store.create_config(sample_embeddings_config)
            assert index_name == "test_embeddings_index"

            # Retrieve the configuration
            retrieved = config_store.get_config("test_embeddings_index")
            assert retrieved is not None
            assert retrieved.index_name == "test_embeddings_index"
            assert retrieved.type == "embeddings"
            assert retrieved.space_id == "shared:household"
            assert retrieved.band_min == "AMBER"
            assert retrieved.embeddings_config is not None
            assert (
                retrieved.embeddings_config.model_id
                == "sentence-transformers/all-MiniLM-L6-v2"
            )
            assert retrieved.embeddings_config.dimensions == 384
            assert retrieved.fts_config is None
            assert retrieved.metadata["model_version"] == "2.0"
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Index configuration can be updated")
def test_update_config():
    """Test updating an existing index configuration."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_fts_config = create_sample_fts_config()

        with uow:
            uow.register_store(config_store)

            # Create initial configuration
            config_store.create_config(sample_fts_config)

            # Update the configuration
            updated_config = sample_fts_config
            updated_config.refresh_interval = 600
            updated_config.band_min = "AMBER"
            updated_config.metadata["updated"] = True

            result = config_store.update_config(updated_config)
            assert result is True

            # Verify the update
            retrieved = config_store.get_config("test_fts_index")
            assert retrieved is not None
            assert retrieved.refresh_interval == 600
            assert retrieved.band_min == "AMBER"
            assert retrieved.metadata["updated"] is True
            assert retrieved.updated_ts > retrieved.created_ts
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Index configuration can be deleted")
def test_delete_config():
    """Test deleting an index configuration."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_fts_config = create_sample_fts_config()

        with uow:
            uow.register_store(config_store)

            # Create configuration
            config_store.create_config(sample_fts_config)

            # Verify it exists
            assert config_store.config_exists("test_fts_index") is True

            # Delete it
            result = config_store.delete_config("test_fts_index")
            assert result is True

            # Verify it's gone
            assert config_store.config_exists("test_fts_index") is False
            assert config_store.get_config("test_fts_index") is None
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("List configurations with no filters returns all configs")
def test_list_all_configs():
    """Test listing all index configurations."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_fts_config = create_sample_fts_config()
        sample_embeddings_config = create_sample_embeddings_config()

        with uow:
            uow.register_store(config_store)

            # Create multiple configurations
            config_store.create_config(sample_fts_config)
            config_store.create_config(sample_embeddings_config)

            # List all configurations
            configs = config_store.list_configs()
            assert len(configs) == 2

            # Check both configs are present
            names = [config.index_name for config in configs]
            assert "test_fts_index" in names
            assert "test_embeddings_index" in names
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("List configurations can filter by type")
def test_list_configs_by_type():
    """Test filtering configurations by index type."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_fts_config = create_sample_fts_config()
        sample_embeddings_config = create_sample_embeddings_config()

        with uow:
            uow.register_store(config_store)

            # Create multiple configurations
            config_store.create_config(sample_fts_config)
            config_store.create_config(sample_embeddings_config)

            # Filter by FTS type
            fts_configs = config_store.get_configs_by_type("fts")
            assert len(fts_configs) == 1
            assert fts_configs[0].type == "fts"
            assert fts_configs[0].index_name == "test_fts_index"

            # Filter by embeddings type
            emb_configs = config_store.get_configs_by_type("embeddings")
            assert len(emb_configs) == 1
            assert emb_configs[0].type == "embeddings"
            assert emb_configs[0].index_name == "test_embeddings_index"
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Configuration validation catches invalid data")
def test_config_validation():
    """Test that IndexConfig validation catches invalid configurations."""
    # FTS config without fts_config should raise error
    with raises(ValueError):
        IndexConfig(
            index_name="invalid_fts",
            type="fts",
            space_id="shared:household",
            band_min="GREEN",
        )

    # Embeddings config without embeddings_config should raise error
    with raises(ValueError):
        IndexConfig(
            index_name="invalid_embeddings",
            type="embeddings",
            space_id="shared:household",
            band_min="GREEN",
        )

    # FTS config with embeddings_config should raise error
    with raises(ValueError):
        IndexConfig(
            index_name="mixed_config",
            type="fts",
            space_id="shared:household",
            band_min="GREEN",
            fts_config=FTSConfig(analyzer="porter"),
            embeddings_config=EmbeddingsConfig(model_id="test", dimensions=100),
        )


@test("Invalid index name patterns are rejected")
def test_invalid_index_name_patterns():
    """Test that invalid index name patterns are rejected."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)

        with uow:
            uow.register_store(config_store)

            invalid_configs = [
                # Too short
                IndexConfig(
                    index_name="x",
                    type="fts",
                    space_id="shared:household",
                    band_min="GREEN",
                    fts_config=FTSConfig(analyzer="simple"),
                ),
                # Too long
                IndexConfig(
                    index_name="x" * 65,
                    type="fts",
                    space_id="shared:household",
                    band_min="GREEN",
                    fts_config=FTSConfig(analyzer="simple"),
                ),
                # Invalid characters
                IndexConfig(
                    index_name="invalid@name!",
                    type="fts",
                    space_id="shared:household",
                    band_min="GREEN",
                    fts_config=FTSConfig(analyzer="simple"),
                ),
            ]

            for invalid_config in invalid_configs:
                with raises(ValueError):
                    config_store.create_config(invalid_config)
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Update non-existent configuration returns False")
def test_update_nonexistent_config():
    """Test that updating a non-existent configuration returns False."""
    db_path = create_temp_db()
    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)
        sample_fts_config = create_sample_fts_config()

        with uow:
            uow.register_store(config_store)

            result = config_store.update_config(sample_fts_config)
            assert result is False
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Configuration serialization and deserialization preserves data")
def test_config_serialization():
    """Test that configuration serialization/deserialization preserves all data."""
    sample_fts_config = create_sample_fts_config()
    sample_embeddings_config = create_sample_embeddings_config()

    # Test FTS config
    fts_dict = sample_fts_config.to_dict()
    fts_restored = IndexConfig.from_dict(fts_dict)

    assert fts_restored.index_name == sample_fts_config.index_name
    assert fts_restored.type == sample_fts_config.type
    assert fts_restored.fts_config is not None
    assert sample_fts_config.fts_config is not None
    assert fts_restored.fts_config.analyzer == sample_fts_config.fts_config.analyzer
    assert fts_restored.fts_config.languages == sample_fts_config.fts_config.languages
    assert fts_restored.metadata == sample_fts_config.metadata

    # Test embeddings config
    emb_dict = sample_embeddings_config.to_dict()
    emb_restored = IndexConfig.from_dict(emb_dict)

    assert emb_restored.index_name == sample_embeddings_config.index_name
    assert emb_restored.type == sample_embeddings_config.type
    assert emb_restored.embeddings_config is not None
    assert sample_embeddings_config.embeddings_config is not None
    assert (
        emb_restored.embeddings_config.model_id
        == sample_embeddings_config.embeddings_config.model_id
    )
    assert (
        emb_restored.embeddings_config.dimensions
        == sample_embeddings_config.embeddings_config.dimensions
    )
    assert emb_restored.metadata == sample_embeddings_config.metadata
