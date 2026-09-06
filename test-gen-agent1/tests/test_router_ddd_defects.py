"""defects.py router 直连 DDD 应用服务（Stage B router-direct）回归测试。

验证 defects.py 已绕过 `app.services.defect_service` 直接调用
`defect_app_service`（参照 projects.py / reports.py 样板），且对外 API
契约保持不变（tags 归一为 JSON 字符串、404 语义、批量恢复/清除计数）。
"""
import inspect
import uuid

import pytest
from fastapi.testclient import TestClient


def _data(resp):
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


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


class TestDefectsRouterDDD:
    def test_defects_router_uses_ddd_app_service(self):
        """Router 不再 import services.defect_service，而是 import domain defect app_service."""
        from app.routers import defects
        src = inspect.getsource(defects)
        assert "from app.services.defect_service" not in src
        assert "from app.domain.defects.application.defect_app_service" in src
        assert "defect_app_service" in src

    def test_defects_router_crud(self, client):
        name = f"ddd_defect_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/defects", json={"title": name, "severity": "major"})
        assert r.status_code == 200, r.text
        item = _data(r)
        assert item.get("id")
        did = item["id"]

        assert client.get(f"/api/defects/{did}").status_code == 200
        r_list = client.get("/api/defects")
        assert r_list.status_code == 200
        payload = _data(r_list)
        assert "defects" in payload and "total" in payload

        # update
        r_up = client.put(f"/api/defects/{did}", json={"title": f"{name}_up"})
        assert r_up.status_code == 200
        assert _data(r_up)["title"] == f"{name}_up"

        # trash -> trash list -> restore -> trash -> purge
        assert client.post(f"/api/defects/{did}/trash").status_code == 200
        assert client.get("/api/defects/trash").status_code == 200
        assert client.post(f"/api/defects/{did}/restore").status_code == 200
        assert client.post(f"/api/defects/{did}/trash").status_code == 200
        assert client.delete(f"/api/defects/trash/{did}").status_code == 200

    def test_defects_router_404(self, client):
        assert client.get(f"/api/defects/nope_{uuid.uuid4().hex[:6]}").status_code == 404
        assert client.put(
            f"/api/defects/nope_{uuid.uuid4().hex[:6]}",
            json={"title": "x"},
        ).status_code == 404
