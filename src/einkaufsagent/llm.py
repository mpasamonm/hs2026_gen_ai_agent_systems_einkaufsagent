"""Chat-Modelle über den LiteLLM-Proxy (OpenAI-kompatible Chat-Completions-API)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from einkaufsagent.config import ModelConfig, litellm_settings


def build_chat_model(cfg: ModelConfig) -> ChatOpenAI:
    base_url, api_key = litellm_settings()
    kwargs: dict = {}
    if cfg.reasoning_effort is not None:
        kwargs["reasoning_effort"] = cfg.reasoning_effort
    if cfg.temperature is not None:
        kwargs["temperature"] = cfg.temperature
    return ChatOpenAI(
        model=cfg.id,
        base_url=base_url,
        api_key=api_key,
        timeout=90,
        max_retries=2,
        use_responses_api=False,  # LiteLLM-Proxy: einheitlich Chat Completions für alle Anbieter
        tags=[cfg.id],
        **kwargs,
    )
