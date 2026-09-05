"""系统管理领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class AdminOrganizationEnabled(DomainEvent):
    def __init__(self, org_id: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.operator = operator

class AdminOrganizationDisabled(DomainEvent):
    def __init__(self, org_id: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.operator = operator

__all__ = ["AdminOrganizationEnabled", "AdminOrganizationDisabled"]
