"""接口定义 definition 关注 GET 兼容端点真实落库回归测试。

来源：ISSUE #533 —— 修复各 compat 里可映射到真实 service 的关注/启停/调度类。
此前 `/api/definition/follow` GET 直接 ``return ok(None)`` 假成功：前端点了有关注
动作、返回 200，但 api_follows（resource_type=definition）从未写入，跨会话读不回。
本测试验证 GET 变体（query 传 id）已接入真实 apitest_service.follow_resource。
"""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_DB_PATH", "test_def_follow_realfix.db")

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    db = os.environ.get("AUTH_DB_PATH")
    if db and os.path.exists(db):
        os.remove(db)
    with TestClient(app) as c:
        yield c


def _data(resp):
    body = resp.json() if hasattr(resp, "json") else resp
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _login_headers(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    session = r.json()["data"]
    return {"X-AUTH-TOKEN": session["sessionId"], "CSRF-TOKEN": session["csrfToken"]}


def _make_definition(client, headers):
    r = client.post("/api/definition/add", json={"name": "follow-get-def", "path": "/x"}, headers=headers)
    assert r.status_code == 200, r.text
    return _data(r)["id"]


class TestDefinitionFollowGetReal:
    def test_follow_get_persists(self, client):
        headers = _login_headers(client)
        def_id = _make_definition(client, headers)
        try:
            # GET /api/definition/follow?definitionId=... -> 真实落库 follow
            r = client.get(f"/api/definition/follow?definitionId={def_id}", headers=headers)
            assert r.status_code == 200, r.text
            assert _data(r)["success"] is True, r.text

            from app.core.helpers import definition_followed as _definition_followed
            assert _definition_followed(def_id) is True, "GET 关注未真实落库"
        finally:
            client.post("/api/definition/delete", json={"id": def_id}, headers=headers)
