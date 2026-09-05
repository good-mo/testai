"""任务生命周期状态值对象 + 状态机定义。

任务状态机（与 app/tasks/manager.py 对齐）：
    pending → running → success / failed / cancelled
  - pending   待执行（可被 worker 认领）
  - running   执行中
  - success   执行成功
  - failed    执行失败（失败可重跑回 running/pending）
  - cancelled 已取消（不可恢复）
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: Dict[TaskStatusEnum, Set[TaskStatusEnum]] = {
    TaskStatusEnum.PENDING: {TaskStatusEnum.RUNNING, TaskStatusEnum.CANCELLED},
    TaskStatusEnum.RUNNING: {TaskStatusEnum.SUCCESS, TaskStatusEnum.FAILED,
                             TaskStatusEnum.CANCELLED},
    TaskStatusEnum.FAILED: {TaskStatusEnum.RUNNING, TaskStatusEnum.PENDING,
                            TaskStatusEnum.CANCELLED},   # 允许失败重跑
    TaskStatusEnum.SUCCESS: set(),
    TaskStatusEnum.CANCELLED: set(),
}


@dataclass(frozen=True)
class TaskStatus(ValueObject):
    """任务状态值对象，自带状态机校验。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in {e.value for e in TaskStatusEnum}:
            raise DomainValidationError(
                f"非法任务状态 '{self.value}'，仅支持 "
                f"{[e.value for e in TaskStatusEnum]}"
            )
        object.__setattr__(self, "value", v)

    @property
    def terminal(self) -> bool:
        """是否终态（不可再流转）。"""
        return self.value in (TaskStatusEnum.SUCCESS.value, TaskStatusEnum.CANCELLED.value)

    def can_transition_to(self, target: "TaskStatus") -> bool:
        return target.value in ALLOWED_TRANSITIONS.get(
            TaskStatusEnum(self.value), set())

    def __str__(self) -> str:
        return self.value
