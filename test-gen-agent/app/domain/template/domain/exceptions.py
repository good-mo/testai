"""模板领域异常。"""
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
    "TemplateNotFound",
]


class TemplateNotFound(AggregateNotFound):
    """模板不存在。"""
