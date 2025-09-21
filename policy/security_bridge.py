"""
SecurityContext Integration Bridge - Sub-issue #8.1

This module provides seamless integration between the API SecurityContext
and the Policy engine's ActorAttrs/DeviceAttrs/EnvAttrs system.

Features:
- Convert SecurityContext to policy attributes
- Map API capabilities to policy permissions
- Handle context propagation and caching
- Support all three API planes (Agents, App, Control)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from api.schemas import Capability, SecurityContext, TrustLevel
from policy.abac import AbacContext, ActorAttrs, DeviceAttrs, EnvAttrs
from policy.rbac import RbacEngine

logger = logging.getLogger(__name__)


class SecurityContextBridge:
    """
    Bridge between API SecurityContext and Policy engine attributes.

    Handles conversion, role resolution, and context enrichment for
    seamless RBAC/ABAC integration across all API planes.
    """

    def __init__(self, rbac_engine: RbacEngine):
        """Initialize bridge with RBAC engine for role resolution."""
        self.rbac = rbac_engine

        # Capability → Permission mapping for policy engine
        self.capability_permissions = {
            Capability.WRITE: ["memory.write", "memory.submit", "memory.ingest"],
            Capability.RECALL: ["memory.read", "memory.recall", "memory.search"],
            Capability.PROJECT: ["memory.project", "memory.share", "memory.refer"],
            Capability.SCHEDULE: [
                "prospective.manage",
                "prospective.schedule",
                "tools.run",
            ],
        }

        # Trust level → Security band mapping
        self.trust_band_mapping = {
            TrustLevel.GREEN: "GREEN",
            TrustLevel.AMBER: "AMBER",
            TrustLevel.RED: "RED",
            TrustLevel.BLACK: "BLACK",
        }

        # Cache for resolved contexts to improve performance
        self._context_cache: Dict[str, Tuple[AbacContext, float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def to_abac_context(
        self,
        security_ctx: SecurityContext,
        space_id: Optional[str] = None,
        operation: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> AbacContext:
        """
        Convert SecurityContext to ABAC evaluation context.

        Args:
            security_ctx: API SecurityContext from authentication
            space_id: Target space for operation (if applicable)
            operation: Specific operation being performed
            request_metadata: Additional request context

        Returns:
            AbacContext ready for policy evaluation
        """

        # Check cache first for performance
        cache_key = self._get_cache_key(security_ctx, space_id, operation)
        cached_result = self._get_cached_context(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for context: {cache_key}")
            return cached_result

        # Convert to ActorAttrs
        actor_attrs = self._to_actor_attrs(security_ctx, space_id)

        # Convert to DeviceAttrs
        device_attrs = self._to_device_attrs(security_ctx)

        # Create environmental context
        env_attrs = self._to_env_attrs(security_ctx, operation, request_metadata)

        # Build complete ABAC context
        abac_ctx = AbacContext(
            actor=actor_attrs,
            device=device_attrs,
            env=env_attrs,
            request_metadata=request_metadata or {},
        )

        # Cache the result
        self._cache_context(cache_key, abac_ctx)

        logger.info(
            f"Created ABAC context for user {security_ctx.user_id} "
            f"on device {security_ctx.device_id} for space {space_id}"
        )

        return abac_ctx

    def _to_actor_attrs(
        self, security_ctx: SecurityContext, space_id: Optional[str] = None
    ) -> ActorAttrs:
        """Convert SecurityContext to ActorAttrs for ABAC evaluation."""

        # Resolve roles from RBAC engine
        actor_id = str(security_ctx.user_id)
        roles = self._resolve_user_roles(actor_id, space_id)

        # Convert capabilities to policy permissions
        permissions = self._map_capabilities_to_permissions(
            security_ctx.capabilities or []
        )

        # Determine if user is minor (would need external data source)
        # For now, use heuristic based on role
        is_minor = "child" in roles or "minor" in roles

        # Extract relation from roles or external context
        relation = self._extract_relation_from_roles(roles)

        # Map trust level
        trust_level = "normal"
        if security_ctx.trust_level:
            trust_level = security_ctx.trust_level.value

        # Determine space access patterns
        space_access = self._get_space_access_patterns(actor_id, roles, space_id)

        return ActorAttrs(
            actor_id=actor_id,
            is_minor=is_minor,
            relation=relation,
            trust_level=trust_level,
            role=roles[0] if roles else None,  # Primary role
            capabilities=permissions,
            space_access=space_access,
            auth_method=(
                security_ctx.auth_method.value if security_ctx.auth_method else None
            ),
            session_id=None,  # Would need session management
            user_agent=None,  # Would come from request headers
        )

    def _to_device_attrs(self, security_ctx: SecurityContext) -> DeviceAttrs:
        """Convert SecurityContext to DeviceAttrs for ABAC evaluation."""

        # Map trust level to device trust
        device_trust = "trusted"
        if security_ctx.trust_level:
            device_trust = security_ctx.trust_level.value

        return DeviceAttrs(
            device_id=security_ctx.device_id,
            trust=device_trust,  # type: ignore
            battery_low=False,  # Would need device telemetry
            cpu_throttled=False,  # Would need device telemetry
            screen_locked=False,  # Would need device state
            location_verified=True,  # Would need location service
            network_type="trusted",  # Would need network detection
            mls_group=security_ctx.mls_group,
            device_fingerprint=None,  # Would need device fingerprinting
            os_version=None,  # Would come from User-Agent
            app_version=None,  # Would come from headers
            rooted_jailbroken=False,  # Would need device attestation
        )

    def _to_env_attrs(
        self,
        security_ctx: SecurityContext,
        operation: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> EnvAttrs:
        """Create environmental attributes for ABAC evaluation."""

        current_time = datetime.now(timezone.utc)

        # Extract space band minimum from request context
        space_band_min = None
        if request_metadata and "space_band" in request_metadata:
            space_band_min = request_metadata["space_band"]

        # Extract IP address from request metadata
        ip_address = None
        if request_metadata and "client_ip" in request_metadata:
            ip_address = request_metadata["client_ip"]

        # Extract request ID for tracing
        request_id = None
        if request_metadata and "trace_id" in request_metadata:
            request_id = request_metadata["trace_id"]

        return EnvAttrs(
            time_of_day_hours=current_time.hour + (current_time.minute / 60.0),
            location=None,  # Would need location service
            space_band_min=space_band_min,
            arousal=None,  # Would need emotion detection
            safety_pressure=None,  # Would need safety assessment
            curfew_hours=None,  # Would come from family settings
            risk_assessment=None,  # Would come from P18 pipeline
            temporal_context=None,  # Would need schedule integration
            ip_address=ip_address,
            request_id=request_id,
            geofence_zone=None,  # Would need geofencing service
            ambient_noise_level=None,  # Would need audio sensors
            family_present=True,  # Would need presence detection
        )

    def _resolve_user_roles(
        self, user_id: str, space_id: Optional[str] = None
    ) -> List[str]:
        """Resolve user roles from RBAC engine."""
        try:
            # Get all role bindings for the user using public method
            bindings = self.rbac.get_bindings(principal_id=user_id, space_id=space_id)
            roles = [binding["role"] for binding in bindings]

            # If no space-specific roles, get global roles
            if not roles and space_id:
                global_bindings = self.rbac.get_bindings(
                    principal_id=user_id, space_id="*"
                )
                roles.extend([binding["role"] for binding in global_bindings])

                # Also try "global" space_id
                global_bindings2 = self.rbac.get_bindings(
                    principal_id=user_id, space_id="global"
                )
                roles.extend([binding["role"] for binding in global_bindings2])

            # Remove duplicates while preserving order
            seen: Set[str] = set()
            unique_roles: List[str] = []
            for role in roles:
                if role not in seen:
                    seen.add(role)
                    unique_roles.append(role)

            return unique_roles or ["guest"]  # Default role

        except Exception as e:
            logger.warning(f"Failed to resolve roles for {user_id}: {e}")
            return ["guest"]

    def _map_capabilities_to_permissions(
        self, capabilities: List[Capability]
    ) -> List[str]:
        """Map API capabilities to policy permissions."""
        permissions: List[str] = []

        for capability in capabilities:
            if capability in self.capability_permissions:
                permissions.extend(self.capability_permissions[capability])

        # Remove duplicates
        return list(set(permissions))

    def _extract_relation_from_roles(self, roles: List[str]) -> Optional[str]:
        """Extract family relation from role names."""
        relation_mapping = {
            "guardian": "guardian",
            "parent": "guardian",
            "admin": "guardian",
            "child": "family",
            "member": "family",
            "guest": "friend",
            "viewer": "friend",
        }

        for role in roles:
            if role in relation_mapping:
                return relation_mapping[role]

        return "family"  # Default relation

    def _get_space_access_patterns(
        self, user_id: str, roles: List[str], current_space: Optional[str] = None
    ) -> List[str]:
        """Determine space access patterns for the user."""
        patterns: List[str] = []

        # Role-based patterns
        if "admin" in roles or "guardian" in roles:
            patterns.extend(["*:*", "shared:*", "family:*"])
        elif "member" in roles:
            patterns.extend([f"personal:{user_id}", "shared:family", "family:*"])
        elif "child" in roles:
            patterns.extend([f"personal:{user_id}", "shared:family"])
        else:  # guest, viewer
            patterns.extend(["shared:public"])

        # Add current space if specified
        if current_space:
            patterns.append(current_space)

        return list(set(patterns))  # Remove duplicates

    def _get_cache_key(
        self,
        security_ctx: SecurityContext,
        space_id: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> str:
        """Generate cache key for context caching."""
        return f"{security_ctx.user_id}:{security_ctx.device_id}:{space_id}:{operation}"

    def _get_cached_context(self, cache_key: str) -> Optional[AbacContext]:
        """Get cached ABAC context if still valid."""
        if cache_key in self._context_cache:
            context, timestamp = self._context_cache[cache_key]
            if (datetime.now().timestamp() - timestamp) < self._cache_ttl:
                return context
            else:
                # Remove expired entry
                del self._context_cache[cache_key]
        return None

    def _cache_context(self, cache_key: str, context: AbacContext) -> None:
        """Cache ABAC context with timestamp."""
        self._context_cache[cache_key] = (context, datetime.now().timestamp())

        # Simple cache cleanup - remove oldest entries if cache grows too large
        if len(self._context_cache) > 1000:
            oldest_key = min(
                self._context_cache.keys(), key=lambda k: self._context_cache[k][1]
            )
            del self._context_cache[oldest_key]

    def clear_cache(self) -> None:
        """Clear the context cache."""
        self._context_cache.clear()
        logger.info("SecurityContext bridge cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            "cache_size": len(self._context_cache),
            "cache_limit": 1000,
            "cache_ttl_seconds": self._cache_ttl,
        }
