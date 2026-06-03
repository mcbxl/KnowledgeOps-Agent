from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import get_settings
from app.main import app
from app.services.storage import KnowledgeStore


def test_request_id_header_is_added():
    client = TestClient(app)

    response = client.get("/api/health", headers={"X-Request-ID": "req-test-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-1"


def test_api_key_protects_non_public_routes(tmp_path):
    store = KnowledgeStore(f"sqlite:///{tmp_path / 'knowledgeops-auth.db'}")
    app.dependency_overrides[routes.get_store] = lambda: store
    settings = get_settings()
    previous_key = settings.api_key
    settings.api_key = "secret-test-key"
    client = TestClient(app)

    try:
        health = client.get("/api/health")
        assert health.status_code == 200

        rejected = client.get("/api/documents")
        assert rejected.status_code == 401
        assert rejected.headers["X-Request-ID"]

        accepted = client.get("/api/documents", headers={"X-API-Key": "secret-test-key"})
        assert accepted.status_code != 401
    finally:
        settings.api_key = previous_key
        app.dependency_overrides.clear()
