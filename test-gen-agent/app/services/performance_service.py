# app/services/performance_service.py
"""性能测试业务逻辑层（performance 域 DDD 接入 · 薄委托门面）。

性能基准与 SLO 判定规则已收拢到 performance 域领域层
（`app/domain/performance/`：状态机、指标聚合、SLO 判定、聚合命令），
本四层 Service 作为「既有 LangGraph / 引擎入口」与 DDD 应用服务之间的
**接入门面**：把一批被测目标翻译成领域 `PerformanceTest`，经
`PerformanceAppService` + 真实 `EngineBenchmarkRunner` 跑完整个生命周期，
再汇总为与既有 `app/performance` 输出一致的 `performance_report` 结构。

> 保持对外契约与 `run_performance_tests` 一致（可回滚）；领域内不变量
> （状态迁移、指标名一致性、SLO 达标判定）由 DDD 领域层单一守护。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from app.config import settings
from app.domain.performance.application.dto import CreatePerformanceTestCommand
from app.domain.performance.application.performance_app_service import (
    PerformanceAppService,
)
from app.domain.performance.domain.services.performance_policy import PerformancePolicy
from app.domain.performance.infrastructure.performance_repository_impl import (
    EngineBenchmarkRunner,
    InMemoryPerformanceRepository,
)

logger = logging.getLogger(__name__)


class PerformanceService:
    """性能测试服务（performance 域 DDD 薄门面）。

    用法：对一组被测目标执行完整性能基准 + SLO 校验，产出
    `performance_report`（结构与既有 summarize_benchmarks 一致）。
    """

    def __init__(
        self,
        *,
        default_iterations: Optional[int] = None,
        default_warmup: Optional[int] = None,
    ):
        self._iterations = default_iterations if default_iterations is not None else settings.perf_iterations
        self._warmup = default_warmup if default_warmup is not None else settings.perf_warmup

    # ── 对外：跑一批被测目标并汇总为 performance_report ─────────
    def run_for_targets(
        self,
        targets: List[Dict[str, Any]],
        *,
        source_ref: str = "",
        iterations: Optional[int] = None,
        warmup: Optional[int] = None,
        operator: str = "system",
    ) -> Dict[str, Any]:
        """对提取出的被测目标逐个经 DDD 域执行基准 + SLO 判定并汇总。

        Args:
            targets: [{"name": func_name, "callable": <可调用>, "params": {...}}]
            source_ref: 被测文件/来源标识。
            iterations / warmup: 采样/预热次数（默认取配置或构造注入）。

        Returns:
            与既有 summarize_benchmarks 兼容的 performance_report 字典：
            {overall_passed, total_benchmarks, passed, failed, benchmarks, summary}
        """
        iterations = iterations or self._iterations
        warmup = warmup or self._warmup

        results: List[Dict[str, Any]] = []
        for t in targets or []:
            name = t.get("name", "")
            func = t.get("callable")
            if not name or not callable(func):
                continue
            try:
                callable_obj = _build_callable(func, t.get("params") or {})
            except Exception as e:  # pragma: no cover - 构造失败不应中断批次
                logger.warning("构造基准调用失败 [%s]: %s", name, e)
                callable_obj = func

            # 每次为目标建独立领域任务：走 DDD 完整生命周期（start→跑基准→SLO 判定）
            app_svc = PerformanceAppService(
                repo=InMemoryPerformanceRepository(),
                runner=EngineBenchmarkRunner(
                    default_iterations=iterations, default_warmup=warmup
                ),
            )
            thresholds = [
                t.to_dict() for t in PerformancePolicy.default_slo_thresholds()
            ]
            created = app_svc.create(
                CreatePerformanceTestCommand(
                    target_name=name,
                    source_ref=source_ref,
                    thresholds=thresholds,
                    operator=operator,
                )
            )
            test = app_svc.run(
                test_id=created["id"],
                target=callable_obj,
                iterations=iterations,
                warmup=warmup,
                operator=operator,
            )
            results.append(self._test_to_benchmark(test))

        return self._summarize(results)

    # ── 内部：领域任务 → 兼容 benchmark 条目 ─────────────────────
    @staticmethod
    def _test_to_benchmark(test: Dict[str, Any]) -> Dict[str, Any]:
        """把 DDD PerformanceTest.to_dict 归一为 legacy BenchmarkResult 形状。"""
        return {
            "name": test.get("target_name", ""),
            "metrics": test.get("metrics"),
            "slo": test.get("slo_result"),
            "passed": bool(test.get("passed", False)),
            "status": test.get("status", ""),
        }

    @staticmethod
    def _summarize(benchmarks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """汇总结果（与 summarize_benchmarks 兼容口径）。"""
        total = len(benchmarks)
        passed = sum(1 for b in benchmarks if b.get("passed"))
        failed = total - passed
        overall_passed = passed == total and total > 0
        summary_lines = []
        for b in benchmarks:
            metrics = b.get("metrics") or {}
            name = b.get("name", "")
            if isinstance(metrics, dict):
                summary_lines.append(
                    f"⚡ {name}: avg={metrics.get('avg_time', 0):.3f}s "
                    f"p95={metrics.get('p95_time', 0):.3f}s "
                    f"tps={metrics.get('throughput', 0):.2f}"
                )
            else:
                summary_lines.append(f"⚡ {name}")
        return {
            "overall_passed": overall_passed,
            "total_benchmarks": total,
            "passed": passed,
            "failed": failed,
            "benchmarks": benchmarks,
            "summary": "\n".join(summary_lines),
        }


def _build_callable(func: Callable[..., Any], params: Dict[str, Any]) -> Callable[[], Any]:
    """把函数与默认参数打包为无参可调用对象。"""
    if not params:
        return lambda: func()
    return lambda: func(**params)


# 模块级单例门面（沿用既有 service 模块惯例）
performance_service = PerformanceService()

__all__ = ["PerformanceService", "performance_service"]
