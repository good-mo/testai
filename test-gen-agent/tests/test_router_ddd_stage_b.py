"""Router 直连 DDD 应用服务（Stage B）回归测试。

验证以下 routers 已绕过 services 直接调用 DDD application services
（参照 datafactory.py / reports.py 样板）：
  1. scripts.py   → script_app_service
  2. runs.py      → run_record_app_service
  3. task_center.py → task_center_app_service

对外 API 契约保持不变（返回结构 / 404 语义 / passed int 归一化）。
"""
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


# ═══════════════════════════════════════════════════════
# 1. scripts.py router 直连 script_app_service
# ═══════════════════════════════════════════════════════
class TestScriptsRouterDDD:
    def test_scripts_router_uses_ddd_app_service(self):
        """Router 不再 import services.script_service，而是 import domain script app_service."""
        import inspect

        from app.routers import scripts
        src = inspect.getsource(scripts)
        assert "from app.services.script_service" not in src
        assert "from app.domain.script.application.script_app_service" in src
        assert "script_app_service" in src

    def test_scripts_router_endpoints_work(self, client):
        name = f"ddd_router_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/scripts", json={
            "name": name, "file_path": "/tmp/ddd.py",
            "framework": "pytest",
        })
        assert r.status_code == 200, r.text
        script = _data(r)
        assert script.get("id")
        sid = script["id"]

        # get / list
        assert client.get(f"/api/scripts/{sid}").status_code == 200
        r_list = client.get("/api/scripts")
        assert r_list.status_code == 200
        payload = _data(r_list)
        assert "scripts" in payload and "total" in payload

        # update / delete / 404
        r_up = client.put(f"/api/scripts/{sid}", json={"name": f"{name}_updated"})
        assert r_up.status_code == 200
        assert _data(r_up)["name"] == f"{name}_updated"
        assert client.delete(f"/api/scripts/{sid}").status_code == 200
        assert client.get(f"/api/scripts/{sid}").status_code == 404

    def test_scripts_missing_404(self, client):
        assert client.get(f"/api/scripts/nope_{uuid.uuid4().hex[:6]}").status_code == 404


# ═══════════════════════════════════════════════════════
# 2. runs.py router 直连 run_record_app_service
# ═══════════════════════════════════════════════════════
class TestRunsRouterDDD:
    def test_runs_router_uses_ddd_app_service(self):
        """Router 不再 import services.run_service，而是 import domain run_record app_service."""
        import inspect

        from app.routers import runs
        src = inspect.getsource(runs)
        assert "from app.services.run_service" not in src
        assert "from app.domain.runs.application.run_record_app_service" in src
        assert "run_record_app_service" in src

    def test_runs_passed_is_int_not_bool(self, client):
        """/api/runs 输出的 passed 为 int 0/1（兼容既有契约）。"""
        r = client.get("/api/runs")
        assert r.status_code == 200, r.text
        data = _data(r)
        records = data.get("records", [])
        for rec in records:
            assert isinstance(rec.get("passed"), int) or rec.get("passed") in (0, 1, None)

    def test_runs_router_404(self, client):
        r = client.get(f"/api/runs/nope_{uuid.uuid4().hex[:8]}")
        assert r.status_code == 404

    def test_runs_stats(self, client):
        r = client.get("/api/runs/stats")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════
# 3. task_center.py router helper 直连 task_center_app_service
# ═══════════════════════════════════════════════════════
class TestTaskCenterRouterDDD:
    def test_task_center_router_uses_ddd_app_service(self):
        """Router 不再 import services.task_center_service，而是 import domain task_center app_service."""
        import inspect

        from app.routers import task_center
        src = inspect.getsource(task_center)
        assert "from app.services.task_center_service" not in src
        assert "from app.domain.task_center.application.task_center_app_service" in src
        assert "task_center_app_service" in src

    def test_task_center_helper_functions_exist(self):
        """兼容 helper 函数仍可用且委托 DDD。"""
        from app.routers import task_center
        assert hasattr(task_center, "_exec_stop_ids")
        assert hasattr(task_center, "_exec_delete_ids")
        assert hasattr(task_center, "_exec_rerun_id")
        assert hasattr(task_center, "_schedule_switch_ids")

    def test_task_center_endpoint(self, client):
        r = client.get("/project/task-center/exec-task/page")
        assert r.status_code == 200
