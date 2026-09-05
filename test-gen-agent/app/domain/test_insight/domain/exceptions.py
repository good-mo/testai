"""TestInsight 领域异常。"""
from app.domain.common.exceptions import DomainException, DomainValidationError, InvariantViolation

__all__ = [
    "DomainException",
    "DomainValidationError",
    "InvariantViolation",
    "TraceRunNotFound",
    "InvalidTraceRecord",
]


class TraceRunNotFound(DomainException):
    """执行追溯记录不存在。"""

    status_code = 404

    def __init__(self, message: str = "执行追溯记录不存在"):
        super().__init__(message)


class InvalidTraceRecord(DomainValidationError):
    """执行追溯记录不满足领域约束。"""

    def __init__(self, message: str = "执行追溯记录非法"):
        super().__init__(message)
