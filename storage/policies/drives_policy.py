"""Drives Policy Integration - Drive-aware access controls and behavioral constraints."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from policy import PolicyDecision
from storage.drives_store import DrivesStore

logger = logging.getLogger(__name__)


@dataclass
class DrivesPolicyConfig:
    """Configuration for drives-aware policy decisions."""

    # Drive priority thresholds for policy actions
    high_priority_threshold: float = 0.8  # Emergency drive state
    urgent_threshold: float = 0.7  # Urgent action needed
    normal_threshold: float = 0.4  # Normal operating range

    # Drive-specific escalation rules
    sleep_escalation_hours: float = 6.0  # Hours awake before escalation
    social_isolation_hours: float = 24.0  # Hours without social contact
    planning_debt_threshold: float = 0.8  # Planning debt before restriction

    # Behavioral constraints
    restrict_risky_when_tired: bool = True  # Block risky actions when sleep deprived
    prioritize_drives_over_tasks: bool = (
        True  # Drive satisfaction overrides task requests
    )
    escalate_band_on_emergency: bool = True  # Escalate to AMBER on drive emergency

    # Temporal modulation
    circadian_modulation: bool = True  # Apply time-of-day effects
    weekend_relaxation: bool = True  # Relax some constraints on weekends

    # Drive weighting for decision making
    drive_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "sleep": 1.0,  # Sleep is critical
            "social": 0.8,  # Social connection important
            "hunger": 0.9,  # Basic need
            "exercise": 0.6,  # Health maintenance
            "chores": 0.4,  # Household maintenance
            "planning": 0.7,  # Cognitive load management
            "achievement": 0.5,  # Personal growth
            "creativity": 0.3,  # Self-expression
        }
    )


class DrivesPolicyEngine:
    """Drive-aware policy integration for Family OS drives system."""

    def __init__(
        self, drives_store: DrivesStore, config: Optional[DrivesPolicyConfig] = None
    ):
        self.drives_store = drives_store
        self.config = config or DrivesPolicyConfig()

    def enrich_context_with_drives(
        self, context: Dict[str, Any], person_id: str, space_id: str
    ) -> Dict[str, Any]:
        """Enrich ABAC context with current drive state information."""
        try:
            # Get current drive state
            drive_state = self.drives_store.get_drive_state(person_id, space_id)

            # Calculate drive priorities
            priorities = self.drives_store.get_drive_priorities(
                person_id,
                space_id,
                affect_arousal=context.get("affect_arousal", 0.0),
                time_of_day_sin=context.get("time_of_day_sin", 0.0),
                day_of_week_sin=context.get("day_of_week_sin", 0.0),
                is_urgent=context.get("is_urgent", False),
            )

            # Identify highest priority drives
            max_priority = max(priorities.values()) if priorities else 0.0
            urgent_drives = [
                drive
                for drive, priority in priorities.items()
                if priority >= self.config.urgent_threshold
            ]
            emergency_drives = [
                drive
                for drive, priority in priorities.items()
                if priority >= self.config.high_priority_threshold
            ]

            # Specific drive assessments
            sleep_priority = priorities.get("sleep", 0.0)
            social_priority = priorities.get("social", 0.0)
            planning_priority = priorities.get("planning", 0.0)

            # Update context with drive information
            enriched_context = context.copy()
            enriched_context.update(
                {
                    "drives_max_priority": max_priority,
                    "drives_urgent": urgent_drives,
                    "drives_emergency": emergency_drives,
                    "drives_sleep_priority": sleep_priority,
                    "drives_social_priority": social_priority,
                    "drives_planning_priority": planning_priority,
                    "drives_priorities": priorities,
                    "drives_last_update": drive_state.last_update,
                    "drives_assessment_time": time.time(),
                }
            )

            return enriched_context

        except Exception as e:
            logger.error(f"Failed to enrich context with drives: {e}")
            return context

    def evaluate_drives_policy(
        self, action: str, context: Dict[str, Any], person_id: str, space_id: str
    ) -> tuple[PolicyDecision, List[str], Dict[str, Any]]:
        """Evaluate drive-aware policy for the given action and context."""

        try:
            # Enrich context with drive information
            enriched_context = self.enrich_context_with_drives(
                context, person_id, space_id
            )

            decision = "ALLOW"
            reasons = []
            obligations_dict = {
                "redact": [],
                "band_min": None,
                "log_audit": True,
                "reason_tags": [],
            }

            # Get drive state information
            max_priority = enriched_context.get("drives_max_priority", 0.0)
            urgent_drives = enriched_context.get("drives_urgent", [])
            emergency_drives = enriched_context.get("drives_emergency", [])
            sleep_priority = enriched_context.get("drives_sleep_priority", 0.0)
            planning_priority = enriched_context.get("drives_planning_priority", 0.0)

            # Emergency drive state - escalate band and restrict risky actions
            if emergency_drives:
                reasons.append(f"emergency_drive_state: {emergency_drives}")
                obligations_dict["reason_tags"].append("drive_emergency")

                if self.config.escalate_band_on_emergency:
                    obligations_dict["band_min"] = "AMBER"
                    reasons.append("band_escalated_for_drive_emergency")

                # Block risky actions during drive emergency
                if action in ["memory.project", "memory.detach", "tools.run"]:
                    decision = "DENY"
                    reasons.append("risky_action_blocked_during_drive_emergency")
                    return decision, reasons, obligations_dict

            # Sleep deprivation restrictions
            if sleep_priority >= self.config.urgent_threshold:
                reasons.append(f"sleep_deprivation_detected: {sleep_priority:.3f}")
                obligations_dict["reason_tags"].append("sleep_deprived")

                if self.config.restrict_risky_when_tired:
                    if action in ["memory.project", "tools.run"]:
                        obligations_dict["redact"].extend(["pii.email", "pii.phone"])
                        decision = "ALLOW_REDACTED"
                        reasons.append("sleep_deprivation_triggers_redaction")

                    if action == "memory.detach":
                        decision = "DENY"
                        reasons.append("memory_detach_blocked_when_sleep_deprived")
                        return decision, reasons, obligations_dict

            # Planning debt restrictions - block cognitive load when overwhelmed
            if planning_priority >= self.config.planning_debt_threshold:
                reasons.append(f"high_planning_debt: {planning_priority:.3f}")
                obligations_dict["reason_tags"].append("planning_overwhelmed")

                # Restrict complex cognitive tasks
                if action in ["prospective.manage", "tools.run"]:
                    if max_priority >= self.config.urgent_threshold:
                        decision = "DENY"
                        reasons.append("complex_task_blocked_due_planning_debt")
                        return decision, reasons, obligations_dict
                    else:
                        obligations_dict["band_min"] = "AMBER"
                        reasons.append("planning_debt_escalates_band")

            # Drive prioritization - urgent drives override normal tasks
            if urgent_drives and self.config.prioritize_drives_over_tasks:
                reasons.append(f"urgent_drives_detected: {urgent_drives}")
                obligations_dict["reason_tags"].append("drive_priority")

                # Suggest drive-serving actions be prioritized
                if action == "memory.write":
                    obligations_dict["band_min"] = (
                        "GREEN"  # Keep immediate needs visible
                    )
                    reasons.append("drive_urgency_maintains_green_band")

            # Temporal modulation effects
            if self.config.circadian_modulation:
                time_of_day_sin = enriched_context.get("time_of_day_sin", 0.0)

                # Late night restrictions for non-sleep actions
                if time_of_day_sin < -0.7:  # Late night
                    if action not in ["memory.read", "prospective.manage"]:
                        obligations_dict["redact"].extend(["pii.sensitive"])
                        if decision == "ALLOW":
                            decision = "ALLOW_REDACTED"
                        reasons.append("late_night_activity_redaction")

            # Weekend relaxation
            if self.config.weekend_relaxation:
                day_of_week_sin = enriched_context.get("day_of_week_sin", 0.0)
                if day_of_week_sin > 0.5:  # Weekend
                    # Relax some drive-based restrictions
                    if "sleep_deprived" in obligations_dict["reason_tags"]:
                        # Remove some sleep restrictions on weekends
                        if action == "memory.project":
                            if decision == "ALLOW_REDACTED":
                                decision = "ALLOW"
                                obligations_dict["redact"] = []
                                reasons.append("weekend_relaxes_sleep_restrictions")

            return decision, reasons, obligations_dict

        except Exception as e:
            logger.error(f"Failed to evaluate drives policy: {e}")
            return (
                "ALLOW",
                ["drives_policy_error"],
                {"redact": [], "band_min": None, "log_audit": True, "reason_tags": []},
            )

    def get_drives_summary(self, person_id: str, space_id: str) -> Dict[str, Any]:
        """Get current drives summary for reporting and debugging."""
        try:
            drive_state = self.drives_store.get_drive_state(person_id, space_id)
            priorities = self.drives_store.get_drive_priorities(person_id, space_id)

            # Recent events
            recent_events = self.drives_store.get_drive_events(
                person_id, space_id, hours=24, limit=10
            )

            return {
                "person_id": person_id,
                "space_id": space_id,
                "priorities": priorities,
                "max_priority": max(priorities.values()) if priorities else 0.0,
                "urgent_drives": [
                    drive
                    for drive, priority in priorities.items()
                    if priority >= self.config.urgent_threshold
                ],
                "emergency_drives": [
                    drive
                    for drive, priority in priorities.items()
                    if priority >= self.config.high_priority_threshold
                ],
                "last_update": drive_state.last_update,
                "recent_events": len(recent_events),
                "version": drive_state.version,
            }

        except Exception as e:
            logger.error(f"Failed to get drives summary: {e}")
            return {"person_id": person_id, "space_id": space_id, "error": str(e)}

    def update_drives_from_event(
        self, event: Dict[str, Any], person_id: str, space_id: str
    ) -> bool:
        """Update drive states based on observed events."""
        try:
            event_type = event.get("type", "")

            # Sleep-related events
            if event_type in ["sleep_start", "sleep_end", "bedtime_reminder"]:
                if event_type == "sleep_start":
                    # Sleep satisfaction
                    duration = event.get("duration", 8.0)  # Hours
                    delta_x = min(duration / 8.0, 1.0)  # Normalize to 0-1

                    self.drives_store.satisfy_drive(
                        person_id,
                        space_id,
                        "sleep",
                        delta_x=delta_x,
                        source="sleep_event",
                        tags=["sleep", "restorative"],
                    )
                    return True

                elif event_type == "sleep_end":
                    # Begin sleep debt accumulation
                    self.drives_store.satisfy_drive(
                        person_id,
                        space_id,
                        "sleep",
                        delta_x=-0.1,
                        source="wake_event",
                        tags=["wake", "debt_start"],
                    )
                    return True

            # Social interaction events
            elif event_type in ["social_interaction", "family_time", "conversation"]:
                quality = event.get("quality", 0.5)
                duration = event.get("duration", 1.0)  # Hours
                delta_x = quality * min(
                    duration / 2.0, 1.0
                )  # Up to 2 hours max benefit

                self.drives_store.satisfy_drive(
                    person_id,
                    space_id,
                    "social",
                    delta_x=delta_x,
                    source="social_event",
                    tags=["social", "interaction"],
                )
                return True

            # Task completion events
            elif event_type in ["task_completed", "chore_done", "achievement"]:
                task_type = event.get("task_type", "general")
                success = event.get("success", True)

                if success:
                    if task_type in ["chore", "household"]:
                        self.drives_store.satisfy_drive(
                            person_id,
                            space_id,
                            "chores",
                            delta_x=0.3,
                            source="task_completion",
                            tags=["chore", "completion"],
                        )
                    elif task_type in ["planning", "organization"]:
                        self.drives_store.satisfy_drive(
                            person_id,
                            space_id,
                            "planning",
                            delta_x=0.4,
                            source="planning_event",
                            tags=["planning", "organization"],
                        )
                    elif task_type in ["achievement", "goal"]:
                        self.drives_store.satisfy_drive(
                            person_id,
                            space_id,
                            "achievement",
                            delta_x=0.5,
                            source="achievement_event",
                            tags=["achievement", "goal"],
                        )
                return True

            # Exercise and health events
            elif event_type in ["exercise", "physical_activity", "health"]:
                intensity = event.get("intensity", 0.5)
                duration = event.get("duration", 0.5)  # Hours
                delta_x = intensity * min(duration / 1.0, 1.0)

                self.drives_store.satisfy_drive(
                    person_id,
                    space_id,
                    "exercise",
                    delta_x=delta_x,
                    source="exercise_event",
                    tags=["exercise", "health"],
                )
                return True

            # Eating events
            elif event_type in ["meal", "eating", "nutrition"]:
                satisfaction = event.get("satisfaction", 0.7)

                self.drives_store.satisfy_drive(
                    person_id,
                    space_id,
                    "hunger",
                    delta_x=satisfaction,
                    source="meal_event",
                    tags=["nutrition", "meal"],
                )
                return True

            # Creative activities
            elif event_type in ["creative", "art", "music", "writing"]:
                satisfaction = event.get("satisfaction", 0.6)

                self.drives_store.satisfy_drive(
                    person_id,
                    space_id,
                    "creativity",
                    delta_x=satisfaction,
                    source="creative_event",
                    tags=["creativity", "expression"],
                )
                return True

            return False  # Event not relevant to drives

        except Exception as e:
            logger.error(f"Failed to update drives from event: {e}")
            return False
