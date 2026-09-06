"""功能用例 featureCase 关注状态服务器侧读回闭环回归测试。

来源：ISSUE #512（功能用例 featureCase follow 假成功/恒未关注）。
背景：此前功能用例详情 followFlag 在 `_to_functional_case` 中硬编码为 False，
`/functional/case/edit/follower` 关注/取消关注返回 ok(None) 空实现不落库，
导致前端收藏图标恒为未关注、点关注提示成功但后端无动作、跨会话读不回状态。

本测试验证：
  - 未关注时详情 followFlag=False；
  - 经 /functional/case/edit/follower 关注后，详情读回 followFlag=True；
  - 再次 toggle 取关后，详情读回 followFlag=False；
  - /functional/case/follower 返回真实关注者。
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


def _make_case(client, name="featureCase-follow-用例"):
    r = client.post("/functional/case/add", json={"name": name, "priority": "P2"})
    assert r.status_code == 200, r.text
    cid = _data(r).get("id")
    assert cid, r.text
    return cid


class TestFeatureCaseFollowReadback:
    def test_follow_toggle_reads_back_in_detail(self, client):
        cid = _make_case(client)
        try:
            # 未关注：详情 followFlag=False
            resp = client.get(f"/functional/case/detail/{cid}")
            assert resp.status_code == 200, resp.text
            assert _data(resp)["followFlag"] is False

            # 关注（toggle 第一次）：真实落库 + 返回 followed=True
            resp = client.post("/functional/case/edit/follower",
                               json={"functionalCaseId": cid, "userId": "admin"})
            assert resp.status_code == 200, resp.text
            assert _data(resp)["followed"] is True, resp.text

            # 详情读回 followFlag=True
            resp = client.get(f"/functional/case/detail/{cid}")
            assert _data(resp)["followFlag"] is True

            # 关注者列表返回 admin
            resp = client.get(f"/functional/case/follower?functional_case_id={cid}")
            assert resp.status_code == 200, resp.text
            assert "admin" in _data(resp), _data(resp)

            # 再次 toggle：取关，详情读回 False
            resp = client.post("/functional/case/edit/follower",
                               json={"functionalCaseId": cid, "userId": "admin"})
            assert _data(resp)["followed"] is False, resp.text
            resp = client.get(f"/functional/case/detail/{cid}")
            assert _data(resp)["followFlag"] is False
        finally:
            client.post("/functional/case/delete", json={"id": cid})
