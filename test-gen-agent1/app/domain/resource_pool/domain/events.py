"""资源池领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ResourcePoolCreated(DomainEvent):
    def __init__(self, pool_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=pool_id)
        self.name = name
        self.operator = operator

class ResourcePoolUpdated(DomainEvent):
    def __init__(self, pool_id: str, operator: str = "system"):
        super().__init__(aggregate_id=pool_id)
        self.operator = operator

class ResourcePoolDeleted(DomainEvent):
    def __init__(self, pool_id: str, operator: str = "system"):
        super().__init__(aggregate_id=pool_id)
        self.operator = operator

__all__ = ["ResourcePoolCreated", "ResourcePoolUpdated", "ResourcePoolDeleted"]
