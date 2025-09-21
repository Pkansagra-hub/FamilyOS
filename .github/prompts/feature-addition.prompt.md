````prompt# ✨ Feature Addition Prompts

# ✨ Feature Addition Prompts

Use these prompts when adding new features to ensure proper planning, implementation, and integration.

Use these prompts when adding new features to ensure proper planning, implementation, and integration following MemoryOS standards.

---

---

## 🎯 **Feature Planning Request**

## 🎯 **Feature Planning Request**

```

```I want to add a new feature to the system:

I want to add a new feature to the system:

**Feature Overview:**

**Feature Overview:**- **Feature Name:** [Descriptive name]

- **Feature Name:** [Specific feature name - avoid generic terms]- **Purpose:** [What problem it solves]

- **Purpose:** [Concrete problem it solves with measurable outcomes]- **Business Value:** [Why it's needed]

- **Business Value:** [Quantifiable benefit: reduce latency by 50%, increase throughput by 2x]- **Priority:** [High/Medium/Low]

- **Priority:** [Critical/High/Medium/Low with business justification]

**Requirements:**

**Requirements:**- **Functional Requirements:** [What it must do]

- **Functional Requirements:** [Specific capabilities: store 1M+ memories, retrieve in <100ms]- **Non-Functional Requirements:** [Performance/security/etc]

- **Non-Functional Requirements:** [Measurable: 99.9% uptime, <200ms p95 response time]- **User Experience:** [How users interact]

- **User Experience:** [Exact user flows: API endpoints, event notifications]- **Integration Requirements:** [How it fits in system]

- **Integration Requirements:** [Specific services: integrates with memory_steward, hippocampus]

**Scope Definition:**

**Scope Definition:**- **In Scope:** [What's included in this feature]

- **In Scope:** [Specific deliverables with acceptance criteria]- **Out of Scope:** [What's explicitly not included]

- **Out of Scope:** [Explicitly excluded features for future versions]- **Dependencies:** [What it depends on]

- **Dependencies:** [Exact services/APIs: requires memory_steward v2.1+, event_bus]- **Assumptions:** [What we're assuming]

- **Assumptions:** [Technical/business assumptions that could change scope]

**Architecture Impact:**

**Architecture Impact:**- **Affected Components:** [Services/modules impacted]

- **Affected Components:** [Exact modules: api/routers/memory.py, storage/memory_store.py]- **New Components:** [New services/modules needed]

- **New Components:** [Services/modules to create with brain region mapping]- **Integration Points:** [How it connects to existing]

- **Contract Changes:** [API/Event/Storage contracts requiring updates]- **Data Flow:** [How data moves through system]

- **Performance Impact:** [Expected resource usage: +20% CPU, +500MB memory]

**Technical Considerations:**

**Contract Requirements (Must Define First):**- **Performance Requirements:** [Speed/throughput needs]

- **API Changes:** [New endpoints: POST /api/v1/features, GET /api/v1/features/{id}]- **Security Requirements:** [Security implications]

- **Event Changes:** [New events: feature.created, feature.updated, feature.deleted]- **Scalability Needs:** [Growth expectations]

- **Storage Changes:** [New tables: features, feature_metadata with relationships]- **Monitoring Requirements:** [Observability needs]

- **Schema Updates:** [Existing schema modifications with migration plan]

**Success Criteria:**

**Quality Gates:**- **Acceptance Criteria:** [When is it done]

- [ ] All contracts defined and validated before implementation- **Performance Metrics:** [How to measure success]

- [ ] ≥95% test coverage including integration and performance tests- **User Adoption Metrics:** [Usage indicators]

- [ ] Security audit passed with proper RBAC/ABAC enforcement- **Business Metrics:** [Business impact measures]

- [ ] Performance benchmarks meet SLA requirements

- [ ] Documentation complete with API examples and user guidesPlease help me plan this feature with proper architecture and implementation strategy.

```

**Validation Commands:**

- [ ] `python contracts/automation/interactive_contract_builder.py` (create contracts)---

- [ ] `python contracts/automation/validation_helper.py --feature [feature-name]`

- [ ] `python -m ward test --path tests/component/test_[feature].py`## 🏗️ **Feature Implementation Request**

- [ ] `python -m pytest tests/performance/test_[feature]_performance.py`

- [ ] `python scripts/security/audit_feature.py [feature-name]````

I'm ready to implement a new feature. Please help me build it:

Please help me plan this feature with concrete specifications and measurable outcomes.

```**Feature Details:**

- **Feature Name:** [Name of feature]

---- **Target Components:** [Where it will be implemented]

- **Implementation Approach:** [How to build it]

## 🚀 **Feature Implementation Request**

**Contract Requirements:**

```- **API Changes:** [New endpoints/modifications needed]

I'm ready to implement a planned feature:- **Event Changes:** [New events/schema changes]

- **Storage Changes:** [New data/schema requirements]

**Feature Specification:**- **Version Impact:** [MAJOR/MINOR/PATCH implications]

- **Feature Name:** [validated feature name]

- **Contracts Status:** [all contracts defined and validated]**Implementation Plan:**

- **Architecture Tier:** [API/Events/Storage/Cognitive]- **Phase 1:** [Initial implementation scope]

- **Brain Region:** [hippocampus|cortex|cerebellum|etc.] (for cognitive features)- **Phase 2:** [Additional functionality]

- **Phase 3:** [Full feature completion]

**Implementation Plan:**- **Rollout Strategy:** [How to deploy safely]

- **New Files:** [Exact file paths to create]

  - `[service]/feature_[name].py` (main implementation)**Technical Implementation:**

  - `[service]/models/[feature]_models.py` (Pydantic models)- **New Code Required:** [Components to create]

  - `tests/component/test_[feature].py` (unit tests)- **Existing Code Changes:** [Components to modify]

  - `tests/integration/test_[feature]_integration.py` (integration tests)- **Configuration Changes:** [Settings/config updates]

- **Modified Files:** [Existing files to update with specific changes]- **Database Changes:** [Schema/data modifications]

- **Configuration:** [New environment variables, settings]

**Integration Points:**

**Implementation Patterns:**- **Service Integration:** [How it integrates with services]

- **Storage Integration:** [BaseStore extension, new tables, relationships]- **Event Integration:** [Event production/consumption]

- **Event Integration:** [EventBus handlers, event producers/consumers]- **Storage Integration:** [Data persistence patterns]

- **API Integration:** [New endpoints, middleware, validation]- **UI Integration:** [User interface changes]

- **Policy Integration:** [RBAC rules, space isolation, access controls]

**Quality Requirements:**

**Observability Requirements:**- **Testing Strategy:** [How to test the feature]

- **Metrics:** [Specific metrics: familyos_feature_operations_total, familyos_feature_response_seconds]- **Performance Validation:** [SLA compliance testing]

- **Traces:** [Span names: feature_service.create, feature_service.retrieve]- **Security Validation:** [Security testing approach]

- **Logs:** [Structured log events with correlation IDs]- **Documentation:** [What docs need updating]

- **Dashboards:** [Monitoring views for feature performance]

**Risk Mitigation:**

**Implementation Checklist:**- **Feature Flags:** [Gradual rollout approach]

- [ ] Create feature implementation following MemoryOS patterns- **Rollback Plan:** [How to disable if needed]

- [ ] Implement Pydantic models with contract validation- **Monitoring:** [How to track feature health]

- [ ] Add BaseStore integration for data persistence- **Error Handling:** [How to handle failures]

- [ ] Create event handlers for async processing

- [ ] Add API endpoints with proper middlewarePlease implement this feature following MemoryOS patterns and best practices.

- [ ] Implement policy enforcement at all entry points```

- [ ] Add comprehensive observability instrumentation

- [ ] Create test suite with ≥95% coverage---

- [ ] Validate all contracts with automation tools

- [ ] Performance test against SLA requirements## 🔌 **Feature Integration Request**



**Code Generation Commands:**```

```bashI need to integrate a new feature with existing systems:

# Generate feature scaffold

python scripts/feature/scaffold_feature.py [feature-name] --brain-region [region]**Feature Information:**

- **Feature Name:** [Name of feature]

# Generate contract templates- **Implementation Status:** [Development stage]

python contracts/automation/contract_suite.py generate --feature [feature-name]- **Core Functionality:** [What it does]



# Validate implementation**Integration Requirements:**

python contracts/automation/validation_helper.py --feature [feature-name]- **Upstream Dependencies:** [Services it needs]

python -m ward test --path tests/component/test_[feature].py- **Downstream Impact:** [Services that will use it]

```- **Data Integration:** [Shared data requirements]

- **Event Integration:** [Event flow requirements]

Please implement this feature following MemoryOS architecture standards.

```**API Integration:**

- **New Endpoints:** [APIs the feature provides]

---- **Endpoint Changes:** [Modified existing APIs]

- **Authentication:** [Auth requirements]

## 🔗 **Feature Integration Request**- **Rate Limiting:** [Performance constraints]



```**Event Integration:**

I need to integrate a new feature with existing MemoryOS components:- **Events Produced:** [Events feature generates]

- **Events Consumed:** [Events feature handles]

**Feature Details:**- **Event Routing:** [How events flow]

- **Feature Name:** [implemented feature name]- **Error Handling:** [Failed event processing]

- **Implementation Status:** [completed|tested|ready-for-integration]

- **Core Functionality:** [specific capabilities implemented]**Storage Integration:**

- **New Data Models:** [Data the feature stores]

**Integration Points:**- **Existing Data Usage:** [Data the feature reads]

- **API Integration:** [Endpoints to expose: GET /api/v1/[feature], POST /api/v1/[feature]]- **Data Consistency:** [Transaction requirements]

- **Event Integration:** [Events to publish/consume: [feature].created, memory.updated]- **Migration Strategy:** [Existing data handling]

- **Storage Integration:** [Database tables, foreign keys, indices]

- **Service Integration:** [Dependencies: memory_steward, hippocampus, policy]**Security Integration:**

- **Access Control:** [Who can use the feature]

**Integration Requirements:**- **Data Security:** [How data is protected]

- **Upstream Dependencies:** [Services this feature depends on]- **Audit Requirements:** [What to audit]

- **Downstream Consumers:** [Services that will use this feature]- **Compliance:** [Regulatory requirements]

- **Cross-Feature Impact:** [Existing features that need updates]

- **Data Migration:** [Schema changes, data transformation needs]**Testing Strategy:**

- **Feature Testing:** [Feature-specific tests]

**Testing Strategy:**- **Integration Testing:** [Cross-system tests]

- **Integration Tests:** [Cross-service API calls, event flows]- **Regression Testing:** [Existing functionality]

- **Performance Tests:** [End-to-end latency, throughput validation]- **Performance Testing:** [End-to-end SLA]

- **Contract Tests:** [Schema compliance, API compatibility]

- **Security Tests:** [RBAC enforcement, data access controls]Please help me integrate this feature safely with comprehensive validation.

```

**Deployment Strategy:**

- **Feature Flags:** [Gradual rollout controls, A/B testing]---

- **Configuration:** [Environment-specific settings]

- **Monitoring:** [Health checks, metrics, alerts]## 🚀 **Feature Deployment Request**

- **Rollback Plan:** [Disable procedures, data consistency]

```

**Integration Commands:**I'm ready to deploy a new feature. Help me prepare:

```bash

# Validate integration readiness**Feature Information:**

python contracts/automation/validation_helper.py --integration [feature-name]- **Feature Name:** [Name]

python -m ward test --path tests/integration/test_[feature]_integration.py- **Version:** [Version number]

- **Target Environment:** [Dev/Staging/Prod]

# Deploy with feature flags

python scripts/deployment/deploy_feature.py [feature-name] --environment dev --feature-flag enabled**Deployment Readiness:**

- [ ] All contracts validated

# Monitor integration- [ ] Tests passing (≥95% coverage)

python scripts/monitoring/watch_feature.py [feature-name] --metrics --logs- [ ] Performance benchmarks met

```- [ ] Security audit completed

- [ ] Documentation complete

**Success Criteria:**- [ ] Feature flags configured

- [ ] All integration tests pass

- [ ] Performance SLAs maintained across integrated components**Rollout Strategy:**

- [ ] Security policies enforced for all feature access- **Deployment Type:** [Blue-green/Rolling/Canary]

- [ ] Monitoring and alerting operational- **User Rollout:** [Gradual/Full/A-B test]

- [ ] Feature flags working for controlled rollout- **Feature Flags:** [How to control feature]

- **Monitoring Plan:** [What to monitor]

Please help me integrate this feature safely with comprehensive validation.

```**Configuration:**

- **Feature Settings:** [Feature-specific config]

---- **Environment Variables:** [Required env vars]

- **Database Changes:** [Schema/data updates]

## 📊 **Feature Validation Request**- **External Dependencies:** [Third-party services]



```**Monitoring & Alerting:**

I need comprehensive validation of a completed feature:- **Health Checks:** [Feature health validation]

- **Success Metrics:** [KPIs to track]

**Feature Information:**- **Error Monitoring:** [Error detection/alerting]

- **Feature Name:** [completed feature name]- **Performance Monitoring:** [Performance tracking]

- **Implementation Status:** [development complete]

- **Integration Status:** [integrated with MemoryOS components]**Risk Management:**

- **Testing Status:** [unit and integration tests complete]- **Rollback Plan:** [How to disable feature]

- **Rollback Triggers:** [When to rollback]

**Validation Requirements:**- **Data Recovery:** [Data consistency handling]

- **Functional Validation:** [Verify all requirements met]- **Communication Plan:** [User/stakeholder updates]

- **Performance Validation:** [Benchmark against SLA requirements]

- **Security Validation:** [Audit access controls and data protection]**Validation Plan:**

- **Contract Validation:** [Ensure API/Event/Storage compliance]- **Smoke Tests:** [Basic functionality validation]

- **User Acceptance:** [User workflow testing]

**Test Coverage Analysis:**- **Load Testing:** [Performance under load]

- **Unit Test Coverage:** [Current coverage percentage]- **Business Metrics:** [Business impact validation]

- **Integration Test Coverage:** [Cross-component test results]

- **Performance Test Results:** [Latency, throughput, resource usage]Please validate deployment readiness and provide deployment procedures.

- **Security Test Results:** [RBAC, data encryption, input validation]```



**Production Readiness:**---

- **Configuration Management:** [Environment variables, secrets]

- **Monitoring Setup:** [Metrics, dashboards, alerts configured]## 📊 **Feature Performance Request**

- **Documentation:** [API docs, user guides, troubleshooting]

- **Deployment Procedures:** [CI/CD pipeline, rollback plans]```

I need to ensure my new feature meets performance requirements:

**Validation Commands:**

```bash**Feature Details:**

# Comprehensive validation suite- **Feature Name:** [Name of feature]

python contracts/automation/validation_helper.py --production-ready [feature-name]- **Performance Requirements:** [SLA targets]

python -m ward test --path tests/ --coverage-report- **Current Performance:** [Baseline metrics]

python -m pytest tests/performance/ --benchmark-min-rounds=10- **Performance Concerns:** [Known bottlenecks]

python scripts/security/full_audit.py [feature-name]

**Performance Targets:**

# Production readiness check- **Response Time:** [API response targets]

python scripts/deployment/validate_feature.py [feature-name] --environment prod- **Throughput:** [Operations per second]

python scripts/monitoring/health_check.py [feature-name]- **Resource Usage:** [CPU/Memory limits]

```- **Concurrency:** [Concurrent user support]



**Acceptance Criteria:****Testing Strategy:**

- [ ] All functional requirements validated- **Load Testing:** [Normal load scenarios]

- [ ] Performance benchmarks meet or exceed SLA- **Stress Testing:** [High load scenarios]

- [ ] Security audit passes all checks- **Spike Testing:** [Sudden load increases]

- [ ] ≥95% test coverage achieved- **Endurance Testing:** [Long-running scenarios]

- [ ] All contracts validated and compliant

- [ ] Documentation complete and accurate**Optimization Areas:**

- [ ] Monitoring and alerting operational- **Algorithm Efficiency:** [Logic optimization]

- [ ] Deployment procedures tested and documented- **Database Performance:** [Query optimization]

- **Caching Strategy:** [What to cache]

**Quality Metrics:**- **Async Processing:** [Parallel operations]

- **Code Quality:** [Linting, type checking, complexity analysis]

- **Test Quality:** [Coverage, assertion strength, edge cases]**Monitoring Setup:**

- **Performance:** [Response time, throughput, resource efficiency]- **Real-time Metrics:** [Live performance tracking]

- **Security:** [Vulnerability scan, access control verification]- **Performance Dashboards:** [Visualization setup]

- **Alerting Thresholds:** [When to alert]

Please validate this feature comprehensively before production deployment.- **Trend Analysis:** [Performance over time]

```

**Performance Validation:**

````- [ ] Response time targets met
- [ ] Throughput requirements satisfied
- [ ] Resource usage within limits
- [ ] Scalability validated
- [ ] No performance regression

**Optimization Plan:**
- **Immediate Optimizations:** [Quick wins]
- **Long-term Improvements:** [Architectural changes]
- **Monitoring Improvements:** [Better visibility]
- **Capacity Planning:** [Future scaling needs]

Please help me ensure this feature meets all performance requirements.
```

---

## 🔄 **Feature Enhancement Request**

```
I want to enhance an existing feature with new capabilities:

**Current Feature:**
- **Feature Name:** [Existing feature name]
- **Current Functionality:** [What it does now]
- **Usage Patterns:** [How users currently use it]
- **Known Limitations:** [What needs improvement]

**Proposed Enhancements:**
- **New Capabilities:** [Additional functionality]
- **Improved Performance:** [Speed/efficiency gains]
- **Better User Experience:** [UX improvements]
- **Enhanced Security:** [Security improvements]

**Enhancement Scope:**
- **In Scope:** [What's included in enhancement]
- **Out of Scope:** [What's not included]
- **Backward Compatibility:** [Compatibility requirements]
- **Migration Strategy:** [How to transition users]

**Technical Changes:**
- **API Enhancements:** [New/modified endpoints]
- **Data Model Changes:** [Schema modifications]
- **Event Changes:** [Event schema updates]
- **Configuration Changes:** [New settings]

**Impact Assessment:**
- **Breaking Changes:** [What might break]
- **Performance Impact:** [Effect on performance]
- **Security Impact:** [Security implications]
- **User Impact:** [Effect on user workflows]

**Implementation Strategy:**
- **Phased Rollout:** [How to deploy incrementally]
- **Feature Flags:** [How to control rollout]
- **A/B Testing:** [How to validate improvements]
- **Rollback Plan:** [How to revert if needed]

**Success Metrics:**
- **Adoption Metrics:** [Feature usage indicators]
- **Performance Metrics:** [Speed/efficiency measures]
- **User Satisfaction:** [User feedback indicators]
- **Business Metrics:** [Business impact measures]

Please help me enhance this feature while maintaining stability and user experience.
```
