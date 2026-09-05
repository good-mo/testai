"""任务中心操作聚合根 TaskCommand。

任务中心（task_center）限界上下文中的核心概念：一次对执行任务或定时任务
发起的管理操作。本域为横切展示域——执行任务数据来自 runs DDD / 定时任务
来自 test_plan DDD，此聚合建模的是一次操作命令的语义与结果状态。

聚合边界内的组成：
  - TaskCommand（聚合根：command_id + 目标 ID 列表 + 操作类型 + 结果）
"""
from __future__ import annotations

import time
import uuid
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.task_center.domain.events import (
    ScheduleEnabledChanged,
    TaskBatchStopped,
)

# 操作类型常量
OP_STOP_TASKS = "stop_tasks"
OP_DELETE_TASKS = "delete_tasks"
OP_RERUN_TASK = "rerun_task"
OP_SWITCH_SCHEDULES = "switch_schedules"
OP_ENABLE_SCHEDULES = "enable_schedules"
OP_DELETE_SCHEDULES = "delete_schedules"
OP_UPDATE_CRON = "update_cron"

_VALID_OPS = frozenset({
    OP_STOP_TASKS, OP_DELETE_TASKS, OP_RERUN_TASK,
    OP_SWITCH_SCHEDULES, OP_ENABLE_SCHEDULES,
    OP_DELETE_SCHEDULES, OP_UPDATE_CRON,
})


class TaskCommand(AggregateRoot):
    """任务中心批量操作聚合根。"""

    def __init__(
        self,
        *,
        command_id: str = "",
        operation: str = OP_STOP_TASKS,
        target_ids: Optional[List[str]] = None,
        payload: Optional[dict] = None,
        status: str = "pending",
        operator: str = "system",
        created_at: Optional[float] = None,
        _created: bool = False,
    ):
        if operation not in _VALID_OPS:
            raise DomainValidationError(f"非法任务中心操作: {operation}")
        if not command_id:
            command_id = uuid.uuid4().hex[:12]
        self.id = Identifier.of(command_id)
        self._operation = operation
        self._target_ids = list(target_ids or [])
        self._payload = dict(payload or {})
        self._status = status or "pending"
        self._operator = operator or "system"
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []
        self.version = 0
        if _created:
            self._record_initial_event()

    @property
    def operation(self) -> str:
        return self._operation

    @property
    def target_ids(self) -> List[str]:
        return list(self._target_ids)

    @property
    def payload(self) -> dict:
        return dict(self._payload)

    @property
    def status(self) -> str:
        return self._status

    @property
    def operator(self) -> str:
        return self._operator

    @property
    def created_at(self) -> float:
        return self._created_at

    def _record_initial_event(self) -> None:
        """创建时按操作类型记录对应领域事件。"""
        if self._operation == OP_STOP_TASKS:
            self.record_event(TaskBatchStopped(self._target_ids, self._operator))
        elif self._operation == OP_ENABLE_SCHEDULES:
            self.record_event(ScheduleEnabledChanged(
                self._target_ids,
                bool(self._payload.get("enable", True)),
                self._operator,
            ))
        elif self._operation == OP_SWITCH_SCHEDULES:
            self.record_event(ScheduleEnabledChanged(
                self._target_ids, True, self._operator))

    # ── 业务命令 ─────────────────────────────────────
    def mark_running(self) -> None:
        """标记操作执行中。"""
        self._status = "running"

    def mark_completed(self) -> None:
        """标记操作已完成。"""
        self._status = "completed"

    def mark_failed(self) -> None:
        """标记操作失败。"""
        self._status = "failed"

    # ── 持久化 / 序列化 ─────────────────────────────
    def to_dict(self) -> dict:
        return {
            "commandId": self.id.value,
            "id": self.id.value,
            "operation": self._operation,
            "targetIds": self._target_ids,
            "payload": self._payload,
            "status": self._status,
            "operator": self._operator,
            "createdAt": self._created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "TaskCommand":
        return TaskCommand(
            command_id=str(data.get("commandId") or data.get("command_id") or data.get("id") or ""),
            operation=data.get("operation", OP_STOP_TASKS),
            target_ids=data.get("targetIds") or data.get("target_ids") or [],
            payload=data.get("payload") or {},
            status=data.get("status", "pending"),
            operator=data.get("operator", "system"),
            created_at=data.get("createdAt") or data.get("created_at"),
        )


__all__ = [
    "TaskCommand",
    "OP_STOP_TASKS", "OP_DELETE_TASKS", "OP_RERUN_TASK",
    "OP_SWITCH_SCHEDULES", "OP_ENABLE_SCHEDULES",
    "OP_DELETE_SCHEDULES", "OP_UPDATE_CRON",
]
