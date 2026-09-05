"""definition/scenario 单端点 /follow toggle 服务器侧读回回归测试。

来源：ISSUE #512（definition/scenario 单端点 /follow toggle）。
背景：接口定义/场景详情页的「关注」使用单端点 toggle，
前端此前只做乐观翻转、从不回读服务器侧状态；后端 `follow/{id}`
返回硬编码 `followed: True`，既不真实落库也无法回读真实状态。

修复要求：
  1. `/api/definition/follow/{id}`、`/api/scenario/follow/{id}` 单端点
     必须真实翻转 api_follows 落库状态；
  2. 响应返回 `followed` 实际状态，供前端「回读」而非纯乐观翻转。
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.apitest_service import apitest_service


def _login(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })
    return client


@pytest.fixture
def client():
    from app.main import app
    return _login(TestClient(app))


def _make_definition():
    d = apitest_service.create_definition(name="follow-读回定义")
    return d.get("id")


def _make_scenario():
    s = apitest_service.create_scenario(name="follow-读回场景")
    return s.get("id")


class TestDefinitionFollowToggleReadback:
    def test_definition_toggle_persists_and_reads_back(self, client):
        did = _make_definition()
        assert did
        assert apitest_service.list_followers("definition", did) == []

        # 第一次 toggle：应关注（followed=True）
        resp = client.get(f"/api/definition/follow/{did}")
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        assert data.get("followed") is True, f"首 toggle 应回读 followed=True, got {data}"
        assert apitest_service.list_followers("definition", did), "关注应真实落库"

        # 第二次 toggle：应取消关注（followed=False）
        resp = client.get(f"/api/definition/follow/{did}")
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        assert data.get("followed") is False, f"二次 toggle 应回读 followed=False, got {data}"
        assert apitest_service.list_followers("definition", did) == [], "取消后应移除记录"

    def test_definition_post_toggle_reads_back(self, client):
        did = _make_definition()
        resp = client.post(f"/api/definition/follow/{did}", json={})
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        assert data.get("followed") is True, f"POST toggle 应回读 True, got {data}"
        apitest_service.unfollow_resource("definition", did)


class TestScenarioFollowToggleReadback:
    def test_scenario_toggle_persists_and_reads_back(self, client):
        sid = _make_scenario()
        assert sid
        assert apitest_service.list_followers("scenario", sid) == []

        resp = client.get(f"/api/scenario/follow/{sid}")
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        assert data.get("followed") is True, f"首 toggle 应回读 True, got {data}"
        assert apitest_service.list_followers("scenario", sid), "关注应真实落库"

        resp = client.get(f"/api/scenario/follow/{sid}")
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        assert data.get("followed") is False, f"二次 toggle 应回读 False, got {data}"
        assert apitest_service.list_followers("scenario", sid) == []

    def test_scenariofollow_no_underscore_reads_back(self, client):
        sid = _make_scenario()
        resp = client.get(f"/api/scenariofollow/{sid}")
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        assert data.get("followed") is True, f"无下划线形式应回读 True, got {data}"
        apitest_service.unfollow_resource("scenario", sid)

