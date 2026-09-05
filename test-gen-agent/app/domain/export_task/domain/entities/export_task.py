"""导出任务聚合根 ExportTask。"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.export_task.domain.events import ExportTaskCompleted, ExportTaskRegistered


class ExportTask(AggregateRoot):
    """功能用例导出任务聚合根。"""

    def __init__(
        self,
        *,
        file_id: str,
        task_id: str = "",
        path: str = "",
        filename: str = "",
        count: int = 0,
        is_successful: bool = True,
        created_at: Optional[float] = None,
        _created: bool = False,
    ):
        if not file_id:
            raise DomainValidationError("文件 ID 不能为空")
        self.id = Identifier.of(file_id)
        self._task_id = task_id or ""
        self._path = path or ""
        self._filename = filename or ""
        self._count = int(count or 0)
        self._is_successful = bool(is_successful)
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(ExportTaskRegistered(file_id, self._filename))

    @property
    def task_id(self) -> str:
        return self._task_id
    @property
    def path(self) -> str:
        return self._path
    @property
    def filename(self) -> str:
        return self._filename
    @property
    def count(self) -> int:
        return self._count
    @property
    def is_successful(self) -> bool:
        return self._is_successful
    @property
    def created_at(self) -> float:
        return self._created_at

    def mark_success(self, count: int = 0) -> None:
        """标记导出成功。"""
        self._is_successful = True
        if count:
            self._count = count
        self.record_event(ExportTaskCompleted(self.id.value, self._filename, self._count))

    def mark_failed(self) -> None:
        """标记导出失败。"""
        self._is_successful = False

    def to_dict(self) -> dict:
        return {
            "fileId": self.id.value,
            "taskId": self._task_id,
            "path": self._path,
            "filename": self._filename,
            "count": self._count,
            "created_at": self._created_at,
            "is_successful": self._is_successful,
        }

    @staticmethod
    def from_dict(data: dict) -> "ExportTask":
        return ExportTask(
            file_id=str(data.get("fileId") or data.get("file_id") or ""),
            task_id=data.get("taskId") or data.get("task_id") or "",
            path=data.get("path", ""),
            filename=data.get("filename", ""),
            count=data.get("count", 0),
            is_successful=bool(data.get("is_successful", True)),
            created_at=data.get("created_at"),
        )
