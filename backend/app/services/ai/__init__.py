"""AI provider package.

``get_provider`` returns the concrete provider configured via
``Settings.ai_provider``. Business logic must use this factory
rather than importing a specific provider directly.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.ai.base import AIProvider, AIProviderNotConfiguredError
from app.services.ai.providers.noop import NoopProvider

logger = get_logger("ai")


def get_provider(settings: Settings) -> AIProvider:
    """Return the configured AI provider instance.

    Raises ``AIProviderNotConfiguredError`` when the provider name is
    unknown or its required credentials are missing.
    """
    name = settings.ai_provider.strip().lower()

    if name in ("none", ""):
        return NoopProvider()

    if name == "deepseek":
        if not settings.ai_api_key:
            raise AIProviderNotConfiguredError(
                "DeepSeek provider requires ai_api_key (DEEPSEEK_API_KEY)"
            )
        from app.services.ai.providers.deepseek import DeepSeekProvider

        return DeepSeekProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            base_url=settings.ai_api_base_url,
            timeout=settings.ai_timeout_seconds,
            temperature=settings.ai_temperature,
        )

    if name == "ollama_cloud":
        if not settings.ollama_api_key:
            raise AIProviderNotConfiguredError(
                "Ollama Cloud provider requires ollama_api_key (OLLAMA_API_KEY)"
            )
        from app.services.ai.providers.ollama_cloud import OllamaCloudProvider

        return OllamaCloudProvider(
            api_key=settings.ollama_api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
            temperature=settings.ai_temperature,
        )

    raise AIProviderNotConfiguredError(f"Unknown AI provider: {name!r}")
