"""
Simple test for Epic 2.1 Issue 2.1.2 - Sequence Management.

Following the exact pattern from test_episodic_store_contracts.py
"""

import os
import sqlite3
# Add parent directory to path for imports
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage.base_store import StoreConfig
from storage.episodic_store import EpisodicSequence, EpisodicStore


def test_simple_sequence_management():
    """Test basic sequence management functionality."""
    print("Testing simple sequence management...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test.db")
        store = EpisodicStore(config)

        # Connect to database
        conn = sqlite3.connect(config.db_path)
        conn.row_factory = sqlite3.Row

        try:
            # Initialize store and begin transaction
            store.begin_transaction(conn)

            # Create a simple sequence
            sequence = EpisodicSequence(
                sequence_id="01BX5ZZKBKACTAV9WEVGEMMV99",
                space_id="personal:test.space",
                ts=datetime.fromisoformat("2024-01-01T10:00:00"),
                label="Test Sequence",
                items=[
                    {"id": "01BX5ZZKBKACTAV9WEVGEMMV01", "ts": "2024-01-01T10:00:00"},
                    {"id": "01BX5ZZKBKACTAV9WEVGEMMV02", "ts": "2024-01-01T11:00:00", "weight": 0.8}
                ],
                closed=False
            )

            # Test create sequence
            created_id = store.create_sequence(sequence)
            assert created_id == "01BX5ZZKBKACTAV9WEVGEMMV99"
            print("✅ Sequence creation passed")

            # Test get sequence
            retrieved = store.get_sequence("01BX5ZZKBKACTAV9WEVGEMMV99")
            assert retrieved is not None
            assert retrieved.sequence_id == "01BX5ZZKBKACTAV9WEVGEMMV99"
            assert retrieved.label == "Test Sequence"
            assert len(retrieved.items) == 2
            assert not retrieved.closed
            print("✅ Sequence retrieval passed")

            # Test update sequence
            sequence.label = "Updated Sequence"
            sequence.closed = True
            update_result = store.update_sequence(sequence)
            assert update_result is True
            print("✅ Sequence update passed")

            # Test list sequences
            sequences = store.list_sequences("personal:test.space")
            assert len(sequences) >= 1
            print("✅ Sequence listing passed")

            # Test delete sequence
            delete_result = store.delete_sequence("01BX5ZZKBKACTAV9WEVGEMMV99")
            assert delete_result is True
            print("✅ Sequence deletion passed")

            # Verify deletion
            deleted = store.get_sequence("01BX5ZZKBKACTAV9WEVGEMMV99")
            assert deleted is None
            print("✅ Sequence deletion verification passed")

            store.commit_transaction(conn)
            print("✅ All sequence management tests passed!")

        except Exception:
            store.rollback_transaction(conn)
            raise
        finally:
            conn.close()


if __name__ == "__main__":
    print("🧪 Testing Epic 2.1 Issue 2.1.2: Simple Sequence Management")
    print("=" * 80)

    try:
        test_simple_sequence_management()
        print("\n🎉 Epic 2.1 Issue 2.1.2 basic functionality validated!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)        exit(1)
