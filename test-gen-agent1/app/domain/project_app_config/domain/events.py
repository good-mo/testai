"""项目应用配置领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ProjectConfigSaved(DomainEvent):
    """项目配置已保存。"""
    def __init__(self, project_id: str, module: str, key: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=f"{project_id}:{module}:{key}")
        self.project_id = project_id
        self.module = module
        self.key = key
        self.operator = operator

__all__ = ["ProjectConfigSaved"]
