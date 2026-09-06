"""空壳路由治理回归测试。

对应 Issue #608 修复7：
  - 统一占位标识 stub() 返回 `{"stub": true}`，让「假成功占位」可被测试/调用方辨识
    （原来只 return ok(None)，测试断言只看 200 覆盖不到）。
  - scripts/stub_route_report.py 定期出报告 + 防增量门禁。
  - 点名空壳 test_plan_module_move 已真实化（重挂父模块），不应再被判定为空壳。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.response import ok, stub


class TestStubIdentifier:
    """统一占位标识 stub()。"""

    def test_stub_returns_200_and_marker(self):
        r = stub()
        body = json.loads(r.body)
        assert r.status_code == 200
        assert body["code"] == 200
        assert body["data"]["stub"] is True

    def test_stub_keeps_success_message(self):
        r = stub(message="占位")
        body = json.loads(r.body)
        assert body["data"]["stub"] is True
        assert "占位" in body["data"]["message"]

    def test_ok_has_no_stub_marker(self):
        r = ok(None)
        body = json.loads(r.body)
        data = body.get("data")
        assert not (isinstance(data, dict) and data.get("stub") is True)


class TestStubReportScript:
    """stub_route_report.py 判定逻辑。"""

    def _records(self):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "stub_route_report", "scripts/stub_route_report.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_report_runs_and_finds_pure_stubs(self):
        mod = self._records()
        records = mod.scan_routes()
        # 全库扫描总能跑通且数量 > 0
        assert len(records) > 0
        by_name = {r["name"]: r for r in records}
        # functional_mind_case_edit（读 body 后 return ok(None)）仍应被判定为空壳 A 类
        rec = by_name.get("functional_mind_case_edit")
        assert rec is not None, "应能找到 functional_mind_case_edit 路由"
        assert mod.classify(rec) in ("A", "X"), "该读 body 后 return ok(None) 的薄占位应被识别"

    def test_test_plan_module_move_no_longer_stub(self):
        mod = self._records()
        records = mod.scan_routes()
        by_name = {r["name"]: r for r in records}
        rec = by_name.get("test_plan_module_move")
        assert rec is not None, "应能找到 test_plan_module_move 路由"
        assert rec["side"], "真实化后函数体内应出现 service 副作用引用"
        assert mod.classify(rec) == "", "已接真实 service 的路由不应再被判为空壳"
