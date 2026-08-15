"""No-op provider for when AI analysis is disabled."""

from __future__ import annotations

from app.services.ai.base import (
    AIAnalysisRequest,
    AIAnalysisResult,
    AIProviderNotConfiguredError,
    ProviderHealth,
)


class NoopProvider:
    """Returns errors when AI is disabled ('ai_provider=none')."""

    name: str = "noop"

    async def analyze_role(self, request: AIAnalysisRequest) -> AIAnalysisResult:
        raise AIProviderNotConfiguredError(
            "AI analysis is disabled (ai_provider=none)"
        )

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=True,
            provider=self.name,
            detail="AI provider is disabled",
        )
