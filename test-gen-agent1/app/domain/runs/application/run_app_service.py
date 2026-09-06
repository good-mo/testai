"""任务运行应用服务（Application Service / Use Case 门面）。

承载"任务队列（TaskCenter）"用例的事务边界：入队 → 执行（start → 完成 /
失败 / 取消）→ 失败重跑 → 保存聚合 → 发布领域事件。保持瘦，只做编排。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound, DomainValidationError
from app.domain.runs.application.dto import (
    CompleteTaskCommand,
    EnqueueTaskCommand,
    StartTaskCommand,
    TaskListQuery,
)
from app.domain.runs.domain.entities.task import Task
from app.domain.runs.domain.repository import TaskRepository
from app.domain.runs.domain.value_objects.task_status import TaskStatusEnum
from app.domain.runs.infrastructure.run_repository_impl import TaskRepoAdapter

logger = logging.getLogger(__name__)


class RunAppService:
    """任务运行用例编排服务。"""

    def __init__(self, repo: TaskRepository = None):
        self._repo: TaskRepository = repo or TaskRepoAdapter()

    # ── 入队 ─────────────────────────────────────────
    def enqueue(self, cmd: EnqueueTaskCommand) -> dict:
        task = Task(
            task_id=self._repo.next_id(),
            status=cmd.status,
            coro_name=cmd.coro_name,
            args=cmd.args,
            handler_name=cmd.handler_name,
            handler_args=cmd.handler_args,
            handler_kwargs=cmd.handler_kwargs,
            restartable=cmd.restartable,
        )
        self._repo.save(task)
        self._publish(task)
        return task.to_dict()

    # ── 执行生命周期 ─────────────────────────────────
    def start(self, cmd: StartTaskCommand) -> dict:
        task = self._find_or_raise(cmd.task_id)
        task.start(cmd.worker)
        self._repo.update(task)
        self._publish(task)
        return task.to_dict()

    def complete(self, cmd: CompleteTaskCommand) -> dict:
        """根据目标状态驱动聚合状态机：success/failed/cancelled。"""
        task = self._find_or_raise(cmd.task_id)
        target = str(cmd.status).lower()
        if target == TaskStatusEnum.SUCCESS.value:
            task.succeed(cmd.result)
        elif target == TaskStatusEnum.FAILED.value:
            task.fail(cmd.error)
        elif target == TaskStatusEnum.CANCELLED.value:
            task.cancel()
        else:
            raise DomainValidationError(f"不支持的任务完成状态: {cmd.status}")
        self._repo.update(task)
        self._publish(task)
        return task.to_dict()

    def requeue(self, task_id: str) -> dict:
        """失败任务重跑入队：failed -> pending。"""
        task = self._find_or_raise(task_id)
        task.requeue()
        self._repo.save(task)
        self._publish(task)
        return task.to_dict()

    # ── 认领 / 查询 ─────────────────────────────────
    def claim_next_pending(self, worker_id: str = "") -> Optional[dict]:
        task = self._repo.claim_next_pending(worker_id=worker_id)
        if task is None:
            return None
        return task.to_dict()

    def get(self, task_id: str) -> Optional[dict]:
        task = self._repo.find_by_id(task_id)
        return task.to_dict() if task else None

    def list_recent(self, query: TaskListQuery) -> dict:
        tasks = self._repo.list_recent(limit=query.limit)
        return {"list": [t.to_dict() for t in tasks], "total": len(tasks)}

    def list_pending(self) -> dict:
        tasks = self._repo.list_pending()
        return {"list": [t.to_dict() for t in tasks], "total": len(tasks)}

    def delete(self, task_id: str) -> bool:
        return self._repo.delete(task_id)

    # ── 内部助手 ─────────────────────────────────────
    def _find_or_raise(self, task_id: str) -> Task:
        task = self._repo.find_by_id(task_id)
        if task is None:
            raise AggregateNotFound(f"任务不存在: {task_id}")
        return task

    def _publish(self, task: Task) -> None:
        for ev in task.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
run_app_service = RunAppService()
