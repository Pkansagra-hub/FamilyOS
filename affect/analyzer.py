
from dataclasses import dataclass
from typing import Iterable, Dict, List, Tuple
from .state import AffectAnnotation

@dataclass
class DriftReport:
    person_id: str
    space_id: str
    drift_valence: float
    drift_arousal: float
    suggestions: Dict[str, float]

def detect_drift(person_id: str, space_id: str, annotations: Iterable[AffectAnnotation]) -> DriftReport:
    anns = [a for a in annotations]
    if len(anns) < 20:
        return DriftReport(person_id=person_id, space_id=space_id, drift_valence=0.0, drift_arousal=0.0, suggestions={})
    mid = len(anns) // 2
    v1 = sum(a.valence for a in anns[:mid]) / max(1, mid)
    v2 = sum(a.valence for a in anns[mid:]) / max(1, len(anns)-mid)
    a1 = sum(a.arousal for a in anns[:mid]) / max(1, mid)
    a2 = sum(a.arousal for a in anns[mid:]) / max(1, len(anns)-mid)
    return DriftReport(person_id=person_id, space_id=space_id, drift_valence=(v2 - v1), drift_arousal=(a2 - a1),
                       suggestions={"valence_bias_delta": (v2 - v1), "arousal_temp_hint": 1.0})
