"""用户视图（user-view）落库读回闭环回归测试。

来源：ISSUE #533（auth/router、system_compat 等大量「进程内 dict/空壳」端点）。
背景：此前 `/user-view/{view_type}/add|update|delete` 与 `grouped/list` 均基于进程内
dict `_user_views`（key=`view_type:scope_id`），进程重启即丢、多 worker 不共享，
保存成功但数据不落库、跨会话读不回——属「假成功」。

本测试验证：
  - 新增视图后落库，grouped/list 可读回该自定义视图；
  - 新增时附带的 conditions/searchMode 读回一致；
  - update 合并字段后 grouped/list/get 读回新值；
  - delete 后 grouped/list 不再返回该视图（真实落库删除）；
  - 跨连接读回：直接以新连接/独立 store 查询确认写入了 user_views 表，
    证明不再依赖进程内 dict。
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


VIEW_TYPE = "functional"
SCOPE = "user-view-persist-proj"


def _list_custom(client):
    resp = client.get(f"/user-view/{VIEW_TYPE}/grouped/list", params={"scopeId": SCOPE})
    assert resp.status_code == 200, resp.text
    data = _data(resp)
    return data.get("customViews", []), data.get("internalViews", [])


class TestUserViewPersist:
    def test_add_grouped_readback_update_delete(self, client):
        # 清理历史残留，保证断言干净
        existing, _ = _list_custom(client)
        for v in existing:
            client.get(f"/user-view/{VIEW_TYPE}/delete/{v['id']}")

        # 1. 新增视图（带 conditions / searchMode）
        add_body = {
            "scopeId": SCOPE,
            "name": "持久化视图",
            "searchMode": "OR",
            "conditions": [{"field": "priority", "operator": "eq", "value": "P1"}],
        }
        resp = client.post(f"/user-view/{VIEW_TYPE}/add", json=add_body)
        assert resp.status_code == 200, resp.text
        added = _data(resp)
        assert added.get("name") == "持久化视图", resp.text
        assert added.get("internal") is False
        vid = added.get("id")
        assert vid, resp.text

        try:
            # 2. grouped/list 读回（落库后可见）
            customs, internals = _list_custom(client)
            ids = [v["id"] for v in customs]
            assert vid in ids, f"新增视图未在 grouped/list 读回: {customs}"
            found = next(v for v in customs if v["id"] == vid)
            assert found.get("name") == "持久化视图"
            # internalViews 由后端动态生成、不落库，仍应含默认 all_data
            assert any(v.get("id") == "all_data" for v in internals)

            # 3. get 详情读回完整字段（conditions/searchMode）
            resp = client.get(f"/user-view/{VIEW_TYPE}/get/{vid}")
            assert resp.status_code == 200, resp.text
            detail = _data(resp)
            assert detail.get("name") == "持久化视图"
            assert detail.get("searchMode") == "OR"
            assert detail.get("conditions") == add_body["conditions"]

            # 4. update 合并字段后读回新值
            resp = client.post(f"/user-view/{VIEW_TYPE}/update",
                               json={"id": vid, "name": "改名后的视图", "searchMode": "AND"})
            assert resp.status_code == 200, resp.text
            customs, _ = _list_custom(client)
            found = next(v for v in customs if v["id"] == vid)
            assert found.get("name") == "改名后的视图"
            assert found.get("searchMode") == "AND"
            # 未被覆盖的自定义字段仍保留（合并而非覆盖整对象）
            detail = _data(client.get(f"/user-view/{VIEW_TYPE}/get/{vid}"))
            assert detail.get("conditions") == add_body["conditions"]

            # 5. 独立连接确认写入 user_views 表（不依赖进程内 dict）
            from app.repositories.user_view_repo import user_view_repo
            db_view = user_view_repo.get_custom_view(vid)
            assert db_view is not None, "user_views 表无记录，说明未真正落库"
            assert db_view.get("name") == "改名后的视图"
        finally:
            # 6. 删除后 grouped/list 不再返回该视图
            resp = client.get(f"/user-view/{VIEW_TYPE}/delete/{vid}")
            assert resp.status_code == 200, resp.text
            customs, _ = _list_custom(client)
            assert vid not in [v["id"] for v in customs], "删除后视图仍存在"
            from app.repositories.user_view_repo import user_view_repo
            assert user_view_repo.get_custom_view(vid) is None, "删除未落库生效"

    def test_update_non_exist_returns_ok_no_error(self, client):
        # 更新不存在的视图不应 5xx（保持原行为 ok()）
        resp = client.post(f"/user-view/{VIEW_TYPE}/update",
                           json={"id": "not-exist-view", "name": "x"})
        assert resp.status_code == 200, resp.text
