"""覆盖率门禁值对象。

封装单次覆盖率报告，并提供"是否达标/是否出错的判定"，
供应用层与领域策略复用，避免把百分比判定散落各处。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from app.domain.common.value_objects import ValueObject


@dataclass(frozen=True)
class CoverageGate(ValueObject):
    """覆盖率门禁：按给定阈值判定报告是否达标。

    报告字段与 run_records.coverage_report / graph.coverage_report 对齐：
      - coverage_pct           综合覆盖率
      - line_coverage_pct      行覆盖率
      - passed_threshold       是否已达标（graph 输出）
      - error                  覆盖率分析是否出错
    """

    report: Dict = None
    threshold: float = 80.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "report", dict(self.report or {}))
        object.__setattr__(self, "threshold", float(self.threshold))

    @property
    def has_error(self) -> bool:
        return bool((self.report or {}).get("error"))

    @property
    def passed_threshold(self) -> bool:
        """判定是否达标：优先采纳报告自身 passed_threshold，否则按阈值自算。"""
        report = self.report or {}
        explicit = report.get("passed_threshold")
        if explicit is not None:
            return bool(explicit)
        pct = float(report.get("line_coverage_pct") or report.get("coverage_pct") or 0.0)
        return pct >= self.threshold

    @property
    def line_coverage_pct(self) -> float:
        report = self.report or {}
        return float(report.get("line_coverage_pct") or 0.0)

    @property
    def coverage_pct(self) -> float:
        report = self.report or {}
        return float(report.get("coverage_pct") or 0.0)

    def human_summary(self) -> str:
        report = self.report or {}
        return report.get("human_summary") or (
            f"行覆盖率 {self.line_coverage_pct}%"
            + ("（达标）" if self.passed_threshold else f"（低于 {self.threshold}%）")
        )


__all__ = ["CoverageGate"]
