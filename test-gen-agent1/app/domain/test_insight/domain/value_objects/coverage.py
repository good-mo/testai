"""测试覆盖率值对象。

将覆盖率约束在 [0, 100] 的合法百分比区间，并提供"是否达标"等
派生判断（默认 80% 为覆盖良好阈值）。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject

# 覆盖率良好判定阈值（百分比）
COVERAGE_GOOD_THRESHOLD = 80.0


@dataclass(frozen=True)
class Coverage(ValueObject):
    """覆盖率值对象（百分比 0~100）。"""

    value: float

    def __post_init__(self) -> None:
        try:
            v = float(self.value)
        except (TypeError, ValueError):
            raise DomainValidationError(f"非法覆盖率 '{self.value}'，应为数值")
        if v < 0 or v > 100:
            raise DomainValidationError(f"覆盖率 '{self.value}' 超出 [0,100] 区间")
        object.__setattr__(self, "value", round(v, 1))

    @property
    def is_good(self) -> bool:
        return self.value >= COVERAGE_GOOD_THRESHOLD

    def __str__(self) -> str:
        return f"{self.value:g}"


# 0 覆盖率常量
COVERAGE_ZERO = Coverage(0.0)
