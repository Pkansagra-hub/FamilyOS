"""
affect package — on-device affect inference (valence, arousal, tags) for Family OS.

This package exposes:
- realtime text+behavior scoring (fast, explainable)
- optional enhanced scoring hooks (prosody/vision/wearables; off by default)
- state management (EMA) + baselines
- a policy bridge for sharing band recommendations
- an analyzer for offline backfill/calibration tasks
"""
from .realtime_classifier import score_text_and_behavior, RealtimeConfig
from .state import AffectStateStore, MemoryAffectStateStore, AffectState, BehaviorBaselines
from .policy_bridge import recommend_band

__all__ = [
    "score_text_and_behavior",
    "RealtimeConfig",
    "AffectStateStore",
    "MemoryAffectStateStore",
    "AffectState",
    "BehaviorBaselines",
    "recommend_band",
]
