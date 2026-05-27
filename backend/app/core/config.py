from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: Path = Field(default=Path("./knowledgeops.db"), alias="KNOWLEDGEOPS_DB_PATH")
    storage_dir: Path = Field(default=Path("./storage"), alias="KNOWLEDGEOPS_STORAGE_DIR")
    allow_web_ingest: bool = Field(default=True, alias="KNOWLEDGEOPS_ALLOW_WEB_INGEST")
    llm_provider: str = Field(default="local", alias="KNOWLEDGEOPS_LLM_PROVIDER")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings

