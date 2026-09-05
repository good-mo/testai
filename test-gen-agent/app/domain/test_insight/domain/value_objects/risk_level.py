"""风险等级值对象。

用于风险预警：把"复杂度 + 覆盖缺口 + 缺陷密度"折算出的风险分
映射为 low / medium / high 三档，供领域策略与上层展示使用。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class RiskLevelEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def label(self) -> str:
        return {RiskLevelEnum.LOW: "低", RiskLevelEnum.MEDIUM: "中", RiskLevelEnum.HIGH: "高"}[self]


VALID: Set[str] = {e.value for e in RiskLevelEnum}


@dataclass(frozen=True)
class RiskLevel(ValueObject):
    """风险等级值对象。"""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.value if isinstance(self.value, RiskLevelEnum) else self.value
        v = str(raw).strip().lower()
        if v not in VALID:
            raise DomainValidationError(
                f"非法风险等级 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def enum(self) -> RiskLevelEnum:
        return RiskLevelEnum(self.value)

    @property
    def label(self) -> str:
        return RiskLevelEnum(self.value).label

    def __str__(self) -> str:
        return self.value
