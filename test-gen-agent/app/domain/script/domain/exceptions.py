"""脚本领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)

__all__ = [
    "DomainException", "DomainValidationError", "InvariantViolation",
    "AggregateNotFound", "ScriptNotFound",
]


class ScriptNotFound(AggregateNotFound):
    """脚本不存在。"""
