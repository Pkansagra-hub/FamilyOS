#!/bin/bash

# Control Plane API Examples - Memory-Centric Family AI
# Family governance, subscription management, and system oversight

BASE_URL="http://localhost:8000/v1"
FAMILY_ID="family_demo_12345"
ADMIN_TOKEN="demo_admin_token"

echo "=== Family Administration Examples ==="

# 1. Add new family member with democratic approval
echo "Adding new family member..."
curl -X POST "$BASE_URL/control/admin/family-members" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "add_family_member",
    "family_context": {
      "family_id": "'$FAMILY_ID'",
      "requesting_member_id": "parent_alice_001",
      "democratic_approval_status": {
        "approval_required": true,
        "approval_votes": [
          {
            "member_id": "parent_alice_001",
            "vote": "approve",
            "timestamp": "2024-01-15T10:00:00Z"
          },
          {
            "member_id": "parent_bob_002",
            "vote": "approve",
            "timestamp": "2024-01-15T10:05:00Z"
          }
        ]
      }
    },
    "operation_details": {
      "new_member": {
        "name": "Emma Johnson",
        "age": 8,
        "role": "child_member",
        "permissions": [
          {
            "permission_id": "child_basic_interaction",
            "permission_name": "Basic Child Interaction",
            "description": "Age-appropriate AI interaction for children",
            "child_safety_level": "safe",
            "required_family_approval": false
          }
        ]
      }
    },
    "memory_integration": {
      "memory_space_impact": ["shared", "extended"],
      "memory_preservation_required": true,
      "memory_access_changes": {
        "child_memory_access": "age_appropriate_only",
        "parental_oversight": "required"
      }
    },
    "child_safety_considerations": {
      "child_impact_assessment": "Positive - adds child to family AI with appropriate protections",
      "parental_oversight_changes": ["enhanced_monitoring", "content_filtering"],
      "age_appropriate_notifications": true
    }
  }'

echo -e "\n\n=== Family Policy Management ==="

# 2. Create family privacy policy
echo "Creating family privacy policy..."
curl -X POST "$BASE_URL/control/admin/policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "create_family_policy",
    "family_context": {
      "family_id": "'$FAMILY_ID'",
      "requesting_member_id": "parent_alice_001"
    },
    "operation_details": {
      "policy": {
        "policy_id": "family_privacy_v1",
        "policy_name": "Family Privacy Protection Policy",
        "policy_description": "Comprehensive privacy protection for all family members with enhanced child protection",
        "memory_integration": {
          "memory_space_scope": ["personal", "selective", "shared"],
          "memory_access_controls": {
            "child_memory_isolation": true,
            "parental_oversight_required": true,
            "automatic_pii_redaction": true
          },
          "memory_retention_rules": {
            "child_data_retention_days": 30,
            "adult_data_retention_days": 365,
            "automatic_deletion_enabled": true
          }
        },
        "family_safety_enforcement": {
          "child_protection_rules": [
            "no_personal_information_sharing",
            "content_filtering_mandatory",
            "parental_approval_for_external_communication"
          ],
          "parental_oversight_requirements": [
            "daily_activity_summaries",
            "weekly_safety_reports",
            "immediate_alert_on_concerns"
          ],
          "emergency_override_conditions": [
            "immediate_child_safety_threat",
            "family_security_incident"
          ]
        },
        "democratic_approval": {
          "requires_family_vote": true,
          "minimum_approval_threshold": 0.75,
          "age_weighted_voting": true,
          "policy_education_required": true
        }
      }
    }
  }'

echo -e "\n\n=== Subscription Management ==="

# 3. Check family subscription status
echo "Checking family subscription..."
curl -X GET "$BASE_URL/control/subscriptions/status?family_id=$FAMILY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 4. Update subscription tier
echo -e "\n\nUpdating subscription tier..."
curl -X PUT "$BASE_URL/control/subscriptions/tier" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "family_id": "'$FAMILY_ID'",
    "new_tier": {
      "tier_id": "family_premium",
      "tier_name": "Family Premium",
      "family_size_limit": 8,
      "device_limit": 20,
      "memory_capacity": {
        "family_memory_limit_gb": 100,
        "memory_retention_days": 730,
        "cross_device_sync": true
      },
      "family_features": {
        "advanced_emotional_intelligence": true,
        "multi_generational_support": true,
        "professional_family_coordination": true,
        "enhanced_child_protection": true,
        "family_analytics_insights": true
      },
      "pricing": {
        "monthly_price_usd": 29.99,
        "annual_discount_percentage": 20,
        "family_transparency": {
          "no_hidden_fees": true,
          "family_budget_controls": true,
          "billing_transparency": true
        }
      }
    },
    "family_approval": {
      "approved_by_family": true,
      "approval_timestamp": "2024-01-15T14:30:00Z",
      "budget_impact_acknowledged": true
    }
  }'

echo -e "\n\n=== System Oversight ==="

# 5. Get system health metrics
echo "Getting system health metrics..."
curl -X GET "$BASE_URL/control/system/health?family_id=$FAMILY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 6. Get family experience metrics
echo -e "\n\nGetting family experience metrics..."
curl -X GET "$BASE_URL/control/system/metrics/family-experience?family_id=$FAMILY_ID&period=7d" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

echo -e "\n\n=== Emergency Protocols ==="

# 7. Test emergency response system
echo "Testing emergency response (simulation)..."
curl -X POST "$BASE_URL/control/emergency/test" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "initiate_emergency_protocol",
    "family_context": {
      "family_id": "'$FAMILY_ID'",
      "requesting_member_id": "system_monitor"
    },
    "operation_details": {
      "emergency_type": "child_safety",
      "severity": "medium",
      "immediate_action_required": false
    },
    "simulation_mode": true,
    "test_protocols": [
      "family_notification_system",
      "child_protection_activation",
      "parental_alert_mechanisms",
      "system_isolation_procedures"
    ]
  }'

echo -e "\n\n=== Family Governance Dashboard ==="

# 8. Get family governance overview
echo "Getting family governance overview..."
curl -X GET "$BASE_URL/control/governance/overview?family_id=$FAMILY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 9. Get democratic decision history
echo -e "\n\nGetting democratic decision history..."
curl -X GET "$BASE_URL/control/governance/decisions?family_id=$FAMILY_ID&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

echo -e "\n\n=== Memory System Administration ==="

# 10. Get family memory administration overview
echo "Getting family memory administration overview..."
curl -X GET "$BASE_URL/control/memory/administration?family_id=$FAMILY_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 11. Validate memory space configurations
echo -e "\n\nValidating memory space configurations..."
curl -X POST "$BASE_URL/control/memory/validate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "family_id": "'$FAMILY_ID'",
    "validation_scope": "all_memory_spaces",
    "include_privacy_validation": true,
    "include_child_safety_validation": true,
    "include_cross_device_sync_validation": true
  }'

echo -e "\n\nControl Plane API examples completed!"
echo "These examples demonstrate:"
echo "- Democratic family administration with approval processes"
echo "- Family policy creation and management"
echo "- Transparent subscription management with budget controls"
echo "- Comprehensive system oversight and monitoring"
echo "- Emergency protocols with family protection"
echo "- Family governance and democratic decision-making"
echo "- Memory system administration with privacy protection"
