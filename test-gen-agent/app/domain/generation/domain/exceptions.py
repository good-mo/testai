"""生成编排领域异常。

领域层只抛领域语义异常；应用层负责把领域异常翻译成 HTTP 响应。
"""
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
]
