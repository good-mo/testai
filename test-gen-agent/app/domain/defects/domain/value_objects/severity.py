"""缺陷严重程度值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class SeverityEnum(str, Enum):
    BLOCKER = "blocker"        # 阻断
    CRITICAL = "critical"      # 严重
    MAJOR = "major"            # 主要（默认）
    MINOR = "minor"            # 次要
    TRIVIAL = "trivial"        # 轻微


VALID: Set[str] = {e.value for e in SeverityEnum}
# 严重度排序权重：数值越小越严重
ORDER = {
    SeverityEnum.BLOCKER.value: 0,
    SeverityEnum.CRITICAL.value: 1,
    SeverityEnum.MAJOR.value: 2,
    SeverityEnum.MINOR.value: 3,
    SeverityEnum.TRIVIAL.value: 4,
}


@dataclass(frozen=True)
class Severity(ValueObject):
    """缺陷严重程度值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).lower()
        if v not in VALID:
            raise DomainValidationError(
                f"非法缺陷严重程度 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def weight(self) -> int:
        return ORDER[self.value]

    def __str__(self) -> str:
        return self.value
