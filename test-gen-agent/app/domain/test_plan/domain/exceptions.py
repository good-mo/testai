"""测试计划领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)


class TestPlanNotFound(AggregateNotFound):
    """测试计划不存在。"""

    def __init__(self, message: str = "测试计划不存在"):
        super().__init__(message)


class InvalidTestPlanStatusTransition(InvariantViolation):
    """测试计划状态非法迁移。"""

    def __init__(self, current: str, target: str):
        super().__init__(f"不允许从状态 '{current}' 迁移到 '{target}'")


class PlanCaseNotFound(DomainException):
    """计划关联用例不存在。"""

    status_code = 404

    def __init__(self, message: str = "计划关联用例不存在"):
        super().__init__(message)


__all__ = [
    "AggregateNotFound",
    "DomainException",
    "DomainValidationError",
    "InvariantViolation",
    "InvalidTestPlanStatusTransition",
    "PlanCaseNotFound",
    "TestPlanNotFound",
]
