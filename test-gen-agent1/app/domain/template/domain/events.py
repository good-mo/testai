"""模板领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class TemplateCreated(DomainEvent):
    """模板已创建。"""

    def __init__(self, template_id: str, scene: str = "FUNCTIONAL",
                 scope_type: str = "PROJECT", scope_id: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.scene = scene
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.operator = operator


class TemplateUpdated(DomainEvent):
    """模板已更新。"""

    def __init__(self, template_id: str, action: str = "meta",
                 operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.action = action
        self.operator = operator


class TemplateDeleted(DomainEvent):
    """模板已删除。"""

    def __init__(self, template_id: str, operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.operator = operator


class TemplateDefaultSet(DomainEvent):
    """模板被设为默认。"""

    def __init__(self, template_id: str, scope_type: str = "PROJECT",
                 scope_id: str = "", scene: str = ""):
        super().__init__(aggregate_id=template_id)
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.scene = scene


__all__ = [
    "TemplateCreated", "TemplateUpdated", "TemplateDeleted", "TemplateDefaultSet",
]
