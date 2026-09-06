"""测试计划生命周期状态值对象 + 状态机定义。

计划生命周期：prepared(待开始) → running(进行中) → completed(已完成)。
「归档 archived」是计划的一种终态标记，仅可从非归档态进入，且不可直接
回退到运行态（可由运维处置）；状态机在此守护这些不变量。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class PlanStatusEnum(str, Enum):
    PREPARED = "prepared"     # 待开始（默认）
    RUNNING = "running"       # 进行中
    COMPLETED = "completed"   # 已完成
    ARCHIVED = "archived"     # 已归档（终态标记）


# 业务允许的状态迁移矩阵
ALLOWED_TRANSITIONS: Dict[PlanStatusEnum, Set[PlanStatusEnum]] = {
    PlanStatusEnum.PREPARED: {PlanStatusEnum.RUNNING, PlanStatusEnum.COMPLETED},
    PlanStatusEnum.RUNNING: {PlanStatusEnum.COMPLETED, PlanStatusEnum.PREPARED},
    PlanStatusEnum.COMPLETED: {PlanStatusEnum.RUNNING},  # 允许重新打开
}


class PlanStatus(ValueObject):
    """测试计划状态值对象，自带状态机校验。"""

    def __init__(self, value):
        if isinstance(value, PlanStatusEnum):
            v = value
        else:
            raw = str(value).strip().lower()
            if raw in ("", "none"):
                raw = PlanStatusEnum.PREPARED.value
            try:
                v = PlanStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法测试计划状态 '{value}'，仅支持 "
                    f"{[e.value for e in PlanStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_archived(self) -> bool:
        return self.value is PlanStatusEnum.ARCHIVED

    def can_transition_to(self, target: "PlanStatus") -> bool:
        # 归档为特殊标记，不进入常规状态机
        if target.value is PlanStatusEnum.ARCHIVED:
            return True
        if self.value is PlanStatusEnum.ARCHIVED:
            return False
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PlanStatus):
            return self.value is other.value
        if isinstance(other, PlanStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other.lower()
        return NotImplemented
