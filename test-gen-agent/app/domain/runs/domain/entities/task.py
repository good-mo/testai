"""任务聚合根 Task（异步任务队列 / TaskCenter）。

聚合边界内的组成：
  - Task（聚合根：任务元数据 + 生命周期状态 + 结果）
  - 值对象：TaskStatus（自带状态机）

职责：守护任务生命周期状态机不变量（pending→running→success/failed/cancelled），
防止非法流转（如终态后再运行、成功态被取消）。所有变更必须经由聚合根方法。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import InvariantViolation
from app.domain.runs.domain.events import (
    TaskCancelled,
    TaskFailed,
    TaskRequeued,
    TaskStarted,
    TaskSucceeded,
)
from app.domain.runs.domain.value_objects.task_status import (
    TaskStatus,
    TaskStatusEnum,
)


class Task(AggregateRoot):
    """任务聚合根。"""

    def __init__(
        self,
        *,
        task_id: str,
        status: str = TaskStatusEnum.PENDING.value,
        coro_name: str = "",
        args: Optional[list] = None,
        handler_name: str = "",
        handler_args: Optional[list] = None,
        handler_kwargs: Optional[dict] = None,
        restartable: bool = False,
        result: Any = None,
        error: str = "",
        claimed_by: str = "",
        created_at: Optional[float] = None,
        started_at: Optional[float] = None,
        finished_at: Optional[float] = None,
    ):
        self.id = Identifier.of(task_id)
        self._status = TaskStatus(status)
        self._coro_name = coro_name or ""
        self._args = list(args or [])
        self._handler_name = handler_name or ""
        self._handler_args = list(handler_args or [])
        self._handler_kwargs = dict(handler_kwargs or {})
        self._restartable = bool(restartable)
        self._result = result
        self._error = error or ""
        self._claimed_by = claimed_by or ""
        now = time.time()
        self._created_at = created_at if created_at is not None else now
        self._started_at = started_at
        self._finished_at = finished_at
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def coro_name(self) -> str:
        return self._coro_name

    @property
    def args(self) -> List[Any]:
        return list(self._args)

    @property
    def handler_name(self) -> str:
        return self._handler_name

    @property
    def handler_args(self) -> List[Any]:
        return list(self._handler_args)

    @property
    def handler_kwargs(self) -> Dict[str, Any]:
        return dict(self._handler_kwargs)

    @property
    def restartable(self) -> bool:
        return self._restartable

    @property
    def result(self) -> Any:
        return self._result

    @property
    def error(self) -> str:
        return self._error

    @property
    def claimed_by(self) -> str:
        return self._claimed_by

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def started_at(self) -> float:
        return self._started_at

    @property
    def finished_at(self) -> float:
        return self._finished_at

    @property
    def terminal(self) -> bool:
        return self._status.terminal

    # ── 内部流转守卫 ─────────────────────────────────
    def _transit(self, target: TaskStatusEnum, **meta) -> None:
        ts = TaskStatus(target.value)
        if self._status.terminal:
            raise InvariantViolation(
                f"任务已处于终态 '{self._status}'，不能再迁移到 '{target.value}'")
        if not self._status.can_transition_to(ts):
            raise InvariantViolation(
                f"不允许任务状态从 '{self._status}' 迁移到 '{target.value}'")
        self._status = ts

    # ── 业务命令 ─────────────────────────────────────
    def start(self, worker: str = "") -> None:
        """认领并开始执行：pending -> running。"""
        self._transit(TaskStatusEnum.RUNNING)
        self._claimed_by = worker or ""
        self._started_at = time.time()
        self.record_event(TaskStarted(self.id.value, self._claimed_by))

    def succeed(self, result: Any = None) -> None:
        """执行成功：running -> success。"""
        self._transit(TaskStatusEnum.SUCCESS)
        self._result = result
        self._finished_at = time.time()
        self.record_event(TaskSucceeded(self.id.value))

    def fail(self, error: str = "") -> None:
        """执行失败：running -> failed（可重跑）。"""
        self._transit(TaskStatusEnum.FAILED)
        self._error = error or ""
        self._finished_at = time.time()
        self.record_event(TaskFailed(self.id.value, self._error))

    def cancel(self) -> None:
        """取消任务：pending/running -> cancelled。"""
        self._transit(TaskStatusEnum.CANCELLED)
        self._finished_at = time.time()
        self.record_event(TaskCancelled(self.id.value))

    def requeue(self) -> None:
        """失败重跑入队：failed -> pending。"""
        self._transit(TaskStatusEnum.PENDING)
        self._claimed_by = ""
        self._error = ""
        self._started_at = None
        self._finished_at = None
        self.record_event(TaskRequeued(self.id.value))

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "task_id": self.id.value,
            "status": self._status.value,
            "coro_name": self._coro_name,
            "args": list(self._args),
            "handler_name": self._handler_name,
            "handler_args": list(self._handler_args),
            "handler_kwargs": dict(self._handler_kwargs),
            "restartable": self._restartable,
            "result": self._result,
            "error": self._error,
            "claimed_by": self._claimed_by,
            "created_at": self._created_at,
            "started_at": self._started_at,
            "finished_at": self._finished_at,
        }

    @staticmethod
    def _parse_json_field(value, default):
        """兼容 task_repo 将 args/handler_* 以 JSON 字符串落库的读取形态。"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return default
        return value if value is not None else default

    @staticmethod
    def from_dict(data: dict) -> "Task":
        return Task(
            task_id=str(data.get("task_id") or data.get("id") or ""),
            status=data.get("status", "pending"),
            coro_name=data.get("coro_name", ""),
            args=Task._parse_json_field(data.get("args"), []),
            handler_name=data.get("handler_name", ""),
            handler_args=Task._parse_json_field(data.get("handler_args"), []),
            handler_kwargs=Task._parse_json_field(data.get("handler_kwargs"), {}),
            restartable=Task._parse_json_field(data.get("restartable"), False),
            result=data.get("result"),
            error=data.get("error", ""),
            claimed_by=data.get("claimed_by", ""),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
        )
