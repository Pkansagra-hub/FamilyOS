from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional, Set

from .adapters.json_doc import JsonDocStore
from .errors import RBACError

Capability = str
SCHEMA_VERSION = 2  # Enhanced for Issue #26.1: Role hierarchy

# Issue #26.2: Dynamic assignment types
AssignmentStrategy = Literal[
    "immediate", "approval_required", "conditional", "scheduled"
]


class AssignmentStatus(Enum):
    """Status for dynamic role assignments"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ACTIVE = "active"


@dataclass
class DynamicAssignment:
    """Dynamic role assignment with lifecycle management - Issue #26.2"""

    assignment_id: str
    principal_id: str
    role: str
    space_id: str
    strategy: AssignmentStrategy
    status: AssignmentStatus
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    expires_at: Optional[str] = None
    justification: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class RoleDef:
    """Enhanced role definition with inheritance support - Issue #26.1"""

    name: str
    caps: List[Capability]
    inherits: List[str] = field(default_factory=list)  # Roles this role inherits from
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Binding:
    principal_id: str
    role: str
    space_id: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class RbacEngine:
    """
    Role-Based Access Control engine with a single-file JSON store.
    Provides define/remove role, bind/unbind, and capability checks.
    """

    def __init__(self, path: str):
        self.store = JsonDocStore(
            path, schema_version=SCHEMA_VERSION, init_data={"roles": {}, "bindings": []}
        )

    def _read(self) -> Dict[str, object]:
        return self.store.read()

    def _write(self, data: Dict[str, object]) -> None:
        self.store.write(data)

    def define_role(self, role: RoleDef) -> None:
        """Define a role with inheritance support - Issue #26.1"""
        # Validate inheritance hierarchy to prevent cycles
        self._validate_role_hierarchy(role.name, role.inherits)

        def _mut(doc):
            # Store role with inheritance information
            role_data = {
                "caps": sorted(set(role.caps)),
                "inherits": role.inherits,
                "description": role.description,
                "created_at": role.created_at,
            }
            doc.setdefault("roles", {})[role.name] = role_data

        self.store.update(_mut)

    def remove_role(self, role_name: str) -> None:
        def _mut(doc):
            roles = doc.setdefault("roles", {})
            if role_name in roles:
                del roles[role_name]
            # Also drop any bindings to that role
            doc["bindings"] = [
                b for b in doc.get("bindings", []) if b.get("role") != role_name
            ]

        self.store.update(_mut)

    def bind(self, b: Binding) -> None:
        def _mut(doc):
            if b.role not in doc.get("roles", {}):
                raise RBACError(f"unknown_role:{b.role}")
            # de-dup
            for existing in doc.get("bindings", []):
                if (
                    existing["principal_id"] == b.principal_id
                    and existing["role"] == b.role
                    and existing["space_id"] == b.space_id
                ):
                    return
            doc.setdefault("bindings", []).append(b.__dict__)

        self.store.update(_mut)

    def unbind(self, principal_id: str, role: str, space_id: str) -> None:
        def _mut(doc):
            doc["bindings"] = [
                b
                for b in doc.get("bindings", [])
                if not (
                    b["principal_id"] == principal_id
                    and b["role"] == role
                    and b["space_id"] == space_id
                )
            ]

        self.store.update(_mut)

    def list_caps(self, principal_id: str, space_id: str) -> Set[Capability]:
        """List capabilities with inheritance resolution - Issue #26.1"""
        data = self._read()
        caps: Set[Capability] = set()

        # Get all roles for this principal in this space
        for b in data.get("bindings", []):
            if b.get("principal_id") == principal_id and b.get("space_id") == space_id:
                role_name = b.get("role")
                if role_name:
                    # Resolve capabilities with inheritance
                    resolved_caps = self._resolve_role_capabilities(role_name, data)
                    caps.update(resolved_caps)
        return caps

    def _resolve_role_capabilities(self, role_name: str, data: Dict) -> Set[Capability]:
        """Resolve capabilities for a role including inherited capabilities - Issue #26.1"""
        resolved_caps: Set[Capability] = set()
        visited_roles: Set[str] = set()

        def _resolve_recursive(current_role: str):
            if current_role in visited_roles:
                # Circular dependency detected - log and skip
                return
            visited_roles.add(current_role)

            role_data = data.get("roles", {}).get(current_role)
            if not role_data:
                return

            # Add direct capabilities
            if isinstance(role_data, list):
                # Legacy format - just capabilities
                resolved_caps.update(role_data)
            elif isinstance(role_data, dict):
                # New format with inheritance
                resolved_caps.update(role_data.get("caps", []))

                # Recursively resolve inherited roles
                for inherited_role in role_data.get("inherits", []):
                    _resolve_recursive(inherited_role)

        _resolve_recursive(role_name)
        return resolved_caps

    def _validate_role_hierarchy(self, role_name: str, inherits: List[str]) -> None:
        """Validate role hierarchy to prevent circular dependencies - Issue #26.1"""
        data = self._read()

        def _has_circular_dependency(
            current_role: str, target_role: str, visited: Set[str]
        ) -> bool:
            if current_role == target_role:
                return True
            if current_role in visited:
                return False

            visited.add(current_role)
            role_data = data.get("roles", {}).get(current_role, {})

            if isinstance(role_data, dict):
                for inherited in role_data.get("inherits", []):
                    if _has_circular_dependency(inherited, target_role, visited.copy()):
                        return True
            return False

        # Check each inherited role for circular dependencies
        for inherited_role in inherits:
            if _has_circular_dependency(inherited_role, role_name, set()):
                raise RBACError(
                    f"circular_dependency: Role '{role_name}' cannot inherit from '{inherited_role}' (creates cycle)"
                )

    def get_role_hierarchy(self, role_name: str) -> Dict[str, List[str]]:
        """Get the complete hierarchy for a role - Issue #26.1"""
        data = self._read()
        hierarchy = {"inherits": [], "inherited_by": []}

        # Find what this role inherits
        role_data = data.get("roles", {}).get(role_name, {})
        if isinstance(role_data, dict):
            hierarchy["inherits"] = role_data.get("inherits", [])

        # Find what roles inherit from this role
        for other_role, other_data in data.get("roles", {}).items():
            if isinstance(other_data, dict):
                if role_name in other_data.get("inherits", []):
                    hierarchy["inherited_by"].append(other_role)

        return hierarchy

    # Issue #26.2: Dynamic Role Assignment Methods

    def request_role_assignment(
        self,
        principal_id: str,
        role: str,
        space_id: str,
        strategy: AssignmentStrategy = "immediate",
        justification: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> str:
        """Request dynamic role assignment - Issue #26.2"""
        assignment_id = (
            f"assign_{int(datetime.now().timestamp())}_{principal_id}_{role}"
        )

        # Calculate expiration if needed
        expires_at = None
        if expires_in_hours:
            expiry = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            expires_at = expiry.isoformat()

        # Determine initial status based on strategy
        if strategy == "immediate":
            status = AssignmentStatus.ACTIVE
        elif strategy == "approval_required":
            status = AssignmentStatus.PENDING
        elif strategy == "conditional":
            status = AssignmentStatus.PENDING  # Evaluate conditions
        elif strategy == "scheduled":
            status = AssignmentStatus.PENDING
        else:
            status = AssignmentStatus.PENDING

        assignment = DynamicAssignment(
            assignment_id=assignment_id,
            principal_id=principal_id,
            role=role,
            space_id=space_id,
            strategy=strategy,
            status=status,
            expires_at=expires_at,
            justification=justification,
        )

        def _mut(doc):
            # Convert assignment to JSON-serializable dict
            assignment_dict = assignment.__dict__.copy()
            assignment_dict["status"] = (
                assignment.status.value
            )  # Convert enum to string
            doc.setdefault("dynamic_assignments", {})[assignment_id] = assignment_dict

            # If immediate, also create the binding
            if strategy == "immediate":
                binding = Binding(principal_id, role, space_id)
                # Check if role exists
                if role not in doc.get("roles", {}):
                    raise RBACError(f"unknown_role:{role}")
                # Add binding
                doc.setdefault("bindings", []).append(binding.__dict__)

        self.store.update(_mut)
        return assignment_id

    def approve_assignment(self, assignment_id: str, approver_id: str) -> bool:
        """Approve a pending dynamic assignment - Issue #26.2"""

        def _mut(doc):
            assignments = doc.setdefault("dynamic_assignments", {})
            if assignment_id not in assignments:
                raise RBACError(f"assignment_not_found:{assignment_id}")

            assignment = assignments[assignment_id]
            if assignment["status"] != "pending":
                raise RBACError(f"assignment_not_pending:{assignment_id}")

            # Update assignment status
            assignment["status"] = "approved"
            assignment["approved_by"] = approver_id
            assignment["approved_at"] = datetime.now(timezone.utc).isoformat()

            # Create the actual binding
            binding = Binding(
                assignment["principal_id"], assignment["role"], assignment["space_id"]
            )

            # Check if role exists
            if assignment["role"] not in doc.get("roles", {}):
                raise RBACError(f"unknown_role:{assignment['role']}")

            # Add binding
            doc.setdefault("bindings", []).append(binding.__dict__)

        self.store.update(_mut)
        return True

    def reject_assignment(
        self, assignment_id: str, rejector_id: str, reason: str = ""
    ) -> bool:
        """Reject a pending dynamic assignment - Issue #26.2"""

        def _mut(doc):
            assignments = doc.setdefault("dynamic_assignments", {})
            if assignment_id not in assignments:
                raise RBACError(f"assignment_not_found:{assignment_id}")

            assignment = assignments[assignment_id]
            if assignment["status"] != "pending":
                raise RBACError(f"assignment_not_pending:{assignment_id}")

            assignment["status"] = "rejected"
            assignment["approved_by"] = rejector_id
            assignment["approved_at"] = datetime.now(timezone.utc).isoformat()
            assignment["metadata"]["rejection_reason"] = reason

        self.store.update(_mut)
        return True

    def get_pending_assignments(
        self, approver_role: Optional[str] = None
    ) -> List[Dict]:
        """Get pending assignments that need approval - Issue #26.2"""
        data = self._read()
        assignments = data.get("dynamic_assignments", {})

        pending = []
        for assignment_id, assignment in assignments.items():
            if assignment.get("status") == "pending":
                pending.append(assignment)

        return pending

    def cleanup_expired_assignments(self) -> int:
        """Clean up expired dynamic assignments - Issue #26.2"""
        now = datetime.now(timezone.utc)
        cleaned_count = 0

        def _mut(doc):
            nonlocal cleaned_count
            assignments = doc.setdefault("dynamic_assignments", {})
            bindings = doc.setdefault("bindings", [])

            expired_assignments = []
            for assignment_id, assignment in assignments.items():
                expires_at = assignment.get("expires_at")
                if expires_at:
                    try:
                        expiry = datetime.fromisoformat(
                            expires_at.replace("Z", "+00:00")
                        )
                        if now > expiry:
                            expired_assignments.append(assignment_id)

                            # Remove associated binding if it exists
                            principal_id = assignment["principal_id"]
                            role = assignment["role"]
                            space_id = assignment["space_id"]

                            doc["bindings"] = [
                                b
                                for b in bindings
                                if not (
                                    b["principal_id"] == principal_id
                                    and b["role"] == role
                                    and b["space_id"] == space_id
                                )
                            ]
                    except ValueError:
                        # Invalid date format, mark as expired
                        expired_assignments.append(assignment_id)

            # Remove expired assignments
            for assignment_id in expired_assignments:
                if assignment_id in assignments:
                    assignments[assignment_id]["status"] = "expired"
                    cleaned_count += 1

        self.store.update(_mut)
        return cleaned_count

    def has_cap(self, principal_id: str, space_id: str, cap: Capability) -> bool:
        return cap in self.list_caps(principal_id, space_id)

    def get_bindings(
        self,
        principal_id: Optional[str] = None,
        space_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        data = self._read()
        res = []
        for b in data.get("bindings", []):
            if principal_id and b.get("principal_id") != principal_id:
                continue
            if space_id and b.get("space_id") != space_id:
                continue
            if role and b.get("role") != role:
                continue
            res.append(b)
        return res
