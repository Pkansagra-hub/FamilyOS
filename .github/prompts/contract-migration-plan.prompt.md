````prompt
# 🔄 Contract Migration Planning Prompts

Use these prompts when planning safe migrations for breaking contract changes with adapters and rollout strategies.

---

## 📋 **Create Breaking Change Migration Plan**

```
I need to create a comprehensive migration plan for breaking contract changes:

**Breaking Change Context:**
- **Proposed Changes:** [Detailed list of breaking modifications]
- **Source Version:** [Current frozen contract version]
- **Target Version:** [Proposed new contract version]
- **Impact Scope:** [API/Events/Storage/Pipelines affected]
- **Business Justification:** [Why breaking changes are necessary]

**Change Impact Assessment:**
- **API Changes:** [Modified endpoints, parameters, response formats]
- **Event Changes:** [Modified topics, envelope structure, payload schema]
- **Storage Changes:** [Schema modifications, data structure changes]
- **Consumer Impact:** [Which systems/teams will be affected]

**Migration Plan Requirements:**
1. **Change Matrix Documentation:**
   - What fields/topics/routes change and why
   - Before/after schema comparisons
   - Backward compatibility analysis
   - Forward compatibility considerations

2. **Adapter Strategy:**
   - Shims for N-1 version compatibility
   - Dual-read/dual-write implementations
   - Feature flags for risky transition paths
   - Policy band adjustments for breaking changes

3. **Migration Choreography:**
   ```
   Phase 1: Dual-write/dual-read (backward compatibility)
   Phase 2: Cutover window with backout criteria
   Phase 3: Deprecation and cleanup (≥2 releases notice)
   ```

4. **Observability & Monitoring:**
   - Counters for old vs new traffic patterns
   - Error rates and conversion dropoffs
   - Performance impact measurements
   - Migration progress tracking

5. **Documentation Requirements:**
   - `contracts/MIGRATION-v<from>-to-v<to>.md`
   - Updated `POLICY_VERSIONING.md`
   - Consumer integration guides
   - Troubleshooting and rollback procedures

6. **Implementation Checklist:**
   - Contract changes with version bumps
   - Adapter implementations and feature flags
   - Comprehensive test coverage (contract + integration)
   - Monitoring dashboards and alerts
   - Rollback procedures and criteria

**Migration Timeline Planning:**
- **Phase 1 Duration:** [Dual-mode operation period]
- **Cutover Window:** [Planned transition timeframe]
- **Deprecation Notice:** [How long before old version removal]
- **Rollback Criteria:** [Conditions that trigger rollback]

**Risk Mitigation:**
- **Consumer Coordination:** [How to communicate with affected teams]
- **Rollback Strategy:** [Quick revert procedures]
- **Error Handling:** [Graceful degradation during transition]
- **Performance Impact:** [Load testing and capacity planning]

**Adapter Implementation Locations:**
- **API Layer:** [Specific router/handler modifications needed]
- **Event Bus:** [Envelope transformation and routing logic]
- **Storage Layer:** [Schema migration and data transformation]
- **Integration Points:** [Cross-service communication adapters]

**Validation Strategy:**
- Contract validation with both old and new schemas
- Integration testing with dual-mode operation
- Performance testing under mixed traffic
- Rollback testing and validation

**Acceptance Criteria:**
- [ ] Complete change matrix documented
- [ ] Adapter strategy designed and located
- [ ] Migration phases clearly defined
- [ ] Observability plan implemented
- [ ] Migration documentation created
- [ ] PR checklist completed
- [ ] Rollback procedures validated
- [ ] Consumer communication plan ready

**Deliverables:**
- `contracts/MIGRATION-v<from>-to-v<to>.md` document
- Updated `POLICY_VERSIONING.md`
- Adapter implementation specifications
- Monitoring and observability plan
- Consumer integration guides
- Rollback procedures documentation

Please help me create a comprehensive migration plan for these breaking changes.
```

---

## 🛠️ **Adapter Implementation Strategy**

```
I need to design adapters for backward compatibility during migration:

**Adapter Requirements:**
- **Compatibility Scope:** [Which versions need support]
- **Transformation Logic:** [How to convert between formats]
- **Performance Impact:** [Acceptable overhead during transition]
- **Error Handling:** [How to handle conversion failures]

**Implementation Approach:**
- **API Adapters:** Request/response transformation layers
- **Event Adapters:** Envelope and payload conversion
- **Storage Adapters:** Schema migration and data transformation
- **Feature Flags:** Runtime control of adapter behavior

**Code Locations:**
- Where to place adapter logic
- Integration with existing middleware
- Configuration and feature flag setup
- Testing and validation approach

Please help me design the adapter implementation strategy.
```

---

## 📊 **Migration Monitoring & Rollback**

```
I need to plan monitoring and rollback procedures for contract migration:

**Monitoring Requirements:**
- **Traffic Patterns:** [Old vs new version usage]
- **Error Rates:** [Conversion failures and compatibility issues]
- **Performance Metrics:** [Latency and throughput impact]
- **Business Metrics:** [User experience and functionality impact]

**Rollback Triggers:**
- **Error Rate Thresholds:** [When to automatically rollback]
- **Performance Degradation:** [Acceptable impact limits]
- **Business Impact:** [User experience criteria]
- **Consumer Feedback:** [Issues reported by affected teams]

**Rollback Procedures:**
- Quick revert to previous contract version
- Adapter deactivation procedures
- Consumer notification process
- Post-rollback validation steps

**Success Criteria:**
- Migration completion metrics
- Consumer adoption rates
- System stability measurements
- Performance baseline maintenance

Please help me design comprehensive monitoring and rollback procedures.
```
````
