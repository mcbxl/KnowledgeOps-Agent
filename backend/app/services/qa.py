from __future__ import annotations

from app.schemas.api import AskResponse, Citation
from app.services.retrieval import HybridRetrievalService, hit_snippet


class AnswerAgent:
    def __init__(self, retrieval: HybridRetrievalService) -> None:
        self.retrieval = retrieval

    def answer(self, query: str, intent: str = "auto", limit: int = 8, answer_mode: str = "knowledge_only") -> AskResponse:
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

        bullets = []
        for index, hit in enumerate(hits[:4], start=1):
            path = " > ".join(hit.chunk.section_path)
            bullets.append(f"{index}. 根据《{hit.document.title}》的 {path}：{hit_snippet(hit.chunk.text, 220)}")
        answer = "我只根据当前知识库检索到的片段回答：\n\n" + "\n".join(bullets)
        if detected == "compare":
            answer += "\n\n这些片段来自不同来源或章节，适合作为对比分析的证据集合。"
        elif detected == "summary":
            answer += "\n\n这是基于高相关片段的摘要，建议继续查看引用以确认完整上下文。"

        confidence = min(0.95, sum(hit.score for hit in hits[:3]) / max(min(len(hits), 3), 1))
        return AskResponse(
            answer=answer,
            citations=citations,
            detected_intent=detected,
            confidence=round(confidence, 4),
        )

