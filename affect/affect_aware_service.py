
from typing import Dict, Optional
from .state import AffectStateStore, MemoryAffectStateStore, AffectState, AffectAnnotation, BehaviorWindow, ContextInfo
from .realtime_classifier import score_text_and_behavior, RealtimeConfig
from .calibration import ValenceCalibration, ArousalCalibration

class AffectAwareService:
    def __init__(self, store: Optional[AffectStateStore] = None, v_cal=None, a_cal=None, cfg: Optional[RealtimeConfig] = None):
        self.store = store or MemoryAffectStateStore()
        self.v_cal = v_cal or ValenceCalibration()
        self.a_cal = a_cal or ArousalCalibration()
        self.cfg = cfg or RealtimeConfig()

    def process_event(self, person_id: str, space_id: str, event_id: str, text: Optional[str] = None, behavior: Optional[BehaviorWindow] = None, ctx: Optional[ContextInfo] = None) -> Dict[str, object]:
        st = self.store.get_state(person_id, space_id)
        res = score_text_and_behavior(text=text, behavior=behavior, ctx=ctx, st=st, cfg=self.cfg)
        v = self.v_cal.apply(res["valence"])
        a = self.a_cal.apply(res["arousal"])
        c = res.get("confidence", 0.5)
        tags = res.get("tags", [])
        st.v_ema = (1.0 - self.cfg.alpha_valence) * st.v_ema + self.cfg.alpha_valence * v
        st.a_ema = (1.0 - self.cfg.alpha_arousal) * st.a_ema + self.cfg.alpha_arousal * a
        st.confidence = (st.confidence + c) / 2.0
        st.model_version = self.cfg.model_version
        self.store.put_state(st)
        ann = AffectAnnotation(event_id=event_id, space_id=space_id, valence=v, arousal=a, tags=tags, confidence=c, model_version=self.cfg.model_version)
        self.store.append_annotation(ann)
        result = {"event_id": event_id, "space_id": space_id, "valence": v, "arousal": a, "tags": tags, "confidence": c,
                  "state": {"v_ema": st.v_ema, "a_ema": st.a_ema, "confidence": st.confidence, "model_version": st.model_version},
                  "details": res.get("details", {})}
        return result

    def get_state(self, person_id: str, space_id: str) -> Dict[str, object]:
        st = self.store.get_state(person_id, space_id)
        return {"person_id": person_id, "space_id": space_id, "v_ema": st.v_ema, "a_ema": st.a_ema, "confidence": st.confidence, "model_version": st.model_version}
