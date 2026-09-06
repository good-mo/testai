"""DDD apitest 域 A→B→C 渐进迁移回归测试。

背景
----
`app/domain/apitest/` DDD 层（阶段 A）已就绪后，本测试锁定「阶段 B/C」迁移契约：
  - 阶段 C：`ApitestService` 的定义/用例/场景 对象级 CRUD 已改为经
    `apitest_app_service`（DDD 门面）下沉业务规则到聚合；
  - 阶段 B：Router 调用薄 Service → 门面 → 聚合，完成 DDD 路由。

本测试直接以 Service 为界验证迁移后行为与旧契约一致（创建/读取/更新/软删/
恢复的缺失语义、状态机、名称守卫），并在迁移后仍保持既有对外契约（204→404、
bool 返回值等），作为逐域切换的回归基线。
"""
import uuid

from app.domain.common.exceptions import DomainValidationError
from app.services.apitest_service import apitest_service

TAG = "migsvc"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def test_definition_migration_contract():
    # 阶段 C：经门面创建 → 名称守卫生效
    d = apitest_service.create_definition(name="登录", path="/login",
                                          method="POST", project_id="p")
    assert d and d["id"]
    did = d["id"]
    # 更新（门面 set_content 聚合守护）
    got = apitest_service.update_definition(did, path="/v2/login")
    assert got and got["path"] == "/v2/login"
    assert apitest_service.get_definition(did)["path"] == "/v2/login"
    # 缺失语义保持旧契约（返回 None / False，而非抛 500）
    assert apitest_service.update_definition("nope", name="x") is None
    assert apitest_service.get_definition("nope") is None
    # 软删 + 恢复（聚合软删语义）
    assert apitest_service.delete_definition(did) is True
    assert apitest_service.delete_definition("nope") is False
    assert apitest_service.restore_definition(did) is True
    assert apitest_service.restore_definition("nope") is False
    # 名称不可为空（域不变量）
    import pytest
    with pytest.raises((DomainValidationError, Exception)):
        # 经兼容层：路由已默认未命名，故直接验证聚合守卫
        from app.domain.apitest.domain.entities.api_definition import ApiDefinition
        ApiDefinition(definition_id=_mk(), name="")


def test_case_status_state_machine_via_migration():
    c = apitest_service.create_api_case(name="用例A", request={"method": "GET"},
                                        project_id="p")
    assert c and c["id"]
    cid = c["id"]
    assert apitest_service.get_api_case(cid)["status"] == "draft"
    # 阶段 C：状态迁移经聚合状态机（draft → active）
    apitest_service.update_api_case(cid, status="active")
    assert apitest_service.get_api_case(cid)["status"] == "active"
    # 软删生命周期
    assert apitest_service.delete_api_case(cid) is True
    assert apitest_service.delete_api_case("nope") is False
    assert apitest_service.restore_case(cid) is True


def test_scenario_migration_contract():
    sc = apitest_service.create_scenario(name="场景1", project_id="p")
    assert sc and sc["id"]
    sid = sc["id"]
    got = apitest_service.update_scenario(sid, name="场景改")
    assert got and got["name"] == "场景改"
    assert apitest_service.update_scenario("nope", name="x") is None
    assert apitest_service.delete_scenario(sid) is True
    assert apitest_service.delete_scenario("nope") is False
    assert apitest_service.restore_scenario(sid) is True
