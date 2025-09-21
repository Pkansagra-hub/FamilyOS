from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import math

from .state import BehaviorWindow, ContextInfo, AffectState, BehaviorBaselines
from .features.ensemble_text import ensemble_text_scores, TextEnsembleConfig
from .features.prosody import arousal_from_prosody
from .features.face import va_from_face_aus
from .features.hrv import arousal_from_hrv_z


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


@dataclass
class EnhancedConfig:
    # Behavior weights (increased for better spiky detection)
    kappa1_burst: float = 1.5
    kappa2_backspace: float = 0.9
    kappa3_retries: float = 1.1
    kappa4_friction: float = 0.4
    kappa5_tod: float = 0.2
    kappa6_fatigue: float = 0.2
    # Fusion priors
    w_text: float = 1.0
    w_beh: float = 0.8
    w_prosody: float = 0.6
    w_face: float = 0.4
    w_hrv: float = 0.5
    urgent_bump: float = 0.15
    model_version: str = "affect-enhanced:2025-09-04"


def _behavior_arousal(
    behavior: BehaviorWindow,
    baselines: BehaviorBaselines,
    cfg: EnhancedConfig,
    friction: bool,
    tod_hours: Optional[float],
) -> Tuple[float, float]:
    # Burstiness: coef of variation
    deltas = [d for d in (behavior.inter_request_deltas or []) if d > 0]
    if len(deltas) >= 2:
        mean_dt = sum(deltas) / len(deltas)
        var_dt = sum((d - mean_dt) ** 2 for d in deltas) / len(deltas)
        burst = math.sqrt(var_dt) / max(mean_dt, 1e-9)
    else:
        burst = 0.0
    backspace_ratio = (
        0.0
        if behavior.keystrokes_total <= 0
        else behavior.backspaces / max(1, behavior.keystrokes_total)
    )
    retry_rate = behavior.retries / max(1.0, behavior.active_seconds)

    # Compute z against *previous* baseline (do not include current sample yet)
    zB = baselines.burst.z(burst)
    zbs = baselines.backspace_ratio.z(backspace_ratio)
    zr = baselines.retry_rate.z(retry_rate)
    # Now update baselines with current sample for next time
    baselines.burst.update(burst)
    baselines.backspace_ratio.update(backspace_ratio)
    baselines.retry_rate.update(retry_rate)

    f_tod = 0.0
    if tod_hours is not None:
        rad = 2.0 * math.pi * (tod_hours % 24.0) / 24.0
        f_tod = 0.1 * math.sin(rad) + 0.1 * math.cos(rad)

    fatigue = min(behavior.session_seconds / 3600.0, 1.0)

    a_beh = sigmoid(
        cfg.kappa1_burst * zB
        + cfg.kappa2_backspace * zbs
        + cfg.kappa3_retries * zr
        + cfg.kappa4_friction * (1.0 if friction else 0.0)
        + cfg.kappa5_tod * f_tod
        - cfg.kappa6_fatigue * fatigue
    )
    coverage = min(1.0, max(0.0, behavior.active_seconds / 120.0))
    c_beh = max(
        0.0, min(1.0, math.sqrt(coverage) * sigmoid(abs(zB) + abs(zbs) + abs(zr) - 1.0))
    )
    return a_beh, c_beh


def _fuse_valence(
    parts: List[Tuple[str, Optional[float], float, float]], priors: Dict[str, float]
) -> Tuple[float, float]:
    num = den = 0.0
    confs = []
    for name, v, _a, c in parts:
        if v is None:
            continue
        w = priors.get(name, 0.4)
        num += w * c * v
        den += w * c
        confs.append(c)
    if den == 0:
        return 0.0, 0.0
    v = max(-1.0, min(1.0, num / den))
    c = min(1.0, max(0.0, sum(confs) / len(confs))) if confs else 0.0
    return v, c


def _fuse_arousal(
    parts: List[Tuple[str, Optional[float], float, float]],
    priors: Dict[str, float],
    a_ctx: float,
) -> Tuple[float, float]:
    num = den = 0.0
    confs = []
    for name, _v, a, c in parts:
        w = priors.get(name, 0.4)
        num += w * c * a
        den += w * c
        confs.append(c)
    if den == 0:
        a = 0.0
    else:
        a = max(0.0, min(1.0, num / den))
    a = max(0.0, min(1.0, a + a_ctx))
    c = min(1.0, max(0.0, sum(confs) / len(confs))) if confs else 0.0
    return a, c


def score_enhanced_event(
    text: str,
    behavior: BehaviorWindow,
    ctx: ContextInfo,
    state: AffectState,
    text_cfg: Optional[TextEnsembleConfig] = None,
    cfg: Optional[EnhancedConfig] = None,
    prosody_feats: Optional[tuple] = None,  # (pitch_std_z, energy_z, rate_z)
    face_aus_z: Optional[list] = None,  # list of AU z-scores
    hrv_z: Optional[float] = None,  # HRV z-score (lower → higher arousal)
) -> Dict[str, object]:
    """Enhanced scoring with text ensemble + behavior + optional modalities.
    Returns: {v, a, tags, confidence, details}
    """
    cfg = cfg or EnhancedConfig()
    text_cfg = text_cfg or TextEnsembleConfig()

    # TEXT ENSEMBLE
    tx = ensemble_text_scores(text or "", cfg=text_cfg)

    # BEHAVIOR
    friction = bool(ctx.battery_low or ctx.cpu_throttled)
    a_beh, c_beh = _behavior_arousal(
        behavior, state.baselines, cfg, friction, ctx.time_of_day_hours
    )

    # OPTIONAL MODALITIES
    parts: List[Tuple[str, Optional[float], float, float]] = []
    # text contributes valence and arousal
    parts.append(
        ("text", float(tx["v_text"]), float(tx["a_text"]), float(tx["c_text"]))
    )
    # behavior: arousal only
    parts.append(("beh", None, a_beh, c_beh))

    details = {"text": tx, "beh": {"a": a_beh, "c": c_beh, "friction": friction}}

    if prosody_feats is not None and len(prosody_feats) == 3:
        a_pr, c_pr = arousal_from_prosody(*prosody_feats)
        parts.append(("prosody", None, a_pr, c_pr))
        details["prosody"] = {"a": a_pr, "c": c_pr}

    if face_aus_z is not None and len(face_aus_z) > 0:
        v_face, a_face, c_face = va_from_face_aus(face_aus_z)
        parts.append(("face", v_face, a_face, c_face))
        details["face"] = {"v": v_face, "a": a_face, "c": c_face}

    if hrv_z is not None:
        a_hrv, c_hrv = arousal_from_hrv_z(hrv_z)
        parts.append(("hrv", None, a_hrv, c_hrv))
        details["hrv"] = {"a": a_hrv, "c": c_hrv}

    priors = {
        "text": cfg.w_text,
        "beh": cfg.w_beh,
        "prosody": cfg.w_prosody,
        "face": cfg.w_face,
        "hrv": cfg.w_hrv,
    }
    a_ctx = cfg.urgent_bump if ctx.intent_urgent else 0.0

    v, cv = _fuse_valence(parts, priors)
    a, ca = _fuse_arousal(parts, priors, a_ctx)

    # Overall confidence is blend of v/a confidences
    c_overall = min(1.0, max(0.0, 0.5 * (cv + ca)))

    # Tags: start with text tags; add urgency if applicable
    tags = list(tx["tags"])
    if ctx.intent_urgent and "urgent" not in tags:
        tags.append("urgent")

    details["fusion"] = {
        "priors": priors,
        "a_ctx": a_ctx,
        "parts": [{"name": n, "v": v, "a": a, "c": c} for (n, v, a, c) in parts],
    }

    return {"v": v, "a": a, "tags": tags, "confidence": c_overall, "details": details}
