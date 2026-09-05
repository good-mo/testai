"""用户视图领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class UserViewCreated(DomainEvent):
    def __init__(self, view_id: str, name: str = "", view_type: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=view_id)
        self.name = name
        self.view_type = view_type
        self.operator = operator

class UserViewUpdated(DomainEvent):
    def __init__(self, view_id: str, operator: str = "system"):
        super().__init__(aggregate_id=view_id)
        self.operator = operator

class UserViewDeleted(DomainEvent):
    def __init__(self, view_id: str, operator: str = "system"):
        super().__init__(aggregate_id=view_id)
        self.operator = operator

__all__ = ["UserViewCreated", "UserViewUpdated", "UserViewDeleted"]
