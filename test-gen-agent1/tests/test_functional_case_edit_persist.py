"""功能用例「编辑」持久化回归测试。

对应 ISSUE #400：功能用例列表行内「编辑」保存后，
模块（moduleId）/ 标签（tags）/ 前置条件（prerequisite）
曾因后端 /functional/case/update 未映射被静默丢弃，表现为
“编辑没反应、保存不生效、一刷新就被还原”。
本测试确保这些字段能真实落库并回读一致。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
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


def test_functional_case_update_persists_module_tags_prereq(client):
    # 准备一个功能用例模块
    r = client.post("/functional/case/module/add", json={"name": "编辑持久化模块", "parentId": "root"})
    assert r.status_code == 200, r.text
    mod_id = _data(r).get("id")
    assert mod_id, r.text

    # 创建一个功能用例
    r = client.post("/functional/case/add", json={"name": "编辑持久化用例", "priority": "P2"})
    assert r.status_code == 200, r.text
    case_id = _data(r).get("id")
    assert case_id, r.text

    # 模拟前端“编辑”保存：改模块 / 标签 / 前置条件
    payload = {
        "id": case_id,
        "name": "编辑持久化用例-改",
        "priority": "P0",
        "moduleId": mod_id,
        "tags": ["冒烟", "回归"],
        "prerequisite": "前置条件A",
        "description": "desc",
    }
    r = client.post("/functional/case/update", json=payload)
    assert r.status_code == 200, r.text
    out = _data(r)
    assert out["moduleId"] == mod_id, f"moduleId 未持久化: {out.get('moduleId')}"
    assert set(out["tags"]) == {"冒烟", "回归"}, f"tags 未持久化: {out.get('tags')}"
    assert out["prerequisite"] == "前置条件A", f"prerequisite 未持久化: {out.get('prerequisite')}"
    assert out["priority"] == "P0"
    assert out["moduleName"] == "编辑持久化模块"

    # 重新读取详情，验证已落库
    r = client.get(f"/functional/case/detail/{case_id}")
    assert r.status_code == 200, r.text
    detail = _data(r)
    assert detail["moduleId"] == mod_id
    assert detail["moduleName"] == "编辑持久化模块"
    assert set(detail["tags"]) == {"冒烟", "回归"}
    assert detail["prerequisite"] == "前置条件A"

    # 清理
    client.post("/functional/case/delete", json={"id": case_id})
    client.post(f"/functional/case/module/delete/{mod_id}")
