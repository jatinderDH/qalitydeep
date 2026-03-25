from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from .config import get_settings


def get_chat_model(**overrides: Any) -> BaseChatModel:
    """
    Return a LangChain chat model configured from env.

    Supports:
    - OpenAI via `langchain_openai.ChatOpenAI`
    - Anthropic (Claude) via `langchain_anthropic.ChatAnthropic`
    - Ollama via `langchain_community.chat_models.ChatOllama`
    """
    settings = get_settings()
    backend = overrides.pop("backend", settings.llm_backend)

    if backend == "openai":
        from langchain_openai import ChatOpenAI

        model = overrides.pop("model", settings.openai_model)
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=overrides.pop("temperature", 0.1),
            **overrides,
        )

    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model = overrides.pop("model", settings.anthropic_model)
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=overrides.pop("temperature", 0.1),
            **overrides,
        )

    if backend == "ollama":
        from langchain_community.chat_models import ChatOllama

        model = overrides.pop("model", settings.ollama_model)
        return ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=overrides.pop("temperature", 0.1),
            **overrides,
        )

    raise ValueError(f"Unsupported LLM_BACKEND: {backend}")

