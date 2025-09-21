from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from .abac import AbacContext, AbacEngine
from .config_loader import resolve_band_for_space
from .consent import ConsentStore
from .decision import Obligation, PolicyDecision
from .rbac import RbacEngine

Band = Literal["GREEN", "AMBER", "RED", "BLACK"]
ShareOp = Literal["REFER", "PROJECT", "DETACH", "UNDO"]
SpaceType = Literal["personal", "selective", "shared", "extended", "interfamily"]


@dataclass
class ShareRequest:
    op: str  # Changed from ShareOp to str for flexibility
    actor_id: str
    from_space: str
    to_space: Optional[str]
    band: Band
    tags: List[str]


@dataclass
class SpaceInfo:
    """Enhanced space information with hierarchy and type details."""

    space_id: str
    space_type: SpaceType
    parent_space: Optional[str] = None
    hierarchy_level: int = 0
    family_id: Optional[str] = None
    household_id: Optional[str] = None


class SpacePolicy:
    """Enhanced SpacePolicy with comprehensive space hierarchy and cross-family support."""

    def __init__(
        self,
        rbac: RbacEngine,
        abac: AbacEngine,
        consent: ConsentStore,
        band_defaults: dict | None = None,
        space_config: dict | None = None,
    ):
        self.rbac = rbac
        self.abac = abac
        self.consent = consent
        self.band_defaults = band_defaults or {}
        self.space_config = space_config or {}

    def parse_space_id(self, space_id: str) -> SpaceInfo:
        """Parse space ID and extract space information."""
        if ":" not in space_id:
            raise ValueError(f"Invalid space ID format: {space_id}")

        space_type, space_path = space_id.split(":", 1)

        if space_type == "personal":
            # personal:alice.family1 → family_id="alice.family1", hierarchy=0
            # For personal spaces, keep the full path as family_id
            return SpaceInfo(
                space_id=space_id,
                space_type=space_type,
                family_id=space_path,  # Keep full path as family_id
                hierarchy_level=0,
            )

        elif space_type == "selective":
            # selective:household1.family1 → household="household1", family="family1"
            if "." in space_path:
                household_id, family_id = space_path.split(".", 1)
            else:
                household_id = space_path
                family_id = None
            return SpaceInfo(
                space_id=space_id,
                space_type=space_type,
                household_id=household_id,
                family_id=family_id,
                hierarchy_level=1,
            )

        elif space_type == "shared":
            # shared:household1 → household="household1"
            household_id = space_path
            # Parent space is the corresponding selective space
            parent_space = f"selective:{household_id}"
            return SpaceInfo(
                space_id=space_id,
                space_type=space_type,
                household_id=household_id,
                hierarchy_level=2,
                parent_space=parent_space,
            )

        elif space_type == "extended":
            # extended:family1 → family="family1"
            family_id = space_path
            return SpaceInfo(
                space_id=space_id,
                space_type=space_type,
                family_id=family_id,
                hierarchy_level=3,
            )

        elif space_type == "interfamily":
            # interfamily:global → top level
            return SpaceInfo(
                space_id=space_id, space_type=space_type, hierarchy_level=4
            )

        else:
            raise ValueError(f"Unknown space type: {space_type}")

    def _extract_family_name_for_comparison(self, space_info: SpaceInfo) -> str | None:
        """Extract family name for cross-family comparison."""
        if not space_info.family_id:
            return None

        if space_info.space_type == "personal":
            # For personal:alice.family1, extract family1
            if "." in space_info.family_id:
                return space_info.family_id.split(".")[-1]
            return space_info.family_id
        else:
            # For other space types, family_id is already the family name
            return space_info.family_id

    def is_cross_family_operation(self, from_space: str, to_space: str) -> bool:
        """Determine if operation crosses family boundaries."""
        try:
            from_info = self.parse_space_id(from_space)
            to_info = self.parse_space_id(to_space)

            # Interfamily spaces are always cross-family
            if (
                from_info.space_type == "interfamily"
                or to_info.space_type == "interfamily"
            ):
                return True

            # Extract family names for comparison
            from_family = self._extract_family_name_for_comparison(from_info)
            to_family = self._extract_family_name_for_comparison(to_info)

            # Different family names indicate cross-family
            if from_family and to_family:
                return from_family != to_family

            return False
        except ValueError:
            # If parsing fails, assume cross-family for safety
            return True

    def get_required_consent_level(
        self, from_space: str, to_space: str, operation: ShareOp
    ) -> str:
        """Determine required consent level based on space hierarchy and operation."""
        try:
            from_info = self.parse_space_id(from_space)
            to_info = self.parse_space_id(to_space)

            # Higher hierarchy levels require more restrictive consent
            max_level = max(from_info.hierarchy_level, to_info.hierarchy_level)

            if operation == "PROJECT":
                if max_level >= 4:  # interfamily
                    return "explicit_interfamily_consent"
                elif max_level >= 3:  # extended
                    return "extended_family_consent"
                elif max_level >= 2:  # shared
                    return "household_consent"
                else:
                    return "family_consent"
            elif operation == "REFER":
                # REFER operations have lower consent requirements
                if max_level >= 4:
                    return "interfamily_consent"
                elif max_level >= 2:
                    return "household_consent"
                else:
                    return "implicit_consent"

            return "basic_consent"
        except ValueError:
            return "explicit_interfamily_consent"  # Fail safe

    def evaluate_band_policy(
        self, request: ShareRequest, from_info: SpaceInfo, to_info: Optional[SpaceInfo]
    ) -> tuple[bool, List[str]]:
        """Enhanced band policy evaluation with space-aware logic."""
        reasons = []

        # BLACK band always denies projection operations
        if request.band == "BLACK":
            if request.op in ("PROJECT", "DETACH"):
                return False, ["band_black_denies_projection"]
            elif request.op == "REFER":
                reasons.append("band_black_limits_refer_to_metadata_only")

        # RED band restrictions based on space hierarchy
        if request.band == "RED":
            if request.op == "PROJECT":
                if to_info and to_info.space_type in ("extended", "interfamily"):
                    return False, ["band_red_denies_external_projection"]
                elif to_info and to_info.hierarchy_level > from_info.hierarchy_level:
                    return False, ["band_red_denies_hierarchy_escalation"]
                else:
                    reasons.append("band_red_restricts_projection_metadata_only")
            elif request.op == "DETACH" and to_info:
                if to_info.space_type in ("extended", "interfamily"):
                    return False, ["band_red_denies_external_detachment"]

        # AMBER band escalation rules
        if request.band == "AMBER":
            if request.op == "PROJECT" and to_info:
                if to_info.space_type == "interfamily":
                    reasons.append("band_amber_requires_explicit_consent_interfamily")
                elif to_info.hierarchy_level > from_info.hierarchy_level + 1:
                    reasons.append("band_amber_limits_hierarchy_jump")

        # Apply space-specific band floor
        space_band_floor = self.get_space_band_floor(from_info.space_id)
        if space_band_floor and self._band_level(request.band) < self._band_level(
            space_band_floor
        ):
            reasons.append(f"space_band_floor_escalated_to_{space_band_floor}")

        return True, reasons

    def _band_level(self, band: Band) -> int:
        """Get numeric level for band comparison."""
        return {"GREEN": 0, "AMBER": 1, "RED": 2, "BLACK": 3}[band]

    def get_space_band_floor(self, space_id: str) -> Optional[Band]:
        """Get minimum required band for a space."""
        return resolve_band_for_space(space_id, self.band_defaults)

    def evaluate_share(
        self, req: ShareRequest, abac_ctx: AbacContext
    ) -> PolicyDecision:
        """Enhanced share evaluation with comprehensive space policy support."""
        reasons = []
        eff_caps = []
        cap_map = {
            "REFER": "memory.refer",
            "PROJECT": "memory.project",
            "DETACH": "memory.detach",
            "UNDO": "privacy.undo",
            # Add common memory operations for API compatibility
            "memory.read": "memory.read",
            "memory.write": "memory.write",
            "memory.refer": "memory.refer",
            "memory.project": "memory.project",
            "memory.detach": "memory.detach",
        }
        cap_needed = cap_map.get(
            req.op, req.op
        )  # Fall back to operation name if not mapped

        # Parse space information
        try:
            from_info = self.parse_space_id(req.from_space)
            to_info = self.parse_space_id(req.to_space) if req.to_space else None
        except ValueError as e:
            return PolicyDecision(
                decision="DENY", reasons=[f"invalid_space_format:{str(e)}"]
            )

        # RBAC check
        if not self.rbac.has_cap(req.actor_id, req.from_space, cap_needed):
            return PolicyDecision(
                decision="DENY", reasons=[f"missing_cap:{cap_needed}"]
            )
        eff_caps.append(cap_needed)

        # Enhanced consent checking for cross-family operations
        if req.op in ("PROJECT", "REFER") and req.to_space:
            if self.is_cross_family_operation(req.from_space, req.to_space):
                required_consent = self.get_required_consent_level(
                    req.from_space, req.to_space, req.op
                )
                if not self.consent.has_consent(
                    req.from_space, req.to_space, required_consent
                ):
                    return PolicyDecision(
                        decision="DENY", reasons=[f"missing_consent:{required_consent}"]
                    )
                reasons.append(f"consent_verified:{required_consent}")

        # Enhanced band policy evaluation
        band_allowed, band_reasons = self.evaluate_band_policy(req, from_info, to_info)
        if not band_allowed:
            return PolicyDecision(decision="DENY", reasons=band_reasons)
        reasons.extend(band_reasons)

        # Space hierarchy validation
        if req.op == "PROJECT" and to_info:
            hierarchy_change = abs(to_info.hierarchy_level - from_info.hierarchy_level)
            if hierarchy_change >= 3:
                reasons.append("hierarchy_jump_warning")
            if (
                to_info.space_type == "interfamily"
                and from_info.space_type != "interfamily"
            ):
                reasons.append("interfamily_projection_audit_required")

        # ABAC evaluation with enhanced context
        enhanced_abac_ctx = self._enhance_abac_context(
            abac_ctx, from_info, to_info, req
        )
        abac_dec, abac_reasons, obligations_dict = self.abac.evaluate(
            f"memory.{req.op.lower()}", enhanced_abac_ctx
        )
        reasons.extend(abac_reasons)

        # Build obligations
        obligations = Obligation(
            redact=obligations_dict.get("redact", []),
            band_min=obligations_dict.get("band_min"),
            log_audit=obligations_dict.get("log_audit", True),
            reason_tags=obligations_dict.get("reason_tags", [])
            + [f"space_type:{from_info.space_type}"],
        )

        # Add space-specific audit requirements
        if to_info and to_info.space_type == "interfamily":
            obligations.log_audit = True
            obligations.reason_tags.append("interfamily_operation")

        # Determine final decision
        decision = (
            "ALLOW_REDACTED"
            if abac_dec == "ALLOW_REDACTED" or obligations.redact
            else "ALLOW"
        )

        return PolicyDecision(
            decision=decision,
            reasons=reasons,
            obligations=obligations,
            effective_caps=eff_caps,
        )

    def _enhance_abac_context(
        self,
        ctx: AbacContext,
        from_info: SpaceInfo,
        to_info: Optional[SpaceInfo],
        req: ShareRequest,
    ) -> AbacContext:
        """Enhance ABAC context with space hierarchy information."""
        # Start with existing env attrs (only fields that exist in EnvAttrs)
        enhanced_env = {
            "time_of_day_hours": ctx.env.time_of_day_hours,
            "location": ctx.env.location,
            "space_band_min": ctx.env.space_band_min,
            "arousal": ctx.env.arousal,
            "safety_pressure": ctx.env.safety_pressure,
            "curfew_hours": ctx.env.curfew_hours,
            "risk_assessment": ctx.env.risk_assessment or {},
            "temporal_context": ctx.env.temporal_context,
            "ip_address": ctx.env.ip_address,
            "request_id": ctx.env.request_id,
            "geofence_zone": ctx.env.geofence_zone,
            "ambient_noise_level": ctx.env.ambient_noise_level,
            "family_present": ctx.env.family_present,
        }

        # Create space-specific risk assessment data
        space_risk_data = {
            "from_space_type": from_info.space_type,
            "from_hierarchy_level": from_info.hierarchy_level,
            "from_family_id": from_info.family_id,
            "from_household_id": from_info.household_id,
        }

        if to_info:
            space_risk_data.update(
                {
                    "to_space_type": to_info.space_type,
                    "to_hierarchy_level": to_info.hierarchy_level,
                    "to_family_id": to_info.family_id,
                    "to_household_id": to_info.household_id,
                    "is_cross_family": self.is_cross_family_operation(
                        req.from_space, req.to_space
                    ),
                    "hierarchy_level_change": to_info.hierarchy_level
                    - from_info.hierarchy_level,
                }
            )

        # Add space risk data to existing risk assessment
        enhanced_env["risk_assessment"].update(space_risk_data)

        # Adjust safety pressure based on space operations
        if to_info:
            hierarchy_delta = abs(to_info.hierarchy_level - from_info.hierarchy_level)
            if hierarchy_delta > 2:  # Big hierarchy jump
                current_pressure = enhanced_env["safety_pressure"] or 0.0
                enhanced_env["safety_pressure"] = min(1.0, current_pressure + 0.3)
            elif to_info.space_type == "interfamily":
                current_pressure = enhanced_env["safety_pressure"] or 0.0
                enhanced_env["safety_pressure"] = min(1.0, current_pressure + 0.2)

        # Create new context with enhanced environment
        from .abac import EnvAttrs

        enhanced_env_attrs = EnvAttrs(**enhanced_env)

        return AbacContext(actor=ctx.actor, device=ctx.device, env=enhanced_env_attrs)

    def get_space_capabilities(self, space_id: str, actor_id: str) -> List[str]:
        """Get available capabilities for an actor in a specific space."""
        try:
            space_info = self.parse_space_id(space_id)
            base_caps = []

            # Get RBAC capabilities
            for cap in [
                "memory.read",
                "memory.write",
                "memory.refer",
                "memory.project",
                "memory.detach",
            ]:
                if self.rbac.has_cap(actor_id, space_id, cap):
                    base_caps.append(cap)

            # Space type specific capabilities
            if space_info.space_type == "interfamily":
                if self.rbac.has_cap(actor_id, space_id, "privacy.interfamily_admin"):
                    base_caps.append("interfamily.admin")

            return base_caps
        except ValueError:
            return []
