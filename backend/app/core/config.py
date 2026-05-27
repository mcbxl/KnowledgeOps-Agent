from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="mysql+pymysql://knowledgeops:knowledgeops@127.0.0.1:3306/knowledgeops?charset=utf8mb4",
        alias="KNOWLEDGEOPS_DATABASE_URL",
    )
    storage_dir: str = Field(default="./storage", alias="KNOWLEDGEOPS_STORAGE_DIR")
    allow_web_ingest: bool = Field(default=True, alias="KNOWLEDGEOPS_ALLOW_WEB_INGEST")
    llm_provider: str = Field(default="local", alias="KNOWLEDGEOPS_LLM_PROVIDER")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    return settings
