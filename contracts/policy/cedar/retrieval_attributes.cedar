// Retrieval Service Attribute-Based Access Control (Cedar)
// Defines fine-grained attribute-based policies for memory recall operations
// Comprehensive ABAC implementation with dynamic attributes

// =============================================================================
// Enhanced Entity Type Definitions
// =============================================================================

entity User in [Role, Department] = {
    "id": String,
    "role": String,
    "clearance_level": Long,
    "department": String,
    "team": String,
    "assigned_spaces": Set<String>,
    "active_since": String,
    "last_activity": String,
    "emergency_access": Bool,
    "authorized_topics": Set<String>
};

entity Role = {
    "name": String,
    "permissions": Set<String>,
    "max_clearance": Long,
    "default_qos_budget": Long,
    "space_types_allowed": Set<String>
};

entity Department = {
    "name": String,
    "allowed_spaces": Set<String>,
    "security_policy": String,
    "clearance_requirement": Long
};

entity Space = {
    "id": String,
    "type": String,  // "personal", "selective", "shared", "extended", "interfamily"
    "owner": User,
    "members": Set<User>,
    "sensitivity": String, // "public", "internal", "confidential", "restricted"
    "created_at": String,
    "department": String,
    "access_policy": String
};

entity MemoryItem in [Space, SecurityBand] = {
    "id": String,
    "content_type": String,
    "created_at": String,
    "updated_at": String,
    "owner": User,
    "topics": Set<String>,
    "metadata": String
};

entity SecurityBand = {
    "level": String,  // "GREEN", "AMBER", "RED", "BLACK"
    "clearance_required": Long,
    "audit_required": Bool,
    "department_restricted": Bool
};
// =============================================================================
// Action Definitions
// =============================================================================

action "recall:read" appliesTo {
    principal: User,
    resource: MemoryItem,
    context: {
        "qos_budget_ms": Long,
        "timestamp": String,
        "space_id"?: String,
        "emergency"?: Bool,
        "trace_enabled"?: Bool
    }
};

action "recall:trace" appliesTo {
    principal: User,
    resource: MemoryItem,
    context: {
        "qos_budget_ms": Long,
        "timestamp": String,
        "space_id"?: String,
        "trace_depth": Long
    }
};

action "recall:debug" appliesTo {
    principal: User,
    resource: MemoryItem,
    context: {
        "qos_budget_ms": Long,
        "timestamp": String,
        "space_id"?: String,
        "debug_level": String
    }
};

// =============================================================================
// Core RBAC Policies
// =============================================================================

// Basic read access for memory readers
@id("rbac-memory-reader-basic")
permit (
    principal in Role::"memory_reader",
    action == "recall:read",
    resource
) when {
    // Clearance check
    principal.clearance_level >= resource.in.clearance_required &&

    // QoS budget limits
    context.qos_budget_ms <= principal.in.default_qos_budget &&

    // Space access validation
    (
        // Personal space: must be owner
        (resource.in.type == "personal" && resource.in.owner == principal) ||

        // Selective space: must be member
        (resource.in.type == "selective" && principal in resource.in.members) ||

        // Shared space: department match
        (resource.in.type == "shared" && principal.department == resource.in.department)
    ) &&

    // Security band restrictions (GREEN, AMBER only)
    resource.in.level in ["GREEN", "AMBER"]
};

// Enhanced access for memory analysts
@id("rbac-memory-analyst-enhanced")
permit (
    principal in Role::"memory_analyst",
    action in ["recall:read", "recall:trace"],
    resource
) when {
    // Clearance and QoS checks
    principal.clearance_level >= resource.in.clearance_required &&
    context.qos_budget_ms <= principal.in.default_qos_budget &&

    // Extended space access
    (
        (resource.in.type == "personal" && resource.in.owner == principal) ||
        (resource.in.type == "selective" && principal in resource.in.members) ||
        (resource.in.type == "shared" && principal.department == resource.in.department) ||
        (resource.in.type == "extended" && principal.clearance_level >= 3)
    ) &&

    // Extended security bands (GREEN, AMBER, RED)
    resource.in.level in ["GREEN", "AMBER", "RED"]
};

// Administrative access for memory admins
@id("rbac-memory-admin-full")
permit (
    principal in Role::"memory_admin",
    action in ["recall:read", "recall:trace", "recall:debug"],
    resource
) when {
    // Admins need clearance 4+ for BLACK band
    (resource.in.level != "BLACK" || principal.clearance_level >= 4) &&

    // Higher QoS budget
    context.qos_budget_ms <= 1000
};
forbid(
  principal,
  action,
  resource
) when {
  // Department isolation for confidential items
  resource.sensitivity == "confidential" &&
  principal.department != resource.owner.department &&
  principal.role != "memory_admin"
};

@id("abac-clearance-level")
forbid(
  principal,
  action,
  resource
) when {
  // Clearance level requirements
  resource.band == "BLACK" &&
  principal.clearance_level < 3
};

@id("abac-qos-budget-limits")
forbid(
  principal,
  action in [recall_read, recall_trace],
  resource
) when {
  // QoS budget limits by role
  (principal.role == "memory_reader" &&
   context.qos_budget > 100) ||
  (principal.role == "memory_analyst" &&
   context.qos_budget > 500) ||
  (principal.role == "memory_admin" &&
   context.qos_budget > 1000)
};

@id("abac-space-member-access")
permit(
  principal,
  action in [recall_read],
  resource
) when {
  // Direct space membership grants read access for GREEN/AMBER
  principal in resource.space.members &&
  resource.band in ["GREEN", "AMBER"] &&
  resource.space.type != "interfamily"
};

@id("abac-topic-based-access")
forbid(
  principal,
  action,
  resource
) when {
  // Topic-based restrictions
  resource.topics.contains("medical") &&
  principal.role != "memory_admin" &&
  !principal.assigned_spaces.contains("medical:authorized")
};

@id("abac-cross-space-restrictions")
forbid(
  principal,
  action,
  resource
) when {
  // Prevent cross-space queries for non-admins during certain operations
  context.operation_type == "bulk_query" &&
  principal.role != "memory_admin" &&
  resource.space.type == "interfamily"
};

// Data reduction policies

@id("data-redaction-sensitive")
permit(
  principal,
  action in [recall_read],
  resource
) when {
  // Allow access but require redaction for sensitive content
  resource.sensitivity in ["confidential", "restricted"] &&
  principal.role != "memory_admin"
} unless {
  // Full access for same department
  principal.department == resource.owner.department
};

// Example attribute mappings:
// User attributes:
// - role: "memory_reader" | "memory_analyst" | "memory_admin"
// - clearance_level: 1-5 (1=basic, 5=top secret)
// - assigned_spaces: ["personal:user123", "shared:team_alpha", ...]
// - department: "engineering" | "research" | "operations" | "admin"
// - team: "backend" | "ml" | "security" | ...

// Space attributes:
// - type: space classification level
// - sensitivity: data classification
// - members: who has access
// - owner: primary responsible party

// Memory item attributes:
// - band: security classification
// - topics: content categorization
// - sensitivity: data classification level
// - created_at/updated_at: temporal attributes
