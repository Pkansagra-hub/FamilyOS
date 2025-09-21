"""
API routers for the 3-plane architecture.

This package contains routers for:
- Agents Plane: mTLS authenticated tool endpoints
- App Plane: Bearer token authenticated user endpoints
- Control Plane: Admin/security endpoints with HSM certs
"""

from fastapi import FastAPI

# Import all the API plane routers
from . import admin_index_security, agents_tools, app_frontend, health, rbac


def setup_routers(app: FastAPI) -> None:
    """Setup all API routers for the 3-plane architecture."""

    # 🤖 AGENTS PLANE (mTLS authenticated) - /v1/tools/*
    app.include_router(agents_tools.router, tags=["agents"])

    # 📱 APP PLANE (Bearer token authenticated) - /api/v1/*
    app.include_router(app_frontend.router, tags=["app"])

    # 🔐 ADMIN/INDEX/SECURITY PLANE (Admin authenticated) - /admin/v1/*
    app.include_router(admin_index_security.router, tags=["control"])

    # Additional routers
    app.include_router(health.router, tags=["health"])
    app.include_router(rbac.router, tags=["rbac"])


__all__ = ["setup_routers"]
