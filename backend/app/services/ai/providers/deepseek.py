"""DeepSeek provider implementation.

Uses the DeepSeek Chat API (OpenAI-compatible) with structured JSON output.
Provider-independent: the rest of the codebase never references this module.
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

logger = get_logger("ai.providers.deepseek")

# DeepSeek-specific request fields (not part of the provider-independent protocol)
_JSON_RESPONSE_FORMAT = {"type": "json_object"}


class DeepSeekProvider:
    """Concrete provider for the DeepSeek Chat API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        timeout: int = 60,
        temperature: float = 0.3,
    ) -> None:
        self.name = "deepseek"
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
            "response_format": _JSON_RESPONSE_FORMAT,
            "temperature": self._temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error("DeepSeek request timed out: %s", exc)
            raise AIProviderTimeoutError() from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "DeepSeek returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise AIProviderUnavailableError(
                f"DeepSeek returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("DeepSeek request failed: %s", exc)
            raise AIProviderUnavailableError(str(exc)) from exc

        # Parse response
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            logger.error("Failed to parse DeepSeek response structure: %s", exc)
            raise AIOutputValidationError("Malformed provider response") from exc

        # Validate against Pydantic schema
        try:
            result = parse_analysis_result(content)
        except Exception as exc:
            logger.error("AI output failed Pydantic validation: %s", exc)
            raise AIOutputValidationError(
                f"AI output schema validation failed: {exc}"
            ) from exc

        return result

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/v1/models",
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
