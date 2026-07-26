"""LLM provider package — swappable providers behind one interface.

To add a new provider, implement :class:`LanguageModelProvider` and register it
in ``llm/registry.py``. The pipeline only ever talks to the interface, so
providers can be swapped by changing ``BUILDERMC_LLM_PROVIDER`` in the env.

Available providers:
  * ``stub``   — deterministic, no network (default, for testing)
  * ``nvidia`` — real LLM via NVIDIA NIM, needs BUILDERMC_NVIDIA_API_KEY
"""
from __future__ import annotations

from .base import LanguageModelProvider, MalformedLLMOutputError
from .nvidia_nim_provider import NvidiaNimProvider
from .registry import PROVIDER_REGISTRY, get_provider
from .stub_provider import StubProvider

__all__ = [
    "LanguageModelProvider",
    "MalformedLLMOutputError",
    "NvidiaNimProvider",
    "PROVIDER_REGISTRY",
    "StubProvider",
    "get_provider",
]
