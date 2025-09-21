# 🐛 Bug Fix Development Prompts

Use these prompts when fixing bugs to ensure proper analysis, implementation, and validation.

---

## 🔍 **Bug Analysis Request**

```
I found a bug that needs investigation and fixing:

**Bug Information:**
- **Title:** [Specific error description - avoid generic terms]
- **Severity:** [Critical/High/Medium/Low]
- **Component:** [Exact service/module: memory_steward, hippocampus, api/routers/memory.py]
- **Environment:** [dev|staging|prod|local]

**Bug Description:**
- **Symptoms:** [Specific behaviors: HTTP 500 errors, memory leaks, slow queries]
- **Expected Behavior:** [Concrete expected outcome]
- **Actual Behavior:** [Exact current behavior with measurements]
- **Reproduction Steps:** [Exact API calls, user actions, or test commands]

**Impact Assessment:**
- **Users Affected:** [Specific count/percentage: 10% of users, all admin users]
- **Business Impact:** [Measurable effect: reduced throughput by 50%, data loss risk]
- **Data Impact:** [Specific data issues: corrupted records, missing entries]
- **Workarounds:** [Temporary solutions currently in place]

**Investigation Done:**
- **Logs Checked:** [Specific files: logs/memory_service.log, logs/error.log]
- **Code Analysis:** [Exact functions/classes examined]
- **Recent Changes:** [Specific deployments: v1.2.3 deployed 2h ago]
- **Performance Data:** [Metrics: response time increased from 100ms to 2s]

**Technical Details:**
- **Error Messages:** [Exact error text from logs]
- **Stack Traces:** [Full Python tracebacks]
- **Environment Info:** [Python 3.11, Poetry venv, Ubuntu 22.04]
- **Dependencies:** [Recent version changes, new packages]

**Debugging Commands to Run:**
- [ ] `python -m ward test --path tests/component/test_[affected_service].py`
- [ ] `python scripts/debug/analyze_logs.py [service-name] --since "1 hour ago"`
- [ ] `python contracts/automation/validation_helper.py --service [service-name]`
- [ ] `python -m pytest tests/integration/test_[service]_integration.py -v`
- [ ] `python scripts/performance/profile_service.py [service-name]`

Please help me analyze this bug systematically and plan an appropriate fix.
```

---

## 🔧 **Bug Fix Implementation Request**

```
I'm ready to implement a fix for a bug. Please help me:

**Bug Details:**
- **Bug ID/Title:** [Bug identifier]
- **Root Cause:** [What's causing the issue]
- **Affected Components:** [Services/modules involved]

**Proposed Fix:**
- **Approach:** [How to fix the issue]
- **Code Changes:** [What code needs modification]
- **Configuration Changes:** [Any config updates]
- **Data Changes:** [Any data migrations/fixes]

**Fix Scope:**
- **Files to Modify:** [List specific files]
- **New Code Required:** [Any new functionality]
- **Deprecated Code:** [Code to remove/replace]
- **Dependencies:** [External dependency changes]

**Risk Assessment:**
- **Breaking Changes:** [Will this break anything]
- **Performance Impact:** [Effect on performance]
- **Side Effects:** [Unintended consequences]
- **Rollback Plan:** [How to undo if needed]

**Testing Strategy:**
- **Unit Tests:** [New/modified tests needed]
- **Integration Tests:** [Cross-component testing]
- **Regression Tests:** [Ensure no new bugs]
- **Manual Testing:** [User workflow validation]

**Contract Impact:**
- **API Changes:** [Any API modifications]
- **Event Changes:** [Event schema changes]
- **Storage Changes:** [Data schema modifications]
- **Version Bump:** [MAJOR/MINOR/PATCH needed]

Please implement this fix following best practices and proper validation.
```

---

## 🚨 **Critical Bug Hotfix Request**

```
URGENT: Critical bug needs immediate hotfix

**Critical Bug Information:**
- **Severity:** Critical/Production Down
- **Impact:** [Production systems affected]
- **Users Affected:** [Number/type of users]
- **Business Impact:** [Revenue/operations impact]

**Incident Details:**
- **Start Time:** [When issue began]
- **Detection Method:** [How we found out]
- **Current Status:** [System state now]
- **Immediate Actions Taken:** [What's been done]

**Root Cause:**
- **Primary Cause:** [Main reason for failure]
- **Contributing Factors:** [Other factors involved]
- **Code Location:** [Specific code causing issue]
- **Recent Changes:** [Related deployments/changes]

**Hotfix Requirements:**
- **Minimal Fix:** [Smallest possible change]
- **Risk Assessment:** [Hotfix risks]
- **Testing Strategy:** [Fast validation approach]
- **Deployment Plan:** [Emergency deployment steps]

**Communication:**
- **Stakeholders Notified:** [Who has been informed]
- **Status Updates:** [How often to update]
- **Resolution ETA:** [Expected fix time]
- **Post-Mortem Plan:** [Follow-up analysis]

**Rollback Plan:**
- **Rollback Triggers:** [When to rollback]
- **Rollback Time:** [How long to rollback]
- **Rollback Testing:** [How to verify rollback]
- **Data Recovery:** [Any data restoration needed]

Please prioritize this critical fix and follow emergency procedures.
```

---

## 🔄 **Bug Fix Validation Request**

```
I've implemented a bug fix and need comprehensive validation:

**Fix Information:**
- **Bug Title:** [Original bug description]
- **Fix Description:** [What was changed]
- **Files Modified:** [List changed files]
- **Deployment Status:** [Where fix is deployed]

**Validation Requirements:**
- **Bug Resolution:** [Verify original issue fixed]
- **Regression Testing:** [Ensure no new issues]
- **Performance Impact:** [Check performance effect]
- **Integration Validation:** [Cross-component testing]

**Test Coverage:**
- **Automated Tests:** [Unit/integration tests run]
- **Manual Testing:** [Manual validation done]
- **User Acceptance:** [User workflow testing]
- **Load Testing:** [Performance under load]

**Monitoring Setup:**
- **Error Monitoring:** [Watch for new errors]
- **Performance Monitoring:** [Track performance metrics]
- **Business Metrics:** [Monitor business impact]
- **Alerting:** [Set up alerts for issues]

**Verification Checklist:**
- [ ] Original bug symptoms resolved
- [ ] No new errors introduced
- [ ] Performance within acceptable range
- [ ] All tests passing
- [ ] User workflows functional
- [ ] Monitoring shows healthy metrics

**Documentation:**
- **Fix Documentation:** [Document what was fixed]
- **User Communication:** [Notify affected users]
- **Knowledge Base:** [Update troubleshooting docs]
- **Post-Mortem:** [Schedule follow-up analysis]

Please validate this fix comprehensively before considering it complete.
```
- **Logs Reviewed:** [What logs checked]
- **Code Analysis:** [Code sections examined]
- **Recent Changes:** [Recent deployments/changes]
- **Similar Issues:** [Related bugs/patterns]

**Additional Context:**
- **Error Messages:** [Specific error text]
- **Stack Traces:** [Technical error details]
- **Environment Info:** [OS/version/config details]
- **Timing:** [When did this start happening]

Please help me analyze this bug and plan an appropriate fix.
```

---

## 🔧 **Bug Fix Implementation Request**

```
I'm ready to implement a fix for a bug. Please help me:

**Bug Details:**
- **Bug ID/Title:** [Bug identifier]
- **Root Cause:** [What's causing the issue]
- **Affected Components:** [Services/modules involved]

**Proposed Fix:**
- **Approach:** [How to fix the issue]
- **Code Changes:** [What code needs modification]
- **Configuration Changes:** [Any config updates]
- **Data Changes:** [Any data migrations/fixes]

**Fix Scope:**
- **Files to Modify:** [List specific files]
- **New Code Required:** [Any new functionality]
- **Deprecated Code:** [Code to remove/replace]
- **Dependencies:** [External dependency changes]

**Risk Assessment:**
- **Breaking Changes:** [Will this break anything]
- **Performance Impact:** [Effect on performance]
- **Side Effects:** [Unintended consequences]
- **Rollback Plan:** [How to undo if needed]

**Testing Strategy:**
- **Unit Tests:** [New/modified tests needed]
- **Integration Tests:** [Cross-component testing]
- **Regression Tests:** [Ensure no new bugs]
- **Manual Testing:** [User workflow validation]

**Contract Impact:**
- **API Changes:** [Any API modifications]
- **Event Changes:** [Event schema changes]
- **Storage Changes:** [Data schema modifications]
- **Version Bump:** [MAJOR/MINOR/PATCH needed]

Please implement this fix following best practices and proper validation.
```

---

## 🚨 **Critical Bug Hotfix Request**

```
URGENT: Critical bug needs immediate hotfix

**Critical Bug Information:**
- **Severity:** Critical/Production Down
- **Impact:** [Production systems affected]
- **Users Affected:** [Number/type of users]
- **Business Impact:** [Revenue/operations impact]

**Incident Details:**
- **Start Time:** [When issue began]
- **Detection Method:** [How we found out]
- **Current Status:** [System state now]
- **Immediate Actions Taken:** [What's been done]

**Root Cause:**
- **Primary Cause:** [Main reason for failure]
- **Contributing Factors:** [Other factors involved]
- **Code Location:** [Specific code causing issue]
- **Recent Changes:** [Related deployments/changes]

**Hotfix Requirements:**
- **Minimal Fix:** [Smallest possible change]
- **Risk Assessment:** [Hotfix risks]
- **Testing Strategy:** [Fast validation approach]
- **Deployment Plan:** [Emergency deployment steps]

**Communication:**
- **Stakeholders Notified:** [Who has been informed]
- **Status Updates:** [How often to update]
- **Resolution ETA:** [Expected fix time]
- **Post-Mortem Plan:** [Follow-up analysis]

**Rollback Plan:**
- **Rollback Triggers:** [When to rollback]
- **Rollback Time:** [How long to rollback]
- **Rollback Testing:** [How to verify rollback]
- **Data Recovery:** [Any data restoration needed]

Please prioritize this critical fix and follow emergency procedures.
```

---

## 🔄 **Bug Fix Validation Request**

```
I've implemented a bug fix and need comprehensive validation:

**Fix Information:**
- **Bug Title:** [Original bug description]
- **Fix Description:** [What was changed]
- **Files Modified:** [List changed files]
- **Deployment Status:** [Where fix is deployed]

**Validation Requirements:**
- **Bug Resolution:** [Verify original issue fixed]
- **Regression Testing:** [Ensure no new issues]
- **Performance Impact:** [Check performance effect]
- **Integration Validation:** [Cross-component testing]

**Test Coverage:**
- **Automated Tests:** [Unit/integration tests run]
- **Manual Testing:** [Manual validation done]
- **User Acceptance:** [User workflow testing]
- **Load Testing:** [Performance under load]

**Monitoring Setup:**
- **Error Monitoring:** [Watch for new errors]
- **Performance Monitoring:** [Track performance metrics]
- **Business Metrics:** [Monitor business impact]
- **Alerting:** [Set up alerts for issues]

**Verification Checklist:**
- [ ] Original bug symptoms resolved
- [ ] No new errors introduced
- [ ] Performance within acceptable range
- [ ] All tests passing
- [ ] User workflows functional
- [ ] Monitoring shows healthy metrics

**Documentation:**
- **Fix Documentation:** [Document what was fixed]
- **User Communication:** [Notify affected users]
- **Knowledge Base:** [Update troubleshooting docs]
- **Post-Mortem:** [Schedule follow-up analysis]

Please validate this fix comprehensively before considering it complete.
```

---

## 📊 **Bug Pattern Analysis Request**

```
I'm seeing recurring bugs and need pattern analysis:

**Bug Pattern Information:**
- **Pattern Type:** [Similar symptoms/causes]
- **Frequency:** [How often occurring]
- **Affected Components:** [Common components involved]
- **Time Pattern:** [When bugs typically occur]

**Recent Bug List:**
- **Bug 1:** [Brief description and date]
- **Bug 2:** [Brief description and date]
- **Bug 3:** [Brief description and date]
- [Add more as needed]

**Common Factors:**
- **Code Areas:** [Common code sections]
- **Dependencies:** [Shared dependencies]
- **Environment Factors:** [Common conditions]
- **User Patterns:** [Common user behaviors]

**Impact Analysis:**
- **User Experience:** [Effect on users]
- **System Stability:** [Effect on system]
- **Development Velocity:** [Effect on development]
- **Business Operations:** [Effect on business]

**Prevention Strategy:**
- **Code Improvements:** [Structural changes needed]
- **Testing Enhancements:** [Better test coverage]
- **Monitoring Improvements:** [Better detection]
- **Process Changes:** [Development process improvements]

**Investigation Goals:**
- [ ] Identify root cause patterns
- [ ] Develop prevention strategies
- [ ] Improve detection methods
- [ ] Create better testing approaches
- [ ] Update development practices

Please help me analyze these bug patterns and develop prevention strategies.
```

---

## 🛡️ **Bug Prevention Request**

```
I want to prevent bugs proactively in my code area:

**Code Area Information:**
- **Component:** [Service/module to protect]
- **Current Bug Rate:** [Historical bug frequency]
- **Risk Factors:** [Known areas of concern]
- **Complexity Level:** [High/Medium/Low complexity]

**Prevention Strategies Needed:**
- **Code Quality:** [Static analysis, reviews]
- **Testing Strategy:** [Comprehensive test coverage]
- **Monitoring:** [Early detection systems]
- **Documentation:** [Clear usage guidelines]

**Specific Concerns:**
- **Error-Prone Areas:** [Known trouble spots]
- **Integration Points:** [Complex interactions]
- **Performance Bottlenecks:** [Performance-sensitive code]
- **Security Vulnerabilities:** [Security-critical areas]

**Quality Improvements:**
- **Code Standards:** [Coding guidelines enforcement]
- **Review Process:** [Code review requirements]
- **Automated Testing:** [CI/CD testing pipeline]
- **Static Analysis:** [Code quality tools]

**Monitoring & Detection:**
- **Error Tracking:** [Error monitoring setup]
- **Performance Monitoring:** [Performance tracking]
- **User Feedback:** [User issue reporting]
- **Automated Alerting:** [Proactive issue detection]

**Success Metrics:**
- [ ] Reduced bug report frequency
- [ ] Faster bug detection
- [ ] Improved code quality scores
- [ ] Better test coverage
- [ ] Enhanced user satisfaction

Please help me implement comprehensive bug prevention for this component.
```
