from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from app.models.domain import Chunk, Document
from app.services.embedding import EmbeddingService
from app.services.storage import KnowledgeStore
from app.services.text_utils import cosine, normalize_space, tokenize
from app.services.vector_store import NoopVectorIndex, VectorIndex


@dataclass
class RetrievalHit:
    chunk: Chunk
    document: Document
    score: float
    lexical_score: float
    vector_score: float
    rerank_score: float


class HybridRetrievalService:
    def __init__(
        self,
        store: KnowledgeStore,
        embedder: EmbeddingService,
        vector_index: VectorIndex | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.vector_index = vector_index or NoopVectorIndex()

    def search(self, query: str, intent: str = "auto", limit: int = 8) -> list[RetrievalHit]:
        detected_intent = self.detect_intent(query, intent)
        weights = self._weights_for_intent(detected_intent)
        chunks = self.store.list_chunks()
        documents = {doc.id: doc for doc in self.store.list_documents()}
        lexical = self._bm25(query, chunks)
        query_embedding = self.embedder.embed(query)
        vector_index_scores = {
            hit.chunk_id: max(0.0, min(1.0, hit.score))
            for hit in self.vector_index.search(query_embedding, max(limit * 4, 20))
        }
        hits: list[RetrievalHit] = []
        query_tokens = set(tokenize(query))

        for chunk in chunks:
            vector_score = vector_index_scores.get(
                chunk.id,
                max(0.0, cosine(query_embedding, chunk.embedding)),
            )
            lexical_score = lexical.get(chunk.id, 0.0)
            rerank_score = self._rerank(query_tokens, chunk)
            score = (
                weights["lexical"] * lexical_score
                + weights["vector"] * vector_score
                + weights["rerank"] * rerank_score
            )
            if score <= 0:
                continue
            hits.append(
                RetrievalHit(
                    chunk=chunk,
                    document=documents[chunk.document_id],
                    score=score,
                    lexical_score=lexical_score,
                    vector_score=vector_score,
                    rerank_score=rerank_score,
                )
            )

        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]

    def detect_intent(self, query: str, intent: str = "auto") -> str:
        if intent != "auto":
            return intent
        q = query.lower()
        if any(term in q for term in ["compare", "difference", "对比", "区别", "vs"]):
            return "compare"
        if any(term in q for term in ["summarize", "summary", "总结", "概括"]):
            return "summary"
        if any(term in q for term in ["what is", "explain", "是什么", "解释"]):
            return "concept"
        return "fact"

    def _weights_for_intent(self, intent: str) -> dict[str, float]:
        return {
            "fact": {"lexical": 0.48, "vector": 0.26, "rerank": 0.26},
            "concept": {"lexical": 0.25, "vector": 0.48, "rerank": 0.27},
            "summary": {"lexical": 0.22, "vector": 0.52, "rerank": 0.26},
            "compare": {"lexical": 0.32, "vector": 0.38, "rerank": 0.30},
        }.get(intent, {"lexical": 0.35, "vector": 0.40, "rerank": 0.25})

    def _bm25(self, query: str, chunks: list[Chunk]) -> dict[str, float]:
        query_terms = tokenize(query)
        if not query_terms or not chunks:
            return {}
        doc_tokens = {chunk.id: tokenize(" ".join(chunk.section_path) + " " + chunk.text) for chunk in chunks}
        avgdl = sum(len(tokens) for tokens in doc_tokens.values()) / max(len(doc_tokens), 1)
        df = defaultdict(int)
        for tokens in doc_tokens.values():
            for term in set(tokens):
                df[term] += 1
        scores: dict[str, float] = {}
        k1 = 1.5
        b = 0.75
        n_docs = len(chunks)
        for chunk in chunks:
            tokens = doc_tokens[chunk.id]
            counts = Counter(tokens)
            score = 0.0
            for term in query_terms:
                if term not in counts:
                    continue
                idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
                tf = counts[term]
                denom = tf + k1 * (1 - b + b * len(tokens) / max(avgdl, 1))
                score += idf * (tf * (k1 + 1)) / denom
            scores[chunk.id] = min(score / 6.0, 1.0)
        return scores

    def _rerank(self, query_tokens: set[str], chunk: Chunk) -> float:
        if not query_tokens:
            return 0.0
        chunk_tokens = set(tokenize(chunk.text))
        section_tokens = set(tokenize(" ".join(chunk.section_path)))
        overlap = len(query_tokens & chunk_tokens) / len(query_tokens)
        section_boost = len(query_tokens & section_tokens) / len(query_tokens)
        length_penalty = 0.0 if 160 <= len(chunk.text) <= 1600 else 0.08
        return max(0.0, min(1.0, overlap * 0.75 + section_boost * 0.25 - length_penalty))


def hit_snippet(text: str, max_chars: int = 260) -> str:
    cleaned = normalize_space(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(" ", 1)[0] + "..."
