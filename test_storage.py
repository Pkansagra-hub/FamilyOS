#!/usr/bin/env python3
"""
Quick storage test script to verify storage functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage.core.unit_of_work import UnitOfWork
from storage.stores.memory.episodic_store import EpisodicStore
import uuid
from datetime import datetime

def test_storage():
    """Test storage functionality directly"""
    print("🧪 Testing FamilyOS Storage System...")
    
    try:
        # Initialize UnitOfWork
        print("  ├── Initializing UnitOfWork...")
        uow = UnitOfWork(db_path="test_memory.db")
        
        # Initialize EpisodicStore 
        print("  ├── Initializing EpisodicStore...")
        episodic_store = EpisodicStore(uow)
        
        # Register store
        uow.register_store(episodic_store)
        print("  ├── Store registered successfully")
        
        # Test writing
        print("  ├── Testing write operations...")
        with uow:
            event_id = episodic_store.append_event(
                space_id="shared:household",
                content="Storage test from Copilot - testing write functionality",
                event_type="test",
                context={
                    "test_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "source": "copilot_storage_test"
                }
            )
            print(f"  ├── ✅ Event written with ID: {event_id}")
        
        # Test reading
        print("  ├── Testing read operations...")
        with uow:
            recent_events = episodic_store.get_recent_events(
                space_id="shared:household",
                limit=5
            )
            print(f"  ├── ✅ Retrieved {len(recent_events)} recent events")
            
            if recent_events:
                latest_event = recent_events[0]
                print(f"  ├── Latest event: {latest_event.get('content', 'N/A')[:50]}...")
        
        print("  └── ✅ Storage system is working correctly!")
        return True
        
    except Exception as e:
        print(f"  └── ❌ Storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_storage()
    sys.exit(0 if success else 1)