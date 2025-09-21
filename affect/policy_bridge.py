
from typing import Dict, List

def recommend_band(current_band: str, v: float, a: float, tags: List[str], actor_is_minor: bool) -> Dict[str, object]:
    order = ["BLACK", "RED", "AMBER", "GREEN"]
    idx = {b:i for i,b in enumerate(order)}
    cur_i = idx.get(current_band, idx["AMBER"])
    reasons: List[str] = []
    conf = 0.5
    if a >= 0.70 and v <= -0.40:
        cur_i = max(idx["RED"], cur_i - 1)
        reasons.append("high arousal negative valence → downshift")
        conf = max(conf, 0.7)
    if actor_is_minor and ("family_conflict_hint" in tags):
        cur_i = max(cur_i, idx["RED"])
        reasons.append("min RED for minors in conflict")
        conf = max(conf, 0.8)
    if (v >= 0.50 and a >= 0.40) and ("positive_family_moment" in tags):
        cur_i = max(cur_i, idx["GREEN"])
        reasons.append("allow GREEN for positive shared moment")
        conf = max(conf, 0.6)
    return {"band": order[cur_i], "reasons": reasons, "confidence": conf}
