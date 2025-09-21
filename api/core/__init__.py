"""
Core API infrastructure components.

This package provides the foundational infrastructure for the MemoryOS API,
including application factory, dependency injection, and exception handling.
"""

from .app import create_app
from .dependencies import (
    get_policy_service,
    get_rbac_engine,
    get_redactor,
    get_space_policy,
    setup_dependencies,
)
from .exceptions import setup_exception_handlers

__all__ = [
    "create_app",
    "setup_dependencies",
    "get_policy_service",
    "get_rbac_engine",
    "get_space_policy",
    "get_redactor",
    "setup_exception_handlers",
]
