````prompt# 🏗️ New Service Development Prompts# New Service Development

# 🏗️ New Service Development Prompts



Use these standardized prompts when creating new services to ensure proper planning and implementation following MemoryOS architecture standards.

Use these standardized prompts when creating new services to ensure proper planning and implementation.Goal: Create new services following contracts-first methodology and MemoryOS architecture standards while ensuring proper integration and quality.

---



## 🎯 **Service Planning Request**

---Context Required:

```

I want to create a new service. Help me plan it properly:- Service purpose and business domain



**Service Overview:**## 🎯 **Service Planning Request**- Architecture tier (API/Events/Storage/Cognitive)

- **Name:** [service-name] (must be valid Python module name)

- **Purpose:** [Specific business capability - avoid "manage" or "handle"]- Functional and non-functional requirements

- **Domain:** [memory|attention|perception|action|social|learning] (maps to MemoryOS cognitive domains)

- **Priority:** [Critical/High/Medium/Low]```- Integration points and dependencies



**Architecture Requirements:**I want to create a new service. Help me plan it properly:- Security band and policy requirements

- **Tier:** [API/Events/Storage/Cognitive] (determines pipeline P01-P20 placement)

- **Dependencies:** [List existing services: memory_steward, hippocampus, episodic, etc.]

- **Integration Points:** [Specific APIs/events: GET /api/v1/memories, memory.created events]

- **Data Flow:** [Input: HTTP requests → Processing: store in sqlite → Output: JSON responses]**Service Overview:**Tasks:



**Functional Requirements:**- **Name:** [Service name]1) **Contracts First**: Define API OpenAPI specs, event schemas, and storage contracts before implementation

- **Core Features:** [Specific capabilities: store memories, retrieve by query, semantic search]

- **User Interface:** [REST API endpoints, async event handlers, background workers]- **Purpose:** [What problem does it solve]2) **Architecture Design**: Plan service structure following MemoryOS patterns (BaseStore, EventBus, PolicyService)

- **Data Processing:** [Exact operations: validate input, apply policy, store with UoW]

- **Business Logic:** [Concrete rules: memories expire after 30 days, max 100MB per memory]- **Domain:** [Which business domain]3) **Security Integration**: Implement Policy Enforcement Point (PEP) with proper RBAC/ABAC and space/band rules



**Non-Functional Requirements:**- **Priority:** [High/Medium/Low]4) **Implementation**: Build service with proper observability (metrics/traces/logs), UnitOfWork patterns, and MLS integration

- **Performance:** [Specific SLAs: 95th percentile response <200ms, throughput >1000 req/s]

- **Security:** [Exact requirements: Bearer token auth, RBAC with policy/, space isolation]5) **Quality Assurance**: Achieve ≥95% test coverage with unit, integration, contract, and performance tests

- **Scalability:** [Concrete limits: handle 10K users, 1M memories, 100GB storage]

- **Availability:** [Specific uptime: 99.9% availability, max 5min downtime/month]**Architecture Requirements:**6) **Documentation**: Create comprehensive service documentation and integration guides



**MemoryOS Integration Requirements:**- **Tier:** [API/Events/Storage/Cognitive]

- **BaseStore:** [Extends storage/base_store.py for data persistence]

- **EventBus:** [Uses events/ for async communication]- **Dependencies:** [Other services needed]Implementation Patterns:

- **PolicyService:** [Integrates policy/ for access control]

- **Observability:** [Uses observability/ for metrics/traces/logs]- **Integration Points:** [How it connects to system]- BaseStore extension for storage services

- **MLS/Security:** [Uses security/ for encryption/signing]

- **Data Flow:** [Input → Processing → Output]- EventBus integration for event processing

**Contract Files Required:**

- [ ] contracts/api/openapi/modules/[service-name]-openapi.yaml- PolicyService integration for access control

- [ ] contracts/events/modules/[service-name]-catalog.json

- [ ] contracts/storage/schemas/[service-name]-*.schema.json**Functional Requirements:**- MLS group integration for space-scoped data



**Implementation Structure:**- **Core Features:** [Main capabilities]- UnitOfWork pattern for transactional operations

```

[service-name]/- **User Interface:** [How users interact]

├── __init__.py           # Exports: [ServiceName]Service, [ServiceName]Store

├── README.md            # Service documentation with examples- **Data Processing:** [What data operations]Quality Requirements:

├── service.py           # Main [ServiceName]Service class

├── models.py            # Pydantic models for data validation- **Business Logic:** [Key rules/workflows]- Unit tests ≥95% coverage with real components (no "mock theater")

├── store.py             # [ServiceName]Store(BaseStore) class

├── handlers.py          # Event handlers (if needed)- Integration tests for all I/O paths (API ↔ events ↔ storage)

└── tests/               # Test modules mirroring structure

    ├── test_service.py**Non-Functional Requirements:**- Contract compliance validation in tests

    ├── test_store.py

    └── test_handlers.py- **Performance:** [SLA requirements]- Performance benchmarks meeting SLA requirements

```

- **Security:** [Security band and requirements]- Security audit with proper PEP enforcement

**Quality Gates:**

- [ ] ≥95% test coverage with WARD framework- **Scalability:** [Growth expectations]

- [ ] All contracts validated with automation tools

- [ ] Performance benchmarks meet SLA requirements- **Availability:** [Uptime requirements]Deliverables:

- [ ] Security audit passes policy enforcement tests

- [ ] Integration tests with real components (no mocks)- Complete contract definitions (API/Events/Storage)



**Generation Commands:**Please help me design the service architecture and create implementation plan.- Service implementation following MemoryOS patterns

- [ ] `python contracts/automation/interactive_contract_builder.py` (guided creation)

- [ ] `python contracts/automation/contract_suite.py generate --service [service-name]````- Comprehensive test suite with ≥95% coverage

- [ ] `python contracts/automation/validation_helper.py --service [service-name]`

- Integration with observability and security systems

Please design the service with these concrete specifications.

```---- Deployment configuration and documentation



---- **Performance:** [SLA requirements]



## 📋 **Service Implementation Request**## 📋 **Service Implementation Request**- **Security:** [Security band and requirements]



```- **Scalability:** [Growth expectations]

I'm ready to implement a new service. Please help me build it:

```- **Availability:** [Uptime requirements]

**Service Specification:**

- **Name:** [service-name] (validated Python module name)I'm ready to implement a new service. Please help me build it:

- **Architecture Tier:** [API/Events/Storage/Cognitive]

- **Core Purpose:** [Specific business function]Please help me design the service architecture and create implementation plan.

- **Brain Region:** [hippocampus|cortex|cerebellum|etc.] (for cognitive services)

**Service Specification:**```

**Contract Requirements (must exist first):**

- **API Contract:** [contracts/api/openapi/modules/[service-name]-openapi.yaml]- **Name:** [Service name]

- **Event Contract:** [contracts/events/modules/[service-name]-catalog.json]

- **Storage Contract:** [contracts/storage/schemas/[service-name]-*.schema.json]- **Architecture Tier:** [API/Events/Storage/Cognitive]---



**Implementation Patterns:**- **Core Purpose:** [Primary function]

- **Storage:** [Extends BaseStore? Which tables/collections?]

- **Events:** [Produces/consumes which topics? Event handlers needed?]## 📋 **Service Implementation Request**

- **Policy:** [RBAC/ABAC rules, space isolation requirements]

- **Observability:** [Metrics: familyos_[service]_*, traces: service.component.method]**Contract Requirements:**



**Integration Requirements:**- **API Contracts:** [OpenAPI specs needed]```

- **UnitOfWork:** [Transactional operations: create_memory, update_memory, etc.]

- **MLS Groups:** [Space-scoped data encryption required?]- **Event Contracts:** [Event schemas needed]I'm ready to implement a new service. Please help me build it:

- **Policy Service:** [Access control enforcement points]

- **Event Bus:** [Async processing patterns, event handlers]- **Storage Contracts:** [Data schemas needed]



**Quality Standards:****Service Specification:**

- **Test Coverage:** ≥95% with WARD framework

- **Performance:** [Specific SLA: <200ms p95, >1000 req/s]**Implementation Patterns:**- **Name:** [Service name]

- **Security:** [Policy enforcement, access controls, data encryption]

- **Documentation:** [README with API examples, integration guide]- **Storage:** [Does it need BaseStore extension?]- **Architecture Tier:** [API/Events/Storage/Cognitive]



**Implementation Checklist:**- **Events:** [Does it produce/consume events?]- **Core Purpose:** [Primary function]

- [ ] Scaffold service structure with concrete file names

- [ ] Implement [ServiceName]Service class with all methods- **Policy:** [Access control requirements]

- [ ] Create [ServiceName]Store(BaseStore) with storage operations

- [ ] Add event handlers in handlers.py (if applicable)- **Observability:** [Metrics/traces/logs needed]**Contract Requirements:**

- [ ] Implement models.py with Pydantic validation

- [ ] Create comprehensive test suite in tests/- **API Contracts:** [OpenAPI specs needed]

- [ ] Add observability instrumentation

- [ ] Validate contract compliance**Integration Requirements:**- **Event Contracts:** [Event schemas needed]



**Scaffolding Commands:**- **UnitOfWork:** [Transactional operations needed?]- **Storage Contracts:** [Data schemas needed]

```bash

# Create service structure- **MLS Groups:** [Space-scoped data?]

mkdir [service-name] && cd [service-name]

touch __init__.py service.py models.py store.py handlers.py README.md- **Policy Service:** [RBAC/ABAC enforcement?]**Implementation Patterns:**

mkdir tests && cd tests

touch test_service.py test_store.py test_handlers.py- **Event Bus:** [Event processing patterns?]- **Storage:** [Does it need BaseStore extension?]

```

- **Events:** [Does it produce/consume events?]

Please scaffold and implement the service following MemoryOS patterns.

```**Quality Standards:**- **Policy:** [Access control requirements]



---- **Test Coverage:** ≥95%- **Observability:** [Metrics/traces/logs needed]



## 🔌 **Service Integration Request**- **Performance:** [SLA targets]



```- **Security:** [Security controls]**Integration Requirements:**

I need to integrate a new service with existing MemoryOS components:

- **Documentation:** [What docs needed]- **UnitOfWork:** [Transactional operations needed?]

**Service Details:**

- **Service Name:** [service-name]- **MLS Groups:** [Space-scoped data?]

- **Current Status:** [contracts-defined|implemented|tested]

- **Core Functionality:** [Specific business operations]Please scaffold the service following MemoryOS patterns and best practices.- **Policy Service:** [RBAC/ABAC enforcement?]



**Integration Points:**```- **Event Bus:** [Event processing patterns?]

- **Upstream Dependencies:** [memory_steward, hippocampus, policy, etc.]

- **Downstream Consumers:** [api/, other cognitive services]

- **Event Flows:** [Events produced: service.created, Events consumed: memory.updated]

- **Data Sharing:** [Shared storage patterns, foreign keys]---**Quality Standards:**



**Technical Integration:**- **Test Coverage:** ≥95%

- **API Integration:** [REST endpoints: GET /api/v1/[service]/[resource]]

- **Event Integration:** [Topics: [service].*, Handlers: handle_memory_event]## 🔌 **Service Integration Request**- **Performance:** [SLA targets]

- **Storage Integration:** [Tables: [service]_*, Foreign keys to memories table]

- **Security Integration:** [Policy rules, space isolation, band controls]- **Security:** [Security controls]



**Testing Requirements:**```- **Documentation:** [What docs needed]

- **Unit Tests:** [Service-specific logic, storage operations]

- **Integration Tests:** [Cross-service API calls, event flows]I need to integrate a new service with existing systems:

- **Contract Tests:** [API compliance, event schema validation]

- **Performance Tests:** [End-to-end SLA validation]Please scaffold the service following MemoryOS patterns and best practices.



**Deployment Concerns:****Service Details:**```

- **Configuration:** [Environment variables, database connections]

- **Monitoring:** [Health checks, metrics dashboards, alerts]- **Service Name:** [Name of service]

- **Rollback:** [Service disable flags, graceful degradation]

- **Migration:** [Data migration scripts, contract versioning]- **Current Status:** [Development stage]---



**Integration Commands:**- **Core Functionality:** [What it does]

```bash

# Validate integration## 🔌 **Service Integration Request**

python contracts/automation/validation_helper.py --integration [service-name]

python -m ward test --path tests/integration/test_[service]_integration.py**Integration Points:**

python -m pytest tests/performance/test_[service]_performance.py

```- **Upstream Dependencies:** [Services it depends on]```



**Success Criteria:**- **Downstream Consumers:** [Services that will use it]I need to integrate a new service with existing systems:

- [ ] All upstream dependencies respond correctly

- [ ] Event flows work end-to-end- **Event Flows:** [Events it produces/consumes]

- [ ] Performance SLAs maintained

- [ ] Security policies enforced- **Data Sharing:** [Shared data requirements]**Service Details:**

- [ ] Monitoring and alerting functional

- **Service Name:** [Name of service]

Please help me integrate this service safely with proper validation.

```**Technical Integration:**- **Current Status:** [Development stage]



---- **API Integration:** [REST/GraphQL endpoints]- **Core Functionality:** [What it does]



## 🚀 **Service Deployment Request**- **Event Integration:** [Event topics and handlers]



```- **Storage Integration:** [Shared data patterns]**Integration Points:**

I'm ready to deploy a new service. Help me prepare:

- **Security Integration:** [Policy enforcement]- **Upstream Dependencies:** [Services it depends on]

**Service Information:**

- **Service Name:** [service-name]- **Downstream Consumers:** [Services that will use it]

- **Version:** [1.0.0] (SemVer)

- **Environment:** [dev|staging|prod]**Testing Requirements:**- **Event Flows:** [Events it produces/consumes]

- **Deployment Type:** [blue-green|rolling|canary]

- **Unit Tests:** [Service-specific tests]- **Data Sharing:** [Shared data requirements]

**Pre-Deployment Checklist:**

- [ ] All contracts validated: `python contracts/automation/validation_helper.py`- **Integration Tests:** [Cross-service tests]

- [ ] Tests passing ≥95% coverage: `python -m ward test --path [service-name]/tests/`

- [ ] Performance benchmarks met: `python -m pytest tests/performance/`- **Contract Tests:** [Interface compliance]**Technical Integration:**

- [ ] Security audit completed: `python scripts/security/audit_service.py [service-name]`

- [ ] Documentation complete: README.md, API docs generated- **Performance Tests:** [End-to-end SLA]- **API Integration:** [REST/GraphQL endpoints]



**Configuration Requirements:**- **Event Integration:** [Event topics and handlers]

- **Environment Variables:** [Specific vars: DATABASE_URL, EVENT_BUS_URL, POLICY_ENDPOINT]

- **Database Setup:** [Tables, indices, migrations]**Deployment Concerns:**- **Storage Integration:** [Shared data patterns]

- **External Dependencies:** [Event bus, policy service, observability stack]

- **Resource Limits:** [CPU: 2 cores, Memory: 4GB, Storage: 100GB]- **Configuration:** [Service settings]- **Security Integration:** [Policy enforcement]



**Monitoring Setup:**- **Monitoring:** [Observability setup]

- **Health Checks:** [HTTP endpoint: GET /health, Response: 200 OK]

- **Metrics:** [Key indicators: request_rate, error_rate, response_time]- **Rollback:** [Failure recovery]**Testing Requirements:**

- **Alerts:** [Thresholds: error_rate >5%, response_time >500ms]

- **Dashboards:** [Service overview, performance metrics, error tracking]- **Migration:** [Data/config migration]- **Unit Tests:** [Service-specific tests]



**Rollback Plan:**- **Integration Tests:** [Cross-service tests]

- **Rollback Triggers:** [Error rate >10%, response time >1s, health check failures]

- **Rollback Procedure:** [Specific steps, automated scripts]Please help me integrate this service safely with proper testing and validation.- **Contract Tests:** [Interface compliance]

- **Data Consistency:** [Transaction rollback, event replay]

- **Communication Plan:** [Stakeholder notification, status page updates]```- **Performance Tests:** [End-to-end SLA]



**Deployment Commands:**

```bash

# Validate deployment readiness---**Deployment Concerns:**

python scripts/deployment/validate_service.py [service-name]

python contracts/automation/validation_helper.py --production-ready [service-name]- **Configuration:** [Service settings]



# Deploy with monitoring## 🚀 **Service Deployment Request**- **Monitoring:** [Observability setup]

python scripts/deployment/deploy_service.py [service-name] --environment [env]

```- **Rollback:** [Failure recovery]



**Success Criteria:**```- **Migration:** [Data/config migration]

- [ ] Service starts successfully

- [ ] Health checks passingI'm ready to deploy a new service. Help me prepare:

- [ ] Metrics within normal ranges

- [ ] Integration tests pass in environmentPlease help me integrate this service safely with proper testing and validation.

- [ ] No performance regression

**Service Information:**```

Please validate deployment readiness and provide deployment procedures.

```- **Service Name:** [Name]



````- **Version:** [Initial version]---

- **Environment:** [Dev/Staging/Prod]

## 🚀 **Service Deployment Request**

**Deployment Checklist:**

- [ ] All contracts validated```

- [ ] Tests passing (≥95% coverage)I'm ready to deploy a new service. Help me prepare:

- [ ] Performance benchmarks met

- [ ] Security audit completed**Service Information:**

- [ ] Documentation complete- **Service Name:** [Name]

- **Version:** [Initial version]

**Configuration Requirements:**- **Environment:** [Dev/Staging/Prod]

- **Environment Variables:** [Required config]

- **Database Setup:** [Storage requirements]**Deployment Checklist:**

- **External Dependencies:** [Third-party services]- [ ] All contracts validated

- **Resource Limits:** [CPU/Memory/Storage]- [ ] Tests passing (≥95% coverage)

- [ ] Performance benchmarks met

**Monitoring Setup:**- [ ] Security audit completed

- **Health Checks:** [Service health endpoints]- [ ] Documentation complete

- **Metrics:** [Key performance indicators]

- **Alerts:** [Error/performance thresholds]**Configuration Requirements:**

- **Dashboards:** [Monitoring visualizations]- **Environment Variables:** [Required config]

- **Database Setup:** [Storage requirements]

**Rollback Plan:**- **External Dependencies:** [Third-party services]

- **Rollback Triggers:** [When to rollback]- **Resource Limits:** [CPU/Memory/Storage]

- **Rollback Procedure:** [How to rollback]

- **Data Recovery:** [Data consistency handling]**Monitoring Setup:**

- **Communication Plan:** [Stakeholder notification]- **Health Checks:** [Service health endpoints]

- **Metrics:** [Key performance indicators]

Please validate deployment readiness and provide deployment procedures.- **Alerts:** [Error/performance thresholds]

```- **Dashboards:** [Monitoring visualizations]

**Rollback Plan:**
- **Rollback Triggers:** [When to rollback]
- **Rollback Procedure:** [How to rollback]
- **Data Recovery:** [Data consistency handling]
- **Communication Plan:** [Stakeholder notification]

Please validate deployment readiness and provide deployment procedures.
```

---

## 🔄 **Service Modernization Request**

```
I need to modernize an existing service to current standards:

**Current Service:**
- **Name:** [Service name]
- **Current Architecture:** [How it works now]
- **Known Issues:** [What needs improvement]
- **Dependencies:** [Current dependencies]

**Modernization Goals:**
- **Contract Compliance:** [Bring up to contract standards]
- **Architecture Updates:** [Move to current patterns]
- **Performance Improvements:** [SLA compliance]
- **Security Enhancements:** [Current security gaps]

**Migration Strategy:**
- **Approach:** [Big bang/Gradual/Parallel]
- **Backward Compatibility:** [How long to maintain]
- **Data Migration:** [How to handle existing data]
- **Feature Parity:** [Must maintain all features]

**Risk Assessment:**
- **High Risk Areas:** [What could break]
- **Mitigation Strategies:** [How to reduce risk]
- **Testing Strategy:** [How to validate changes]
- **Rollback Plan:** [How to undo if needed]

**Success Criteria:**
- [ ] Contract compliance achieved
- [ ] Performance SLA met
- [ ] Security requirements satisfied
- [ ] No functionality regression

Please help me plan and execute this modernization safely.
```

---

## 🐛 **Service Debugging Request**

```
I'm having issues with a service and need help debugging:

**Service Information:**
- **Service Name:** [Which service]
- **Environment:** [Dev/Staging/Prod]
- **Version:** [Service version]

**Problem Description:**
- **Symptoms:** [What's going wrong]
- **Error Messages:** [Specific errors seen]
- **When Started:** [When problem began]
- **Frequency:** [How often it happens]

**Impact Assessment:**
- **Affected Users:** [Who is impacted]
- **Business Impact:** [Effect on operations]
- **Severity:** [Critical/High/Medium/Low]
- **Workarounds:** [Any temporary fixes]

**Investigation Done:**
- **Logs Checked:** [What logs reviewed]
- **Metrics Reviewed:** [Performance data]
- **Recent Changes:** [Any recent deployments]
- **Dependencies Checked:** [Upstream/downstream status]

**Debugging Assistance Needed:**
- [ ] Log analysis
- [ ] Performance profiling
- [ ] Contract validation
- [ ] Integration testing
- [ ] Root cause analysis

Please help me identify and resolve the issue with this service.
```
