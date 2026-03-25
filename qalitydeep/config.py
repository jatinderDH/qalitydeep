from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_env: Literal["dev", "test", "prod"] = Field(
        default="dev", alias="APP_ENV"
    )
    data_dir: Path = Field(default=Path("./data"), alias="QALITYDEEP_DATA_DIR")

    llm_backend: Literal["openai", "ollama", "anthropic"] = Field(
        default="openai", alias="LLM_BACKEND"
    )

    # OpenAI / compatible
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    # Anthropic (Claude)
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", alias="ANTHROPIC_MODEL"
    )

    # Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="llama3.1", alias="OLLAMA_MODEL")

    # LangSmith
    langsmith_api_key: str | None = Field(
        default=None, alias="LANGSMITH_API_KEY"
    )
    langsmith_project: str | None = Field(
        default=None, alias="LANGSMITH_PROJECT"
    )

    # Remote eval API (optional)
    remote_eval_api_url: str | None = Field(
        default=None, alias="REMOTE_EVAL_API_URL"
    )
    remote_eval_api_key: str | None = Field(
        default=None, alias="REMOTE_EVAL_API_KEY"
    )
    remote_eval_collection: str = Field(
        default="qalitydeep-default", alias="REMOTE_EVAL_COLLECTION"
    )

    # Eval API (for playground - where to send requests)
    eval_api_url: str = Field(
        default="http://localhost:8000", alias="EVAL_API_URL"
    )

    class Config:
        populate_by_name = True

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "datasets").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "runs").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "sample").mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Do not auto‑load .env here; DeepEval already handles .env*.env.local
    env = {k: v for k, v in os.environ.items()}
    settings = Settings(**env)
    settings.ensure_dirs()
    return settings

