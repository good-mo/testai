"""项目管理-版本页面接口集成测试。

覆盖 projectVersion 页面所有前端 API 调用的路径、方法和响应格式，
确保路径参数路由存在且返回前端期望的数据结构。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app


def _client():
    client = TestClient(app)
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })
    return client


def test_get_version_enable_returns_bool():
    """GET /project/version/enable/{project_id} 应返回 boolean（前端期望）。"""
    client = _client()
    pid = f"proj-v-{uuid.uuid4().hex[:8]}"
    r = client.get(f"/project/version/enable/{pid}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, bool), f"data type={type(data).__name__}, value={data}"


def test_toggle_version_enable():
    """GET /project/version/switch/enable/{project_id} 应能切换版本启用状态。"""
    client = _client()
    pid = f"proj-v-{uuid.uuid4().hex[:8]}"
    r = client.get(f"/project/version/enable/{pid}")
    assert r.json()["data"] is False
    r = client.get(f"/project/version/switch/enable/{pid}")
    assert r.status_code == 200
    r = client.get(f"/project/version/enable/{pid}")
    assert r.json()["data"] is True


def test_version_crud_full_flow():
    """项目版本完整 CRUD 流程。"""
    client = _client()
    pid = f"proj-v-{uuid.uuid4().hex[:8]}"

    # 添加版本
    r = client.post("/project/version/add", json={
        "projectId": pid, "name": "v1.0", "description": "test",
        "status": False, "latest": False, "publishTime": 1700000000000,
    })
    assert r.status_code == 200
    vid = r.json()["data"]["id"]
    assert vid, "创建版本应返回 id"

    # 列表（POST）
    r = client.post("/project/version/list", json={"projectId": pid, "current": 1, "pageSize": 10})
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, dict)
    assert "list" in data and "total" in data
    assert data["total"] == 1
    item = data["list"][0]
    for key in ("id", "name", "status", "latest", "publishTime", "createTime", "createUser", "projectId"):
        assert key in item, f"版本项缺少字段 {key}"

    # 切换状态
    r = client.get(f"/project/version/switch/status/{vid}")
    assert r.status_code == 200

    # 设为最新
    r = client.get(f"/project/version/switch/latest/{vid}")
    assert r.status_code == 200

    # 选项列表
    r = client.get(f"/project/version/option/{pid}")
    assert r.status_code == 200
    opts = r.json()["data"]
    assert isinstance(opts, list)
    if opts:
        assert "id" in opts[0] and "name" in opts[0]
        assert "latest" in opts[0] and "enable" in opts[0]

    # 更新
    r = client.post("/project/version/update", json={
        "id": vid, "name": "v1.0-updated", "status": True,
    })
    assert r.status_code == 200

    # 删除
    r = client.get(f"/project/version/delete/{vid}")
    assert r.status_code == 200

    # 验证删除
    r = client.post("/project/version/list", json={"projectId": pid, "current": 1, "pageSize": 10})
    assert r.json()["data"]["total"] == 0


def test_version_list_accepts_post_body():
    """POST /project/version/list 应解析 body 中的 projectId。"""
    client = _client()
    pid = f"proj-v-{uuid.uuid4().hex[:8]}"
    client.post("/project/version/add", json={"projectId": pid, "name": "x", "latest": False})

    # POST with body projectId (frontend actual call pattern)
    r = client.post("/project/version/list", json={"projectId": pid, "current": 1, "pageSize": 20})
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, dict)
    assert "list" in data
    assert data["total"] >= 1


def test_version_routes_with_path_and_query_params():
    """验证版本路由同时支持路径参数和 query 参数。"""
    client = _client()
    pid = "default-project"
    # Path param pattern (frontend actual)
    r = client.get(f"/project/version/enable/{pid}")
    assert r.status_code == 200
    # Query param pattern (legacy)
    r2 = client.get("/project/version/enable", params={"projectId": pid})
    assert r2.status_code == 200
