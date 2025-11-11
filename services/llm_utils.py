from __future__ import annotations

import logging
import os
from typing import List, Tuple

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

try:
    from langchain_community.chat_models import ChatOllama  # type: ignore
except ImportError:  # pragma: no cover
    ChatOllama = None  # type: ignore


def get_llm_candidates(
    *,
    temperature: float = 0.7,
    prefer_order: Tuple[str, ...] | List[str] | None = None,
    openai_model: str = "gpt-3.5-turbo",
) -> List[Tuple[str, object]]:
    """
    Build a list of available LLM chat models in preference order.

    Returns a list of tuples: (provider_name, llm_instance)
    Supported provider names: "openai", "ollama"
    """

    if prefer_order is None:
        prefer_order = ("openai", "ollama")

    # Normalize to list and keep order without duplicates
    ordered_providers = []
    for provider in prefer_order:
        lower = provider.lower()
        if lower not in ordered_providers:
            ordered_providers.append(lower)
    for provider in ("openai", "ollama"):
        if provider not in ordered_providers:
            ordered_providers.append(provider)

    candidates: List[Tuple[str, object]] = []

    for provider in ordered_providers:
        if provider == "openai":
            openai_key = os.getenv("OPENAI_API_KEY", "")
            if openai_key:
                try:
                    llm = ChatOpenAI(
                        model=openai_model,
                        temperature=temperature,
                        api_key=openai_key,
                    )
                    candidates.append(("openai", llm))
                except Exception as e:
                    logger.debug(f"Failed to initialize OpenAI LLM: {e}")
                    continue

        elif provider == "ollama":
            if ChatOllama:
                ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
                base_url = os.getenv("OLLAMA_BASE_URL")
                try:
                    if base_url:
                        llm = ChatOllama(
                            model=ollama_model,
                            temperature=temperature,
                            base_url=base_url,
                        )
                    else:
                        llm = ChatOllama(
                            model=ollama_model,
                            temperature=temperature,
                        )
                    candidates.append(("ollama", llm))
                except Exception as e:
                    logger.debug(f"Failed to initialize Ollama LLM: {e}")
                    continue

    return candidates
