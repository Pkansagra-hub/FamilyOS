# Agent Plane API - cURL Examples
# Memory-Centric Family AI - Agent Plane cURL Examples

## Environment Setup
export FAMILY_API_BASE="http://localhost:8000"
export FAMILY_API_TOKEN="your_jwt_token_here"

## 1. Submit a Family Memory

### Basic family conversation memory
curl -X POST "${FAMILY_API_BASE}/v1/memory/submit" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "Emma mentioned she has a soccer practice on Wednesday at 4 PM. She needs her cleats and water bottle.",
      "metadata": {
        "content_type": "conversation",
        "importance": 0.8,
        "tags": ["soccer", "schedule", "emma", "sports"]
      }
    },
    "context": {
      "space_id": "shared:household",
      "family_context": {
        "participants": ["fam_mom_001", "fam_emma_003"],
        "relationship_type": "parent-child"
      },
      "temporal_context": {
        "timestamp": "2025-09-21T14:30:00Z",
        "recurrence": "weekly"
      },
      "emotional_context": {
        "valence": 0.7,
        "arousal": 0.4,
        "dominant_emotion": "neutral"
      }
    },
    "options": {
      "privacy_level": "GREEN",
      "retention_policy": "standard"
    }
  }'

### Personal reflection memory
curl -X POST "${FAMILY_API_BASE}/v1/memory/submit" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "I felt really proud when Emma scored her first goal today. She has been practicing so hard.",
      "metadata": {
        "content_type": "reflection",
        "importance": 0.9,
        "tags": ["pride", "emma", "soccer", "achievement", "parenting"]
      }
    },
    "context": {
      "space_id": "personal:mom_private",
      "family_context": {
        "participants": ["fam_mom_001"],
        "relationship_type": "parent-child"
      },
      "temporal_context": {
        "timestamp": "2025-09-21T16:45:00Z"
      },
      "emotional_context": {
        "valence": 0.9,
        "arousal": 0.6,
        "dominant_emotion": "joy"
      }
    },
    "options": {
      "privacy_level": "AMBER",
      "retention_policy": "extended"
    }
  }'

### Important family goal memory
curl -X POST "${FAMILY_API_BASE}/v1/memory/submit" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "Family goal: Save $5000 for summer vacation to Europe. Everyone contributes by reducing entertainment expenses by 20%.",
      "metadata": {
        "content_type": "goal",
        "importance": 1.0,
        "tags": ["family-goal", "vacation", "savings", "europe", "budget"]
      }
    },
    "context": {
      "space_id": "shared:household",
      "family_context": {
        "participants": ["fam_mom_001", "fam_dad_002", "fam_emma_003", "fam_tommy_004"],
        "relationship_type": "family-group"
      },
      "temporal_context": {
        "timestamp": "2025-09-21T19:00:00Z"
      }
    },
    "options": {
      "force_consolidation": true,
      "privacy_level": "GREEN",
      "retention_policy": "permanent"
    }
  }'

## 2. Recall Family Memories

### Find memories about Emma's soccer
curl -X POST "${FAMILY_API_BASE}/v1/memory/recall" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "text": "When is Emma'\''s soccer practice this week?",
      "query_type": "semantic",
      "filters": {
        "participants": ["fam_emma_003"],
        "tags": ["soccer"],
        "content_types": ["conversation", "observation"]
      }
    },
    "context": {
      "space_id": "shared:household",
      "requester_id": "fam_dad_002"
    },
    "options": {
      "max_results": 5,
      "similarity_threshold": 0.7,
      "include_context": true
    }
  }'

### Recall recent family conversations
curl -X POST "${FAMILY_API_BASE}/v1/memory/recall" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "text": "What did we discuss about vacation plans?",
      "query_type": "temporal",
      "filters": {
        "time_range": {
          "start": "2025-09-15T00:00:00Z",
          "end": "2025-09-21T23:59:59Z"
        },
        "tags": ["vacation", "family-goal"],
        "importance_threshold": 0.6
      }
    },
    "context": {
      "space_id": "shared:household",
      "requester_id": "fam_mom_001",
      "family_context": {
        "relationship_to_content": "participant"
      }
    },
    "options": {
      "max_results": 10,
      "privacy_mode": "full"
    }
  }'

### Emotional context search
curl -X POST "${FAMILY_API_BASE}/v1/memory/recall" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "text": "Times when Emma felt proud or accomplished",
      "query_type": "emotional",
      "filters": {
        "participants": ["fam_emma_003"],
        "time_range": {
          "start": "2025-09-01T00:00:00Z",
          "end": "2025-09-21T23:59:59Z"
        }
      }
    },
    "context": {
      "space_id": "shared:household",
      "requester_id": "fam_mom_001"
    },
    "options": {
      "max_results": 8,
      "similarity_threshold": 0.6,
      "privacy_mode": "summary"
    }
  }'

## 3. Chat Completions with Memory Context

### Family coordination chat
curl -X POST "${FAMILY_API_BASE}/v1/chat/completions" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Help me plan the logistics for Emma'\''s soccer practice this week"
      }
    ],
    "memory_context": {
      "include_family_memories": true,
      "space_ids": ["shared:household"],
      "max_context_memories": 10
    },
    "family_context": {
      "requester_id": "fam_dad_002",
      "participants": ["fam_emma_003"]
    },
    "options": {
      "temperature": 0.7,
      "max_tokens": 500,
      "stream": false
    }
  }'

### Personal advice with emotional awareness
curl -X POST "${FAMILY_API_BASE}/v1/chat/completions" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "I'\''m feeling overwhelmed with balancing work and family time. Can you help?"
      }
    ],
    "memory_context": {
      "include_family_memories": true,
      "space_ids": ["personal:mom_private", "shared:household"],
      "max_context_memories": 15,
      "emotional_context_weight": 0.8
    },
    "family_context": {
      "requester_id": "fam_mom_001"
    },
    "options": {
      "temperature": 0.6,
      "max_tokens": 800,
      "empathy_mode": true
    }
  }'

## 4. Affect Analysis

### Analyze text for emotional content
curl -X POST "${FAMILY_API_BASE}/v1/affect/analyze" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "I'\''m so frustrated! Emma forgot her soccer cleats again and now we'\''re running late for practice!",
      "content_type": "conversation"
    },
    "context": {
      "family_member_id": "fam_mom_001",
      "situation": "family_coordination",
      "participants": ["fam_mom_001", "fam_emma_003"]
    },
    "analysis_options": {
      "include_family_impact": true,
      "suggest_responses": true,
      "emotional_regulation": true
    }
  }'

### Analyze family conversation dynamics
curl -X POST "${FAMILY_API_BASE}/v1/affect/analyze" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "Family dinner conversation about screen time limits",
      "content_type": "conversation",
      "context_memories": ["mem_abc123", "mem_def456"]
    },
    "context": {
      "family_member_id": "fam_dad_002",
      "situation": "family_meeting",
      "participants": ["fam_mom_001", "fam_dad_002", "fam_emma_003", "fam_tommy_004"]
    },
    "analysis_options": {
      "family_dynamics_analysis": true,
      "conflict_detection": true,
      "harmony_suggestions": true
    }
  }'

## Error Handling Examples

### Invalid memory space
curl -X POST "${FAMILY_API_BASE}/v1/memory/submit" \
  -H "Authorization: Bearer ${FAMILY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "Test memory"
    },
    "context": {
      "space_id": "invalid:space"
    }
  }'
# Expected: 400 Bad Request with validation_error

### Unauthorized access
curl -X POST "${FAMILY_API_BASE}/v1/memory/recall" \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "text": "test query"
    },
    "context": {
      "space_id": "shared:household"
    }
  }'
# Expected: 401 Unauthorized with authentication_error
