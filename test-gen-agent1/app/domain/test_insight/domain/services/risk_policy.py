"""TestInsight 领域服务：风险分级策略。

将"复杂度分 + 覆盖缺口分 + 缺陷密度分"折算出的风险分，映射为
low / medium / high 三档，并给出回归建议。属无状态领域策略，
供风险评估用例复用，避免口径散落。
"""
from __future__ import annotations

from app.domain.test_insight.domain.value_objects.risk_level import (
    RiskLevel,
    RiskLevelEnum,
)

# 分档阈值
HIGH_THRESHOLD = 60.0
MEDIUM_THRESHOLD = 30.0


class RiskPolicy:
    """风险等级判定策略（无状态领域服务）。"""

    # 单项得分上限
    MAX_COMPLEXITY = 40.0
    MAX_COVERAGE_GAP = 30.0
    MAX_DEFECT_DENSITY = 30.0

    def classify(self, risk_score: float) -> RiskLevel:
        if risk_score >= HIGH_THRESHOLD:
            return RiskLevel(RiskLevelEnum.HIGH)
        if risk_score >= MEDIUM_THRESHOLD:
            return RiskLevel(RiskLevelEnum.MEDIUM)
        return RiskLevel(RiskLevelEnum.LOW)

    def recommendation(self, high_count: int) -> str:
        if high_count > 0:
            return "发布前请优先回归高风险模块，并补齐覆盖率缺口。"
        return "暂未发现高风险模块，建议保持常规回归节奏。"
