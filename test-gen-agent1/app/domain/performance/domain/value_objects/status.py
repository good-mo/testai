"""性能测试状态值对象 + 状态机定义。

描述一次性能测试任务的生命周期：
  pending(待执行) → running(执行中) → passed(达标) / failed(不达标) / skipped(跳过)

规则：
  - 只有处于 running 的测试才能进入终态（passed/failed/skipped）。
  - 终态不可再流转（重新跑需另建新任务）。
  - failed / skipped 需带原因（由聚合统一存储 reason）。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class PerformanceStatusEnum(str, Enum):
    PENDING = "pending"     # 待执行
    RUNNING = "running"     # 执行中
    PASSED = "passed"       # 达标
    FAILED = "failed"       # 不达标
    SKIPPED = "skipped"     # 跳过


# 允许的状态迁移矩阵（不变量）
ALLOWED_TRANSITIONS: Dict[PerformanceStatusEnum, Set[PerformanceStatusEnum]] = {
    PerformanceStatusEnum.PENDING: {PerformanceStatusEnum.RUNNING, PerformanceStatusEnum.SKIPPED},
    PerformanceStatusEnum.RUNNING: {
        PerformanceStatusEnum.PASSED,
        PerformanceStatusEnum.FAILED,
        PerformanceStatusEnum.SKIPPED,
    },
    PerformanceStatusEnum.PASSED: set(),
    PerformanceStatusEnum.FAILED: set(),
    PerformanceStatusEnum.SKIPPED: set(),
}

# 终结态（不可再迁移）
TERMINAL: Set[PerformanceStatusEnum] = {
    PerformanceStatusEnum.PASSED,
    PerformanceStatusEnum.FAILED,
    PerformanceStatusEnum.SKIPPED,
}


class PerformanceStatus(ValueObject):
    """性能测试状态值对象，自带状态机校验。"""

    def __init__(self, value: object):
        if isinstance(value, PerformanceStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            if raw in ("", "none"):
                raw = PerformanceStatusEnum.PENDING.value
            try:
                v = PerformanceStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法性能测试状态 '{value}'，仅支持 "
                    f"{[e.value for e in PerformanceStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_terminal(self) -> bool:
        return self.value in TERMINAL

    def can_transition_to(self, target: "PerformanceStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PerformanceStatus):
            return self.value is other.value
        if isinstance(other, PerformanceStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other.lower()
        return NotImplemented


__all__ = ["PerformanceStatus", "PerformanceStatusEnum", "ALLOWED_TRANSITIONS"]
