# attention\_gate/ — Thalamus‑Inspired Admission & Smart Routing

**Version:** attention-gate @ 2025-09-14T00:00:00Z
**Scope:** Single, authoritative spec for the `attention_gate/` component in FamilyOS. Explains **why** it exists, **how** it works, the **envelopes** it consumes/produces, where it **fits** in the memory system, the **algorithms** behind salience and intent derivation, and the **operational guardrails** (policy, privacy, backpressure). It is written to be understandable and maintainable far into the future.

---

## 0) Problem & Philosophy

**Problem.** FamilyOS receives heterogeneous, sometimes **untagged** or **low‑confidence** requests. We need a gate that decides whether to **admit**, **defer**, **boost**, or **drop** each request and—when untagged—**derive the right pipeline intent(s)** (e.g., `P02:WRITE`, `P01:RECALL`, `P05:PROSPECTIVE_SCHEDULE`). The decision must blend **policy safety** with **cognitive salience** and **resource budgets**.

**Neuroscience inspiration.** The design abstracts the **thalamus** as a central gating hub that allocates attentional resources and relays/broadcasts task‑relevant information; it is modulated by cortical and basal ganglia loops that provide dynamic **Go/No‑Go** gating for working memory and action selection. Empirical work shows **central thalamus** activity tracks “attentional effort,” and **PFC–Basal Ganglia** models explain dynamic gating for update vs. maintenance in working memory. Global Neuronal Workspace theory explains when selected content is **broadcast** for global access—our system analog is “admit + boost then broadcast.” ([PMC][1])

**ML inspiration.** We also borrow from **attention mechanisms** and **sparse routing (Mixture‑of‑Experts)**: different inputs activate different “experts,” but compute stays bounded. Our gate uses simple, auditable rules first, with optional small NN heads to improve derivation—never a black box at the edge. ([arXiv][2])

**Philosophy.**

* **Deterministic first, learnable later:** rules + thresholds first; pluggable light models second.
* **Safety before speed:** ABAC/RBAC and policy bands gate outcomes; default **fail‑closed**. ([NIST][3])
* **Edge‑first & auditable:** compact signals, bounded compute, and full decision traces.
* **Backpressure aware:** never overload downstream; bounded queues + reactive backpressure. ([GitHub][4])

---

## 1) Interfaces (Envelopes)

### 1.1 Input — Gate Decision Request

> Emitted by **API→PEP→Intent Router** when intent is missing or low‑confidence, or when policy requires gating.

```json
{
  "request_id": "req-2025-09-14-0001",
  "actor": {"person_id": "alice", "role": "member"},
  "space_id": "shared:household",
  "policy": {"band": "GREEN", "abac": {"device_trust": "high"}},
  "payload": {
    "text": "remind me tomorrow to call mom",
    "attachments": [],
    "hints": {"deadline": "2025-09-15T09:00:00Z"}
  },
  "declared_intent": null,
  "declared_confidence": 0.0,
  "signals": {
    "affect": {"valence": 0.1, "arousal": 0.65, "c": 0.7},          // optional
    "metacog": {"uncertainty": 0.35},                                // optional
    "qos": {"budget_ms": 15, "device_thermal": "Nominal"}            // optional
  },
  "context": {
    "recency": {"similar_requests_24h": 0},
    "social": {"child_present": false}
  },
  "trace_id": "trace-xyz123",
  "version": "gate:2025-09-14"
}
```

**Rules:** `request_id`, `actor.person_id`, `space_id`, `policy.band` required. Others optional; degrade gracefully.

---

### 1.2 Output — Gate Decision + Derived Intents

```json
{
  "gate_decision": {
    "action": "ADMIT",          // ADMIT | BOOST | DEFER | DROP
    "priority": 0.72,           // 0..1 after calibration
    "reasons": ["deadline_soon","low_cost","semantics:schedule"],
    "obligations": ["mask:pii:min"],   // policy obligations to attach
    "ttl_ms": 30000             // how long the decision is valid
  },
  "derived_intents": [
    {"intent": "PROSPECTIVE_SCHEDULE", "confidence": 0.91},
    {"intent": "HIPPO_ENCODE", "confidence": 0.80}
  ],
  "routing": {
    "topic": "bus.prospective.schedule",
    "deadline": "2025-09-15T09:00:00Z"
  },
  "trace": {
    "trace_id": "trace-xyz123",
    "features": {"urg": 0.8, "aff_a": 0.65, "novel": 0.9, "risk": 0.1},
    "thresholds": {"admit": 0.55, "boost": 0.75, "drop": 0.20}
  },
  "ts": "2025-09-14T00:00:01.000Z",
  "version": "gate:2025-09-14"
}
```

---

### 1.3 Observability / Telemetry

* **Counters:** `gate_decisions_total{action,intent}`
* **Histograms:** `gate_latency_seconds`, `priority_score`, `queue_depth`
* **Span tags:** `band`, `aff_a`, `urg`, `policy_obligations`, `backpressure_state`

---

## 2) System Fit (FamilyOS)

* **Fast‑path vs Gate‑path:** The **Intent Router** remains deterministic and cheap (validate header `agent_intent` + threshold). All **untagged/low‑confidence** go to Attention Gate.
* **Pre‑bus:** `attention_gate/` runs **before** the Event Bus; its outputs are **derived intents** and **policy obligations** for downstream subscribers.
* **Downstream subscribers:** `hippocampus/` (encode), `prospective/` (reminders), `retrieval/`, `learning/`, `arbitration/` (plans) act on emitted events.
* **Backpressure:** The gate exposes a bounded queue and participates in **Reactive Streams** backpressure to prevent overload. ([GitHub][4])

---

## 3) Algorithms & Math

### 3.1 Decision stages (auditable cascade)

1. **Policy & Schema checks (hard gates):** ABAC/RBAC, band limits, payload shape → may **DROP** or **DEFER**. (NIST SP 800‑162 defines ABAC.) ([NIST][3])
2. **Intent derivation (when missing/ambiguous):**

   * **Rules/grammar:** lightweight patterns (e.g., “remind me…”, “find…”, “save…”) produce proto‑intents.
   * **Optional NN head:** tiny ONNX text classifier to refine (`SCHEDULE`, `RECALL`, `WRITE`, `PROJECT`).
   * **Confidence fusion:** max‑entropy (rules) + classifier prob with calibration (Platt/temperature).
3. **Salience scoring & cost side‑checks:** compute **priority** ∈ \[0,1].
4. **Backpressure policy:** adjust action by system load (see 3.5).
5. **Action selection:** choose **ADMIT/BOOST/DEFER/DROP** and attach obligations.

### 3.2 Salience & utility score

We combine features inspired by **biased competition** and **thalamic allocation of attentional effort**: urgency, novelty, predicted value, risk, affect arousal, social context, and policy costs. ([PMC][5])

Let features $x = \{u$rgency, $n$ovelty, $v$alue, $r$isk, $a$ffect\_arousal, $c$ost, $s$ocial\_risk$\}$.
Raw score:

$$
S = w_u u + w_n n + w_v v - w_r r + w_a a - w_c c - w_s s + b
$$

Calibrated priority:

$$
\text{priority} = \sigma\big(\alpha\,S + \beta\,\text{context\_bump}\big)
$$

Default weights are conservative (`risk` and `cost` penalize strongly). Bias terms (e.g., **child\_present**) increase safety penalty.

**Notes.**

* **Urgency** from deadlines / temporal proximity.
* **Novelty** from short‑window dedupe.
* **Affect arousal** from `affect/` (if available).
* **Value** via heuristics (e.g., saving notes > generic chat).
* **Risk** blends policy band + toxicity/light safety flags.
* **Cost** uses device/runtime budgets.

### 3.3 Intent derivation (rules + optional NN)

**Rule atoms → intents:**

* `/(remind|tomorrow|in \d+ (min|hour|day)s?)/i` → `PROSPECTIVE_SCHEDULE`
* `/^(find|search|where|show me)/i` → `RECALL`
* `/^(save|remember|note|log)/i` → `WRITE`
* `/^(plan|schedule .*meeting|draft itinerary)/i` → `PROJECT`

**Optional NN head.** A tiny intent classifier improves coverage for colloquialisms; calibrated outputs are used only to **raise** confidence (never to bypass policy). (Inspired by ML attention/routing and sparse‑gated MoE, but run at small scale.) ([arXiv][2])

### 3.4 Working‑memory style gating (why “gate”?)

Our **open/close** gating mirrors **PFC–Basal Ganglia** loops: a **Go/No‑Go** style decision updates or maintains working state; here we “update” the system’s workflow by **admitting** and **broadcasting** salient content, and “hold” by **deferring/dropping** low‑salience or unsafe items. This analogy motivates binary/tri‑state thresholds and separate **update vs. maintain** control. ([PMC][6])

### 3.5 Load & backpressure control

To keep the system stable, the gate enforces **bounded queues** and participates in **Reactive Streams** style non‑blocking backpressure: if subscribers are slow, the gate **DEFERs** or **DOWN‑BANDS** items and eventually **DROPs** with audit when budgets are exceeded. (Use DRR or simple token bucket for fairness and burst control.) ([GitHub][4])

**Token bucket (per space & per actor):**

* rate $r$ tokens/sec; burst $b$; each ADMIT consumes 1 token; budget refill per schedule. ([Wikipedia][7])

**Deficit Round Robin (optional):**

* fair multiplexing across spaces/actors with minimal overhead. ([ACM Digital Library][8])

**Circuit‑breaker (drop‑to‑safe):**

* if downstream topics fail repeatedly, open breaker and **DEFER/DROP** until health recovers, preventing cascades. ([GeeksforGeeks][9])

---

## 4) Privacy & Policy

* **Policy first:** ABAC rules (NIST SP 800‑162) evaluated before scoring; attach obligations (`mask`, `redact`, `defer`) to all admits. ([NIST][3])
* **Minimal signals:** Gate consumes compact scores (e.g., affect scalars), not raw audio/video.
* **Space‑scoped:** All decisions and traces are scoped to `space_id`; events encrypted per space keys.
* **Auditability:** Every decision includes `reasons` and the feature vector snapshot.

---

## 5) Error Handling & Validation

* **Missing fields:** degrade gracefully; set `priority` lower and include `reason:"missing_field:x"`.
* **Schema violations / unsafe band:** **DROP** with policy reason.
* **Overload:** return `DEFER` with retry hint; if breaker open → **DROP** with `reason:"downstream_unhealthy"`.

---

## 6) Example (end‑to‑end)

**Input:** “remind me tomorrow to call mom” (untagged).
**Gate:** rules → `PROSPECTIVE_SCHEDULE` (0.86); salience high (`urg=0.8`, `novel=0.9`, `cost=low`).
**Decision:** `BOOST`, `priority=0.78`, obligations `mask:pii:min`.
**Emit:** `bus.prospective.schedule` + `hippocampus.encode`.

---

## 7) Implementation Sketch

### 7.1 Config (YAML)

```yaml
# config/attention_gate.yaml
bands:
  deny: [BLACK]
  review: [RED]
admit_threshold: 0.55
boost_threshold: 0.75
drop_threshold: 0.20
weights:
  urgency: 1.2
  novelty: 0.8
  value:   0.6
  risk:    1.4
  affect_a: 0.3
  cost:     0.9
  social:   1.0
fairness:
  token_bucket:
    rate_per_actor: 2    # tokens/sec
    burst_per_actor: 5
  drb_round_bytes: 4096
breaker:
  fail_window: 30s
  fail_threshold: 0.25
  half_open_after: 15s
```

### 7.2 Pseudocode (deterministic core)

```python
def gate(request, cfg, classifiers=None, load=None):
    # 1) Policy & schema
    if request.policy.band in cfg.bands.deny:
        return drop("policy_band")
    if not minimal_schema_ok(request):
        return drop("schema_invalid")

    # 2) Intent derivation
    intents = rule_intents(request.payload.text)
    if classifiers and not intents:
        intents = nn_intents(request.payload.text, classifiers)  # calibrated

    if not intents:
        intents = [{"intent": "HIPPO_ENCODE", "confidence": 0.6}]  # safe default

    # 3) Salience & cost
    feats = extract_features(request, load)  # urg, novel, val, risk, affect_a, cost, social
    S = dot(cfg.weights, feats) + bias(feats)
    priority = sigmoid(alpha*S + beta*context_bump(request))

    # 4) Backpressure
    if over_budget(request.actor):
        return defer("rate_limited", priority)
    if breaker_open("bus.prospective.schedule"):
        return defer("downstream_unhealthy", priority)

    # 5) Action selection
    if priority < cfg.drop_threshold:   return drop("low_priority", priority)
    if priority >= cfg.boost_threshold: return boost(intents, priority)
    if priority >= cfg.admit_threshold: return admit(intents, priority)
    return defer("borderline", priority)
```

### 7.3 Topics & subscribers

* `bus.gate.decisions.audit` — full decision traces for observability.
* `bus.[pipeline].in` — derived intents (e.g., `bus.prospective.schedule`, `bus.hippo.encode`).

### 7.4 Metrics

* `gate_decisions_total{action}`
* `gate_priority_score` (histogram)
* `gate_queue_depth`, `breaker_state`
* `intents_derived_total{intent}`

---

## 8) Test Plan (MVP)

1. **Policy gates:** RED/BLACK bands always **DROP/DEFER**; GREEN admits when priority ≥ threshold.
2. **Intent derivation:** unit tests on rules; shadow tests comparing rules vs. NN head; NN must never increase risk.
3. **Backpressure:** synthetic load opens breaker; verify **DEFER** then automatic recovery to **ADMIT**.
4. **Audit:** 100% of decisions emit `reasons` + features; PII never appears in traces.
5. **Fairness:** token‑bucket limits per actor/space verified under contention.

---

## 9) References (selected)

**Neuroscience & Cognitive Architecture**

* **Central thalamus & attentional effort.** Schiff et al., *J. Neurophysiology*, 2013/2012 (PMCID: PMC3569130). Shows thalamic neurons regulate short‑term shifts of attentional effort. ([Physiological Journals][10])
* **Biased competition theory.** Reviews and spiking models explaining attention as competition modulated by top‑down bias. ([Physiological Journals][11])
* **PFC–Basal Ganglia working‑memory gating.** Frank, O’Reilly et al. computational models of dynamic gating for update vs. maintenance; “executive without a homunculus.” ([SpringerLink][12])
* **Global Neuronal Workspace (broadcasting).** Dehaene & Changeux: selected content is globally broadcast—our analog for **boost/broadcast**. ([MIT Press Direct][13])

**Machine Learning & Routing**

* **Attention mechanisms.** “Attention Is All You Need.” Transformer as attention‑only architecture. ([arXiv][2])
* **Conditional computation & sparse routing.** Mixture‑of‑Experts (Shazeer et al., 2017) and Switch Transformer (Fedus et al., 2021). ([arXiv][14])

**Policy & Backpressure**

* **ABAC (NIST SP 800‑162).** Attribute‑based access control; we evaluate subject/object/environment attributes against policy. ([NIST][3])
* **Reactive Streams / backpressure (JVM spec & guide).** Non‑blocking backpressure to avoid unbounded buffers. ([GitHub][4])
* **Deficit Round Robin (fair queuing).** Classic fair scheduler for low‑overhead fairness. ([ACM Digital Library][8])
* **Token bucket.** Standard burst control. ([Wikipedia][7])

---

## 10) Files (orientation)

* `gate_service.py` — service entry; HTTP/IPC handler pre‑bus.
* `intent_rules.py` — deterministic rules for derivation.
* `intent_head_onnx.py` — optional tiny classifier + calibration.
* `salience.py` — feature extraction & priority scoring.
* `backpressure.py` — token bucket, DRR scheduler, circuit‑breaker shims.
* `policy_bridge.py` — ABAC check & obligation attachment.
* `trace.py` — decision traces with feature snapshots (no PII).
* `config/attention_gate.yaml` — thresholds, weights, fairness settings.
* `tests/` — unit + load + safety tests (policy, backpressure, audit).

---

**Stewardship.** Keep the gate **deterministic** and **auditable**. Treat learned components as **advisors**, not authorities. When in doubt: **fail‑closed**, **defer**, and **explain**.

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3569130/?utm_source=chatgpt.com "Gating of attentional effort through the central thalamus - PMC"
[2]: https://arxiv.org/abs/1706.03762v4?utm_source=chatgpt.com "[1706.03762v4] Attention Is All You Need"
[3]: https://www.nist.gov/publications/guide-attribute-based-access-control-abac-definition-and-considerations-0?utm_source=chatgpt.com "Guide to Attribute Based Access Control (ABAC) Definition and Considerations | NIST"
[4]: https://github.com/reactive-streams/reactive-streams-jvm?utm_source=chatgpt.com "GitHub - reactive-streams/reactive-streams-jvm: Reactive Streams Specification for the JVM"
[5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC2740806/?utm_source=chatgpt.com "Top-down and bottom-up mechanisms in biasing competition in the human brain - PMC"
[6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC2440774/?utm_source=chatgpt.com "Towards an executive without a homunculus: computational models of the prefrontal cortex/basal ganglia system - PMC"
[7]: https://en.wikipedia.org/wiki/Token_bucket?utm_source=chatgpt.com "Token bucket"
[8]: https://dl.acm.org/doi/abs/10.1145/217382.217453?utm_source=chatgpt.com "Efficient fair queueing using deficit round robin | Proceedings of the conference on Applications, technologies, architectures, and protocols for computer communication"
[9]: https://www.geeksforgeeks.org/microservices-resilience-patterns/?utm_source=chatgpt.com "Microservices Resilience Patterns - GeeksforGeeks"
[10]: https://journals.physiology.org/doi/full/10.1152/jn.00317.2011?utm_source=chatgpt.com "Gating of attentional effort through the central thalamus | Journal of Neurophysiology | American Physiological Society"
[11]: https://journals.physiology.org/doi/full/10.1152/jn.01095.2004?utm_source=chatgpt.com "Neurodynamics of Biased Competition and Cooperation for Attention: A Model With Spiking Neurons | Journal of Neurophysiology | American Physiological Society"
[12]: https://link.springer.com/article/10.3758/cabn.1.2.137?utm_source=chatgpt.com "Interactions between frontal cortex and basal ganglia in working memory: A computational model | Cognitive, Affective, & Behavioral Neuroscience"
[13]: https://direct.mit.edu/netn/article/6/4/1186/111960/The-global-neuronal-workspace-as-a-broadcasting?utm_source=chatgpt.com "The global neuronal workspace as a broadcasting network | Network Neuroscience | MIT Press"
[14]: https://arxiv.org/abs/1701.06538?utm_source=chatgpt.com "[1701.06538] Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer"
