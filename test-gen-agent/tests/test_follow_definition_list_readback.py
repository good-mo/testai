"""接口定义列表/详情 follow 服务器侧读回回归测试。

来源：ISSUE #512（修复② 关注状态读回）。
背景：definition 关注已接入真实落库（api_follows, resource_type=definition），
但部分列表/详情返回点仍硬编码 `follow: False`，导致前端收藏图标恒为未关注、
跨会话读不回真实状态。本测试验证这些返回点读回真实关注状态。

涉及返回点：
  - apitest_compat_definition.py `_to_definition`（定义分页列表/详情）
  - frontend.py 定义回收站分页列表
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


def _make_definition(name="follow-列表读回定义"):
    d = apitest_service.create_definition(name=name)
    did = d.get("id")
    assert did
    return did


class TestDefinitionListReadback:
    def test_definition_list_reads_back_follow(self, client):
        did = _make_definition()
        try:
            # 未关注时列表 follow=False
            resp = client.post("/api/definition/page", json={"pageSize": 50, "current": 1})
            assert resp.status_code == 200, resp.text
            items = resp.json().get("data", {}).get("list", [])
            item = next((x for x in items if x.get("id") == did), None)
            assert item is not None, "新建定义应出现在列表"
            assert item.get("follow") is False, f"未关注应 follow=False, got {item.get('follow')}"

            # 关注落库后，列表读回 follow=True
            assert apitest_service.follow_resource("definition", did)
            resp = client.post("/api/definition/page", json={"pageSize": 50, "current": 1})
            assert resp.status_code == 200, resp.text
            items = resp.json().get("data", {}).get("list", [])
            item = next((x for x in items if x.get("id") == did), None)
            assert item.get("follow") is True, f"关注后列表应读回 follow=True, got {item.get('follow')}"

            # 取关后读回 False
            assert apitest_service.unfollow_resource("definition", did)
            resp = client.post("/api/definition/page", json={"pageSize": 50, "current": 1})
            items = resp.json().get("data", {}).get("list", [])
            item = next((x for x in items if x.get("id") == did), None)
            assert item.get("follow") is False, f"取关后列表应读回 follow=False, got {item.get('follow')}"
        finally:
            apitest_service.unfollow_resource("definition", did)

    def test_definition_detail_reads_back_follow(self, client):
        did = _make_definition()
        try:
            resp = client.get(f"/api/definition/get-detail?id={did}")
            assert resp.status_code == 200, resp.text
            detail = resp.json().get("data", {})
            assert detail.get("follow") is False, f"未关注详情应 follow=False, got {detail.get('follow')}"

            assert apitest_service.follow_resource("definition", did)
            resp = client.get(f"/api/definition/get-detail?id={did}")
            assert resp.status_code == 200, resp.text
            detail = resp.json().get("data", {})
            assert detail.get("follow") is True, f"关注后详情应读回 follow=True, got {detail.get('follow')}"
        finally:
            apitest_service.unfollow_resource("definition", did)
