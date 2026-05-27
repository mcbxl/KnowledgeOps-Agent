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

        task = client.post("/api/tasks/ops-report")
        assert task.status_code == 200
        assert task.json()["status"] in {"queued", "completed"}

        tasks = client.get("/api/tasks")
        assert tasks.status_code == 200
        assert len(tasks.json()) >= 1
    finally:
        app.dependency_overrides.clear()
