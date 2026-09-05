"""性能测试领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    DomainException,
    DomainValidationError,
    InvariantViolation,
)


class InvalidPerformanceStatusTransition(InvariantViolation):
    """性能测试状态非法迁移。"""

    def __init__(self, current: str, target: str):
        super().__init__(f"不允许从状态 '{current}' 迁移到 '{target}'")


class PerformanceTestNotFound(DomainException):
    status_code = 404

    def __init__(self, message: str = "性能测试任务不存在"):
        super().__init__(message)


class SLOValidationRejected(DomainValidationError):
    """SLO 校验不通过（用于需要显式抛出的校验场景）。"""


__all__ = [
    "InvalidPerformanceStatusTransition",
    "PerformanceTestNotFound",
    "SLOValidationRejected",
]
