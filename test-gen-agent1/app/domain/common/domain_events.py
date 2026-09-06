"""领域事件与事件总线。

领域事件用于在聚合之间、聚合与外部（应用层/集成层）之间解耦传播
业务事实。事件在聚合根的方法中被记录，事务提交后由应用层统一发布。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class DomainEvent:
    """领域事件基类。"""

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    occurred_at: float = field(default_factory=time.time)
    aggregate_id: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": type(self).__name__,
            "occurred_at": self.occurred_at,
            "aggregate_id": self.aggregate_id,
        }


Handler = Callable[[DomainEvent], Any]


class EventBus:
    """进程内同步领域事件总线。

    简单起见实现为进程内同步派发；真实分布式中可替换为消息中间件适配器。
    用法：
        @event_bus.on("TestCaseUpdated")
        def notify(event): ...
        event_bus.dispatch(event)
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = {}

    def on(self, event_type: str):
        """注册事件处理器（装饰器）。event_type 可为类名或事件类型对象。"""

        def wrapper(handler: Handler) -> Handler:
            self._handlers.setdefault(event_type, []).append(handler)
            return handler

        return wrapper

    def register(self, event_type: str, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        """同步派发事件给所有订阅者。"""
        event_type = type(event).__name__
        for handler in list(self._handlers.get(event_type, [])):
            handler(event)

    def clear(self) -> None:
        self._handlers.clear()


# 全局单例总线（进程内）
event_bus = EventBus()


__all__ = ["DomainEvent", "EventBus", "Handler", "event_bus"]
