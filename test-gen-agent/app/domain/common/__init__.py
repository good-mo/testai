"""DDD 通用原语。

提供领域建模所需的基础基类：
  - Entity / AggregateRoot：实体与聚合根
  - ValueObject：值对象
  - DomainEvent + EventBus：领域事件与分发
  - DomainException：领域异常基类
"""
from app.domain.common.domain_events import DomainEvent, EventBus, event_bus
from app.domain.common.entities import (
    AggregateRoot,
    Entity,
    Identifier,
)
from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)
from app.domain.common.value_objects import ValueObject

__all__ = [
    "AggregateRoot",
    "Entity",
    "Identifier",
    "ValueObject",
    "DomainEvent",
    "EventBus",
    "event_bus",
    "DomainException",
    "DomainValidationError",
    "InvariantViolation",
    "AggregateNotFound",
]
