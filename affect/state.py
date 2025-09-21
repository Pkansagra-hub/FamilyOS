
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import time, math, threading

def _now_ts() -> float:
    return time.time()

@dataclass
class RunningMeanVar:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    def update(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        d2 = x - self.mean
        self.m2 += d * d2
    @property
    def var(self) -> float:
        return self.m2 / max(1, self.n - 1)
    @property
    def std(self) -> float:
        v = self.var
        return math.sqrt(v) if v > 0 else 1.0
    def z(self, x: float) -> float:
        return (x - self.mean) / max(1e-6, self.std)

@dataclass
class BehaviorBaselines:
    burst: RunningMeanVar = field(default_factory=RunningMeanVar)
    backspace_ratio: RunningMeanVar = field(default_factory=RunningMeanVar)
    retry_rate: RunningMeanVar = field(default_factory=RunningMeanVar)

@dataclass
class BehaviorWindow:
    active_seconds: float = 0.0
    chars_typed: int = 0
    backspaces: int = 0
    retries: int = 0
    clicks: int = 0
    prosody_pitch_std: Optional[float] = None
    prosody_energy_std: Optional[float] = None
    hrv_rmssd_z: Optional[float] = None
    face_aus_z: Optional[List[float]] = None

@dataclass
class ContextInfo:
    is_night: bool = False
    is_work_hours: bool = False
    interlocutor: Optional[str] = None
    topic_hint: Optional[str] = None
    device_trust: Optional[str] = None

@dataclass
class AffectAnnotation:
    event_id: str
    space_id: str
    valence: float
    arousal: float
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    model_version: str = "affect-mvp"
    created_at: float = field(default_factory=_now_ts)

@dataclass
class AffectState:
    person_id: str
    space_id: str
    v_ema: float = 0.0
    a_ema: float = 0.0
    confidence: float = 0.0
    model_version: str = "affect-mvp"
    updated_at: float = field(default_factory=_now_ts)
    baselines: BehaviorBaselines = field(default_factory=BehaviorBaselines)

class AffectStateStore:
    def get_state(self, person_id: str, space_id: str) -> AffectState: ...
    def put_state(self, st: AffectState) -> None: ...
    def append_annotation(self, ann: AffectAnnotation) -> None: ...
    def list_annotations(self, person_id: str, space_id: str, limit: int = 2000) -> List[AffectAnnotation]: ...

class MemoryAffectStateStore(AffectStateStore):
    def __init__(self) -> None:
        self._states: Dict[Tuple[str,str], AffectState] = {}
        self._anns: Dict[Tuple[str,str], List[AffectAnnotation]] = {}
        self._lock = threading.Lock()
    def get_state(self, person_id: str, space_id: str) -> AffectState:
        with self._lock:
            key = (person_id, space_id)
            st = self._states.get(key)
            if st is None:
                st = AffectState(person_id=person_id, space_id=space_id)
                self._states[key] = st
            return st
    def put_state(self, st: AffectState) -> None:
        with self._lock:
            self._states[(st.person_id, st.space_id)] = st
    def append_annotation(self, ann: AffectAnnotation) -> None:
        with self._lock:
            arr = self._anns.setdefault((ann.event_id, ann.space_id), [])
            arr.append(ann)
    def list_annotations(self, person_id: str, space_id: str, limit: int = 2000) -> List[AffectAnnotation]:
        with self._lock:
            rows: List[AffectAnnotation] = []
            for (eid, sid), anns in self._anns.items():
                if sid == space_id:
                    rows.extend(anns)
            rows.sort(key=lambda a: a.created_at)
            return rows[-limit:]
