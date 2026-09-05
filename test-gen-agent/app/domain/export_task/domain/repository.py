"""导出任务聚合仓储接口。"""
from __future__ import annotations

from typing import Optional, Protocol

from app.domain.export_task.domain.entities.export_task import ExportTask


class ExportTaskRepository(Protocol):
    def register(self, task: ExportTask) -> ExportTask: ...
    def get(self, file_id: str) -> Optional[ExportTask]: ...
    def remove(self, file_id: str) -> None: ...
    def latest(self) -> Optional[ExportTask]: ...

__all__ = ["ExportTaskRepository"]
