#!/usr/bin/env python3
"""
Retrieval Service Foundation Contracts Validation
Validates that Policy Contracts and Type System work together correctly
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add retrieval module to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from retrieval.types import (
    PolicyContext,
    PolicyDecision,
    QoSBudget,
    RetrievalFilters,
    RetrievalOperation,
    RetrievalRequest,
    SecurityBand,
    SpaceType,
    parse_filters_from_dict,
    validate_space_id,
)


def validate_policy_integration():
    """Validate that policy contracts integrate with type system"""
    print("🔍 Validating Policy Integration...")

    # Test PolicyContext creation with comprehensive filters
    context = PolicyContext(
        user_id="alice",
        role="memory_analyst",
        operation=RetrievalOperation.READ,
        space_id="shared:research_team",
        clearance_level=3,
        department="Research",
        requested_bands=[SecurityBand.GREEN, SecurityBand.AMBER, SecurityBand.RED],
        timestamp=datetime.now(),
        qos_budget=500,
        content_types=["text", "document"],
        space_types=[SpaceType.SHARED, SpaceType.EXTENDED],
        temporal_range_days=90,
        quality_requirements={"min_quality_score": 0.8},
        business_hours_only=False,
    )

    policy_input = context.to_policy_input()
    assert "filters" in policy_input
    assert "bands" in policy_input["filters"]
    assert policy_input["filters"]["bands"] == ["GREEN", "AMBER", "RED"]
    assert policy_input["filters"]["content_types"] == ["text", "document"]
    assert policy_input["context"]["temporal_range_days"] == 90

    print("✅ Policy context integration validated")


def validate_filter_types():
    """Validate comprehensive filter types"""
    print("🔍 Validating Filter Types...")

    # Test comprehensive filter creation
    filters = RetrievalFilters(
        after=datetime.now() - timedelta(days=30),
        before=datetime.now(),
        topics=["machine_learning", "research"],
        exclude_topics=["sensitive"],
        topic_logic="OR",
        bands=[SecurityBand.GREEN, SecurityBand.AMBER],
        max_band=SecurityBand.RED,
        space_types=[SpaceType.SHARED, SpaceType.EXTENDED],
        space_ids=["shared:research_team"],
        owner_filter="include_shared",
        content_types=["text", "document"],
        languages=["en", "es"],
        min_quality_score=0.7,
        exclude_duplicates=True,
    )

    # Test filter validation
    try:
        # This should fail - topics and exclude_topics overlap
        RetrievalFilters(topics=["test"], exclude_topics=["test"])
        assert False, "Should have failed on topic overlap"
    except ValueError:
        pass  # Expected

    # Test filter serialization
    filter_dict = filters.to_dict()
    assert "topics" in filter_dict
    assert "bands" in filter_dict
    assert filter_dict["bands"] == ["GREEN", "AMBER"]
    assert filter_dict["max_band"] == "RED"
    # topic_logic is "OR" which is default, so it may not be in dict
    if "topic_logic" in filter_dict:
        assert filter_dict["topic_logic"] == "OR"

    print("✅ Filter types validation passed")


def validate_qos_types():
    """Validate QoS budget types"""
    print("🔍 Validating QoS Types...")

    # Test QoS budget creation
    qos = QoSBudget(
        latency_budget_ms=1000,
        priority=7,
        max_results=100,
        allow_partial=True,
        timeout_behavior="graceful",
        mode="sync",
        ranking_profile="research_focused",
    )

    qos_dict = qos.to_dict()
    assert qos_dict["latency_budget_ms"] == 1000
    assert qos_dict["mode"] == "sync"
    assert qos_dict["ranking_profile"] == "research_focused"

    # Test validation
    try:
        QoSBudget(latency_budget_ms=10000)  # Too high
        assert False, "Should have failed on high latency"
    except ValueError:
        pass  # Expected

    print("✅ QoS types validation passed")


def validate_request_response_types():
    """Validate request and response types"""
    print("🔍 Validating Request/Response Types...")

    # Test comprehensive request creation
    request = RetrievalRequest(
        query="machine learning research papers",
        space_id="shared:research_team",
        k=50,
        filters=RetrievalFilters(
            topics=["machine_learning"],
            bands=[SecurityBand.GREEN, SecurityBand.AMBER],
            space_types=[SpaceType.SHARED],
        ),
        return_trace=True,
        qos=QoSBudget(latency_budget_ms=800, priority=6, mode="sync"),
    )

    # Test API serialization
    api_dict = request.to_api_dict()
    assert api_dict["query"] == "machine learning research papers"
    assert api_dict["k"] == 50
    assert "filters" in api_dict
    assert "qos" in api_dict
    assert api_dict["qos"]["latency_budget_ms"] == 800

    print("✅ Request/Response types validation passed")


def validate_filter_parsing():
    """Validate filter parsing from API dictionaries"""
    print("🔍 Validating Filter Parsing...")

    # Test comprehensive filter parsing
    filter_data = {
        "after": "2025-09-01T00:00:00Z",
        "before": "2025-09-16T23:59:59Z",
        "within_days": 7,
        "topics": ["machine_learning", "research"],
        "exclude_topics": ["sensitive"],
        "topic_logic": "AND",
        "bands": ["GREEN", "AMBER"],
        "max_band": "RED",
        "min_band": "GREEN",
        "space_types": ["shared", "extended"],
        "space_ids": ["shared:research_team"],
        "owner_filter": "include_shared",
        "content_types": ["text", "document"],
        "languages": ["en", "es"],
        "min_content_length": 100,
        "max_content_length": 10000,
        "has_attachments": True,
        "min_quality_score": 0.8,
        "min_relevance_score": 0.7,
        "exclude_duplicates": True,
        "min_engagement": 5,
    }

    # Test conflicting temporal filters
    try:
        RetrievalFilters(
            after=datetime.now() - timedelta(days=30), within_days=7  # Conflict!
        )
        assert False, "Should have failed on conflicting temporal filters"
    except ValueError:
        pass  # Expected

    # Test valid parsing (remove within_days conflict)
    del filter_data["within_days"]  # Remove conflict
    filters = parse_filters_from_dict(filter_data)

    assert filters.topics == ["machine_learning", "research"]
    assert filters.bands == [SecurityBand.GREEN, SecurityBand.AMBER]
    assert filters.max_band == SecurityBand.RED
    assert filters.space_types == [SpaceType.SHARED, SpaceType.EXTENDED]
    assert filters.content_types == ["text", "document"]
    assert filters.min_quality_score == 0.8

    print("✅ Filter parsing validation passed")


def validate_space_id_utility():
    """Validate space ID utility functions"""
    print("🔍 Validating Space ID Utilities...")

    try:
        # Test valid space IDs
        assert validate_space_id("personal:alice_workspace")
        assert validate_space_id("shared:research_team")
        assert validate_space_id("extended:family_vault")
        assert validate_space_id("interfamily:extended_network")

        # Test invalid space IDs
        assert not validate_space_id("invalid:space")
        assert not validate_space_id("no_colon_here")
        assert not validate_space_id("")
        assert not validate_space_id("personal:")  # Empty identifier

        print("✅ Space ID utilities validation passed")
    except Exception as e:
        print(f"❌ Space ID validation failed: {e}")
        raise


def validate_policy_decision_types():
    """Validate policy decision types and constraints"""
    print("🔍 Validating Policy Decision Types...")

    # Test policy decision with comprehensive constraints
    decision = PolicyDecision(
        decision="PERMIT",
        reasons=["User has required clearance", "Space access granted"],
        constraints={
            "max_results": 100,
            "allowed_bands": ["GREEN", "AMBER", "RED"],
            "temporal": {"max_days_back": 365, "business_hours_only": False},
            "space": {
                "allowed_types": ["shared", "extended"],
                "owner_restrictions": False,
            },
            "quality": {"min_score": 0.6},
        },
        policy_version="2.0.0",
        evaluation_time_ms=15.5,
        applied_rules=["clearance_check", "space_access", "time_bounds"],
    )

    # Test property accessors
    assert decision.is_permitted
    assert decision.max_results == 100
    assert decision.allowed_bands == [
        SecurityBand.GREEN,
        SecurityBand.AMBER,
        SecurityBand.RED,
    ]

    # Test constraint accessors
    time_constraints = decision.time_constraints
    assert time_constraints["max_days_back"] == 365

    space_constraints = decision.space_constraints
    assert space_constraints["allowed_types"] == ["shared", "extended"]

    # Test custom constraint getter
    assert decision.get_constraint("quality", {})["min_score"] == 0.6
    assert decision.get_constraint("nonexistent", "default") == "default"

    print("✅ Policy decision types validation passed")


def main():
    """Run all foundation contract validations"""
    print("🚀 Starting Retrieval Foundation Contracts Validation")
    print("=" * 60)

    try:
        validate_policy_integration()
        validate_filter_types()
        validate_qos_types()
        validate_request_response_types()
        validate_filter_parsing()
        validate_space_id_utility()
        validate_policy_decision_types()

        print("=" * 60)
        print("✅ ALL FOUNDATION CONTRACT VALIDATIONS PASSED!")
        print("🎯 Policy contracts and type system integration confirmed")
        print("📋 MILESTONE 1 (Foundation Contracts) - COMPLETE")
        return True

    except Exception as e:
        print("=" * 60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("📋 MILESTONE 1 (Foundation Contracts) - NEEDS FIXES")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
