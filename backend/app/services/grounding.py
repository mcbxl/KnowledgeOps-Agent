from __future__ import annotations

from app.schemas.api import AnswerGrounding, Citation
from app.services.text_utils import tokenize


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "using",
    "with",
    "you",
    "your",
    "根据",
    "当前",
    "知识库",
    "片段",
    "回答",
    "引用",
}


class GroundingAuditor:
    """Lightweight faithfulness check over generated answers and returned citations."""

    def audit(self, answer: str, citations: list[Citation]) -> AnswerGrounding:
        answer_terms = self._content_terms(answer)
        evidence_terms = self._content_terms(" ".join(citation.snippet for citation in citations))
        if not answer_terms:
            return AnswerGrounding(
                status="unsupported",
                groundedness_score=0.0,
                evidence_coverage=0.0,
                citation_count=len(citations),
                warnings=["Answer has no auditable content terms."],
            )
        if not citations or not evidence_terms:
            return AnswerGrounding(
                status="unsupported",
                groundedness_score=0.0,
                evidence_coverage=0.0,
                citation_count=len(citations),
                unsupported_terms=sorted(answer_terms)[:12],
                warnings=["No citation evidence is available."],
            )

        supported = answer_terms & evidence_terms
        unsupported = answer_terms - evidence_terms
        coverage = len(supported) / max(len(answer_terms), 1)
        citation_strength = min(1.0, len(citations) / 3)
        score = round(coverage * 0.82 + citation_strength * 0.18, 4)
        warnings = []
        if coverage < 0.35:
            warnings.append("Answer terms have low overlap with citation snippets.")
        if len(citations) < 2:
            warnings.append("Answer relies on fewer than two citations.")

        if score >= 0.72:
            status = "grounded"
        elif score >= 0.42:
            status = "weak"
        else:
            status = "unsupported"

        return AnswerGrounding(
            status=status,
            groundedness_score=score,
            evidence_coverage=round(coverage, 4),
            citation_count=len(citations),
            unsupported_terms=sorted(unsupported)[:12],
            warnings=warnings,
        )

    def _content_terms(self, text: str) -> set[str]:
        return {term for term in tokenize(text) if len(term) > 2 and term not in STOPWORDS}
