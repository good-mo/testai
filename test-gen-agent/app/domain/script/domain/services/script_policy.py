"""脚本领域策略：健康度计算与状态判定（纯逻辑，无状态）。"""
from __future__ import annotations


def calc_health_score(total: int, success_count: int, fail_count: int,
                      previous_score: float, last_success: bool) -> float:
    """计算健康度评分（0-100）。"""
    success_rate = success_count / total if total > 0 else 1.0
    base_score = success_rate * 100.0
    penalty = 0.0
    if not last_success:
        penalty += 10.0
    if fail_count >= 3:
        penalty += 5.0 * min(fail_count, 10)
    score = max(0, min(100, base_score - penalty))
    smoothed = previous_score * 0.7 + score * 0.3
    return round(max(0, min(100, smoothed)), 1)


def determine_status(health_score: float) -> str:
    """根据健康度评分判定状态。"""
    if health_score >= 85:
        return "healthy"
    elif health_score >= 60:
        return "unstable"
    return "degraded"


__all__ = ["calc_health_score", "determine_status"]
