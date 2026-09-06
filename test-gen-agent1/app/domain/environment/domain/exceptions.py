"""环境领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)

__all__ = [
    "DomainException", "DomainValidationError", "InvariantViolation",
    "AggregateNotFound", "EnvironmentNotFound",
]


class EnvironmentNotFound(AggregateNotFound):
    """环境不存在。"""
