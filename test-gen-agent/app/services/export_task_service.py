# app/services/export_task_service.py
"""功能用例导出任务注册表（export_task 域 DDD 接入 · 阶段 C 薄门面）。

导出任务数据访问已收敛到 export_task 域 DDD 应用服务
`export_task_app_service`（见 `app/domain/export_task/`）。本模块收敛为对
DDD 应用门面的**薄委托门面**，仅保留既有模块级函数签名以兼容
`functional_export_service`、`websocket` 等调用方，返回结构与重构前一致
（DDD 门面底层复用同一进程内任务注册表，读写语义零变化），对外零回归、可回滚。

> 推荐调用方直接使用 `export_task_app_service`；本模块仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.export_task.application.dto import (
    GetTaskCommand,
    RegisterTaskCommand,
    RemoveTaskCommand,
)
from app.domain.export_task.application.export_task_app_service import (
    export_task_app_service as _ddd,
)


def register_task(file_id: str, task_id: str, path: str, filename: str,
                  count: int, is_successful: bool = True) -> Dict[str, Any]:
    """登记一个已完成（或正在）的导出任务。"""
    return _ddd.register(RegisterTaskCommand(
        file_id=file_id, task_id=task_id, path=path, filename=filename,
        count=count, is_successful=is_successful,
    ))


def get_task(file_id: str) -> Optional[Dict[str, Any]]:
    """按 fileId 读取导出任务。"""
    return _ddd.get(GetTaskCommand(file_id=file_id))


def remove_task(file_id: str) -> None:
    """移除指定 fileId 的导出任务。"""
    _ddd.remove(RemoveTaskCommand(file_id=file_id))


def active_task() -> Optional[Dict[str, Any]]:
    """当前是否有进行中的导出任务（用于 check/export-task）。"""
    return _ddd.latest()


def wait_task(file_id: str, timeout: float = 20.0, interval: float = 0.2) -> Optional[Dict[str, Any]]:
    """轮询等待某 fileId 的导出任务就绪。"""
    return _ddd.wait_task(file_id, timeout=timeout, interval=interval)


__all__ = ["register_task", "get_task", "remove_task", "active_task", "wait_task"]
