"""误报规则领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class FakeErrorCreated(DomainEvent):
    """误报规则已创建。"""
    def __init__(self, rule_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=rule_id)
        self.name = name
        self.operator = operator

class FakeErrorUpdated(DomainEvent):
    """误报规则已更新。"""
    def __init__(self, rule_id: str, operator: str = "system"):
        super().__init__(aggregate_id=rule_id)
        self.operator = operator

class FakeErrorDeleted(DomainEvent):
    """误报规则已删除。"""
    def __init__(self, rule_id: str, operator: str = "system"):
        super().__init__(aggregate_id=rule_id)
        self.operator = operator

__all__ = ["FakeErrorCreated", "FakeErrorUpdated", "FakeErrorDeleted"]
