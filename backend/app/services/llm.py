from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings
from app.services.retrieval import RetrievalHit, hit_snippet


class AnswerGenerator(Protocol):
    def generate(self, query: str, hits: list[RetrievalHit], detected_intent: str) -> str:
        ...


@dataclass
class LocalCitationAnswerGenerator:
    """Deterministic generator for local development and tests."""

    def generate(self, query: str, hits: list[RetrievalHit], detected_intent: str) -> str:
        if not hits:
            return "知识库中没有找到足够依据回答这个问题。"

        bullets = []
        for index, hit in enumerate(hits[:4], start=1):
            path = " > ".join(hit.chunk.section_path)
            bullets.append(
                f"{index}. 根据《{hit.document.title}》的 {path}: "
                f"{hit_snippet(hit.chunk.text, 220)}"
            )
        answer = "我只根据当前知识库检索到的片段回答：\n\n" + "\n".join(bullets)
        if detected_intent == "compare":
            answer += "\n\n这些片段来自不同来源或章节，适合作为对比分析的证据集合。"
        elif detected_intent == "summary":
            answer += "\n\n这是基于高相关片段的摘要，建议继续查看引用以确认完整上下文。"
        return answer


class LangChainOpenAIAnswerGenerator:
    """Grounded answer generation through LangChain chat models."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI answer generation requires installing the 'prod' extras: pip install -e .[prod]"
            ) from exc

        kwargs: dict[str, object] = {"model": model, "temperature": 0}
        if api_key:
            kwargs["api_key"] = api_key
        self.client = ChatOpenAI(**kwargs)
        self.human_message = HumanMessage
        self.system_message = SystemMessage

    def generate(self, query: str, hits: list[RetrievalHit], detected_intent: str) -> str:
        if not hits:
            return "知识库中没有找到足够依据回答这个问题。"

        context = "\n\n".join(
            f"[{index}] title={hit.document.title}\n"
            f"section={' > '.join(hit.chunk.section_path)}\n"
            f"score={hit.score:.4f}\n"
            f"text={hit.chunk.text}"
            for index, hit in enumerate(hits[:6], start=1)
        )
        messages = [
            self.system_message(
                content=(
                    "You are a KnowledgeOps RAG answer agent. Answer only from the provided "
                    "context. If evidence is insufficient, say what is missing. Include compact "
                    "source markers like [1] or [2]. Do not invent facts."
                )
            ),
            self.human_message(
                content=(
                    f"Question: {query}\n"
                    f"Detected intent: {detected_intent}\n\n"
                    f"Context:\n{context}\n\n"
                    "Return a concise Chinese answer with citations."
                )
            ),
        ]
        response = self.client.invoke(messages)
        return str(response.content).strip()


def build_answer_generator(settings: Settings) -> AnswerGenerator:
    provider = settings.llm_provider.lower()
    if provider in {"openai", "langchain_openai"}:
        return LangChainOpenAIAnswerGenerator(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
        )
    return LocalCitationAnswerGenerator()
