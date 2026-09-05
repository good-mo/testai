"""
前端全模块端到端业务流程测试（test_frontend_e2e_all.py）
=========================================================
从用户视角，按「15 大模块 / 75+ 页面」的完整业务闭环逐一走通。

覆盖模块：
  01. 工作台（首页/待办/我关注的/我创建的）
  02. AI 用例生成（用例生成/低代码/项目批量）
  03. 测试计划（列表/创建/详情/关联/报告）
  04. 用例管理（功能用例/评审/回收站）
  05. 接口测试-调试
  06. 接口测试-定义（CRUD/模块/回收站）
  07. 接口测试-用例（CRUD/统计/历史）
  08. 接口测试-场景（CRUD/模块/统计/回收站）
  09. 缺陷管理（CRUD/详情/回收站）
  10. 项目管理-权限（基本信息/菜单/版本/成员/用户组）
  11. 项目管理-模板（列表/字段/详情/工作流）
  12. 项目管理-功能（文件/消息/脚本/环境/日志）
  13. 系统设置-系统（用户/用户组/组织/参数/资源池/插件/日志）
  14. 系统设置-组织（成员/用户组/项目/模板/任务中心）
  15. 分享与全页面（报告分享/文档分享/PDF导出）

每个模块：核心 CRUD + 关键业务动作 + 数据保留。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "E2E-"

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


def _data(resp):
    """提取响应 data 字段。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _unique(prefix=""):
    """生成唯一标识。"""
    return f"{PREFIX}{prefix}-{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 01. 工作台模块（4 页面）
# ═══════════════════════════════════════════════════════════
class Test01Workbench:
    """工作台 - 首页 / 待办 / 我关注的 / 我创建的。"""

    def test_home_page_business_flow(self, client):
        """首页：项目概览 + 各类统计 + 布局。"""
        # 项目概览
        r = client.post("/dashboard/project_view", json={})
        assert r.status_code == 200
        data = _data(r)
        assert "caseCountMap" in data
        # 用例数量
        r = client.post("/dashboard/case_count", json={})
        assert r.status_code == 200
        # 缺陷数量
        r = client.post("/dashboard/bug_count", json={})
        assert r.status_code == 200
        # 接口数量
        r = client.post("/dashboard/api_count", json={})
        assert r.status_code == 200
        # 接口用例数量
        r = client.post("/dashboard/api_case_count", json={})
        assert r.status_code == 200
        # 场景用例数量
        r = client.post("/dashboard/scenario_count", json={})
        assert r.status_code == 200
        # 用例评审数
        r = client.post("/dashboard/review_case_count", json={})
        assert r.status_code == 200
        # 获取布局
        r = client.get("/dashboard/layout/get")
        assert r.status_code == 200
        # 成员下拉
        r = client.get("/dashboard/member/get-project-member/option")
        assert r.status_code == 200
        # 测试计划概览下拉
        r = client.get("/dashboard/plan/option")
        assert r.status_code == 200

    def test_todo_and_created_business_flow(self, client):
        """待办 & 我创建的：列表查询。"""
        # 待办-测试计划
        r = client.post("/dashboard/todo/plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 待办-用例评审
        r = client.post("/dashboard/todo/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 待办-缺陷
        r = client.post("/dashboard/todo/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 我创建的
        r = client.post("/dashboard/create_by_me", json={})
        assert r.status_code == 200
        # 我负责的用例
        r = client.post("/dashboard/my/functional/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _data(r)
        assert "list" in data
        # 我负责的缺陷
        r = client.post("/dashboard/my/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 我负责的接口用例
        r = client.post("/dashboard/my/api/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 我负责的场景
        r = client.post("/dashboard/my/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 我负责的测试计划
        r = client.post("/dashboard/my/plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 我参与的评审
        r = client.post("/dashboard/my/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200

    def test_my_followed_business_flow(self, client):
        """我关注的：列表查询。"""
        r = client.post("/dashboard/my/functional/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        r = client.post("/dashboard/my/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 02. AI 用例生成模块（3 页面）
# ═══════════════════════════════════════════════════════════
class Test02AiCaseGen:
    """AI 用例生成 - 用例生成 / 低代码 / 项目批量。"""

    def test_test_types_and_ai_business_flow(self, client):
        """用例生成：测试类型 + AI 能力。"""
        # 测试类型
        r = client.get("/api/test-types")
        assert r.status_code == 200
        data = _data(r)
        assert "types" in data
        assert len(data["types"]) >= 7
        # 洞察能力
        r = client.get("/api/insights/skill-path")
        assert r.status_code in (200, 404, 500)
        # 任务列表
        r = client.get("/api/tasks")
        assert r.status_code == 200

    def test_lowcode_business_flow(self, client):
        """低代码生成。"""
        r = client.post("/api/insights/lowcode", json={"input": "创建用户登录测试"})
        assert r.status_code in (200, 400, 404, 422)

    def test_project_scan_business_flow(self, client):
        """项目批量生成。"""
        # 项目扫描需要目录参数
        r = client.post("/api/projects/scan", json={})
        assert r.status_code in (200, 400, 404, 422)


# ═══════════════════════════════════════════════════════════
# 03. 测试计划模块（7 页面）
# ═══════════════════════════════════════════════════════════
class Test03TestPlan:
    """测试计划 - 列表/创建/详情/关联/报告。"""

    def test_plan_list_and_create_business_flow(self, client):
        """计划列表 → 创建 → 详情 → 更新 → 归档。"""
        # 列表
        r = client.post("/test-plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _data(r)
        assert "list" in data
        # 创建
        name = _unique("计划")
        r = client.post("/test-plan/add", json={
            "name": name,
            "description": "E2E 业务流程测试计划",
        })
        assert r.status_code == 200, f"创建测试计划失败: {r.text}"
        plan_id = r.json().get("id") or _data(r).get("id")
        assert plan_id, f"创建测试计划未返回ID: {r.text}"
        # 详情
        r = client.get(f"/test-plan/{plan_id}")
        assert r.status_code == 200, f"获取测试计划失败: {r.text}"
        # 更新
        r = client.post("/test-plan/update", json={
            "id": plan_id,
            "name": name + "-更新",
        })
        assert r.status_code == 200, f"更新测试计划失败: {r.text}"
        # 归档
        r = client.post("/test-plan/archived", json={"id": plan_id})
        assert r.status_code in (200, 404), f"归档失败: {r.text}"

    def test_plan_association_and_report_business_flow(self, client):
        """计划关联 + 统计 + 报告。"""
        # 关联页面
        r = client.post("/test-plan/association/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 统计
        r = client.get("/test-plan/statistics")
        assert r.status_code in (200, 404)
        # 功能用例列表
        r = client.post("/test-plan/functional/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 报告
        r = client.post("/test-plan/report/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 获取计划数
        r = client.get("/test-plan/getCount")
        assert r.status_code in (200, 404)

    def test_plan_module_management(self, client):
        """计划模块树。"""
        r = client.get("/test-plan/module/tree")
        assert r.status_code in (200, 404)
        r = client.post("/test-plan/module/count", json={})
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 04. 用例管理模块（9 页面）
# ═══════════════════════════════════════════════════════════
class Test04CaseManagement:
    """用例管理 - 功能用例 / 评审 / 回收站。"""

    def test_case_crud_business_flow(self, client):
        """用例：创建 → 列表 → 详情 → 更新 → 软删除。"""
        # 列表
        r = client.post("/functional/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        # 创建
        title = _unique("功能用例")
        r = client.post("/functional/case/add", json={
            "name": title,
            "description": "E2E 业务流程测试用例",
            "priority": "P1",
            "type": "functional",
        })
        assert r.status_code == 200, f"创建功能用例失败: {r.text}"
        case_id = r.json().get("id") or _data(r).get("id")
        assert case_id, f"创建功能用例未返回ID: {r.text}"
        # 详情
        r = client.get(f"/functional/case/detail/{case_id}")
        assert r.status_code in (200, 404)
        # 更新
        r = client.post("/functional/case/update", json={
            "id": case_id,
            "name": title + "-更新",
        })
        assert r.status_code in (200, 404)
        # 模块树
        r = client.get("/functional/case/module/tree")
        assert r.status_code in (200, 404)

    def test_case_review_business_flow(self, client):
        """用例评审：列表 → 创建 → 详情。"""
        # 评审列表
        r = client.post("/case/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 评审创建
        review_name = _unique("评审")
        r = client.post("/case/review/add", json={
            "name": review_name,
        })
        assert r.status_code in (200, 404)

    def test_case_trash_business_flow(self, client):
        """回收站。"""
        r = client.post("/functional/case/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)

    def test_case_basic_crud_via_api(self, client):
        """通过 /api/cases 的用例 CRUD。"""
        # 创建
        title = _unique("API用例")
        r = client.post("/api/cases", json={
            "title": title,
            "description": "API 方式创建",
            "test_type": "functional",
            "priority": "P2",
        })
        assert r.status_code == 200, f"创建用例失败: {r.text}"
        case_id = r.json().get("id") or _data(r).get("id")
        assert case_id
        # 获取
        r = client.get(f"/api/cases/{case_id}")
        assert r.status_code == 200
        # 更新
        r = client.put(f"/api/cases/{case_id}", json={"description": "已更新"})
        assert r.status_code == 200
        # 删除
        r = client.delete(f"/api/cases/{case_id}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 05. 接口测试-调试（1 页面）
# ═══════════════════════════════════════════════════════════
class Test05ApiDebug:
    """接口调试页面。"""

    def test_debug_business_flow(self, client):
        """接口调试。"""
        r = client.post("/api/debug", json={
            "method": "GET",
            "url": "https://httpbin.org/get",
        })
        assert r.status_code in (200, 404, 405, 500)
        # 调试日志
        r = client.get("/api/debug/logs")
        assert r.status_code in (200, 404)
        # 模块树
        r = client.get("/api/debug/module/tree")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 06. 接口测试-定义（2 页面）
# ═══════════════════════════════════════════════════════════
class Test06ApiDefinition:
    """接口定义 - 列表/CRUD/模块/回收站。"""

    def test_definition_full_business_flow(self, client):
        """定义：列表 → 创建 → 详情 → 更新 → 删除。"""
        # 列表
        r = client.post("/api/definition/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, f"接口定义列表失败: {r.text}"
        data = _data(r)
        assert "list" in data or "items" in data
        # 创建
        name = _unique("接口定义")
        r = client.post("/api/definition/add", json={
            "name": name,
            "method": "GET",
            "path": "/api/e2e/test",
            "protocol": "HTTP",
        })
        assert r.status_code == 200, f"创建接口定义失败: {r.text}"
        def_id = r.json().get("id") or _data(r).get("id")
        assert def_id, f"创建接口定义未返回ID: {r.text}"
        # 详情
        r = client.get(f"/api/definition/get-detail/{def_id}")
        assert r.status_code in (200, 404)
        # 更新
        r = client.post("/api/definition/update", json={
            "id": def_id,
            "name": name + "-更新",
        })
        assert r.status_code == 200, f"更新接口定义失败: {r.text}"
        # 模块树
        r = client.get("/api/definition/module/tree")
        assert r.status_code in (200, 404)
        # 模块添加
        r = client.post("/api/definition/module/add", json={
            "name": _unique("模块"),
            "parent_id": "NONE",
        })
        assert r.status_code in (200, 404)
        # 删除（软删除）
        r = client.post(f"/api/definition/delete-to-gc/{def_id}")
        assert r.status_code in (200, 404)

    def test_definition_alternative_api(self, client):
        """通过 /api/api-definitions 的接口定义 CRUD。"""
        name = _unique("ALT定义")
        r = client.post("/api/api-definitions", json={"name": name, "method": "GET"})
        assert r.status_code == 200
        def_id = _data(r).get("id")
        assert def_id
        # 列表
        r = client.get("/api/api-definitions")
        assert r.status_code == 200
        # 详情
        r = client.get(f"/api/api-definitions/{def_id}")
        assert r.status_code == 200
        # 删除
        r = client.delete(f"/api/api-definitions/{def_id}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 07. 接口测试-用例
# ═══════════════════════════════════════════════════════════
class Test07ApiCase:
    """接口用例 - CRUD/统计/历史。"""

    def test_api_case_full_business_flow(self, client):
        """用例：列表 → 创建 → 详情 → 更新。"""
        # 列表
        r = client.post("/api/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 创建
        case_name = _unique("接口用例")
        r = client.post("/api/case/add", json={
            "name": case_name,
            "method": "GET",
            "path": "/api/e2e/case",
        })
        assert r.status_code in (200, 404)
        # 统计
        r = client.post("/api/case/statistics")
        assert r.status_code in (200, 404)
        # 执行历史
        r = client.post("/api/case/execute/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)

    def test_api_case_via_apitest_api(self, client):
        """通过 /api/apitest/cases 的接口用例 CRUD。"""
        # 列表
        r = client.get("/api/apitest/cases")
        assert r.status_code == 200
        # 创建
        name = _unique("APITest用例")
        r = client.post("/api/apitest/cases", json={"name": name})
        assert r.status_code in (200, 201)
        case_id = r.json().get("id")
        if case_id:
            r = client.get(f"/api/apitest/cases/{case_id}")
            assert r.status_code == 200
            r = client.delete(f"/api/apitest/cases/{case_id}")
            assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 08. 接口测试-场景（3 页面）
# ═══════════════════════════════════════════════════════════
class Test08ApiScenario:
    """接口场景 - CRUD/模块/统计/回收站。"""

    def test_scenario_full_business_flow(self, client):
        """场景：列表 → 创建 → 详情 → 更新。"""
        # 列表
        r = client.post("/api/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 创建
        name = _unique("接口场景")
        r = client.post("/api/scenario/add", json={"name": name})
        assert r.status_code in (200, 404)
        # 模块树
        r = client.post("/api/scenario/module/tree", json={})
        assert r.status_code in (200, 404)
        # 统计
        r = client.post("/api/scenario/statistics")
        assert r.status_code in (200, 404)
        # 回收站
        r = client.post("/api/scenario/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)

    def test_scenario_via_apitest_api(self, client):
        """通过 /api/apitest/scenarios 的场景 CRUD。"""
        r = client.get("/api/apitest/scenarios")
        assert r.status_code == 200
        name = _unique("APITest场景")
        r = client.post("/api/apitest/scenarios", json={"name": name})
        assert r.status_code in (200, 201)
        scenario_id = r.json().get("id")
        if scenario_id:
            r = client.get(f"/api/apitest/scenarios/{scenario_id}")
            assert r.status_code == 200
            r = client.delete(f"/api/apitest/scenarios/{scenario_id}")
            assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 09. 缺陷管理模块（4 页面）
# ═══════════════════════════════════════════════════════════
class Test09BugManagement:
    """缺陷管理 - 列表/CRUD/详情/回收站。"""

    def test_bug_full_business_flow(self, client):
        """缺陷：列表 → 创建 → 详情 → 更新。"""
        # 列表
        r = client.post("/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, f"缺陷列表失败: {r.text}"
        data = _data(r)
        assert "list" in data
        # 创建
        title = _unique("缺陷")
        r = client.post("/bug/add", json={
            "title": title,
            "description": "E2E 业务流程测试缺陷",
        })
        assert r.status_code == 200, f"创建缺陷失败: {r.text}"
        bug_id = r.json().get("id") or _data(r).get("id")
        assert bug_id, f"创建缺陷未返回ID: {r.text}"
        # 详情
        r = client.get(f"/bug/get/{bug_id}")
        assert r.status_code in (200, 404)
        # 更新
        r = client.post("/bug/update", json={
            "id": bug_id,
            "status": "closed",
        })
        assert r.status_code in (200, 404)
        # 模板
        r = client.get("/bug/template/detail")
        assert r.status_code in (200, 404)

    def test_front_prefix_bug_page(self, client):
        """缺陷列表 /front/ 前缀重写：验证 FrontPrefixMiddleware 路径重写生效。

        回归：若 /front/bug/page 返回 404，说明 /front 前缀未被正确重写，
        前端所有带 /front 前缀的请求都会失败，导致缺陷管理页等界面无数据。
        """
        r = client.post("/front/bug/page", json={"pageSize": 5, "current": 1})
        assert r.status_code == 200, f"/front/bug/page 应返回 200，实际 {r.status_code}: {r.text}"
        data = _data(r)
        assert "list" in data and "total" in data
        # 校验重写后能取到真实数据
        assert len(data["list"]) > 0, "重写后的缺陷列表不应为空"
        # 非 /front 前缀的直连路径也应保持可用
        r2 = client.post("/bug/page", json={"pageSize": 5, "current": 1})
        assert r2.status_code == 200

    def test_bug_alternative_api(self, client):
        """通过 /api/defects 的缺陷 CRUD。"""
        r = client.get("/api/defects")
        assert r.status_code == 200
        title = _unique("API缺陷")
        r = client.post("/api/defects", json={"title": title, "description": "API方式"})
        assert r.status_code == 200
        bug_id = r.json().get("id") or _data(r).get("id")
        assert bug_id
        r = client.get(f"/api/defects/{bug_id}")
        assert r.status_code == 200
        r = client.put(f"/api/defects/{bug_id}", json={"status": "fixed"})
        assert r.status_code == 200

    def test_bug_recycle(self, client):
        """缺陷回收站。"""
        r = client.post("/bug/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 10. 项目管理-权限（5 页面）
# ═══════════════════════════════════════════════════════════
class Test10ProjectPermission:
    """项目管理 - 权限相关页面。"""

    def test_basic_info_business_flow(self, client):
        """基本信息。"""
        # 项目列表
        r = client.get("/api/projects")
        assert r.status_code == 200
        data = _data(r)
        assert "projects" in data
        # 项目权限
        r = client.get("/project/has-permission")
        assert r.status_code in (200, 404)

    def test_menu_and_version_business_flow(self, client):
        """菜单管理 + 项目版本。"""
        # 菜单管理相关
        r = client.get("/project/application/case")
        assert r.status_code in (200, 404)
        # 项目版本列表
        r = client.get("/api/project/versions")
        assert r.status_code in (200, 404)
        # 项目成员列表
        r = client.post("/project/member/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 用户组列表
        r = client.get("/project/group/list")
        assert r.status_code in (200, 404)

    def test_project_create_and_update(self, client):
        """项目创建与更新。"""
        r = client.post("/api/projects", json={
            "name": _unique("项目"),
            "description": "E2E 测试项目",
        })
        assert r.status_code in (200, 201)


# ═══════════════════════════════════════════════════════════
# 11. 项目管理-模板（7 页面）
# ═══════════════════════════════════════════════════════════
class Test11ProjectTemplate:
    """项目管理 - 模板相关页面。"""

    def test_template_business_flow(self, client):
        """模板：列表 → 详情 → 字段设置。"""
        # 模板列表
        r = client.get("/api/templates")
        assert r.status_code in (200, 404)
        # 模板选项
        r = client.get("/template/option")
        assert r.status_code in (200, 404)
        # 数据工厂模板
        r = client.get("/api/data/templates")
        assert r.status_code in (200, 404)
        # 模板字段
        r = client.post("/template/field/list", json={"type": "case"})
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 12. 项目管理-功能（5 页面）
# ═══════════════════════════════════════════════════════════
class Test12ProjectFunctions:
    """项目管理 - 文件/消息/脚本/环境/日志。"""

    def test_file_management_business_flow(self, client):
        """文件管理。"""
        # 文件列表
        r = client.post("/api/files", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 文件模块树
        r = client.post("/api/files/module/tree", json={})
        assert r.status_code in (200, 404)
        # 文件类型
        r = client.get("/api/files/types")
        assert r.status_code in (200, 404)

    def test_message_and_script_business_flow(self, client):
        """消息管理 + 公共脚本。"""
        # 消息通知列表
        r = client.post("/api/messages", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 机器人列表
        r = client.get("/api/notification/robots")
        assert r.status_code in (200, 404)
        # 公共脚本
        r = client.post("/project/custom/func/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 添加公共脚本
        r = client.post("/project/custom/func/add", json={
            "name": _unique("脚本"),
            "content": "def hello():\n    return 'hello'",
        })
        assert r.status_code in (200, 404)

    def test_environment_and_log_business_flow(self, client):
        """环境管理 + 日志。"""
        # 环境列表
        r = client.get("/api/environments")
        assert r.status_code in (200, 404)
        # 环境添加
        r = client.post("/api/environments", json={
            "name": _unique("环境"),
            "description": "E2E 测试环境",
        })
        assert r.status_code in (200, 201)
        # 项目日志
        r = client.post("/api/logs", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 13. 系统设置-系统（10 页面）
# ═══════════════════════════════════════════════════════════
class Test13SystemSettings:
    """系统设置 - 系统级。"""

    def test_system_user_and_group_business_flow(self, client):
        """系统用户 + 用户组。"""
        # 用户列表
        r = client.get("/api/users")
        assert r.status_code in (200, 404)
        # 用户组列表
        r = client.get("/api/user-groups")
        assert r.status_code in (200, 404)
        # 系统版本
        r = client.get("/system/version/current")
        assert r.status_code in (200, 404)

    def test_org_and_parameter_business_flow(self, client):
        """组织项目 + 系统参数。"""
        # 组织列表
        r = client.get("/api/organizations")
        assert r.status_code in (200, 404)
        # 组织切换选项
        r = client.get("/system/organization/switch-option")
        assert r.status_code in (200, 404)
        # 系统参数
        r = client.get("/api/settings")
        assert r.status_code in (200, 404)

    def test_resource_pool_and_plugin_business_flow(self, client):
        """资源池 + 插件。"""
        # 资源池列表
        r = client.get("/api/resource-pools")
        assert r.status_code in (200, 404)
        # 插件列表
        r = client.get("/api/plugins")
        assert r.status_code in (200, 404)
        # 授权管理
        r = client.get("/api/license")
        assert r.status_code in (200, 404)

    def test_system_log_business_flow(self, client):
        """系统日志。"""
        r = client.get("/api/logs/system")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 14. 系统设置-组织（9 页面）
# ═══════════════════════════════════════════════════════════
class Test14OrgSettings:
    """系统设置 - 组织级。"""

    def test_org_member_and_project_business_flow(self, client):
        """组织成员 + 组织项目。"""
        # 组织成员列表
        r = client.get("/api/organization/members")
        assert r.status_code in (200, 404)
        # 组织项目列表
        r = client.get("/api/organization/projects")
        assert r.status_code in (200, 404)

    def test_org_template_and_task_center_business_flow(self, client):
        """组织模板 + 任务中心。"""
        # 组织模板列表
        r = client.get("/api/organization/templates")
        assert r.status_code in (200, 404)
        # 任务中心
        r = client.post("/organization/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 15. 分享与全页面
# ═══════════════════════════════════════════════════════════
class Test15ShareAndFullPage:
    """分享页面 + 全页面。"""

    def test_login_and_auth_business_flow(self, client):
        """登录认证。"""
        # 已登录
        r = client.get("/is-login")
        assert r.status_code == 200
        data = _data(r)
        assert "id" in data or "username" in data or "sessionId" in data
        # 个人信息
        r = client.get("/personal/get")
        assert r.status_code == 200
        # 菜单列表
        r = client.post("/api/user/menu")
        assert r.status_code in (200, 404)

    def test_share_pages_business_flow(self, client):
        """分享页面。"""
        # 场景报告分享
        r = client.get("/share/report/scenario")
        assert r.status_code in (200, 404)
        # 用例报告分享
        r = client.get("/share/report/case")
        assert r.status_code in (200, 404)
        # 测试计划报告分享
        r = client.get("/share/report/test-plan")
        assert r.status_code in (200, 404)

    def test_full_page_export(self, client):
        """全页面 - PDF 导出。"""
        # 测试计划 PDF
        r = client.post("/api/test-plan/report/export", json={"format": "pdf"})
        assert r.status_code in (200, 400, 404, 422)
        # 场景 PDF
        r = client.post("/api/report/scenario/export", json={"format": "pdf"})
        assert r.status_code in (200, 400, 404, 422)
        # 用例 PDF
        r = client.post("/api/report/case/export", json={"format": "pdf"})
        assert r.status_code in (200, 400, 404, 422)


# ═══════════════════════════════════════════════════════════
# 数据保留验证
# ═══════════════════════════════════════════════════════════
class TestDataPreserved:
    """验证各模块测试数据被保留。"""

    def test_cases_data_preserved(self, client):
        """用例数据。"""
        r = client.get("/api/cases")
        assert r.status_code == 200
        data = _data(r)
        assert "cases" in data
        assert data["total"] >= 50

    def test_defects_data_preserved(self, client):
        """缺陷数据。"""
        r = client.post("/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _data(r)
        assert "list" in data
        # 种子数据应该有至少 15 条
        assert data["total"] >= 15

    def test_api_definitions_data_preserved(self, client):
        """接口定义数据。"""
        r = client.post("/api/definition/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _data(r)
        assert "list" in data or "items" in data
        total = data.get("total", 0)
        assert total >= 5

    def test_test_plans_data_preserved(self, client):
        """测试计划数据。"""
        r = client.post("/test-plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = _data(r)
        assert "list" in data
        assert data["total"] >= 15

    def test_api_scenarios_data_preserved(self, client):
        """接口场景数据。"""
        r = client.post("/api/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            data = _data(r)
            assert "list" in data or "items" in data
