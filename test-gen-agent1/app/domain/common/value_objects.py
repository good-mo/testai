"""值对象基类。

值对象无独立标识，由其属性集合定义；两个值对象相等当且仅当属性全等。
值对象是不可变的（frozen），应通过其内部方法派生新值而非原地修改。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """值对象不可变基类。"""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValueObject):
            return NotImplemented
        return type(self) is type(other) and self._as_tuple() == other._as_tuple()

    def __hash__(self) -> int:
        return hash((type(self), self._as_tuple()))

    def _as_tuple(self) -> tuple:
        return tuple(
            getattr(self, f.name)
            for f in self.__dataclass_fields__.values()  # type: ignore[attr-defined]
            if f.name != "_as_tuple"
        )

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{type(self).__name__}({attrs})"
