"""DDD 测试计划试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：优先级守卫、状态机、归档、用例编排不变量。
  2. 应用服务全链路（对接真实 TestPlanRepo 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.test_plan.application.dto import (
    AddCaseCommand,
    ChangeStatusCommand,
    CreatePlanCommand,
    PlanListQuery,
    RemoveCaseCommand,
    UpdateCaseStatusCommand,
    UpdatePlanCommand,
)
from app.domain.test_plan.application.test_plan_app_service import test_plan_app_service
from app.domain.test_plan.domain.value_objects.case_status import CaseExecutionStatusEnum
from app.domain.test_plan.domain.value_objects.priority import Priority, PriorityEnum
from app.domain.test_plan.domain.value_objects.status import PlanStatus, PlanStatusEnum

TAG = "dddtestplan"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _plan(**kw):
    from app.domain.test_plan.domain.entities.test_plan import TestPlan
    kw.setdefault("plan_id", _mk())
    kw.setdefault("name", "迭代测试计划")
    return TestPlan(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_priority_guard(self):
        assert str(Priority("p1")) == "P1"
        with pytest.raises(DomainValidationError):
            Priority("P9")

    def test_priority_weight(self):
        assert Priority(PriorityEnum.P0.value).weight < Priority("P3").weight

    def test_status_normalize(self):
        assert str(PlanStatus("Running")) == "running"
        assert str(PlanStatus("")) == "prepared"

    def test_archived_flag(self):
        assert PlanStatus(PlanStatusEnum.ARCHIVED.value).is_archived

    def test_name_required(self):
        with pytest.raises(DomainValidationError):
            _plan(name="")


class TestAggregate:
    def test_rename(self):
        p = _plan()
        p.rename("新计划", "u")
        assert p.name == "新计划"

    def test_rename_empty_rejected(self):
        p = _plan()
        with pytest.raises(DomainValidationError):
            p.rename("", "u")

    def test_state_machine(self):
        p = _plan()
        assert str(p.status) == "prepared"
        p.change_status("running", "u")
        assert str(p.status) == "running"
        p.change_status("completed", "u")
        assert str(p.status) == "completed"
        # 允许重新打开
        p.change_status("running", "u")
        assert str(p.status) == "running"

    def test_illegal_transition_rejected(self):
        # prepared -> completed -> running 是合法；但 prepared 直接无法走到 archived（走 archive）
        with pytest.raises(DomainValidationError):
            _plan().change_status(PlanStatusEnum.ARCHIVED.value, "u")

    def test_archive(self):
        p = _plan()
        p.archive("u")
        assert p.status.is_archived
        with pytest.raises(DomainValidationError):
            p.archive("u")  # 重复归档
        # 归档后不可直接回到运行态
        with pytest.raises(DomainValidationError):
            p.change_status("running", "u")

    def test_threshold_guard(self):
        p = _plan()
        with pytest.raises(DomainValidationError):
            p.set_threshold(120, "u")
        p.set_threshold(80, "u")
        assert p.pass_threshold == 80

    def test_case_dup_rejected_by_default(self):
        p = _plan(repeat_case=False)
        p.add_case("r1", "case-1", "functional", "u")
        with pytest.raises(DomainValidationError):
            p.add_case("r2", "case-1", "functional", "u")

    def test_case_add_update_remove(self):
        p = _plan(repeat_case=True)
        p.add_case("r1", "case-1", "functional", "u")
        p.add_case("r2", "case-2", "api", "u")
        assert len(p.cases) == 2
        p.update_case_status("r1", "passed", "u")
        assert str(p.cases[0].status) == CaseExecutionStatusEnum.PASSED.value
        p.remove_case("r1", "u")
        assert len(p.cases) == 1

    def test_reorder(self):
        p = _plan(repeat_case=True)
        p.add_case("r1", "c1", "functional", "u")
        p.add_case("r2", "c2", "api", "u")
        p.add_case("r3", "c3", "scenario", "u")
        p.reorder_cases(["r3", "r1", "r2"], "u")
        assert [c.rel_id for c in p.cases] == ["r3", "r1", "r2"]

    def test_events_collected(self):
        p = _plan()
        p.change_status("running", "u")
        p.rename("abc", "u")
        names = [type(e).__name__ for e in p.pull_domain_events()]
        assert "TestPlanStatusChanged" in names
        assert "TestPlanUpdated" in names


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_plan_id():
    plan = test_plan_app_service.create(CreatePlanCommand(
        name=_mk(), priority="P1", operator="admin",
    ))
    pid = plan["id"]
    yield pid
    # 清理（物理删除，含关联用例）
    test_plan_app_service.delete(pid, "admin")


def test_create_and_get(fresh_plan_id):
    assert test_plan_app_service.get(fresh_plan_id) is not None


def test_update(fresh_plan_id):
    r = test_plan_app_service.update(UpdatePlanCommand(
        plan_id=fresh_plan_id, name=_mk(), priority="P0", status="running",
        operator="admin"))
    assert r is not None
    assert r["priority"] == "P0"
    assert r["status"] == "running"


def test_status_flow(fresh_plan_id):
    r = test_plan_app_service.change_status(ChangeStatusCommand(
        plan_id=fresh_plan_id, target_status="running", operator="admin"))
    assert r["status"] == "running"
    r2 = test_plan_app_service.change_status(ChangeStatusCommand(
        plan_id=fresh_plan_id, target_status="completed", operator="admin"))
    assert r2["status"] == "completed"


def test_archive_roundtrip(fresh_plan_id):
    assert test_plan_app_service.archive(fresh_plan_id, "admin")
    g = test_plan_app_service.get(fresh_plan_id)
    assert g and g["status"] == "archived"


def test_case_lifecycle(fresh_plan_id):
    # 添加功能用例
    r = test_plan_app_service.add_case(AddCaseCommand(
        plan_id=fresh_plan_id, case_id=_mk(), case_type="functional", operator="admin"))
    assert r["cases"] and r["cases"][0]["status"] == "pending"
    rel_id = r["cases"][0]["rel_id"]
    # 更新执行状态
    r2 = test_plan_app_service.update_case_status(UpdateCaseStatusCommand(
        plan_id=fresh_plan_id, rel_id=rel_id, status="passed", operator="admin"))
    assert r2["cases"][0]["status"] == "passed"
    # 统计
    st = test_plan_app_service.statistics(fresh_plan_id)
    assert st["total"] == 1 and st["passed"] == 1
    # 移除
    r3 = test_plan_app_service.remove_case(RemoveCaseCommand(
        plan_id=fresh_plan_id, rel_id=rel_id, operator="admin"))
    assert r3["cases"] == []


def test_list(fresh_plan_id):
    result = test_plan_app_service.list(PlanListQuery(limit=10))
    assert "list" in result and "total" in result
    # 清理创建的计划残留
    name = test_plan_app_service.get(fresh_plan_id)["name"]
    matched = test_plan_app_service.list(PlanListQuery(keyword=name))
    assert matched["total"] >= 1
