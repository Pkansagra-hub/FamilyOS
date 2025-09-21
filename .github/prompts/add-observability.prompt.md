````prompt
# 📊 Observability Integration Prompts

Use these prompts when adding comprehensive observability (metrics, traces, logs) to code changes.

---

## 🔍 **Add Observability to Code Changes**

```
I need to add proper observability to a code change or module:

**Code Context:**
- **Module/Component:** [Which component needs observability]
- **Change Type:** [New feature/Bug fix/Refactor/Performance improvement]
- **Code Diff/Files:** [Specific files or diff to instrument]
- **Business Logic:** [What the code does functionally]

**Observability Requirements:**
- **Metrics:** Prometheus metrics with `familyos_*` naming convention
- **Traces:** Distributed tracing with proper span naming
- **Logs:** Structured JSON logging with correlation IDs
- **SLO Integration:** Metrics aligned with SLO buckets and targets

**Implementation Checklist:**
1. **Prometheus Metrics:**
   - Use `familyos_*` naming convention
   - Include SLO-aligned histogram buckets
   - Add business-relevant labels
   - Counter/Gauge/Histogram as appropriate

2. **Distributed Tracing:**
   - Import from `observability/trace.py`
   - Use pattern: `start_span("{area}.{component}.{method}")`
   - Include relevant span attributes
   - Proper span lifecycle management

3. **Structured Logging:**
   - JSON format with correlation IDs
   - Include business context
   - Appropriate log levels
   - No PII in logs

4. **Test Coverage:**
   - Assert key metrics exist in tests
   - Verify span creation and attributes
   - Test log output structure
   - Performance test with observability overhead

**Validation Steps:**
- Run VS Code task `ci:fast` or equivalent
- Verify metrics appear in test output
- Check span creation in trace logs
- Validate structured log format

**Acceptance Criteria:**
- [ ] Metrics follow `familyos_*` naming convention
- [ ] Traces use proper span naming pattern
- [ ] Logs are structured JSON with correlation IDs
- [ ] Tests validate observability instrumentation
- [ ] SLO buckets are properly configured
- [ ] No PII leaked in telemetry data
- [ ] CI validation passes

Please help me implement comprehensive observability for this code change.
```

---

## 🔧 **Observability Troubleshooting**

```
I'm having issues with observability implementation:

**Problem Details:**
- **Issue Type:** [Metrics not appearing/Traces not working/Logs malformed/etc.]
- **Component:** [Which service/module has issues]
- **Error Messages:** [Specific observability-related errors]
- **Expected Behavior:** [What should be happening]

**Current Implementation:**
- **Metrics Added:** [List metrics that were added]
- **Spans Created:** [List trace spans]
- **Log Statements:** [Logging implementation details]
- **Test Coverage:** [What observability tests exist]

**Environment Context:**
- **Local Development:** [Works locally or not]
- **CI/CD Pipeline:** [Pipeline observability status]
- **Telemetry Backend:** [Prometheus/Jaeger/etc. configuration]

Please help me diagnose and fix the observability implementation issues.
```

---

## 📈 **Performance Impact Assessment**

```
I need to assess the performance impact of adding observability:

**Baseline Metrics:**
- **Current Performance:** [Existing latency/throughput numbers]
- **Resource Usage:** [CPU/Memory utilization]
- **Hot Paths:** [Critical performance paths]

**Observability Overhead:**
- **Metrics Collection:** [Number and frequency of metrics]
- **Trace Sampling:** [Sampling rate and span complexity]
- **Log Volume:** [Logging frequency and payload size]

**Assessment Criteria:**
- Acceptable performance overhead < 5%
- Memory increase < 10%
- No impact on critical user-facing latency
- SLO targets maintained

Please help me evaluate and optimize the observability performance impact.
```
````
