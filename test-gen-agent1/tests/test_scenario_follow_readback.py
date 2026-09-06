"""接口场景 scenario 关注状态服务器侧读回闭环回归测试。

来源：ISSUE #461（router/auth、*_compat 等大量「假成功」空壳端点）。
背景：此前 `/api/scenario/follow` GET 返回 ok()、POST 返回 ok(None) 均不落库，
且 `_to_scenario` 无 follow 字段读回，前端收藏图标恒为未关注、跨会话读不回状态。

本测试验证（与 definition 关注闭环同构，resource_type=scenario）：
  - 新建场景后详情 follow=False；
  - 经 POST /api/scenario/follow toggle 后，详情读回 follow=True；
  - 再次 toggle 取关后，详情读回 follow=False；
  - GET /api/scenario/follow（query 传 id）同样真实落库并回读。
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


def _data(resp):
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _make_scenario(client, name="scenario-follow-场景"):
    r = client.post("/api/scenario/add", json={"name": name, "steps": []})
    assert r.status_code == 200, r.text
    sid = _data(r).get("id")
    assert sid, r.text
    return sid


class TestScenarioFollowReadback:
    def test_follow_toggle_reads_back_in_detail(self, client):
        sid = _make_scenario(client)
        try:
            # 未关注：详情 follow=False
            resp = client.get(f"/api/scenario/detail/{sid}")
            assert resp.status_code == 200, resp.text
            assert _data(resp)["follow"] is False

            # POST toggle 第一次：真实落库 + 回读 followed=True
            resp = client.post("/api/scenario/follow", json={"id": sid})
            assert resp.status_code == 200, resp.text
            assert _data(resp)["followed"] is True, resp.text

            # 详情读回 follow=True
            resp = client.get(f"/api/scenario/detail/{sid}")
            assert resp.status_code == 200, resp.text
            assert _data(resp)["follow"] is True

            # GET follow（query 传 id）第二次 toggle：取关，回读 followed=False
            resp = client.get(f"/api/scenario/follow?id={sid}")
            assert resp.status_code == 200, resp.text
            assert _data(resp)["success"] is False, resp.text

            # 详情读回 follow=False
            resp = client.get(f"/api/scenario/detail/{sid}")
            assert _data(resp)["follow"] is False
        finally:
            client.post("/api/scenario/delete", json={"id": sid})
