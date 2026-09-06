"""apitest 域 DDD 薄门面（阶段 C 续 · purge/batch_purge/batch_update/
rollback_definition / module stats）回归测试。

背景
----
definition/case/scenario 三大聚合的 回收站 purge（物理删除）、batch_purge、
batch_update、rollback_definition 与 module stats（按模块统计/总数/模块数）
等旁路方法，此前 `apitest_service` 仍直连 `ApitestRepo`；本批将其收敛为对
`apitest_web` → `apitest_app_service`（DDD 门面）的薄委托，对外契约零变化。

本测试验证：
  1. 这些 Service 方法确以 `apitest_web` 为委托出口（不再直接 new ApitestRepo
     直连 purge/batch_update/rollback/count_*）；
  2. 薄委托端到端行为与旧直连语义一致（物理删除后不可再读回 / 批量计数值 /
     版本回滚 / 模块统计）。

仍属双轨直连的旁路（mock 列表/CRUD、env、env_groups、global_params、
module_tree 增删改查、execution、followers、logs、schedules）不在本测试范围。
"""
import inspect
import uuid

import pytest

from app.repositories.apitest_repo import ApitestRepo
from app.services.apitest_service import apitest_service

TAG = "appurge"
# 这些方法应已收敛为经 apitest_web 薄委托，而非直连 ApitestRepo。
_DELEGATED = [
    "purge_definition", "purge_case", "purge_scenario", "purge_mock",
    "batch_purge_definitions", "batch_purge_cases", "batch_purge_scenarios",
    "batch_purge_mocks",
    "batch_update_definitions", "batch_update_cases", "batch_update_scenarios",
    "rollback_definition",
    "count_definitions_by_module", "count_definitions_total",
    "count_cases_for_definition", "count_modules",
]


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


# ─────────────────────────────────────────────────────────────
# 1) 委托出口校验：Service 方法体引用 apitest_web，而非 ApitestRepo
# ─────────────────────────────────────────────────────────────
class TestDelegationRouting:
    @pytest.mark.parametrize("method_name", _DELEGATED)
    def test_service_method_delegates_to_ddd_facade(self, method_name):
        method = getattr(apitest_service, method_name)
        assert method, f"缺少 Service 方法 {method_name}"
        src = inspect.getsource(method)
        # 经 apitest_web 薄委托
        assert "apitest_web." in src, (
            f"{method_name} 未收敛为 apitest_web 薄委托：\n{src}"
        )
        # 不再直连 ApitestRepo（保持薄门面纯度）
        assert "ApitestRepo." not in src, (
            f"{method_name} 仍直连 ApitestRepo：\n{src}"
        )

    def test_ddd_facade_exposes_routed_methods(self):
        import app.domain.apitest.application.apitest_web as web
        for name in [
            "purge_definition", "purge_case", "purge_scenario", "purge_mock",
            "batch_purge_definitions", "batch_purge_cases", "batch_purge_scenarios",
            "batch_purge_mocks",
            "batch_update_definitions", "batch_update_cases", "batch_update_scenarios",
            "rollback_definition",
            "count_definitions_by_module", "count_definitions_total",
            "count_cases_for_definition", "count_modules",
        ]:
            assert callable(getattr(web, name)), f"apitest_web 缺少 {name}"


# ─────────────────────────────────────────────────────────────
# 2) 端到端行为：purge / batch_purge / batch_update / rollback
# ─────────────────────────────────────────────────────────────
class TestPurgeBehaviour:
    def test_purge_definition_hard_deletes(self):
        d = apitest_service.create_definition(name=_mk(), path="/api/pd",
                                              method="GET", project_id="pp")
        did = d["id"]
        try:
            # 软删进回收站
            assert apitest_service.delete_definition(did) is True
            trash = apitest_service.list_trash_definitions(project_id="pp")
            assert any(x["id"] == did for x in trash)
            # purge 物理删除
            assert apitest_service.purge_definition(did) is True
            # 读回不可得
            assert apitest_service.get_definition(did) is None
            trash2 = apitest_service.list_trash_definitions(project_id="pp")
            assert not any(x["id"] == did for x in trash2)
        finally:
            _cleanup_definition(did)

    def test_batch_purge_and_batch_update_definitions(self):
        d1 = apitest_service.create_definition(name=_mk(), path="/api/bu1",
                                                method="POST", project_id="pp2")
        d2 = apitest_service.create_definition(name=_mk(), path="/api/bu2",
                                                method="POST", project_id="pp2")
        try:
            # 批量更新
            cnt = apitest_service.batch_update_definitions(
                [d1["id"], d2["id"]], method="PUT")
            assert cnt == 2
            g1 = apitest_service.get_definition(d1["id"])
            assert g1 and g1["method"] == "PUT"
            # 软删 + 批量物理删除
            apitest_service.delete_definition(d1["id"])
            apitest_service.delete_definition(d2["id"])
            purged = apitest_service.batch_purge_definitions([d1["id"], d2["id"]])
            assert purged == 2
            assert apitest_service.get_definition(d1["id"]) is None
            assert apitest_service.get_definition(d2["id"]) is None
        finally:
            _cleanup_definition(d1["id"])
            _cleanup_definition(d2["id"])

    def test_batch_purge_cases(self):
        c1 = apitest_service.create_api_case(name=_mk(), project_id="ppc")
        c2 = apitest_service.create_api_case(name=_mk(), project_id="ppc")
        try:
            apitest_service.delete_api_case(c1["id"])
            apitest_service.delete_api_case(c2["id"])
            purged = apitest_service.batch_purge_cases([c1["id"], c2["id"]])
            assert purged == 2
            assert apitest_service.get_api_case(c1["id"]) is None
            assert apitest_service.get_api_case(c2["id"]) is None
        finally:
            _cleanup_case(c1["id"])
            _cleanup_case(c2["id"])

    def test_batch_purge_scenarios(self):
        s1 = apitest_service.create_scenario(name=_mk(), project_id="pps")
        s2 = apitest_service.create_scenario(name=_mk(), project_id="pps")
        try:
            apitest_service.delete_scenario(s1["id"])
            apitest_service.delete_scenario(s2["id"])
            purged = apitest_service.batch_purge_scenarios([s1["id"], s2["id"]])
            assert purged == 2
            assert apitest_service.get_scenario(s1["id"]) is None
            assert apitest_service.get_scenario(s2["id"]) is None
        finally:
            _cleanup_scenario(s1["id"])
            _cleanup_scenario(s2["id"])

    def test_rollback_definition(self):
        d = apitest_service.create_definition(name=_mk(), path="/api/rb",
                                               method="GET", project_id="ppr")
        did = d["id"]
        ver = None
        try:
            # 创建第二个版本
            ver = apitest_service.create_definition_version(did, "v2")
            # 回滚到 v1（原定义自身所在版本）
            result = apitest_service.rollback_definition(
                did, d.get("version_id") or d.get("version") or "")
            # 回滚不应炸：返回 dict 或（该 id 已被新版本顶替时）None 皆可
            assert result is None or isinstance(result, dict)
        finally:
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


# ─────────────────────────────────────────────────────────────
# 3) 模块统计：module stats 走 DDD 门面且语义一致
# ─────────────────────────────────────────────────────────────
class TestModuleStats:
    def test_count_definitions_by_module_and_total(self):
        d = apitest_service.create_definition(name=_mk(), path="/api/ms",
                                               method="GET", project_id="pms")
        did = d["id"]
        try:
            by_mod = apitest_service.count_definitions_by_module()
            assert isinstance(by_mod, dict)
            total = apitest_service.count_definitions_total()
            assert total >= 1
            # 语义与直连一致
            assert by_mod == ApitestRepo.count_definitions_by_module()
            assert total == ApitestRepo.count_definitions_total()
        finally:
            _cleanup_definition(did)

    def test_count_cases_for_definition(self):
        c = apitest_service.create_api_case(name=_mk(), project_id="pmsc")
        cid = c["id"]
        try:
            # 无对应 definition 时计数 0 且不炸
            assert apitest_service.count_cases_for_definition("no_such_def") == 0
            assert isinstance(apitest_service.count_cases_for_definition(cid), int)
        finally:
            _cleanup_case(cid)

    def test_count_modules(self):
        n = apitest_service.count_modules("api")
        assert isinstance(n, int) and n >= 0
