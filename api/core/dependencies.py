"""
Dependency injection container for MemoryOS API.

This module sets up all the dependencies needed by the API layer,
including policy engines, storage services, and external integrations.
"""

from fastapi import FastAPI

from policy.abac import AbacEngine
from policy.consent import ConsentStore
from policy.rbac import RbacEngine
from policy.redactor import Redactor
from policy.service import PolicyService
from policy.space_policy import SpacePolicy


async def setup_dependencies(app: FastAPI) -> None:
    """
    Setup dependency injection container.

    Args:
        app: FastAPI application instance
    """
    # Initialize policy engines
    rbac_engine = RbacEngine("/var/family/policy/roles.json")
    abac_engine = AbacEngine()
    consent_store = ConsentStore("/var/family/policy/consent.json")
    redactor = Redactor()

    # Initialize space policy
    space_policy = SpacePolicy(
        rbac=rbac_engine, abac=abac_engine, consent=consent_store
    )

    # Initialize policy service
    policy_service = PolicyService(
        rbac_engine=rbac_engine,
        abac_engine=abac_engine,
        space_policy=space_policy,
        redactor=redactor,
    )

    # Store dependencies in app state
    app.state.policy_service = policy_service
    app.state.rbac_engine = rbac_engine
    app.state.space_policy = space_policy
    app.state.redactor = redactor


def get_policy_service(app: FastAPI) -> PolicyService:
    """Get policy service from app state."""
    return app.state.policy_service


def get_rbac_engine(app: FastAPI) -> RbacEngine:
    """Get RBAC engine from app state."""
    return app.state.rbac_engine


def get_space_policy(app: FastAPI) -> SpacePolicy:
    """Get space policy from app state."""
    return app.state.space_policy


def get_redactor(app: FastAPI) -> Redactor:
    """Get redactor from app state."""
    return app.state.redactor
