from typing import List

def negation_scope_multipliers(tokens: List[str], window: int = 3) -> List[int]:
    """Return a list of multipliers (+1 / -1) indicating negation for each token.
    A negation flips the sign for the next `window` tokens unless another clause boundary occurs.
    """
    multipliers = [1] * len(tokens)
    neg_left = 0
    for i, tok in enumerate(tokens):
        lower = tok.lower()
        if lower in {"not","no","never","aint","isnt","arent","dont","doesnt","didnt","cant","couldnt","wont","wouldnt","shouldnt"} or lower.endswith("n't"):
            neg_left = window
            continue
        if neg_left > 0:
            multipliers[i] = -1
            neg_left -= 1
    return multipliers
