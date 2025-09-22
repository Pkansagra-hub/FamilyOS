"""
Memory-Centric Distributed Tracing
==================================

OpenTelemetry-based tracing specifically designed for Memory Backbone architecture.
Tracks cognitive processing, memory operations, and family intelligence coordination.

Key Features:
- Cognitive Span: Specialized spans for brain-inspired processing
- Memory Operation Tracing: Submit, recall, consolidate, sync operations
- Family Intelligence Correlation: Track family context across devices
- Pipeline Instrumentation: Detailed tracing for all 20 pipelines
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, ContextManager, Dict, List, Optional

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from .envelope import MemoryEnvelope, envelope_tracker


class CognitiveSpan:
    """
    Specialized span for cognitive processing in Memory Backbone
    Provides brain-inspired context and memory operation tracking
    """

    def __init__(
        self,
        span: trace.Span,
        cognitive_stage: str,
        memory_operation: str,
        envelope_id: str,
    ):
        self.span = span
        self.cognitive_stage = cognitive_stage
        self.memory_operation = memory_operation
        self.envelope_id = envelope_id
        self.start_time = time.time()

        # Set cognitive context attributes
        self.span.set_attribute("memory.cognitive_stage", cognitive_stage)
        self.span.set_attribute("memory.operation", memory_operation)
        self.span.set_attribute("memory.envelope_id", envelope_id)

    def set_memory_context(
        self, spaces: List[str], family_context: Dict[str, Any]
    ) -> None:
        """Set memory space and family context"""
        self.span.set_attribute("memory.spaces", ",".join(spaces))
        for key, value in family_context.items():
            self.span.set_attribute(f"family.{key}", str(value))

    def set_cognitive_load(
        self, working_memory_usage: float, attention_score: float
    ) -> None:
        """Set cognitive processing metrics"""
        self.span.set_attribute("cognitive.working_memory_usage", working_memory_usage)
        self.span.set_attribute("cognitive.attention_score", attention_score)

    def set_emotional_context(self, emotional_state: Dict[str, Any]) -> None:
        """Set emotional intelligence context"""
        for key, value in emotional_state.items():
            self.span.set_attribute(f"emotion.{key}", str(value))

    def set_device_context(
        self, device_id: str, is_family_device: bool = False
    ) -> None:
        """Set device and family coordination context"""
        self.span.set_attribute("device.id", device_id)
        self.span.set_attribute("device.is_family_device", is_family_device)

    def record_memory_transformation(
        self, input_size: int, output_size: int, operation_type: str
    ) -> None:
        """Record memory transformation metrics"""
        self.span.set_attribute("memory.input_size", input_size)
        self.span.set_attribute("memory.output_size", output_size)
        self.span.set_attribute("memory.transformation_type", operation_type)

        # Track transformation in envelope
        envelope_tracker.track_transformation(
            self.envelope_id,
            self.cognitive_stage,
            operation_type,
            input_size,
            output_size,
            {"span_id": self.span.get_span_context().span_id},
        )

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to span with optional attributes"""
        self.span.add_event(name, attributes or {})

    def set_error(self, error: str) -> None:
        """Mark span with error"""
        self.span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        self.span.set_attribute("error", True)
        self.span.set_attribute("error.message", error)

    def finish(self) -> None:
        """Complete the span"""
        duration = time.time() - self.start_time
        self.span.set_attribute("duration", duration)
        self.span.end()


class MemoryTracer:
    """
    Memory-Centric Distributed Tracer
    Provides specialized tracing for Family AI Memory Backbone
    """

    def __init__(
        self,
        service_name: str = "family-ai-memory",
        service_version: str = "1.0.0",
        jaeger_endpoint: str = "http://localhost:14268/api/traces",
        otlp_endpoint: str = "http://localhost:4317",
    ):
        """Initialize MemoryTracer with OpenTelemetry setup"""
        self.logger = logging.getLogger(__name__)

        self.service_name = service_name
        self.service_version = service_version

        # Setup resource
        resource = Resource.create(
            {
                SERVICE_NAME: service_name,
                SERVICE_VERSION: service_version,
                "memory.architecture": "memory_backbone",
                "family.ai": "true",
            }
        )

        # Setup tracer provider
        trace.set_tracer_provider(TracerProvider(resource=resource))
        self.tracer = trace.get_tracer(__name__)

        # Setup exporters
        self._setup_exporters(jaeger_endpoint, otlp_endpoint)

        # Instrument FastAPI and requests
        try:
            FastAPIInstrumentor().instrument()
            RequestsInstrumentor().instrument()
        except Exception as e:
            self.logger.warning(f"Failed to initialize instrumentation: {e}")
            # Continue without instrumentation in development mode

    def _setup_exporters(self, jaeger_endpoint: str, otlp_endpoint: str) -> None:
        """Setup multiple trace exporters for comprehensive observability"""
        tracer_provider = trace.get_tracer_provider()

        # Console exporter for development
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(console_processor)

        # Jaeger exporter for distributed tracing
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            jaeger_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(jaeger_processor)
        except Exception as e:
            print(f"Failed to setup Jaeger exporter: {e}")

        # OTLP exporter for cloud observability
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            otlp_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(otlp_processor)
        except Exception as e:
            print(f"Failed to setup OTLP exporter: {e}")

    @contextmanager
    def start_cognitive_span(
        self, cognitive_stage: str, memory_operation: str, envelope: MemoryEnvelope
    ) -> ContextManager[CognitiveSpan]:
        """Start a cognitive processing span"""
        span_name = f"memory.{cognitive_stage}.{memory_operation}"

        with self.tracer.start_as_current_span(span_name) as span:
            cognitive_span = CognitiveSpan(
                span=span,
                cognitive_stage=cognitive_stage,
                memory_operation=memory_operation,
                envelope_id=envelope.envelope_id,
            )

            # Set envelope context
            cognitive_span.span.set_attribute(
                "envelope.cognitive_trace_id", envelope.cognitive_trace_id
            )
            cognitive_span.span.set_attribute(
                "envelope.api_plane",
                envelope.api_plane.value if envelope.api_plane else "unknown",
            )
            cognitive_span.span.set_attribute(
                "envelope.user_id", envelope.user_id or "unknown"
            )
            cognitive_span.span.set_attribute(
                "envelope.device_id", envelope.device_id or "unknown"
            )

            # Set memory context if available
            if envelope.memory_spaces:
                cognitive_span.set_memory_context(
                    envelope.memory_spaces, envelope.family_context
                )

            # Set emotional context if available
            if envelope.emotional_context:
                cognitive_span.set_emotional_context(envelope.emotional_context)

            yield cognitive_span

    @contextmanager
    def start_pipeline_span(
        self, pipeline_name: str, envelope: MemoryEnvelope
    ) -> ContextManager[CognitiveSpan]:
        """Start a pipeline processing span"""
        return self.start_cognitive_span(
            cognitive_stage=f"pipeline.{pipeline_name}",
            memory_operation=envelope.memory_operation.value,
            envelope=envelope,
        )

    @contextmanager
    def start_memory_operation_span(
        self, operation: str, envelope: MemoryEnvelope
    ) -> ContextManager[CognitiveSpan]:
        """Start a memory operation span"""
        return self.start_cognitive_span(
            cognitive_stage="memory_engine",
            memory_operation=operation,
            envelope=envelope,
        )

    @contextmanager
    def start_family_sync_span(
        self, target_device: str, envelope: MemoryEnvelope
    ) -> ContextManager[CognitiveSpan]:
        """Start a family synchronization span"""
        with self.start_cognitive_span(
            cognitive_stage="family_sync", memory_operation="sync", envelope=envelope
        ) as span:
            span.span.set_attribute("sync.target_device", target_device)
            span.span.set_attribute("sync.is_e2ee", True)
            yield span

    def trace_envelope_journey(self, envelope: MemoryEnvelope) -> Dict[str, Any]:
        """Generate complete trace summary for envelope journey"""
        return {
            "envelope_id": envelope.envelope_id,
            "cognitive_trace_id": envelope.cognitive_trace_id,
            "total_spans": len(envelope.transformations),
            "journey_duration": envelope.processing_duration,
            "stages": [t.stage for t in envelope.transformations],
            "memory_spaces": envelope.memory_spaces,
            "family_context": envelope.family_context,
            "is_complete": envelope.is_complete,
            "error_state": envelope.error_state,
        }


# Global memory tracer instance
memory_tracer = MemoryTracer()
# Global memory tracer instance
memory_tracer = MemoryTracer()
