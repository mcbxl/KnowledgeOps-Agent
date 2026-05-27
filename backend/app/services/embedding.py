from __future__ import annotations

from hashlib import blake2b
from .text_utils import tokenize


class DeterministicEmbeddingService:
    """Small local embedding replacement for development and tests.

    Production deployments can replace this with OpenAI, BGE, Jina, or a gateway service
    without changing retrieval orchestration.
    """

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = sum(v * v for v in vector) ** 0.5
        if norm:
            vector = [v / norm for v in vector]
        return vector

