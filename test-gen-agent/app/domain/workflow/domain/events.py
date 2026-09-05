"""工作流状态领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class WorkflowStatusCreated(DomainEvent):
    def __init__(self, status_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=status_id)
        self.name = name
        self.operator = operator

class WorkflowStatusUpdated(DomainEvent):
    def __init__(self, status_id: str, operator: str = "system"):
        super().__init__(aggregate_id=status_id)
        self.operator = operator

class WorkflowStatusDeleted(DomainEvent):
    def __init__(self, status_id: str, operator: str = "system"):
        super().__init__(aggregate_id=status_id)
        self.operator = operator

__all__ = ["WorkflowStatusCreated", "WorkflowStatusUpdated", "WorkflowStatusDeleted"]
