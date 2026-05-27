from __future__ import annotations

from datetime import datetime, timezone
from app.schemas.api import AgentRunResponse, AgentStage
from app.services.ops import KnowledgeOpsService
from app.services.retrieval import HybridRetrievalService
from app.services.storage import KnowledgeStore


class KnowledgeOpsAgent:
    """Rule-based orchestration layer for the local MVP.

    The class keeps the same boundaries a LangGraph workflow would use in a
    production version: observe, diagnose, plan, and recommend actions.
    """

    def __init__(self, store: KnowledgeStore, retrieval: HybridRetrievalService) -> None:
        self.store = store
        self.retrieval = retrieval
        self.ops = KnowledgeOpsService(store)

    def run(self, objective: str, focus: str = "overview") -> AgentRunResponse:
        docs = self.store.list_documents()
        chunks = self.store.list_chunks()
        report = self.ops.build_report()
        stages = [
            self._observe_assets(len(docs), len(chunks), report.average_quality_score),
            self._diagnose_quality(report),
            self._diagnose_conflicts(report),
            self._probe_retrieval(docs, focus),
            self._plan_operations(report, focus),
        ]
        attention_count = sum(1 for stage in stages if stage.status == "needs_attention")
        summary = (
            f"已扫描 {len(docs)} 份文档和 {len(chunks)} 个知识片段，"
            f"平均质量分 {round(report.average_quality_score * 100)}%。"
        )
        if attention_count:
            summary += f" 发现 {attention_count} 个环节需要治理，建议优先处理高严重度问题。"
        else:
            summary += " 当前知识库状态稳定，可以继续扩充主题覆盖。"
        return AgentRunResponse(
            objective=objective,
            focus=focus,
            generated_at=datetime.now(timezone.utc),
            executive_summary=summary,
            stages=stages,
            recommended_backlog=self._backlog(report, focus),
        )

    def _observe_assets(self, doc_count: int, chunk_count: int, quality: float) -> AgentStage:
        status = "completed" if doc_count and chunk_count else "needs_attention"
        actions = [] if status == "completed" else ["导入至少 3 份 Markdown、PDF 或技术网页作为初始知识集。"]
        return AgentStage(
            name="资产盘点",
            status=status,
            observation=f"当前共有 {doc_count} 份文档、{chunk_count} 个 chunk，质量均分 {round(quality * 100)}%。",
            evidence=[f"documents={doc_count}", f"chunks={chunk_count}", f"quality={quality}"],
            next_actions=actions,
        )

    def _diagnose_quality(self, report) -> AgentStage:
        low_quality = [issue for issue in report.issues if issue.kind == "low_quality"]
        return AgentStage(
            name="质量诊断",
            status="needs_attention" if low_quality else "completed",
            observation=(
                f"发现 {len(low_quality)} 个低质量文档候选。"
                if low_quality
                else "未发现明显低质量文档，结构化程度基本可用。"
            ),
            evidence=[issue.title for issue in low_quality[:5]],
            next_actions=[
                "补充章节标题、摘要和关键结论。",
                "将过短的零散笔记合并成主题页。",
            ]
            if low_quality
            else ["继续保持文档的标题层级和来源元数据。"],
        )

    def _diagnose_conflicts(self, report) -> AgentStage:
        conflicts = [issue for issue in report.issues if issue.kind == "conflict_candidate"]
        return AgentStage(
            name="冲突检测",
            status="needs_attention" if conflicts else "completed",
            observation=(
                f"发现 {len(conflicts)} 个潜在知识冲突，需要人工确认权威版本。"
                if conflicts
                else "未发现明显版本冲突或互斥结论。"
            ),
            evidence=[issue.title for issue in conflicts[:5]],
            next_actions=[
                "为冲突文档标记版本、发布日期和权威来源。",
                "保留最新实践，将旧实践标记为 deprecated。",
            ]
            if conflicts
            else ["继续导入新资料后定期运行冲突扫描。"],
        )

    def _probe_retrieval(self, docs, focus: str) -> AgentStage:
        if not docs:
            return AgentStage(
                name="检索探测",
                status="needs_attention",
                observation="暂无文档，无法评估检索效果。",
                next_actions=["先导入样例文档，再执行检索评估。"],
            )
        probe = docs[0].tags[0] if docs[0].tags else docs[0].title
        hits = self.retrieval.search(probe, "auto", 3)
        top_score = round(hits[0].score, 3) if hits else 0.0
        status = "completed" if top_score >= 0.2 else "needs_attention"
        return AgentStage(
            name="检索探测",
            status=status,
            observation=f"使用主题词「{probe}」进行探测，Top1 相关度为 {top_score}。",
            evidence=[hit.document.title for hit in hits],
            next_actions=[
                "增加同义词标签和章节标题，提升关键词召回。",
                "后续接入 Qdrant 与 Cross-Encoder reranker 做生产级召回。",
            ]
            if status == "needs_attention"
            else ["保留当前 Hybrid Search 链路，并逐步扩充评测集。"],
        )

    def _plan_operations(self, report, focus: str) -> AgentStage:
        high_issues = [issue for issue in report.issues if issue.severity == "high"]
        actions = [
            "每周生成新增、过期、冲突、低质量文档报告。",
            "为高频主题自动生成 FAQ 和学习路线。",
            "将知识图谱中的孤立主题作为待补充知识点。",
        ]
        if focus == "conflict":
            actions.insert(0, "优先处理冲突候选，建立权威版本标记。")
        if focus == "retrieval":
            actions.insert(0, "优先构建检索 benchmark，记录 query、期望文档和命中率。")
        return AgentStage(
            name="治理计划",
            status="needs_attention" if high_issues else "completed",
            observation=f"当前高严重度问题 {len(high_issues)} 个，已生成下一步治理动作。",
            evidence=[issue.title for issue in high_issues[:5]],
            next_actions=actions,
        )

    def _backlog(self, report, focus: str) -> list[dict[str, str]]:
        backlog = [
            {
                "priority": "P0",
                "item": "接入真实向量库与关键词索引",
                "reason": "当前本地索引适合演示，生产版需要 Qdrant/Elasticsearch 支持规模化检索。",
            },
            {
                "priority": "P1",
                "item": "建立检索评估集",
                "reason": "用固定 query 衡量 TopK 命中率、引用覆盖率和答案忠实度。",
            },
            {
                "priority": "P1",
                "item": "升级冲突检测",
                "reason": "将启发式冲突候选升级为实体聚类、事实抽取和 NLI 判断。",
            },
        ]
        if report.issues:
            backlog.insert(
                0,
                {
                    "priority": "P0",
                    "item": "处理当前运营报告中的高严重度问题",
                    "reason": f"报告中共有 {len(report.issues)} 个问题候选，会影响知识可信度。",
                },
            )
        if focus == "growth":
            backlog.append(
                {
                    "priority": "P2",
                    "item": "自动生成主题补全建议",
                    "reason": "根据知识图谱发现孤立节点和缺失前置概念。",
                }
            )
        return backlog

