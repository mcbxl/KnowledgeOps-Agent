from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings
from app.models.domain import Chunk, Document


@dataclass
class VectorSearchHit:
    chunk_id: str
    score: float


class VectorIndex(Protocol):
    enabled: bool

    def upsert_chunks(self, document: Document, chunks: list[Chunk]) -> None:
        ...

    def search(self, query_embedding: list[float], limit: int) -> list[VectorSearchHit]:
        ...


class NoopVectorIndex:
    enabled = False

    def upsert_chunks(self, document: Document, chunks: list[Chunk]) -> None:
        return None

    def search(self, query_embedding: list[float], limit: int) -> list[VectorSearchHit]:
        return []


class QdrantVectorIndex:
    enabled = True

    def __init__(self, url: str, collection: str, api_key: str | None = None) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, PointStruct, VectorParams
        except ImportError as exc:
            raise RuntimeError(
                "Qdrant integration requires installing the 'prod' extras: pip install -e .[prod]"
            ) from exc

        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection = collection
        self.distance = Distance
        self.point = PointStruct
        self.vector_params = VectorParams

    def upsert_chunks(self, document: Document, chunks: list[Chunk]) -> None:
        chunks = [chunk for chunk in chunks if chunk.embedding]
        if not chunks:
            return
        self._ensure_collection(len(chunks[0].embedding))
        self.client.upsert(
            collection_name=self.collection,
            points=[
                self.point(
                    id=chunk.id,
                    vector=chunk.embedding,
                    payload={
                        "document_id": document.id,
                        "title": document.title,
                        "section_path": chunk.section_path,
                        "tags": chunk.tags,
                        "order_index": chunk.order_index,
                    },
                )
                for chunk in chunks
            ],
        )

    def search(self, query_embedding: list[float], limit: int) -> list[VectorSearchHit]:
        if not query_embedding:
            return []
        self._ensure_collection(len(query_embedding))
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            limit=limit,
        )
        return [VectorSearchHit(chunk_id=str(result.id), score=float(result.score)) for result in results]

    def _ensure_collection(self, dimensions: int) -> None:
        existing = {collection.name for collection in self.client.get_collections().collections}
        if self.collection in existing:
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=self.vector_params(size=dimensions, distance=self.distance.COSINE),
        )


def build_vector_index(settings: Settings) -> VectorIndex:
    if settings.enable_qdrant:
        if not settings.qdrant_url:
            raise RuntimeError("KNOWLEDGEOPS_QDRANT_URL is required when Qdrant is enabled.")
        return QdrantVectorIndex(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection=settings.qdrant_collection,
        )
    return NoopVectorIndex()
