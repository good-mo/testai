"""调试领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class DebugItemCreated(DomainEvent):
    """调试项已创建。"""
    def __init__(self, debug_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=debug_id)
        self.name = name
        self.operator = operator

class DebugItemUpdated(DomainEvent):
    """调试项已更新。"""
    def __init__(self, debug_id: str, operator: str = "system"):
        super().__init__(aggregate_id=debug_id)
        self.operator = operator

class DebugItemDeleted(DomainEvent):
    """调试项已删除。"""
    def __init__(self, debug_id: str, operator: str = "system"):
        super().__init__(aggregate_id=debug_id)
        self.operator = operator

__all__ = ["DebugItemCreated", "DebugItemUpdated", "DebugItemDeleted"]
