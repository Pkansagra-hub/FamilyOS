"""
Observability Tracing
====================

Lightweight tracing utilities for Family AI Memory Backbone.
Provides span context and distributed tracing helpers.
"""

import time
import uuid
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .context import trace_id_var, span_id_var, set_trace_id, set_span_id

class Span:
    """Simple span implementation for tracing"""
    
    def __init__(self, name: str, trace_id: Optional[str] = None, parent_span_id: Optional[str] = None):
        self.span_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.name = name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        
    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span"""
        self.attributes[key] = value
        
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span"""
        # Simple implementation - could be enhanced
        event_attrs = attributes or {}
        event_attrs['event_name'] = name
        event_attrs['timestamp'] = time.time()
        
    def finish(self) -> None:
        """Finish the span"""
        self.end_time = time.time()
        
    def __enter__(self):
        set_trace_id(self.trace_id)
        set_span_id(self.span_id)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()

@contextmanager
def start_span(name: str, trace_id: Optional[str] = None):
    """Start a new span"""
    span = Span(name, trace_id)
    try:
        yield span
    finally:
        span.finish()

def get_current_span() -> Optional[Span]:
    """Get the current span from context"""
    # Simple implementation - return None for now
    return None

def start_span_async(name: str, trace_id: Optional[str] = None) -> Span:
    """Start a span for async operations"""
    return Span(name, trace_id)