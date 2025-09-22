"""
Observability Context Management
===============================

Context variables for tracing and correlation across the Family AI system.
Provides thread-safe context management for tracking requests through
the Memory Backbone architecture.
"""

from contextvars import ContextVar
from typing import Optional

# Context variables for distributed tracing
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
memory_operation_var: ContextVar[Optional[str]] = ContextVar(
    "memory_operation", default=None
)
family_context_var: ContextVar[Optional[dict]] = ContextVar(
    "family_context", default=None
)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context"""
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set the trace ID in context"""
    trace_id_var.set(trace_id)


def get_span_id() -> Optional[str]:
    """Get the current span ID from context"""
    return span_id_var.get()


def set_span_id(span_id: str) -> None:
    """Set the span ID in context"""
    span_id_var.set(span_id)


def get_memory_operation() -> Optional[str]:
    """Get the current memory operation from context"""
    return memory_operation_var.get()


def set_memory_operation(operation: str) -> None:
    """Set the memory operation in context"""
    memory_operation_var.set(operation)


def get_family_context() -> Optional[dict]:
    """Get the current family context from context"""
    return family_context_var.get()


def set_family_context(context: dict) -> None:
    """Set the family context in context"""
    family_context_var.set(context)


def clear_context() -> None:
    """Clear all context variables"""
    trace_id_var.set(None)
    span_id_var.set(None)
    memory_operation_var.set(None)
    family_context_var.set(None)
