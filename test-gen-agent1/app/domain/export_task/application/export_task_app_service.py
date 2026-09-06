"""导出任务应用服务。"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.export_task.application.dto import (
    GetTaskCommand,
    RegisterTaskCommand,
    RemoveTaskCommand,
)
from app.domain.export_task.domain.entities.export_task import ExportTask
from app.domain.export_task.infrastructure.export_task_repository_impl import (
    ExportTaskRepoAdapter,
)


class ExportTaskAppService:
    """导出任务用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or ExportTaskRepoAdapter()

    def register(self, cmd: RegisterTaskCommand) -> dict:
        task = ExportTask(
            file_id=cmd.file_id,
            task_id=cmd.task_id or str(uuid.uuid4()),
            path=cmd.path,
            filename=cmd.filename,
            count=cmd.count,
            is_successful=cmd.is_successful,
            _created=True,
        )
        saved = self._repo.register(task)
        return saved.to_dict()

    def get(self, cmd: GetTaskCommand) -> Optional[dict]:
        task = self._repo.get(cmd.file_id)
        return task.to_dict() if task else None

    def remove(self, cmd: RemoveTaskCommand) -> None:
        self._repo.remove(cmd.file_id)

    def latest(self) -> Optional[dict]:
        task = self._repo.latest()
        return task.to_dict() if task else None

    def wait_task(self, file_id: str, timeout: float = 20.0, interval: float = 0.2):
        """轮询等待某 fileId 的导出任务就绪。"""
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            task = self._repo.get(file_id)
            if task:
                return task.to_dict()
            time.sleep(interval)
        return None


export_task_app_service = ExportTaskAppService()
