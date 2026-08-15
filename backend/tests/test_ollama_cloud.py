"""Tests for the Ollama Cloud provider.

All provider HTTP calls are mocked -- no network or API usage.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.ai import get_provider
from app.services.ai.base import (
    AIAnalysisRequest,
    AIAnalysisResult,
    AIProviderNotConfiguredError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIOutputValidationError,
)
from app.services.ai.providers.ollama_cloud import (
    OLLAMA_CLOUD_BASE_URL,
    OllamaCloudProvider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_RESULT = AIAnalysisResult(
    ai_exposure_score=0.72,
    ai_exposure_summary="The Data Analyst role has significant AI exposure.",
    automation_score=0.65,
    augmentation_score=0.80,
    reskilling_priority="high",
)


def _make_request() -> AIAnalysisRequest:
    return AIAnalysisRequest(
        role_id="r1",
        role_name="Data Analyst",
        role_description="Analyses business data",
        industry="Finance",
    )


def _make_provider(**overrides: Any) -> OllamaCloudProvider:
    kwargs: dict[str, Any] = {
        "api_key": "test-ollama-key",
        "model": "deepseek-v4-flash:cloud",
        "timeout": 60,
        "temperature": 0.3,
    }
    kwargs.update(overrides)
    return OllamaCloudProvider(**kwargs)


def _mock_chat_response(content: str, status_code: int = 200) -> MagicMock:
    """A mocked httpx response shaped like the Ollama Cloud chat response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "model": "deepseek-v4-flash:cloud",
        "message": {"role": "assistant", "content": content},
        "done": True,
    }
    return resp


def _patched_client(mock_method: AsyncMock) -> MagicMock:
    """A mocked httpx.AsyncClient whose __aexit__ does not suppress errors."""
    mock_client = MagicMock()
    inner = MagicMock()
    inner.post = mock_method
    inner.get = mock_method
    mock_client.__aenter__.return_value = inner
    mock_client.__aexit__.return_value = False
    return mock_client


# ---------------------------------------------------------------------------
# Unit tests: request construction
# ---------------------------------------------------------------------------


class TestOllamaCloudRequest:
    async def test_sends_expected_payload(self):
        """Verify the /api/chat payload requests structured JSON."""
        provider = _make_provider()
        resp = _mock_chat_response(VALID_RESULT.model_dump_json())

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            await provider.analyze_role(_make_request())

        args, kwargs = mock_post.call_args
        assert args[0] == f"{OLLAMA_CLOUD_BASE_URL}/api/chat"
        assert kwargs["headers"]["Authorization"] == "Bearer test-ollama-key"
        assert kwargs["json"]["model"] == "deepseek-v4-flash:cloud"
        assert kwargs["json"]["stream"] is False
        assert kwargs["json"]["format"] == "json"
        assert kwargs["json"]["messages"][0]["role"] == "user"
        assert "Data Analyst" in kwargs["json"]["messages"][0]["content"]
        assert kwargs["json"]["options"]["temperature"] == 0.3

    async def test_custom_base_url_used(self):
        """A custom base_url overrides the default."""
        provider = _make_provider(base_url="https://example.com")
        resp = _mock_chat_response(VALID_RESULT.model_dump_json())

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            await provider.analyze_role(_make_request())

        args, _ = mock_post.call_args
        assert args[0] == "https://example.com/api/chat"

    async def test_never_logs_api_key(self, caplog):
        """The request builder keeps the key in the header only."""
        import logging

        provider = _make_provider()
        resp = _mock_chat_response(VALID_RESULT.model_dump_json())
        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            await provider.analyze_role(_make_request())

        captured = caplog.get_records("call")
        assert all("test-ollama-key" not in r.getMessage() for r in captured)


# ---------------------------------------------------------------------------
# Unit tests: response parsing & validation
# ---------------------------------------------------------------------------


class TestOllamaCloudParsing:
    async def test_valid_structured_json_parsed(self):
        """message.content JSON string is validated into AIAnalysisResult."""
        provider = _make_provider()
        resp = _mock_chat_response(VALID_RESULT.model_dump_json())

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            result = await provider.analyze_role(_make_request())

        assert isinstance(result, AIAnalysisResult)
        assert result.ai_exposure_score == 0.72
        assert result.reskilling_priority == "high"

    async def test_markdown_fenced_json_parsed(self):
        """JSON wrapped in ```json fences is accepted (real provider behaviour)."""
        provider = _make_provider()
        fenced = "```json\n" + VALID_RESULT.model_dump_json() + "\n```"
        resp = _mock_chat_response(fenced)

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            result = await provider.analyze_role(_make_request())

        assert isinstance(result, AIAnalysisResult)
        assert result.ai_exposure_score == 0.72

    async def test_prose_wrapped_json_parsed(self):
        """JSON embedded in surrounding prose is still extracted."""
        provider = _make_provider()
        wrapped = "Here is the analysis:\n" + VALID_RESULT.model_dump_json() + "\nHope that helps."
        resp = _mock_chat_response(wrapped)

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            result = await provider.analyze_role(_make_request())

        assert isinstance(result, AIAnalysisResult)
        assert result.ai_exposure_score == 0.72

    async def test_missing_content_raises_validation_error(self):
        """Envelope without message.content -> AIOutputValidationError."""
        provider = _make_provider()
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"model": "deepseek-v4-flash:cloud", "done": True}

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            with pytest.raises(AIOutputValidationError):
                await provider.analyze_role(_make_request())

    async def test_invalid_json_content_raises_validation_error(self):
        """Non-JSON content -> AIOutputValidationError."""
        provider = _make_provider()
        resp = _mock_chat_response("not json at all")

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            with pytest.raises(AIOutputValidationError):
                await provider.analyze_role(_make_request())

    async def test_schema_mismatch_raises_validation_error(self):
        """Valid JSON that fails the AIAnalysisResult schema -> validation error."""
        provider = _make_provider()
        resp = _mock_chat_response('{"unexpected": "shape", "score": "high"}')

        mock_post = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            with pytest.raises(AIOutputValidationError):
                await provider.analyze_role(_make_request())


# ---------------------------------------------------------------------------
# Unit tests: error mapping
# ---------------------------------------------------------------------------


class TestOllamaCloudErrors:
    async def test_timeout_raises_timeout_error(self):
        provider = _make_provider()

        mock_post = AsyncMock(side_effect=httpx.TimeoutException("request timed out"))

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            with pytest.raises(AIProviderTimeoutError):
                await provider.analyze_role(_make_request())

    async def test_http_error_raises_unavailable(self):
        provider = _make_provider()

        request = httpx.Request("POST", "https://ollama.com/api/chat")
        response = httpx.Response(401, request=request, text="unauthorized")
        http_error = httpx.HTTPStatusError(
            "401 Unauthorized", request=request, response=response
        )
        mock_post = AsyncMock(side_effect=http_error)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            with pytest.raises(AIProviderUnavailableError):
                await provider.analyze_role(_make_request())

    async def test_connection_error_raises_unavailable(self):
        provider = _make_provider()

        request = httpx.Request("POST", "https://ollama.com/api/chat")
        conn_error = httpx.ConnectError("connection refused", request=request)
        mock_post = AsyncMock(side_effect=conn_error)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_post)):
            with pytest.raises(AIProviderUnavailableError):
                await provider.analyze_role(_make_request())

    async def test_health_check_healthy(self):
        provider = _make_provider()
        resp = MagicMock()
        resp.status_code = 200
        resp.elapsed.total_seconds.return_value = 0.5

        mock_get = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_get)):
            health = await provider.health_check()

        assert health.healthy is True
        assert health.provider == "ollama_cloud"
        assert health.latency_ms == 500

    async def test_health_check_unhealthy(self):
        provider = _make_provider()
        resp = MagicMock()
        resp.status_code = 401

        mock_get = AsyncMock(return_value=resp)

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_get)):
            health = await provider.health_check()

        assert health.healthy is False
        assert health.detail == "HTTP 401"

    async def test_health_check_exception_reports_unhealthy(self):
        provider = _make_provider()
        mock_get = AsyncMock(side_effect=httpx.ConnectError(
            "refused", request=httpx.Request("GET", "https://ollama.com/api/tags")
        ))

        with patch("httpx.AsyncClient", return_value=_patched_client(mock_get)):
            health = await provider.health_check()

        assert health.healthy is False
        assert health.detail is not None


# ---------------------------------------------------------------------------
# Factory wiring tests
# ---------------------------------------------------------------------------


class TestOllamaCloudFactory:
    def test_factory_returns_ollama_cloud_provider(self):
        settings = Settings(
            app_env="test",
            log_level="WARNING",
            ai_provider="ollama_cloud",
            ollama_api_key="test-key-not-real",
            ai_model="deepseek-v4-flash:cloud",
        )
        provider = get_provider(settings)
        assert isinstance(provider, OllamaCloudProvider)
        assert provider.name == "ollama_cloud"

    def test_factory_requires_api_key(self):
        settings = Settings(
            app_env="test",
            log_level="WARNING",
            ai_provider="ollama_cloud",
            ollama_api_key="",
        )
        with pytest.raises(AIProviderNotConfiguredError):
            get_provider(settings)

    def test_factory_provider_name_matches_settings(self):
        settings = Settings(
            app_env="test",
            log_level="WARNING",
            ai_provider="ollama_cloud",
            ollama_api_key="k",
            ai_model="m",
        )
        provider = get_provider(settings)
        assert isinstance(provider, OllamaCloudProvider)
        assert provider.name == "ollama_cloud"
        assert provider._model == "m"  # type: ignore[attr-defined]
        assert provider._api_key == "k"  # type: ignore[attr-defined]
