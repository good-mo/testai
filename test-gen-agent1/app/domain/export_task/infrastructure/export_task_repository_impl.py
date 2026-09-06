"""导出任务聚合仓储实现（Adapter / Anti-Corruption Layer）。

将 `ExportTask` 聚合与进程内任务注册表对接。任务注册表为内存 dict，
与既有 `app.services.export_task_service` 同一份存储语义，但不再反向依赖
services 层（避免 domain → services → domain 循环依赖风险）。
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from app.domain.export_task.domain.entities.export_task import ExportTask

_lock = threading.RLock()
# fileId -> {fileId, taskId, path, filename, count, created_at, is_successful}
_ACTIVE_TASKS: Dict[str, Dict[str, Any]] = {}


def _register_task(file_id: str, task_id: str, path: str, filename: str,
                   count: int, is_successful: bool = True) -> Dict[str, Any]:
    """登记一个导出任务记录。"""
    task = {
        "fileId": file_id,
        "taskId": task_id,
        "path": path,
        "filename": filename,
        "count": count,
        "created_at": time.time(),
        "is_successful": is_successful,
    }
    with _lock:
        _ACTIVE_TASKS[file_id] = task
    return task


def _get_task(file_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _ACTIVE_TASKS.get(file_id)


def _remove_task(file_id: str) -> None:
    with _lock:
        _ACTIVE_TASKS.pop(file_id, None)


def _active_task() -> Optional[Dict[str, Any]]:
    """当前是否有进行中的导出任务。"""
    with _lock:
        if not _ACTIVE_TASKS:
            return None
        latest = max(_ACTIVE_TASKS.values(), key=lambda t: t.get("created_at", 0))
        return latest


class ExportTaskRepoAdapter:
    """将进程内注册表封装为面向 ExportTask 的仓储。"""

    def register(self, task: ExportTask) -> ExportTask:
        _register_task(
            task.id.value, task.task_id, task.path,
            task.filename, task.count, task.is_successful,
        )
        return task

    def get(self, file_id: str) -> Optional[ExportTask]:
        data = _get_task(file_id)
        return ExportTask.from_dict(data) if data else None

    def remove(self, file_id: str) -> None:
        _remove_task(file_id)

    def latest(self) -> Optional[ExportTask]:
        data = _active_task()
        return ExportTask.from_dict(data) if data else None
