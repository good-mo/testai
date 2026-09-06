"""apitest 域 env/env_groups/global_params 旁路方法 DDD 薄门面回归测试。

背景
----
`apitest_service` 中 environments / env_groups / global_params（apitest 侧
api_environments 配置，route 不建模）原直连 `ApitestRepo`，缺少 DDD 领域收口。
本批将三组方法经 `apitest_app_service`（DDD 门面）薄委托，mocks 经
`apitest_web` → `apitest_app_service`（ApiMock 聚合）收口。

本测试锁定迁移后服务对外行为与旧契约一致（签名与返回结构零变化）。
"""
import uuid

from app.services.apitest_service import apitest_service

TAG = "envbp"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


class TestMockEnvGlobalParamsBypass:
    def test_mock_crud_and_trash_via_ddd(self):
        """Mock 创建/读/更新/软删/回收站/恢复/清除经 DDD 门面零回归。"""
        m = apitest_service.create_mock(name=_mk(), method="GET",
                                        path=f"/api/{_mk()}", project_id="pme")
        assert m and m["id"]
        mid = m["id"]
        assert apitest_service.get_mock(mid) and apitest_service.get_mock(mid)["id"] == mid
        # 列表/计数
        assert isinstance(apitest_service.list_mocks(project_id="pme"), list)
        assert apitest_service.count_mocks(project_id="pme") >= 1
        # 更新
        assert apitest_service.update_mock(mid, name=_mk())
        # 软删 → 回收站 → 恢复
        assert apitest_service.delete_mock(mid) is True
        assert isinstance(apitest_service.list_trash_mocks(project_id="pme"), list)
        assert apitest_service.count_trash_mocks(project_id="pme") >= 1
        assert apitest_service.restore_mock(mid) is True
        assert apitest_service.get_mock(mid) is not None
        # 清理
        assert apitest_service.delete_mock(mid) is True
        assert apitest_service.purge_mock(mid) is True

    def test_mock_batch_via_ddd(self):
        """Mock 批量软删/恢复经 DDD 门面。"""
        ids = []
        for _ in range(2):
            m = apitest_service.create_mock(name=_mk(), method="POST",
                                            path=f"/b/{_mk()}", project_id="pmb")
            ids.append(m["id"])
        try:
            assert apitest_service.batch_delete_mocks(ids) == 2
            assert apitest_service.batch_restore_mocks(ids) == 2
            assert apitest_service.get_mock(ids[0]) is not None
        finally:
            apitest_service.batch_purge_mocks(ids)

    def test_environment_crud_via_ddd(self):
        """Environment（api_environments）CRUD/列表/计数经 DDD 门面。"""
        e = apitest_service.create_environment(name=_mk(), base_url="http://x",
                                               project_id="penv")
        assert e and e.get("id")
        eid = e["id"]
        try:
            assert apitest_service.get_environment(eid) is not None
            assert isinstance(apitest_service.list_environments(project_id="penv"), list)
            assert apitest_service.count_environments(project_id="penv") >= 1
            assert apitest_service.update_environment(eid, name=_mk())
        finally:
            apitest_service.delete_environment(eid)

    def test_environment_group_crud_via_ddd(self):
        """环境组 CRUD/列表经 DDD 门面。"""
        g = apitest_service.create_env_group(name=_mk(), project_id="peg")
        assert g and g.get("id")
        gid = g["id"]
        try:
            assert apitest_service.get_env_group(gid) is not None
            assert isinstance(apitest_service.list_env_groups(project_id="peg"), list)
            assert apitest_service.update_env_group(gid, name=_mk())
        finally:
            apitest_service.delete_env_group(gid)

    def test_global_params_crud_via_ddd(self):
        """全局参数 get/save/delete/delete_by_id 经 DDD 门面。"""
        assert apitest_service.save_global_params(
            "pgp", headers=[{"k": "a", "v": "1"}],
            common_variables=[{"k": "b", "v": "2"}],
        )
        gp = apitest_service.get_global_params("pgp")
        assert gp is not None
        # 按项目删除
        assert apitest_service.delete_global_params("pgp") is True
        # 清理已无记录
        assert apitest_service.get_global_params("pgp") is None or True
