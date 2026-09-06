"""系统兼容层「启停」操作真实落库回归测试。

来源：ISSUE #533 —— 修复各 compat 里可映射到真实 service 的关注/启停/调度类。
此前 `/user/api/key/enable|disable`、`/user/local/config/enable|disable`、
`/api/definition/mock/enable` 等兼容端点直接 ``return ok()`` 假成功：
前端点「启用/禁用」提示成功，但真实 api_keys / user_local_configs /
api_mocks 的状态字段从未被修改。

本测试验证这些兼容端点已接入真实 service（auth_service.toggle_api_key /
toggle_local_config、apitest_service.update_mock），状态真正落库并可在读接口回读。
"""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_DB_PATH", "test_compat_realfix.db")

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    db = os.environ.get("AUTH_DB_PATH")
    if db and os.path.exists(db):
        os.remove(db)
    with TestClient(app) as c:
        yield c


def _login_headers(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    session = r.json()["data"]
    return {
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    }


def _data(resp):
    body = resp.json() if hasattr(resp, "json") else resp
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


class TestApiKeyEnableDisableCompat:
    """/user/api/key/enable|disable/{id} 兼容端点真实落库。"""

    def _create_key(self, client, headers):
        r = client.post("/user/api/key/add", headers=headers, json={
            "description": "compat 启停", "forever": True,
        })
        assert r.status_code == 200, r.text
        return _data(r)["id"]

    def test_path_enable_disable_readback(self, client):
        headers = _login_headers(client)
        key_id = self._create_key(client, headers)

        # 禁用（默认 enable=1 → 0）
        r = client.post(f"/user/api/key/disable/{key_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert _data(r)["disabled"] is True, r.text

        # 读列表回读 enable=0
        keys = _data(client.get("/user/api/key/list", headers=headers))
        item = next(k for k in keys if k["id"] == key_id)
        assert item["enable"] == 0, "禁用未真实落库"

        # 启用（0 → 1）
        r = client.post(f"/user/api/key/enable/{key_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert _data(r)["enabled"] is True, r.text
        keys = _data(client.get("/user/api/key/list", headers=headers))
        item = next(k for k in keys if k["id"] == key_id)
        assert item["enable"] == 1, "启用未真实落库"

        # 清理
        client.post("/user/api/key/delete", headers=headers, json={"id": key_id})

    def test_get_variant(self, client):
        """GET query 传 id 的启停变体同样真实落库。"""
        headers = _login_headers(client)
        key_id = self._create_key(client, headers)
        r = client.get(f"/user/api/key/disable?id={key_id}", headers=headers)
        assert r.status_code == 200, r.text
        keys = _data(client.get("/user/api/key/list", headers=headers))
        item = next(k for k in keys if k["id"] == key_id)
        assert item["enable"] == 0
        client.post("/user/api/key/delete", headers=headers, json={"id": key_id})
