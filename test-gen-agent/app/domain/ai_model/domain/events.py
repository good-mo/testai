"""AI 模型源领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class AiModelCreated(DomainEvent):
    """模型源已创建。"""

    def __init__(self, model_id: str, name: str = "", provider: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=model_id)
        self.name = name
        self.provider = provider
        self.operator = operator


class AiModelUpdated(DomainEvent):
    """模型源已更新。"""

    def __init__(self, model_id: str, operator: str = "system"):
        super().__init__(aggregate_id=model_id)
        self.operator = operator


class AiModelDeleted(DomainEvent):
    """模型源已删除。"""

    def __init__(self, model_id: str, operator: str = "system"):
        super().__init__(aggregate_id=model_id)
        self.operator = operator


__all__ = ["AiModelCreated", "AiModelUpdated", "AiModelDeleted"]
