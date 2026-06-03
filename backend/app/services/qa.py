from __future__ import annotations

from app.schemas.api import AskResponse, Citation
from app.services.llm import AnswerGenerator, LocalCitationAnswerGenerator
from app.services.retrieval import HybridRetrievalService, hit_snippet


class AnswerAgent:
    def __init__(
        self,
        retrieval: HybridRetrievalService,
        generator: AnswerGenerator | None = None,
    ) -> None:
        self.retrieval = retrieval
        self.generator = generator or LocalCitationAnswerGenerator()

    def answer(
        self,
        query: str,
        intent: str = "auto",
        limit: int = 8,
        answer_mode: str = "knowledge_only",
    ) -> AskResponse:
        detected = self.retrieval.detect_intent(query, intent)
        hits = self.retrieval.search(query, detected, limit)
        citations = [
            Citation(
                document_id=hit.document.id,
                chunk_id=hit.chunk.id,
                title=hit.document.title,
                section_path=hit.chunk.section_path,
                page=hit.chunk.page,
                snippet=hit_snippet(hit.chunk.text),
                score=round(hit.score, 4),
            )
            for hit in hits
        ]
        if not hits:
            answer = "知识库中没有找到足够依据回答这个问题。"
            if answer_mode == "draft_with_gaps":
                answer += " 可以补充相关文档后重新提问。"
            return AskResponse(answer=answer, citations=[], detected_intent=detected, confidence=0.0)

        answer = self.generator.generate(query, hits, detected)
        confidence = min(0.95, sum(hit.score for hit in hits[:3]) / max(min(len(hits), 3), 1))
        return AskResponse(
            answer=answer,
            citations=citations,
            detected_intent=detected,
            confidence=round(confidence, 4),
        )
