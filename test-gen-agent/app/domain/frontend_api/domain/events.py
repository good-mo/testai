"""前端兼容领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class FrontendApiImported(DomainEvent):
    def __init__(self, source: str = "", operator: str = "system"):
        super().__init__()
        self.source = source
        self.operator = operator

__all__ = ["FrontendApiImported"]
