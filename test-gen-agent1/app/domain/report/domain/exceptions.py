"""报告领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)

__all__ = [
    "DomainException",
    "DomainValidationError",
    "InvariantViolation",
    "AggregateNotFound",
    "ReportNotFound",
    "InvalidReportTransition",
]


class ReportNotFound(AggregateNotFound):
    """报告产物不存在（未生成 / 不在回收站）。"""


class InvalidReportTransition(DomainValidationError):
    """报告状态迁移不合法。"""
