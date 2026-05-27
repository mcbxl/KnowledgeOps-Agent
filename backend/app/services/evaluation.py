from __future__ import annotations

from datetime import datetime, timezone
from app.schemas.api import RetrievalEvalCase, RetrievalEvalResponse
from app.services.retrieval import HybridRetrievalService
from app.services.storage import KnowledgeStore


class RetrievalEvaluationService:
    def __init__(self, store: KnowledgeStore, retrieval: HybridRetrievalService) -> None:
        self.store = store
        self.retrieval = retrieval

    def evaluate(self, queries: list[str], limit: int = 5) -> RetrievalEvalResponse:
        if not queries:
            queries = self._default_queries()
        cases: list[RetrievalEvalCase] = []
        for query in queries:
            hits = self.retrieval.search(query, "auto", limit)
            top_score = round(hits[0].score, 4) if hits else 0.0
            citation_ready = bool(hits and hits[0].document.title and hits[0].chunk.section_path)
            recommendation = self._recommendation(hits, top_score, citation_ready)
            cases.append(
                RetrievalEvalCase(
                    query=query,
                    hit_count=len(hits),
                    top_score=top_score,
                    citation_ready=citation_ready,
                    recommendation=recommendation,
                )
            )
        avg = round(sum(case.top_score for case in cases) / max(len(cases), 1), 4)
        ready = round(sum(1 for case in cases if case.citation_ready) / max(len(cases), 1), 4)
        return RetrievalEvalResponse(
            generated_at=datetime.now(timezone.utc),
            average_top_score=avg,
            citation_ready_rate=ready,
            cases=cases,
        )

    def _default_queries(self) -> list[str]:
        docs = self.store.list_documents()
        queries: list[str] = []
        for doc in docs[:6]:
            if doc.tags:
                queries.append(doc.tags[0])
            else:
                queries.append(doc.title)
        return queries or ["知识库有哪些内容？"]

    def _recommendation(self, hits, top_score: float, citation_ready: bool) -> str:
        if not hits:
            return "没有召回结果，建议补充相关文档或增加关键词标签。"
        if top_score < 0.2:
            return "Top1 分数偏低，建议优化标题层级、标签和分块粒度。"
        if not citation_ready:
            return "召回成功但引用元数据不足，建议检查 chunk 元数据绑定。"
        return "召回和引用元数据可用，可纳入基准评测。"

