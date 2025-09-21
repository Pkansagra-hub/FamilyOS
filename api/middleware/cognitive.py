"""
Cognitive Middleware for MemoryOS API
=====================================

Brain-inspired cognitive middleware that integrates with the MemoryOS production server.
Provides cognitive load adaptation, neural pathway routing, and feature flag evaluation
for all incoming HTTP requests.
"""

import time
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from feature_flags import (
    AdaptiveLearningEngine,
    BrainRegion,
    CognitiveFlagContext,
    CognitiveFlagManager,
    CognitiveTrace,
    CognitiveTraceEnricher,
    NeuralEvent,
    NeuralPathway,
    NeuralPathwayCorrelator,
    PerformanceMetrics,
    initialize_cognitive_manager,
)
from observability.context import trace_id_var
from observability.logging import get_json_logger

# from observability.metrics import increment_counter, record_histogram
from observability.trace import start_span

logger = get_json_logger(__name__)


class CognitiveMiddleware(BaseHTTPMiddleware):
    """
    Brain-inspired cognitive middleware for production MemoryOS API.

    Integrates cognitive feature flags, neural pathway correlation, adaptive learning,
    and cognitive trace enrichment into the HTTP request pipeline.
    """

    def __init__(self, app, cognitive_manager: Optional[CognitiveFlagManager] = None):
        super().__init__(app)
        self.cognitive_manager = cognitive_manager
        self.neural_correlator: Optional[NeuralPathwayCorrelator] = None
        self.trace_enricher: Optional[CognitiveTraceEnricher] = None
        self.learning_engine: Optional[AdaptiveLearningEngine] = None
        self.initialized = False

        # Middleware metrics
        self.request_count = 0
        self.cognitive_adaptations = 0
        self.neural_correlations = 0

    async def initialize(self):
        """Initialize cognitive components."""
        if self.initialized:
            return

        try:
            # Initialize cognitive manager if not provided
            if not self.cognitive_manager:
                self.cognitive_manager = await initialize_cognitive_manager()

            # Initialize brain-inspired components
            self.neural_correlator = NeuralPathwayCorrelator(self.cognitive_manager)
            self.trace_enricher = CognitiveTraceEnricher(self.cognitive_manager)
            self.learning_engine = AdaptiveLearningEngine(self.cognitive_manager)

            self.initialized = True
            logger.info("🧠 Cognitive middleware initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize cognitive middleware: {e}")
            # Continue without cognitive features
            self.initialized = False

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through cognitive middleware pipeline."""

        # Ensure initialization
        if not self.initialized:
            await self.initialize()

        # Start cognitive trace
        start_time = time.time()
        correlation_id = trace_id_var.get() or "unknown"

        # Create neural event for this request
        neural_event = None
        cognitive_trace = None
        cognitive_context = None

        try:
            # Create cognitive context from request
            cognitive_context = await self._create_cognitive_context(request)

            # Create neural event
            neural_event = self._create_neural_event(request, correlation_id)

            # Start cognitive trace
            cognitive_trace = await self._start_cognitive_trace(request, correlation_id)

            # Apply cognitive feature flags
            cognitive_flags = await self._get_cognitive_flags(
                cognitive_context, request
            )

            # Add cognitive headers to request
            await self._add_cognitive_headers(
                request, cognitive_context, cognitive_flags
            )

            # Record cognitive metrics
            self._record_cognitive_metrics(cognitive_context, "request_start")

            # Process request with cognitive awareness
            with start_span("cognitive_request_processing") as span:
                span.set_attributes(
                    {
                        "cognitive.load": cognitive_context.cognitive_load,
                        "cognitive.neural_pathway": (
                            neural_event.neural_pathway.value
                            if neural_event.neural_pathway
                            else None
                        ),
                        "cognitive.brain_region": (
                            neural_event.brain_region.value
                            if neural_event.brain_region
                            else None
                        ),
                        "cognitive.flags_enabled": len(
                            [f for f, enabled in cognitive_flags.items() if enabled]
                        ),
                    }
                )

                response = await call_next(request)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000

            # Create performance metrics
            performance_metrics = self._create_performance_metrics(
                cognitive_context, processing_time, response.status_code == 200
            )

            # Record performance for adaptive learning
            if self.learning_engine:
                await self.learning_engine.record_performance(performance_metrics)

            # Enrich cognitive trace
            if self.trace_enricher and cognitive_trace:
                await self.trace_enricher.finish_trace(
                    cognitive_trace.trace_id,
                    success=response.status_code < 400,
                    duration_ms=processing_time,
                )

            # Add cognitive response headers
            await self._add_cognitive_response_headers(
                response, cognitive_context, processing_time
            )

            # Record final metrics
            self._record_cognitive_metrics(cognitive_context, "request_complete")

            return response

        except Exception as e:
            logger.error(f"❌ Error in cognitive middleware: {e}")

            # Record error metrics
            if cognitive_context:
                self._record_cognitive_metrics(cognitive_context, "request_error")

            # Ensure we still return a response
            if "response" in locals():
                return response
            else:
                # If error occurred before calling next, we need to call it
                return await call_next(request)

    async def _create_cognitive_context(self, request: Request) -> CognitiveFlagContext:
        """Create cognitive context from HTTP request."""

        # Calculate cognitive load based on request characteristics
        cognitive_load = 0.3  # Base load

        # Increase load based on request complexity
        if request.method in ["POST", "PUT", "PATCH"]:
            cognitive_load += 0.2

        # Check for complex endpoints
        path = request.url.path
        if "/search" in path or "/query" in path:
            cognitive_load += 0.2
        if "/admin" in path:
            cognitive_load += 0.1
        if "/cognitive" in path:
            cognitive_load += 0.3

        # Headers that indicate high cognitive load
        if request.headers.get("Content-Type", "").startswith("application/json"):
            try:
                # Estimate JSON complexity (this is a simple heuristic)
                content_length = int(request.headers.get("Content-Length", "0"))
                if content_length > 1024:  # Large JSON payload
                    cognitive_load += 0.1
            except ValueError:
                pass

        # User-Agent complexity
        user_agent = request.headers.get("User-Agent", "")
        if "bot" in user_agent.lower() or "crawler" in user_agent.lower():
            cognitive_load += 0.1

        # Time-based load (higher during peak hours)
        current_hour = time.localtime().tm_hour
        if 9 <= current_hour <= 17:  # Business hours
            cognitive_load += 0.1

        # Clamp cognitive load
        cognitive_load = min(1.0, max(0.1, cognitive_load))

        return CognitiveFlagContext(
            cognitive_load=cognitive_load,
            working_memory_load=cognitive_load * 0.8,
            attention_queue_depth=int(cognitive_load * 200),
            hippocampus_activity=cognitive_load * 0.6,
            memory_pressure=cognitive_load * 0.7,
        )

    def _create_neural_event(
        self, request: Request, correlation_id: str
    ) -> NeuralEvent:
        """Create neural event from HTTP request."""

        # Determine neural pathway based on request type
        neural_pathway = NeuralPathway.EXECUTIVE_CONTROL  # Default
        brain_region = BrainRegion.PREFRONTAL_CORTEX  # Default

        path = request.url.path.lower()
        method = request.method

        # Map endpoints to neural pathways
        if "/memory" in path or "/recall" in path:
            neural_pathway = NeuralPathway.MEMORY_FORMATION
            brain_region = BrainRegion.HIPPOCAMPUS
        elif "/attention" in path or "/focus" in path:
            neural_pathway = NeuralPathway.ATTENTION_RELAY
            brain_region = BrainRegion.THALAMUS
        elif "/search" in path or "/query" in path:
            neural_pathway = NeuralPathway.RECALL_ASSEMBLY
            brain_region = BrainRegion.TEMPORAL_LOBE
        elif "/cognitive" in path or "/brain" in path:
            neural_pathway = NeuralPathway.EXECUTIVE_CONTROL
            brain_region = BrainRegion.PREFRONTAL_CORTEX
        elif "/sensory" in path or "/perception" in path:
            neural_pathway = NeuralPathway.SENSORY_PROCESSING
            brain_region = BrainRegion.PARIETAL_LOBE
        elif "/motor" in path or "/action" in path:
            neural_pathway = NeuralPathway.MOTOR_OUTPUT
            brain_region = BrainRegion.CEREBELLUM
        elif "/emotion" in path or "/affect" in path:
            neural_pathway = NeuralPathway.EMOTIONAL_REGULATION
            brain_region = BrainRegion.TEMPORAL_LOBE

        return NeuralEvent(
            event_id=correlation_id,
            event_type=f"http_{method.lower()}",
            source_component="api_middleware",
            neural_pathway=neural_pathway,
            brain_region=brain_region,
            hemisphere="bilateral",
            cognitive_load=0.5,  # Will be updated with actual context
            event_data={
                "method": method,
                "path": path,
                "user_agent": request.headers.get("User-Agent", ""),
                "content_type": request.headers.get("Content-Type", ""),
            },
        )

    async def _start_cognitive_trace(
        self, request: Request, correlation_id: str
    ) -> Optional[CognitiveTrace]:
        """Start cognitive trace for the request."""

        if not self.trace_enricher:
            return None

        try:
            trace = await self.trace_enricher.start_trace(
                trace_id=correlation_id,
                component_name="api_middleware",
                operation_name=f"{request.method}_{request.url.path.replace('/', '_')}",
            )
            return trace
        except Exception as e:
            logger.error(f"❌ Failed to start cognitive trace: {e}")
            return None

    async def _get_cognitive_flags(
        self, cognitive_context: CognitiveFlagContext, request: Request
    ) -> Dict[str, bool]:
        """Get cognitive feature flags for the request."""

        if not self.cognitive_manager:
            return {}

        try:
            # Get all cognitive flags
            flags = await self.cognitive_manager.get_all_cognitive_flags(
                cognitive_context
            )

            # Extract boolean flags
            cognitive_flags = {}
            for component, component_flags in flags.items():
                for flag_name, flag_config in component_flags.items():
                    if isinstance(flag_config, dict) and "enabled" in flag_config:
                        cognitive_flags[f"{component}.{flag_name}"] = flag_config[
                            "enabled"
                        ]
                    elif isinstance(flag_config, bool):
                        cognitive_flags[f"{component}.{flag_name}"] = flag_config

            return cognitive_flags

        except Exception as e:
            logger.error(f"❌ Failed to get cognitive flags: {e}")
            return {}

    async def _add_cognitive_headers(
        self,
        request: Request,
        cognitive_context: CognitiveFlagContext,
        cognitive_flags: Dict[str, bool],
    ):
        """Add cognitive context to request headers."""

        # Add cognitive context headers (for downstream services)
        if not hasattr(request, "state"):
            request.state = type("State", (), {})()

        request.state.cognitive_context = cognitive_context
        request.state.cognitive_flags = cognitive_flags
        request.state.cognitive_load = cognitive_context.cognitive_load

    def _create_performance_metrics(
        self,
        cognitive_context: CognitiveFlagContext,
        processing_time: float,
        success: bool,
    ) -> PerformanceMetrics:
        """Create performance metrics from request processing."""

        return PerformanceMetrics(
            cognitive_load=cognitive_context.cognitive_load,
            response_time_ms=processing_time,
            accuracy_score=1.0 if success else 0.0,
            component_name="api_middleware",
            operation_success=success,
            neural_pathway=NeuralPathway.EXECUTIVE_CONTROL,  # Default for middleware
            brain_region=BrainRegion.PREFRONTAL_CORTEX,
            pathway_efficiency=1.0 - cognitive_context.cognitive_load,
            user_satisfaction=1.0 if success and processing_time < 1000 else 0.5,
            system_efficiency=max(0.0, 1.0 - (processing_time / 5000.0)),  # 5s baseline
            cognitive_efficiency=1.0 - cognitive_context.cognitive_load,
        )

    async def _add_cognitive_response_headers(
        self,
        response: Response,
        cognitive_context: CognitiveFlagContext,
        processing_time: float,
    ):
        """Add cognitive information to response headers."""

        response.headers["X-Cognitive-Load"] = f"{cognitive_context.cognitive_load:.3f}"
        response.headers["X-Neural-Pathway"] = "executive_control"
        response.headers["X-Brain-Region"] = "prefrontal_cortex"
        response.headers["X-Cognitive-Processing-Time"] = f"{processing_time:.2f}ms"
        response.headers["X-Cognitive-Adaptation"] = "active"

    def _record_cognitive_metrics(
        self, cognitive_context: CognitiveFlagContext, stage: str
    ):
        """Record cognitive metrics for observability."""

        try:
            # TODO: Re-enable metrics when observability functions are available
            logger.info(
                f"Cognitive metrics recorded for stage: {stage}, "
                f"cognitive_load: {cognitive_context.cognitive_load}"
            )

            # Update internal metrics
            if stage == "request_start":
                self.request_count += 1
                if cognitive_context.cognitive_load > 0.7:
                    self.cognitive_adaptations += 1

        except Exception as e:
            logger.error(f"❌ Failed to record cognitive metrics: {e}")

    def get_middleware_stats(self) -> Dict[str, Any]:
        """Get middleware statistics."""

        return {
            "request_count": self.request_count,
            "cognitive_adaptations": self.cognitive_adaptations,
            "neural_correlations": self.neural_correlations,
            "initialized": self.initialized,
            "components": {
                "cognitive_manager": self.cognitive_manager is not None,
                "neural_correlator": self.neural_correlator is not None,
                "trace_enricher": self.trace_enricher is not None,
                "learning_engine": self.learning_engine is not None,
            },
        }


# Cognitive middleware instance for production use
cognitive_middleware = None


def get_cognitive_middleware() -> Optional[CognitiveMiddleware]:
    """Get the global cognitive middleware instance."""
    return cognitive_middleware


async def initialize_cognitive_middleware(
    app, cognitive_manager: Optional[CognitiveFlagManager] = None
):
    """Initialize cognitive middleware for the application."""
    global cognitive_middleware

    try:
        cognitive_middleware = CognitiveMiddleware(app, cognitive_manager)
        await cognitive_middleware.initialize()
        logger.info("🧠 Cognitive middleware ready for production")
        return cognitive_middleware
    except Exception as e:
        logger.error(f"❌ Failed to initialize cognitive middleware: {e}")
        return None
