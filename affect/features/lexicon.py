from typing import Dict, Set

# Minimal demonstration lexicon; replace/extend at runtime from a JSON file if desired.
POSITIVE = {
    "love": 0.9, "great": 0.8, "good": 0.6, "happy": 0.7, "joy": 0.8,
    "thanks": 0.5, "grateful": 0.7, "awesome": 0.9, "fun": 0.6, "nice": 0.5,
}
NEGATIVE = {
    "hate": -0.9, "bad": -0.6, "sad": -0.7, "angry": -0.8, "upset": -0.6,
    "terrible": -0.9, "awful": -0.9, "annoyed": -0.5, "cry": -0.6, "worse": -0.7,
}
LEXICON: Dict[str, float] = {}
LEXICON.update(POSITIVE)
LEXICON.update(NEGATIVE)

NEGATIONS: Set[str] = {"not","no","never","aint","isnt","arent","dont","doesnt","didnt","cant","couldnt","wont","wouldnt","shouldnt","n't"}
BOOSTERS: Dict[str, float] = {"very":1.3, "extremely":1.5, "super":1.25, "really":1.2, "so":1.1}
DIMINISHERS: Dict[str, float] = {"slightly":0.8, "somewhat":0.85, "kinda":0.85, "sorta":0.85, "maybe":0.9}
HEDGES: Set[str] = {"maybe","perhaps","seems","appears","probably","i think","i guess","kinda","sorta","might","could"}

TOXIC_SEEDS: Dict[str, float] = {
    # Very small seed set; expand offline. Values ~= intensity
    "stupid": 0.6, "idiot": 0.8, "dumb": 0.5, "hate": 0.6, "shut up": 0.8
}

EMOJI_POS = {":)", "🙂", "😊", "😄", "❤️", "💖", "👍", "🥳"}
EMOJI_NEG = {":(", "☹️", "😢", "😭", "😠", "😡", "👎"}
