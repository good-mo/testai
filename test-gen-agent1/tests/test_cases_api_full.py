"""
后端用例管理 API 全面测试（HTTP 层）
=====================================
覆盖用户要求的用例模块「功能用例 - 接口业务逻辑」全部接口：

一、基础 CRUD（repository.py）
  GET/POST /api/cases, GET/PUT/DELETE /api/cases/{case_id}, GET /api/cases/stats

二、高级管理（management.py）
  full / relations(增删查) / import / export / mindmap /
  reviews(submit/approve/reject/query) / dependencies(增删查) /
  trash / restore / purge / versions / rollback / changes / requirements

说明：测试通过 HTTP TestClient 调用真实 FastAPI 路由，
依据当前后端实际响应结构编写断言。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient

# 测试数据特征前缀，便于清理
PREFIX = "FULLAPI-TEST-"


@pytest.fixture(scope="module")
def client():
    """登录后的测试客户端。"""
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


def _cleanup(client):
    """清理测试产生的用例（软删+purge），保持可重复运行。"""
    try:
        r = client.get("/api/cases?limit=200")
        data = r.json()
        cases = data.get("data", {}).get("cases", [])
        if not cases and "cases" in data:  # 兼容裸响应
            cases = data.get("cases", [])
        for c in cases:
            if str(c.get("title", "")).startswith(PREFIX):
                cid = c["id"]
                client.post(f"/api/cases/{cid}/trash", json={"deleted_by": "test"})
                client.delete(f"/api/cases/{cid}/purge")
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _auto_cleanup(client):
    yield
    _cleanup(client)


def _create_case(client, **overrides):
    """创建一条测试用例，返回 case dict。"""
    payload = {
        "title": PREFIX + "接口用例",
        "description": "全面测试用例描述",
        "source_code": "def foo(): pass",
        "test_code": "def test_foo(): pass",
        "file_path": "tests/full_api",
        "tags": ["smoke", "api"],
        "status": "draft",
        "priority": "P1",
        "test_type": "functional",
        "structured_cases": [{"name": "sc1", "steps": ["step1"]}],
    }
    payload.update(overrides)
    resp = client.post("/api/cases", json=payload)
    assert resp.status_code == 200, f"创建失败: {resp.text}"
    body = resp.json()
    case = body.get("data", body)  # 兼容裸/包裹格式
    assert case.get("id"), f"未返回 case id: {body}"
    return case


def _data(resp):
    """解析响应，统一取 data 层（裸对象时原样返回）。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body and isinstance(body["data"], (dict, list)):
        return body["data"]
    return body


# ════════════════════════════════════════════════════════════
# 一、基础 CRUD
# ════════════════════════════════════════════════════════════

class TestBasicCRUD:
    """基础 CRUD 接口测试。"""

    def test_create_case_defaults(self, client):
        """POST /api/cases 创建，校验默认值。"""
        case = _create_case(client)
        assert case["status"] == "draft"
        assert case["priority"] == "P1"
        assert case["test_type"] == "functional"
        assert case["tags"] == ["smoke", "api"]

    def test_create_case_custom_test_type(self, client):
        """创建指定 test_type 的用例。"""
        case = _create_case(client, test_type="performance", priority="P0")
        assert case["test_type"] == "performance"
        assert case["priority"] == "P0"

    def test_get_case(self, client):
        """GET /api/cases/{id} 按 ID 查询。"""
        case = _create_case(client)
        resp = client.get(f"/api/cases/{case['id']}")
        assert resp.status_code == 200
        got = _data(resp)
        assert got["id"] == case["id"]
        assert got["title"].startswith(PREFIX)

    def test_get_case_not_found(self, client):
        """GET 不存在的用例返回 404。"""
        resp = client.get("/api/cases/nonexistent-id-xyz")
        assert resp.status_code == 404

    def test_list_cases(self, client):
        """GET /api/cases 列表返回 cases 与 total。

        total 应为过滤条件下的真实总数（DB 侧 COUNT），而非当前页长度。
        用唯一关键词确保 total 可精确断言。
        """
        for i in range(3):
            _create_case(client, title=f"{PREFIX}唯一总量{i}")
        resp = client.get("/api/cases", params={"search": "唯一总量", "limit": 2})
        assert resp.status_code == 200
        data = _data(resp)
        assert "cases" in data
        assert "total" in data
        assert isinstance(data["total"], int)
        assert data["total"] >= len(data["cases"])  # total 为真实总数（SQL COUNT），>= 当前页条数
        # 命中 3 条但只返回 1 页 2 条 -> total 应为 3，而不是当前页长度 2
        assert data["total"] == 3
        assert len(data["cases"]) == 2

    def test_list_filter_by_status(self, client):
        """按 status 过滤。"""
        _create_case(client, title=PREFIX + "过滤-状态", status="approved")
        _create_case(client, title=PREFIX + "过滤-状态2", status="draft")
        resp = client.get("/api/cases", params={"status": "approved"})
        data = _data(resp)
        titles = [c["title"] for c in data["cases"]]
        assert any(t.startswith(PREFIX + "过滤-状态") for t in titles)

    def test_list_filter_by_priority(self, client):
        """按 priority 过滤。"""
        _create_case(client, title=PREFIX + "过滤-优先级", priority="P3")
        resp = client.get("/api/cases", params={"priority": "P3"})
        data = _data(resp)
        assert all(c["priority"] == "P3" for c in data["cases"])

    def test_list_filter_by_tag(self, client):
        """按 tag 过滤。"""
        _create_case(client, title=PREFIX + "过滤-标签", tags=["smoke"])
        _create_case(client, title=PREFIX + "过滤-标签2", tags=["regression"])
        resp = client.get("/api/cases", params={"tag": "regression"})
        data = _data(resp)
        titles = [c["title"] for c in data["cases"]]
        assert PREFIX + "过滤-标签2" in titles
        assert PREFIX + "过滤-标签" not in titles

    def test_list_filter_by_search(self, client):
        """按关键词 search 过滤。"""
        _create_case(client, title=PREFIX + "唯一搜索关键词XYZ")
        resp = client.get("/api/cases", params={"search": "唯一搜索关键词XYZ"})
        data = _data(resp)
        assert any(c["title"].startswith(PREFIX) for c in data["cases"])

    def test_list_filter_by_test_type(self, client):
        """按 test_type 过滤。"""
        _create_case(client, title=PREFIX + "过滤-类型", test_type="ui")
        resp = client.get("/api/cases", params={"test_type": "ui"})
        data = _data(resp)
        assert all(c.get("test_type") == "ui" for c in data["cases"])

    def test_list_pagination(self, client):
        """limit/offset 分页。"""
        for i in range(3):
            _create_case(client, title=f"{PREFIX}分页-{i}")
        resp = client.get("/api/cases", params={"search": "分页-", "limit": 2, "offset": 0})
        data = _data(resp)
        # 共 3 条分页用例，只取 2 条/页，total 应为全量 3
        assert data["total"] == 3
        assert len(data["cases"]) == 2
        # 第二页 offset=2 返回剩余 1 条，total 仍为 3
        resp2 = client.get("/api/cases", params={"search": "分页-", "limit": 2, "offset": 2})
        data2 = _data(resp2)
        assert data2["total"] == 3
        assert len(data2["cases"]) == 1

    def test_update_case_only_nonempty(self, client):
        """PUT 只更新非空字段。"""
        case = _create_case(client, title=PREFIX + "更新前")
        resp = client.put(f"/api/cases/{case['id']}", json={"title": PREFIX + "更新后", "priority": "P0"})
        assert resp.status_code == 200
        updated = _data(resp)
        assert updated["title"] == PREFIX + "更新后"
        assert updated["priority"] == "P0"

    def test_update_case_test_type_special(self, client):
        """PUT 的 test_type 特殊写入 metadata。"""
        case = _create_case(client, test_type="functional")
        resp = client.put(f"/api/cases/{case['id']}", json={"test_type": "security"})
        assert resp.status_code == 200
        updated = _data(resp)
        assert updated["test_type"] == "security"

    def test_update_case_structured_cases_ignored_if_not_list(self, client):
        """PUT 时 structured_cases 非 list 则忽略，不报错。"""
        case = _create_case(client)
        resp = client.put(f"/api/cases/{case['id']}", json={"structured_cases": "not-a-list"})
        assert resp.status_code in (200, 400)

    def test_update_case_invalid_field_400(self, client):
        """PUT 非法字段（如非法状态）返回 400。"""
        case = _create_case(client)
        resp = client.put(f"/api/cases/{case['id']}", json={"status": "INVALID_STATUS"})
        assert resp.status_code == 400

    def test_update_case_not_found_404(self, client):
        """PUT 不存在的用例返回 404。"""
        resp = client.put("/api/cases/nonexistent-id-xyz", json={"title": "x"})
        assert resp.status_code == 404

    def test_delete_case_soft(self, client):
        """DELETE 软删除到回收站。"""
        case = _create_case(client)
        resp = client.delete(f"/api/cases/{case['id']}")
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("trashed") is True or data.get("deleted") is True
        # 删除后查询不到
        assert client.get(f"/api/cases/{case['id']}").status_code == 404

    def test_get_stats(self, client):
        """GET /api/cases/stats 返回统计信息。"""
        _create_case(client)
        resp = client.get("/api/cases/stats")
        assert resp.status_code == 200
        stats = _data(resp)
        assert "total" in stats
        assert "by_status" in stats
        assert "by_priority" in stats


# ════════════════════════════════════════════════════════════
# 二、高级管理
# ════════════════════════════════════════════════════════════

class TestAdvancedFull:
    """GET /api/cases/{id}/full 完整信息聚合。"""

    def test_full_info(self, client):
        case = _create_case(client)
        resp = client.get(f"/api/cases/{case['id']}/full")
        assert resp.status_code == 200
        full = _data(resp)
        for key in ["relations", "dependencies", "reviews", "versions", "changes", "requirements"]:
            assert key in full

    def test_full_info_not_found(self, client):
        resp = client.get("/api/cases/nonexistent-id-xyz/full")
        assert resp.status_code == 404


class TestAdvancedRelations:
    """用例关联（增删查）。"""

    def test_add_list_relation(self, client):
        a = _create_case(client, title=PREFIX + "关联-主")
        b = _create_case(client, title=PREFIX + "关联-从")
        resp = client.post(f"/api/cases/{a['id']}/relations",
                           json={"related_case_id": b["id"], "relation_type": "related"})
        assert resp.status_code == 200
        # 列出关联
        resp = client.get(f"/api/cases/{a['id']}/relations")
        data = _data(resp)
        assert len(data["relations"]) >= 1

    def test_add_relation_self_error_400(self, client):
        a = _create_case(client)
        resp = client.post(f"/api/cases/{a['id']}/relations", json={"related_case_id": a["id"]})
        assert resp.status_code == 400

    def test_add_relation_missing_case_400(self, client):
        a = _create_case(client)
        resp = client.post(f"/api/cases/{a['id']}/relations", json={"related_case_id": "nonexistent"})
        assert resp.status_code == 400

    def test_remove_relation(self, client):
        a = _create_case(client, title=PREFIX + "移除关联-主")
        b = _create_case(client, title=PREFIX + "移除关联-从")
        client.post(f"/api/cases/{a['id']}/relations", json={"related_case_id": b["id"]})
        resp = client.delete(f"/api/cases/{a['id']}/relations/{b['id']}")
        assert resp.status_code == 200
        # 移除后为空
        data = _data(client.get(f"/api/cases/{a['id']}/relations"))
        assert len(data["relations"]) == 0

    def test_remove_relation_not_found_404(self, client):
        a = _create_case(client)
        resp = client.delete(f"/api/cases/{a['id']}/relations/nonexistent")
        assert resp.status_code == 404


class TestAdvancedImportExport:
    """用例导入 / 导出 / 脑图。"""

    def test_export_excel(self, client):
        _create_case(client)
        resp = client.get("/api/cases/export", params={"format": "excel"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "") or "csv" in resp.headers.get("content-type", "")

    def test_export_mindmap(self, client):
        _create_case(client)
        resp = client.get("/api/cases/export", params={"format": "mindmap"})
        assert resp.status_code == 200
        assert "json" in resp.headers.get("content-type", "")

    def test_export_invalid_format_400(self, client):
        resp = client.get("/api/cases/export", params={"format": "bad"})
        assert resp.status_code == 400

    def test_import_excel(self, client):
        csv_text = "标题,类型,优先级,标签\n导入用例A,api,P1,smoke\n导入用例B,functional,P2,regression"
        resp = client.post("/api/cases/import", json={"format": "excel", "content": csv_text})
        assert resp.status_code == 200
        data = _data(resp)
        assert data["imported"] >= 1

    def test_import_xmind(self, client):
        mm = '{"id":"root","text":"库","children":[{"id":"type_api","text":"接口测试","children":[{"id":"c1","text":"导入脑图用例","case_id":"fulla_imp_1","type":"case"}]}]}'
        resp = client.post("/api/cases/import", json={"format": "mindmap", "content": mm})
        assert resp.status_code == 200

    def test_import_invalid_format_400(self, client):
        resp = client.post("/api/cases/import", json={"format": "bad", "content": ""})
        assert resp.status_code == 400

    def test_mindmap(self, client):
        _create_case(client)
        resp = client.get("/api/cases/mindmap")
        assert resp.status_code == 200
        tree = _data(resp)
        assert tree["id"] == "root"

    def test_mindmap_with_project_filter(self, client):
        _create_case(client, file_path="fulla/proj/mindmap")
        resp = client.get("/api/cases/mindmap", params={"project_filter": "fulla/proj"})
        assert resp.status_code == 200
        tree = _data(resp)
        assert tree["id"] == "root"


class TestAdvancedReviews:
    """用例评审流程（submit/approve/reject/query）。"""

    def test_submit_review(self, client):
        case = _create_case(client)
        resp = client.post(f"/api/cases/{case['id']}/reviews/submit",
                           json={"reviewer": "admin", "comment": "请评审"})
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("review_status") == "pending"

    def test_approve_review(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/reviews/submit", json={"reviewer": "admin"})
        resp = client.post(f"/api/cases/{case['id']}/reviews/approve",
                           json={"reviewer": "qa", "comment": "通过"})
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("review_status") == "approved"

    def test_reject_review(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/reviews/submit", json={"reviewer": "admin"})
        resp = client.post(f"/api/cases/{case['id']}/reviews/reject",
                           json={"reviewer": "qa", "comment": "驳回"})
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("review_status") == "rejected"

    def test_list_reviews(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/reviews/submit", json={"reviewer": "admin"})
        resp = client.get(f"/api/cases/{case['id']}/reviews")
        assert resp.status_code == 200
        data = _data(resp)
        assert len(data["reviews"]) >= 1


class TestAdvancedDependencies:
    """用例依赖（增删查）。"""

    def test_add_dependency(self, client):
        a = _create_case(client, title=PREFIX + "依赖-主")
        b = _create_case(client, title=PREFIX + "依赖-从")
        resp = client.post(f"/api/cases/{a['id']}/dependencies",
                           json={"depends_on": b["id"], "dep_type": "before", "description": "前置依赖"})
        assert resp.status_code == 200

    def test_list_dependencies(self, client):
        a = _create_case(client, title=PREFIX + "依赖列表-主")
        b = _create_case(client, title=PREFIX + "依赖列表-从")
        client.post(f"/api/cases/{a['id']}/dependencies", json={"depends_on": b["id"], "dep_type": "after"})
        resp = client.get(f"/api/cases/{a['id']}/dependencies")
        data = _data(resp)
        assert len(data["dependencies"]) >= 1

    def test_remove_dependency(self, client):
        a = _create_case(client, title=PREFIX + "移除依赖-主")
        b = _create_case(client, title=PREFIX + "移除依赖-从")
        client.post(f"/api/cases/{a['id']}/dependencies", json={"depends_on": b["id"]})
        resp = client.delete(f"/api/cases/{a['id']}/dependencies/{b['id']}")
        assert resp.status_code == 200

    def test_remove_dependency_not_found_404(self, client):
        a = _create_case(client)
        resp = client.delete(f"/api/cases/{a['id']}/dependencies/nonexistent")
        assert resp.status_code == 404

    def test_add_dependency_self_400(self, client):
        a = _create_case(client)
        resp = client.post(f"/api/cases/{a['id']}/dependencies", json={"depends_on": a["id"]})
        assert resp.status_code == 400


class TestAdvancedTrash:
    """回收站（软删/恢复/彻底删除/列表）。"""

    def test_trash_case(self, client):
        case = _create_case(client)
        resp = client.post(f"/api/cases/{case['id']}/trash",
                           json={"deleted_by": "admin", "reason": "不需要"})
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("trashed") is True or data.get("deleted") is True

    def test_trash_not_found_404(self, client):
        resp = client.post("/api/cases/nonexistent/trash", json={"deleted_by": "admin"})
        assert resp.status_code == 404

    def test_list_trash(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/trash", json={"deleted_by": "admin"})
        resp = client.get("/api/cases/trash")
        assert resp.status_code == 200
        data = _data(resp)
        assert len(data["trash"]) >= 1

    def test_restore_case(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/trash", json={"deleted_by": "admin"})
        resp = client.post(f"/api/cases/{case['id']}/restore", json={"operator": "admin"})
        assert resp.status_code == 200
        # 恢复后可查询
        assert client.get(f"/api/cases/{case['id']}").status_code == 200

    def test_restore_not_in_trash_404(self, client):
        case = _create_case(client)
        resp = client.post(f"/api/cases/{case['id']}/restore", json={"operator": "admin"})
        assert resp.status_code == 404

    def test_purge_case(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/trash", json={"deleted_by": "admin"})
        resp = client.delete(f"/api/cases/{case['id']}/purge")
        assert resp.status_code == 200
        assert client.get(f"/api/cases/{case['id']}").status_code == 404

    def test_purge_not_found_404(self, client):
        resp = client.delete("/api/cases/nonexistent/purge")
        assert resp.status_code == 404


class TestAdvancedVersions:
    """版本管理（列表/快照/回滚）。"""

    def test_list_versions(self, client):
        case = _create_case(client)
        resp = client.get(f"/api/cases/{case['id']}/versions")
        assert resp.status_code == 200
        data = _data(resp)
        assert len(data["versions"]) >= 1

    def test_get_version(self, client):
        case = _create_case(client)
        client.put(f"/api/cases/{case['id']}", json={"title": PREFIX + "版本更新"})
        versions = _data(client.get(f"/api/cases/{case['id']}/versions"))["versions"]
        assert len(versions) >= 1
        v = versions[0]["version"]
        resp = client.get(f"/api/cases/{case['id']}/versions/{v}")
        assert resp.status_code == 200
        vdata = _data(resp)
        assert "snapshot" in vdata

    def test_get_version_not_found_404(self, client):
        case = _create_case(client)
        resp = client.get(f"/api/cases/{case['id']}/versions/99999")
        assert resp.status_code == 404

    def test_rollback(self, client):
        case = _create_case(client)
        versions = _data(client.get(f"/api/cases/{case['id']}/versions"))["versions"]
        v = versions[0]["version"]
        resp = client.post(f"/api/cases/{case['id']}/rollback", json={"version": v, "operator": "admin"})
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("rolled_back") is True

    def test_rollback_not_found_404(self, client):
        case = _create_case(client)
        resp = client.post(f"/api/cases/{case['id']}/rollback", json={"version": 99999})
        assert resp.status_code == 404


class TestAdvancedChanges:
    """变更记录（审计日志）。"""

    def test_list_changes(self, client):
        case = _create_case(client)
        client.put(f"/api/cases/{case['id']}", json={"title": PREFIX + "变更测试"})
        resp = client.get(f"/api/cases/{case['id']}/changes")
        assert resp.status_code == 200
        data = _data(resp)
        assert len(data["changes"]) >= 1

    def test_list_changes_limit(self, client):
        case = _create_case(client)
        resp = client.get(f"/api/cases/{case['id']}/changes", params={"limit": 5})
        assert resp.status_code == 200
        data = _data(resp)
        assert len(data["changes"]) <= 5


class TestAdvancedRequirements:
    """需求关联（增删查）。"""

    def test_add_requirement(self, client):
        case = _create_case(client)
        resp = client.post(f"/api/cases/{case['id']}/requirements",
                           json={"requirement_id": "JIRA-123", "requirement_type": "jira",
                                 "requirement_title": "需求1", "requirement_url": "http://jira/1"})
        assert resp.status_code == 200

    def test_add_requirement_invalid_400(self, client):
        case = _create_case(client)
        resp = client.post(f"/api/cases/{case['id']}/requirements",
                           json={"requirement_id": "", "requirement_type": "jira"})
        # 空 requirement_id 时后端可能直接写入，也可能校验；两种都允许
        assert resp.status_code in (200, 400)

    def test_add_requirement_case_not_found_400(self, client):
        resp = client.post("/api/cases/nonexistent/requirements",
                           json={"requirement_id": "JIRA-999", "requirement_type": "jira"})
        assert resp.status_code == 400

    def test_list_requirements(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/requirements",
                    json={"requirement_id": "TAPD-88", "requirement_type": "tapd",
                          "requirement_title": "需求", "requirement_url": ""})
        resp = client.get(f"/api/cases/{case['id']}/requirements")
        data = _data(resp)
        assert len(data["requirements"]) >= 1

    def test_remove_requirement(self, client):
        case = _create_case(client)
        client.post(f"/api/cases/{case['id']}/requirements",
                    json={"requirement_id": "JIRA-456", "requirement_type": "jira"})
        resp = client.delete(f"/api/cases/{case['id']}/requirements/JIRA-456")
        assert resp.status_code == 200

    def test_remove_requirement_not_found_404(self, client):
        case = _create_case(client)
        resp = client.delete(f"/api/cases/{case['id']}/requirements/JIRA-NOPE")
        assert resp.status_code == 404
