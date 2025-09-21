# Memory-Centric Family AI - ABAC Policy Rules
# Attribute-Based Access Control for Family Memory Operations
# Supports: spaces, roles, devices, bands, obligations, and family relationships

package familyos.abac

# =============================================================================
# Core Policy Decision Entry Point
# =============================================================================

# Main authorization decision for family memory operations
allow {
    input.action == "memory_operation"
    is_valid_family_member
    has_memory_space_access
    passes_band_requirements
    meets_device_requirements
    satisfies_obligations
    respects_family_policies
}

# Main authorization decision for family coordination
allow {
    input.action == "family_coordination"
    is_valid_family_member
    has_coordination_permissions
    passes_relationship_requirements
    satisfies_supervision_requirements
    respects_emergency_protocols
}

# Main authorization decision for device operations
allow {
    input.action == "device_operation"
    is_valid_device_owner_or_delegate
    passes_device_security_requirements
    has_device_capability_access
    satisfies_sync_requirements
}

# =============================================================================
# Family Member Validation
# =============================================================================

# Validate family member identity and status
is_valid_family_member {
    input.actor.family_member_id
    input.actor.family_role in family_roles
    is_active_family_member
    not is_suspended_member
}

# Define valid family roles
family_roles := {
    "family_admin",
    "parent",
    "child",
    "extended_family",
    "guest"
}

# Check if family member is active
is_active_family_member {
    # Family member exists in system
    input.actor.family_member_id != ""
    # Family ID matches
    input.family_context.family_id == input.actor.family_id
}

# Check if family member is suspended
is_suspended_member {
    input.actor.family_member_id in data.suspended_members
}

# =============================================================================
# Memory Space Access Control
# =============================================================================

# Memory space access validation
has_memory_space_access {
    memory_space := input.memory_context.memory_space
    memory_space in allowed_memory_spaces
}

# Define allowed memory spaces based on family role and relationship
allowed_memory_spaces[space] {
    space := "personal"
    # Personal space: always accessible to owner
    input.actor.user_id == input.memory_context.memory_owner_id
}

allowed_memory_spaces[space] {
    space := "selective"
    # Selective space: accessible to owner and explicitly granted members
    input.actor.user_id == input.memory_context.memory_owner_id
}

allowed_memory_spaces[space] {
    space := "selective"
    # Selective space: accessible to explicitly granted family members
    input.actor.family_member_id in input.memory_context.selective_access_list
}

allowed_memory_spaces[space] {
    space := "shared"
    # Shared space: accessible to all family members
    input.actor.family_role in {"family_admin", "parent", "child", "extended_family"}
}

allowed_memory_spaces[space] {
    space := "extended"
    # Extended space: accessible to family admin and parents
    input.actor.family_role in {"family_admin", "parent"}
}

allowed_memory_spaces[space] {
    space := "extended"
    # Extended space: accessible to explicitly granted children
    input.actor.family_role == "child"
    input.actor.family_member_id in input.memory_context.extended_access_list
}

allowed_memory_spaces[space] {
    space := "interfamily"
    # Interfamily space: only accessible to family admin
    input.actor.family_role == "family_admin"
}

# =============================================================================
# Band Requirements (Data Sensitivity)
# =============================================================================

# Band-based access control validation
passes_band_requirements {
    band := input.band
    band in allowed_bands
}

# Define allowed bands based on family role and age
allowed_bands[band] {
    band := "GREEN"
    # Green band: accessible to all family members
    input.actor.family_role in family_roles
}

allowed_bands[band] {
    band := "AMBER"
    # Amber band: accessible to adults and supervised children
    input.actor.family_role in {"family_admin", "parent"}
}

allowed_bands[band] {
    band := "AMBER"
    # Amber band: accessible to children with supervision
    input.actor.family_role == "child"
    input.abac.supervision_required == false
}

allowed_bands[band] {
    band := "RED"
    # Red band: only accessible to parents and family admin
    input.actor.family_role in {"family_admin", "parent"}
}

allowed_bands[band] {
    band := "BLACK"
    # Black band: only accessible to family admin
    input.actor.family_role == "family_admin"
}

# =============================================================================
# Device Requirements
# =============================================================================

# Device access validation
meets_device_requirements {
    is_trusted_device
    has_required_capabilities
    passes_security_requirements
}

# Validate device trust level
is_trusted_device {
    input.device.device_id in data.trusted_devices
    input.device.ownership_type in allowed_ownership_types
}

# Define allowed device ownership types based on family role
allowed_ownership_types[ownership] {
    ownership := "personal"
    # Personal devices: accessible to owner
    input.device.device_owner_id == input.actor.user_id
}

allowed_ownership_types[ownership] {
    ownership := "shared_family"
    # Shared family devices: accessible to all family members
    input.actor.family_role in family_roles
}

allowed_ownership_types[ownership] {
    ownership := "guest"
    # Guest devices: limited access
    input.actor.family_role == "guest"
    input.memory_context.memory_space == "shared"
}

# Validate device capabilities
has_required_capabilities {
    required_capability := input.memory_context.required_capability
    required_capability in input.device.capabilities
}

# Device security requirements
passes_security_requirements {
    # Device must have encryption for sensitive operations
    sensitive_operation
    input.device.encryption_hardware == true
}

passes_security_requirements {
    # Non-sensitive operations don't require encryption
    not sensitive_operation
}

# Define sensitive operations
sensitive_operation {
    input.band in {"AMBER", "RED", "BLACK"}
}

sensitive_operation {
    input.memory_context.memory_space in {"selective", "extended", "interfamily"}
}

# =============================================================================
# Family Coordination Permissions
# =============================================================================

# Family coordination access validation
has_coordination_permissions {
    coordination_type := input.family_context.coordination_type
    coordination_type in allowed_coordination_types
}

# Define allowed coordination types based on family role
allowed_coordination_types[coord_type] {
    coord_type := "scheduling"
    # Scheduling: accessible to parents and children
    input.actor.family_role in {"family_admin", "parent", "child"}
}

allowed_coordination_types[coord_type] {
    coord_type := "information_sharing"
    # Information sharing: accessible to all family members
    input.actor.family_role in family_roles
}

allowed_coordination_types[coord_type] {
    coord_type := "decision_making"
    # Decision making: accessible to parents and family admin
    input.actor.family_role in {"family_admin", "parent"}
}

allowed_coordination_types[coord_type] {
    coord_type := "emergency_response"
    # Emergency response: accessible to all family members
    input.actor.family_role in family_roles
}

# =============================================================================
# Relationship Requirements
# =============================================================================

# Relationship context validation
passes_relationship_requirements {
    relationship_context := input.family_context.relationship_context
    is_valid_relationship_context(relationship_context)
}

# Validate relationship context format and access
is_valid_relationship_context(context) {
    # Personal context (single member)
    context == input.actor.family_member_id
}

is_valid_relationship_context(context) {
    # Pair/group context (multiple members)
    members := split(context, "_")
    input.actor.family_member_id in members
    all_members_in_family(members)
}

# Validate all members are in the same family
all_members_in_family(members) {
    count(members) > 0
    all_members := {member | member := members[_]}
    family_members := data.family_members[input.family_context.family_id]
    all_members & family_members == all_members
}

# =============================================================================
# Supervision Requirements
# =============================================================================

# Supervision validation for children
satisfies_supervision_requirements {
    # Adults don't require supervision
    input.actor.family_role in {"family_admin", "parent", "extended_family"}
}

satisfies_supervision_requirements {
    # Children may require supervision based on age and content
    input.actor.family_role == "child"
    child_supervision_satisfied
}

# Child supervision logic
child_supervision_satisfied {
    # No supervision required for child
    input.abac.supervision_required == false
}

child_supervision_satisfied {
    # Supervision required and present
    input.abac.supervision_required == true
    input.family_context.supervision_active == true
}

child_supervision_satisfied {
    # Emergency override for critical situations
    input.abac.emergency_override == true
    input.family_context.emergency_type in {"medical", "safety", "security"}
}

# =============================================================================
# Emergency Protocols
# =============================================================================

# Emergency protocol validation
respects_emergency_protocols {
    not is_emergency_situation
}

respects_emergency_protocols {
    is_emergency_situation
    has_emergency_permissions
}

# Detect emergency situations
is_emergency_situation {
    input.family_context.emergency_type in {"medical", "safety", "security", "missing_person"}
}

# Emergency permissions validation
has_emergency_permissions {
    # Family admin always has emergency permissions
    input.actor.family_role == "family_admin"
}

has_emergency_permissions {
    # Parents have emergency permissions
    input.actor.family_role == "parent"
}

has_emergency_permissions {
    # Extended family with emergency delegation
    input.actor.family_role == "extended_family"
    input.actor.delegation_context.emergency_access == true
}

has_emergency_permissions {
    # Children in life-threatening situations
    input.actor.family_role == "child"
    input.family_context.emergency_type == "medical"
    input.family_context.threat_level == "critical"
}

# =============================================================================
# Obligation Requirements
# =============================================================================

# Policy obligation validation
satisfies_obligations {
    count(input.obligations) == 0
}

satisfies_obligations {
    count(input.obligations) > 0
    all_obligations_satisfied
}

# Validate all obligations are satisfied
all_obligations_satisfied {
    obligations := input.obligations
    satisfied_obligations := {obligation |
        obligation := obligations[_]
        is_obligation_satisfied(obligation)
    }
    obligations == satisfied_obligations
}

# Individual obligation validation
is_obligation_satisfied("REDACT_PII") {
    input.redaction_applied == true
}

is_obligation_satisfied("AUDIT_ACCESS") {
    input.audit_context.audit_enabled == true
}

is_obligation_satisfied("FAMILY_CONSENT_REQUIRED") {
    has_family_consent
}

is_obligation_satisfied("AGE_APPROPRIATE_FILTER") {
    age_appropriate_content
}

is_obligation_satisfied("EMERGENCY_ACCESS_LOG") {
    emergency_access_logged
}

is_obligation_satisfied("MEMORY_CONSOLIDATION_ELIGIBLE") {
    memory_consolidation_criteria_met
}

is_obligation_satisfied("CROSS_DEVICE_SYNC") {
    sync_requirements_met
}

is_obligation_satisfied("SUBSCRIPTION_GATE_CHECK") {
    subscription_tier_adequate
}

is_obligation_satisfied("RELATIONSHIP_VALIDATION") {
    relationship_context_validated
}

is_obligation_satisfied("EMOTIONAL_CONTEXT_PRESERVE") {
    emotional_context_preserved
}

# =============================================================================
# Family Policy Compliance
# =============================================================================

# Family-specific policy validation
respects_family_policies {
    respects_privacy_settings
    respects_content_restrictions
    respects_time_boundaries
    respects_device_restrictions
}

# Privacy settings compliance
respects_privacy_settings {
    privacy_level := input.family_context.privacy_level
    privacy_level in allowed_privacy_levels
}

# Define allowed privacy levels
allowed_privacy_levels[level] {
    level := "public"
    # Public: accessible in any context
}

allowed_privacy_levels[level] {
    level := "family"
    # Family: accessible within family context
    input.actor.family_role in family_roles
}

allowed_privacy_levels[level] {
    level := "parents_only"
    # Parents only: restricted to parents and family admin
    input.actor.family_role in {"family_admin", "parent"}
}

allowed_privacy_levels[level] {
    level := "private"
    # Private: only accessible to owner
    input.actor.user_id == input.memory_context.memory_owner_id
}

# Content restriction compliance
respects_content_restrictions {
    content_type := input.memory_context.content_type
    content_appropriate_for_role(content_type, input.actor.family_role)
}

# Age-appropriate content validation
content_appropriate_for_role(content_type, "child") {
    content_type in {"educational", "entertainment_child", "family_photos", "family_messages"}
}

content_appropriate_for_role(content_type, role) {
    role in {"family_admin", "parent", "extended_family"}
    # Adults can access all content types
}

# Time boundary compliance
respects_time_boundaries {
    current_time := time.now_ns()
    family_schedule := data.family_schedules[input.family_context.family_id]
    is_within_allowed_time(current_time, family_schedule)
}

# Device restriction compliance
respects_device_restrictions {
    device_allowed_for_user
    device_within_location_bounds
}

# =============================================================================
# Sync Requirements
# =============================================================================

# Device sync validation
satisfies_sync_requirements {
    sync_mode := input.device_context.sync_mode
    sync_allowed_for_operation(sync_mode)
}

# Validate sync mode for operation
sync_allowed_for_operation("local_only") {
    input.memory_context.memory_space == "personal"
}

sync_allowed_for_operation("family_sync") {
    input.memory_context.memory_space in {"selective", "shared", "extended"}
    has_family_sync_permissions
}

sync_allowed_for_operation("full_sync") {
    input.actor.family_role in {"family_admin", "parent"}
}

# Family sync permissions
has_family_sync_permissions {
    input.actor.family_role in {"family_admin", "parent", "child"}
    input.device.sync_capability != "none"
}

# =============================================================================
# Helper Functions
# =============================================================================

# Validate family consent
has_family_consent {
    consent_type := input.family_context.consent_type
    consent_obtained_for_type(consent_type)
}

# Age-appropriate content validation
age_appropriate_content {
    input.actor.family_role != "child"
}

age_appropriate_content {
    input.actor.family_role == "child"
    input.memory_context.age_rating <= input.actor.age_category_limit
}

# Emergency access logging
emergency_access_logged {
    input.audit_context.emergency_access_logged == true
}

# Memory consolidation criteria
memory_consolidation_criteria_met {
    input.memory_context.consolidation_eligible == true
    input.memory_context.memory_age >= input.memory_context.consolidation_threshold
}

# Sync requirements validation
sync_requirements_met {
    input.device.sync_capability in {"full", "partial"}
    input.device.network_capability != "offline"
}

# Subscription tier validation
subscription_tier_adequate {
    required_tier := input.memory_context.required_subscription_tier
    current_tier := input.subscription_context.subscription_tier
    tier_level(current_tier) >= tier_level(required_tier)
}

# Tier level mapping
tier_level("base") = 1
tier_level("child_addon") = 2
tier_level("extended_family") = 3
tier_level("premium") = 4

# Relationship context validation
relationship_context_validated {
    input.family_context.relationship_context_verified == true
}

# Emotional context preservation
emotional_context_preserved {
    input.family_context.emotional_context != null
    input.memory_context.preserve_emotional_context == true
}

# Time boundary validation helper
is_within_allowed_time(current_time, schedule) {
    # Always allow emergency access
    input.family_context.emergency_type
}

is_within_allowed_time(current_time, schedule) {
    # Check against family schedule rules
    time_allowed_by_schedule(current_time, schedule)
}

# Device location validation
device_within_location_bounds {
    device_location := input.device.physical_location
    allowed_locations := data.family_device_policies[input.family_context.family_id].allowed_locations
    device_location in allowed_locations
}

# Device user validation
device_allowed_for_user {
    # Personal devices: only owner
    input.device.ownership_type == "personal"
    input.device.device_owner_id == input.actor.user_id
}

device_allowed_for_user {
    # Shared family devices: all family members
    input.device.ownership_type == "shared_family"
    input.actor.family_role in family_roles
}

device_allowed_for_user {
    # Guest devices: limited access
    input.device.ownership_type == "guest"
    input.actor.family_role == "guest"
}

# =============================================================================
# Default Deny Policy
# =============================================================================

# Default deny for any unmatched requests
default allow = false
