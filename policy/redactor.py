from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Pattern

# Base regexes
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"\b(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b"
)
# Credit cards – filter by Luhn
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
URL_RE = re.compile(r"\bhttps?://\S+\b")
IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _luhn_check(number: str) -> bool:
    digits = [int(ch) for ch in re.sub(r"\D", "", number)]
    if len(digits) < 13 or len(digits) > 16:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


@dataclass
class RedactionSpan:
    start: int
    end: int
    label: str


@dataclass
class RedactionResult:
    text: str
    spans: List[RedactionSpan] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)


class Redactor:
    def __init__(
        self,
        categories: List[str] | None = None,
        custom_patterns: Dict[str, Pattern] | None = None,
    ):
        self.categories = categories or [
            "pii.email",
            "pii.phone",
            "pii.cc",
            "url",
            "pii.ip",
            "pii.ssn",
        ]
        self.custom_patterns = custom_patterns or {}

    def redact_text(self, text: str) -> RedactionResult:
        spans: List[RedactionSpan] = []
        out = text

        def _apply(pattern: Pattern, label: str, validator=None):
            nonlocal out, spans
            new_spans = []
            s = 0
            while True:
                m = pattern.search(out, s)
                if not m:
                    break
                val = m.group(0)
                if validator and not validator(val):
                    s = m.end()
                    continue
                new_spans.append(RedactionSpan(m.start(), m.end(), label))
                s = m.end()
            spans.extend(new_spans)
            out_tmp = pattern.sub(f"[REDACT:{label}]", out)
            out = out_tmp

        patterns = []
        if "pii.email" in self.categories:
            patterns.append((EMAIL_RE, "EMAIL", None))
        if "pii.phone" in self.categories:
            patterns.append((PHONE_RE, "PHONE", None))
        if "pii.cc" in self.categories:
            patterns.append((CC_RE, "CC", _luhn_check))
        if "url" in self.categories:
            patterns.append((URL_RE, "URL", None))
        if "pii.ip" in self.categories:
            patterns.append((IP_RE, "IP", None))
        if "pii.ssn" in self.categories:
            patterns.append((SSN_RE, "SSN", None))
        for k, pat in self.custom_patterns.items():
            patterns.append((pat, k.upper(), None))

        for p, label, validator in patterns:
            _apply(p, label, validator)

        return RedactionResult(text=out, spans=spans, categories=self.categories)

    def redact_payload(
        self, payload: Dict[str, Any], key_policies: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
        if not key_policies:
            return payload
        redacted = dict(payload)
        for k, cat in key_policies.items():
            if k in redacted and isinstance(redacted[k], str):
                tmp = Redactor([cat]).redact_text(redacted[k])
                redacted[k] = tmp.text
        return redacted
