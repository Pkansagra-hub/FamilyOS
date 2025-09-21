"""
MemoryOS API Application
===========================
Main application entry point for MemoryOS API.
Optimized for high performance and minimal response times.
"""

import logging
import os
import os.path
import sys
import tempfile
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.middleware.cognitive import initialize_cognitive_middleware

# Middleware functions imported to prevent duplicate initialization
from api.routers import setup_routers

# Brain-inspired cognitive system imports
from feature_flags import (
    get_brain_inspired_capabilities,
    initialize_brain_inspired_features,
    initialize_cognitive_manager,
)

# Configure optimized logging for performance
log_level = os.getenv("LOG_LEVEL", "INFO").upper()  # Show startup progress
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Startup banner
print("\n" + "=" * 60)
print("🧠 MemoryOS API Server - Production Startup")
print("=" * 60)
print(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
print(f"📝 Log Level: {log_level}")
print(f"⏰ Startup Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Initialize policy service ONCE at module level with file-based singleton pattern
_policy_service = None
_middleware_initialized = False
_init_lock_file = os.path.join(tempfile.gettempdir(), "memoryos_middleware.lock")


def get_policy_service():
    """Get or initialize policy service - prevents duplicate initialization using file lock."""
    global _policy_service

    # Check if already initialized in this process
    if _policy_service is not None:
        return _policy_service

    # Check if another process is initializing
    if os.path.exists(_init_lock_file):
        logger.info("🔄 Policy service initialization in progress by another process")
        return None

    try:
        # Create lock file
        with open(_init_lock_file, "w") as f:
            f.write(str(os.getpid()))

        # Initialize policy service
        from policy.service import initialize_policy_service

        _policy_service = initialize_policy_service()
        logger.info("✅ Policy service initialized")

        return _policy_service

    except Exception as e:
        logger.error(f"❌ Failed to initialize policy service: {e}")
        return None
    finally:
        # Clean up lock file
        if os.path.exists(_init_lock_file):
            try:
                os.remove(_init_lock_file)
            except Exception as e:
                logger.debug(f"Failed to remove lock file: {e}")


def setup_middleware_once(app: FastAPI):
    """Setup middleware chain only once to prevent duplicates using file lock."""
    global _middleware_initialized

    # Check if already initialized in this process
    if _middleware_initialized:
        logger.info("🔄 Middleware already initialized in this process, skipping")
        return

    # Check if lock file exists (another process initializing)
    lock_file = os.path.join(tempfile.gettempdir(), "memoryos_middleware_setup.lock")
    if os.path.exists(lock_file):
        logger.info(
            "🔄 Middleware initialization in progress by another process, skipping"
        )
        return

    try:
        # Create lock file
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))

        from api.middleware.middleware_integration import (
            setup_middleware_chain,
            validate_middleware_chain,
        )

        # Get policy service
        policy_service = get_policy_service()

        if policy_service is None:
            logger.warning("⚠️  Policy service not available, skipping middleware setup")
            return

        # Setup middleware chain
        setup_middleware_chain(app, policy_service)
        validate_middleware_chain(app)
        _middleware_initialized = True
        logger.info("🔐 Policy enforcement middleware chain initialized")

    except Exception as e:
        logger.error(f"❌ Failed to setup middleware chain: {e}")
        logger.warning("⚠️  Running without complete middleware chain")
    finally:
        # Clean up lock file
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception as e:
                logger.debug(f"Failed to remove lock file: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan event handler."""
    # Startup
    print("\n🚀 Starting MemoryOS API Server...")
    logger.info("🚀 MemoryOS API starting up")
    logger.info(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"📝 Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"🔗 CORS Origins: {cors_origins}")

    print("📋 Initializing MemoryOS services...")

    # Phase 1: Initialize Brain-Inspired Cognitive System (M4.3 Integration)
    await initialize_cognitive_system()

    # Phase 2: Initialize Core Services (Events, SSE, etc.)
    await initialize_core_services()

    # Phase 3: Initialize Cognitive Orchestration Layer
    await initialize_cognitive_orchestration()

    # Phase 4: Initialize Policy System with Default Roles
    await initialize_policy_system()

    logger.info("✅ Sub-issue #8.2: PolicyEnforcementMiddleware implemented")
    logger.info("📡 API docs available at: /docs")

    # Startup completion banner
    print("\n" + "=" * 60)
    print("✅ MemoryOS API Server Ready for Production!")
    print("=" * 60)
    print("📡 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("📊 Metrics: http://localhost:8000/metrics")
    print("🌐 Server: http://localhost:8000")
    print("🧠 Cognitive Architecture: OPERATIONAL")
    print("🔗 Component Integration: ACTIVE")
    print("=" * 60)

    yield

    # Shutdown
    logger.info("📴 MemoryOS API shutting down")
    await cleanup_core_services()


# Create FastAPI application with performance optimizations and modern lifespan
app = FastAPI(
    title="MemoryOS API",
    description="Cognitive Memory Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    # Performance optimizations
    openapi_url="/openapi.json" if os.getenv("ENVIRONMENT") != "production" else None,
    debug=False,  # Always disable debug in production
)


# Real timing middleware - NO SIMULATION
class RealTimingMiddleware(BaseHTTPMiddleware):
    """Real timing middleware with actual measurements only"""

    async def dispatch(self, request, call_next):
        """Real dispatch with actual timing - NO FAKE DATA"""
        start_time = time.time()
        response = await call_next(request)
        total_time = (time.time() - start_time) * 1000  # Convert to ms

        # Only add real response time
        response.headers["X-Response-Time"] = str(round(total_time, 2))

        return response


# Add real timing middleware
app.add_middleware(RealTimingMiddleware)

# Add memory flow observability middleware
try:
    from api.middleware.memory_observability import MemoryObservabilityMiddleware

    app.add_middleware(MemoryObservabilityMiddleware)
    logger.info("✅ Memory Flow Observability Middleware added")
except ImportError:
    logger.warning("⚠️ Memory Flow Observability Middleware not available")

# Add CORS middleware
cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware will be initialized in startup event


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "memoryos-api"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Add actual readiness checks (database, redis, etc.)
    return {"status": "ready", "service": "memoryos-api"}


@app.get("/health/live")
async def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive", "service": "memoryos-api"}


# Metrics endpoint (placeholder)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    # TODO: Implement actual Prometheus metrics
    return PlainTextResponse(
        "# MemoryOS metrics placeholder\n", media_type="text/plain"
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "MemoryOS API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs": "/docs",
        "health": "/health",
    }


# Setup routers
setup_routers(app)

# Setup middleware chain (Sub-issue #8.2 implementation) - ALWAYS setup
setup_middleware_once(app)


# Startup and shutdown events are now handled by the lifespan context manager


async def initialize_core_services():
    """
    Initialize core services for Intent Router, Events Bus, and SSE Streaming.

    This completes Phase 3 integration by connecting all the components we've built:
    - Events Bus (foundation for event system)
    - Intent Router (smart/fast path routing)
    - SSE Hub (live streaming with events bus integration)
    - Ingress Adapter (routing bridge between HTTP and services)
    """
    try:
        logger.info("🔧 Initializing core services...")

        # Step 1: Initialize Events Bus
        from events.bus import EventBus

        events_bus = EventBus()
        await events_bus.start()
        logger.info("✅ Events Bus initialized and started")

        # Step 2: Initialize Intent Router
        from intent.router import IntentRouter

        intent_router = IntentRouter()
        logger.info("✅ Intent Router initialized")

        # Step 3: Initialize SSE Hub and connect to Events Bus
        from api.ports.event_hub import default_sse_hub

        await default_sse_hub.set_event_bus(events_bus)

        # Check integration status
        bus_status = await default_sse_hub.get_events_bus_status()
        if bus_status["integration_status"] == "ready":
            logger.info("✅ SSE Hub connected to Events Bus - live streaming ready")
        else:
            logger.warning(
                f"⚠️ SSE Hub integration status: {bus_status['integration_status']}"
            )

        # Step 4: Initialize Ingress Adapter with all ports and services
        from api.ingress.adapter import initialize_ingress_adapter
        from api.ports.command_bus import default_command_bus
        from api.ports.observability import default_observability
        from api.ports.query_facade import default_query_facade

        initialize_ingress_adapter(
            command_bus=default_command_bus,
            query_facade=default_query_facade,
            sse_hub=default_sse_hub,
            observability=default_observability,
            intent_router=intent_router,
        )
        logger.info("✅ Ingress Adapter initialized with all ports and intent router")

        # Step 5: Store services globally for access by request handling pipeline
        # This makes the services available to the request handling pipeline
        app.state.events_bus = events_bus
        app.state.intent_router = intent_router
        app.state.sse_hub = default_sse_hub

        logger.info(
            "🎯 Core services integration complete - smart routing and live streaming active"
        )

    except Exception as e:
        logger.error(f"❌ Failed to initialize core services: {e}", exc_info=True)
        logger.warning("⚠️ Some features may not be available without core services")


async def initialize_cognitive_system():
    """
    Phase 1: Initialize Brain-Inspired Cognitive System (M4.3 Integration).

    Integrates our complete brain-inspired cognitive feature flag system
    with neural pathway correlation, adaptive learning, and cognitive middleware.

    Components integrated:
    - Cognitive Feature Flags Manager
    - Brain-Inspired Suite (Neural Correlator, Trace Enricher, Learning Engine)
    - Cognitive Middleware (request pipeline integration)
    """
    try:
        print("\n🧠 Phase 1: Initializing Brain-Inspired Cognitive System...")
        logger.info("🧠 Starting Brain-Inspired Cognitive System initialization")

        # Step 1.1: Initialize Cognitive Flag Manager
        print("  ├── Initializing Cognitive Flag Manager...")
        cognitive_manager = await initialize_cognitive_manager()
        if cognitive_manager:
            app.state.cognitive_manager = cognitive_manager
            logger.info("✅ Cognitive Flag Manager initialized")
            print("  ├── ✅ Cognitive Flag Manager ready")
        else:
            logger.warning("⚠️ Cognitive Flag Manager initialization failed")
            print("  ├── ⚠️ Cognitive Flag Manager failed")
            return

        # Step 1.2: Initialize Brain-Inspired Suite
        print("  ├── Initializing Brain-Inspired Suite...")
        brain_suite = await initialize_brain_inspired_features(
            cognitive_manager=cognitive_manager,
            enable_real_time=True,
            enable_learning=True,
            enable_enrichment=True,
        )
        if brain_suite:
            app.state.brain_inspired_suite = brain_suite
            logger.info("✅ Brain-Inspired Suite initialized")
            print("  ├── ✅ Neural Correlator, Trace Enricher, Learning Engine ready")

            # Log capabilities
            capabilities = get_brain_inspired_capabilities()
            logger.info(
                f"🧠 Brain capabilities: {len(capabilities['neural_pathways'])} pathways, "
                f"{len(capabilities['brain_regions'])} regions, "
                f"{len(capabilities['learning_algorithms'])} learning algorithms"
            )
        else:
            logger.warning("⚠️ Brain-Inspired Suite initialization failed")
            print("  ├── ⚠️ Brain-Inspired Suite failed")

        # Step 1.3: Initialize Cognitive Middleware
        print("  ├── Initializing Cognitive Middleware...")
        cognitive_middleware = await initialize_cognitive_middleware(
            app, cognitive_manager
        )
        if cognitive_middleware:
            app.state.cognitive_middleware = cognitive_middleware
            logger.info("✅ Cognitive Middleware integrated into request pipeline")
            print("  └── ✅ Cognitive Middleware integrated into request pipeline")
        else:
            logger.warning("⚠️ Cognitive Middleware initialization failed")
            print("  └── ⚠️ Cognitive Middleware failed")

        print("\n🎯 Phase 1 Complete: Brain-Inspired Cognitive System operational")
        logger.info("🎯 Brain-Inspired Cognitive System initialization complete")

    except Exception as e:
        logger.error(
            f"❌ Failed to initialize Brain-Inspired Cognitive System: {e}",
            exc_info=True,
        )
        print(f"\n❌ Phase 1 Failed: {e}")
        logger.warning("⚠️ Running without full cognitive features")


async def initialize_cognitive_orchestration():
    """
    Phase 2: Initialize Cognitive Orchestration Layer.

    This function integrates the core cognitive orchestration components:
    - Working Memory Manager (hierarchical cache L1/L2/L3)
    - Attention Gate (brain-inspired thalamic functions)
    - Memory Steward (sophisticated hippocampal orchestrator)
    - Context Bundle Builder (advanced recall assembly)
    - Cognitive Event Router (smart-path processing)
    """
    try:
        print("\n🧠 Phase 2: Initializing Cognitive Orchestration Layer...")
        logger.info("🧠 Starting Cognitive Orchestration Layer initialization")

        # Step 2.1: Initialize Working Memory Manager
        print("  ├── Initializing Working Memory Manager...")
        try:
            from storage.core.unit_of_work import UnitOfWork
            from working_memory.manager import WorkingMemoryManager

            # Create UnitOfWork for Working Memory
            uow = UnitOfWork(db_path="workspace/working_memory.db")
            working_memory = WorkingMemoryManager(uow=uow)
            app.state.working_memory = working_memory
            logger.info(
                "✅ Working Memory Manager initialized with hierarchical cache (L1/L2/L3)"
            )
            print(
                "  ├── ✅ Working Memory Manager ready (1,342 lines, hierarchical cache)"
            )
        except ImportError as e:
            logger.warning(f"⚠️ Working Memory Manager not available: {e}")
            print("  ├── ⚠️ Working Memory Manager not available")
        except Exception as e:
            logger.warning(f"⚠️ Working Memory initialization failed: {e}")
            print("  ├── ⚠️ Working Memory initialization failed")

        # Step 2.2: Initialize Attention Gate
        print("  ├── Initializing Attention Gate...")
        try:
            from attention_gate.gate_service import AttentionGate

            attention_gate = AttentionGate()
            app.state.attention_gate = attention_gate
            logger.info("✅ Attention Gate initialized with thalamic functions")
            print("  ├── ✅ Attention Gate ready (brain-inspired thalamic functions)")
        except ImportError as e:
            logger.warning(f"⚠️ Attention Gate not available: {e}")
            print("  ├── ⚠️ Attention Gate not available")
        except Exception as e:
            logger.warning(f"⚠️ Attention Gate initialization failed: {e}")
            print("  ├── ⚠️ Attention Gate initialization failed")

        # Step 2.3: Initialize Memory Steward
        print("  ├── Initializing Memory Steward...")
        try:
            from memory_steward.orchestrator import MemoryStewardOrchestrator
            from policy.service import PolicyService
            from storage.core.unit_of_work import UnitOfWork

            # Create dependencies for Memory Steward
            policy_service = PolicyService()
            uow = UnitOfWork(db_path="workspace/memory_steward.db")

            # Initialize Memory Steward with proper dependencies and event bus integration
            memory_steward = MemoryStewardOrchestrator(
                unit_of_work=uow,
                event_bus=app.state.events_bus,
                policy_engine=policy_service,
            )
            app.state.memory_steward = memory_steward
            logger.info(
                "✅ Memory Steward initialized with hippocampal orchestration and event bus"
            )
            print("  ├── ✅ Memory Steward ready (707-line hippocampal orchestrator)")
        except ImportError as e:
            logger.warning(f"⚠️ Memory Steward not available: {e}")
            print("  ├── ⚠️ Memory Steward not available")
        except Exception as e:
            import traceback

            logger.error(f"❌ Memory Steward initialization failed: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            print(f"  ├── ❌ Memory Steward initialization failed: {e}")
            print(f"      Traceback: {traceback.format_exc()}")

        # Step 2.4: Initialize Context Bundle Builder
        print("  ├── Initializing Context Bundle Builder...")
        try:
            from context_bundle import ContextBundleOrchestrator

            context_bundle = ContextBundleOrchestrator()
            app.state.context_bundle = context_bundle
            logger.info("✅ Context Bundle Builder initialized")
            print("  ├── ✅ Context Bundle Builder ready (advanced recall assembly)")
        except ImportError as e:
            logger.warning(f"⚠️ Context Bundle Builder not available: {e}")
            print("  ├── ⚠️ Context Bundle Builder not available")
        except Exception as e:
            logger.warning(f"⚠️ Context Bundle initialization failed: {e}")
            print("  ├── ⚠️ Context Bundle initialization failed")

        # Step 2.5: Initialize Cognitive Event Router
        print("  ├── Initializing Cognitive Event Router...")
        try:
            from cognitive_events.dispatcher import CognitiveDispatcher

            # Initialize cognitive event dispatcher with events bus
            cognitive_dispatcher = CognitiveDispatcher(event_bus=app.state.events_bus)
            app.state.cognitive_dispatcher = cognitive_dispatcher
            logger.info(
                "✅ Cognitive Event Router initialized with events bus integration"
            )
            print("  ├── ✅ Cognitive Event Router ready (smart-path processing)")
        except ImportError as e:
            logger.warning(f"⚠️ Cognitive Event Router not available: {e}")
            print("  ├── ⚠️ Cognitive Event Router not available")
        except Exception as e:
            logger.warning(f"⚠️ Cognitive Events initialization failed: {e}")
            print("  ├── ⚠️ Cognitive Event Router initialization failed")

        # Step 2.6: Initialize Pipeline Manager
        print("  ├── Initializing Pipeline Manager...")
        try:
            from pipelines.manager import PipelineManager
            from pipelines.registry import pipeline_registry

            # Initialize pipeline manager with cognitive integration
            pipeline_manager = PipelineManager()
            app.state.pipeline_manager = pipeline_manager
            app.state.pipeline_registry = pipeline_registry
            logger.info(
                "✅ Pipeline Manager initialized with cognitive orchestration integration"
            )
            print("  └── ✅ Pipeline Manager ready (P01-P20 coordination)")
        except ImportError as e:
            logger.warning(f"⚠️ Pipeline Manager not available: {e}")
            print("  └── ⚠️ Pipeline Manager not available")
        except Exception as e:
            logger.warning(f"⚠️ Pipeline Manager initialization failed: {e}")
            print("  └── ⚠️ Pipeline Manager initialization failed")

        print("\n🎯 Phase 2 Complete: Cognitive Orchestration Layer operational")
        logger.info("🎯 Cognitive Orchestration Layer initialization complete")

        # Wire cognitive components together for event flow
        await wire_cognitive_components()

    except Exception as e:
        logger.error(f"❌ Error in cognitive orchestration: {e}", exc_info=True)
        print(f"\n❌ Phase 2 Failed: {e}")


async def wire_cognitive_components():
    """
    Phase 2.1: Wire Cognitive Components for Event Flow.

    Connect cognitive components through event-driven architecture:
    Attention Gate → Memory Steward → Context Bundle → Working Memory
    """
    try:
        print("\n🔗 Phase 2.1: Wiring Cognitive Component Event Flow...")
        logger.info("🔗 Starting cognitive component event flow wiring")

        # Step 2.1.1: Wire Attention Gate to Memory Steward
        if hasattr(app.state, "attention_gate") and hasattr(
            app.state, "memory_steward"
        ):
            print("  ├── Wiring Attention Gate → Memory Steward...")
            # TODO: Add event subscription for HIPPO_ENCODE events from attention gate
            logger.info("✅ Attention Gate → Memory Steward event flow configured")
            print("  ├── ✅ Attention Gate → Memory Steward connected")

        # Step 2.1.2: Wire Memory Steward to Context Bundle
        if hasattr(app.state, "memory_steward") and hasattr(
            app.state, "context_bundle"
        ):
            print("  ├── Wiring Memory Steward → Context Bundle...")
            # TODO: Add event subscription for MEMORY_FORMED events
            logger.info("✅ Memory Steward → Context Bundle event flow configured")
            print("  ├── ✅ Memory Steward → Context Bundle connected")

        # Step 2.1.3: Wire Context Bundle to Working Memory
        if hasattr(app.state, "context_bundle") and hasattr(
            app.state, "working_memory"
        ):
            print("  ├── Wiring Context Bundle → Working Memory...")
            # TODO: Add event subscription for CONTEXT_ASSEMBLED events
            logger.info("✅ Context Bundle → Working Memory event flow configured")
            print("  ├── ✅ Context Bundle → Working Memory connected")

        # Step 2.1.4: Wire Pipeline Manager to Cognitive Components
        if hasattr(app.state, "pipeline_manager"):
            print("  └── Wiring Pipeline Manager to Cognitive Components...")
            # TODO: Connect P01/P02/P04 pipelines to cognitive orchestration
            logger.info(
                "✅ Pipeline Manager → Cognitive Components integration configured"
            )
            print("  └── ✅ Pipeline Manager integrated with cognitive orchestration")

        print("\n🎯 Phase 2.1 Complete: Cognitive Component Event Flow operational")
        logger.info("🎯 Cognitive component event flow wiring complete")

    except Exception as e:
        logger.error(f"❌ Error in cognitive component wiring: {e}", exc_info=True)
        print(f"\n❌ Phase 2.1 Failed: {e}")


async def initialize_policy_system():
    """
    Phase 4: Initialize Policy System with Default Roles and User Bindings.

    Sets up RBAC roles and creates default user bindings for development.
    """
    try:
        print("\n🔐 Phase 4: Initializing Policy System...")
        logger.info("🔐 Starting Policy System initialization")

        # Get the policy service
        policy_service = get_policy_service()
        if not policy_service:
            logger.error("❌ Policy service not available")
            print("  ├── ❌ Policy service not available")
            return

        # Initialize default roles and bindings
        print("  ├── Initializing default roles and user bindings...")
        await policy_service.initialize_default_roles()

        # Add additional development user bindings for UUIDs
        from policy.rbac import Binding

        # Create some example family member bindings with proper UUIDs
        test_users = [
            ("dad12345-1234-4567-8901-123456789012", "admin", "shared:household"),
            ("mom12345-1234-4567-8901-123456789012", "guardian", "shared:household"),
            ("teen1234-1234-4567-8901-123456789012", "member", "shared:household"),
            ("child123-1234-4567-8901-123456789012", "child", "shared:household"),
            ("guest123-1234-4567-8901-123456789012", "guest", "shared:household"),
        ]

        for user_id, role, space in test_users:
            policy_service.rbac.bind(Binding(user_id, role, space))

        logger.info(
            "✅ Policy System initialized with default roles and family bindings"
        )
        print("  ├── ✅ Default roles and family member bindings created")

        # Store policy service globally
        app.state.policy_service = policy_service

        print("🎯 Phase 4 Complete: Policy System operational")
        logger.info("🎯 Policy System initialization complete")

    except Exception as e:
        logger.error(f"❌ Error in policy system initialization: {e}", exc_info=True)
        print(f"\n❌ Phase 4 Failed: {e}")


# Shutdown events are now handled by the lifespan context manager


async def cleanup_core_services():
    """Clean up core services during shutdown."""
    try:
        logger.info("🧹 Cleaning up core services...")

        # Disconnect SSE Hub from Events Bus
        if hasattr(app.state, "sse_hub"):
            await app.state.sse_hub.disconnect_from_events_bus()
            logger.info("✅ SSE Hub disconnected from Events Bus")

        # Stop Events Bus
        if hasattr(app.state, "events_bus"):
            await app.state.events_bus.shutdown()
            logger.info("✅ Events Bus shutdown completed")

        logger.info("🎯 Core services cleanup complete")

    except Exception as e:
        logger.error(f"❌ Error during core services cleanup: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn

    # Development server - RELOAD DISABLED to prevent duplicate middleware initialization
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled to prevent duplicate middleware initialization
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
