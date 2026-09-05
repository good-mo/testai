"""文件领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)

__all__ = [
    "DomainException", "DomainValidationError", "InvariantViolation",
    "AggregateNotFound", "FileNotFound", "UnsafeFilenameError",
]


class FileNotFound(AggregateNotFound):
    """文件不存在。"""


class UnsafeFilenameError(DomainValidationError):
    """文件名不安全（路径穿越风险）。"""
