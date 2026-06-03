from __future__ import annotations

from datetime import datetime, timezone
from importlib.util import find_spec

from sqlalchemy import text

from app.core.config import Settings
from app.schemas.api import RuntimeComponent, RuntimeStatusResponse
from app.services.storage import KnowledgeStore


class RuntimeStatusService:
    def __init__(self, settings: Settings, store: KnowledgeStore) -> None:
        self.settings = settings
        self.store = store

    def build_status(self) -> RuntimeStatusResponse:
        components = [
            self._database_component(),
            self._embedding_component(),
            self._llm_component(),
            self._vector_component(),
            self._security_component(),
        ]
        order = {"ok": 0, "degraded": 1, "action_required": 2}
        overall = max((component.status for component in components), key=lambda item: order[item])
        recommendations = self._recommendations(components)
        return RuntimeStatusResponse(
            generated_at=datetime.now(timezone.utc),
            environment=self.settings.environment,
            status=overall,
            components=components,
            recommendations=recommendations,
        )

    def _database_component(self) -> RuntimeComponent:
        try:
            with self.store.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            return RuntimeComponent(
                name="Metadata Store",
                status="action_required",
                provider=self._database_provider(),
                detail=f"Database connectivity failed: {exc}",
                checks=["SQLAlchemy engine", "SELECT 1"],
            )
        return RuntimeComponent(
            name="Metadata Store",
            status="ok",
            provider=self._database_provider(),
            detail="Database connection is healthy.",
            checks=["SQLAlchemy engine", "documents/chunks/tasks metadata"],
        )

    def _embedding_component(self) -> RuntimeComponent:
        provider = self.settings.embedding_provider.lower()
        if provider in {"openai", "langchain_openai"}:
            missing = []
            if not self.settings.openai_api_key:
                missing.append("OPENAI_API_KEY")
            if find_spec("langchain_openai") is None:
                missing.append("langchain-openai package")
            if missing:
                return RuntimeComponent(
                    name="Embedding Model",
                    status="action_required",
                    provider=self.settings.embedding_model,
                    detail=f"OpenAI embeddings are configured but missing: {', '.join(missing)}.",
                    checks=["LangChain OpenAIEmbeddings", "API key"],
                )
            return RuntimeComponent(
                name="Embedding Model",
                status="ok",
                provider=self.settings.embedding_model,
                detail="LangChain OpenAIEmbeddings is ready.",
                checks=["LangChain OpenAIEmbeddings", f"dimensions={self.settings.embedding_dimensions}"],
            )
        return RuntimeComponent(
            name="Embedding Model",
            status="degraded",
            provider="local deterministic",
            detail="Using deterministic local embeddings for development and tests.",
            checks=[f"dimensions={self.settings.embedding_dimensions}", "no external API key required"],
        )

    def _llm_component(self) -> RuntimeComponent:
        provider = self.settings.llm_provider.lower()
        if provider in {"openai", "langchain_openai"}:
            missing = []
            if not self.settings.openai_api_key:
                missing.append("OPENAI_API_KEY")
            if find_spec("langchain_openai") is None:
                missing.append("langchain-openai package")
            if missing:
                return RuntimeComponent(
                    name="Answer Generator",
                    status="action_required",
                    provider=self.settings.llm_model,
                    detail=f"OpenAI answer generation is configured but missing: {', '.join(missing)}.",
                    checks=["LangChain ChatOpenAI", "grounded prompt", "API key"],
                )
            return RuntimeComponent(
                name="Answer Generator",
                status="ok",
                provider=self.settings.llm_model,
                detail="LangChain ChatOpenAI grounded generation is ready.",
                checks=["LangChain ChatOpenAI", "citation-grounded prompt"],
            )
        return RuntimeComponent(
            name="Answer Generator",
            status="degraded",
            provider="local citation generator",
            detail="Using local grounded answer fallback instead of an external LLM.",
            checks=["deterministic output", "citations retained"],
        )

    def _vector_component(self) -> RuntimeComponent:
        if not self.settings.enable_qdrant:
            return RuntimeComponent(
                name="Vector Index",
                status="degraded",
                provider="local JSON embedding scan",
                detail="Qdrant is disabled; retrieval falls back to stored embeddings and cosine scoring.",
                checks=["hybrid retrieval fallback", "no external vector DB required"],
            )
        missing = []
        if not self.settings.qdrant_url:
            missing.append("KNOWLEDGEOPS_QDRANT_URL")
        if find_spec("qdrant_client") is None:
            missing.append("qdrant-client package")
        if missing:
            return RuntimeComponent(
                name="Vector Index",
                status="action_required",
                provider="Qdrant",
                detail=f"Qdrant is enabled but missing: {', '.join(missing)}.",
                checks=["Qdrant client", self.settings.qdrant_collection],
            )
        return RuntimeComponent(
            name="Vector Index",
            status="ok",
            provider="Qdrant",
            detail="Qdrant client dependency and configuration are present.",
            checks=[self.settings.qdrant_url or "", self.settings.qdrant_collection],
        )

    def _security_component(self) -> RuntimeComponent:
        checks = [
            f"api_key={'enabled' if self.settings.api_key else 'disabled'}",
            f"web_ingest={'enabled' if self.settings.allow_web_ingest else 'disabled'}",
            f"private_web_ingest={'enabled' if self.settings.allow_private_web_ingest else 'blocked'}",
            f"max_upload_bytes={self.settings.max_upload_bytes}",
            f"extensions={','.join(sorted(self.settings.upload_extensions))}",
            f"cors_origins={len(self.settings.parsed_cors_origins)}",
        ]
        if self.settings.allow_private_web_ingest:
            return RuntimeComponent(
                name="Security Guardrails",
                status="action_required",
                provider="FastAPI validation",
                detail="Private web ingestion is enabled; disable it for production to reduce SSRF risk.",
                checks=checks,
            )
        if not self.settings.api_key and self.settings.environment.lower() == "production":
            return RuntimeComponent(
                name="Security Guardrails",
                status="action_required",
                provider="FastAPI middleware",
                detail="Production environment should configure KNOWLEDGEOPS_API_KEY.",
                checks=checks,
            )
        return RuntimeComponent(
            name="Security Guardrails",
            status="ok",
            provider="FastAPI middleware",
            detail="SSRF-sensitive targets are blocked, uploads are constrained, and API key state is explicit.",
            checks=checks,
        )

    def _recommendations(self, components: list[RuntimeComponent]) -> list[str]:
        recommendations = []
        if any(component.status == "action_required" for component in components):
            recommendations.append("Resolve action_required components before production deployment.")
        if self.settings.embedding_provider.lower() == "local":
            recommendations.append("Set KNOWLEDGEOPS_EMBEDDING_PROVIDER=openai for real semantic embeddings.")
        if self.settings.llm_provider.lower() == "local":
            recommendations.append("Set KNOWLEDGEOPS_LLM_PROVIDER=openai for real grounded answer generation.")
        if not self.settings.enable_qdrant:
            recommendations.append("Enable Qdrant to move vector search out of metadata storage.")
        if not recommendations:
            recommendations.append("Runtime is ready for the configured environment.")
        return recommendations

    def _database_provider(self) -> str:
        if self.settings.database_url.startswith("sqlite"):
            return "SQLite"
        if self.settings.database_url.startswith("mysql"):
            return "MySQL"
        return "SQLAlchemy"
