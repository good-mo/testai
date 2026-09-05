"""功能用例导出领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class CaseExportTriggered(DomainEvent):
    def __init__(self, export_type: str = "", count: int = 0,
                 operator: str = "system"):
        super().__init__()
        self.export_type = export_type
        self.count = count
        self.operator = operator

__all__ = ["CaseExportTriggered"]
