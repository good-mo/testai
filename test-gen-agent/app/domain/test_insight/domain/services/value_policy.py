"""TestInsight 领域服务：价值量化与事故规避策略。

基于缺陷严重度权重与覆盖率，把测试活动量化为可感知价值
（发现缺陷价值、避免线上事故、价值分），回答"测试的价值在哪"。
属无状态领域策略，与具体存储解耦。
"""
from __future__ import annotations

from app.domain.test_insight.domain.value_objects.risk_level import RiskLevelEnum

# 缺陷严重度 → "避免线上事故"价值权重（可配置）
SEVERITY_WEIGHT = {
    "blocker": 100.0,
    "critical": 50.0,
    "major": 10.0,
    "minor": 1.0,
}
# 高影响严重度（视为避免一次线上事故）
HIGH_IMPACT_SEVERITIES = ("blocker", "critical")
# 价值分折算：缺陷价值上限 50 分、覆盖率上限 50 分
DEFECT_SCORE_CAP = 50.0
COVERAGE_SCORE_CAP = 50.0
VALUE_SCORE_CAP = 100.0
# 覆盖良好判定阈值
COVERAGE_GOOD_THRESHOLD = 80.0

# 风险等级 → 排序权重（便于下游汇总高低危清单）
RISK_ORDER = {
    RiskLevelEnum.HIGH.value: 2,
    RiskLevelEnum.MEDIUM.value: 1,
    RiskLevelEnum.LOW.value: 0,
}


class ValuePolicy:
    """价值量化策略（无状态领域服务）。"""

    def severity_weight(self, severity: str) -> float:
        return SEVERITY_WEIGHT.get(severity, 0.0)

    def is_high_impact(self, severity: str) -> bool:
        return severity in HIGH_IMPACT_SEVERITIES

    def value_score(self, defect_value: float, avg_coverage: float) -> float:
        """综合价值分（0-100）：缺陷权重分 + 平均覆盖率折算分。"""
        defect_score = min(defect_value, DEFECT_SCORE_CAP) * 2
        coverage_score = min(avg_coverage, 100.0) * 0.5
        return round(min(defect_score + coverage_score, VALUE_SCORE_CAP), 1)

    def coverage_gap(self, avg_coverage: float) -> int:
        """覆盖率缺口分（未测/低覆盖时放大风险）。"""
        if avg_coverage <= 0:
            return 20
        return min(30, max(0, 30 - int(avg_coverage * 0.3)))
