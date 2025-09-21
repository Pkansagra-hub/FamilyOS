"""
Memory-Centric ASGI Middleware for Family AI

Automatic envelope tracking and observability for all FastAPI requests.
Provides seamless integration with Memory Backbone architecture.
"""

import time
import uuid
from typing import Callable, Dict, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .envelope import (
    MemoryEnvelope, 
    MemoryOperation, 
    MemoryPlane, 
    CognitiveStage,
    EnvelopeTracker,
    MemoryTransformation
)
from .memory_trace import MemoryTracer
from .metrics import MetricsCollector


class MemoryTracingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for automatic envelope tracking and observability"""
    
    def __init__(
        self, 
        app: Any,
        tracer: MemoryTracer,
        metrics_collector: MetricsCollector,
        envelope_tracker: EnvelopeTracker
    ):
        super().__init__(app)
        self.tracer = tracer
        self.metrics_collector = metrics_collector
        self.envelope_tracker = envelope_tracker
        
        # Memory plane detection patterns
        self.plane_patterns = {
            MemoryPlane.AGENT: ["/v1/agents", "/v1/tools", "/v1/memory"],
            MemoryPlane.TOOL: ["/v1/connectors", "/v1/integrations", "/v1/apps"],
            MemoryPlane.CONTROL: ["/v1/admin", "/v1/control", "/v1/system"]
        }
        
        # Memory operations mapping
        self.operation_patterns = {
            "POST": MemoryOperation.FORMATION,
            "GET": MemoryOperation.RECALL,
            "PUT": MemoryOperation.CONSOLIDATION,
            "DELETE": MemoryOperation.FORGET,
            "PATCH": MemoryOperation.UPDATE
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with envelope tracking and observability"""
        
        # Create memory envelope for request
        envelope = self._create_request_envelope(request)
        
        # Start envelope tracking
        self.envelope_tracker.start_envelope(envelope)
        
        # Record transformation: HTTP Request → Memory Processing
        self.envelope_tracker.record_transformation(
            envelope.envelope_id,
            transformation_type="http_ingress",
            stage_from="external",
            stage_to=envelope.current_stage.value,
            metadata={
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client_ip": getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
            }
        )
        
        # Start distributed trace span
        with self.tracer.trace_memory_operation(
            operation=envelope.memory_operation,
            plane=envelope.memory_plane,
            envelope_id=envelope.envelope_id,
            metadata={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.user_agent": request.headers.get("user-agent", ""),
                "memory.envelope_id": envelope.envelope_id,
                "memory.operation": envelope.memory_operation.value,
                "memory.plane": envelope.memory_plane.value
            }
        ) as span:
            
            # Add envelope context to request state
            request.state.memory_envelope = envelope
            request.state.memory_span = span
            
            # Record metrics start
            start_time = time.time()
            
            try:
                # Process request through application
                response = await call_next(request)
                
                # Record successful processing
                processing_time = time.time() - start_time
                self._record_success_metrics(envelope, response, processing_time)
                
                # Update envelope with response
                self._update_envelope_response(envelope, response)
                
                # Record transformation: Memory Processing → HTTP Response
                self.envelope_tracker.record_transformation(
                    envelope.envelope_id,
                    transformation_type="http_egress",
                    stage_from=envelope.current_stage.value,
                    stage_to="external",
                    metadata={
                        "status_code": response.status_code,
                        "response_headers": dict(response.headers),
                        "processing_time_ms": processing_time * 1000
                    }
                )
                
                # Add envelope ID to response headers for traceability
                response.headers["X-Memory-Envelope-ID"] = envelope.envelope_id
                response.headers["X-Memory-Operation"] = envelope.memory_operation.value
                response.headers["X-Memory-Plane"] = envelope.memory_plane.value
                
                # Complete envelope tracking
                self.envelope_tracker.complete_envelope(envelope.envelope_id)
                
                return response
                
            except Exception as e:
                # Record error metrics and envelope state
                processing_time = time.time() - start_time
                self._record_error_metrics(envelope, e, processing_time)
                
                # Record error transformation
                self.envelope_tracker.record_transformation(
                    envelope.envelope_id,
                    transformation_type="error_handling",
                    stage_from=envelope.current_stage.value,
                    stage_to="error",
                    metadata={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "processing_time_ms": processing_time * 1000
                    }
                )
                
                # Update span with error information
                span.set_status("ERROR", str(e))
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                # Complete envelope in error state
                self.envelope_tracker.complete_envelope(envelope.envelope_id, error=str(e))
                
                raise
    
    def _create_request_envelope(self, request: Request) -> MemoryEnvelope:
        """Create memory envelope for incoming HTTP request"""
        
        # Detect memory plane from URL pattern
        memory_plane = self._detect_memory_plane(request.url.path)
        
        # Determine memory operation from HTTP method
        memory_operation = self.operation_patterns.get(
            request.method, 
            MemoryOperation.RECALL
        )
        
        # Determine initial cognitive stage
        cognitive_stage = self._determine_cognitive_stage(memory_plane, memory_operation)
        
        # Extract user/family context
        user_id = self._extract_user_context(request)
        family_context = self._extract_family_context(request)
        
        return MemoryEnvelope(
            envelope_id=str(uuid.uuid4()),
            memory_operation=memory_operation,
            memory_plane=memory_plane,
            current_stage=cognitive_stage,
            user_id=user_id,
            family_context=family_context,
            metadata={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_query": str(request.url.query) if request.url.query else None,
                "content_type": request.headers.get("content-type"),
                "user_agent": request.headers.get("user-agent"),
                "origin": request.headers.get("origin"),
                "referer": request.headers.get("referer")
            }
        )
    
    def _detect_memory_plane(self, path: str) -> MemoryPlane:
        """Detect memory plane from URL path"""
        for plane, patterns in self.plane_patterns.items():
            if any(pattern in path for pattern in patterns):
                return plane
        return MemoryPlane.AGENT  # Default to agent plane
    
    def _determine_cognitive_stage(
        self, 
        plane: MemoryPlane, 
        operation: MemoryOperation
    ) -> CognitiveStage:
        """Determine initial cognitive stage based on plane and operation"""
        
        if plane == MemoryPlane.AGENT:
            if operation in [MemoryOperation.FORMATION, MemoryOperation.UPDATE]:
                return CognitiveStage.ATTENTION_GATE
            else:
                return CognitiveStage.MEMORY_RECALL
        elif plane == MemoryPlane.TOOL:
            return CognitiveStage.EXTERNAL_INTEGRATION
        else:  # CONTROL plane
            return CognitiveStage.SYSTEM_CONTROL
    
    def _extract_user_context(self, request: Request) -> Optional[str]:
        """Extract user ID from request headers or authentication"""
        # Check for user ID in headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
            
        # Check for authentication token (placeholder for JWT/OAuth)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # In real implementation, decode JWT token to extract user ID
            return "user_from_token"  # Placeholder
            
        # Check for user ID in query parameters
        return request.query_params.get("user_id")
    
    def _extract_family_context(self, request: Request) -> Dict[str, Any]:
        """Extract family context from request"""
        family_context = {}
        
        # Extract family ID
        family_id = request.headers.get("X-Family-ID")
        if family_id:
            family_context["family_id"] = family_id
            
        # Extract device ID
        device_id = request.headers.get("X-Device-ID")
        if device_id:
            family_context["device_id"] = device_id
            
        # Extract space context
        space_id = request.headers.get("X-Space-ID")
        if space_id:
            family_context["space_id"] = space_id
            
        return family_context
    
    def _update_envelope_response(self, envelope: MemoryEnvelope, response: Response):
        """Update envelope with response information"""
        envelope.metadata.update({
            "response_status": response.status_code,
            "response_content_type": response.headers.get("content-type"),
            "response_size": response.headers.get("content-length")
        })
    
    def _record_success_metrics(
        self, 
        envelope: MemoryEnvelope, 
        response: Response, 
        processing_time: float
    ):
        """Record success metrics for envelope processing"""
        
        # Record HTTP metrics
        self.metrics_collector.record_http_request(
            method=envelope.metadata.get("http_method", "UNKNOWN"),
            plane=envelope.memory_plane.value,
            status_code=response.status_code,
            duration=processing_time
        )
        
        # Record memory operation metrics
        self.metrics_collector.record_memory_operation(
            operation=envelope.memory_operation.value,
            plane=envelope.memory_plane.value,
            stage=envelope.current_stage.value,
            duration=processing_time,
            success=True
        )
        
        # Record envelope metrics
        self.metrics_collector.record_envelope_metrics(envelope)
    
    def _record_error_metrics(
        self, 
        envelope: MemoryEnvelope, 
        error: Exception, 
        processing_time: float
    ):
        """Record error metrics for envelope processing"""
        
        # Record HTTP error metrics
        self.metrics_collector.record_http_request(
            method=envelope.metadata.get("http_method", "UNKNOWN"),
            plane=envelope.memory_plane.value,
            status_code=500,  # Internal server error
            duration=processing_time
        )
        
        # Record memory operation error
        self.metrics_collector.record_memory_operation(
            operation=envelope.memory_operation.value,
            plane=envelope.memory_plane.value,
            stage=envelope.current_stage.value,
            duration=processing_time,
            success=False
        )
        
        # Record error-specific metrics
        error_type = type(error).__name__
        self.metrics_collector.record_error(
            error_type=error_type,
            plane=envelope.memory_plane.value,
            operation=envelope.memory_operation.value
        )


class MemoryContextMiddleware(BaseHTTPMiddleware):
    """Middleware for injecting memory context into request processing"""
    
    def __init__(self, app: Any):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Inject memory context into request state"""
        
        # Initialize memory context in request state
        if not hasattr(request.state, 'memory_context'):
            request.state.memory_context = {
                "correlation_id": str(uuid.uuid4()),
                "start_time": time.time(),
                "memory_operations": [],
                "cognitive_journey": []
            }
        
        response = await call_next(request)
        
        # Add correlation headers to response
        response.headers["X-Memory-Correlation-ID"] = request.state.memory_context["correlation_id"]
        
        return response


def create_memory_middleware(
    tracer: MemoryTracer,
    metrics_collector: MetricsCollector,
    envelope_tracker: EnvelopeTracker
) -> MemoryTracingMiddleware:
    """Factory function to create memory tracing middleware"""
    return MemoryTracingMiddleware(
        app=None,  # Will be set by FastAPI
        tracer=tracer,
        metrics_collector=metrics_collector,
        envelope_tracker=envelope_tracker
    )


def add_memory_observability(app, observability_components: Dict[str, Any]):
    """Add memory observability middleware to FastAPI application"""
    
    # Extract components
    tracer = observability_components.get("tracer")
    metrics_collector = observability_components.get("metrics_collector")
    envelope_tracker = observability_components.get("envelope_tracker")
    
    if not all([tracer, metrics_collector, envelope_tracker]):
        raise ValueError("Missing required observability components")
    
    # Add memory context middleware first
    app.add_middleware(MemoryContextMiddleware)
    
    # Add memory tracing middleware
    app.add_middleware(
        MemoryTracingMiddleware,
        tracer=tracer,
        metrics_collector=metrics_collector,
        envelope_tracker=envelope_tracker
    )
    
    return app