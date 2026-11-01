from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from repo_analyzer.core.errors import RepositoryValidationError
from repo_analyzer.repository.git import RepositoryManager


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class AnalysisStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED = "UNSUPPORTED"


ACTIVE_STATUSES = frozenset({AnalysisStatus.QUEUED, AnalysisStatus.RUNNING})
TERMINAL_STATUSES = frozenset(set(AnalysisStatus) - set(ACTIVE_STATUSES))


class AnalysisCreateRequest(ApiModel):
    repository_url: str = Field(min_length=1, max_length=2048)

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, value: str) -> str:
        try:
            return RepositoryManager.validate_github_url(value)
        except RepositoryValidationError as exc:
            raise ValueError(str(exc)) from exc


class AnalysisSummary(ApiModel):
    id: UUID
    repository_url: str
    status: AnalysisStatus
    commit_sha: str | None = None
    analyzer_version: str | None = None
    schema_version: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0
    failure_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class AnalysisListResponse(ApiModel):
    items: list[AnalysisSummary]
    limit: int
    offset: int


class UserResponse(ApiModel):
    id: UUID
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class ErrorDetail(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    detail: ErrorDetail

