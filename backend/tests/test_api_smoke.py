from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services.storage import KnowledgeStore


def test_ingest_search_ask_agent_and_eval(tmp_path):
    store = KnowledgeStore(f"sqlite:///{tmp_path / 'knowledgeops-test.db'}")
    app.dependency_overrides[routes.get_store] = lambda: store
    client = TestClient(app)

    try:
        ingest = client.post(
            "/api/documents/text",
            json={
                "title": "React 18 Migration",
                "content": (
                    "# React 18\n\n"
                    "React 18 recommends createRoot for new roots.\n\n"
                    "## Legacy\n\n"
                    "ReactDOM.render is legacy guidance."
                ),
                "source_type": "markdown",
                "tags": ["react"],
            },
        )
        assert ingest.status_code == 200
        document_id = ingest.json()["id"]
        assert ingest.json()["chunk_count"] >= 1

        detail = client.get(f"/api/documents/{document_id}")
        assert detail.status_code == 200
        assert detail.json()["chunks"][0]["embedding_dimensions"] > 0
        assert detail.json()["chunks"][0]["token_count"] > 0

        search = client.post(
            "/api/search",
            json={"query": "React createRoot", "intent": "auto", "limit": 3},
        )
        assert search.status_code == 200
        assert len(search.json()) >= 1

        ask = client.post(
            "/api/ask",
            json={
                "query": "React 18 should use what API?",
                "intent": "auto",
                "limit": 3,
                "answer_mode": "knowledge_only",
            },
        )
        assert ask.status_code == 200
        assert ask.json()["citations"]
        assert ask.json()["grounding"]["citation_count"] >= 1

        agent = client.post(
            "/api/agent/run",
            json={"objective": "Diagnose the knowledge base", "focus": "overview"},
        )
        assert agent.status_code == 200
        assert len(agent.json()["stages"]) >= 4

        evaluation = client.post(
            "/api/eval/retrieval",
            json={"queries": ["React createRoot"], "limit": 3},
        )
        assert evaluation.status_code == 200
        assert evaluation.json()["cases"][0]["hit_count"] >= 1

        benchmark = client.post(
            "/api/eval/benchmarks",
            json={
                "name": "React retrieval baseline",
                "limit": 3,
                "cases": [
                    {
                        "query": "React createRoot",
                        "expected_document_id": document_id,
                    }
                ],
            },
        )
        assert benchmark.status_code == 200
        benchmark_id = benchmark.json()["id"]

        benchmarks = client.get("/api/eval/benchmarks")
        assert benchmarks.status_code == 200
        assert len(benchmarks.json()) >= 1

        benchmark_run = client.post(f"/api/eval/benchmarks/{benchmark_id}/run")
        assert benchmark_run.status_code == 200
        assert benchmark_run.json()["benchmark_id"] == benchmark_id
        assert benchmark_run.json()["expected_hit_rate"] == 1.0

        task = client.post("/api/tasks/ops-report")
        assert task.status_code == 200
        assert task.json()["status"] in {"queued", "completed"}
        task_id = task.json()["id"]

        tasks = client.get("/api/tasks")
        assert tasks.status_code == 200
        assert len(tasks.json()) >= 1

        events = client.get(f"/api/tasks/{task_id}/events")
        assert events.status_code == 200
        event_types = {event["event_type"] for event in events.json()}
        assert "queued" in event_types
        assert event_types & {"completed", "started"}
    finally:
        app.dependency_overrides.clear()
