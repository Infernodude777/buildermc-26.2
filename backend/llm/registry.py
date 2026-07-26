"""Provider registry — maps provider names to concrete LanguageModelProvider instances.

New providers are added in three steps:
  1. Implement ``LanguageModelProvider`` in a new module.
  2. Register the provider in ``PROVIDER_REGISTRY`` below.
  3. Expose the new name via ``BUILDERMC_LLM_PROVIDER``.

The registry is a plain mapping, which keeps the dependency graph explicit and
makes it trivial to test with a fake provider by passing the factory directly.
"""
from __future__ import annotations

from typing import Callable

from config.settings import Settings, settings

from models.requests import ProviderConfig

from .base import LanguageModelProvider
from .nvidia_nim_provider import OpenAiCompatibleProvider
from .stub_provider import StubProvider


ProviderFactory = Callable[[], LanguageModelProvider]


def _stub_factory() -> LanguageModelProvider:
    return StubProvider()


def _nvidia_factory() -> LanguageModelProvider:
    if not settings.nvidia_api_key:
        raise ValueError(
            "BUILDERMC_NVIDIA_API_KEY is not set. "
            "Add it to backend/.env or the environment to use the nvidia provider."
        )
    return OpenAiCompatibleProvider(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        model=settings.nvidia_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


# Public registry. Keys are the values accepted by BUILDERMC_LLM_PROVIDER.
PROVIDER_REGISTRY: dict[str, ProviderFactory] = {
    "stub": _stub_factory,
    "nvidia": _nvidia_factory,
}


def get_provider(name: str, _settings: Settings | None = None) -> LanguageModelProvider:
    """Return a provider instance by registered name.

    Args:
        name: Provider name (e.g. ``stub`` or ``nvidia``).
        _settings: Optional settings object for dependency injection in tests.

    Raises:
        ValueError: If the provider name is unknown or the provider cannot be
            constructed (e.g. missing API key).
    """
    name = (name or "stub").strip().lower()
    factory = PROVIDER_REGISTRY.get(name)
    if factory is None:
        available = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown llm_provider {name!r}. Available: {available}. "
            f"Set BUILDERMC_LLM_PROVIDER in the environment."
        )
    return factory()


def create_provider_from_config(config: ProviderConfig) -> LanguageModelProvider:
    """Create a per-request provider from the mod's /api config.

    This decouples the service layer from provider-specific construction details
    and keeps runtime provider switching behind a single factory function.
    Currently only OpenAI-compatible endpoints are supported, but the dispatch
    is extensible for future providers.
    """
    provider = (config.provider or "openai").strip().lower()
    if provider in ("openai", "nvidia"):
        # ``nvidia`` is kept as an alias for backward compatibility; the
        # underlying implementation is OpenAI-compatible and works with any
        # ``/chat/completions`` endpoint (NVIDIA NIM, OpenAI, Groq, etc.).
        return OpenAiCompatibleProvider(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_id,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    raise ValueError(f"Unsupported per-request provider: {config.provider!r}")
