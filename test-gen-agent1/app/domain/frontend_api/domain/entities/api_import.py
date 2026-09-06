"""前端兼容 API 导入聚合根 ApiImport。

前端兼容（frontend_api）限界上下文中的核心概念：一次 API 测试数据的
导入操作记录。前端可经 Postman / Swagger 将接口定义等批量导入系统，
本聚合记录一次导入的来源与统计信息，供查询与审计。

聚合边界内的组成：
  - ApiImport（聚合根：import_id + 来源 + 导入统计 + 状态）
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.frontend_api.domain.events import FrontendApiImported

# 导入来源常量
SOURCE_POSTMAN = "postman"
SOURCE_SWAGGER = "swagger"
SOURCE_AUTO = "auto"


class ApiImport(AggregateRoot):
    """前端兼容 API 数据导入操作聚合根。"""

    def __init__(
        self,
        *,
        import_id: str = "",
        source: str = SOURCE_AUTO,
        imported: int = 0,
        failed: int = 0,
        status: str = "done",
        operator: str = "system",
        created_at: Optional[float] = None,
        _created: bool = False,
    ):
        if source not in (SOURCE_POSTMAN, SOURCE_SWAGGER, SOURCE_AUTO):
            raise DomainValidationError(f"非法导入来源: {source}")
        if not import_id:
            import_id = uuid.uuid4().hex[:12]
        self.id = Identifier.of(import_id)
        self._source = source
        self._imported = int(imported or 0)
        self._failed = int(failed or 0)
        self._status = status or "done"
        self._operator = operator or "system"
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(FrontendApiImported(self._source, self._operator))

    @property
    def source(self) -> str:
        return self._source

    @property
    def imported(self) -> int:
        return self._imported

    @property
    def failed(self) -> int:
        return self._failed

    @property
    def status(self) -> str:
        return self._status

    @property
    def operator(self) -> str:
        return self._operator

    @property
    def created_at(self) -> float:
        return self._created_at

    # ── 业务命令 ─────────────────────────────────────
    def mark_completed(self, imported: int = 0, failed: int = 0) -> None:
        """标记导入完成。"""
        self._imported = int(imported or 0)
        self._failed = int(failed or 0)
        self._status = "done"

    def mark_failed(self, error_count: int = 0) -> None:
        """标记导入失败。"""
        self._failed = int(error_count or 0)
        self._status = "failed"

    # ── 持久化 / 序列化 ─────────────────────────────
    def to_dict(self) -> dict:
        return {
            "importId": self.id.value,
            "id": self.id.value,
            "source": self._source,
            "imported": self._imported,
            "failed": self._failed,
            "status": self._status,
            "operator": self._operator,
            "createdAt": self._created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ApiImport":
        return ApiImport(
            import_id=str(data.get("importId") or data.get("import_id") or data.get("id") or ""),
            source=data.get("source", SOURCE_AUTO),
            imported=data.get("imported", 0),
            failed=data.get("failed", 0),
            status=data.get("status", "done"),
            operator=data.get("operator", "system"),
            created_at=data.get("createdAt") or data.get("created_at"),
        )


__all__ = ["ApiImport", "SOURCE_POSTMAN", "SOURCE_SWAGGER", "SOURCE_AUTO"]
