from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.schemas.api import OpsReport, QualityIssue, TopicCoverage
from app.services.guardrails import PromptInjectionScanner
from app.services.storage import KnowledgeStore
from app.services.text_utils import normalize_space, tokenize


class KnowledgeOpsService:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self.prompt_scanner = PromptInjectionScanner()

    def build_report(self) -> OpsReport:
        docs = self.store.list_documents()
        chunks = self.store.list_chunks()
        issues: list[QualityIssue] = []
        issues.extend(self._duplicate_issues(docs))
        issues.extend(self._quality_issues(docs))
        issues.extend(self._prompt_injection_issues(docs))
        issues.extend(self._conflict_candidates(chunks))
        topic_coverage = self._topic_coverage(docs, chunks)
        quality_scores = [self._quality_score(doc.content) for doc in docs]
        return OpsReport(
            generated_at=datetime.now(timezone.utc),
            document_count=len(docs),
            chunk_count=len(chunks),
            average_quality_score=round(sum(quality_scores) / max(len(quality_scores), 1), 3),
            issues=issues,
            topic_coverage=topic_coverage,
            faqs=self._faqs(docs),
            learning_path=self._learning_path(docs, topic_coverage),
            graph=self._graph(docs, chunks, topic_coverage),
        )

    def _duplicate_issues(self, docs) -> list[QualityIssue]:
        by_hash = defaultdict(list)
        for doc in docs:
            by_hash[doc.content_hash].append(doc)
        issues: list[QualityIssue] = []
        for group in by_hash.values():
            if len(group) <= 1:
                continue
            titles = [doc.title for doc in group]
            issues.append(
                QualityIssue(
                    kind="duplicate",
                    severity="high",
                    title="Duplicate documents detected",
                    description="Multiple documents have the same content hash.",
                    document_ids=[doc.id for doc in group],
                    confidence=0.98,
                    evidence=titles,
                    suggested_actions=[
                        "Keep the newest or most authoritative source.",
                        "Archive duplicates after confirming ownership.",
                    ],
                )
            )
        return issues

    def _quality_issues(self, docs) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for doc in docs:
            score = self._quality_score(doc.content)
            heading_count = sum(1 for line in doc.content.splitlines() if line.strip().startswith("#"))
            token_count = len(tokenize(doc.content))
            if score >= 0.45:
                continue
            issues.append(
                QualityIssue(
                    kind="low_quality",
                    severity="medium",
                    title=f"Low quality document: {doc.title}",
                    description="The document is short, weakly structured, or has low information density.",
                    document_ids=[doc.id],
                    confidence=round(1 - score, 3),
                    evidence=[
                        f"quality_score={score}",
                        f"token_count={token_count}",
                        f"heading_count={heading_count}",
                    ],
                    suggested_actions=[
                        "Add section headings and a short summary.",
                        "Merge tiny notes into a topic page.",
                        "Add source, version, and key takeaways.",
                    ],
                )
            )
        return issues

    def _prompt_injection_issues(self, docs) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for doc in docs:
            report = self.prompt_scanner.scan(doc.content)
            if not report.is_risky:
                continue
            severity = "high" if report.risk_level == "high" else "medium"
            issues.append(
                QualityIssue(
                    kind="prompt_injection_risk",
                    severity=severity,
                    title=f"Prompt injection risk: {doc.title}",
                    description=(
                        "The document contains instructions that look like prompt injection, "
                        "secret exfiltration, or attempts to override system/developer guidance."
                    ),
                    document_ids=[doc.id],
                    confidence=0.92 if severity == "high" else 0.74,
                    evidence=[finding.snippet for finding in report.findings[:5]],
                    suggested_actions=[
                        "Review the source before using it for answer generation.",
                        "Keep this document quarantined or tag it as untrusted.",
                        "Prefer trusted source allowlists for web ingestion.",
                    ],
                )
            )
        return issues

    def _conflict_candidates(self, chunks) -> list[QualityIssue]:
        topic_claims = defaultdict(list)
        conflict_pairs = [
            ("reactdom.render", "createroot"),
            ("deprecated", "recommended"),
            ("legacy", "new"),
            ("old", "new"),
            ("must", "must not"),
            ("should", "should not"),
            ("required", "forbidden"),
        ]
        for chunk in chunks:
            lower = chunk.text.lower()
            if any(left in lower or right in lower for left, right in conflict_pairs):
                topic_claims[self._topic_key(chunk.text)].append(chunk)

        issues: list[QualityIssue] = []
        for topic, group in topic_claims.items():
            texts = " ".join(chunk.text.lower() for chunk in group)
            matched_pairs = [
                f"{left} <> {right}"
                for left, right in conflict_pairs
                if left in texts and right in texts
            ]
            if not matched_pairs:
                continue
            snippets = [self._snippet(chunk.text) for chunk in group[:4]]
            issues.append(
                QualityIssue(
                    kind="conflict_candidate",
                    severity="high",
                    title=f"Potential conflict: {topic}",
                    description="Similar topic chunks contain version-migration, deprecation, or opposing guidance signals.",
                    document_ids=sorted({chunk.document_id for chunk in group}),
                    confidence=min(0.95, 0.55 + len(matched_pairs) * 0.12 + len(group) * 0.04),
                    evidence=[*matched_pairs, *snippets],
                    suggested_actions=[
                        "Check publication date and version metadata.",
                        "Mark the authoritative guidance as current.",
                        "Label old guidance as deprecated instead of deleting it.",
                    ],
                )
            )
        return issues

    def _topic_coverage(self, docs, chunks) -> list[TopicCoverage]:
        doc_by_id = {doc.id: doc for doc in docs}
        topic_docs: dict[str, set[str]] = defaultdict(set)
        topic_chunks: Counter[str] = Counter()

        for doc in docs:
            for tag in doc.tags[:8]:
                topic_docs[tag].add(doc.id)
        for chunk in chunks:
            doc = doc_by_id.get(chunk.document_id)
            tags = chunk.tags or (doc.tags if doc else [])
            for tag in tags[:8]:
                topic_docs[tag].add(chunk.document_id)
                topic_chunks[tag] += 1

        coverage: list[TopicCoverage] = []
        for topic, doc_ids in topic_docs.items():
            chunk_count = topic_chunks[topic]
            if chunk_count <= 1 or len(doc_ids) <= 1:
                hint = "thin"
            elif chunk_count >= 8:
                hint = "dense"
            else:
                hint = "healthy"
            coverage.append(
                TopicCoverage(
                    topic=topic,
                    document_count=len(doc_ids),
                    chunk_count=chunk_count,
                    quality_hint=hint,
                    related_documents=sorted(doc_ids),
                )
            )
        return sorted(coverage, key=lambda item: (item.quality_hint == "thin", -item.chunk_count))

    def _quality_score(self, content: str) -> float:
        tokens = tokenize(content)
        heading_bonus = min(sum(1 for line in content.splitlines() if line.strip().startswith("#")) / 8, 0.25)
        length_score = min(len(tokens) / 900, 0.45)
        density = min(len(set(tokens)) / max(len(tokens), 1) * 1.2, 0.30)
        return round(min(1.0, length_score + density + heading_bonus), 3)

    def _topic_key(self, text: str) -> str:
        counts = Counter(token for token in tokenize(text) if len(token) > 2)
        common = [term for term, _ in counts.most_common(3)]
        return " / ".join(common) if common else "unknown topic"

    def _faqs(self, docs) -> list[dict[str, str]]:
        faqs = []
        for doc in docs[:8]:
            tag = doc.tags[0] if doc.tags else doc.title
            faqs.append(
                {
                    "question": f"What is the key idea of {tag}?",
                    "answer": doc.summary or "No summary is available yet.",
                }
            )
        return faqs

    def _learning_path(self, docs, coverage: list[TopicCoverage]) -> list[str]:
        if not docs:
            return ["Import course notes, papers, project docs, or web pages first."]
        thin_topics = [topic.topic for topic in coverage if topic.quality_hint == "thin"][:3]
        healthy_topics = [topic.topic for topic in coverage if topic.quality_hint != "thin"][:5]
        path = [f"Stage {idx}: study and summarize {topic}" for idx, topic in enumerate(healthy_topics, start=1)]
        path.extend(f"Gap: add more sources for {topic}" for topic in thin_topics)
        return path or ["Add tags to documents so the agent can build a learning path."]

    def _graph(self, docs, chunks, coverage: list[TopicCoverage]) -> dict:
        nodes = []
        edges = []
        seen = set()
        coverage_by_topic = {item.topic: item for item in coverage}
        doc_by_id = {doc.id: doc for doc in docs}

        for doc in docs:
            nodes.append(
                {
                    "id": doc.id,
                    "label": doc.title,
                    "type": "document",
                    "meta": {"source_type": doc.source_type, "chunk_count": self.store.count_chunks(doc.id)},
                }
            )
            for tag in doc.tags[:6]:
                tag_id = f"topic:{tag}"
                if tag_id not in seen:
                    topic = coverage_by_topic.get(tag)
                    nodes.append(
                        {
                            "id": tag_id,
                            "label": tag,
                            "type": "topic",
                            "meta": {"coverage": topic.quality_hint if topic else "unknown"},
                        }
                    )
                    seen.add(tag_id)
                edges.append({"source": doc.id, "target": tag_id, "type": "tagged_as"})

        section_counter: Counter[str] = Counter()
        for chunk in chunks:
            if not chunk.section_path:
                continue
            section = chunk.section_path[-1]
            section_id = f"section:{chunk.document_id}:{section}"
            section_counter[section_id] += 1
            if section_counter[section_id] == 1:
                nodes.append({"id": section_id, "label": section, "type": "section"})
                edges.append({"source": chunk.document_id, "target": section_id, "type": "has_section"})
            doc = doc_by_id.get(chunk.document_id)
            for tag in (chunk.tags or (doc.tags if doc else []))[:3]:
                edges.append({"source": section_id, "target": f"topic:{tag}", "type": "mentions"})

        return {"nodes": nodes, "edges": edges, "chunkCount": len(chunks)}

    def _snippet(self, text: str, max_chars: int = 220) -> str:
        cleaned = normalize_space(text)
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[:max_chars].rsplit(" ", 1)[0] + "..."
