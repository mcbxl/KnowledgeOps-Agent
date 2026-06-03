from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", alias="KNOWLEDGEOPS_ENVIRONMENT")
    database_url: str = Field(
        default="mysql+pymysql://knowledgeops:knowledgeops@127.0.0.1:3306/knowledgeops?charset=utf8mb4",
        alias="KNOWLEDGEOPS_DATABASE_URL",
    )
    storage_dir: str = Field(default="./storage", alias="KNOWLEDGEOPS_STORAGE_DIR")
    allow_web_ingest: bool = Field(default=True, alias="KNOWLEDGEOPS_ALLOW_WEB_INGEST")
    allow_private_web_ingest: bool = Field(
        default=False,
        alias="KNOWLEDGEOPS_ALLOW_PRIVATE_WEB_INGEST",
    )
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, alias="KNOWLEDGEOPS_MAX_UPLOAD_BYTES")
    allowed_upload_extensions: str = Field(
        default="txt,md,markdown,pdf",
        alias="KNOWLEDGEOPS_ALLOWED_UPLOAD_EXTENSIONS",
    )
    llm_provider: str = Field(default="local", alias="KNOWLEDGEOPS_LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="KNOWLEDGEOPS_LLM_MODEL")
    embedding_provider: str = Field(default="local", alias="KNOWLEDGEOPS_EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="KNOWLEDGEOPS_EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=256, alias="KNOWLEDGEOPS_EMBEDDING_DIMENSIONS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    qdrant_url: str | None = Field(default=None, alias="KNOWLEDGEOPS_QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="KNOWLEDGEOPS_QDRANT_API_KEY")
    qdrant_collection: str = Field(
        default="knowledgeops_chunks",
        alias="KNOWLEDGEOPS_QDRANT_COLLECTION",
    )
    enable_qdrant: bool = Field(default=False, alias="KNOWLEDGEOPS_ENABLE_QDRANT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="KNOWLEDGEOPS_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def upload_extensions(self) -> set[str]:
        return {
            item.strip().lower().lstrip(".")
            for item in self.allowed_upload_extensions.split(",")
            if item.strip()
        }

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    return settings
