"""通知状态与消息类型值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class NotificationStatusEnum(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"


@dataclass(frozen=True)
class NotificationStatus(ValueObject):
    """通知状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).upper()
        try:
            NotificationStatusEnum(v)
        except ValueError:
            raise DomainValidationError(
                f"非法通知状态 '{self.value}'，仅支持 UNREAD / READ"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value

    def mark_read(self) -> "NotificationStatus":
        return NotificationStatus(NotificationStatusEnum.READ.value)


@dataclass(frozen=True)
class RobotPlatform(ValueObject):
    """机器人平台（IN_SITE / MAIL / CUSTOM / DING_TALK 等）。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).upper()
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["NotificationStatus", "NotificationStatusEnum", "RobotPlatform"]
