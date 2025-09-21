````prompt
# 🎯 Milestone Planning & Management Prompts

Use these prompts when planning milestones, organizing epics, and managing the overall development strategy.

---

## 🏔️ **Milestone Planning & Breakdown**

```
I need to plan a milestone for MemoryOS development:

**Milestone Overview:**
- **Milestone Number:** [M1, M2, M3, etc.]
- **Milestone Name:** [foundation, cognitive-core, intelligence-layer, etc.]
- **Duration:** [Estimated weeks: 12-16 weeks typical]
- **Business Objective:** [What capability this milestone delivers]

**Scope & Objectives:**
- **Primary Goals:** [Main technical objectives to achieve]
- **Success Criteria:** [Measurable outcomes that define completion]
- **Dependencies:** [Prerequisites from previous milestones]
- **Constraints:** [Timeline, resource, or technical limitations]

**Epic Breakdown:**
I need to break this milestone into 3-5 epics:
- **Epic 1:** [Name and description of first epic]
- **Epic 2:** [Name and description of second epic]
- **Epic 3:** [Name and description of third epic]
- **Epic 4:** [Additional epics if needed]

**Architecture Considerations:**
- **System Components:** [Which parts of MemoryOS are affected]
- **Contract Changes:** [API, Events, Storage contracts needed]
- **Integration Points:** [How this milestone connects to existing system]
- **Performance Goals:** [SLO targets and performance requirements]

**Risk Assessment:**
- **Technical Risks:** [Potential technical challenges]
- **Integration Risks:** [Complexity of connecting components]
- **Timeline Risks:** [Factors that could delay delivery]
- **Mitigation Strategies:** [Plans to address identified risks]

**Resource Planning:**
- **Team Structure:** [How the 2-person team will be organized]
- **Skill Requirements:** [Technical expertise needed]
- **External Dependencies:** [Third-party tools or services required]
- **Knowledge Gaps:** [Areas requiring research or learning]

**Milestone Deliverables:**
- **Core Features:** [Primary functionality delivered]
- **Quality Metrics:** [Test coverage, performance benchmarks]
- **Documentation:** [READMEs, ADRs, API docs required]
- **Deployment Artifacts:** [What gets deployed to dev/staging]

**Acceptance Criteria:**
- [ ] All epics completed and integrated
- [ ] Full test suite passing (unit + integration + contract)
- [ ] Performance targets met
- [ ] Security requirements satisfied
- [ ] Documentation complete and reviewed
- [ ] Ready for next milestone dependencies

Please help me plan this milestone with proper epic breakdown and implementation strategy.
```

---

## 📋 **Epic Planning & Organization**

```
I need to plan an epic within a milestone:

**Epic Context:**
- **Parent Milestone:** [M1-foundation, M2-cognitive-core, etc.]
- **Epic Number:** [1.1, 1.2, 2.1, etc.]
- **Epic Name:** [event-bus-infrastructure, storage-foundation, etc.]
- **Estimated Duration:** [3-4 weeks typical]

**Epic Objectives:**
- **Primary Goal:** [What this epic achieves]
- **Business Value:** [Why this epic matters]
- **Technical Outcome:** [Specific technical deliverable]
- **Integration Points:** [How it connects to other epics]

**Issue Breakdown:**
Break this epic into 5-8 issues:
- **Issue 1:** [Specific task/feature to implement]
- **Issue 2:** [Next task in logical sequence]
- **Issue 3:** [Subsequent implementation task]
- **Issue 4-8:** [Additional issues as needed]

**Contract Dependencies:**
- **API Contracts:** [OpenAPI specifications needed]
- **Event Contracts:** [Event schemas and envelope changes]
- **Storage Contracts:** [Database schemas and migrations]
- **Integration Contracts:** [Cross-service communication needs]

**Technical Architecture:**
- **Components Affected:** [Which modules/services change]
- **Design Patterns:** [Architectural patterns to apply]
- **Technology Stack:** [Specific tools/libraries needed]
- **Performance Considerations:** [Latency, throughput, resource usage]

**Implementation Strategy:**
- **Development Order:** [Logical sequence for issue implementation]
- **Feature Flags:** [How to gate new functionality]
- **Testing Strategy:** [Unit, integration, contract testing approach]
- **Observability Plan:** [Metrics, traces, logs to implement]

**Quality Assurance:**
- **Test Coverage Goals:** [Coverage targets for this epic]
- **Performance Benchmarks:** [Speed and resource targets]
- **Security Requirements:** [Security and privacy needs]
- **Documentation Standards:** [Docs that must be created/updated]

Please help me plan this epic with detailed issue breakdown and implementation approach.
```

---

## 📝 **Issue Planning & Implementation**

```
I need to plan an individual issue within an epic:

**Issue Context:**
- **Parent Epic:** [M1.1-event-bus, M1.2-storage, etc.]
- **Issue Number:** [1.1.1, 1.1.2, 2.1.3, etc.]
- **Issue Name:** [event-envelope-design, basic-publisher, etc.]
- **Estimated Duration:** [1-5 days typical]

**Issue Objectives:**
- **Specific Goal:** [Exact task to accomplish]
- **Acceptance Criteria:** [Clear success definition]
- **Definition of Done:** [When this issue is complete]
- **Dependencies:** [Other issues that must complete first]

**Technical Implementation:**
- **Files to Modify:** [Specific files that will change]
- **Contract Changes:** [Any contract updates needed]
- **Test Requirements:** [Tests that must be written]
- **Documentation Updates:** [Docs that need updating]

**Implementation Approach:**
1. **Contracts First:** [Update contracts before code]
2. **Test-Driven:** [Write failing tests first]
3. **Feature Flags:** [How to gate this functionality]
4. **Observability:** [Metrics/traces/logs to add]
5. **Validation:** [How to verify it works]

**Quality Checklist:**
- [ ] Contract syntax validation passes
- [ ] Unit tests written and passing (≥70% coverage)
- [ ] Integration tests cover I/O paths
- [ ] Contract tests validate schemas
- [ ] Performance tests for hot paths
- [ ] Security scan passes
- [ ] Code review complete
- [ ] Documentation updated

**Branch Strategy:**
- **Branch Name:** `issue/{epic-id}.{issue-id}-{issue-name}`
- **Base Branch:** `epic/M{milestone}.{epic}-{epic-name}`
- **Merge Target:** Parent epic branch
- **PR Title:** `feat({epic}): {issue-description}`

**Risk Mitigation:**
- **Technical Risks:** [Potential implementation challenges]
- **Integration Risks:** [How this might break other things]
- **Timeline Risks:** [Factors that could extend duration]
- **Rollback Plan:** [How to revert if problems arise]

Please help me plan this issue with detailed implementation strategy and validation approach.
```

---

## 📊 **Progress Tracking & Status**

```
I need to track progress across milestones, epics, and issues:

**Current Status Request:**
- **Active Milestone:** [Which milestone is in progress]
- **Epic Status:** [Status of each epic in the milestone]
- **Issue Progress:** [Completed vs remaining issues]
- **Blockers:** [Issues preventing progress]

**Metrics Needed:**
- **Velocity:** [Issues completed per sprint/week]
- **Quality:** [Test coverage, defect rates]
- **Performance:** [Whether SLO targets are being met]
- **Risk Status:** [Current risk assessment]

**Reporting Requirements:**
- **Stakeholder Updates:** [Progress summary for leadership]
- **Team Status:** [Current work and next priorities]
- **Milestone Forecast:** [Projected completion dates]
- **Resource Needs:** [Any additional support required]

Please help me assess current progress and create status reports.
```
````
