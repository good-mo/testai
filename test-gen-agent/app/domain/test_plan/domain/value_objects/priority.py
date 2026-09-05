"""测试计划优先级值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class PriorityEnum(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"  # 默认
    P3 = "P3"


VALID: Set[str] = {e.value for e in PriorityEnum}
# 优先级权重：数值越小优先级越高
ORDER = {
    PriorityEnum.P0.value: 0,
    PriorityEnum.P1.value: 1,
    PriorityEnum.P2.value: 2,
    PriorityEnum.P3.value: 3,
}


@dataclass(frozen=True)
class Priority(ValueObject):
    """测试计划优先级值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).strip().upper()
        if v not in VALID:
            raise DomainValidationError(
                f"非法测试计划优先级 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def weight(self) -> int:
        return ORDER[self.value]

    def __str__(self) -> str:
        return self.value
