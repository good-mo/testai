"""功能用例导出聚合根 CaseExportJob。

功能用例导出（functional_export）限界上下文中的核心概念：一次功能用例
导出作业。记录导出的格式、筛选参数、结果 fileId 等。任务注册/文件路径等
持久信息由 export_task 上下文托管，本聚合负责导出作业的业务状态与触发语义。

聚合边界内的组成：
  - CaseExportJob（聚合根：job_id + 导出格式 + 参数摘要 + 结果状态）
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.functional_export.domain.events import CaseExportTriggered

# 导出格式常量
EXPORT_KIND_EXCEL = "excel"
EXPORT_KIND_XMIND = "xmind"


class CaseExportJob(AggregateRoot):
    """功能用例导出作业聚合根。"""

    def __init__(
        self,
        *,
        job_id: str = "",
        kind: str = EXPORT_KIND_EXCEL,
        body: Optional[Dict[str, Any]] = None,
        file_id: str = "",
        status: str = "pending",
        count: int = 0,
        operator: str = "system",
        created_at: Optional[float] = None,
        _created: bool = False,
    ):
        if kind not in (EXPORT_KIND_EXCEL, EXPORT_KIND_XMIND):
            raise DomainValidationError(f"非法导出格式: {kind}")
        if not job_id:
            job_id = uuid.uuid4().hex[:12]
        self.id = Identifier.of(job_id)
        self._kind = kind
        self._body = dict(body or {})
        self._file_id = file_id or ""
        self._status = status or "pending"
        self._count = int(count or 0)
        self._operator = operator or "system"
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(CaseExportTriggered(
                export_type=self._kind, count=self._count, operator=self._operator))

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def body(self) -> Dict[str, Any]:
        return dict(self._body)

    @property
    def file_id(self) -> str:
        return self._file_id

    @property
    def status(self) -> str:
        return self._status

    @property
    def count(self) -> int:
        return self._count

    @property
    def operator(self) -> str:
        return self._operator

    @property
    def created_at(self) -> float:
        return self._created_at

    # ── 业务命令 ─────────────────────────────────────
    def mark_running(self) -> None:
        """标记导出进行中。"""
        self._status = "running"

    def mark_completed(self, file_id: str = "", count: int = 0) -> None:
        """标记导出完成。"""
        if file_id:
            self._file_id = file_id
        if count:
            self._count = int(count)
        self._status = "completed"

    def mark_failed(self) -> None:
        """标记导出失败。"""
        self._status = "failed"

    # ── 持久化 / 序列化 ─────────────────────────────
    def to_dict(self) -> dict:
        return {
            "jobId": self.id.value,
            "id": self.id.value,
            "kind": self._kind,
            "body": self._body,
            "fileId": self._file_id,
            "status": self._status,
            "count": self._count,
            "operator": self._operator,
            "createdAt": self._created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "CaseExportJob":
        return CaseExportJob(
            job_id=str(data.get("jobId") or data.get("job_id") or data.get("id") or ""),
            kind=data.get("kind", EXPORT_KIND_EXCEL),
            body=data.get("body") or {},
            file_id=data.get("fileId") or data.get("file_id") or "",
            status=data.get("status", "pending"),
            count=data.get("count", 0),
            operator=data.get("operator", "system"),
            created_at=data.get("createdAt") or data.get("created_at"),
        )


__all__ = ["CaseExportJob", "EXPORT_KIND_EXCEL", "EXPORT_KIND_XMIND"]
