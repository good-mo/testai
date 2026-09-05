"""功能用例导出仓储实现（Adapter / Anti-Corruption Layer）。

不再反向依赖 `app.services.functional_export_service`（避免 domain → services
→ domain 循环依赖风险）。直接对接：
  - app.repositories.case_repo.CaseRepo（用例数据 + 文件序列化）
  - 进程内导出任务注册表（与 export_task 上下文共享语义）
文件写入目标目录与既有 `output/functional_case_export` 保持一致。
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from app.domain.export_task.domain.entities.export_task import ExportTask
from app.domain.export_task.infrastructure.export_task_repository_impl import (
    ExportTaskRepoAdapter,
)
from app.repositories.case_repo import CaseRepo

# 导出目录（仓库根/output/functional_case_export）
_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
EXPORT_DIR = os.path.join(_BASE, "output", "functional_case_export")
os.makedirs(EXPORT_DIR, exist_ok=True)


def _resolve_export_cases(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """按导出参数挑选功能用例（与 /functional/case/page 同源）。"""
    all_cases = CaseRepo.list_cases(limit=10000)
    func_cases = []
    for c in all_cases:
        meta = c.get("metadata") or {}
        if isinstance(meta, str):
            try:
                import json
                meta = json.loads(meta)
            except Exception:
                meta = {}
        test_type = c.get("test_type", "") or meta.get("test_type", "")
        if test_type and test_type != "functional":
            continue
        func_cases.append(c)

    select_all = bool(body.get("selectAll"))
    select_ids = body.get("selectIds") or []
    exclude_ids = body.get("excludeIds") or []
    module_ids = body.get("moduleIds") or []

    result = func_cases
    if module_ids:
        result = [
            c for c in result
            if (c.get("module_id") or (c.get("metadata") or {}).get("module_id", "")) in module_ids
        ]
    if select_all:
        excluded = set(exclude_ids or [])
        result = [c for c in result if c.get("id") not in excluded]
    elif select_ids:
        id_set = set(select_ids)
        result = [c for c in result if c.get("id") in id_set]
    return result


def _do_export(body: Dict[str, Any], kind: str) -> Dict[str, Any]:
    """执行导出并登记任务，返回 {fileId, taskId, count}。"""
    cases = _resolve_export_cases(body)
    file_id = body.get("fileId") or str(uuid.uuid4())
    task_id = str(uuid.uuid4())

    ext = "csv" if kind == "excel" else "json"
    filename = f"功能用例_{int(time.time())}.{ext}"
    path = os.path.join(EXPORT_DIR, f"{file_id}.{ext}")

    if kind == "excel":
        try:
            data = CaseRepo.export_excel(cases)
        except Exception:
            data = "\ufeffID,标题,描述,类型,优先级,状态,标签\n".encode("utf-8")
    else:
        try:
            content = CaseRepo.export_mindmap(cases)
            data = content.encode("utf-8")
        except Exception:
            import json
            data = json.dumps({"root": [], "cases": len(cases)},
                              ensure_ascii=False).encode("utf-8")

    with open(path, "wb") as f:
        f.write(data)

    task_adapter = ExportTaskRepoAdapter()
    task = ExportTask(
        file_id=file_id,
        task_id=task_id,
        path=path,
        filename=filename,
        count=len(cases),
        is_successful=True,
        _created=True,
    )
    task_adapter.register(task)
    return {"fileId": file_id, "taskId": task_id, "count": len(cases)}


class ExportRepoAdapter:
    """将 CaseExportRepository 委托给低层存储实现。"""

    def __init__(self):
        self._task_repo = ExportTaskRepoAdapter()

    def export_cases(self, body: Dict[str, Any], kind: str) -> dict:
        if kind == "excel":
            return _do_export(body, "excel")
        return _do_export(body, "xmind")

    def task_status(self) -> Optional[Dict[str, Any]]:
        """当前是否有「进行中」的导出任务（同步即时完成，返回 None）。"""
        return None

    def download_path(self, file_id: str) -> Optional[str]:
        """返回文件 ID 对应的导出文件路径（无则 None）。"""
        if not file_id:
            return None
        for ext in ("csv", "json"):
            path = os.path.join(EXPORT_DIR, f"{file_id}.{ext}")
            if os.path.exists(path):
                return path
        return None

    def download_task_meta(self, file_id: str) -> Optional[Dict[str, Any]]:
        """返回某 fileId 导出任务的元信息（用于下载时取原始文件名）。"""
        task = self._task_repo.get(file_id)
        if task:
            return task.to_dict()
        return None
