"""
Simple test for IndexConfigStore to verify basic functionality.
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


@test("IndexConfigStore basic CRUD operations work")
def test_basic_crud():
    """Test basic CRUD operations for IndexConfigStore."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Set up store and transaction
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)

        # Register store before transaction
        uow.register_store(config_store)

        # Create test configuration
        fts_config = IndexConfig(
            index_name="test_index",
            type="fts",
            space_id="shared:household",
            band_min="GREEN",
            fts_config=FTSConfig(analyzer="porter", languages=["en"]),
        )

        with uow:
            # Create
            index_name = config_store.create_config(fts_config)
            assert index_name == "test_index"

            # Read
            retrieved = config_store.get_config("test_index")
            assert retrieved is not None
            assert retrieved.index_name == "test_index"
            assert retrieved.type == "fts"

            # Update
            fts_config.refresh_interval = 300
            result = config_store.update_config(fts_config)
            assert result is True

            # Verify update
            updated = config_store.get_config("test_index")
            assert updated is not None
            assert updated.refresh_interval == 300

            # Delete
            delete_result = config_store.delete_config("test_index")
            assert delete_result is True

            # Verify deletion
            deleted = config_store.get_config("test_index")
            assert deleted is None

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Configuration validation works correctly")
def test_config_validation():
    """Test that configuration validation catches invalid data."""
    # FTS without fts_config should fail
    with raises(ValueError):
        IndexConfig(
            index_name="invalid",
            type="fts",
            space_id="shared:household",
            band_min="GREEN",
        )

    # Embeddings without embeddings_config should fail
    with raises(ValueError):
        IndexConfig(
            index_name="invalid",
            type="embeddings",
            space_id="shared:household",
            band_min="GREEN",
        )


@test("List operations work correctly")
def test_list_operations():
    """Test listing configurations with filtering."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        config = StoreConfig(db_path=db_path)
        config_store = IndexConfigStore(config)
        uow = UnitOfWork(db_path, use_connection_pool=False)

        uow.register_store(config_store)

        with uow:
            # Create multiple configs
            fts_config = IndexConfig(
                index_name="fts_index",
                type="fts",
                space_id="shared:household",
                band_min="GREEN",
                fts_config=FTSConfig(analyzer="porter"),
            )

            emb_config = IndexConfig(
                index_name="emb_index",
                type="embeddings",
                space_id="shared:household",
                band_min="AMBER",
                embeddings_config=EmbeddingsConfig(model_id="test", dimensions=100),
            )

            config_store.create_config(fts_config)
            config_store.create_config(emb_config)

            # List all
            all_configs = config_store.list_configs()
            assert len(all_configs) == 2

            # Filter by type
            fts_configs = config_store.get_configs_by_type("fts")
            assert len(fts_configs) == 1
            assert fts_configs[0].type == "fts"

            emb_configs = config_store.get_configs_by_type("embeddings")
            assert len(emb_configs) == 1
            assert emb_configs[0].type == "embeddings"

    finally:
        Path(db_path).unlink(missing_ok=True)
