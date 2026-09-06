"""环境状态与告警级别值对象。

环境状态机：
  offline → launching → online ⇄ error / maintenance
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class EnvStatusEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    LAUNCHING = "launching"


ALLOWED_TRANSITIONS: Dict[EnvStatusEnum, Set[EnvStatusEnum]] = {
    EnvStatusEnum.OFFLINE: {EnvStatusEnum.LAUNCHING, EnvStatusEnum.ONLINE,
                            EnvStatusEnum.ERROR, EnvStatusEnum.MAINTENANCE},
    EnvStatusEnum.LAUNCHING: {EnvStatusEnum.ONLINE, EnvStatusEnum.ERROR,
                              EnvStatusEnum.OFFLINE},
    EnvStatusEnum.ONLINE: {EnvStatusEnum.OFFLINE, EnvStatusEnum.ERROR,
                           EnvStatusEnum.MAINTENANCE},
    EnvStatusEnum.ERROR: {EnvStatusEnum.ONLINE, EnvStatusEnum.OFFLINE,
                          EnvStatusEnum.LAUNCHING, EnvStatusEnum.MAINTENANCE},
    EnvStatusEnum.MAINTENANCE: {EnvStatusEnum.ONLINE, EnvStatusEnum.OFFLINE,
                                EnvStatusEnum.ERROR},
}


@dataclass(frozen=True)
class EnvStatus(ValueObject):
    """环境状态值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        try:
            EnvStatusEnum(v)
        except ValueError:
            raise DomainValidationError(
                f"非法环境状态 '{self.value}'，仅支持 "
                f"{[e.value for e in EnvStatusEnum]}"
            )
        object.__setattr__(self, "value", v)

    def can_transition_to(self, target: "EnvStatus") -> bool:
        return target.value in [e.value for e in ALLOWED_TRANSITIONS.get(
            EnvStatusEnum(self.value), set())]

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AlertLevel(ValueObject):
    """告警级别值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in ("info", "warning", "critical"):
            raise DomainValidationError(
                f"非法告警级别 '{self.value}'，仅支持 info / warning / critical"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["EnvStatus", "EnvStatusEnum", "AlertLevel", "ALLOWED_TRANSITIONS"]
