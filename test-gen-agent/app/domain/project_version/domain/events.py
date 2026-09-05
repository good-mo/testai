"""项目版本领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ProjectVersionCreated(DomainEvent):
    def __init__(self, version_id: str, name: str = "", project_id: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=version_id)
        self.name = name
        self.project_id = project_id
        self.operator = operator

class ProjectVersionUpdated(DomainEvent):
    def __init__(self, version_id: str, operator: str = "system"):
        super().__init__(aggregate_id=version_id)
        self.operator = operator

class ProjectVersionStatusChanged(DomainEvent):
    def __init__(self, version_id: str, enable: bool, operator: str = "system"):
        super().__init__(aggregate_id=version_id)
        self.enable = enable
        self.operator = operator

__all__ = ["ProjectVersionCreated", "ProjectVersionUpdated", "ProjectVersionStatusChanged"]
