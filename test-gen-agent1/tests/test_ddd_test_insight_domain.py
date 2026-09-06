"""DDD TestInsight 测试洞察域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：值对象守卫、聚合不变量、领域服务策略。
  2. 应用服务全链路（对接真实 trace.db 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.test_insight.application.dto import RecordTraceCommand, TraceListQuery
from app.domain.test_insight.application.test_insight_app_service import (
    test_insight_app_service,
)
from app.domain.test_insight.domain.entities.trace_run import TraceRun
from app.domain.test_insight.domain.services.risk_policy import RiskPolicy
from app.domain.test_insight.domain.services.value_policy import ValuePolicy
from app.domain.test_insight.domain.value_objects.attribution import (
    Attribution,
    AttributionEnum,
)
from app.domain.test_insight.domain.value_objects.coverage import Coverage
from app.domain.test_insight.domain.value_objects.risk_level import RiskLevel, RiskLevelEnum
from app.domain.test_insight.domain.value_objects.test_result import (
    TestResult,
    TestResultEnum,
)

TAG = "dddinsight"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_result_normalize(self):
        assert str(TestResult("PASSED")) == "passed"
        # 缺省即为 unknown（未知/未跑）
        assert TestResult(TestResultEnum.UNKNOWN.value).value == "unknown"
        with pytest.raises(DomainValidationError):
            TestResult("blocked")

    def test_result_is_defective(self):
        assert TestResult(TestResultEnum.PASSED).is_passed
        assert TestResult(TestResultEnum.FAILED).is_defective
        assert TestResult(TestResultEnum.ERROR).is_defective
        assert not TestResult(TestResultEnum.UNKNOWN).is_passed

    def test_attribution_guard_and_label(self):
        assert str(Attribution("Code_Regression")) == "code_regression"
        assert Attribution(AttributionEnum.ENV_ANOMALY).label == "环境异常"
        with pytest.raises(DomainValidationError):
            Attribution("unknown_reason")

    def test_risk_level(self):
        assert str(RiskLevel(RiskLevelEnum.HIGH)) == "high"
        assert RiskLevel("Medium").label == "中"
        with pytest.raises(DomainValidationError):
            RiskLevel("critical")

    def test_coverage_range(self):
        assert Coverage(0).value == 0.0
        assert Coverage(88).is_good
        assert not Coverage(30).is_good
        with pytest.raises(DomainValidationError):
            Coverage(101)
        with pytest.raises(DomainValidationError):
            Coverage(-1)


class TestAggregate:
    def test_file_required(self):
        with pytest.raises(DomainValidationError):
            TraceRun(trace_id=_mk(), file_path="  ")

    def test_counts_must_be_non_negative(self):
        with pytest.raises(DomainValidationError):
            TraceRun(trace_id=_mk(), file_path="a.py", passed_count=-1)

    def test_defective_result_needs_counts(self):
        # failed 结果但无任何计数 → 不完整
        with pytest.raises(DomainValidationError):
            TraceRun(trace_id=_mk(), file_path="a.py", result="failed",
                     failed_count=0, passed_count=0, error_count=0)
        # 有 failed 计数则合法
        r = TraceRun(trace_id=_mk(), file_path="a.py", result="failed", failed_count=2)
        assert r.is_defective and r.total_cases == 2

    def test_coverage_overflow(self):
        with pytest.raises(DomainValidationError):
            TraceRun(trace_id=_mk(), file_path="a.py", coverage=120)

    def test_passed_run_roundtrip(self):
        r = TraceRun(trace_id="t1", file_path="/a/b.py", result="passed",
                     passed_count=10, coverage=90.0, created_by="ci")
        d = r.to_dict()
        assert d["passed_count"] == 10
        assert d["coverage"] == 90.0
        r2 = TraceRun.from_dict(d)
        assert r2.id.value == "t1"
        assert r2.result.value == "passed"
        assert r2.coverage.value == 90.0

    def test_record_emits_event(self):
        r = TraceRun(trace_id="t2", file_path="c.py", result="unknown")
        r.record("u")
        assert len(r.pull_domain_events()) == 1


class TestDomainServices:
    def test_risk_policy_thresholds(self):
        assert RiskPolicy().classify(75).value == "high"
        assert RiskPolicy().classify(45).value == "medium"
        assert RiskPolicy().classify(10).value == "low"

    def test_value_policy(self):
        vp = ValuePolicy()
        assert vp.severity_weight("blocker") == 100.0
        assert vp.is_high_impact("critical")
        assert not vp.is_high_impact("minor")
        assert vp.value_score(30, 80) == 100.0  # 满分封顶
        assert vp.coverage_gap(0) == 20


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实 trace.db 存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_trace_file():
    fpath = f"/__ddd/{_mk()}.py"
    yield fpath
    # 清理本测试产生的执行记录
    from app.repositories.insight_repo import InsightRepo
    conn = InsightRepo._conn()
    conn.execute("DELETE FROM test_runs WHERE file_path = ?", (fpath,))
    conn.commit()


def test_record_and_get(fresh_trace_file):
    rec = test_insight_app_service.record_trace(RecordTraceCommand(
        file_path=fresh_trace_file, result="passed",
        passed_count=6, coverage=92.0, created_by="admin",
    ))
    assert rec["id"]
    g = test_insight_app_service.get(rec["id"])
    assert g and g["file_path"] == fresh_trace_file
    assert g["result"] == "passed" and g["coverage"] == 92.0


def test_record_defective(fresh_trace_file):
    rec = test_insight_app_service.record_trace(RecordTraceCommand(
        file_path=fresh_trace_file, result="failed", failed_count=2,
        error_count=1, attribution="code_regression",
    ))
    assert rec["attribution"] == "code_regression"
    # 缺计数 → 领域校验失败
    with pytest.raises(DomainValidationError):
        test_insight_app_service.record_trace(RecordTraceCommand(
            file_path=fresh_trace_file, result="error",
        ))


def test_list_and_stats(fresh_trace_file):
    test_insight_app_service.record_trace(RecordTraceCommand(
        file_path=fresh_trace_file, result="passed", passed_count=1))
    q = TraceListQuery(file_path=fresh_trace_file)
    res = test_insight_app_service.list(q)
    assert res["total"] >= 1
    assert "runs" in res and "stats" in res and "attributions" in res


def test_prove_coverage(fresh_trace_file):
    test_insight_app_service.record_trace(RecordTraceCommand(
        file_path=fresh_trace_file, result="passed", passed_count=3, coverage=90.0))
    proof = test_insight_app_service.prove_coverage(fresh_trace_file)
    assert proof["total_runs"] >= 1
    assert proof["has_passed_evidence"] is True
    assert proof["file_path"] == fresh_trace_file


def test_analysis_delegation():
    # 跨域分析用例可正常经由防腐层调用（不影响 trace 表）
    v = test_insight_app_service.get_value()
    assert "value_score" in v
    sp = test_insight_app_service.skill_path()
    assert isinstance(sp, dict)
