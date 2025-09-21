# affect/ — Enhanced Affect System (Edge-First, Family‑Safe)
**Version:** affect-enhanced @ 2025-09-04T22:40:06Z  
**Scope:** This document is the single, authoritative spec for the `affect/` component in Family OS. It explains **why** it exists, **how** it works, **what** envelopes it consumes/produces, **how it fits** into the memory system, and the **math** behind it. It is written to be understandable and maintainable even a century from now.

---

## 0) Problem & Philosophy

Families need assistants that **understand tone** without violating privacy. We approximate **affect** along two axes—**Valence** (negative ↔ positive) and **Arousal** (calm ↔ excited)—and expose a small set of **tags** (e.g., `hedging`, `urgent`, `toxic_light`, `family_conflict_hint`). Everything runs **on‑device**; no raw audio, images, or keystrokes leave the device. Outputs are compact scalars with confidence and are space‑scoped by **Memory Spaces**.

Design principles:
- **Edge‑first:** optional, budget‑aware heads (fast Tier‑0, optional Tier‑1).  
- **Explainable first, learnable later:** lexicon rules always available; tiny NN heads optional.  
- **Privacy by construction:** store only derived aggregates; never keep raw media.  
- **Interoperable:** small, stable envelopes; confidence‑aware fusion; per‑space EMAs.  
- **Family‑safe:** toxicity is “family‑safe” focused; banding rules prefer safety.

---

## 1) Interfaces (Envelopes)

### 1.1 Input — Scoring Request (Enhanced)

> Emitted by **P02 Write/Ingest** after redaction and before projection (if device budget allows enhanced classifier).

```json
{
  "person_id": "alice",
  "space_id": "shared:household",
  "event_id": "evt-2025-09-04-00123",
  "text": "I absolutely love this outcome!! best day ever :)",
  "behavior": {
    "inter_request_deltas": [0.5, 1.0, 0.4, 0.6],
    "keystrokes_total": 80,
    "backspaces": 20,
    "retries": 3,
    "session_seconds": 700,
    "active_seconds": 90
  },
  "ctx": {
    "battery_low": false,
    "cpu_throttled": false,
    "intent_urgent": true,
    "time_of_day_hours": 14.3
  },
  "modalities": {
    "prosody_feats": [0.7, 0.3, 0.4],   
    "face_aus_z": [0.2, -0.1, 0.4],     
    "hrv_z": -0.8                       
  },
  "trace_id": "trace-abc123",
  "model_prefs": {
    "text_onnx_path": null,
    "use_vader": true,
    "use_textblob": true
  }
}
```

**Field rules**
- `person_id`, `space_id`, `event_id`: required.  
- `text`: optional (empty allowed).  
- `behavior`, `ctx`, `modalities`, `model_prefs`: optional; degrade gracefully.  
- **Invariants:** no raw audio/frames/keys; short arrays (≤12 deltas). Versions are on outputs.

### 1.2 Where behavior fields come from (on-device aggregator)

| Field | Source | Computation (sliding window 60–120s) |
|---|---|---|
| `inter_request_deltas` | UI or API middleware emits **REQUEST_SENT** | Append `now - last_ts` to ring buffer; prune older than window. |
| `keystrokes_total` | Text input listeners | Count only; never store characters. |
| `backspaces` | Same | Count Backspace/Delete (or text length decreases on mobile). |
| `retries` | REQUEST_SENT + last result | Same/near‑same prompt within 10s of error or ≤20s after “retry” → increment. |
| `session_seconds` | App lifecycle | Time since last session start (restart after ≥10m idle). |
| `active_seconds` | Foreground + activity ping | Accumulate while foreground & active (≤window). |

**Friction flags:** iOS `ProcessInfo.thermalState`, Android `PowerManager/ThermalService`, Desktop/Electron OS APIs.

### 1.3 Output — Affect Annotation + State

```json
{
  "affect_annotation": {
    "event_id": "evt-2025-09-04-00123",
    "space_id": "shared:household",
    "valence": 0.78,
    "arousal": 0.67,
    "tags": ["urgent","toxic_light"],
    "confidence": 0.72,
    "model_version": "affect-enhanced:2025-09-04",
    "ts": "2025-09-04T12:34:56.000Z"
  },
  "affect_state": {
    "person_id": "alice",
    "space_id": "shared:household",
    "v_ema": 0.51,
    "a_ema": 0.58,
    "confidence": 0.70,
    "model_version": "affect-enhanced:2025-09-04",
    "updated_at": "2025-09-04T12:34:56.000Z"
  }
}
```

### 1.4 Output — Policy Recommendation (Banding)

```json
{
  "policy_recommendation": {
    "band": "AMBER",                 
    "reasons": ["downshift: high arousal + negative valence"],
    "confidence": 0.7
  }
}
```

**Banding rules (MVP)**
- If **a ≥ 0.70** and **v ≤ −0.40** → downshift by 1 (min RED).  
- If `family_conflict_hint` and **actor is minor** → min RED.  
- If **v ≥ 0.50** and **a ≥ 0.40** and tag `positive_family_moment` → allow GREEN and extend rollup half‑life ×2.

### 1.5 Output — Observability / Trace
Compact, no PII; includes per‑source details, priors, and context bump.

```json
{
  "trace_id": "trace-abc123",
  "affect": {
    "sources": [
      {"name":"text.lexicon","v":0.74,"a":0.62,"c":0.70},
      {"name":"vader","v":0.80,"a":0.65,"c":0.75},
      {"name":"beh","a":0.55,"c":0.60},
      {"name":"prosody","a":0.66,"c":0.65}
    ],
    "fusion": {"priors": {"text":1.0,"beh":0.8,"prosody":0.6,"face":0.4,"hrv":0.5}, "a_ctx": 0.15},
    "tokens_sample": ["i","absolutely","love","the","outcome"]
  }
}
```

### 1.6 CRDT side‑record (optional)
Affect annotations can be attached in the local event CRDT or as side‑records; always scoped to the same **space** and protected by **MLS** keys.

---

## 2) System Fit (Family OS)

- **P02 Write/Ingest → AffectEnhanced.score(...)**: computes `{v,a,tags,c}`.  
- **P18 Safety/Abuse & Policy**: consumes banding recs; RED/BLACK can gate projection.  
- **P01 Recall/Ranker**: uses `v̄,ā` EMAs to bias retrieval (e.g., down‑weight conflict when minors present).  
- **P03 Consolidation**: tags (e.g., `positive_family_moment`) boost rollup half‑life; high arousal negative moments may be compacted more aggressively.  
- **P06 Learning/Neuromod**: uses corrections (undoes) and outcomes to calibrate heads.  
- **Storage**: `st_aff` for annotations/state; `st_meta` for metacog; all replicated via **P07 CRDT** within authorized spaces.

---

## 3) Algorithms & Math

### 3.1 Text valence (lexicon + rules)
For tokens t with lexicon weight L(t) ∈ [−1,1]:  
Negation window `W_neg` flips polarity: `neg(i) ∈ {{+1,−1}}`. Boosters scale by `boost(i) ≥ 1`.

\[ S_{{text}} = \frac1N \sum_i L(t_i)\,\cdot neg(i)\,\cdot boost(i) \]

Add punctuation/emoji cues and squash to valence:  
\[ v_{{text}} = \tanh\big(S_{{text}} + \alpha\,exclaim - \beta\,allcaps + \gamma\,emoji_+ - \delta\,emoji_-\big) \]
Typical: α=0.25, β=0.3, γ=0.2, δ=0.2; clip to [−1,1].

### 3.2 Text arousal proxy
\[ a_{{text}} = \sigma\big( \eta_1 |S_{{text}}| + \eta_2\,punct\_density + \eta_3\,booster\_rate \big) \]
σ is logistic; η₁≈1.2, η₂≈0.8, η₃≈0.6.

### 3.3 Hedging / negation / toxicity tags
- **Hedging** h ∈ [0,1] = fraction of hedge tokens damped by sentence length (tag if h≥0.25).  
- **Negation** tag if any negation scopes applied.  
- **Toxicity** (family‑safe): tiny linear or ONNX head; `tox_light ≥0.5`, `tox_high ≥0.8`.

### 3.4 Behavioral arousal
Collect session window stats; normalize vs rolling personal baselines (z‑scores computed **before** updating baselines):  
\[ a_{{beh}} = \sigma(\kappa_1 z_B + \kappa_2 z_{{bs}} + \kappa_3 z_r + \kappa_4 \mathbb{{1}}[friction] + \kappa_5 f_{{tod}}(t) - \kappa_6 g(T_s)) \]

### 3.5 Optional modalities
- **Prosody**: \( a = \sigma(0.5\,z_{{\sigma F0}} + 0.3\,z_E + 0.4\,z_{{rate}}) \)  
- **Face AUs**: linear map from AU vector → (v,a) with confidence from AU magnitude (no frames stored).  
- **Wearables HRV**: \( a = \sigma(-\lambda z_{{HRV}}) \), λ≈0.8.

### 3.6 Late fusion (confidence‑weighted)
Valence (sources with `v_s`): \( v = \frac{{\sum w_s c_s v_s}}{{\sum w_s c_s + \epsilon}} \)  
Arousal (all `a_s`): \( a = \text{{clip}}\Big( \frac{{\sum w_s c_s a_s}}{{\sum w_s c_s + \epsilon}} + a_{{ctx}}, 0,1 \Big) \)

**Priors:** text=1.0, behavior=0.8, prosody=0.6, face=0.4, hrv=0.5. Calibrate with light Platt/temperature scaling if ONNX heads are enabled.

---

## 4) Privacy & Policy

- **Never** store raw audio/video/keystrokes; only scalars, tags, z‑scores, confidences, and model version.  
- All annotations are **space‑scoped**; replication uses **MLS** groups per space.  
- Banding decisions are advisory; **policy** layer finalizes allow/deny and audit trails.

---

## 5) Error Handling & Validation

- Missing fields → omitted in fusion; confidence reduced accordingly.  
- Out‑of‑range inputs are clipped; arrays pruned to ≤12.  
- Malformed optional modalities are dropped with a trace warning.  
- Undo within 15 minutes (AMBER) can be treated as negative feedback for calibration.

---

## 6) Example (end‑to‑end)

```json
{
  "affect": {"v": 0.76, "a": 0.69, "tags": ["urgent","toxic_light"], "confidence": 0.71, "model_version": "affect-enhanced:2025-09-04"},
  "affect_state": {"v_ema": 0.51, "a_ema": 0.58, "confidence": 0.70},
  "policy": {"band": "AMBER", "reasons": ["downshift: high arousal + negative valence"], "confidence": 0.70},
  "trace_id": "trace-abc123"
}
```

---

## 7) References (selected)

- Hutto & Gilbert (2014) **VADER**: Valence Aware Dictionary for Sentiment Reasoning.  
- Russell (1980) **Circumplex model of affect**; Russell & Barrett (1999).  
- Scherer (2005) **Appraisal theory** of emotion.  
- Platt (1999) **Probabilistic outputs for SVMs** (Platt scaling); generalized to valence calibration.  
- Task Force of the European Society of Cardiology (1996) **HRV** standards; RMSSD/SDRR.  
- Boersma (1993) **Praat** basis for F0; prosodic arousal proxies.  
- HCI burstiness measures & keystroke dynamics literature for behavioral arousal proxies.

---

## 8) Files (orientation)

- `realtime_classifier.py` — Tier‑0 (text rules + behavior), always available.  
- `enhanced_classifier.py` — ensemble + modalities + fusion.  
- `features/ensemble_text.py`, `features/onnx_text.py`, `features/prosody.py`, `features/face.py`, `features/hrv.py` — optional heads.  
- `policy_bridge.py` — banding rules.  
- `state.py` — per‑person/space EMAs and baselines.  
- `affect_aware_service.py` — service wrapper for P02.  
- `tests/` — unit tests for ensemble, fusion, thresholds.

---

**Stewardship:** This module should remain understandable and auditable. Keep defaults conservative; prefer safety when uncertain.
