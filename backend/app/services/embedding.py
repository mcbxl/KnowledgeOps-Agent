from __future__ import annotations

from hashlib import blake2b
from typing import Protocol

from app.core.config import Settings
from .text_utils import tokenize


class EmbeddingService(Protocol):
    dimensions: int | None

    def embed(self, text: str) -> list[float]:
        ...


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


class LangChainOpenAIEmbeddingService:
    """Production embedding provider backed by LangChain's OpenAI integration."""

    def __init__(self, model: str, api_key: str | None = None, dimensions: int | None = None) -> None:
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI embeddings require installing the 'prod' extras: pip install -e .[prod]"
            ) from exc

        kwargs: dict[str, object] = {"model": model}
        if api_key:
            kwargs["api_key"] = api_key
        if dimensions and model.startswith("text-embedding-3"):
            kwargs["dimensions"] = dimensions
        self.client = OpenAIEmbeddings(**kwargs)
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        return list(self.client.embed_query(text))


def build_embedding_service(settings: Settings) -> EmbeddingService:
    provider = settings.embedding_provider.lower()
    if provider in {"openai", "langchain_openai"}:
        return LangChainOpenAIEmbeddingService(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
            dimensions=settings.embedding_dimensions,
        )
    return DeterministicEmbeddingService(settings.embedding_dimensions)
