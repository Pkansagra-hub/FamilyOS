
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math

from .state import BehaviorWindow, ContextInfo, AffectState, BehaviorBaselines
from .features.lexicon import LEXICON, NEGATIONS, BOOSTERS, DIMINISHERS, HEDGES, TOXIC_SEEDS
from .features.text_metrics import tokenize, punct_counts, exclam_density, question_density, emoji_valence_hint

@dataclass
class RealtimeConfig:
    model_version: str = "affect-mvp"
    alpha_valence: float = 0.2
    alpha_arousal: float = 0.2
    w_text: float = 0.65
    w_behavior: float = 0.25
    w_context: float = 0.10
    eta1_emoji: float = 1.2
    eta2_punct: float = 0.8
    eta3_booster: float = 0.6

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x); return 1.0/(1.0+z)
    else:
        z = math.exp(x); return z/(1.0+z)

def _lexicon_valence(tokens: List[str]) -> Tuple[float, List[str]]:
    s = 0.0
    tags: List[str] = []
    prev = None
    for t in tokens:
        w = LEXICON.get(t, 0.0)
        if t in NEGATIONS:
            tags.append("negation")
        if t in BOOSTERS:
            w *= 1.4; tags.append("booster")
        if t in DIMINISHERS:
            w *= 0.6; tags.append("diminisher")
        if prev in NEGATIONS and w != 0.0:
            w *= -0.8; tags.append("negated")
        s += w
        prev = t
    if tokens:
        s /= math.sqrt(len(tokens))
    return (math.tanh(s), tags)

def _behavior_features(behavior: Optional[BehaviorWindow], baselines: BehaviorBaselines) -> Tuple[float, float, Dict[str,float]]:
    if behavior is None or behavior.active_seconds <= 0:
        return (0.0, 0.0, {})
    cps = behavior.chars_typed / max(1.0, behavior.active_seconds)
    burst = cps
    backspace_ratio = 0.0 if behavior.chars_typed <= 0 else behavior.backspaces / max(1, behavior.chars_typed)
    retry_rate = behavior.retries / max(1.0, behavior.active_seconds)
    zB = baselines.burst.z(burst)
    zbs = baselines.backspace_ratio.z(backspace_ratio)
    zr = baselines.retry_rate.z(retry_rate)
    baselines.burst.update(burst)
    baselines.backspace_ratio.update(backspace_ratio)
    baselines.retry_rate.update(retry_rate)
    ar = _sigmoid(0.7*zB + 0.5*zr + 0.4*zbs)
    v_adj = -0.15 if (ar > 0.65 and zbs > 0.5) else (0.08 if zbs < -0.5 else 0.0)
    return (v_adj, ar, {"z_burst": zB, "z_backspace_ratio": zbs, "z_retry_rate": zr})

def score_text_and_behavior(text: Optional[str], behavior: Optional[BehaviorWindow], ctx: Optional[ContextInfo], st: Optional[AffectState], cfg: Optional[RealtimeConfig] = None) -> Dict[str, object]:
    cfg = cfg or RealtimeConfig()
    tokens = tokenize(text or "")
    v_text, text_tags = _lexicon_valence(tokens)
    exclam, question = punct_counts(text or "")
    v_text += cfg.eta2_punct * (0.05*exclam - 0.03*question)
    v_text += cfg.eta1_emoji * emoji_valence_hint(text or "")
    tox = 1.0 if any(t in (text or "").lower() for t in TOXIC_SEEDS) else 0.0
    if tox:
        v_text -= 0.1
        text_tags.append("toxic_seed")
    v_adj, a_behavior, b_feats = _behavior_features(behavior, st.baselines if st else BehaviorBaselines())
    v = cfg.w_text * v_text + cfg.w_behavior * v_adj
    a = a_behavior
    if exclam >= 2:
        a = 1.0 - (1.0-a)*0.85
    if ctx and ctx.is_night:
        a *= 0.95
    if ctx and ctx.is_work_hours:
        a = 1.0 - (1.0-a)*0.92
    c = 0.6 + 0.2*(1 if behavior and behavior.active_seconds>0 else 0) + 0.2*(1 if text else 0)
    v = _clamp(v, -1.0, 1.0)
    a = _clamp(a, 0.0, 1.0)
    tags = list(set(text_tags))
    details = {"text": {"tokens": tokens[:64], "exclam": exclam, "question": question}, "behavior": b_feats}
    return {"valence": v, "arousal": a, "tags": tags, "confidence": c, "details": details, "model_version": cfg.model_version}
