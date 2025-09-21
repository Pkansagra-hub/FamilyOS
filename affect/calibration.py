from dataclasses import dataclass

def sigmoid(x: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-x))

def logit(p: float) -> float:
    import math
    eps = 1e-8
    p = min(max(p, eps), 1.0 - eps)
    return math.log(p / (1 - p))

@dataclass
class ValenceCalibration:
    theta: float = 1.0
    bias: float = 0.0

    def apply(self, v: float) -> float:
        import math
        return max(-1.0, min(1.0, math.tanh(self.theta * v + self.bias)))

@dataclass
class ArousalCalibration:
    temperature: float = 1.0

    def apply(self, a: float) -> float:
        return sigmoid(logit(a) / max(1e-6, self.temperature))
