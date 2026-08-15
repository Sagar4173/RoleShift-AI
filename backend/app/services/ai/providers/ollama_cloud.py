"""Ollama Cloud provider implementation.

Uses the Ollama Cloud HTTPS API (https://ollama.com) directly with an
Ollama Cloud API key. Structured JSON output is requested via the
``format: "json"`` field, then validated against the shared
``AIAnalysisResult`` Pydantic schema.

The API key is provided via configuration (``OLLAMA_API_KEY`` in
``backend/.env``) and is never logged or exposed.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.services.ai.base import (
    AIAnalysisRequest,
    AIAnalysisResult,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIOutputValidationError,
    ProviderHealth,
    parse_analysis_result,
)
from app.services.ai.prompt import build_analysis_prompt

logger = get_logger("ai.providers.ollama_cloud")

# Ollama Cloud API base (direct HTTPS, no local install required).
OLLAMA_CLOUD_BASE_URL = "https://ollama.com"

# Request field requesting structured JSON output from the model.
_JSON_FORMAT = "json"


class OllamaCloudProvider:
    """Concrete provider for the Ollama Cloud API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = OLLAMA_CLOUD_BASE_URL,
        timeout: int = 60,
        temperature: float = 0.3,
    ) -> None:
        self.name = "ollama_cloud"
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._temperature = temperature

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def analyze_role(self, request: AIAnalysisRequest) -> AIAnalysisResult:
        prompt = build_analysis_prompt(request)
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": _JSON_FORMAT,
            "options": {"temperature": self._temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error("Ollama Cloud request timed out: %s", exc)
            raise AIProviderTimeoutError() from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama Cloud returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise AIProviderUnavailableError(
                f"Ollama Cloud returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Ollama Cloud request failed: %s", exc)
            raise AIProviderUnavailableError(str(exc)) from exc

        # Parse response envelope: {"message": {"role", "content"}, ...}
        try:
            body = response.json()
            content = body["message"]["content"]
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse Ollama Cloud response structure: %s", exc)
            raise AIOutputValidationError("Malformed provider response") from exc

        # Validate the structured content against the Pydantic schema
        try:
            result = parse_analysis_result(content)
        except Exception as exc:
            logger.error("AI output failed Pydantic validation: %s", exc)
            raise AIOutputValidationError(
                f"AI output schema validation failed: {exc}"
            ) from exc

        return result

    async def health_check(self) -> ProviderHealth:
        """Verify the API key is accepted by listing available cloud models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/api/tags",
                    headers=self._headers(),
                )
                healthy = response.status_code == 200
                latency_ms = int(response.elapsed.total_seconds() * 1000)
                return ProviderHealth(
                    healthy=healthy,
                    provider=self.name,
                    latency_ms=latency_ms,
                    detail=None if healthy else f"HTTP {response.status_code}",
                )
        except Exception as exc:
            return ProviderHealth(
                healthy=False,
                provider=self.name,
                detail=str(exc)[:200],
            )
