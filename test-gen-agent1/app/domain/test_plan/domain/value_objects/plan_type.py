"""测试计划类型值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class PlanTypeEnum(str, Enum):
    TEST_PLAN = "TEST_PLAN"   # 普通测试计划（默认）
    GROUP = "GROUP"           # 计划组


@dataclass(frozen=True)
class PlanType(ValueObject):
    """测试计划类型值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).strip().upper()
        if v not in {e.value for e in PlanTypeEnum}:
            raise DomainValidationError(
                f"非法测试计划类型 '{self.value}'，仅支持 TEST_PLAN / GROUP"
            )
        object.__setattr__(self, "value", v)

    @property
    def is_group(self) -> bool:
        return self.value is PlanTypeEnum.GROUP.value

    def __str__(self) -> str:
        return self.value
