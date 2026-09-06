"""SLO（Service Level Objective）相关值对象。

  - SLOThreshold          单项阈值定义（metric / 上限 / 下限）
  - SLOValidationResult   一次 SLO 校验结果（passed / checks / details）

阈值与结果均为不可变值对象，满足「相等即属性全等」的领域约定。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.common.value_objects import ValueObject
from app.domain.performance.domain.value_objects.performance_metrics import (
    PerformanceMetrics,
)

# 允许作为 SLO 指标的数值字段（校验用，避免对任意属性放开）
_SLO_METRIC_FIELDS = {
    "total_time",
    "min_time",
    "max_time",
    "avg_time",
    "median_time",
    "p95_time",
    "stddev",
    "throughput",
    "peak_memory_mb",
    "cpu_time",
}


@dataclass(frozen=True)
class SLOThreshold(ValueObject):
    """单项 SLO 阈值定义。"""

    metric: str
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.metric not in _SLO_METRIC_FIELDS:
            raise ValueError(f"非法 SLO 指标 '{self.metric}'，仅支持 {sorted(_SLO_METRIC_FIELDS)}")
        object.__setattr__(self, "metric", self.metric)
        object.__setattr__(self, "description", self.description or "")

    def is_satisfied(self, metrics: PerformanceMetrics) -> bool:
        """判断当前指标是否满足该阈值。"""
        actual = getattr(metrics, self.metric, None)
        if actual is None:
            return False
        if self.max_value is not None and actual > self.max_value:
            return False
        if self.min_value is not None and actual < self.min_value:
            return False
        return True

    def bound(self) -> Optional[float]:
        """返回生效的边界值（上限优先）。"""
        return self.max_value if self.max_value is not None else self.min_value

    def operator(self) -> str:
        return "≤" if self.max_value is not None else "≥"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "max_value": self.max_value,
            "min_value": self.min_value,
            "description": self.description,
        }


@dataclass(frozen=True)
class SLOValidationResult(ValueObject):
    """一次 SLO 校验的结果。"""

    name: str
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "checks": [dict(c) for c in self.checks],
            "details": self.details,
        }

    def summary_line(self) -> str:
        status = "✅" if self.passed else "❌"
        return f"{status} SLO[{self.name}]: {self.details}"


__all__ = ["SLOThreshold", "SLOValidationResult"]
