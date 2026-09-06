"""性能测试应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由/图节点与领域层之间的用例编排入口；
  2. 承载「性能测试任务」用例的事务边界：加载聚合 → 执行领域命令 →
     保存聚合 → 发布领域事件；
  3. 提供一个 `run` 编排，把「实际跑基准（由 runner 承担，对接既有
     app/performance 引擎）」与「领域内 SLO 判定」串成一次完整流程；
  4. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
runner / repo 均由构造注入，便于测试替换（内存仓储 + 替身 runner）。
"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Protocol, runtime_checkable

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.performance.application.dto import (
    ConfigureThresholdsCommand,
    CreatePerformanceTestCommand,
    FailTestCommand,
    PerformanceListQuery,
    RecordResultCommand,
    SkipTestCommand,
    StartTestCommand,
)
from app.domain.performance.domain.entities.performance_test import PerformanceTest
from app.domain.performance.domain.repository import PerformanceRepository
from app.domain.performance.domain.value_objects.performance_metrics import (
    PerformanceMetrics,
)
from app.domain.performance.domain.value_objects.slo import SLOValidationResult

logger = logging.getLogger(__name__)


@runtime_checkable
class BenchmarkRunner(Protocol):
    """把被测可调用对象跑成领域性能指标（Port）。

    真实实现见基础设施层 `EngineBenchmarkRunner`（复用既有 app/performance
    引擎）；单测可注入替身 runner，避免依赖真实计时/内存采集。
    """

    def run(
        self,
        target: Callable[[], object],
        *,
        name: str,
        iterations: int = 100,
        warmup: int = 5,
    ) -> PerformanceMetrics: ...


class PerformanceAppService:
    """性能测试用例编排服务。"""

    def __init__(self, repo: PerformanceRepository = None, runner: Optional[BenchmarkRunner] = None):
        self._repo = repo
        self._runner = runner

    # ── 聚合级基础操作 ─────────────────────────────
    def create(self, cmd: CreatePerformanceTestCommand) -> dict:
        test = PerformanceTest(
            test_id=self._repo.next_id(),
            target_name=cmd.target_name,
            source_ref=cmd.source_ref,
            thresholds=cmd.thresholds,
        )
        self._repo.save(test)
        self._publish(test)
        return test.to_dict()

    def get(self, test_id: str) -> Optional[dict]:
        test = self._repo.find_by_id(test_id)
        return test.to_dict() if test else None

    def get_or_raise(self, test_id: str) -> dict:
        test = self._find_or_raise(test_id)
        return test.to_dict()

    def configure_thresholds(self, cmd: ConfigureThresholdsCommand) -> Optional[dict]:
        test = self._find_or_raise(cmd.test_id)
        test.set_thresholds(cmd.thresholds, cmd.operator)
        self._repo.update(test)
        self._publish(test)
        return test.to_dict()

    def start(self, cmd: StartTestCommand) -> Optional[dict]:
        test = self._find_or_raise(cmd.test_id)
        test.start(cmd.operator)
        self._repo.update(test)
        self._publish(test)
        return test.to_dict()

    def record_result(self, cmd: RecordResultCommand) -> Optional[dict]:
        test = self._find_or_raise(cmd.test_id)
        metrics = PerformanceMetrics.from_dict(cmd.metrics)
        slo_result = None
        if cmd.slo_result is not None:
            slo_result = SLOValidationResult(
                name=cmd.slo_result.get("name", metrics.name),
                passed=bool(cmd.slo_result.get("passed")),
                checks=list(cmd.slo_result.get("checks") or []),
                details=cmd.slo_result.get("details", ""),
            )
        test.record_result(metrics=metrics, slo_result=slo_result, operator=cmd.operator)
        self._repo.update(test)
        self._publish(test)
        return test.to_dict()

    def fail(self, cmd: FailTestCommand) -> Optional[dict]:
        test = self._find_or_raise(cmd.test_id)
        test.fail(cmd.reason, cmd.operator)
        self._repo.update(test)
        self._publish(test)
        return test.to_dict()

    def skip(self, cmd: SkipTestCommand) -> Optional[dict]:
        test = self._find_or_raise(cmd.test_id)
        test.skip(cmd.reason, cmd.operator)
        self._repo.update(test)
        self._publish(test)
        return test.to_dict()

    def delete(self, test_id: str) -> bool:
        if not self._repo.delete(test_id):
            raise AggregateNotFound(f"性能测试任务不存在: {test_id}")
        return True

    # ── 查询（读模型）──────────────────────────────
    def list(self, query: PerformanceListQuery) -> dict:
        items, total = self._repo.list(
            status=query.status,
            target_name=query.target_name,
            limit=query.limit,
            offset=query.offset,
        )
        return {"list": [t.to_dict() for t in items], "total": total}

    # ── 完整执行编排 ───────────────────────────────
    def run(
        self,
        *,
        test_id: str,
        target: Callable[[], object],
        iterations: int = 100,
        warmup: int = 5,
        operator: str = "system",
        auto_start: bool = True,
    ) -> dict:
        """对被测目标执行一次完整性能测试并判定 SLO 达标。

        流程：加载任务 → start(如需) → runner 跑基准得指标 → record_result。
        """
        if self._runner is None:
            raise RuntimeError("未注入 runner，无法执行实际基准测试")
        test = self._find_or_raise(test_id)
        if auto_start and test.status.value.value == "pending":
            test.start(operator)
            self._repo.update(test)
        metrics = self._runner.run(
            target, name=test.target_name, iterations=iterations, warmup=warmup
        )
        test.record_result(metrics=metrics, operator=operator)
        self._repo.update(test)
        self._publish(test)
        return test.to_dict()

    # ── 内部助手 ───────────────────────────────────
    def _find_or_raise(self, test_id: str) -> PerformanceTest:
        test = self._repo.find_by_id(test_id)
        if test is None:
            raise AggregateNotFound(f"性能测试任务不存在: {test_id}")
        return test

    def _publish(self, test: PerformanceTest) -> None:
        events = test.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


__all__ = ["PerformanceAppService", "BenchmarkRunner"]
