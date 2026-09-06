# -*- coding: utf-8 -*-
"""功能用例导出业务层（functional_export 域 DDD 接入 · 阶段 C 薄门面）。

功能用例导出（Excel/XMind）业务已收敛到 functional_export 域 DDD 应用服务
`export_app_service`（见 `app/domain/functional_export/`，聚合根
`CaseExportJob`）。本模块收敛为对 DDD 应用门面的**薄委托门面**，仅保留既有
模块级函数签名以兼容 `functional_cases_extra.py` / `functional_cases.py` 等
调用方，导出目录/文件路径/任务登记语义与重构前一致（DDD 门面底层复用既有
`CaseRepo` + `export_task` 域进程内任务注册表），对外 API 零回归、可回滚。

> 推荐调用方直接使用 `export_app_service`；本模块仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.functional_export.application.dto import ExportCasesCommand
from app.domain.functional_export.application.export_app_service import (
    export_app_service as _ddd,
)


def export_cases_excel(body: Dict[str, Any]) -> Dict[str, Any]:
    """按给定参数导出功能用例为 Excel(CSV)。"""
    return _ddd.export_cases(ExportCasesCommand(body=body, kind="excel"))


def export_cases_xmind(body: Dict[str, Any]) -> Dict[str, Any]:
    """按给定参数导出功能用例为 XMind(JSON)。"""
    return _ddd.export_cases(ExportCasesCommand(body=body, kind="xmind"))


def task_status() -> Optional[Dict[str, Any]]:
    """当前是否有「进行中」的导出任务（供 check/export-task）。"""
    return _ddd.task_status()


def download_path(file_id: str) -> Optional[str]:
    """返回文件 ID 对应的导出文件路径（无则 None）。"""
    return _ddd.download_path(file_id)


def download_task_meta(file_id: str) -> Optional[Dict[str, Any]]:
    """返回某 fileId 导出任务的元信息（用于下载时取原始文件名）。"""
    return _ddd.download_task_meta(file_id)


__all__ = [
    "export_cases_excel", "export_cases_xmind",
    "task_status", "download_path", "download_task_meta",
]
