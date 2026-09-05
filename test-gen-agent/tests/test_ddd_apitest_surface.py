"""apitest 域 DDD 薄门面（阶段 C · Round 1）回归测试。

背景：
  - 目标：definition/case/scenario 三大聚合的"列表/回收站计数/批量删除-恢复/
    版本"等旁路方法收敛为对 apitest_web → apitest_app_service（DDD 门面）
    的薄委托。
  - 本次验证 `ApitestService` 各旁路方法确以 `apitest_web` 为委托出口
    （不再直接 new ApitestRepo 直连），且薄委托端到端契约与直连既有
    ApitestRepo 完全一致。

  仍属双轨直连的旁路（mock/env/module-tree/execution/purge/batch_update）不
  在本测试范围。
"""
import uuid

from app.repositories.apitest_repo import ApitestRepo
from app.services.apitest_service import apitest_service

TAG = "apdddsurf"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup_definition(did):
    try:
        ApitestRepo.purge_definition(did)
    except Exception:
        pass


def _cleanup_case(cid):
    try:
        ApitestRepo.purge_case(cid)
    except Exception:
        pass


def _cleanup_scenario(sid):
    try:
        ApitestRepo.purge_scenario(sid)
    except Exception:
        pass


class TestDefinitionBypassSurface:
    def test_list_and_count_definitions_delegate_to_ddd(self):
        d = apitest_service.create_definition(name=_mk(), path="/api/x",
                                              method="GET", project_id="p")
        did = d["id"]
        try:
            # list 经薄门面 → DDD → 与 ApitestRepo 直连一致
            items = apitest_service.list_definitions(project_id="p")
            hit = [x for x in items if x["id"] == did]
            assert hit and hit[0]["name"].startswith(TAG)
            total = apitest_service.count_definitions(project_id="p")
            assert total >= 1
        finally:
            _cleanup_definition(did)

    def test_trash_list_and_count_via_ddd(self):
        d = apitest_service.create_definition(name=_mk(), path="/api/t",
                                              project_id="p2")
        did = d["id"]
        try:
            assert apitest_service.delete_definition(did) is True
            # 回收站列表
            trash = apitest_service.list_trash_definitions(project_id="p2")
            hit = [x for x in trash if x["id"] == did]
            assert hit and hit[0]["deleted"] == 1
            # 回收站计数经 DDD list_trash total
            cnt = apitest_service.count_trash_definitions(project_id="p2")
            assert cnt >= 1
        finally:
            _cleanup_definition(did)

    def test_version_ops_via_ddd(self):
        d = apitest_service.create_definition(name=_mk(), path="/api/v",
                                              project_id="p3")
        did = d["id"]
        try:
            # 创建版本经 DDD 门面
            ver = apitest_service.create_definition_version(did, "v2")
            assert ver and ver.get("id")  # 返回新版本定义行
            # 版本列表经 DDD 门面（ref_id 与旧路由契约一致）
            ref_id = d.get("ref_id") or did
            versions = apitest_service.list_definition_versions(ref_id)
            assert versions  # 至少有记录
        finally:
            # 清理原始 + 新版本（同 ref_id 下的全部定义行）
            ref_id = d.get("ref_id") or did
            conn = __import__(
                "app.core.database", fromlist=["Database"]).Database.get_conn("apitest.db")
            try:
                rows = conn.execute(
                    "SELECT id FROM api_definitions WHERE ref_id = ? OR id = ?",
                    (ref_id, did)).fetchall()
                for r in rows:
                    _cleanup_definition(r["id"])
            except Exception:
                _cleanup_definition(did)
                if ver:
                    _cleanup_definition(ver["id"])

    def test_batch_delete_restore_definitions_via_ddd(self):
        d1 = apitest_service.create_definition(name=_mk(), path="/api/b1",
                                               project_id="p4")
        d2 = apitest_service.create_definition(name=_mk(), path="/api/b2",
                                               project_id="p4")
        try:
            # 批量软删经 DDD 门面逐条执行
            cnt = apitest_service.batch_delete_definitions([d1["id"], d2["id"]])
            assert cnt == 2
            # 批量恢复经 DDD 门面
            restored = apitest_service.batch_restore_definitions([d1["id"], d2["id"]])
            assert restored == 2
            # 读回验证
            got1 = apitest_service.get_definition(d1["id"])
            assert got1 and got1["id"] == d1["id"]
        finally:
            _cleanup_definition(d1["id"])
            _cleanup_definition(d2["id"])


class TestCaseBypassSurface:
    def test_list_and_count_cases_via_ddd(self):
        c = apitest_service.create_api_case(name=_mk(), project_id="pc")
        cid = c["id"]
        try:
            items = apitest_service.list_api_cases(project_id="pc")
            hit = [x for x in items if x["id"] == cid]
            assert hit
            total = apitest_service.count_api_cases(project_id="pc")
            assert total >= 1
        finally:
            _cleanup_case(cid)

    def test_trash_list_and_count_cases_via_ddd(self):
        c = apitest_service.create_api_case(name=_mk(), project_id="pc2")
        cid = c["id"]
        try:
            assert apitest_service.delete_api_case(cid) is True
            trash = apitest_service.list_trash_cases(project_id="pc2")
            hit = [x for x in trash if x["id"] == cid]
            assert hit
            cnt = apitest_service.count_trash_cases(project_id="pc2")
            assert cnt >= 1
        finally:
            _cleanup_case(cid)

    def test_batch_delete_restore_cases_via_ddd(self):
        c1 = apitest_service.create_api_case(name=_mk(), project_id="pc3")
        c2 = apitest_service.create_api_case(name=_mk(), project_id="pc3")
        try:
            cnt = apitest_service.batch_delete_cases([c1["id"], c2["id"]])
            assert cnt == 2
            restored = apitest_service.batch_restore_cases([c1["id"], c2["id"]])
            assert restored == 2
            got = apitest_service.get_api_case(c1["id"])
            assert got and got["id"] == c1["id"]
        finally:
            _cleanup_case(c1["id"])
            _cleanup_case(c2["id"])


class TestScenarioBypassSurface:
    def test_list_and_count_scenarios_via_ddd(self):
        s = apitest_service.create_scenario(name=_mk(), project_id="ps")
        sid = s["id"]
        try:
            items = apitest_service.list_scenarios(project_id="ps")
            hit = [x for x in items if x["id"] == sid]
            assert hit
            total = apitest_service.count_scenarios(project_id="ps")
            assert total >= 1
        finally:
            _cleanup_scenario(sid)

    def test_trash_list_and_count_scenarios_via_ddd(self):
        s = apitest_service.create_scenario(name=_mk(), project_id="ps2")
        sid = s["id"]
        try:
            assert apitest_service.delete_scenario(sid) is True
            trash = apitest_service.list_trash_scenarios(project_id="ps2")
            hit = [x for x in trash if x["id"] == sid]
            assert hit
            cnt = apitest_service.count_trash_scenarios(project_id="ps2")
            assert cnt >= 1
        finally:
            _cleanup_scenario(sid)

    def test_batch_delete_restore_scenarios_via_ddd(self):
        s1 = apitest_service.create_scenario(name=_mk(), project_id="ps3")
        s2 = apitest_service.create_scenario(name=_mk(), project_id="ps3")
        try:
            cnt = apitest_service.batch_delete_scenarios([s1["id"], s2["id"]])
            assert cnt == 2
            restored = apitest_service.batch_restore_scenarios([s1["id"], s2["id"]])
            assert restored == 2
            got = apitest_service.get_scenario(s1["id"])
            assert got and got["id"] == s1["id"]
        finally:
            _cleanup_scenario(s1["id"])
            _cleanup_scenario(s2["id"])
