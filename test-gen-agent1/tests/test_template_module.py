# tests/test_template_module.py
"""项目管理模板模块接口契约回归测试。

覆盖 projectManagementTemplate 页面「模板管理」链路：
  - 模板列表返回数组（useTable 依赖数组，桩返回对象会导致列表空）
  - 模板详情返回 name/customFields 等完整字段（桩只回 {id} 使编辑页空白）
  - 新增/编辑/删除/设置默认真实落库且可查可删
  - set-default 路径参数顺序与前端一致 /project/template/set-default/{projectId}/{id}
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


def _login(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })
    return client


def _client():
    import app.main
    client = TestClient(app.main.app)
    return _login(client)


def test_project_template_list_returns_array():
    """项目模板列表应返回数组（前端模板管理表格依赖）。"""
    client = _client()
    pid = f"proj-tpl-{uuid.uuid4().hex[:8]}"
    resp = client.get(f"/project/template/list/{pid}/FUNCTIONAL")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert data, "范围内无模板时应播种默认模板，列表不应为空"
    row = data[0]
    for key in ("id", "name", "scene", "scopeId", "customFields", "systemFields"):
        assert key in row, f"列表行缺少字段 {key}"


def test_project_template_get_returns_full_detail():
    """模板详情应返回完整对象（含 name/customFields/systemFields）。"""
    client = _client()
    pid = f"proj-tpl-{uuid.uuid4().hex[:8]}"
    lst = client.get(f"/project/template/list/{pid}/BUG").json()["data"]
    tid = lst[0]["id"]
    resp = client.get(f"/project/template/get/{tid}")
    data = resp.json()["data"]
    assert resp.json()["code"] == 200
    assert data.get("name")
    assert "customFields" in data
    assert "systemFields" in data


def test_project_template_crud_persists():
    """项目模板增删改查应真实落库并保持一致。"""
    client = _client()
    pid = f"proj-tpl-{uuid.uuid4().hex[:8]}"
    # 新增
    created = client.post("/project/template/add", json={
        "name": "契约测试模板", "remark": "r", "scene": "FUNCTIONAL",
        "scopeId": pid, "customFields": [], "systemFields": [],
    }).json()["data"]
    assert created.get("id")
    tid = created["id"]
    # 列表包含新增
    names = [t["name"] for t in client.get(f"/project/template/list/{pid}/FUNCTIONAL").json()["data"]]
    assert "契约测试模板" in names
    # 详情
    got = client.get(f"/project/template/get/{tid}").json()["data"]
    assert got["name"] == "契约测试模板"
    # 设置默认（前端参数顺序 {projectId}/{templateId}）
    sd = client.get(f"/project/template/set-default/{pid}/{tid}")
    assert sd.status_code == 200
    assert sd.json()["code"] == 200
    # 更新
    upd = client.post("/project/template/update", json={
        "id": tid, "name": "改名模板", "scene": "FUNCTIONAL",
        "scopeId": pid, "customFields": [], "systemFields": [],
    })
    assert upd.json()["data"]["name"] == "改名模板"
    # 删除
    dele = client.get(f"/project/template/delete/{tid}")
    assert dele.json()["data"]["deleted"] is True
    names = [t["name"] for t in client.get(f"/project/template/list/{pid}/FUNCTIONAL").json()["data"]]
    assert "改名模板" not in names


def test_org_template_list_returns_array():
    """组织模板列表应返回数组。"""
    client = _client()
    resp = client.get("/organization/template/list/default-org/BUG")
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert data
    assert data[0].get("name")


def test_org_template_get_full_detail():
    """组织模板详情应返回完整字段。"""
    client = _client()
    oid = "default-org"
    lst = client.get(f"/organization/template/list/{oid}/FUNCTIONAL").json()["data"]
    tid = lst[0]["id"]
    resp = client.get(f"/organization/template/get/{tid}")
    data = resp.json()["data"]
    assert data.get("name")
    assert "customFields" in data


def test_org_template_crud_persists():
    """组织模板增删应真实落库。"""
    client = _client()
    oid = "default-org"
    created = client.post("/organization/template/add", json={
        "name": "组织契约测试", "scene": "API", "scopeId": oid,
        "customFields": [], "systemFields": [],
    }).json()["data"]
    assert created.get("id")
    tid = created["id"]
    names = [t["name"] for t in client.get(f"/organization/template/list/{oid}/API").json()["data"]]
    assert "组织契约测试" in names
    dele = client.get(f"/organization/template/delete/{tid}")
    assert dele.json()["data"]["deleted"] is True
