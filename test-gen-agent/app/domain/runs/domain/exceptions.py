"""任务运行领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import DomainException, DomainValidationError, InvariantViolation

__all__ = ["DomainException", "DomainValidationError", "InvariantViolation"]
