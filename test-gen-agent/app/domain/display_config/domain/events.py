"""展示配置领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class DisplayConfigUpdated(DomainEvent):
    """展示配置已更新。"""
    def __init__(self, param_key: str, operator: str = "system"):
        super().__init__(aggregate_id=param_key)
        self.operator = operator

__all__ = ["DisplayConfigUpdated"]
