"""测试项目管理-菜单管理（项目应用配置）相关接口。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    c = TestClient(app)
    r = c.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code == 200:
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
    return c


PROJECT_ID = "test-menu-project"
CONFIG_SUFFIXES = [
    ("workstation", "WORKSTATION_SYNC_RULE"),
    ("test-plan", "TEST_PLAN_CLEAN_REPORT"),
    ("bug", "BUG_SYNC_SYNC_ENABLE"),
    ("case", "CASE_RELATED_CASE_ENABLE"),
    ("api", "API_CLEAN_REPORT"),
    ("ui", "UI_CLEAN_REPORT"),
    ("task", "TASK_CLEAN_REPORT"),
    ("performance-test", "PERFORMANCE_TEST_CLEAN_REPORT"),
]


def test_module_setting_list(client):
    """菜单管理-模块列表。"""
    r = client.get("/project/application/module-setting/", params={"projectId": PROJECT_ID})
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list) and len(data) >= 8
    modules = {item["module"] for item in data}
    assert {"workstation", "testPlan", "bugManagement", "caseManagement",
            "apiTest", "uiTest", "taskCenter", "loadTest"} <= modules


def test_get_config_by_module(client):
    """获取各模块配置。"""
    for suffix, key in CONFIG_SUFFIXES:
        r = client.post(f"/project/application/{suffix}", json={"projectId": PROJECT_ID, "type": suffix})
        assert r.status_code == 200, f"{suffix} -> {r.status_code}"
        data = r.json()["data"]
        assert key in data, f"{suffix} 缺少配置项 {key}"


def test_update_config_by_module(client):
    """更新模块配置并持久化。"""
    r = client.post(
        "/project/application/update/workstation",
        json={"projectId": PROJECT_ID, "type": "WORKSTATION_SYNC_RULE", "typeValue": "false"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["WORKSTATION_SYNC_RULE"] is False

    # 回读确认持久化
    r2 = client.post("/project/application/workstation", json={"projectId": PROJECT_ID})
    assert r2.status_code == 200
    assert r2.json()["data"]["WORKSTATION_SYNC_RULE"] is False


def test_resource_pool_and_user_options(client):
    """资源池与用户选项。"""
    r = client.get("/project/application/api/resource/pool/" + PROJECT_ID)
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)

    r2 = client.get("/project/application/api/user/" + PROJECT_ID)
    assert r2.status_code == 200
    assert isinstance(r2.json()["data"], list)


def test_bug_case_platform_and_sync(client):
    """缺陷/用例平台下拉、同步信息。"""
    r = client.get("/project/application/bug/platform/org1")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)

    r2 = client.get("/project/application/bug/platform/info/plugin1")
    assert r2.status_code == 200
    assert "formItems" in r2.json()["data"]

    r3 = client.get("/project/application/bug/sync/info/" + PROJECT_ID)
    assert r3.status_code == 200
    assert "platform_key" in r3.json()["data"]

    r4 = client.get("/project/application/case/related/info/" + PROJECT_ID)
    assert r4.status_code == 200
    assert "platform_key" in r4.json()["data"]


def test_fake_error_crud(client):
    """误报规则增删改查。"""
    r = client.post("/fake/error/add", json={
        "projectId": PROJECT_ID, "name": "规则A", "enable": True,
        "label": "HTTP", "rule": "status==500", "ruleResult": "500",
    })
    assert r.status_code == 200
    rid = r.json()["data"]["id"]

    r2 = client.post("/fake/error/list", json={"projectId": PROJECT_ID})
    assert r2.status_code == 200
    assert any(item["id"] == rid for item in r2.json()["data"])

    # 启用状态更新
    r3 = client.post("/fake/error/update/enable", json={"selectIds": [rid], "enable": True})
    assert r3.status_code == 200

    # 删除
    r4 = client.post("/fake/error/delete", json={"selectIds": [rid]})
    assert r4.status_code == 200

    r5 = client.post("/fake/error/list", json={"projectId": PROJECT_ID})
    assert all(item["id"] != rid for item in r5.json()["data"])


def test_api_config_includes_fake_count(client):
    """接口配置包含误报规则启用数量。"""
    r = client.post("/project/application/api", json={"projectId": PROJECT_ID})
    assert r.status_code == 200
    assert "ENABLE_FAKE_ERROR_NUM" in r.json()["data"]
