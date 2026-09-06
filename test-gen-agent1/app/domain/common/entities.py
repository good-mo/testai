"""实体与聚合根基类。

DDD 中「实体」具备唯一标识与生命周期；「聚合根」是事务一致性的边界，
外部只能经由聚合根访问聚合内的实体/值对象，聚合内部的不变量由聚合根
统一守护（守护方法是 apply 业务命令而非直接 setter）。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:  # pragma: no cover
    from app.domain.common.domain_events import DomainEvent


@dataclass
class Identifier:
    """通用标识值对象：封装主键类型与生成。

    现实持久层主键为字符串（uuid/雪花），此处统一以 str 承载，便于
    与现有 sqlite 存储对接；如需数值主键可传 primitive。
    """

    value: str

    @classmethod
    def generate(cls) -> "Identifier":
        return cls(str(uuid.uuid4().hex[:12]))

    @classmethod
    def of(cls, value: Any) -> "Identifier":
        return cls(str(value))

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Identifier):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class Entity:
    """实体基类：按标识判断相等性，而非按属性。

    生命周期内可能被修改多次，但标识恒定。
    """

    id: Identifier
    # 收集自上次快照以来的领域事件（供应用层落库后发布）
    _domain_events: List["DomainEvent"] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))

    # ── 领域事件注册 ────────────────────────────────
    def record_event(self, event: "DomainEvent") -> None:
        """将领域事件暂存到实体，等待提交后统一发布。"""
        self._domain_events.append(event)

    def pull_domain_events(self) -> List["DomainEvent"]:
        """取出并清空本实体暂存的领域事件。"""
        events, self._domain_events = self._domain_events, []
        return events


class AggregateRoot(Entity):
    """聚合根基类。

    聚合是事务一致性的最小单元，聚合内所有修改都必须经由聚合根方法
    触发；聚合根负责校验不变量，并将产生的结果以领域事件形式向外传播。
    """

    # 版本号乐观锁（可选）
    version: int = 0

    def to_dict(self) -> dict:
        """导出为可持久化/可序列化的普通字典。"""
        raise NotImplementedError
