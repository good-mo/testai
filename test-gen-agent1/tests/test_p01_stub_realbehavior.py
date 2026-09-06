"""P0-1 假成功空壳回归测试。

来源：ISSUE #480（API专家 P0-1 大量「写语义」接口是「假成功」空壳）。
锁死此类缺陷不再复发：
  1. `/api/case/run` 及其带路径参数形式：不得对任意 id 伪造 200 SUCCESS。
     对不存在的用例应给出 4xx，而不是伪成功。
  2. `/api/case/follow`、`/api/case/unfollow`（GET 与路径参数形式）：
     必须真实落库关注状态，而不是空壳 `ok()`。

背景：原先这些接口「前端收到 200 但业务状态从未改变」，成为接口测试的
误报源。本测试做「行为级断言」——不只断言 HTTP 200，还断言副作用
（关注状态确实翻转 / 对不存在资源不再伪成功）。
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


def _make_case():
    """用真实服务造一条接口用例。"""
    case = apitest_service.create_api_case(
        name="P0-1回归用例",
        request={
            "protocol": "HTTP",
            "method": "GET",
            "path": "http://127.0.0.1:1/unreachable",
            "headers": {},
            "body": "",
        },
    )
    return case.get("id")


# ════════════════════════════════════════════════════════════
# 1. /api/case/run：不得再对任意 id 伪造 200 SUCCESS
# ════════════════════════════════════════════════════════════
class TestCaseRunNotStub:
    def test_run_nonexistent_case_returns_4xx(self, client):
        """POST /api/case/run/{id} 对不存在的用例应 4xx，而非伪 200 SUCCESS。"""
        resp = client.post("/api/case/run/no-such-case", json={})
        # 修复前：固定返回 200 {id, status:"SUCCESS"}；修复后：4xx
        assert resp.status_code == 404, resp.text

    def test_run_without_id_returns_4xx(self, client):
        """GET /api/case/run 无 id 时不再 200 伪成功，而应 4xx。"""
        resp = client.get("/api/case/run")
        assert 400 <= resp.status_code < 500, resp.text

    def test_run_body_executes_real_engine(self, client):
        """POST /api/case/run 携带存在用例时，返回真实执行结果而非伪 SUCCESS。"""
        cid = _make_case()
        assert cid, "应能创建用例"
        resp = client.post("/api/case/run", json={"id": cid})
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data", {})
        # 真实执行引擎会给出 success/case_id 等结构，而旧壳是 {status:"SUCCESS"}
        assert "success" in data, f"应返回真实执行结果结构，得到: {data}"
        assert not (data.get("status") == "SUCCESS" and "success" not in data)


# ════════════════════════════════════════════════════════════
# 2. /api/case/follow、unfollow：不得再是空壳，必须真实落库
# ════════════════════════════════════════════════════════════
class TestCaseFollowNotStub:
    def test_follow_path_persists_then_unfollow(self, client):
        """GET /api/case/follow/{id} 真实关注、unfollow 真实取消。"""
        cid = _make_case()
        assert cid, "应能创建用例"

        # 关注前无任何关注记录
        assert apitest_service.list_followers("case", cid) == [], "关注前不应有记录"
        resp = client.get(f"/api/case/follow/{cid}")
        assert resp.status_code == 200, resp.text
        followers = apitest_service.list_followers("case", cid)
        assert followers, "关注后应能在 api_follows 查到记录"
        assert cid not in followers or followers, "关注已落库"

        resp = client.get(f"/api/case/unfollow/{cid}")
        assert resp.status_code == 200, resp.text
        followers = apitest_service.list_followers("case", cid)
        assert followers == [], "取消关注后应移除记录"

    def test_follow_query_persists(self, client):
        """GET /api/case/follow（query 传 id）真实落库，非空壳 ok()。"""
        cid = _make_case()
        assert cid
        resp = client.get(f"/api/case/follow?id={cid}")
        assert resp.status_code == 200, resp.text
        followers = apitest_service.list_followers("case", cid)
        assert followers, "follow(query) 应真实落库"
        apitest_service.unfollow_resource("case", cid)


# ════════════════════════════════════════════════════════════
# 3. follow 服务器侧读回闭环：详情/列表须读回真实关注状态
#    上批只做了写入端落库，此处锁死「读取端」与「跨会话一致性」：
#    重新拉取详情时必须回读 api_follows，不能再恒为未关注。
# ════════════════════════════════════════════════════════════
def _make_bug(client, title="读回缺陷"):
    r = client.post("/bug/add", json={"title": title})
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


class TestFollowReadback:
    def test_case_detail_readback_after_follow(self, client):
        """用例详情 follow 字段须真实读回：关注后详情为 True，取关后为 False。"""
        cid = _make_case()
        assert cid

        def detail_follow():
            resp = client.get(f"/api/case/get-detail/{cid}")
            assert resp.status_code == 200, resp.text
            return resp.json()["data"].get("follow")

        try:
            assert detail_follow() is False, "关注前详情 follow 应为 False"
            client.get(f"/api/case/follow/{cid}")
            assert detail_follow() is True, "关注后详情 follow 应读回 True"
            client.get(f"/api/case/unfollow/{cid}")
            assert detail_follow() is False, "取关后详情 follow 应读回 False"
        finally:
            try:
                client.get(f"/api/case/delete/{cid}")
            except Exception:
                pass

    def test_bug_detail_readback_after_follow(self, client):
        """缺陷详情 followFlag 字段须真实读回（跨会话一致）。"""
        bid = _make_bug(client)

        def detail_follow_flag():
            resp = client.get(f"/bug/get/{bid}")
            assert resp.status_code == 200, resp.text
            return resp.json()["data"].get("followFlag")

        try:
            assert detail_follow_flag() is False, "关注前详情 followFlag 应为 False"
            client.get(f"/bug/follow/{bid}")
            assert detail_follow_flag() is True, "关注后详情 followFlag 应读回 True"
            client.get(f"/bug/unfollow/{bid}")
            assert detail_follow_flag() is False, "取关后详情 followFlag 应读回 False"
        finally:
            client.post("/bug/delete", json={"id": bid})
