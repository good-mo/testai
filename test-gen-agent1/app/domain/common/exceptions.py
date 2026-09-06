"""领域异常。

领域层只抛出领域语义异常；应用层负责把领域异常翻译成 HTTP 响应，
从而保持领域层对 FastAPI/HTTP 的零依赖（防腐）。
"""
from __future__ import annotations


class DomainException(Exception):
    """领域异常基类。"""

    status_code: int = 400

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class DomainValidationError(DomainException):
    """领域校验失败（非法值/非法状态参数）。"""

    status_code = 422


class InvariantViolation(DomainException):
    """聚合不变量被破坏（非法状态迁移等）。"""

    status_code = 409


class AggregateNotFound(DomainException):
    """聚合不存在。"""

    status_code = 404
