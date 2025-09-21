"""
Text ensemble with multiple heads:
- Lexicon+rules (always available)
- VADER (if installed)
- TextBlob (if installed)
- ONNX tiny transformer (if configured)
We combine them into (v_text, a_text, tox, confidence) with interpretable tags.
"""

from typing import Dict, List, Optional, Tuple
import math

from affect.features.lexicon import LEXICON, BOOSTERS, DIMINISHERS, HEDGES, TOXIC_SEEDS
from affect.features.text_metrics import (
    tokenize,
    exclaim_rate,
    allcaps_rate,
    punctuation_density,
    emoji_counts,
)
from affect.features.negation import negation_scope_multipliers
from affect.features.onnx_text import OnnxTextModel


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def tanh(x: float) -> float:
    return math.tanh(x)


class TextEnsembleConfig:
    def __init__(
        self,
        negation_window: int = 3,
        alpha_exclaim: float = 0.25,
        beta_allcaps: float = 0.30,
        gamma_emoji_pos: float = 0.20,
        delta_emoji_neg: float = 0.20,
        eta1_abs_sent: float = 1.2,
        eta2_punct: float = 0.8,
        eta3_booster: float = 0.6,
        use_vader: bool = True,
        use_textblob: bool = True,
        onnx_model_path: Optional[str] = None,
    ):
        self.negation_window = negation_window
        self.alpha_exclaim = alpha_exclaim
        self.beta_allcaps = beta_allcaps
        self.gamma_emoji_pos = gamma_emoji_pos
        self.delta_emoji_neg = delta_emoji_neg
        self.eta1_abs_sent = eta1_abs_sent
        self.eta2_punct = eta2_punct
        self.eta3_booster = eta3_booster
        self.use_vader = use_vader
        self.use_textblob = use_textblob
        self.onnx_model_path = onnx_model_path
        self._onnx = OnnxTextModel(onnx_model_path) if onnx_model_path else None


def _lexicon_channels(
    text: str, tokens: List[str], cfg: TextEnsembleConfig
) -> Dict[str, object]:
    mult = negation_scope_multipliers(tokens, window=cfg.negation_window)
    total = 0.0
    booster_hits = 0
    N = max(1, len(tokens))
    for i, tok in enumerate(tokens):
        low = tok.lower()
        w = LEXICON.get(low, 0.0)
        b = 1.0
        if low in BOOSTERS:
            b *= BOOSTERS[low]
            booster_hits += 1
        if low in DIMINISHERS:
            b *= DIMINISHERS[low]
        total += w * mult[i] * b
    S_text = total / math.sqrt(N)
    ex_rate = exclaim_rate(text)
    caps_rate = allcaps_rate(tokens)
    punct = punctuation_density(text)
    booster_rate = booster_hits / N
    emoji_pos, emoji_neg = emoji_counts(text)
    v = tanh(
        S_text
        + cfg.alpha_exclaim * ex_rate
        - cfg.beta_allcaps * caps_rate
        + cfg.gamma_emoji_pos * emoji_pos
        - cfg.delta_emoji_neg * emoji_neg
    )
    a = sigmoid(
        cfg.eta1_abs_sent * abs(S_text)
        + cfg.eta2_punct * punct
        + cfg.eta3_booster * booster_rate
    )
    # confidence
    c = min(1.0, max(0.0, 0.1 + 0.9 * math.sqrt(N / (N + 20.0))))
    if abs(S_text) / math.sqrt(N) < 0.05:
        c *= 0.7
    # hedging/tox
    tags = []
    t_low = " ".join(tokens).lower()
    hedge_count = 0
    for h in HEDGES:
        hedge_count += (
            1
            if ((" " in h and h in t_low) or any(tok.lower() == h for tok in tokens))
            else 0
        )
    if hedge_count / N >= 0.25:
        tags.append("hedging")
    tox = 0.0
    for k, v_int in TOXIC_SEEDS.items():
        if k in text.lower():
            tox = max(tox, v_int)
    if tox >= 0.8:
        tags.append("toxic_high")
    elif tox >= 0.5:
        tags.append("toxic_light")
    return {"v": v, "a": a, "c": c, "tox": tox, "tags": tags, "S_text": S_text}


def _vader_score(text: str) -> Optional[Tuple[float, float]]:
    try:
        try:
            # vaderSentiment package
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore

            analyzer = SentimentIntensityAnalyzer()
        except Exception:
            # nltk VADER
            from nltk.sentiment.vader import SentimentIntensityAnalyzer  # type: ignore

            analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text or "")
        compound = float(max(-1.0, min(1.0, scores.get("compound", 0.0))))
        # arousal proxy from magnitude and punctuation
        punct = text.count("!") + text.count("?")
        a = sigmoid(1.2 * abs(compound) + 0.15 * punct)
        return compound, a
    except Exception:
        return None


def _textblob_score(text: str) -> Optional[Tuple[float, float]]:
    try:
        from textblob import TextBlob  # type: ignore

        tb = TextBlob(text or "")
        pol = float(max(-1.0, min(1.0, tb.sentiment.polarity)))
        subj = float(min(1.0, max(0.0, tb.sentiment.subjectivity)))
        a = 0.5 * abs(pol) + 0.5 * subj  # proxy
        return pol, a
    except Exception:
        return None


import logging

logger = logging.getLogger(__name__)


def _onnx_score(
    cfg: TextEnsembleConfig, text: str
) -> Optional[Tuple[float, float, float, float]]:
    if not cfg or not cfg._onnx:
        return None
    try:
        out = cfg._onnx.predict(text)
        if not out:
            return None

        # Handle tuple output (valence, arousal, toxicity)
        if isinstance(out, tuple) and len(out) >= 2:
            v = float(max(-1.0, min(1.0, out[0])))
            toxicity = float(min(1.0, max(0.0, out[2] if len(out) > 2 else 0.0)))
            # Use arousal from model if available, otherwise derive from valence
            a = float(
                max(0.0, min(1.0, out[1] if len(out) > 1 else 0.5 + 0.5 * abs(v)))
            )
            c = 0.8  # Fixed confidence for now
            return (v, a, toxicity, c)

        # Handle dict output (legacy support)
        elif isinstance(out, dict):
            v = float(max(-1.0, min(1.0, out.get("valence", [0.0])[0])))
            tox = float(min(1.0, max(0.0, out.get("toxicity", [0.0])[0])))
            c = float(min(1.0, max(0.0, out.get("confidence", [0.8])[0])))
            a = 0.5 + 0.5 * abs(v)  # arousal proxy from magnitude
            return (v, a, tox, c)

        return None
    except Exception as e:
        logger.warning("ONNX scoring failed: %s", e)
        return None
    return v, a, tox if tox is not None else 0.0


def ensemble_text_scores(
    text: str, cfg: Optional[TextEnsembleConfig] = None
) -> Dict[str, object]:
    cfg = cfg or TextEnsembleConfig()
    tokens = tokenize(text or "")
    base = _lexicon_channels(text or "", tokens, cfg)

    # Collect predictions
    sources = []  # (name, v, a, c, tox, c_tox)
    # Lexicon (always)
    sources.append(("lexicon", base["v"], base["a"], base["c"], base["tox"], 0.6))
    # VADER
    if cfg.use_vader:
        vd = _vader_score(text or "")
        if vd is not None:
            v, a = vd
            sources.append(("vader", v, a, 0.75, None, 0.0))
    # TextBlob
    if cfg.use_textblob:
        tb = _textblob_score(text or "")
        if tb is not None:
            v, a = tb
            sources.append(("textblob", v, a, 0.65, None, 0.0))
    # ONNX model
    onnx_out = _onnx_score(cfg, text or "")
    if onnx_out is not None:
        v, a, tox, c = onnx_out
        sources.append(("onnx", v, a, c, tox, 0.9))

    # Ensemble weights
    priors = {"onnx": 1.2, "lexicon": 1.0, "vader": 0.8, "textblob": 0.6}

    # Fuse valence
    num_v, den_v = 0.0, 0.0
    for name, v, _a, c, _tox, _ct in sources:
        if v is None:
            continue
        w = priors.get(name, 0.5)
        num_v += w * c * v
        den_v += w * c
    v_fused = 0.0 if den_v == 0 else max(-1.0, min(1.0, num_v / den_v))

    # Fuse arousal
    num_a, den_a = 0.0, 0.0
    for name, _v, a, c, _tox, _ct in sources:
        if a is None:
            continue
        w = priors.get(name, 0.5)
        num_a += w * c * a
        den_a += w * c
    a_fused = 0.0 if den_a == 0 else max(0.0, min(1.0, num_a / den_a))

    # Toxicity
    tox_vals, tox_weights = [], []
    for name, _v, _a, c, tox, ctox in sources:
        if tox is None:
            continue
        w = priors.get(name, 0.5) * (ctox if ctox else c)
        tox_vals.append(w * tox)
        tox_weights.append(w)
    tox_fused = (sum(tox_vals) / sum(tox_weights)) if tox_weights else base["tox"]

    # Confidence: average of confidences weighted by priors
    conf = 0.0
    if den_v + den_a > 0:
        conf = min(
            1.0,
            max(
                0.0, 0.5 * ((den_v) / (den_v + 1e-6)) + 0.5 * ((den_a) / (den_a + 1e-6))
            ),
        )
        # cap to [0.4,1] to avoid overconfident zeros
        conf = max(0.4, conf)

    # Tags
    tags = list(base["tags"])
    if tox_fused >= 0.8 and "toxic_high" not in tags:
        tags.append("toxic_high")
    elif tox_fused >= 0.5 and "toxic_light" not in tags:
        tags.append("toxic_light")

    details = {
        "sources": [
            {"name": name, "v": v, "a": a, "c": c, "tox": tox}
            for (name, v, a, c, tox, _ct) in sources
        ],
        "tokens": tokens[:64],
        "base_S_text": base["S_text"],
    }
    return {
        "v_text": v_fused,
        "a_text": a_fused,
        "tox": tox_fused,
        "c_text": conf,
        "tags": tags,
        "details": details,
    }
