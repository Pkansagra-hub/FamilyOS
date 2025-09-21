from typing import Tuple

def sigmoid(x: float) -> float:
    import math
    if x >= 0:
        z = math.exp(-x); return 1.0/(1.0+z)
    else:
        z = math.exp(x); return z/(1.0+z)

def arousal_from_prosody(pitch_std_z: float, energy_z: float, rate_z: float) -> Tuple[float, float]:
    """
    Map z-scored prosody features to arousal (0..1), with confidence.
    a = σ(0.5*z_pitch_std + 0.3*z_energy + 0.4*z_rate)
    c = σ(|z_pitch_std| + |z_energy| + |z_rate| - 1)
    """
    a = sigmoid(0.5*pitch_std_z + 0.3*energy_z + 0.4*rate_z)
    c = min(1.0, max(0.0, sigmoid(abs(pitch_std_z) + abs(energy_z) + abs(rate_z) - 1.0)))
    return a, c
