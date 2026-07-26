"""Application settings loaded from environment / .env with safe defaults.

Settings are intentionally minimal — the mod's world context and prompt drive
generation, not config. Add a new provider by extending ``llm_provider`` and
wiring it in ``llm/__init__.py``.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BUILDERMC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Where generated .schem files are written (relative to backend/).
    output_dir: Path = Path("generated")

    # Filename used for the latest schematic (Java side checks for this).
    latest_filename: str = "latest.schem"

    # mcschematic version to target (Sponge .schem). JE_1_18_2 is confirmed to
    # exist in mcschematic>=1.3.0 and produces a broadly-compatible .schem.
    schematic_version: str = "JE_1_18_2"

    # Which LLM provider to use: "stub" (deterministic, no network) or "openai"
    # (pluggable — see llm/base.py). Default to stub so the whole pipeline is
    # testable without API keys.
    llm_provider: str = "stub"

    # Maximum accepted structure size to guard against runaway LLM output.
    max_dimension: int = 64

    # API keys for real providers (read from env, never committed).
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # NVIDIA NIM provider (OpenAI-compatible endpoint for glm-5.2 etc.)
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "z-ai/glm-5.2"

    # Shared LLM generation parameters.
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    @property
    def latest_schematic_path(self) -> Path:
        return self.output_dir / self.latest_filename


settings = Settings()
