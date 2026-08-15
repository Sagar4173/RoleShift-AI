"""Shared enums used across RoleShift AI documents and schemas."""

from __future__ import annotations

from enum import Enum


class RoleStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class HumanInvolvement(str, Enum):
    """How much human involvement an activity currently requires."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class SourceType(str, Enum):
    WEBSITE = "website"
    REPORT = "report"
    PUBLICATION = "publication"
    JOB_POSTING = "job_posting"
    INTERNAL = "internal"
    OTHER = "other"


class AnalysisRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ImpactLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReskillingPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"