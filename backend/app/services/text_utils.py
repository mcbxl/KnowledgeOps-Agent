from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def summarize(text: str, max_chars: int = 320) -> str:
    cleaned = normalize_space(text)
    if len(cleaned) <= max_chars:
        return cleaned
    sentence_parts = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    summary = ""
    for part in sentence_parts:
        if len(summary) + len(part) + 1 > max_chars:
            break
        summary = f"{summary} {part}".strip()
    return summary or cleaned[:max_chars].rsplit(" ", 1)[0]


def extract_tags(title: str, content: str, limit: int = 8) -> list[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "are",
        "was",
        "were",
        "have",
        "has",
        "into",
        "about",
    }
    tokens = [t for t in tokenize(f"{title} {content[:4000]}") if len(t) > 2 and t not in stopwords]
    counts = Counter(tokens)
    return [term for term, _ in counts.most_common(limit)]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

