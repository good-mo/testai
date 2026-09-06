"""消息领域异常。"""
from __future__ import annotations

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)

__all__ = [
    "DomainException", "DomainValidationError", "InvariantViolation",
    "AggregateNotFound", "MessageTaskNotFound", "NotificationNotFound",
]


class MessageTaskNotFound(AggregateNotFound):
    """消息设置任务不存在。"""


class NotificationNotFound(AggregateNotFound):
    """站内通知不存在。"""
