# Control Plane Shared Schemas

## Family Administration Types

### FamilyMember
```yaml
FamilyMember:
  type: object
  required: ["member_id", "name", "role", "status"]
  properties:
    member_id:
      type: string
      pattern: "^[a-z0-9_]+$"
      description: "Unique family member identifier"
    name:
      type: string
      minLength: 1
      maxLength: 100
      description: "Family member display name"
    role:
      type: string
      enum: ["parent", "child", "guardian", "extended_family", "caregiver"]
      description: "Family relationship role"
    age_category:
      type: string
      enum: ["infant", "toddler", "child", "teenager", "adult", "senior"]
      description: "Age-appropriate category for privacy and safety"
    status:
      type: string
      enum: ["active", "inactive", "suspended", "pending_verification"]
      description: "Family member account status"
    permissions:
      type: array
      items:
        type: string
        enum: ["admin", "billing", "emergency", "child_advocate", "privacy_officer"]
      description: "Family permissions assigned to member"
    device_ids:
      type: array
      items:
        type: string
      description: "Devices associated with family member"
    privacy_preferences:
      type: object
      properties:
        data_sharing_consent:
          type: string
          enum: ["full_consent", "limited_consent", "minimal_consent", "no_consent"]
        memory_sharing_level:
          type: string
          enum: ["family_wide", "selective", "private_only"]
        external_sharing_permission:
          type: boolean
          default: false
    emergency_contacts:
      type: array
      items:
        type: object
        properties:
          contact_name:
            type: string
          relationship:
            type: string
          phone_number:
            type: string
          email:
            type: string
          priority:
            type: integer
            minimum: 1
            maximum: 10
    created_date:
      type: string
      format: date-time
    last_active:
      type: string
      format: date-time
```

### FamilyDevice
```yaml
FamilyDevice:
  type: object
  required: ["device_id", "device_type", "owner_id", "status"]
  properties:
    device_id:
      type: string
      pattern: "^[a-z0-9_]+$"
      description: "Unique device identifier"
    device_name:
      type: string
      description: "Human-readable device name"
    device_type:
      type: string
      enum: ["smartphone", "tablet", "laptop", "desktop", "smart_speaker", "smart_display", "wearable", "other"]
    owner_id:
      type: string
      description: "Primary family member who owns/uses device"
    shared_device:
      type: boolean
      default: false
      description: "Whether device is shared among family members"
    authorized_users:
      type: array
      items:
        type: string
      description: "Family members authorized to use device"
    status:
      type: string
      enum: ["active", "inactive", "suspended", "offline", "maintenance"]
    device_capabilities:
      type: object
      properties:
        memory_storage_gb:
          type: number
          minimum: 0
        processing_power:
          type: string
          enum: ["low", "medium", "high", "premium"]
        ai_processing_capability:
          type: boolean
        voice_interaction:
          type: boolean
        display_available:
          type: boolean
        camera_available:
          type: boolean
        microphone_available:
          type: boolean
    privacy_settings:
      type: object
      properties:
        always_listening:
          type: boolean
          default: false
        camera_access:
          type: string
          enum: ["always", "on_request", "family_only", "disabled"]
        microphone_access:
          type: string
          enum: ["always", "on_request", "family_only", "disabled"]
        location_sharing:
          type: string
          enum: ["always", "family_only", "emergency_only", "disabled"]
    last_sync:
      type: string
      format: date-time
    firmware_version:
      type: string
    family_ai_version:
      type: string
```

## Emergency Management Types

### EmergencyProtocol
```yaml
EmergencyProtocol:
  type: object
  required: ["protocol_id", "protocol_name", "emergency_type", "activation_criteria"]
  properties:
    protocol_id:
      type: string
      pattern: "^emergency_[a-z0-9_]+$"
    protocol_name:
      type: string
      description: "Human-readable protocol name"
    emergency_type:
      type: string
      enum: ["medical", "safety", "security", "natural_disaster", "family_crisis", "technology_failure"]
    severity_level:
      type: string
      enum: ["low", "medium", "high", "critical"]
    activation_criteria:
      type: object
      properties:
        automatic_triggers:
          type: array
          items:
            type: string
          description: "Conditions that automatically activate protocol"
        manual_activation_authorized:
          type: array
          items:
            type: string
          description: "Family members authorized for manual activation"
        activation_keywords:
          type: array
          items:
            type: string
          description: "Voice keywords that trigger activation"
    response_procedures:
      type: object
      properties:
        immediate_actions:
          type: array
          items:
            type: object
            properties:
              action_sequence:
                type: integer
              action_description:
                type: string
              responsible_party:
                type: string
                enum: ["system", "family_member", "external_contact", "emergency_services"]
              action_timeout:
                type: integer
                description: "Seconds to complete action"
        family_notification:
          type: object
          properties:
            notification_method:
              type: array
              items:
                type: string
                enum: ["push_notification", "voice_announcement", "text_message", "phone_call", "email"]
            notification_message:
              type: string
            family_members_to_notify:
              type: array
              items:
                type: string
            notification_priority:
              type: string
              enum: ["low", "normal", "high", "critical"]
        external_contacts:
          type: array
          items:
            type: object
            properties:
              contact_type:
                type: string
                enum: ["emergency_services", "family_friend", "medical_professional", "school", "workplace"]
              contact_name:
                type: string
              contact_phone:
                type: string
              contact_email:
                type: string
              when_to_contact:
                type: string
                enum: ["immediately", "after_family_notification", "if_no_family_response", "escalation_only"]
              contact_priority:
                type: integer
                minimum: 1
                maximum: 10
    family_roles:
      type: object
      description: "Specific responsibilities for family members during emergency"
      additionalProperties:
        type: object
        properties:
          primary_responsibilities:
            type: array
            items:
              type: string
          backup_responsibilities:
            type: array
            items:
              type: string
          location_during_emergency:
            type: string
          communication_requirements:
            type: array
            items:
              type: string
    resource_requirements:
      type: array
      items:
        type: object
        properties:
          resource_type:
            type: string
            enum: ["physical_item", "information", "access_code", "contact", "location"]
          resource_name:
            type: string
          resource_location:
            type: string
          responsible_family_member:
            type: string
    testing_schedule:
      type: object
      properties:
        test_frequency:
          type: string
          enum: ["weekly", "monthly", "quarterly", "annually"]
        last_test_date:
          type: string
          format: date-time
        next_test_date:
          type: string
          format: date-time
        test_results:
          type: array
          items:
            type: object
            properties:
              test_date:
                type: string
                format: date-time
              test_success:
                type: boolean
              issues_identified:
                type: array
                items:
                  type: string
              family_feedback:
                type: string
```

## Subscription Management Types

### FamilyPlan
```yaml
FamilyPlan:
  type: object
  required: ["plan_id", "plan_name", "plan_category", "pricing"]
  properties:
    plan_id:
      type: string
      pattern: "^plan_[a-z0-9_]+$"
    plan_name:
      type: string
      description: "Marketing name for family plan"
    plan_category:
      type: string
      enum: ["basic", "standard", "premium", "enterprise", "trial"]
    plan_description:
      type: string
      maxLength: 500
    pricing:
      type: object
      properties:
        monthly_price:
          type: number
          minimum: 0
          description: "Monthly price in plan currency"
        annual_price:
          type: number
          minimum: 0
          description: "Annual price in plan currency"
        currency:
          type: string
          enum: ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"]
        promotional_pricing:
          type: object
          properties:
            promotional_monthly:
              type: number
            promotional_annual:
              type: number
            promotion_end_date:
              type: string
              format: date-time
            promotion_description:
              type: string
    family_limits:
      type: object
      properties:
        max_family_members:
          type: integer
          minimum: 1
          maximum: 50
        max_devices:
          type: integer
          minimum: 1
          maximum: 200
        max_concurrent_sessions:
          type: integer
          minimum: 1
    memory_allocation:
      type: object
      properties:
        storage_per_member_gb:
          type: number
          minimum: 0
        total_family_storage_gb:
          type: number
          minimum: 0
        memory_retention_period:
          type: string
          enum: ["6_months", "1_year", "3_years", "indefinite"]
        cross_domain_intelligence:
          type: string
          enum: ["basic", "standard", "advanced", "premium"]
    ai_capabilities:
      type: object
      properties:
        monthly_ai_interactions:
          type: integer
          minimum: 0
          description: "0 means unlimited"
        ai_response_priority:
          type: string
          enum: ["standard", "priority", "premium"]
        emotional_intelligence_level:
          type: string
          enum: ["basic", "standard", "enhanced", "maximum"]
        family_coordination_features:
          type: string
          enum: ["basic", "standard", "advanced", "premium"]
        predictive_capabilities:
          type: boolean
    support_level:
      type: object
      properties:
        support_channels:
          type: array
          items:
            type: string
            enum: ["email", "chat", "phone", "video_call", "in_person"]
        response_time_sla:
          type: string
          enum: ["72_hours", "24_hours", "4_hours", "1_hour", "immediate"]
        dedicated_support_agent:
          type: boolean
        family_training_included:
          type: boolean
        setup_assistance:
          type: boolean
    security_features:
      type: object
      properties:
        encryption_level:
          type: string
          enum: ["standard", "enhanced", "military_grade"]
        privacy_controls:
          type: string
          enum: ["basic", "standard", "advanced", "maximum"]
        audit_logging:
          type: boolean
        compliance_certifications:
          type: array
          items:
            type: string
            enum: ["coppa", "gdpr", "ccpa", "hipaa", "ferpa"]
    integration_capabilities:
      type: object
      properties:
        supported_integrations:
          type: array
          items:
            type: string
        custom_integration_support:
          type: boolean
        api_access:
          type: string
          enum: ["none", "read_only", "full_access", "premium_api"]
        third_party_data_export:
          type: boolean
```

### BillingAccount
```yaml
BillingAccount:
  type: object
  required: ["account_id", "family_id", "billing_status"]
  properties:
    account_id:
      type: string
      pattern: "^billing_[a-z0-9_]+$"
    family_id:
      type: string
    billing_status:
      type: string
      enum: ["active", "suspended", "delinquent", "cancelled", "trial"]
    current_plan:
      type: object
      properties:
        plan_id:
          type: string
        subscription_start:
          type: string
          format: date-time
        next_billing_date:
          type: string
          format: date-time
        billing_cycle:
          type: string
          enum: ["monthly", "annual"]
        auto_renewal:
          type: boolean
          default: true
    payment_methods:
      type: array
      items:
        type: object
        properties:
          payment_method_id:
            type: string
          method_type:
            type: string
            enum: ["credit_card", "debit_card", "bank_account", "digital_wallet", "family_account"]
          is_primary:
            type: boolean
          masked_details:
            type: string
            description: "Masked payment details for family display"
          expiry_date:
            type: string
            format: date
            description: "For cards only"
          billing_address:
            type: object
            properties:
              street:
                type: string
              city:
                type: string
              state:
                type: string
              postal_code:
                type: string
              country:
                type: string
          status:
            type: string
            enum: ["active", "expired", "suspended", "verification_required"]
    billing_preferences:
      type: object
      properties:
        invoice_delivery:
          type: string
          enum: ["email", "postal_mail", "family_app_only"]
        invoice_email:
          type: string
          format: email
        payment_reminders:
          type: boolean
          default: true
        budget_alerts:
          type: boolean
          default: true
        family_spending_notifications:
          type: boolean
          default: false
        currency_preference:
          type: string
          enum: ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"]
    usage_tracking:
      type: object
      properties:
        current_month_usage:
          type: object
        billing_period_usage:
          type: object
        usage_alerts_enabled:
          type: boolean
        usage_limit_notifications:
          type: boolean
```

## System Monitoring Types

### SystemHealthStatus
```yaml
SystemHealthStatus:
  type: object
  required: ["component", "status", "last_check"]
  properties:
    component:
      type: string
      enum: ["memory_system", "ai_coordination", "device_sync", "family_coordination", "emergency_protocols", "billing_system", "security_system"]
    status:
      type: string
      enum: ["healthy", "warning", "degraded", "critical", "offline"]
    health_score:
      type: number
      minimum: 0
      maximum: 1
      description: "Normalized health score (0-1)"
    last_check:
      type: string
      format: date-time
    status_details:
      type: object
      properties:
        performance_metrics:
          type: object
        error_count_24h:
          type: integer
        warning_count_24h:
          type: integer
        uptime_percentage:
          type: number
          minimum: 0
          maximum: 100
    recommendations:
      type: array
      items:
        type: object
        properties:
          recommendation_type:
            type: string
            enum: ["maintenance", "configuration", "upgrade", "family_action"]
          description:
            type: string
          urgency:
            type: string
            enum: ["low", "medium", "high", "critical"]
          family_impact:
            type: string
            enum: ["none", "minimal", "moderate", "significant"]
```

## Privacy and Security Types

### PrivacySettings
```yaml
PrivacySettings:
  type: object
  properties:
    family_privacy_level:
      type: string
      enum: ["open", "moderate", "strict", "maximum"]
      description: "Overall family privacy stance"
    data_minimization:
      type: object
      properties:
        collect_only_necessary:
          type: boolean
          default: true
        automatic_deletion:
          type: boolean
          default: false
        deletion_schedule:
          type: string
          enum: ["30_days", "90_days", "1_year", "3_years", "manual_only"]
    sharing_preferences:
      type: object
      properties:
        default_memory_space:
          type: string
          enum: ["personal", "selective", "shared", "extended"]
        external_sharing_default:
          type: string
          enum: ["never", "ask_each_time", "family_approved", "automatic_limited"]
        analytics_sharing:
          type: boolean
          default: false
          description: "Share anonymized analytics for service improvement"
        research_participation:
          type: boolean
          default: false
          description: "Participate in family AI research (anonymized)"
    child_protection:
      type: object
      properties:
        enhanced_child_privacy:
          type: boolean
          default: true
        parental_oversight_level:
          type: string
          enum: ["minimal", "moderate", "comprehensive", "maximum"]
        child_data_special_protection:
          type: boolean
          default: true
        educational_content_preference:
          type: string
          enum: ["unrestricted", "age_appropriate", "curated", "family_approved"]
    audit_and_transparency:
      type: object
      properties:
        activity_logging:
          type: boolean
          default: true
        family_access_logs:
          type: boolean
          default: true
        data_usage_reports:
          type: string
          enum: ["never", "monthly", "weekly", "real_time"]
        transparency_notifications:
          type: boolean
          default: true
```

## Common Response Types

### APIResponse
```yaml
APIResponse:
  type: object
  required: ["success", "timestamp"]
  properties:
    success:
      type: boolean
    timestamp:
      type: string
      format: date-time
    request_id:
      type: string
      description: "Unique request identifier for tracking"
    family_id:
      type: string
      description: "Family identifier (when applicable)"
    message:
      type: string
      description: "Human-readable response message"
    family_impact_summary:
      type: object
      properties:
        impact_level:
          type: string
          enum: ["none", "minimal", "moderate", "significant"]
        affected_family_members:
          type: array
          items:
            type: string
        coordination_required:
          type: boolean
        family_notification_sent:
          type: boolean
```

### ErrorResponse
```yaml
ErrorResponse:
  type: object
  required: ["error", "error_code", "timestamp"]
  properties:
    error:
      type: string
      description: "Human-readable error message"
    error_code:
      type: string
      pattern: "^[A-Z_]+$"
      description: "Machine-readable error code"
    timestamp:
      type: string
      format: date-time
    request_id:
      type: string
    family_id:
      type: string
    error_details:
      type: object
      properties:
        field_errors:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              error:
                type: string
        validation_errors:
          type: array
          items:
            type: string
        system_context:
          type: object
    resolution_suggestions:
      type: array
      items:
        type: object
        properties:
          suggestion:
            type: string
          action_required:
            type: string
            enum: ["user_action", "family_approval", "contact_support", "wait_and_retry"]
    family_impact:
      type: object
      properties:
        service_disruption:
          type: boolean
        affected_features:
          type: array
          items:
            type: string
        family_notification_required:
          type: boolean
```

## Validation Patterns

### Common Validation Rules
- **family_id**: `^family_[a-z0-9]{8,16}$`
- **member_id**: `^member_[a-z0-9]{8,16}$`
- **device_id**: `^device_[a-z0-9]{8,16}$`
- **plan_id**: `^plan_[a-z0-9_]+$`
- **emergency_protocol_id**: `^emergency_[a-z0-9_]+$`
- **phone_number**: `^\+?[1-9]\d{1,14}$` (E.164 format)
- **email**: Standard email validation with family domain restrictions
- **currency_amount**: Positive number with up to 2 decimal places

### Security Validation
- All family-related operations require family context validation
- Child-related operations require additional parental approval verification
- Emergency operations may bypass normal validation with audit logging
- Privacy-sensitive operations require explicit consent validation
