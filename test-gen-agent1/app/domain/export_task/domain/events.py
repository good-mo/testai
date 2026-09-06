"""导出任务领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ExportTaskRegistered(DomainEvent):
    def __init__(self, file_id: str, filename: str = "", operator: str = "system"):
        super().__init__(aggregate_id=file_id)
        self.filename = filename
        self.operator = operator

class ExportTaskCompleted(DomainEvent):
    def __init__(self, file_id: str, filename: str = "", count: int = 0,
                 operator: str = "system"):
        super().__init__(aggregate_id=file_id)
        self.filename = filename
        self.count = count
        self.operator = operator

__all__ = ["ExportTaskRegistered", "ExportTaskCompleted"]
