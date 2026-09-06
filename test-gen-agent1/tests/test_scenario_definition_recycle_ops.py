"""scenario/definition 回收站、delete-to-gc、批量彻底删除端点回归测试。

来源：ISSUE #533/#461 批量推进第 1 簇 —— scenario/definition 回收站、
delete-to-gc、批量操作等已有真实 store 的 compat 端点存在空壳（假成功）
或软删/彻底删语义混淆：
  - scenario 侧：GET /api/scenario/delete-to-gc 原为空壳 return ok()；
    GET /api/scenario/delete 误调软删 delete_scenario（应 purge 彻底删）；
    POST /api/scenario/batch/delete 空壳；GET /api/scenario/module/trash/tree 空壳返回 []。
  - definition 侧：POST /api/definition/delete、/delete/{id}、/batch/delete
    误用软删 batch_delete_definitions，而前端语义为回收站中彻底删除（purge）。

本测试通过真实 API 验证：
  - delete-to-gc 软删进回收站后：主列表消失、常规详情 404（软删记录不可读）；
  - delete / batch/delete 彻底删除后：详情 404 / 不再出现在回收站。
"""
import uuid

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


def _new_name(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TestScenarioRecycleOps:
    def _make(self, client):
        name = _new_name("scenario-recycle")
        r = client.post("/api/scenario/add", json={"name": name, "steps": []})
        assert r.status_code == 200, r.text
        return _data(r).get("id")

    def test_delete_to_gc_soft_deletes_then_detail_unreadable(self, client):
        sid = self._make(client)
        try:
            # 主列表可见
            r = client.post("/api/scenario/page", json={"current": 1, "pageSize": 100})
            ids = [x["id"] for x in _data(r).get("list", [])]
            assert sid in ids, "刚创建的场景应出现在主列表"

            # delete-to-gc 软删（POST）
            r = client.post("/api/scenario/delete-to-gc", json={"id": sid})
            assert r.status_code == 200, r.text

            # 软删后常规详情不可读（软删记录 get 返回 None → 404）
            r = client.get(f"/api/scenario/detail/{sid}")
            assert r.status_code == 404, r.text
        finally:
            client.post("/api/scenario/delete", json={"id": sid})

    def test_get_delete_to_gc_soft_deletes(self, client):
        """GET /api/scenario/delete-to-gc（query 传 id）应真实软删，不再空壳。"""
        sid = self._make(client)
        try:
            r = client.get(f"/api/scenario/delete-to-gc?id={sid}")
            assert r.status_code == 200, r.text
            # 软删后常规详情不可读（软删记录 get 返回 None → 404）
            r = client.get(f"/api/scenario/detail/{sid}")
            assert r.status_code == 404, r.text
        finally:
            client.post("/api/scenario/delete", json={"id": sid})

    def test_delete_purges_completely(self, client):
        """POST /api/scenario/delete 彻底删除后详情应 404。"""
        sid = self._make(client)
        # 彻底删除
        r = client.post("/api/scenario/delete", json={"id": sid})
        assert r.status_code == 200, r.text
        r = client.get(f"/api/scenario/detail/{sid}")
        assert r.status_code == 404, "彻底删除后详情应 404"

    def test_batch_delete_purges_completely(self, client):
        """POST /api/scenario/batch/delete 批量彻底删除。"""
        sid1 = self._make(client)
        sid2 = self._make(client)
        r = client.post("/api/scenario/batch/delete", json={"ids": [sid1, sid2]})
        assert r.status_code == 200, r.text
        assert _data(r).get("deleted", 0) == 2, r.text
        for sid in (sid1, sid2):
            r = client.get(f"/api/scenario/detail/{sid}")
            assert r.status_code == 404, "批量彻底删除后详情应 404"


class TestDefinitionRecycleOps:
    def _make(self, client):
        name = _new_name("definition-recycle")
        r = client.post("/api/definition/add", json={
            "name": name, "method": "GET", "path": "/api/demo",
        })
        assert r.status_code == 200, r.text
        return _data(r).get("id")

    def _in_trash(self, client, did):
        """definition 回收站分页接口查询目标 id。"""
        r = client.post("/api/definition/page", json={
            "deleted": True, "current": 1, "pageSize": 100,
        })
        assert r.status_code == 200, r.text
        return any(x.get("id") == did for x in _data(r).get("list", []))

    def test_delete_to_gc_soft_deletes(self, client):
        """delete-to-gc 软删进回收站（回收站分页可见）。"""
        did = self._make(client)
        try:
            # 软删前不应在回收站
            assert not self._in_trash(client, did), "刚创建的 definition 不应在回收站"
            r = client.post("/api/definition/delete-to-gc", json={"id": did})
            assert r.status_code == 200, r.text
            # 软删后在回收站分页可见
            assert self._in_trash(client, did), "delete-to-gc 后 definition 应在回收站"
        finally:
            client.post("/api/definition/delete", json={"id": did})

    def test_batch_delete_purges_completely(self, client):
        """POST /api/definition/batch/delete 应批量彻底删除（purge），而非软删。"""
        did1 = self._make(client)
        did2 = self._make(client)
        # 先软删进回收站，模拟回收站中的批量清空
        client.post("/api/definition/delete-to-gc", json={"id": did1})
        client.post("/api/definition/delete-to-gc", json={"id": did2})
        assert self._in_trash(client, did1) and self._in_trash(client, did2)

        r = client.post("/api/definition/batch/delete", json={"ids": [did1, did2]})
        assert r.status_code == 200, r.text
        assert _data(r).get("deleted", 0) == 2, r.text
        # 批量彻底删除后应从回收站消失
        assert not self._in_trash(client, did1), "批量彻底删除后不应再在回收站"
        assert not self._in_trash(client, did2), "批量彻底删除后不应再在回收站"

    def test_delete_path_purges_completely(self, client):
        """POST /api/definition/delete/{id} 彻底删除。"""
        did = self._make(client)
        # 先软删进回收站
        client.post("/api/definition/delete-to-gc", json={"id": did})
        assert self._in_trash(client, did)
        r = client.post(f"/api/definition/delete/{did}")
        assert r.status_code == 200, r.text
        # 彻底删除后从回收站消失
        assert not self._in_trash(client, did), "delete/{id} 彻底删除后不应在回收站"


class TestDefinitionDeleteGcGetCompat:
    """GET /api/definition/delete-to-gc（query 传 id）应真实软删进回收站。"""

    def _make(self, client):
        name = _new_name("definition-get-gc")
        r = client.post("/api/definition/add", json={
            "name": name, "method": "GET", "path": "/api/gc-demo",
        })
        assert r.status_code == 200, r.text
        return _data(r).get("id")

    def test_get_delete_to_gc_soft_deletes(self, client):
        did = self._make(client)
        # GET query 传 id 软删
        r = client.get(f"/api/definition/delete-to-gc?id={did}")
        assert r.status_code == 200, r.text
        # 软删后在回收站分页可见
        r = client.post("/api/definition/page", json={
            "deleted": True, "current": 1, "pageSize": 100,
        })
        assert any(x.get("id") == did for x in _data(r).get("list", [])), \
            "GET delete-to-gc 软删后应出现在回收站"
