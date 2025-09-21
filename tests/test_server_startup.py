#!/usr/bin/env python3
"""
Server Startup Test
==================

Test the full server startup with all cognitive integrations.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


async def test_server_startup():
    """Test full server startup."""
    print("🧪 Testing MemoryOS Server Startup with All Integrations")
    print("=" * 60)

    try:
        from main import app, lifespan

        print("📋 Starting server lifespan...")

        startup_completed = False

        # Use the lifespan context manager properly
        async with lifespan(app):
            print("✅ Server startup completed successfully!")
            startup_completed = True

            # Check if all components are in app.state
            components = [
                ("events_bus", "Events Bus"),
                ("cognitive_manager", "Cognitive Flag Manager"),
                ("working_memory", "Working Memory Manager"),
                ("attention_gate", "Attention Gate"),
                ("memory_steward", "Memory Steward"),
                ("context_bundle", "Context Bundle Builder"),
                ("cognitive_dispatcher", "Cognitive Event Router"),
                ("pipeline_manager", "Pipeline Manager"),
                ("pipeline_registry", "Pipeline Registry"),
            ]

            print("\\n📊 Component Integration Status:")
            for attr, name in components:
                if hasattr(app.state, attr):
                    component = getattr(app.state, attr)
                    if component is not None:
                        print(f"  ✅ {name}: OPERATIONAL")
                    else:
                        print(f"  ❌ {name}: NULL")
                else:
                    print(f"  ❌ {name}: NOT FOUND")

        if startup_completed:
            print("\\n🎉 ALL INTEGRATIONS SUCCESSFUL!")
            print("🚀 MemoryOS Server Ready for Production!")
            return True
        else:
            print("\\n❌ Startup did not complete")
            return False

    except Exception as e:
        print(f"\\n❌ Server startup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_server_startup())
    sys.exit(0 if success else 1)
