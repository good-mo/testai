"""生成任务生命周期状态值对象 + 状态机定义。

生成任务（GenerationJob）从提交到完成的有限状态机：
    PENDING → RUNNING → SUCCEEDED | FAILED | CANCELLED

不变量（内聚于值对象）：
  - RUNNING 仅可从 PENDING 进入（首次提交后开始执行）；
  - SUCCEEDED / FAILED 均为终态，仅可由 RUNNING 进入；
  - 终态（SUCCEEDED / FAILED / CANCELLED）不可再流转。
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class GenerationStatusEnum(str, Enum):
    PENDING = "pending"        # 已提交待执行
    RUNNING = "running"        # 执行中
    SUCCEEDED = "succeeded"    # 成功（已生成通过验证的测试）
    FAILED = "failed"          # 失败（不可恢复错误 / 超上限）
    CANCELLED = "cancelled"    # 取消


# 允许的状态迁移矩阵（业务不变量）
ALLOWED_TRANSITIONS: Dict[GenerationStatusEnum, Set[GenerationStatusEnum]] = {
    GenerationStatusEnum.PENDING: {GenerationStatusEnum.RUNNING, GenerationStatusEnum.CANCELLED},
    GenerationStatusEnum.RUNNING: {
        GenerationStatusEnum.SUCCEEDED,
        GenerationStatusEnum.FAILED,
        GenerationStatusEnum.CANCELLED,
    },
    GenerationStatusEnum.SUCCEEDED: set(),
    GenerationStatusEnum.FAILED: set(),
    GenerationStatusEnum.CANCELLED: set(),
}

_TERMINAL = {
    GenerationStatusEnum.SUCCEEDED,
    GenerationStatusEnum.FAILED,
    GenerationStatusEnum.CANCELLED,
}


class GenerationStatus(ValueObject):
    """生成任务状态值对象，自带状态机校验。"""

    value: GenerationStatusEnum

    def __init__(self, value):
        if isinstance(value, GenerationStatusEnum):
            v = value
        else:
            raw = str(value).lower()
            try:
                v = GenerationStatusEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法生成任务状态 '{value}'，仅支持 "
                    f"{[e.value for e in GenerationStatusEnum]}"
                )
        object.__setattr__(self, "value", v)

    @property
    def is_terminal(self) -> bool:
        return self.value in _TERMINAL

    def can_transition_to(self, target: "GenerationStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(self.value, set())

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GenerationStatus):
            return self.value is other.value
        if isinstance(other, GenerationStatusEnum):
            return self.value is other
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented


__all__ = ["GenerationStatus", "GenerationStatusEnum", "ALLOWED_TRANSITIONS"]
