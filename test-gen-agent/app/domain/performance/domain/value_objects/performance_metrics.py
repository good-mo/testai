"""性能指标值对象 PerformanceMetrics。

聚合一次基准测试采样后的性能画像（不可变）。由 `from_timings` 从
逐次单次耗时列表聚合而来，也可由基础设施层从既有 `app.performance`
引擎产生的字典/对象转换。

字段含义与既有引擎保持一致，便于防腐层双向转换：
  - 时间类：total / min / max / avg / median / p95 / stddev / cpu
  - 吞吐量：throughput 次/秒
  - 资源：peak_memory_mb 峰值内存
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median, pstdev
from typing import Any, Dict, List, Mapping, Optional

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


@dataclass(frozen=True)
class PerformanceMetrics(ValueObject):
    """性能指标不可变值对象。"""

    name: str
    total_time: float = 0.0
    iterations: int = 0
    min_time: float = 0.0
    max_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    p95_time: float = 0.0
    stddev: float = 0.0
    throughput: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_time: float = 0.0
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (self.name or "").strip():
            raise DomainValidationError("性能指标必须带有名称 name")
        object.__setattr__(self, "name", (self.name or "").strip())
        object.__setattr__(self, "extra", dict(self.extra or {}))

    @classmethod
    def from_timings(
        cls,
        *,
        name: str,
        timings: List[float],
        peak_memory_mb: float = 0.0,
        cpu_time: float = 0.0,
        iterations: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "PerformanceMetrics":
        """从逐次耗时列表聚合出指标（空列表返回零值指标）。"""
        if not timings:
            return cls(name=name, iterations=iterations or 0)
        n = iterations if iterations is not None else len(timings)
        total = sum(timings)
        sorted_t = sorted(timings)
        p95_idx = max(0, int(round(0.95 * len(sorted_t))) - 1)
        return cls(
            name=name,
            total_time=total,
            iterations=int(n),
            min_time=min(timings),
            max_time=max(timings),
            avg_time=total / len(timings),
            median_time=median(timings),
            p95_time=sorted_t[p95_idx],
            stddev=pstdev(timings) if len(timings) > 1 else 0.0,
            throughput=(n / total) if total > 0 else 0.0,
            peak_memory_mb=peak_memory_mb,
            cpu_time=cpu_time,
            extra=extra or {},
        )

    def _round(self, value: float, digits: int) -> float:
        return round(value, digits)

    def to_dict(self) -> Dict[str, Any]:
        """导出为可持久化 / 可序列化的普通字典。"""
        return {
            "name": self.name,
            "total_time": self._round(self.total_time, 4),
            "iterations": self.iterations,
            "min_time": self._round(self.min_time, 4),
            "max_time": self._round(self.max_time, 4),
            "avg_time": self._round(self.avg_time, 4),
            "median_time": self._round(self.median_time, 4),
            "p95_time": self._round(self.p95_time, 4),
            "stddev": self._round(self.stddev, 4),
            "throughput": self._round(self.throughput, 2),
            "peak_memory_mb": self._round(self.peak_memory_mb, 2),
            "cpu_time": self._round(self.cpu_time, 4),
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PerformanceMetrics":
        """从持久化字典重建（容忍缺失字段，使用引擎字段名）。"""
        if data is None:
            data = {}
        return cls(
            name=str(data.get("name", "")),
            total_time=float(data.get("total_time", 0.0) or 0.0),
            iterations=int(data.get("iterations", 0) or 0),
            min_time=float(data.get("min_time", 0.0) or 0.0),
            max_time=float(data.get("max_time", 0.0) or 0.0),
            avg_time=float(data.get("avg_time", 0.0) or 0.0),
            median_time=float(data.get("median_time", 0.0) or 0.0),
            p95_time=float(data.get("p95_time", 0.0) or 0.0),
            stddev=float(data.get("stddev", 0.0) or 0.0),
            throughput=float(data.get("throughput", 0.0) or 0.0),
            peak_memory_mb=float(data.get("peak_memory_mb", 0.0) or 0.0),
            cpu_time=float(data.get("cpu_time", 0.0) or 0.0),
            extra=dict(data.get("extra") or {}),
        )

    def summary_line(self) -> str:
        """人类可读的一行摘要。"""
        return (
            f"⚡ {self.name}: "
            f"avg={self.avg_time:.3f}s p95={self.p95_time:.3f}s "
            f"min={self.min_time:.3f}s max={self.max_time:.3f}s "
            f"tps={self.throughput:.2f} mem={self.peak_memory_mb:.1f}MB "
            f"iter={self.iterations}"
        )


__all__ = ["PerformanceMetrics"]
