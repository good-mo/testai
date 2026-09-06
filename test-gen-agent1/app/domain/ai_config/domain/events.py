"""AI 配置领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class AiConfigCreated(DomainEvent):
    """AI 配置已创建。"""

    def __init__(self, config_id: str, scope: str, owner: str = "",
                 project_id: str = "", operator: str = "system"):
        super().__init__(aggregate_id=config_id)
        self.scope = scope
        self.owner = owner
        self.project_id = project_id
        self.operator = operator


class AiConfigUpdated(DomainEvent):
    """AI 配置已更新。"""

    def __init__(self, config_id: str, scope: str, operator: str = "system"):
        super().__init__(aggregate_id=config_id)
        self.scope = scope
        self.operator = operator


class AiConfigDeleted(DomainEvent):
    """AI 配置已删除。"""

    def __init__(self, config_id: str, operator: str = "system"):
        super().__init__(aggregate_id=config_id)
        self.operator = operator


__all__ = ["AiConfigCreated", "AiConfigUpdated", "AiConfigDeleted"]
