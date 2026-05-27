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
        try:
            report = KnowledgeOpsService(self.store).build_report()
            self.store.update_task(
                task_id,
                "completed",
                result={
                    "document_count": report.document_count,
                    "chunk_count": report.chunk_count,
                    "issue_count": len(report.issues),
                    "topic_count": len(report.topic_coverage),
                    "quality_score": report.average_quality_score,
                    "generated_at": report.generated_at.isoformat(),
                },
            )
        except Exception as exc:
            self.store.update_task(task_id, "failed", error=str(exc))

