from __future__ import annotations

from app.services.ops import KnowledgeOpsService
from app.services.storage import KnowledgeStore


class TaskService:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store

    def create_ops_report_task(self) -> dict:
        return self.store.create_task(
            task_type="ops_report",
            title="Generate KnowledgeOps report",
            payload={"runner": "local-background"},
        )

    def run_ops_report_task(self, task_id: str) -> None:
        self.store.update_task(task_id, "running")
        self.store.add_task_event(
            task_id,
            "started",
            "Started KnowledgeOps report generation.",
            {"runner": "fastapi-background-task"},
        )
        try:
            report = KnowledgeOpsService(self.store).build_report()
            result = {
                "document_count": report.document_count,
                "chunk_count": report.chunk_count,
                "issue_count": len(report.issues),
                "topic_count": len(report.topic_coverage),
                "quality_score": report.average_quality_score,
                "generated_at": report.generated_at.isoformat(),
            }
            self.store.update_task(
                task_id,
                "completed",
                result=result,
            )
            self.store.add_task_event(
                task_id,
                "completed",
                "KnowledgeOps report generated successfully.",
                result,
            )
        except Exception as exc:
            self.store.update_task(task_id, "failed", error=str(exc))
            self.store.add_task_event(
                task_id,
                "failed",
                "KnowledgeOps report generation failed.",
                {"error": str(exc)},
            )
