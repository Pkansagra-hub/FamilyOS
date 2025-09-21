import re
from typing import List, Tuple

_WORD_RE = re.compile(r"[A-Za-z']+|[:;=8xX]-?[)D(]")

def tokenize(text: str) -> List[str]:
    # Simple tokenizer: words + basic emoticons
    return _WORD_RE.findall(text or "")

def exclaim_rate(text: str) -> float:
    return (text or "").count("!") / max(1, len(text))

def allcaps_rate(tokens: List[str]) -> float:
    caps = [t for t in tokens if len(t) > 2 and t.isupper()]
    return len(caps) / max(1, len(tokens))

def punctuation_density(text: str) -> float:
    punct = sum(1 for ch in (text or "") if ch in "!?.,;:")
    toks = max(1, len(tokenize(text)))
    return punct / toks

def emoji_counts(text: str) -> Tuple[int, int]:
    pos = sum(1 for ch in (text or "") if ch in "🙂😊😄❤️💖👍🥳")
    neg = sum(1 for ch in (text or "") if ch in "☹️😢😭😠😡👎")
    return pos, neg
