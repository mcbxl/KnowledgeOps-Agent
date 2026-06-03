from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import Settings
from app.main import app
from app.services.runtime import RuntimeStatusService
from app.services.storage import KnowledgeStore


def test_runtime_status_endpoint_reports_local_fallbacks(tmp_path):
    store = KnowledgeStore(f"sqlite:///{tmp_path / 'knowledgeops-runtime.db'}")
    app.dependency_overrides[routes.get_store] = lambda: store
    client = TestClient(app)

    try:
        response = client.get("/api/runtime/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["environment"] == "development"
        assert {component["name"] for component in payload["components"]} >= {
            "Metadata Store",
            "Embedding Model",
            "Answer Generator",
            "Vector Index",
            "Security Guardrails",
        }
    finally:
        app.dependency_overrides.clear()


def test_runtime_status_flags_missing_production_dependencies(tmp_path):
    store = KnowledgeStore(f"sqlite:///{tmp_path / 'knowledgeops-runtime.db'}")
    settings = Settings(
        KNOWLEDGEOPS_EMBEDDING_PROVIDER="openai",
        KNOWLEDGEOPS_LLM_PROVIDER="openai",
        KNOWLEDGEOPS_ENABLE_QDRANT=True,
        KNOWLEDGEOPS_QDRANT_URL="http://127.0.0.1:6333",
        KNOWLEDGEOPS_ALLOW_PRIVATE_WEB_INGEST=True,
        OPENAI_API_KEY="",
    )

    status = RuntimeStatusService(settings, store).build_status()

    assert status.status == "action_required"
    components = {component.name: component for component in status.components}
    assert components["Embedding Model"].status == "action_required"
    assert components["Answer Generator"].status == "action_required"
    assert components["Security Guardrails"].status == "action_required"
