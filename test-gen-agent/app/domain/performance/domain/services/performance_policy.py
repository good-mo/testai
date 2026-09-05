"""性能测试领域服务：SLO 校验策略与默认基线。

将「如何依据一组 SLO 阈值判定一批性能指标是否达标」这一规则抽成
无状态的纯领域策略，供聚合 `record_result` 与应用层复用，规则单一出处。
同时提供面向被测函数的默认 SLO 基线（可覆盖）。
"""
from __future__ import annotations

from typing import List

from app.domain.performance.domain.value_objects.performance_metrics import (
    PerformanceMetrics,
)
from app.domain.performance.domain.value_objects.slo import (
    SLOThreshold,
    SLOValidationResult,
)


class PerformancePolicy:
    """性能测试领域策略（无状态）。"""

    @staticmethod
    def validate_slo(
        name: str,
        metrics: PerformanceMetrics,
        thresholds: List[SLOThreshold],
    ) -> SLOValidationResult:
        """针对一组 SLO 阈值校验性能指标，产出结构化校验结果。

        - 无阈值时默认通过（不设约束即不拦截）。
        - 任一阈值不满足 → passed=False。
        """
        checks = []
        all_passed = True
        for t in thresholds or []:
            ok = t.is_satisfied(metrics)
            if not ok:
                all_passed = False
            actual = getattr(metrics, t.metric, None)
            bound = t.bound()
            checks.append(
                {
                    "metric": t.metric,
                    "actual": round(actual, 4) if actual is not None else None,
                    "threshold": bound,
                    "operator": t.operator(),
                    "passed": ok,
                    "description": t.description,
                }
            )

        detail = "; ".join(
            f"{c['metric']}={c['actual']}{c['operator']}{c['threshold']}"
            if c["threshold"] is not None
            else c["metric"]
            for c in checks
        )
        return SLOValidationResult(
            name=name,
            passed=all_passed,
            checks=checks,
            details=f"{detail} → {'通过' if all_passed else '不达标'}",
        )

    @staticmethod
    def default_slo_thresholds() -> List[SLOThreshold]:
        """企业级默认 SLO 基线（面向被测函数，可按需覆盖）。"""
        return [
            SLOThreshold(
                metric="p95_time", max_value=1.0, description="P95 响应时间 ≤ 1s"
            ),
            SLOThreshold(
                metric="avg_time", max_value=0.5, description="平均响应时间 ≤ 500ms"
            ),
            SLOThreshold(
                metric="throughput", min_value=10.0, description="吞吐量 ≥ 10 次/秒"
            ),
            SLOThreshold(
                metric="peak_memory_mb",
                max_value=512.0,
                description="峰值内存 ≤ 512MB",
            ),
        ]


__all__ = ["PerformancePolicy"]
