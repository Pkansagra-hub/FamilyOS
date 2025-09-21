from typing import Tuple

def sigmoid(x: float) -> float:
    import math
    if x >= 0:
        z = math.exp(-x); return 1.0/(1.0+z)
    else:
        z = math.exp(x); return z/(1.0+z)

def arousal_from_hrv_z(hrv_z: float, lam: float = 0.8) -> Tuple[float, float]:
    """
    Higher arousal ↔ lower HRV. Map z-scored HRV to arousal:
      a = σ(-λ * z_HRV), c based on |z_HRV|.
    """
    a = sigmoid(-lam * hrv_z)
    c = min(1.0, max(0.0, sigmoid(abs(hrv_z) - 0.5)))
    return a, c
