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


class MemberRole(str, Enum):
    """Organization membership role (Phase 6.4 RBAC).

    OWNER is the org anchor: last-owner invariants prevent an organization
    from ever reaching zero owners. ADMIN manages the org operationally
    (destructive actions, AI spend, member management for non-owner roles).
    ANALYST performs the core product work including cost-bearing analysis.
    VIEWER is read-only: no mutations and no AI spend.
    """

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"