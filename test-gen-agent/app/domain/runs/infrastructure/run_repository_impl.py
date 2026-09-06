"""任务运行聚合仓储实现（Adapter 防腐层）。

把"面向聚合的仓储接口"翻译为既有四层 Repo 命令（task_repo 模块函数），
复用已验证的存储逻辑，同时让领域层获得聚合级读写语义与状态机守护。
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.runs.domain.entities.task import Task
from app.core.task_queue_store import task_repo


class TaskRepoAdapter:
    """将既有 task_repo 模块封装为面向 Task 聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex

    # ── 读 ──────────────────────────────────────────
    def find_by_id(self, task_id: str) -> Optional[Task]:
        row = task_repo.get_task(task_id)
        return Task.from_dict(dict(row)) if row else None

    def list_recent(self, limit: int = 50) -> List[Task]:
        return [Task.from_dict(dict(r)) for r in task_repo.list_recent(limit=limit)]

    def list_pending(self) -> List[Task]:
        return [Task.from_dict(dict(r)) for r in task_repo.list_pending()]

    # ── 写 ──────────────────────────────────────────
    def save(self, task: Task) -> Task:
        task_repo.save_task(
            task_id=task.id.value,
            status=task.status.value,
            coro_name=task.coro_name,
            args=task.args,
            handler_name=task.handler_name,
            handler_args=task.handler_args,
            handler_kwargs=task.handler_kwargs,
            restartable=task.restartable,
            created_at=task.created_at,
        )
        return task

    def update(self, task: Task) -> Optional[Task]:
        # task_repo.update_status 以白名单字段 + 状态更新任务
        kwargs = {}
        if task._started_at is not None:
            kwargs["started_at"] = task._started_at
        if task._finished_at is not None:
            kwargs["finished_at"] = task._finished_at
        if task._claimed_by:
            kwargs["claimed_by"] = task._claimed_by
        if task._result is not None:
            kwargs["result"] = task._result
        if task._error:
            kwargs["error"] = task._error
        task_repo.update_status(task.id.value, task.status.value, **kwargs)
        return self.find_by_id(task.id.value)

    def delete(self, task_id: str) -> bool:
        return task_repo.delete_task(task_id)

    def claim_next_pending(self, worker_id: str = "") -> Optional[Task]:
        row = task_repo.claim_next_pending(worker_id=worker_id)
        return Task.from_dict(dict(row)) if row else None
