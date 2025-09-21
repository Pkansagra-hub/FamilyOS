from typing import List, Tuple

def tanh(x: float) -> float:
    import math
    return max(-1.0, min(1.0, math.tanh(x)))

def sigmoid(x: float) -> float:
    import math
    if x >= 0:
        z = math.exp(-x); return 1.0/(1.0+z)
    else:
        z = math.exp(x); return z/(1.0+z)

def va_from_face_aus(au_z: List[float]) -> Tuple[float, float, float]:
    """
    Map z-scored action units (AUs) to (valence, arousal, confidence).
    This is a simple linear map; replace with calibrated weights when available.
    Expect 12-D input (AU1..AU12) or any consistent set; we handle variable length.
    """
    if not au_z: return 0.0, 0.0, 0.0
    # Heuristic weights: eye/cheek/lip raise → positive; brow/press → negative
    w_v = [ 0.25, -0.20, 0.30, -0.25, 0.20, -0.15, 0.35, -0.10, 0.15, -0.20, 0.30, -0.10 ]
    w_a = [ 0.10,  0.25, 0.15,  0.30, 0.20,  0.25, 0.10,  0.30, 0.20,  0.25, 0.10,  0.30 ]
    v_raw = sum((w_v[i % len(w_v)]) * z for i, z in enumerate(au_z)) / max(1, len(au_z))
    a_raw = sum((w_a[i % len(w_a)]) * z for i, z in enumerate(au_z)) / max(1, len(au_z))
    v = tanh(v_raw)
    a = min(1.0, max(0.0, sigmoid(a_raw)))
    c = min(1.0, max(0.0, sum(abs(z) for z in au_z) / (len(au_z) * 3.0)))  # rough confidence
    return v, a, c
