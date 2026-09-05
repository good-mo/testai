"""
前端界面测试（test_frontend_interface.py）
=========================================
基于 docs/业务逻辑.md 梳理的前端界面与后端接口交互测试。

覆盖范围：
一、前端页面加载
  1.1 首页 HTML 渲染（GET /）
  1.2 系统健康检查 / API 类型 / TestPilot 路由

二、前端 API 页面模块（docs 第十七节）
  2.1 接口定义 CRUD + 导入
  2.2 接口用例 CRUD
  2.3 场景 CRUD + 执行
  2.4 Mock 服务 CRUD
  2.5 回收站操作

三、前端各页面调用的核心 API 集成测试
  3.1 工作台：/api/cases/stats, /api/defects, /api/apitest/meta
  3.2 用例库：/api/cases 增删查
  3.3 缺陷：/api/defects 增删改查
  3.4 接口测试：/api/api-definitions 列表/CRUD
  3.5 报告：/api/reports/list
  3.6 洞察：/api/insights/value
  3.7 任务：/api/tasks
  3.8 项目：/api/projects
  3.9 环境：/api/environments
  3.10 用例高级管理（评审/依赖/版本/变更/需求/回收站）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "FRONT-UI-"


@pytest.fixture(scope="module")
def client():
    """已登录的测试客户端。"""
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


def _ok_data(resp):
    """统一解析 API 响应，提取 data 字段。"""
    data = resp.json()
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


def _create_test_case(client, title=None):
    """辅助：创建测试用例并返回 case_id。"""
    r = client.post("/api/cases", json={
        "title": title or f"{PREFIX}测试用例",
        "test_type": "functional",
        "priority": "P2",
    })
    assert r.status_code == 200
    return _ok_data(r)["id"]


# ═══════════════════════════════════════════════════════════
# 一、前端页面加载
# ═══════════════════════════════════════════════════════════
class TestFrontendPageLoad:
    """前端页面加载测试。"""

    def test_index_page_returns_html(self, client):
        """首页应返回 HTML 页面。"""
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_health_check(self, client):
        """健康检查应返回服务状态。"""
        r = client.get("/health")
        assert r.status_code == 200
        data = _ok_data(r)
        assert data.get("status") == "ok"
        assert data.get("version") == "0.2.0"

    def test_test_types_api(self, client):
        """测试类型 API 应返回支持的测试类型。"""
        r = client.get("/api/test-types")
        assert r.status_code == 200
        data = _ok_data(r)
        # 应包含功能/接口/UI/性能/安全/兼容性/可靠性
        assert "types" in data
        assert len(data["types"]) >= 7

    def test_ms_route_available(self, client):
        """TestPilot 前端路由应可用。"""
        r = client.get("/ms")
        assert r.status_code in (200, 404)  # 未构建时返回 404


# ═══════════════════════════════════════════════════════════
# 二、前端 API 页面模块（docs 第十七节）
# ═══════════════════════════════════════════════════════════
class TestFrontendApiDefinitions:
    """前端 API - 接口定义 CRUD。"""

    def test_create_definition(self, client):
        """创建接口定义。"""
        name = f"{PREFIX}API用户接口"
        r = client.post("/api/api-definitions", json={
            "name": name,
            "method": "GET",
            "path": "/api/users",
            "protocol": "HTTP",
            "description": "获取用户列表",
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == name
        assert data["method"] == "GET"
        assert data["path"] == "/api/users"
        assert "id" in data

    def test_list_definitions(self, client):
        """接口定义列表。"""
        r = client.get("/api/api-definitions")
        assert r.status_code == 200
        data = _ok_data(r)
        assert "definitions" in data

    def test_get_definition_detail(self, client):
        """接口定义详情。"""
        # 先创建
        name = f"{PREFIX}详情接口"
        r = client.post("/api/api-definitions", json={"name": name})
        assert r.status_code == 200
        def_id = _ok_data(r)["id"]

        r = client.get(f"/api/api-definitions/{def_id}")
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["id"] == def_id
        assert data["name"] == name

    def test_update_definition(self, client):
        """更新接口定义。"""
        r = client.post("/api/api-definitions", json={"name": f"{PREFIX}更新前"})
        def_id = _ok_data(r)["id"]

        r = client.put(f"/api/api-definitions/{def_id}", json={
            "name": f"{PREFIX}更新后",
            "description": "更新描述",
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == f"{PREFIX}更新后"

    def test_delete_definition(self, client):
        """删除接口定义。"""
        r = client.post("/api/api-definitions", json={"name": f"{PREFIX}删除用"})
        def_id = _ok_data(r)["id"]

        r = client.delete(f"/api/api-definitions/{def_id}")
        assert r.status_code == 200

    def test_definition_not_found(self, client):
        """接口定义不存在返回 404。"""
        r = client.get("/api/api-definitions/nonexistent-id")
        assert r.status_code == 404

    def test_import_definition(self, client):
        """导入接口定义（Postman 格式）。"""
        r = client.post("/api/api-definitions/import", json={
            "format": "postman",
            "data": {
                "name": f"{PREFIX}导入接口",
                "request": {
                    "method": "GET",
                    "url": {"raw": "https://api.example.com/v1/users"}
                }
            }
        })
        assert r.status_code == 200


class TestFrontendApiTestCases:
    """前端 API - 接口用例 CRUD。"""

    def test_create_test_case(self, client):
        """创建接口用例。"""
        name = f"{PREFIX}API查询用户"
        r = client.post("/api/api-test-cases", json={
            "name": name,
            "method": "GET",
            "path": "/api/users",
            "assertions": [{"type": "status", "expected": "200"}],
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == name
        assert data["method"] == "GET"
        assert "id" in data

    def test_list_test_cases(self, client):
        """接口用例列表。"""
        r = client.get("/api/api-test-cases")
        assert r.status_code == 200
        data = _ok_data(r)
        assert "cases" in data

    def test_get_test_case_detail(self, client):
        """接口用例详情。"""
        r = client.post("/api/api-test-cases", json={"name": f"{PREFIX}详情用例"})
        case_id = _ok_data(r)["id"]

        r = client.get(f"/api/api-test-cases/{case_id}")
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["id"] == case_id

    def test_update_test_case(self, client):
        """更新接口用例。"""
        r = client.post("/api/api-test-cases", json={"name": f"{PREFIX}更新前用例"})
        case_id = _ok_data(r)["id"]

        r = client.put(f"/api/api-test-cases/{case_id}", json={
            "name": f"{PREFIX}更新后用例",
            "timeout": 60,
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == f"{PREFIX}更新后用例"

    def test_delete_test_case(self, client):
        """删除接口用例。"""
        r = client.post("/api/api-test-cases", json={"name": f"{PREFIX}删除用例"})
        case_id = _ok_data(r)["id"]

        r = client.delete(f"/api/api-test-cases/{case_id}")
        assert r.status_code == 200

    def test_test_case_not_found(self, client):
        """接口用例不存在返回 404。"""
        r = client.get("/api/api-test-cases/nonexistent-id")
        assert r.status_code == 404


class TestFrontendScenarios:
    """前端 API - 场景 CRUD 与执行。"""

    def test_create_scenario(self, client):
        """创建场景。"""
        name = f"{PREFIX}登录场景"
        r = client.post("/api/scenarios", json={
            "name": name,
            "description": "用户登录完整流程",
            "steps": [{"name": "step1", "method": "POST", "path": "/api/login"}],
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == name
        assert "id" in data

    def test_list_scenarios(self, client):
        """场景列表。"""
        r = client.get("/api/scenarios")
        assert r.status_code == 200
        data = _ok_data(r)
        assert "scenarios" in data

    def test_get_scenario_detail(self, client):
        """场景详情。"""
        r = client.post("/api/scenarios", json={"name": f"{PREFIX}详情场景"})
        scn_id = _ok_data(r)["id"]

        r = client.get(f"/api/scenarios/{scn_id}")
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["id"] == scn_id

    def test_update_scenario(self, client):
        """更新场景。"""
        r = client.post("/api/scenarios", json={"name": f"{PREFIX}更新前场景"})
        scn_id = _ok_data(r)["id"]

        r = client.put(f"/api/scenarios/{scn_id}", json={"name": f"{PREFIX}更新后场景"})
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == f"{PREFIX}更新后场景"

    def test_delete_scenario(self, client):
        """删除场景。"""
        r = client.post("/api/scenarios", json={"name": f"{PREFIX}删除场景"})
        scn_id = _ok_data(r)["id"]

        r = client.delete(f"/api/scenarios/{scn_id}")
        assert r.status_code == 200

    def test_scenario_not_found(self, client):
        """场景不存在返回 404。"""
        r = client.get("/api/scenarios/nonexistent-id")
        assert r.status_code == 404

    def test_execute_scenario(self, client):
        """执行场景。"""
        r = client.post("/api/scenarios", json={"name": f"{PREFIX}执行场景"})
        scn_id = _ok_data(r)["id"]

        r = client.post(f"/api/scenarios/{scn_id}/execute", json={})
        assert r.status_code == 200


class TestFrontendMockServices:
    """前端 API - Mock 服务 CRUD。"""

    def test_create_mock(self, client):
        """创建 Mock 服务。"""
        name = f"{PREFIX}Mock接口"
        r = client.post("/api/mock-services", json={
            "name": name,
            "method": "GET",
            "path": "/api/mock/users",
            "response_code": 200,
            "response_body": '{"data": []}',
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == name
        assert "id" in data

    def test_list_mocks(self, client):
        """Mock 服务列表。"""
        r = client.get("/api/mock-services")
        assert r.status_code == 200
        data = _ok_data(r)
        assert "mocks" in data

    def test_get_mock_detail(self, client):
        """Mock 服务详情。"""
        r = client.post("/api/mock-services", json={"name": f"{PREFIX}详情Mock"})
        mock_id = _ok_data(r)["id"]

        r = client.get(f"/api/mock-services/{mock_id}")
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["id"] == mock_id

    def test_update_mock(self, client):
        """更新 Mock 服务。"""
        r = client.post("/api/mock-services", json={"name": f"{PREFIX}更新前Mock"})
        mock_id = _ok_data(r)["id"]

        r = client.put(f"/api/mock-services/{mock_id}", json={
            "name": f"{PREFIX}更新后Mock",
            "response_code": 201,
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == f"{PREFIX}更新后Mock"

    def test_delete_mock(self, client):
        """删除 Mock 服务。"""
        r = client.post("/api/mock-services", json={"name": f"{PREFIX}删除Mock"})
        mock_id = _ok_data(r)["id"]

        r = client.delete(f"/api/mock-services/{mock_id}")
        assert r.status_code == 200

    def test_mock_not_found(self, client):
        """Mock 服务不存在返回 404。"""
        r = client.get("/api/mock-services/nonexistent-id")
        assert r.status_code == 404


class TestFrontendRecycleBin:
    """前端 API - 回收站操作。"""

    def test_definition_trash_page(self, client):
        """接口定义回收站分页。"""
        r = client.get("/api/definition/trash/page", params={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _ok_data(r)
        assert "list" in data
        assert "total" in data

    def test_scenario_trash_page(self, client):
        """场景回收站分页。"""
        r = client.post("/api/scenario/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _ok_data(r)
        assert "list" in data
        assert "total" in data

    def test_case_recover(self, client):
        """恢复接口用例。"""
        r = client.post("/api/case/recover", json={"id": "nonexistent"})
        assert r.status_code == 200

    def test_scenario_batch_delete(self, client):
        """批量删除场景。"""
        r = client.post("/api/scenario/batch-operation/delete", json={"ids": []})
        assert r.status_code == 200

    def test_scenario_batch_recover_gc(self, client):
        """批量恢复/回收场景。"""
        r = client.post("/api/scenario/batch-operation/recover-gc", json={"ids": []})
        assert r.status_code == 200

    def test_definition_batch_delete(self, client):
        """批量删除接口定义。"""
        r = client.post("/api/definition/batch-delete", json={"ids": []})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 三、前端各页面调用的核心 API 集成测试
# ═══════════════════════════════════════════════════════════
class TestFrontendDashboardAPI:
    """前端工作台 Dashboard 页面调用的 API。"""

    def test_cases_stats_endpoint(self, client):
        """工作台-用例统计。"""
        r = client.get("/api/cases/stats")
        assert r.status_code == 200

    def test_apitest_meta_endpoint(self, client):
        """接口测试元数据。"""
        r = client.get("/api/apitest/meta")
        assert r.status_code == 200

    def test_insights_value_endpoint(self, client):
        """工作台-洞察价值量化。"""
        r = client.get("/api/insights/value")
        assert r.status_code == 200


class TestFrontendCaseLibraryAPI:
    """前端用例库页面调用的 API。"""

    def test_case_create_and_list(self, client):
        """用例创建与列表。"""
        case_id = _create_test_case(client, f"{PREFIX}用例列表测试")

        r = client.get("/api/cases", params={"search": PREFIX, "limit": 50})
        assert r.status_code == 200
        data = _ok_data(r)
        cases = data.get("cases", [])
        assert any(c["id"] == case_id for c in cases)

        client.delete(f"/api/cases/{case_id}")

    def test_case_stats_display(self, client):
        """用例库统计显示。"""
        r = client.get("/api/cases/stats")
        assert r.status_code == 200

    def test_case_mindmap(self, client):
        """用例脑图。"""
        r = client.get("/api/cases/mindmap")
        assert r.status_code == 200

    def test_case_import_invalid_format(self, client):
        """用例导入（无效格式返回 400）。"""
        r = client.post("/api/cases/import", json={
            "format": "invalid_format",
            "content": "{}",
        })
        assert r.status_code == 400

    def test_case_trash_list(self, client):
        """用例回收站列表。"""
        r = client.get("/api/cases/trash")
        assert r.status_code == 200


class TestFrontendDefectAPI:
    """前端缺陷跟踪页面调用的 API。"""

    def test_create_and_update_defect(self, client):
        """创建缺陷并更新状态。"""
        title = f"{PREFIX}前端发现缺陷"
        r = client.post("/api/defects", json={
            "title": title,
            "severity": "major",
            "description": "通过前端界面发现的缺陷",
        })
        assert r.status_code == 200
        def_id = _ok_data(r)["id"]

        # 更新状态
        r = client.put(f"/api/defects/{def_id}", json={"status": "in_progress"})
        assert r.status_code == 200
        data = _ok_data(r)
        assert data.get("status") == "in_progress"

        # 删除
        r = client.delete(f"/api/defects/{def_id}")
        assert r.status_code == 200

    def test_defect_list(self, client):
        """缺陷列表。"""
        r = client.get("/api/defects", params={"limit": 50})
        assert r.status_code == 200
        data = _ok_data(r)
        assert "defects" in data


class TestFrontendReportAPI:
    """前端报告中心页面调用的 API。"""

    def test_reports_list(self, client):
        """报告列表。"""
        r = client.get("/api/reports/list")
        assert r.status_code == 200

    def test_report_generate(self, client):
        """生成报告（可能因无用例返回 404）。"""
        r = client.post("/api/reports/generate", json={"format": "markdown"})
        assert r.status_code in (200, 404)

    def test_report_download_not_found(self, client):
        """下载不存在的报告返回 404。"""
        r = client.get("/api/reports/download/nonexistent.html")
        assert r.status_code == 404


class TestFrontendInsightsAPI:
    """前端测试洞察页面调用的 API。"""

    def test_insights_value(self, client):
        """价值量化。"""
        r = client.get("/api/insights/value")
        assert r.status_code == 200

    def test_insights_risk(self, client):
        """高风险模块预警。"""
        r = client.get("/api/insights/risk")
        assert r.status_code == 200

    def test_insights_skill_path(self, client):
        """职业发展路径。"""
        r = client.get("/api/insights/skill-path")
        assert r.status_code == 200

    def test_insights_lowcode_empty(self, client):
        """低代码生成（空描述返回 400）。"""
        r = client.post("/api/insights/lowcode", json={"description": ""})
        assert r.status_code == 400


class TestFrontendTaskAPI:
    """前端任务队列页面调用的 API。"""

    def test_tasks_list(self, client):
        """任务列表。"""
        r = client.get("/api/tasks")
        assert r.status_code == 200

    def test_task_detail_not_found(self, client):
        """不存在的任务返回 404。"""
        r = client.get("/api/tasks/nonexistent-task")
        assert r.status_code == 404


class TestFrontendProjectAPI:
    """前端项目管理页面调用的 API。"""

    def test_projects_list(self, client):
        """项目列表。"""
        r = client.get("/api/projects")
        assert r.status_code == 200

    def test_create_project(self, client):
        """创建项目。"""
        name = f"{PREFIX}测试项目"
        r = client.post("/api/projects", json={
            "name": name,
            "description": "前端界面测试项目",
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == name
        proj_id = data["id"]

        # 获取详情
        r = client.get(f"/api/projects/{proj_id}")
        assert r.status_code == 200

        # 删除
        r = client.delete(f"/api/projects/{proj_id}")
        assert r.status_code == 200


class TestFrontendEnvironmentAPI:
    """前端接口测试-环境管理页面调用的 API。"""

    def _create_env(self, client):
        """辅助：创建环境并返回 env_id。"""
        name = f"{PREFIX}测试环境"
        r = client.post("/api/environments", json={"name": name})
        assert r.status_code == 200
        data = _ok_data(r)
        assert data["name"] == name
        return data.get("id", data.get("env_id"))

    def test_create_environment(self, client):
        """创建环境。"""
        env_id = self._create_env(client)
        assert env_id

    def test_list_environments(self, client):
        """环境列表。"""
        r = client.get("/api/environments")
        assert r.status_code == 200

    def test_update_environment(self, client):
        """更新环境。"""
        env_id = self._create_env(client)
        r = client.put(f"/api/environments/{env_id}", json={"name": f"{PREFIX}更新环境"})
        assert r.status_code == 200

    def test_delete_environment(self, client):
        """删除环境。"""
        env_id = self._create_env(client)
        r = client.delete(f"/api/environments/{env_id}")
        assert r.status_code == 200


class TestFrontendDebugAPI:
    """前端接口调试页面调用的 API。"""

    def test_debug_api_call(self, client):
        """接口调试请求（网络可能失败，但接口应可用）。"""
        r = client.post("/api/debug", json={
            "method": "GET",
            "url": "https://httpbin.org/get",
            "timeout": 5,
        })
        # 接口本身应可用，网络请求结果不确定
        assert r.status_code in (200, 400, 500, 502, 504)


class TestFrontendCaseAdvancedAPI:
    """前端用例高级管理页面调用的 API。"""

    def test_review_submit(self, client):
        """提交评审。"""
        case_id = _create_test_case(client, f"{PREFIX}评审用例")
        r = client.post(f"/api/cases/{case_id}/reviews/submit", json={
            "reviewer": "tester",
            "comment": "提交评审",
        })
        assert r.status_code == 200
        client.delete(f"/api/cases/{case_id}")

    def test_dependencies_flow(self, client):
        """依赖关系管理。"""
        case_id = _create_test_case(client, f"{PREFIX}依赖主用例")
        dep_id = _create_test_case(client, f"{PREFIX}依赖从用例")

        # 添加依赖
        r = client.post(f"/api/cases/{case_id}/dependencies", json={
            "depends_on": dep_id,
            "dep_type": "before",
        })
        assert r.status_code == 200
        data = _ok_data(r)
        assert data.get("duplicated") is not None or "id" in data

        # 列出依赖
        r = client.get(f"/api/cases/{case_id}/dependencies")
        assert r.status_code == 200
        data = _ok_data(r)
        deps = data.get("dependencies", [])
        assert len(deps) > 0

        # 移除依赖
        r = client.delete(f"/api/cases/{case_id}/dependencies/{dep_id}")
        assert r.status_code == 200

        # 清理
        client.delete(f"/api/cases/{case_id}")
        client.delete(f"/api/cases/{dep_id}")

    def test_versions_flow(self, client):
        """版本管理。"""
        case_id = _create_test_case(client, f"{PREFIX}版本用例")

        r = client.get(f"/api/cases/{case_id}/versions")
        assert r.status_code == 200

        client.delete(f"/api/cases/{case_id}")

    def test_changes_history(self, client):
        """变更记录。"""
        case_id = _create_test_case(client, f"{PREFIX}变更用例")

        r = client.get(f"/api/cases/{case_id}/changes")
        assert r.status_code == 200
        data = _ok_data(r)
        assert "changes" in data
        assert "total" in data

        client.delete(f"/api/cases/{case_id}")

    def test_requirements_flow(self, client):
        """需求关联。"""
        case_id = _create_test_case(client, f"{PREFIX}需求用例")

        # 关联需求
        r = client.post(f"/api/cases/{case_id}/requirements", json={
            "requirement_id": "REQ-001",
            "requirement_type": "jira",
            "requirement_title": "测试需求",
        })
        assert r.status_code == 200

        # 列出需求
        r = client.get(f"/api/cases/{case_id}/requirements")
        assert r.status_code == 200
        data = _ok_data(r)
        reqs = data.get("requirements", [])
        assert len(reqs) > 0

        # 移除需求
        r = client.delete(f"/api/cases/{case_id}/requirements/REQ-001")
        assert r.status_code == 200

        # 清理
        client.delete(f"/api/cases/{case_id}")

    def test_restore_and_purge(self, client):
        """回收站恢复与彻底删除。"""
        case_id = _create_test_case(client, f"{PREFIX}回收用例")

        # 软删除到回收站
        r = client.post(f"/api/cases/{case_id}/trash", json={
            "deleted_by": "tester",
            "reason": "测试删除",
        })
        assert r.status_code == 200

        # 从回收站恢复
        r = client.post(f"/api/cases/{case_id}/restore", json={"operator": "tester"})
        assert r.status_code == 200

        # 再次删除并彻底删除
        client.post(f"/api/cases/{case_id}/trash", json={"deleted_by": "tester"})
        r = client.delete(f"/api/cases/{case_id}/purge")
        assert r.status_code == 200
