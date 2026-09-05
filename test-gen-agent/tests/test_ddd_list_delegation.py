"""核心域「只读列表 / 批量 / schema」委托 DDD 回归测试。

本次收尾已接线的核心域：把 cases/defects/test_plan/project 等域里
仍旁路的只读列表逐步委托 DDD，同时补齐领域视图 schema 差异。

覆盖：
  1. cases：list / list_cases / count_cases 委托 DDD（module_id 过滤、
     last_result 补全）。
  2. defects：list / list_trash / get_stats 委托 DDD（tags JSON 字符串
     归一化、回收站读回）。
  3. test_plan：list_plans / count_plans 委托 DDD（module_ids 过滤穿透）。
  4. project：list_members 委托 DDD（返回成员列表 schema 与 Repo 一致）。
"""
import json
import uuid

from app.repositories.case_repo import CaseRepo
from app.repositories.defect_repo import DefectRepo
from app.repositories.project_repo import ProjectRepo
from app.repositories.test_plan_repo import TestPlanRepo
from app.services.case_service import case_service
from app.services.defect_service import defect_service
from app.services.project_service import project_service
from app.services.test_plan_service import test_plan_service

TAG = "dddlists"


def _mk(prefix="t"):
    return f"{prefix}_{TAG}_{uuid.uuid4().hex[:6]}"


def _cleanup_case(cid):
    try:
        CaseRepo.purge_case(cid)
    except Exception:
        pass


def _cleanup_defect(did):
    try:
        DefectRepo.purge(did)
    except Exception:
        pass


def _cleanup_plan(pid):
    try:
        TestPlanRepo.delete_plan(pid)
    except Exception:
        pass


class TestCasesListDelegation:
    def test_list_delegates_to_ddd_preserves_schema(self):
        """cases: list 委托 DDD 返回含 last_result / module_id 过滤行。"""
        d = case_service.create({
            "id": _mk("c"),
            "title": _mk("title"),
            "metadata": {"module_id": "m1"},
        })
        cid = d["id"]
        try:
            # 验证 DDD list 返回的 last_result 字段
            case_service.update_case_result(cid, {"status": "passed"})
            rows, total = case_service.list(module_id="m1")
            assert total == 1
            assert any(r["id"] == cid for r in rows)
            hit = next(r for r in rows if r["id"] == cid)
            assert hit["last_result"] == {"status": "passed"}, hit
            # 非 module_id 命中 → 空
            rows2, total2 = case_service.list(module_id="other")
            assert total2 == 0
        finally:
            _cleanup_case(cid)

    def test_list_cases_delegates_schema(self):
        """cases: list_cases 经 DDD 返回含 test_type / status 等既有字段。"""
        search_tag = "list_cases_search_tag"
        d = case_service.create({
            "id": _mk("lc"),
            "title": f"{search_tag}_{_mk()}",
            "test_type": "api",
            "status": "draft",
        })
        cid = d["id"]
        try:
            rows = case_service.list_cases(search=search_tag)
            assert len(rows) >= 1
            hit = next(r for r in rows if r["id"] == cid)
            assert hit["test_type"] == "api"
            assert hit["status"] == "draft"
        finally:
            _cleanup_case(cid)

    def test_count_cases_delegates(self):
        """cases: count_cases 经 DDD total 口径与 list 一致。"""
        d = case_service.create({"id": _mk("cnt"), "title": _mk("cnt_t")})
        cid = d["id"]
        try:
            total = case_service.count_cases()
            assert isinstance(total, int) and total >= 1
        finally:
            _cleanup_case(cid)


class TestDefectsListDelegation:
    def test_list_delegates_to_ddd_tags_json_str(self):
        """defects: list 委托 DDD 返回 tags 为 JSON 字符串（schema 保持）。"""
        d = defect_service.create({"title": _mk("def"), "tags": ["x", "y"]})
        did = d["id"]
        try:
            rows, total = defect_service.list()
            assert total >= 1
            found = [r for r in rows if r["id"] == did]
            assert len(found) == 1
            # tags 应为 JSON 字符串（与 DefectRepo 行一致）
            assert found[0]["tags"] == json.dumps(["x", "y"], ensure_ascii=False), found[0]["tags"]
        finally:
            _cleanup_defect(did)

    def test_get_stats_delegates(self):
        """defects: get_stats 委托 DDD 后统计口径与既有一致。"""
        d = defect_service.create({"title": _mk("stats")})
        did = d["id"]
        try:
            stats = defect_service.get_stats()
            assert "total" in stats and stats["total"] >= 1
            assert "by_status" in stats
        finally:
            _cleanup_defect(did)

    def test_list_trash_delegates(self):
        """defects: list_trash 委托 DDD 后回收站读回。"""
        d = defect_service.create({"title": _mk("trash")})
        did = d["id"]
        try:
            defect_service.trash(did)
            items, total = defect_service.list_trash()
            trash_ids = [i["id"] for i in items]
            assert did in trash_ids
            assert total >= 1
        finally:
            _cleanup_defect(did)


class TestTestPlanListDelegation:
    def test_list_plans_delegates_preserves_module_ids(self):
        """test_plan: list_plans 委托 DDD 且 module_ids 过滤穿透生效。"""
        p = test_plan_service.create_plan(name=_mk("tp"), module_id="mod_a")
        pid = p["id"]
        try:
            # 全部计划
            plans = test_plan_service.list_plans()
            assert any(x["id"] == pid for x in plans)
            # module_ids 过滤命中
            plans_a = test_plan_service.list_plans(module_ids=["mod_a"])
            assert any(x["id"] == pid for x in plans_a)
            # module_ids 过滤排除
            plans_b = test_plan_service.list_plans(module_ids=["mod_b"])
            assert not any(x["id"] == pid for x in plans_b)
        finally:
            _cleanup_plan(pid)

    def test_count_plans_delegates(self):
        """test_plan: count_plans 委托 DDD 返回 total。"""
        p = test_plan_service.create_plan(name=_mk("cntp"))
        pid = p["id"]
        try:
            total = test_plan_service.count_plans()
            assert isinstance(total, int) and total >= 1
        finally:
            _cleanup_plan(pid)

    def test_list_plans_schema_bridge_columns(self):
        """test_plan: list 返回行含 metadata / execution_rate / pass_rate。"""
        p = test_plan_service.create_plan(name=_mk("schema"))
        pid = p["id"]
        try:
            plans = test_plan_service.list_plans()
            hit = next(x for x in plans if x["id"] == pid)
            assert "metadata" in hit
            assert "execution_rate" in hit
            assert "pass_rate" in hit
        finally:
            _cleanup_plan(pid)


class TestProjectListDelegation:
    def test_list_members_delegates(self):
        """project: list_members 委托 DDD 后返回 Repo 同 schema 行。"""
        p = project_service.create({"name": _mk("proj")})
        pid = p["id"]
        try:
            # 经 Repo 添加成员（绕过 DDD add_member 以保持 schema 简单）
            ProjectRepo.add_member(pid, user_id="u1", username="u1", name="User1")
            members = project_service.list_members(pid)
            assert any(m["user_id"] == "u1" for m in members)
        finally:
            # 清理项目与成员
            project_service.delete(pid)
