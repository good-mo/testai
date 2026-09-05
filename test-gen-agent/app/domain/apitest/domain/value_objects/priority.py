"""接口用例优先级值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject

VALID: Set[str] = {"P0", "P1", "P2", "P3"}
ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass(frozen=True)
class Priority(ValueObject):
    """接口用例优先级值对象：仅允许 P0~P3。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).upper()
        if v not in VALID:
            raise DomainValidationError(
                f"非法优先级 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def weight(self) -> int:
        return ORDER[self.value]

    def __str__(self) -> str:
        return self.value
