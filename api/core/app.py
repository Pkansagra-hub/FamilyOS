"""
FastAPI application factory for MemoryOS API.

This module provides the central application factory that creates
and configures the FastAPI application with all necessary middleware,
routers, and dependencies.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..middleware import setup_middleware_chain
from ..routers import setup_routers
from .dependencies import setup_dependencies
from .exceptions import setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    await setup_dependencies(app)

    yield

    # Shutdown
    # Cleanup resources here
    pass


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="MemoryOS API",
        description="Contract-first API for MemoryOS across Agents/App/Control planes",
        version="1.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://agents.familyos.local",
            "https://app.familyos.local",
            "https://control.familyos.local",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Setup middleware chain (PEP)
    setup_middleware_chain(app)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Setup routers
    setup_routers(app)

    return app
