from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.api import BenchmarkCase, RetrievalEvalCase, RetrievalEvalResponse
from app.services.retrieval import HybridRetrievalService
from app.services.storage import KnowledgeStore


class RetrievalEvaluationService:
    def __init__(self, store: KnowledgeStore, retrieval: HybridRetrievalService) -> None:
        self.store = store
        self.retrieval = retrieval

    def evaluate(self, queries: list[str], limit: int = 5) -> RetrievalEvalResponse:
        if not queries:
            queries = self._default_queries()
        cases = [BenchmarkCase(query=query) for query in queries]
        return self.evaluate_cases(cases, limit)

    def evaluate_cases(
        self,
        cases_to_run: list[BenchmarkCase],
        limit: int = 5,
        benchmark_id: str | None = None,
        benchmark_name: str | None = None,
    ) -> RetrievalEvalResponse:
        cases: list[RetrievalEvalCase] = []
        expected_total = 0
        expected_hits = 0

        for case in cases_to_run:
            hits = self.retrieval.search(case.query, "auto", limit)
            top_score = round(hits[0].score, 4) if hits else 0.0
            citation_ready = bool(hits and hits[0].document.title and hits[0].chunk.section_path)
            expected_hit = self._expected_hit(hits, case)
            if case.expected_document_id or case.expected_chunk_id:
                expected_total += 1
                expected_hits += 1 if expected_hit else 0
            recommendation = self._recommendation(hits, top_score, citation_ready, expected_hit)
            cases.append(
                RetrievalEvalCase(
                    query=case.query,
                    hit_count=len(hits),
                    top_score=top_score,
                    citation_ready=citation_ready,
                    recommendation=recommendation,
                    expected_document_id=case.expected_document_id,
                    expected_chunk_id=case.expected_chunk_id,
                    expected_hit=expected_hit,
                )
            )

        avg = round(sum(case.top_score for case in cases) / max(len(cases), 1), 4)
        ready = round(sum(1 for case in cases if case.citation_ready) / max(len(cases), 1), 4)
        expected_hit_rate = None
        if expected_total:
            expected_hit_rate = round(expected_hits / expected_total, 4)
        return RetrievalEvalResponse(
            generated_at=datetime.now(timezone.utc),
            average_top_score=avg,
            citation_ready_rate=ready,
            cases=cases,
            expected_hit_rate=expected_hit_rate,
            benchmark_id=benchmark_id,
            benchmark_name=benchmark_name,
        )

    def run_benchmark(self, benchmark: dict) -> RetrievalEvalResponse:
        cases = [BenchmarkCase(**case) for case in benchmark["cases"]]
        return self.evaluate_cases(
            cases,
            benchmark["limit"],
            benchmark_id=benchmark["id"],
            benchmark_name=benchmark["name"],
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

    def _recommendation(
        self,
        hits,
        top_score: float,
        citation_ready: bool,
        expected_hit: bool | None,
    ) -> str:
        if not hits:
            return "没有召回结果，建议补充相关文档或增加关键词标签。"
        if expected_hit is False:
            return "召回结果未命中期望文档或 chunk，建议检查 embedding、标签和分块边界。"
        if top_score < 0.2:
            return "Top1 分数偏低，建议优化标题层级、标签和分块粒度。"
        if not citation_ready:
            return "召回成功但引用元数据不足，建议检查 chunk 元数据绑定。"
        return "召回和引用元数据可用，可纳入基准评测。"

    def _expected_hit(self, hits, case: BenchmarkCase) -> bool | None:
        if not case.expected_document_id and not case.expected_chunk_id:
            return None
        for hit in hits:
            document_ok = not case.expected_document_id or hit.document.id == case.expected_document_id
            chunk_ok = not case.expected_chunk_id or hit.chunk.id == case.expected_chunk_id
            if document_ok and chunk_ok:
                return True
        return False
