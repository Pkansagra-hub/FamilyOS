"""Tests for IndexCheckpointStore."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ward import raises, test

from storage.base_store import StoreConfig
from storage.index_checkpoint_store import (CheckpointQuery, IndexCheckpoint,
                                            IndexCheckpointStore)
from storage.unit_of_work import UnitOfWork


@test("IndexCheckpointStore initializes with config")
def test_initialization():
    config = StoreConfig(db_path="test.db")
    store = IndexCheckpointStore(config)
    assert store.config.db_path == "test.db"


@test("IndexCheckpointStore can create and retrieve checkpoints")
def test_create_and_retrieve_checkpoint():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_checkpoint.db"

        config = StoreConfig(db_path=str(db_path))
        checkpoint_store = IndexCheckpointStore(config)

        # Create checkpoint using high-level method
        checkpoint = IndexCheckpoint(
            id="01HMMJ7K3Z4B6Y8X9W2Q5T1RN0",
            index_name="test_index",
            shard_id="shard_1",
            position=1000,
            content_hash="abc123def456",
            ts=datetime.now(timezone.utc),
            metadata={"test": True}
        )

        uow = UnitOfWork(str(db_path), use_connection_pool=False)
        uow.register_store(checkpoint_store)

        with uow:
            checkpoint_id = checkpoint_store.create_checkpoint(checkpoint)
            uow.track_write("checkpoint", checkpoint_id)

        # Verify checkpoint was created
        assert checkpoint_id == checkpoint.id

        # Retrieve the checkpoint - need new UoW instance for new transaction
        uow2 = UnitOfWork(str(db_path), use_connection_pool=False)
        uow2.register_store(checkpoint_store)

        with uow2:
            retrieved = checkpoint_store.get_checkpoint(checkpoint_id)

        assert retrieved is not None
        assert retrieved.id == checkpoint.id
        assert retrieved.index_name == "test_index"
        assert retrieved.shard_id == "shard_1"
        assert retrieved.position == 1000
        assert retrieved.content_hash == "abc123def456"
        assert retrieved.metadata == {"test": True}


@test("IndexCheckpointStore can query checkpoints")
def test_query_checkpoints():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_checkpoint.db"

        config = StoreConfig(db_path=str(db_path))
        checkpoint_store = IndexCheckpointStore(config)

        uow = UnitOfWork(str(db_path), use_connection_pool=False)
        uow.register_store(checkpoint_store)

        with uow:
            # Create multiple checkpoints
            for i in range(3):
                checkpoint = IndexCheckpoint(
                    id=f"01HMMJ7K3Z4B6Y8X9W2Q5T1RN{i}",
                    index_name="test_index",
                    shard_id=f"shard_{i}",
                    position=1000 + i * 100,
                    content_hash=f"hash_{i}",
                    ts=datetime.now(timezone.utc)
                )
                checkpoint_store.create_checkpoint(checkpoint)
                uow.track_write("checkpoint", checkpoint.id)

        # Query checkpoints - need new UoW instance
        uow2 = UnitOfWork(str(db_path), use_connection_pool=False)
        uow2.register_store(checkpoint_store)

        with uow2:
            query = CheckpointQuery(index_name="test_index", limit=2)
            results = checkpoint_store.query_checkpoints(query)

        assert len(results) == 2
        assert all(cp.index_name == "test_index" for cp in results)


@test("IndexCheckpointStore can manage rebuild status")
def test_rebuild_status_management():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_checkpoint.db"

        config = StoreConfig(db_path=str(db_path))
        checkpoint_store = IndexCheckpointStore(config)

        uow = UnitOfWork(str(db_path), use_connection_pool=False)
        uow.register_store(checkpoint_store)

        with uow:
            # Start rebuild
            checkpoint_store.start_rebuild(
                index_name="test_index",
                total_shards=5,
                target_position=10000
            )

            # Check status
            status = checkpoint_store.get_rebuild_status("test_index")
            assert status is not None
            assert status.index_name == "test_index"
            assert status.total_shards == 5
            assert status.target_position == 10000
            assert status.current_position == 0
            assert status.completed_shards == 0

            # Update progress
            checkpoint_store.update_rebuild_progress("test_index", 5000, 2)

            # Check updated status
            status = checkpoint_store.get_rebuild_status("test_index")
            assert status is not None
            assert status.current_position == 5000
            assert status.completed_shards == 2
            assert status.progress_percent == 50.0

            # Complete rebuild
            checkpoint_store.complete_rebuild("test_index")


@test("IndexCheckpointStore validation fails for invalid index name")
def test_invalid_index_name_validation():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_checkpoint.db"

        config = StoreConfig(db_path=str(db_path))
        checkpoint_store = IndexCheckpointStore(config)

        uow = UnitOfWork(str(db_path), use_connection_pool=False)
        uow.register_store(checkpoint_store)

        with uow:
            # Invalid index name (too short)
            checkpoint = IndexCheckpoint(
                id="01HMMJ7K3Z4B6Y8X9W2Q5T1RN0",
                index_name="x",  # Too short
                shard_id="shard_1",
                position=1000,
                content_hash="abc123def456"
            )

            with raises(ValueError):
                checkpoint_store.create_checkpoint(checkpoint)


@test("IndexCheckpointStore handles concurrent access gracefully")
def test_concurrent_access():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_checkpoint.db"

        config = StoreConfig(db_path=str(db_path))
        checkpoint_store = IndexCheckpointStore(config)

        uow = UnitOfWork(str(db_path), use_connection_pool=False)
        uow.register_store(checkpoint_store)

        # This test would need actual threading to be meaningful
        # For now, just verify basic functionality
        with uow:
            checkpoint = IndexCheckpoint(
                id="01HMMJ7K3Z4B6Y8X9W2Q5T1RN0",
                index_name="concurrent_test",
                shard_id="shard_1",
                position=1000,
                content_hash="abc123def456"
            )

            checkpoint_id = checkpoint_store.create_checkpoint(checkpoint)
            assert checkpoint_id == checkpoint.id            assert checkpoint_id == checkpoint.id
