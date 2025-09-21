# 🧩 New Module Development Prompts

Use these prompts when adding modules to existing services or creating modular components.

---

## 🎯 **Module Planning Request**

```
I want to add a new module to an existing service:

**Target Service:**
- **Service Name:** [Which service to extend]
- **Current Architecture:** [How service is structured]
- **Extension Point:** [Where module fits]

**Module Specification:**
- **Module Name:** [Module identifier]
- **Purpose:** [Single responsibility of module]
- **Scope:** [What it will/won't do]
- **Interface:** [How other components interact]

**Integration Requirements:**
- **Service Registration:** [How to register with parent]
- **Event Subscription:** [Events it needs to handle]
- **Storage Extension:** [New data requirements]
- **Configuration:** [Module-specific settings]

**Dependencies:**
- **Internal:** [Other modules/services needed]
- **External:** [Third-party dependencies]
- **Data:** [Data sources required]
- **Compute:** [Processing requirements]

Please help me design this module with proper separation of concerns.
```

---

## 🔧 **Module Implementation Request**

```
I'm ready to implement a new module. Please help me build it:

**Module Details:**
- **Name:** [Module name]
- **Parent Service:** [Service it belongs to]
- **Core Function:** [Primary responsibility]

**Implementation Pattern:**
- **Module Type:** [Handler/Processor/Store/Analyzer]
- **Interface Style:** [Sync/Async/Event-driven]
- **Data Flow:** [Input → Processing → Output]
- **Error Handling:** [How to handle failures]

**Integration Points:**
- **Service Integration:** [How to integrate with parent]
- **Event Integration:** [Event handling patterns]
- **Storage Integration:** [Data persistence needs]
- **Policy Integration:** [Access control requirements]

**Quality Requirements:**
- **Testing:** [Unit/Integration test requirements]
- **Performance:** [SLA requirements]
- **Observability:** [Metrics/traces/logs]
- **Documentation:** [Usage and integration docs]

**Module Structure:**
```
service/modules/new-module/
├── __init__.py
├── module.py          # Core logic
├── models.py          # Data models
├── handlers.py        # Event/request handlers
└── tests/             # Module tests
```

Please implement this module following MemoryOS patterns.
```

---

## 🔌 **Module Integration Request**

```
I need to integrate a new module with its parent service:

**Module Information:**
- **Module Name:** [Name of module]
- **Parent Service:** [Service it belongs to]
- **Implementation Status:** [Complete/In-progress]

**Integration Requirements:**
- **Service Registration:** [How parent discovers module]
- **Lifecycle Management:** [Start/stop/restart handling]
- **Configuration Sharing:** [Access to service config]
- **Error Propagation:** [How errors bubble up]

**Event Integration:**
- **Event Subscription:** [Events module handles]
- **Event Production:** [Events module produces]
- **Event Routing:** [How events reach module]
- **Error Handling:** [Failed event processing]

**Data Integration:**
- **Shared Storage:** [Access to service data]
- **Module Storage:** [Module-specific data]
- **Data Consistency:** [Transaction boundaries]
- **Migration Strategy:** [Existing data handling]

**Testing Strategy:**
- **Isolation Testing:** [Module tested alone]
- **Integration Testing:** [Module with service]
- **Regression Testing:** [Existing functionality]
- **Performance Testing:** [Impact on service]

Please help me integrate this module safely with proper validation.
```

---

## 🧪 **Module Testing Request**

```
I need comprehensive testing for a new module:

**Module Details:**
- **Module Name:** [Name]
- **Parent Service:** [Service]
- **Functionality:** [What it does]

**Test Coverage Requirements:**
- **Unit Tests:** [Individual function testing]
- **Integration Tests:** [Module with service]
- **Contract Tests:** [Interface compliance]
- **Performance Tests:** [SLA validation]

**Test Scenarios:**
- **Happy Path:** [Normal operation flows]
- **Error Cases:** [Failure scenarios]
- **Edge Cases:** [Boundary conditions]
- **Load Testing:** [Performance under stress]

**Test Environment:**
- **Isolation:** [Can module be tested alone?]
- **Dependencies:** [What needs to be mocked/real?]
- **Data Setup:** [Test data requirements]
- **Cleanup:** [Post-test cleanup needs]

**Success Criteria:**
- [ ] ≥95% code coverage
- [ ] All integration points tested
- [ ] Performance benchmarks met
- [ ] No regression in parent service

Please create comprehensive test suite for this module.
```

---

## 📊 **Module Performance Request**

```
I need to optimize performance for a module:

**Module Information:**
- **Name:** [Module name]
- **Current Performance:** [Baseline metrics]
- **Target Performance:** [SLA requirements]
- **Bottlenecks:** [Known performance issues]

**Performance Requirements:**
- **Throughput:** [Operations per second]
- **Latency:** [Response time requirements]
- **Resource Usage:** [CPU/Memory limits]
- **Concurrency:** [Concurrent operation support]

**Optimization Areas:**
- **Algorithm Efficiency:** [Logic optimization]
- **Data Access:** [Storage optimization]
- **Caching Strategy:** [What to cache]
- **Async Processing:** [Parallel operation opportunities]

**Measurement Strategy:**
- **Benchmarking:** [How to measure performance]
- **Profiling:** [Where to look for bottlenecks]
- **Monitoring:** [Ongoing performance tracking]
- **Alerting:** [Performance degradation detection]

**Constraints:**
- **Backward Compatibility:** [Must maintain interfaces]
- **Resource Limits:** [Available CPU/Memory]
- **Dependencies:** [Performance of upstream services]
- **SLA Requirements:** [Non-negotiable performance targets]

Please help me optimize this module's performance while maintaining functionality.
```

---

## 🔄 **Module Refactoring Request**

```
I need to refactor an existing module to improve it:

**Current Module:**
- **Name:** [Module name]
- **Current Issues:** [What needs improvement]
- **Technical Debt:** [Known problems]
- **Performance Issues:** [Speed/efficiency problems]

**Refactoring Goals:**
- **Code Quality:** [Cleaner, more maintainable code]
- **Performance:** [Better speed/efficiency]
- **Testability:** [Easier to test]
- **Maintainability:** [Easier to modify/extend]

**Refactoring Scope:**
- **Architecture Changes:** [Structural improvements]
- **Interface Changes:** [API modifications]
- **Implementation Changes:** [Internal logic improvements]
- **Dependency Changes:** [Better dependency management]

**Risk Assessment:**
- **Breaking Changes:** [What might break]
- **Performance Impact:** [Potential performance changes]
- **Integration Impact:** [Effect on parent service]
- **Migration Strategy:** [How to transition safely]

**Success Criteria:**
- [ ] Improved code quality metrics
- [ ] Better test coverage
- [ ] Enhanced performance
- [ ] No functionality regression
- [ ] Easier maintenance

Please help me refactor this module safely and effectively.
```