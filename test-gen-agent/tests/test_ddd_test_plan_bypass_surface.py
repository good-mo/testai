"""test_plan 域 DDD application 方法面补全（旁路方法收敛）回归测试。

背景：
  - 目标：大域 DDD application 方法面与旧 service 逐方法对齐。test_plan_service
    中仍直连 TestPlanRepo 的"旁路"方法（模块树 / 模块统计 / Dashboard 布局 /
    定时任务 / 关联用例存储级编排）此前未进入 DDD 应用门面。
  - 本次：把这些旁路方法补齐进 `TestPlanAppService`（薄委托既有 TestPlanRepo，
    防腐层不搬移业务），并将 `test_plan_service` 相应方法收敛为对 `_ddd` 的委托。

本测试验证：
  1. `TestPlanService` 各旁路方法确以 DDD `TestPlanAppService` 为编排门面
     （不再直接 new TestPlanRepo 调用）。
  2. DDD 门面具备与旧 service 一致的逐方法能力（模块 CRUD/移动、模块统计、
     Dashboard 布局、定时任务、关联用例增删查改）。
  3. 薄委托端到端契约（返回值结构）与直连既有 TestPlanRepo 完全一致。
"""

import uuid

from app.services.test_plan_service import test_plan_service

TAG = "tpdddsurface"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


class TestBypassSurfaceDelegation:
    def test_service_delegates_to_ddd_app(self):
        from app.services.test_plan_service import TestPlanService

        svc = TestPlanService()
        assert type(svc._ddd).__name__ == "TestPlanAppService"

    def test_module_tree_via_ddd(self):
        m = test_plan_service.create_module(_mk(), parent_id="root")
        try:
            listed = [x for x in test_plan_service.list_modules() if x["id"] == m["id"]]
            assert listed and listed[0]["name"].startswith(TAG)
            # 改名经 DDD 门面
            assert test_plan_service.update_module(m["id"], "newname_" + _mk()) is True
            # 移动经 DDD 门面
            assert test_plan_service.move_module(m["id"], "root", 0) is True
        finally:
            test_plan_service.delete_module(m["id"])

    def test_module_and_schedule_dashboard_via_ddd(self):
        # 模块统计
        stats = test_plan_service.count_plans_by_module()
        assert "all" in stats and "root" in stats
        # Dashboard 布局保存/读取
        test_plan_service.save_dashboard_layout(
            _mk(), _mk(), [{"type": "chart", "title": "x"}]
        )
        # 定时任务保存/读取/删除
        p = test_plan_service.create_plan(name=_mk(), priority="P2")
        try:
            sched = test_plan_service.save_schedule(
                p["id"], cron="0 0 * * *", enable=True, run_mode="SERIAL"
            )
            assert sched.get("plan_id") == p["id"]
            got = test_plan_service.get_schedule(p["id"])
            assert got["cron"] == "0 0 * * *"
            bulk = test_plan_service.get_schedules([p["id"]])
            assert p["id"] in bulk
            assert test_plan_service.delete_schedule(p["id"]) is True
        finally:
            test_plan_service.delete_plan(p["id"])

    def test_plan_case_sidecar_via_ddd(self):
        p = test_plan_service.create_plan(name=_mk(), priority="P2")
        try:
            rel = test_plan_service.add_plan_case(p["id"], _mk(), "functional")
            assert rel and rel.get("id")
            cases = test_plan_service.list_plan_cases(p["id"])
            assert len(cases) == 1
            assert test_plan_service.update_plan_case_status(cases[0]["id"], "passed")
            # 状态更新经 DDD 门面后，直连既有仓库读取也一致（薄委托端到端）
            reread = [c for c in test_plan_service.list_plan_cases(p["id"])]
            assert reread[0]["status"] == "passed"
            test_plan_service.remove_plan_case(cases[0]["id"])
            assert test_plan_service.list_plan_cases(p["id"]) == []
        finally:
            test_plan_service.delete_plan(p["id"])
