"""AI provider abstraction layer.

Defines the protocol every provider must implement plus shared Pydantic
models for analysis input/output. Business logic references only this
module's types -- never a specific provider or model.

Concrete provider implementations live in ``services.ai.providers``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Analysis request (structured context passed to the provider)
# ---------------------------------------------------------------------------

class ProcessContext(BaseModel):
    """A process relevant to the role being analysed."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ActivityContext(BaseModel):
    """An activity the role performs, with a temporary reference for the LLM."""

    model_config = ConfigDict(extra="forbid")

    temp_ref: str = Field(min_length=1, max_length=20, description="e.g. act_0")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    current_human_involvement: str = Field(max_length=50)


class SkillContext(BaseModel):
    """A current skill of the role."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class AIAnalysisRequest(BaseModel):
    """Fully structured context for a single role analysis request."""

    model_config = ConfigDict(extra="forbid")

    role_id: str = Field(min_length=1, max_length=50)
    role_name: str = Field(min_length=1, max_length=200)
    role_description: str | None = Field(default=None, max_length=2000)
    industry: str | None = Field(default=None, max_length=200)
    processes: list[ProcessContext] = Field(default_factory=list)
    activities: list[ActivityContext] = Field(default_factory=list)
    current_skills: list[SkillContext] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Raw AI output (validated against this schema immediately after parsing)
# ---------------------------------------------------------------------------

class ActivityImpactOutput(BaseModel):
    """Per-activity impact returned by the AI provider."""

    model_config = ConfigDict(extra="forbid")

    activity_ref: str = Field(min_length=1, max_length=20)
    automation_score: float = Field(ge=0.0, le=1.0)
    augmentation_score: float = Field(ge=0.0, le=1.0)
    human_responsibility: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=2000)


class FutureResponsibilityOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    rationale: str | None = Field(default=None, max_length=2000)


class FutureSkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    relevance: float = Field(ge=0.0, le=1.0)
    priority: str = Field(min_length=1, max_length=20)


class RecommendationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    rationale: str | None = Field(default=None, max_length=2000)
    priority: str = Field(min_length=1, max_length=20)


class AIAnalysisResult(BaseModel):
    """Structured output returned by an AI provider (pre-normalisation)."""

    model_config = ConfigDict(extra="forbid")

    ai_exposure_score: float = Field(ge=0.0, le=1.0)
    ai_exposure_summary: str = Field(min_length=1, max_length=2000)
    automation_score: float = Field(ge=0.0, le=1.0)
    augmentation_score: float = Field(ge=0.0, le=1.0)
    reskilling_priority: str = Field(min_length=1, max_length=20)
    activity_impacts: list[ActivityImpactOutput] = Field(default_factory=list)
    future_responsibilities: list[FutureResponsibilityOutput] = Field(default_factory=list)
    future_skills: list[FutureSkillOutput] = Field(default_factory=list)
    recommendations: list[RecommendationOutput] = Field(default_factory=list)
    reasoning: str | None = Field(default=None, max_length=20000)


# ---------------------------------------------------------------------------
# Output parsing helper
# ---------------------------------------------------------------------------


def parse_analysis_result(content: str) -> AIAnalysisResult:
    """Validate raw provider content as an AIAnalysisResult.

    Providers are asked for JSON, but models occasionally wrap the payload
    in markdown code fences (or surrounding prose). This helper tries the
    strict path first, then strips fences, then falls back to the first
    balanced JSON object, so a well-formed response is never rejected purely
    because of decorative formatting.
    """
    text = (content or "").strip()
    error: Exception | None = None

    try:
        return AIAnalysisResult.model_validate_json(text)
    except Exception as exc:
        error = exc

    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return AIAnalysisResult.model_validate_json(fenced.group(1).strip())
        except Exception as exc:
            error = exc

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return AIAnalysisResult.model_validate_json(text[start : end + 1])
        except Exception as exc:
            error = exc

    if error is not None:
        raise error
    raise ValueError("Empty AI provider response")


# ---------------------------------------------------------------------------
# Provider health
# ---------------------------------------------------------------------------
class ProviderHealth(BaseModel):
    healthy: bool
    provider: str
    latency_ms: int | None = None
    detail: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Provider errors
# ---------------------------------------------------------------------------

class AIProviderError(Exception):
    """Base error for AI provider failures."""

    def __init__(self, message: str, *, code: str = "ai_provider_error", status_code: int = 503) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AIProviderTimeoutError(AIProviderError):
    def __init__(self, message: str = "AI provider request timed out") -> None:
        super().__init__(message, code="ai_provider_timeout", status_code=504)


class AIProviderUnavailableError(AIProviderError):
    def __init__(self, message: str = "AI provider is unavailable") -> None:
        super().__init__(message, code="ai_provider_unavailable", status_code=503)


class AIOutputValidationError(AIProviderError):
    def __init__(self, message: str = "AI output failed validation") -> None:
        super().__init__(message, code="ai_output_validation_error", status_code=422)


class AIProviderNotConfiguredError(AIProviderError):
    def __init__(self, message: str = "AI provider is not configured") -> None:
        super().__init__(message, code="ai_provider_not_configured", status_code=503)


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------

class AIProvider(Protocol):
    """Contract every AI provider must implement."""

    name: str

    async def analyze_role(self, request: AIAnalysisRequest) -> AIAnalysisResult:
        """Run a full role analysis and return structured output."""
        ...

    async def health_check(self) -> ProviderHealth:
        """Check provider availability without performing an analysis."""
        ...
