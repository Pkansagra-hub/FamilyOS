# Metacognition (Monitor) Contract (v1.0.0)

**Scope:** Metacognitive monitoring and reflection - system self-awareness, confidence estimation, error detection, and cognitive reflection.

**Purpose:** Provides the cognitive architecture with self-monitoring capabilities, enabling the system to understand its own cognitive processes, detect errors, estimate confidence, and engage in reflective reasoning about its performance.

## Architecture Integration

### From Diagram References:
- **metacognition/monitor.py** - Core metacognitive monitoring
- **metacognition/confidence.py** - Confidence estimation and calibration
- **metacognition/error_detector.py** - Error detection and correction
- **metacognition/reflection.py** - Reflective reasoning processes

### Metacognitive Functions:
1. **Process Monitoring** - Track cognitive process execution
2. **Confidence Estimation** - Assess certainty in decisions/predictions
3. **Error Detection** - Identify potential mistakes or failures
4. **Performance Reflection** - Analyze cognitive performance patterns
5. **Strategy Selection** - Choose appropriate cognitive strategies

## Event-Driven Interface

**Consumes:**
- `ACTION_DECISION@1.0` - For decision confidence monitoring
- `RECALL_RESULT@1.0` - For retrieval confidence assessment
- `PREDICTION_COMPUTED@1.0` - For prediction confidence analysis
- `WORKSPACE_BROADCAST@1.0` - For working memory monitoring
- `ACTION_EXECUTED@1.0` - For outcome-based error detection

**Emits:**
- `METACOG_REPORT@1.0` - Metacognitive assessment reports
- `CONFIDENCE_UPDATE@1.0` - Confidence score updates
- `ERROR_DETECTED@1.0` - Error detection alerts
- `REFLECTION_COMPLETE@1.0` - Reflection process outcomes
- `STRATEGY_SELECTED@1.0` - Cognitive strategy choices

## Storage Schema

### Core Entities:
- **metacog_session** - Metacognitive monitoring session
- **confidence_estimate** - Confidence scores and calibration
- **error_detection** - Detected errors and corrections
- **reflection_result** - Reflection process outcomes
- **strategy_selection** - Chosen cognitive strategies
- **performance_pattern** - Long-term performance patterns

### Retention:
- **Metacog sessions**: P30D (recent monitoring)
- **Confidence estimates**: P90D (calibration analysis)
- **Error detections**: P180D (learning from mistakes)
- **Reflection results**: P60D (strategy optimization)
- **Performance patterns**: P365D (long-term trends)

## Metacognitive Processes

### Monitoring Functions:
```yaml
monitor_decision_confidence:
  input: { decision_context, outcome_uncertainty }
  output: { confidence_score, uncertainty_factors }

detect_cognitive_errors:
  input: { process_trace, expected_outcome }
  output: { error_type, severity, correction_suggestion }

assess_strategy_effectiveness:
  input: { strategy_used, performance_metrics }
  output: { effectiveness_score, improvement_suggestions }

reflect_on_performance:
  input: { recent_actions, outcomes, goals }
  output: { reflection_insights, strategy_adjustments }
```

### Confidence Calibration:
- **Overconfidence Detection** - Identify overconfident predictions
- **Underconfidence Analysis** - Detect conservative biases
- **Calibration Curves** - Maintain prediction reliability
- **Uncertainty Quantification** - Proper uncertainty estimation

## Security & Privacy

### RBAC Permissions:
- **metacog.monitor** - View monitoring data (GREEN)
- **metacog.confidence** - Access confidence scores (AMBER)
- **metacog.errors** - View error detection results (RED)
- **metacog.admin** - Modify metacognitive parameters (BLACK)

### Privacy Controls:
- Monitoring data aggregated to protect individual traces
- Error detection logs sanitized of sensitive content
- Reflection results use anonymized decision patterns
- Confidence scores computed without exposing raw data

## Error Detection & Correction

### Error Types:
1. **Logical Errors** - Inconsistent reasoning patterns
2. **Knowledge Errors** - Incorrect factual assumptions
3. **Strategy Errors** - Inappropriate cognitive strategies
4. **Confidence Errors** - Miscalibrated certainty estimates
5. **Goal Errors** - Misaligned objective pursuit

### Correction Mechanisms:
- **Immediate Correction** - Real-time error intervention
- **Retrospective Analysis** - Post-hoc error examination
- **Strategy Adjustment** - Cognitive strategy modification
- **Confidence Recalibration** - Uncertainty estimation tuning

## Performance Characteristics

### Processing Latency:
- Confidence estimation: p95 ≤ 15ms
- Error detection: p95 ≤ 100ms
- Reflection processing: p95 ≤ 2s
- Strategy selection: p95 ≤ 50ms

### Quality Metrics:
- Confidence calibration: ECE ≤ 0.05
- Error detection accuracy: F1 ≥ 0.8
- Reflection insight quality: Human-rated ≥ 7/10
- Strategy effectiveness: Performance improvement ≥ 5%

### Operational Metrics:
- Monitoring coverage rate
- Error detection frequency
- Reflection trigger rate
- Strategy change frequency

## Dependencies

### Upstream:
- **arbitration/** - Decision making processes
- **retrieval/** - Recall confidence assessment
- **cortex/** - Prediction confidence analysis
- **core/** - Working memory monitoring
- **action/** - Action execution outcomes

### Downstream:
- **learning/** - Error-based learning signals
- **arbitration/** - Strategy selection input
- **core/** - Working memory management
- **cortex/** - Model confidence calibration

## Reflection Processes

### Reflection Triggers:
- **Performance Degradation** - Below-threshold performance
- **Error Accumulation** - Multiple detected errors
- **Goal Misalignment** - Off-track objective pursuit
- **Strategy Ineffectiveness** - Poor strategy performance
- **Scheduled Reflection** - Periodic self-assessment

### Reflection Outputs:
- **Performance Insights** - Understanding of cognitive patterns
- **Strategy Recommendations** - Improved cognitive approaches
- **Confidence Adjustments** - Better uncertainty estimation
- **Goal Refinements** - Clarified objectives
- **Learning Priorities** - Areas needing improvement

## Implementation Notes

- Metacognition operates with **minimal performance overhead**
- Confidence estimates are **continuously calibrated**
- Error detection uses **multiple validation methods**
- Reflection processes are **goal-driven and contextual**
- All metacognitive data respects **privacy boundaries**
- Strategy selection balances **exploration and exploitation**

---

*Metacognition module enables cognitive self-awareness and continuous improvement of thinking processes.*
