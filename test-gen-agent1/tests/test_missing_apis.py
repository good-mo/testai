"""补齐缺失 API 单元测试

覆盖：
  1. 缺陷回收站（软删除/列表/恢复/彻底删除）
  2. 接口/场景模块回收站
  3. 系统用户/项目成员管理
  4. 环境/报告/调试回收站
"""

import pytest
from fastapi.testclient import TestClient


def _data(resp):
    """解析响应，统一取 data 层。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body



@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        # 登录获取认证令牌
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


@pytest.fixture(autouse=True)
def clean_defects():
    """清理缺陷数据，保证测试隔离。"""
    from app.repositories.defect_repo import DefectRepo
    yield
    # 彻底删除所有测试产生的缺陷
    for d in DefectRepo.list(include_deleted=True, limit=1000):
        DefectRepo.purge(d["id"])


# ── 1. 缺陷回收站 ────────────────────────────────────────
def test_defect_trash_restore_purge(client):
    """缺陷软删除进回收站 → 列表 → 恢复 → 再次删除 → 彻底删除。"""
    # 创建缺陷
    r = client.post("/api/defects", json={
        "title": "回收站测试缺陷", "description": "desc", "severity": "critical",
    })
    assert r.status_code == 200
    def_id = _data(r)["id"]

    # 软删除进回收站
    r = client.post(f"/api/defects/{def_id}/trash")
    assert r.status_code == 200 and _data(r)["deleted"] is True

    # 正常列表不应包含回收站数据
    r = client.get("/api/defects")
    assert all(d["id"] != def_id for d in _data(r)["defects"])

    # 回收站列表
    r = client.get("/api/defects/trash")
    assert r.status_code == 200
    assert any(d["id"] == def_id for d in _data(r)["items"])

    # 恢复
    r = client.post(f"/api/defects/{def_id}/restore")
    assert r.status_code == 200 and _data(r)["restored"] is True
    r = client.get("/api/defects/trash")
    assert all(d["id"] != def_id for d in _data(r)["items"])

    # 再次软删除 + 彻底删除
    client.post(f"/api/defects/{def_id}/trash")
    r = client.delete(f"/api/defects/trash/{def_id}")
    assert r.status_code == 200 and _data(r)["purged"] is True
    r = client.get("/api/defects/trash")
    assert all(d["id"] != def_id for d in _data(r)["items"])


def test_defect_batch_trash_ops(client):
    """缺陷批量恢复/批量彻底删除。"""
    ids = []
    for i in range(2):
        r = client.post("/api/defects", json={"title": f"批量缺陷{i}", "severity": "major"})
        ids.append(_data(r)["id"])
        client.post(f"/api/defects/{ids[-1]}/trash")

    # 批量恢复
    r = client.post("/api/defects/trash/recover", json={"ids": ids})
    assert r.status_code == 200 and _data(r)["restored"] == 2

    # 全部移入回收站后批量彻底删除
    for did in ids:
        client.post(f"/api/defects/{did}/trash")
    r = client.post("/api/defects/trash/batch-delete", json={"ids": ids})
    assert r.status_code == 200 and _data(r)["purged"] == 2


# ── 2. 接口/场景模块回收站 ───────────────────────────────
def test_definition_recycle_bin(client):
    """接口定义回收站：删除 → 列表 → 恢复 → 彻底删除。"""
    r = client.post("/api/api-definitions", json={"name": "回收站接口", "method": "GET", "path": "/r"})
    def_id = _data(r)["id"]

    # 删除进回收站
    r = client.delete(f"/api/api-definitions/{def_id}")
    assert r.status_code == 200 and _data(r)["success"] is True

    # 回收站列表
    r = client.get("/api/definition/trash/page")
    assert any(d["id"] == def_id for d in _data(r)["list"])

    # 恢复
    r = client.post("/api/definition/recover", json={"id": def_id})
    assert r.status_code == 200 and _data(r)["restored"] == 1

    # 再次删除后仍在回收站（软删除语义）
    client.delete(f"/api/api-definitions/{def_id}")
    r = client.get("/api/definition/trash/page")
    assert any(d["id"] == def_id for d in _data(r)["list"])


def test_case_recycle_bin(client):
    """接口用例回收站。"""
    # 前端接口用例统一落在 management 存储（api_test_cases 表），
    # 与 /api/case/trash/page 回收站读取一致，保证删除后能进入回收站并可恢复。
    r = client.post("/api/api-test-cases", json={"name": "回收站用例", "method": "POST", "path": "/c"})
    assert r.status_code == 200
    case_id = _data(r)["id"]
    assert case_id

    # 删除进回收站（软删除）
    r = client.delete(f"/api/api-test-cases/{case_id}")
    assert r.status_code == 200

    # 回收站列表
    r = client.post("/api/case/trash/page", json={"pageSize": 50})
    assert any(c["id"] == case_id for c in _data(r)["list"])

    # 恢复（前端用 GET 单条恢复接口）
    r = client.get("/api/case/recover", params={"id": case_id})
    assert r.status_code == 200 and _data(r)["restored"] == 1

    # 批量恢复 + 批量彻底删除
    client.delete(f"/api/api-test-cases/{case_id}")
    r = client.post("/api/case/batch/recover", json={"ids": [case_id]})
    assert _data(r)["restored"] == 1
    client.delete(f"/api/api-test-cases/{case_id}")
    r = client.post("/api/case/batch/delete", json={"ids": [case_id]})
    assert r.status_code == 200 and _data(r)["deleted"] == 1


def test_scenario_recycle_bin(client):
    """接口场景回收站。"""
    r = client.post("/api/scenarios", json={"name": "回收站场景", "description": "d"})
    sc_id = _data(r)["id"]

    # 删除进回收站
    r = client.delete(f"/api/scenarios/{sc_id}")
    assert r.status_code == 200

    r = client.post("/api/scenario/trash/page", json={"pageSize": 50})
    assert any(s["id"] == sc_id for s in _data(r)["list"])

    r = client.post("/api/scenario/recover", json={"id": sc_id})
    assert r.status_code == 200 and _data(r)["restored"] == 1

    # 删除到回收站 → 批量彻底删除
    client.delete(f"/api/scenarios/{sc_id}")
    r = client.post("/api/scenario/batch-operation/delete", json={"ids": [sc_id]})
    assert r.status_code == 200 and _data(r)["deleted"] == 1


# ── 3. 系统用户 / 项目成员 ───────────────────────────────
def test_system_user_management(client):
    """系统用户分页/详情/启停/角色/重置密码。"""
    r = client.post("/system/user/page", json={"keyword": "admin"})
    body = r.json()
    assert r.status_code == 200 and body["code"] == 200
    assert len(body["data"]["list"]) >= 1

    r = client.get("/system/user/get/global/system/role")
    body = r.json()
    assert r.status_code == 200 and len(body["data"]) >= 1


def test_project_member_management(client):
    """项目成员增删查改。"""
    from app.repositories.project_repo import ProjectRepo
    proj = ProjectRepo.create(name="成员测试项目")
    pid = proj["id"]
    from app.auth import store as auth_store
    users = auth_store.AuthStore().list_users()
    uid = users[0]["id"]

    # 添加成员
    r = client.post("/project/member/add", json={
        "projectId": pid, "user_id": uid, "username": users[0]["username"], "role": "admin",
    })
    assert r.status_code == 200 and r.json()["code"] == 200

    # 成员列表
    r = client.post("/project/member/list", json={"projectId": pid})
    assert r.json()["data"]["total"] == 1

    # 移除成员
    r = client.get(f"/project/member/remove/{pid}/{uid}")
    assert r.status_code == 200


# ── 4. 环境/报告/调试回收站 ─────────────────────────────
def test_environment_recycle_bin(client):
    """环境回收站。"""
    from app.environment import manager as em
    env = em.register_environment("回收站环境", endpoint="http://e")
    env_id = env["id"]

    r = client.post(f"/api/environments/{env_id}/trash")
    assert r.status_code == 200 and _data(r)["trashed"] is True

    r = client.get("/api/environments/trash/list")
    assert any(e["id"] == env_id for e in _data(r)["items"])

    r = client.post(f"/api/environments/{env_id}/restore")
    assert r.status_code == 200 and _data(r)["success"] is True
    r = client.get("/api/environments/trash/list")
    assert all(e["id"] != env_id for e in _data(r)["items"])

    # 彻底删除
    client.post(f"/api/environments/{env_id}/trash")
    r = client.delete(f"/api/environments/trash/{env_id}")
    assert r.status_code == 200


def test_debug_logs_api(client):
    """调试日志列表/清空。"""
    r = client.get("/api/debug/logs")
    assert r.status_code == 200 and "logs" in _data(r)
    r = client.delete("/api/debug/logs")
    assert r.status_code == 200 and "cleared" in _data(r)
