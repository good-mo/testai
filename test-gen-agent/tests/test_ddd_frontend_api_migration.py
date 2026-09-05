"""DDD frontend_api 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/frontend_api/` DDD 层就绪后，本测试锁定阶段 C 薄门面接线契约：
`app/services/frontend_api_service.py` 已收敛为对 `frontend_api_app_service` 的
**薄委托门面** —— 导入操作经 `ApiImport` 聚合承载来源语义，CRUD/查询操作经
DTO/infrastructure 委托 DDD 门面。

对外方法签名与返回 schema 与重构前一致，router / api_testing 调用方零改动。
本测试断言确实走 DDD 门面。
"""
import uuid

from app.domain.frontend_api.application.dto import (
    ImportFromPostmanCommand,
    ImportFromSwaggerCommand,
)
from app.domain.frontend_api.application.frontend_api_app_service import (
    frontend_api_app_service as ddd,
)
from app.services.frontend_api_service import frontend_api_service as svc


def test_import_delegates_to_ddd(monkeypatch):
    """import_from_postman/swagger 委托 DDD app_service，参数经 DTO 翻译。"""
    seen = []

    def fake_postman(cmd):
        assert isinstance(cmd, ImportFromPostmanCommand)
        seen.append(("postman",))
        return {"status": "ok", "imported": 1, "failed": 0}

    def fake_swagger(cmd):
        assert isinstance(cmd, ImportFromSwaggerCommand)
        seen.append(("swagger",))
        return {"status": "ok", "imported": 0, "failed": 0}

    monkeypatch.setattr(ddd, "import_postman", fake_postman)
    monkeypatch.setattr(ddd, "import_swagger", fake_swagger)

    svc.import_from_postman({"collections": []})
    assert ("postman",) in seen
    svc.import_from_swagger({"swagger": "2.0", "paths": {}})
    assert ("swagger",) in seen


def test_crud_delegates_to_ddd(monkeypatch):
    """CRUD 方法（list/get/create/update/delete）委托 DDD app_service。"""
    seen = []

    def fake_list(**kw):
        seen.append(("list", kw.get("limit")))
        return []

    def fake_create(**kw):
        seen.append(("create", kw.get("name")))
        return {"id": "d1", "name": kw.get("name")}

    def fake_get(did):
        seen.append(("get", did))
        return {"id": did}

    def fake_update(did, **kw):
        seen.append(("update", did))
        return {"id": did, "name": kw.get("name")}

    def fake_delete(did, permanent=False):
        seen.append(("delete", did, permanent))
        return True

    monkeypatch.setattr(ddd, "list_api_definitions", fake_list)
    monkeypatch.setattr(ddd, "create_api_definition", fake_create)
    monkeypatch.setattr(ddd, "get_api_definition", fake_get)
    monkeypatch.setattr(ddd, "update_api_definition", fake_update)
    monkeypatch.setattr(ddd, "delete_api_definition", fake_delete)

    svc.list_api_definitions(limit=50)
    assert ("list", 50) in seen
    svc.create_api_definition(name="test-api")
    assert ("create", "test-api") in seen
    svc.get_api_definition("d1")
    assert ("get", "d1") in seen
    svc.update_api_definition("d1", name="updated")
    assert ("update", "d1") in seen
    svc.delete_api_definition("d1", permanent=True)
    assert ("delete", "d1", True) in seen


def test_mock_scenario_delegates_to_ddd(monkeypatch):
    """场景/Mock 方法委托 DDD app_service。"""
    seen = []

    def fake_list_scenarios(limit=100):
        seen.append(("scn_list", limit))
        return []

    def fake_list_mocks(limit=100):
        seen.append(("mock_list", limit))
        return []

    monkeypatch.setattr(ddd, "list_scenarios", fake_list_scenarios)
    monkeypatch.setattr(ddd, "list_mock_services", fake_list_mocks)

    svc.list_scenarios(limit=10)
    assert ("scn_list", 10) in seen
    svc.list_mock_services(limit=20)
    assert ("mock_list", 20) in seen
