"""功能用例导出仓储接口（委托 cases DDD）。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class CaseExportRepository(Protocol):
    """功能用例导出协调接口。"""
    def export_cases(self, body: Dict[str, Any], kind: str) -> dict: ...
    def task_status(self) -> Optional[Dict[str, Any]]: ...
    def download_path(self, file_id: str) -> Optional[str]: ...
    def download_task_meta(self, file_id: str) -> Optional[Dict[str, Any]]: ...

__all__ = ["CaseExportRepository"]
