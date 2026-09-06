"""performance 域 DDD 接入（四层 service 桥 + LangGraph 入口）迁移回归。

验证「入口已接」：
  1. 四层 PerformanceService 作为 DDD 薄门面，把一批被测目标经
     PerformanceAppService + 真实引擎防腐层跑完完整生命周期并汇总。
  2. 真实 LangGraph 入口 run_performance_tests 已委托 DDD 门面，
     且保持既有 performance_report 契约（overall_passed / total_benchmarks /
     summary / benchmarks 可序列化）不回归。
  3. 领域状态机结果（status/passed）随 DDD 生命周期进入报告（规则下沉可见）。
"""
import json
import uuid

from app.performance.runner import extract_benchmark_targets, run_performance_tests
from app.services.performance_service import PerformanceService

TAG = "dddperfmig"  # 测试标识


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


SAMPLE_CODE = """
def compute_sum(n: int = 100) -> int:
    total = 0
    for i in range(n):
        total += i
    return total

def multiply(a: int = 3, b: int = 5) -> int:
    return a * b
"""

SIGNATURES = [
    {"name": "compute_sum", "params": {"n": 100}},
    {"name": "multiply", "params": {"a": 3, "b": 5}},
]


def _targets():
    return extract_benchmark_targets(SAMPLE_CODE, SIGNATURES)


class TestPerformanceServiceFacade:
    """四层 service 薄门面接入（委托 DDD 应用服务 + 引擎防腐层）。"""

    def test_run_for_targets_produces_report(self):
        svc = PerformanceService(default_iterations=10, default_warmup=1)
        report = svc.run_for_targets(
            _targets(), source_ref=f"{_mk()}.py", iterations=10, warmup=1
        )
        assert report["total_benchmarks"] == 2
        assert set(report["benchmarks"][0]) >= {
            "name", "metrics", "slo", "passed", "status"
        }
        # 简单函数应全部达标
        assert report["overall_passed"] is True
        assert report["passed"] == 2
        assert report["failed"] == 0
        assert "summary" in report
        json.dumps(report)  # 可序列化

    def test_run_for_targets_empty(self):
        svc = PerformanceService(default_iterations=10, default_warmup=1)
        report = svc.run_for_targets([], source_ref="x.py")
        assert report["total_benchmarks"] == 0
        assert report["overall_passed"] is False

    def test_facade_terminates_each_test_in_terminal_state(self):
        """每个被测目标经 DDD 生命周期进入终态，报告携带状态机结果。"""
        svc = PerformanceService(default_iterations=10, default_warmup=1)
        report = svc.run_for_targets(_targets(), source_ref="demo.py", iterations=10, warmup=1)
        for b in report["benchmarks"]:
            assert b["status"] in ("passed", "failed", "skipped")
            assert b["passed"] is (b["status"] == "passed")
            assert b["metrics"] is not None


class TestLangGraphEntryConnected:
    """真实入口 run_performance_tests 已委托 DDD 门面（入口未接 → 已接）。"""

    def test_entry_routes_through_ddd(self):
        state = {"source_code": SAMPLE_CODE, "signatures": SIGNATURES}
        result = run_performance_tests(state)
        report = result["performance_report"]
        assert "overall_passed" in report
        assert report["total_benchmarks"] >= 1
        assert "summary" in report
        # 经由 DDD 后，benchmark 条目携带领域状态机结果字段
        for b in report.get("benchmarks", []):
            assert "status" in b
            assert "passed" in b

    def test_entry_no_source(self):
        result = run_performance_tests({"source_code": "", "signatures": []})
        assert result["performance_report"].get("error")

    def test_entry_no_benchmarkable_targets(self):
        result = run_performance_tests({"source_code": "def _p():\n    return 1", "signatures": [{"name": "_p", "params": None}]})
        report = result["performance_report"]
        assert report.get("skipped") is True or report["total_benchmarks"] == 0

    def test_entry_report_serializable(self):
        state = {
            "source_code": SAMPLE_CODE,
            "signatures": SIGNATURES,
            "file_path": "demo.py",
        }
        result = run_performance_tests(state)
        json.dumps(result["performance_report"])
