from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from app.schemas.api import OpsReport, QualityIssue
from app.services.storage import KnowledgeStore
from app.services.text_utils import tokenize


class KnowledgeOpsService:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store

    def build_report(self) -> OpsReport:
        docs = self.store.list_documents()
        chunks = self.store.list_chunks()
        issues: list[QualityIssue] = []
        issues.extend(self._duplicate_issues(docs))
        issues.extend(self._quality_issues(docs))
        issues.extend(self._conflict_candidates(chunks))
        quality_scores = [self._quality_score(doc.content) for doc in docs]
        graph = self._graph(docs, chunks)
        return OpsReport(
            generated_at=datetime.now(timezone.utc),
            document_count=len(docs),
            chunk_count=len(chunks),
            average_quality_score=round(sum(quality_scores) / max(len(quality_scores), 1), 3),
            issues=issues,
            faqs=self._faqs(docs),
            learning_path=self._learning_path(docs),
            graph=graph,
        )

    def _duplicate_issues(self, docs) -> list[QualityIssue]:
        by_hash = defaultdict(list)
        for doc in docs:
            by_hash[doc.content_hash].append(doc)
        issues = []
        for group in by_hash.values():
            if len(group) > 1:
                issues.append(
                    QualityIssue(
                        kind="duplicate",
                        severity="high",
                        title="发现重复文档",
                        description="多个文档内容哈希一致，建议保留来源更权威或更新时间更近的一份。",
                        document_ids=[doc.id for doc in group],
                    )
                )
        return issues

    def _quality_issues(self, docs) -> list[QualityIssue]:
        issues = []
        for doc in docs:
            score = self._quality_score(doc.content)
            if score < 0.45:
                issues.append(
                    QualityIssue(
                        kind="low_quality",
                        severity="medium",
                        title=f"低质量文档：{doc.title}",
                        description="文档长度、结构化标题或信息密度不足，建议补充摘要、章节或关键结论。",
                        document_ids=[doc.id],
                    )
                )
        return issues

    def _conflict_candidates(self, chunks) -> list[QualityIssue]:
        claims = defaultdict(list)
        conflict_terms = [
            ("reactdom.render", "createroot"),
            ("deprecated", "recommended"),
            ("旧", "新"),
            ("必须", "不要"),
            ("should", "should not"),
        ]
        for chunk in chunks:
            lower = chunk.text.lower()
            for left, right in conflict_terms:
                if left in lower or right in lower:
                    topic = self._topic_key(chunk.text)
                    claims[topic].append(chunk)
        issues = []
        for topic, group in claims.items():
            texts = " ".join(chunk.text.lower() for chunk in group)
            has_conflict_pair = any(left in texts and right in texts for left, right in conflict_terms)
            doc_ids = sorted({chunk.document_id for chunk in group})
            if has_conflict_pair and len(doc_ids) >= 1:
                issues.append(
                    QualityIssue(
                        kind="conflict_candidate",
                        severity="high",
                        title=f"潜在知识冲突：{topic}",
                        description="相近主题中出现互斥、版本迁移或废弃/推荐类表述，建议人工确认并标记权威版本。",
                        document_ids=doc_ids,
                    )
                )
        return issues

    def _quality_score(self, content: str) -> float:
        tokens = tokenize(content)
        heading_bonus = min(content.count("\n#") / 8, 0.25)
        length_score = min(len(tokens) / 900, 0.45)
        density = min(len(set(tokens)) / max(len(tokens), 1) * 1.2, 0.30)
        return round(min(1.0, length_score + density + heading_bonus), 3)

    def _topic_key(self, text: str) -> str:
        counts = Counter(tokenize(text))
        common = [term for term, _ in counts.most_common(3)]
        return " / ".join(common) if common else "未知主题"

    def _faqs(self, docs) -> list[dict[str, str]]:
        faqs = []
        for doc in docs[:8]:
            tag = doc.tags[0] if doc.tags else doc.title
            faqs.append(
                {
                    "question": f"{tag} 的核心内容是什么？",
                    "answer": doc.summary or "该文档暂无摘要。",
                }
            )
        return faqs

    def _learning_path(self, docs) -> list[str]:
        tag_counts = Counter(tag for doc in docs for tag in doc.tags)
        topics = [tag for tag, _ in tag_counts.most_common(6)]
        if not topics:
            return ["先导入课程讲义、论文或项目文档，再生成学习路线。"]
        return [f"阶段 {idx}: 阅读并整理 {topic} 相关文档" for idx, topic in enumerate(topics, start=1)]

    def _graph(self, docs, chunks) -> dict:
        nodes = []
        edges = []
        seen_tags = set()
        for doc in docs:
            nodes.append({"id": doc.id, "label": doc.title, "type": "document"})
            for tag in doc.tags[:6]:
                tag_id = f"tag:{tag}"
                if tag_id not in seen_tags:
                    nodes.append({"id": tag_id, "label": tag, "type": "tag"})
                    seen_tags.add(tag_id)
                edges.append({"source": doc.id, "target": tag_id, "type": "tagged_as"})
        return {"nodes": nodes, "edges": edges, "chunkCount": len(chunks)}

