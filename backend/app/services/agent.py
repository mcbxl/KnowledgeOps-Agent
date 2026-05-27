from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.schemas.api import AgentRunResponse, AgentStage
from app.services.ops import KnowledgeOpsService
from app.services.retrieval import HybridRetrievalService
from app.services.storage import KnowledgeStore


class AgentState(TypedDict, total=False):
    objective: str
    focus: str
    doc_count: int
    chunk_count: int
    quality_score: float
    report: object
    stages: list[AgentStage]
    recommended_backlog: list[dict[str, str]]


class KnowledgeOpsAgent:
    """LangGraph-orchestrated KnowledgeOps workflow."""

    def __init__(self, store: KnowledgeStore, retrieval: HybridRetrievalService) -> None:
        self.store = store
        self.retrieval = retrieval
        self.ops = KnowledgeOpsService(store)
        self.graph = self._build_graph()

    def run(self, objective: str, focus: str = "overview") -> AgentRunResponse:
        state = self.graph.invoke({"objective": objective, "focus": focus, "stages": []})
        stages = state.get("stages", [])
        attention_count = sum(1 for stage in stages if stage.status == "needs_attention")
        summary = (
            f"Scanned {state.get('doc_count', 0)} documents and "
            f"{state.get('chunk_count', 0)} chunks. "
            f"Average quality score is {round(state.get('quality_score', 0.0) * 100)}%."
        )
        if attention_count:
            summary += f" {attention_count} workflow stages need attention."
        else:
            summary += " The knowledge base is stable for the current checks."
        return AgentRunResponse(
            objective=objective,
            focus=focus,
            generated_at=datetime.now(timezone.utc),
            executive_summary=summary,
            stages=stages,
            recommended_backlog=state.get("recommended_backlog", []),
        )

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("observe_assets", self._observe_assets_node)
        workflow.add_node("diagnose_quality", self._diagnose_quality_node)
        workflow.add_node("diagnose_conflicts", self._diagnose_conflicts_node)
        workflow.add_node("probe_retrieval", self._probe_retrieval_node)
        workflow.add_node("plan_operations", self._plan_operations_node)
        workflow.set_entry_point("observe_assets")
        workflow.add_edge("observe_assets", "diagnose_quality")
        workflow.add_edge("diagnose_quality", "diagnose_conflicts")
        workflow.add_edge("diagnose_conflicts", "probe_retrieval")
        workflow.add_edge("probe_retrieval", "plan_operations")
        workflow.add_edge("plan_operations", END)
        return workflow.compile()

    def _observe_assets_node(self, state: AgentState) -> AgentState:
        docs = self.store.list_documents()
        chunks = self.store.list_chunks()
        report = self.ops.build_report()
        status = "completed" if docs and chunks else "needs_attention"
        stage = AgentStage(
            name="Asset inventory",
            status=status,
            observation=(
                f"Found {len(docs)} documents, {len(chunks)} chunks, "
                f"and an average quality score of {round(report.average_quality_score * 100)}%."
            ),
            evidence=[
                f"documents={len(docs)}",
                f"chunks={len(chunks)}",
                f"quality={report.average_quality_score}",
            ],
            next_actions=[] if status == "completed" else ["Import documents before running governance tasks."],
        )
        return {
            **state,
            "doc_count": len(docs),
            "chunk_count": len(chunks),
            "quality_score": report.average_quality_score,
            "report": report,
            "stages": [*state.get("stages", []), stage],
        }

    def _diagnose_quality_node(self, state: AgentState) -> AgentState:
        report = state["report"]
        low_quality = [issue for issue in report.issues if issue.kind == "low_quality"]
        stage = AgentStage(
            name="Quality diagnosis",
            status="needs_attention" if low_quality else "completed",
            observation=(
                f"Detected {len(low_quality)} low-quality document candidates."
                if low_quality
                else "No obvious low-quality document candidates were detected."
            ),
            evidence=[issue.title for issue in low_quality[:5]],
            next_actions=[
                "Add section headings, summary, source, and key takeaways.",
                "Merge tiny notes into topic pages.",
            ]
            if low_quality
            else ["Keep preserving section hierarchy and source metadata."],
        )
        return {**state, "stages": [*state.get("stages", []), stage]}

    def _diagnose_conflicts_node(self, state: AgentState) -> AgentState:
        report = state["report"]
        conflicts = [issue for issue in report.issues if issue.kind == "conflict_candidate"]
        stage = AgentStage(
            name="Conflict detection",
            status="needs_attention" if conflicts else "completed",
            observation=(
                f"Detected {len(conflicts)} potential knowledge conflicts."
                if conflicts
                else "No obvious version or semantic conflict candidates were detected."
            ),
            evidence=[issue.title for issue in conflicts[:5]],
            next_actions=[
                "Check publication dates and version metadata.",
                "Mark authoritative guidance as current and old guidance as deprecated.",
            ]
            if conflicts
            else ["Continue running conflict scans after new imports."],
        )
        return {**state, "stages": [*state.get("stages", []), stage]}

    def _probe_retrieval_node(self, state: AgentState) -> AgentState:
        docs = self.store.list_documents()
        if not docs:
            stage = AgentStage(
                name="Retrieval probe",
                status="needs_attention",
                observation="No documents are available for retrieval probing.",
                next_actions=["Import documents and rerun the retrieval probe."],
            )
            return {**state, "stages": [*state.get("stages", []), stage]}

        probe = docs[0].tags[0] if docs[0].tags else docs[0].title
        hits = self.retrieval.search(probe, "auto", 3)
        top_score = round(hits[0].score, 3) if hits else 0.0
        status = "completed" if top_score >= 0.2 else "needs_attention"
        stage = AgentStage(
            name="Retrieval probe",
            status=status,
            observation=f"Probe query '{probe}' returned a Top1 score of {top_score}.",
            evidence=[hit.document.title for hit in hits],
            next_actions=[
                "Add synonym tags and clearer section headings.",
                "Use the Eval workspace to build a retrieval benchmark.",
            ]
            if status == "needs_attention"
            else ["Keep the current Hybrid Search flow and expand benchmark queries."],
        )
        return {**state, "stages": [*state.get("stages", []), stage]}

    def _plan_operations_node(self, state: AgentState) -> AgentState:
        report = state["report"]
        focus = state.get("focus", "overview")
        high_issues = [issue for issue in report.issues if issue.severity == "high"]
        actions = [
            "Generate weekly reports for new, stale, conflicting, and low-quality knowledge.",
            "Generate FAQ and learning paths for high-frequency topics.",
            "Use topic coverage to find missing prerequisite concepts.",
        ]
        if focus == "conflict":
            actions.insert(0, "Prioritize conflict candidates and add authoritative version labels.")
        if focus == "retrieval":
            actions.insert(0, "Prioritize a retrieval benchmark with expected documents and chunks.")
        stage = AgentStage(
            name="Governance plan",
            status="needs_attention" if high_issues else "completed",
            observation=f"Found {len(high_issues)} high-severity issues and generated governance actions.",
            evidence=[issue.title for issue in high_issues[:5]],
            next_actions=actions,
        )
        return {
            **state,
            "stages": [*state.get("stages", []), stage],
            "recommended_backlog": self._backlog(report, focus),
        }

    def _backlog(self, report, focus: str) -> list[dict[str, str]]:
        backlog = [
            {
                "priority": "P0",
                "item": "Configure production MySQL metadata storage",
                "reason": "The project now uses a SQLAlchemy MySQL URL as the production store boundary.",
            },
            {
                "priority": "P0",
                "item": "Connect a real vector and keyword index",
                "reason": "Hybrid Search is interface-ready; Qdrant and Elasticsearch can replace local scoring.",
            },
            {
                "priority": "P1",
                "item": "Build retrieval benchmarks",
                "reason": "Track TopK hit rate, citation coverage, and answer faithfulness over fixed queries.",
            },
            {
                "priority": "P1",
                "item": "Upgrade conflict detection",
                "reason": "Move from heuristic candidates to entity clustering, claim extraction, and NLI checks.",
            },
        ]
        if report.issues:
            backlog.insert(
                0,
                {
                    "priority": "P0",
                    "item": "Resolve high-severity governance issues",
                    "reason": f"The latest report contains {len(report.issues)} issue candidates.",
                },
            )
        if focus == "growth":
            backlog.append(
                {
                    "priority": "P2",
                    "item": "Generate topic gap recommendations",
                    "reason": "Use the graph and topic coverage to discover isolated or missing concepts.",
                }
            )
        return backlog
