# Retrieval Service RBAC Policy (OPA/Rego)
# Implements role-based access control for memory recall operations
# Supports space-scoped access and band-level filtering

package retrieval.rbac

import rego.v1

# Define comprehensive roles hierarchy with clearance requirements
roles := {
    "memory_reader": {
        "permissions": ["recall:read"],
        "spaces": ["personal", "selective", "shared"],
        "bands": ["GREEN", "AMBER"],
        "clearance_required": 1,
        "max_results": 50,
        "qos_budget_ms": 200
    },
    "memory_analyst": {
        "permissions": ["recall:read", "recall:trace"],
        "spaces": ["personal", "selective", "shared", "extended"],
        "bands": ["GREEN", "AMBER", "RED"],
        "clearance_required": 2,
        "max_results": 100,
        "qos_budget_ms": 500
    },
    "memory_admin": {
        "permissions": ["recall:read", "recall:trace", "recall:debug"],
        "spaces": ["personal", "selective", "shared", "extended", "interfamily"],
        "bands": ["GREEN", "AMBER", "RED", "BLACK"],
        "clearance_required": 3,
        "max_results": 200,
        "qos_budget_ms": 1000
    },
    "system": {
        "permissions": ["recall:read", "recall:trace", "recall:debug"],
        "spaces": ["personal", "selective", "shared", "extended", "interfamily"],
        "bands": ["GREEN", "AMBER", "RED", "BLACK"],
        "clearance_required": 0,
        "max_results": 1000,
        "qos_budget_ms": 10000
    }
}

# Default deny
default allow := false

# Allow recall operations based on role, clearance, and context
allow if {
    input.action == "recall"
    user_role := input.user.role
    role_config := roles[user_role]

    # Check clearance level requirement
    clearance_check

    # Check permission
    input.operation in role_config.permissions

    # Check space access
    space_allowed

    # Check band access
    band_allowed

    # Check QoS budget limits
    qos_budget_valid

    # Check temporal filters are valid
    temporal_filters_valid

    # Check business hours (if required)
    time_access_allowed
}

# Clearance level validation
clearance_check if {
    user_role := input.user.role
    role_config := roles[user_role]
    user_clearance := input.user.clearance_level

    user_clearance >= role_config.clearance_required
}

# Enhanced space access validation with ownership checks
space_allowed if {
    user_role := input.user.role
    role_config := roles[user_role]
    requested_space := input.context.space_id
    space_prefix := split(requested_space, ":")[0]
    space_prefix in role_config.spaces

    # Additional ownership check for personal spaces
    space_ownership_check
}

# Space ownership validation
space_ownership_check if {
    # For personal spaces, verify ownership
    requested_space := input.context.space_id
    startswith(requested_space, "personal:")
    space_owner := substring(requested_space, 9, -1)
    space_owner == input.user.id
}

space_ownership_check if {
    # For shared spaces, verify department match
    requested_space := input.context.space_id
    startswith(requested_space, "shared:")
    space_dept := substring(requested_space, 7, -1)
    space_dept == input.user.department
}

space_ownership_check if {
    # For other space types, role permissions are sufficient
    requested_space := input.context.space_id
    not startswith(requested_space, "personal:")
    not startswith(requested_space, "shared:")
}

space_ownership_check if {
    # No space specified - global access
    not input.context.space_id
    input.user.role in ["memory_admin", "memory_analyst"]
}

# Enhanced band-level access validation with clearance requirements
band_allowed if {
    user_role := input.user.role
    role_config := roles[user_role]
    user_clearance := input.user.clearance_level

    # If no band filter specified, check role default bands
    not input.filters.bands
    count(role_config.bands) > 0
}

band_allowed if {
    user_role := input.user.role
    role_config := roles[user_role]
    user_clearance := input.user.clearance_level

    # If bands specified in filter, validate each band
    requested_bands := input.filters.bands
    allowed_bands := role_config.bands

    # Additional clearance checks for specific bands
    all_bands_allowed := {band |
        band := requested_bands[_]
        band in allowed_bands
        band_clearance_check(band, user_clearance)
    }
    count(all_bands_allowed) == count(requested_bands)
}

# Band-specific clearance requirements
band_clearance_check("GREEN", clearance) if clearance >= 1
band_clearance_check("AMBER", clearance) if clearance >= 2
band_clearance_check("RED", clearance) if clearance >= 3
band_clearance_check("BLACK", clearance) if clearance >= 4

# Enhanced QoS budget validation by role and clearance
qos_budget_valid if {
    budget := input.context.qos.latency_budget_ms
    user_role := input.user.role
    role_config := roles[user_role]

    budget <= role_config.qos_budget_ms
}

# Business hours and time-based access control
time_access_allowed if {
    # Parse timestamp
    timestamp := input.context.timestamp
    time_parts := time.parse_rfc3339_ns(timestamp)
    hour := time_parts[1]

    # Business hours: 6 AM to 10 PM
    hour >= 6
    hour <= 22
}

time_access_allowed if {
    # After hours access for admins and system roles
    user_role := input.user.role
    user_role in ["memory_admin", "system"]
}

time_access_allowed if {
    # Emergency access flag
    input.context.emergency == true
    input.user.role == "memory_admin"
}

# Enhanced temporal filter validation
temporal_filters_valid if {
    filters := input.filters

    # If no temporal filters, always valid
    not filters.after
    not filters.before
}

temporal_filters_valid if {
    filters := input.filters

    # If only one temporal filter, valid
    filters.after
    not filters.before
}

temporal_filters_valid if {
    filters := input.filters

    # If only one temporal filter, valid
    not filters.after
    filters.before
}

temporal_filters_valid if {
    filters := input.filters

    # If both specified, after must be before 'before'
    filters.after
    filters.before
    after := time.parse_rfc3339_ns(filters.after)
    before := time.parse_rfc3339_ns(filters.before)
    after < before
}

# Complete access decision with enhanced reasoning
access_decision := {
    "allow": allow,
    "reasons": reasons,
    "constraints": constraints,
    "errors": errors
}

# Enhanced reason collection
reasons contains "role_permitted" if {
    user_role := input.user.role
    user_role in object.keys(roles)
}

reasons contains "clearance_sufficient" if clearance_check
reasons contains "space_access_granted" if space_allowed
reasons contains "band_access_granted" if band_allowed
reasons contains "temporal_filters_valid" if temporal_filters_valid
reasons contains "qos_budget_valid" if qos_budget_valid
reasons contains "time_access_allowed" if time_access_allowed

# Error collection for debugging
errors contains sprintf("insufficient_clearance: required=%d, actual=%d", [roles[input.user.role].clearance_required, input.user.clearance_level]) if {
    not clearance_check
    input.user.role in object.keys(roles)
}

errors contains "invalid_role" if {
    not input.user.role in object.keys(roles)
}

errors contains "space_access_denied" if {
    not space_allowed
}

errors contains "band_access_denied" if {
    not band_allowed
}

errors contains "qos_budget_exceeded" if {
    not qos_budget_valid
}

errors contains "time_access_denied" if {
    not time_access_allowed
}

# Enhanced constraints with role-based limits
constraints := {
    "max_results": max_results_for_role,
    "allowed_bands": allowed_bands_for_role,
    "allowed_spaces": allowed_spaces_for_role,
    "qos_budget_ms": qos_budget_for_role,
    "require_audit": audit_required
}

max_results_for_role := roles[input.user.role].max_results if {
    input.user.role in object.keys(roles)
} else := 10  # restrictive default

allowed_bands_for_role := roles[input.user.role].bands if {
    input.user.role in object.keys(roles)
} else := ["GREEN"]  # safe default

allowed_spaces_for_role := roles[input.user.role].spaces if {
    input.user.role in object.keys(roles)
} else := ["personal"]  # safe default

qos_budget_for_role := roles[input.user.role].qos_budget_ms if {
    input.user.role in object.keys(roles)
} else := 50  # restrictive default

# Audit requirements for sensitive operations
audit_required := true if {
    # High-privilege operations require audit
    input.operation in ["recall:trace", "recall:debug"]
}

audit_required := true if {
    # Cross-space access requires audit
    requested_space := input.context.space_id
    not startswith(requested_space, "personal:")
    input.user.role != "system"
}

audit_required := true if {
    # High security bands require audit
    requested_bands := input.filters.bands
    high_security_bands := {"RED", "BLACK"}
    intersection := requested_bands & high_security_bands
    count(intersection) > 0
}

audit_required := false if {
    # No audit required for basic operations
    input.operation == "recall:read"
    input.user.role == "memory_reader"
    not input.filters.bands
}

# Example usage in policy evaluation:
# Input format:
# {
#   "action": "recall",
#   "operation": "recall:read",
#   "user": {
#     "id": "user123",
#     "role": "memory_reader"
#   },
#   "context": {
#     "space_id": "shared:household",
#     "qos": {
#       "latency_budget_ms": 50
#     }
#   },
#   "filters": {
#     "bands": ["GREEN", "AMBER"],
#     "after": "2025-01-01T00:00:00Z"
#   }
# }
