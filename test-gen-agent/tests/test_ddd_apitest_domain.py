"""DDD 接口测试试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：值对象守卫、状态机、软删除/恢复。
  2. 应用服务全链路（对接真实 ApitestRepo 存储）。
"""
import uuid

import pytest

from app.domain.apitest.application.apitest_app_service import apitest_app_service
from app.domain.apitest.application.dto import (
    ChangeApiCaseStatusCommand,
    CreateApiCaseCommand,
    CreateDefinitionCommand,
    CreateScenarioCommand,
    DeleteCaseCommand,
    DeleteDefinitionCommand,
    DeleteScenarioCommand,
    RestoreCaseCommand,
    RestoreDefinitionCommand,
    RestoreScenarioCommand,
    UpdateApiCaseCommand,
    UpdateDefinitionCommand,
    UpdateScenarioCommand,
)
from app.domain.apitest.domain.value_objects.priority import Priority
from app.domain.common.exceptions import DomainValidationError

TAG = "ddda"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _definition(**kw):
    from app.domain.apitest.domain.entities.api_definition import ApiDefinition
    kw.setdefault("definition_id", _mk())
    kw.setdefault("name", "测试接口")
    return ApiDefinition(**kw)


def _case(**kw):
    from app.domain.apitest.domain.entities.api_case import ApiCase
    kw.setdefault("case_id", _mk())
    kw.setdefault("name", "测试用例")
    return ApiCase(**kw)


def _scenario(**kw):
    from app.domain.apitest.domain.entities.scenario import Scenario
    kw.setdefault("scenario_id", _mk())
    kw.setdefault("name", "测试场景")
    return Scenario(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_priority_guard(self):
        assert str(Priority("p1")) == "P1"
        with pytest.raises(DomainValidationError):
            Priority("P9")

    def test_priority_weight(self):
        assert Priority("P0").weight < Priority("P3").weight

    def test_definition_name_required(self):
        with pytest.raises(DomainValidationError):
            _definition(name="")


class TestApiDefinitionAggregate:
    def test_rename(self):
        d = _definition()
        d.rename("新接口", "u")
        assert d.name == "新接口"

    def test_rename_empty_rejected(self):
        d = _definition()
        with pytest.raises(DomainValidationError):
            d.rename("", "u")

    def test_set_content(self):
        d = _definition()
        d.set_content(path="/api/v2/test", method="POST", tags=["api"],
                      operator="u")
        assert d.path == "/api/v2/test"
        assert d.method == "POST"
        assert "api" in d.tags

    def test_soft_delete_restore(self):
        d = _definition()
        d.delete("u")
        assert d.deleted
        with pytest.raises(DomainValidationError):
            d.delete("u")  # 重复删除
        d.restore("u")
        assert not d.deleted

    def test_events_collected(self):
        d = _definition()
        d.rename("新名字", "u")
        names = [type(e).__name__ for e in d.pull_domain_events()]
        assert "ApiDefinitionRenamed" in names


class TestApiCaseAggregate:
    def test_rename(self):
        c = _case()
        c.rename("新用例", "u")
        assert c.name == "新用例"

    def test_change_priority(self):
        c = _case()
        c.change_priority("P0", "u")
        assert c.priority.value == "P0"

    def test_change_status(self):
        c = _case()
        c.change_status("active", "u")
        assert str(c.status) == "active"
        c.change_status("draft", "u")
        assert str(c.status) == "draft"

    def test_set_request(self):
        c = _case()
        c.set_request({"method": "GET", "path": "/api/test"}, "u")
        assert c.request["path"] == "/api/test"

    def test_soft_delete_restore(self):
        c = _case()
        c.delete("u")
        assert c.deleted
        c.restore("u")
        assert not c.deleted

    def test_events_collected(self):
        c = _case()
        c.change_priority("P1", "u")
        names = [type(e).__name__ for e in c.pull_domain_events()]
        assert "ApiCasePriorityChanged" in names


class TestScenarioAggregate:
    def test_rename(self):
        s = _scenario()
        s.rename("新场景", "u")
        assert s.name == "新场景"

    def test_change_status(self):
        s = _scenario()
        s.change_status("active", "u")
        assert str(s.status) == "active"

    def test_set_steps(self):
        s = _scenario()
        s.set_steps([{"id": "1", "type": "api_case"}], "u")
        assert len(s.steps) == 1

    def test_soft_delete_restore(self):
        s = _scenario()
        s.delete("u")
        assert s.deleted
        s.restore("u")
        assert not s.deleted


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_definition_id():
    item = apitest_app_service.create_definition(CreateDefinitionCommand(
        name=_mk(), method="GET", path="/api/ddd", operator="admin",
    ))
    did = item["id"]
    yield did
    # 清理（物理删除）
    from app.repositories.apitest_repo import ApitestRepo
    try:
        ApitestRepo.purge_definition(did)
    except Exception:
        pass


@pytest.fixture
def fresh_case_id():
    item = apitest_app_service.create_api_case(CreateApiCaseCommand(
        name=_mk(), priority="P1", operator="admin",
    ))
    cid = item["id"]
    yield cid
    # 清理（物理删除）
    from app.repositories.apitest_repo import ApitestRepo
    try:
        ApitestRepo.purge_case(cid)
    except Exception:
        pass


@pytest.fixture
def fresh_scenario_id():
    item = apitest_app_service.create_scenario(CreateScenarioCommand(
        name=_mk(), operator="admin",
    ))
    sid = item["id"]
    yield sid
    # 清理（物理删除）
    from app.repositories.apitest_repo import ApitestRepo
    try:
        ApitestRepo.purge_scenario(sid)
    except Exception:
        pass


def test_definition_create_and_get(fresh_definition_id):
    assert apitest_app_service.get_definition(fresh_definition_id) is not None


def test_definition_update(fresh_definition_id):
    r = apitest_app_service.update_definition(UpdateDefinitionCommand(
        definition_id=fresh_definition_id, name=_mk(), path="/api/updated",
        operator="admin"))
    assert r is not None
    assert r["path"] == "/api/updated"


def test_definition_delete_restore(fresh_definition_id):
    assert apitest_app_service.delete_definition(DeleteDefinitionCommand(
        definition_id=fresh_definition_id, operator="admin"))
    tr = apitest_app_service.list_trash_definitions(limit=50)
    assert tr["total"] >= 1
    assert apitest_app_service.restore_definition(RestoreDefinitionCommand(
        definition_id=fresh_definition_id, operator="admin"))
    g = apitest_app_service.get_definition(fresh_definition_id)
    assert g is not None


def test_case_create_and_get(fresh_case_id):
    assert apitest_app_service.get_api_case(fresh_case_id) is not None


def test_case_update(fresh_case_id):
    r = apitest_app_service.update_api_case(UpdateApiCaseCommand(
        case_id=fresh_case_id, name=_mk(), priority="P0", operator="admin"))
    assert r is not None
    assert r["priority"] == "P0"


def test_case_status_change(fresh_case_id):
    r = apitest_app_service.change_api_case_status(ChangeApiCaseStatusCommand(
        case_id=fresh_case_id, target_status="active", operator="admin"))
    assert r["status"] == "active"


def test_case_delete_restore(fresh_case_id):
    assert apitest_app_service.delete_api_case(DeleteCaseCommand(
        case_id=fresh_case_id, operator="admin"))
    tr = apitest_app_service.list_trash_cases(limit=50)
    assert tr["total"] >= 1
    assert apitest_app_service.restore_api_case(RestoreCaseCommand(
        case_id=fresh_case_id, operator="admin"))
    g = apitest_app_service.get_api_case(fresh_case_id)
    assert g is not None


def test_scenario_create_and_get(fresh_scenario_id):
    assert apitest_app_service.get_scenario(fresh_scenario_id) is not None


def test_scenario_update(fresh_scenario_id):
    r = apitest_app_service.update_scenario(UpdateScenarioCommand(
        scenario_id=fresh_scenario_id, name=_mk(), description="updated",
        operator="admin"))
    assert r is not None
    assert r["description"] == "updated"


def test_scenario_delete_restore(fresh_scenario_id):
    assert apitest_app_service.delete_scenario(DeleteScenarioCommand(
        scenario_id=fresh_scenario_id, operator="admin"))
    tr = apitest_app_service.list_trash_scenarios(limit=50)
    assert tr["total"] >= 1
    assert apitest_app_service.restore_scenario(RestoreScenarioCommand(
        scenario_id=fresh_scenario_id, operator="admin"))
    g = apitest_app_service.get_scenario(fresh_scenario_id)
    assert g is not None
