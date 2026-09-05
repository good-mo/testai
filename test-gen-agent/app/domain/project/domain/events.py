"""项目领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，
进而驱动审计日志、通知、索引等副作用（跨聚合/跨域解耦）。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ProjectCreated(DomainEvent):
    def __init__(self, project_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.name = name
        self.operator = operator


class ProjectRenamed(DomainEvent):
    def __init__(self, project_id: str, old_name: str, new_name: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.old_name = old_name
        self.new_name = new_name
        self.operator = operator


class ProjectInfoChanged(DomainEvent):
    def __init__(self, project_id: str, field: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.field = field
        self.operator = operator


class ProjectStatusChanged(DomainEvent):
    def __init__(self, project_id: str, old_status: str, new_status: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class ProjectArchived(DomainEvent):
    def __init__(self, project_id: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.operator = operator


class ProjectActivated(DomainEvent):
    def __init__(self, project_id: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.operator = operator


class ProjectSoftDeleted(DomainEvent):
    def __init__(self, project_id: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.operator = operator


class ProjectRestored(DomainEvent):
    def __init__(self, project_id: str, operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.operator = operator


class ProjectMemberAdded(DomainEvent):
    def __init__(self, project_id: str, user_id: str = "", role: str = "member",
                 operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.user_id = user_id
        self.role = role
        self.operator = operator


class ProjectMemberRemoved(DomainEvent):
    def __init__(self, project_id: str, user_id: str = "", operator: str = "system"):
        super().__init__(aggregate_id=project_id)
        self.user_id = user_id
        self.operator = operator
