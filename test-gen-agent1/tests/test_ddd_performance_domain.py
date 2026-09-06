"""DDD 性能测试域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：值对象守卫、状态机、SLO 判定、聚合命令。
  2. 应用服务全链路（内存仓储 + 替身 runner）。
  3. 与既有 app/performance 引擎的防腐层桥接（EngineBenchmarkRunner）。
"""
import uuid

import pytest

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainValidationError,
)
from app.domain.performance.application.dto import (
    ConfigureThresholdsCommand,
    CreatePerformanceTestCommand,
    FailTestCommand,
    PerformanceListQuery,
    RecordResultCommand,
    SkipTestCommand,
    StartTestCommand,
)
from app.domain.performance.application.performance_app_service import (
    PerformanceAppService,
)
from app.domain.performance.domain.entities.performance_test import PerformanceTest
from app.domain.performance.domain.exceptions import InvalidPerformanceStatusTransition
from app.domain.performance.domain.value_objects.performance_metrics import (
    PerformanceMetrics,
)
from app.domain.performance.domain.value_objects.slo import (
    SLOThreshold,
)
from app.domain.performance.domain.value_objects.status import (
    PerformanceStatus,
)
from app.domain.performance.infrastructure.performance_repository_impl import (
    EngineBenchmarkRunner,
    InMemoryPerformanceRepository,
)

TAG = "dddperf"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _test(**kw):
    kw.setdefault("test_id", _mk())
    kw.setdefault("target_name", "target_fn")
    return PerformanceTest(**kw)


def _metrics(avg=0.1, p95=0.2, tps=100, name="target_fn"):
    timings = [avg] * 100
    m = PerformanceMetrics.from_timings(name=name, timings=timings)
    m = PerformanceMetrics(
        name=name,
        total_time=m.total_time,
        iterations=100,
        min_time=avg,
        max_time=avg,
        avg_time=avg,
        median_time=avg,
        p95_time=p95,
        stddev=0.0,
        throughput=tps,
        peak_memory_mb=10.0,
        cpu_time=0.1,
    )
    return m


# ═══════════════════════════════════════════════════════════
# 一、值对象
# ═══════════════════════════════════════════════════════════
class TestMetricsValueObject:
    def test_from_timings_basic(self):
        m = PerformanceMetrics.from_timings(name="t", timings=[0.01, 0.02, 0.03] * 34)
        assert m.name == "t"
        assert m.avg_time == pytest.approx(0.02)
        assert m.iterations == 102

    def test_empty_timings(self):
        m = PerformanceMetrics.from_timings(name="t", timings=[])
        assert m.avg_time == 0

    def test_name_required(self):
        with pytest.raises(DomainValidationError):
            PerformanceMetrics.from_timings(name="", timings=[0.1])

    def test_roundtrip_dict(self):
        m = _metrics()
        d = m.to_dict()
        r = PerformanceMetrics.from_dict(d)
        # to_dict 对数值做了四舍五入，逐字段比较语义等价
        for f in ("name", "iterations", "min_time", "max_time", "avg_time",
                  "median_time", "p95_time", "stddev", "throughput",
                  "peak_memory_mb", "cpu_time"):
            assert getattr(r, f) == pytest.approx(getattr(m, f), abs=0.001)

    def test_summary_line(self):
        assert "target_fn" in _metrics().summary_line()
        assert "avg=" in _metrics().summary_line()


class TestSLOValueObject:
    def test_threshold_pass(self):
        assert SLOThreshold(metric="p95_time", max_value=1.0).is_satisfied(_metrics())

    def test_threshold_fail(self):
        assert not SLOThreshold(metric="avg_time", max_value=0.05).is_satisfied(_metrics(avg=0.1))

    def test_throughput_min(self):
        assert SLOThreshold(metric="throughput", min_value=50).is_satisfied(_metrics(tps=100))
        assert not SLOThreshold(metric="throughput", min_value=500).is_satisfied(_metrics(tps=100))

    def test_invalid_metric_rejected(self):
        with pytest.raises(ValueError):
            SLOThreshold(metric="no_such", max_value=1.0)


class TestStatusValueObject:
    def test_normalize(self):
        assert str(PerformanceStatus("PENDING")) == "pending"
        assert str(PerformanceStatus("")) == "pending"

    def test_invalid(self):
        with pytest.raises(DomainValidationError):
            PerformanceStatus("exploded")

    def test_transition_matrix(self):
        assert PerformanceStatus("pending").can_transition_to(PerformanceStatus("running"))
        assert PerformanceStatus("running").can_transition_to(PerformanceStatus("passed"))
        assert not PerformanceStatus("passed").can_transition_to(PerformanceStatus("running"))


# ═══════════════════════════════════════════════════════════
# 二、聚合
# ═══════════════════════════════════════════════════════════
class TestAggregate:
    def test_create_default_pending(self):
        t = _test()
        assert str(t.status) == "pending"
        assert not t.passed
        assert not t.is_terminal

    def test_target_required(self):
        with pytest.raises(DomainValidationError):
            _test(target_name="")

    def test_start(self):
        t = _test()
        t.start("u")
        assert str(t.status) == "running"

    def test_start_from_running_rejected(self):
        t = _test()
        t.start("u")
        with pytest.raises(InvalidPerformanceStatusTransition):
            t.start("u")

    def test_record_result_pass(self):
        t = _test()
        t.start("u")
        t.record_result(metrics=_metrics(), operator="u")
        assert t.passed
        assert str(t.status) == "passed"
        assert t.slo_result is None or t.slo_result.passed  # 无阈值默认通过
        assert t.metrics is not None

    def test_record_result_fail(self):
        t = _test(thresholds=[{"metric": "avg_time", "max_value": 0.05}])
        t.start("u")
        t.record_result(metrics=_metrics(avg=0.1), operator="u")
        assert not t.passed
        assert str(t.status) == "failed"
        assert t.reason

    def test_terminal_no_rerun(self):
        t = _test()
        t.start("u")
        t.record_result(metrics=_metrics(), operator="u")  # passed
        with pytest.raises(InvalidPerformanceStatusTransition):
            t.fail("x", "u")
        with pytest.raises(InvalidPerformanceStatusTransition):
            t.skip("x", "u")

    def test_fail(self):
        t = _test()
        t.start("u")
        t.fail("boom", "u")
        assert str(t.status) == "failed"
        assert t.reason == "boom"

    def test_fail_without_start_rejected(self):
        t = _test()
        with pytest.raises(InvalidPerformanceStatusTransition):
            t.fail("x", "u")

    def test_skip(self):
        t = _test()
        t.skip("no need", "u")
        assert str(t.status) == "skipped"
        assert t.is_terminal

    def test_metric_name_mismatch_rejected(self):
        t = _test(target_name="a")
        t.start("u")
        m = PerformanceMetrics.from_timings(name="b", timings=[0.1])
        with pytest.raises(DomainValidationError):
            t.record_result(metrics=m, operator="u")

    def test_set_thresholds_before_run(self):
        t = _test()
        t.set_thresholds([{"metric": "avg_time", "max_value": 0.2}], "u")
        assert len(t.thresholds) == 1
        t.start("u")
        with pytest.raises(InvalidPerformanceStatusTransition):
            t.set_thresholds([], "u")

    def test_to_from_dict_roundtrip(self):
        t = _test(thresholds=[{"metric": "avg_time", "max_value": 0.2}])
        t.start("u")
        t.record_result(metrics=_metrics(avg=0.1), operator="u")
        t2 = PerformanceTest.from_dict(t.to_dict())
        assert t2.to_dict() == t.to_dict()
        assert t2.passed == t.passed


# ═══════════════════════════════════════════════════════════
# 三、应用服务（内存仓储 + 替身 runner）
# ═══════════════════════════════════════════════════════════
class _StubRunner:
    """替身 runner：不真实计时，直接返回给定指标。"""

    def __init__(self, metrics=None, fail=False):
        self._metrics = metrics or _metrics()
        self._fail = fail

    def run(self, target, *, name, iterations=100, warmup=5):
        if self._fail:
            raise RuntimeError("benchmark boom")
        base = self._metrics.to_dict()
        return PerformanceMetrics.from_dict({**base, "name": name})


def _make_service(**runner_kw):
    repo = InMemoryPerformanceRepository()
    svc = PerformanceAppService(repo=repo, runner=_StubRunner(**runner_kw))
    return svc, repo


class TestAppService:
    def test_create_and_get(self):
        svc, _ = _make_service()
        created = svc.create(
            CreatePerformanceTestCommand(target_name="fn", source_ref="mod.py::fn")
        )
        assert created["target_name"] == "fn"
        assert created["status"] == "pending"
        got = svc.get(created["id"])
        assert got["id"] == created["id"]

    def test_get_missing_raises(self):
        svc, _ = _make_service()
        with pytest.raises(AggregateNotFound):
            svc.get_or_raise("nope")

    def test_full_run(self):
        svc, _ = _make_service()
        test = svc.create(CreatePerformanceTestCommand(target_name="target_fn"))
        out = svc.run(test_id=test["id"], target=lambda: sum(range(10)))
        assert out["status"] == "passed"
        assert out["metrics"] is not None

    def test_full_run_violates_slo(self):
        svc, repo = _make_service(metrics=_metrics(avg=0.9, p95=1.5))
        test = svc.create(
            CreatePerformanceTestCommand(
                target_name="target_fn",
                thresholds=[{"metric": "avg_time", "max_value": 0.5}],
            )
        )
        out = svc.run(test_id=test["id"], target=lambda: sum(range(10)))
        assert out["status"] == "failed"
        assert not out["passed"]

    def test_record_result_via_cmd(self):
        svc, _ = _make_service()
        test = svc.create(CreatePerformanceTestCommand(target_name="target_fn"))
        svc.start(StartTestCommand(test_id=test["id"]))
        out = svc.record_result(
            RecordResultCommand(test_id=test["id"], metrics=_metrics().to_dict())
        )
        assert out["status"] == "passed"

    def test_fail_skip(self):
        svc, _ = _make_service()
        t = svc.create(CreatePerformanceTestCommand(target_name="fn"))
        svc.start(StartTestCommand(test_id=t["id"]))
        out = svc.fail(FailTestCommand(test_id=t["id"], reason="boom"))
        assert out["status"] == "failed"

        t2 = svc.create(CreatePerformanceTestCommand(target_name="fn2"))
        out2 = svc.skip(SkipTestCommand(test_id=t2["id"], reason="skip"))
        assert out2["status"] == "skipped"

    def test_list_filter(self):
        svc, _ = _make_service()
        a = svc.create(CreatePerformanceTestCommand(target_name="alpha"))
        b = svc.create(CreatePerformanceTestCommand(target_name="beta"))
        svc.start(StartTestCommand(test_id=a["id"]))
        svc.record_result(
            RecordResultCommand(test_id=a["id"], metrics=_metrics(name="alpha").to_dict())
        )

        res = svc.list(PerformanceListQuery(status="passed"))
        assert any(x["id"] == a["id"] for x in res["list"])
        assert not any(x["id"] == b["id"] for x in res["list"])

    def test_configure_thresholds(self):
        svc, _ = _make_service()
        t = svc.create(CreatePerformanceTestCommand(target_name="fn"))
        out = svc.configure_thresholds(
            ConfigureThresholdsCommand(
                test_id=t["id"], thresholds=[{"metric": "p95_time", "max_value": 0.3}]
            )
        )
        assert len(out["thresholds"]) == 1

    def test_delete(self):
        svc, _ = _make_service()
        t = svc.create(CreatePerformanceTestCommand(target_name="fn"))
        assert svc.delete(t["id"]) is True
        with pytest.raises(AggregateNotFound):
            svc.delete(t["id"])

    def test_run_without_runner_raises(self):
        repo = InMemoryPerformanceRepository()
        svc = PerformanceAppService(repo=repo, runner=None)
        t = svc.create(CreatePerformanceTestCommand(target_name="fn"))
        with pytest.raises(RuntimeError):
            svc.run(test_id=t["id"], target=lambda: 1)


# ═══════════════════════════════════════════════════════════
# 四、与既有 app/performance 引擎桥接（防腐层）
# ═══════════════════════════════════════════════════════════
class TestEngineBridge:
    def test_engine_runner_produces_domain_metrics(self):
        runner = EngineBenchmarkRunner()

        def _fn():
            total = 0
            for i in range(1000):
                total += i
            return total

        m = runner.run(_fn, name="target_fn", iterations=20, warmup=2)
        assert isinstance(m, PerformanceMetrics)
        assert m.name == "target_fn"
        assert m.iterations > 0

    def test_engine_runner_full_slo(self):
        runner = EngineBenchmarkRunner()
        svc = PerformanceAppService(
            repo=InMemoryPerformanceRepository(), runner=runner
        )
        t = svc.create(
            CreatePerformanceTestCommand(
                target_name="target_fn",
                thresholds=[{"metric": "p95_time", "max_value": 2.0}],
            )
        )

        def _fn():
            return sum(range(100))

        out = svc.run(test_id=t["id"], target=_fn, iterations=10, warmup=1)
        assert out["status"] in ("passed", "failed")
        assert out["metrics"] is not None
