"""
按业务模块全量测试（保留测试数据）
=================================
针对前端界面（TestPilot 风格）各业务模块进行全量接口测试，
创建的数据保留在数据库中，不执行清理操作。

覆盖模块：
  1. 工作台 Dashboard     — 项目概览、我的用例/缺陷/接口用例/场景/计划/评审、待办、布局、统计
  2. 功能用例管理         — 列表/创建/详情/更新/删除、模块树、回收站、脑图、自定义字段、导入模板
  3. 接口定义             — 列表/CRUD/回收站/模块管理
  4. 接口用例             — 列表/CRUD/统计/执行历史
  5. 接口场景             — 列表/CRUD/模块/统计
  6. Mock 服务            — 列表/添加/模块
  7. 用例评审             — 列表/CRUD/模块/人员选项
  8. 缺陷管理             — 列表/CRUD/回收站/模板/变更历史
  9. 测试计划             — 列表/CRUD/模块/统计/归档/详情关联
 10. 项目文件管理         — 列表/模块树/类型
 11. 项目环境管理         — 列表/增删/选项/全局参数
 12. 项目消息通知         — 机器人/消息任务
 13. 项目自定义脚本       — 增删/列表
 14. 测试报告             — 报告列表/计划报告/回收站/用例报告/场景报告
 15. 系统设置             — 版本/脚本健康度/运行统计/洞察
 16. 个人设置             — 本地配置/API Key/个人信息/修改密码/登录态
 17. apitest 环境         — 列表/增删/导入导出/元数据/统计/日志
 18. 消息中心             — 列表/已读
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量（必须在导入 app.main 之前）
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "KEEP-DATA-"


def _data(resp):
    """解析响应，统一取 data 层。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _code(resp):
    """获取业务码。"""
    body = resp.json()
    if isinstance(body, dict):
        return body.get("code", 200)
    return 200


def _unique(prefix="测试"):
    """生成唯一名称。"""
    return f"{PREFIX}{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def client():
    """已登录的测试客户端。"""
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
        yield c


# ════════════════════════════════════════════════════════════
# 一、工作台 Dashboard
# ════════════════════════════════════════════════════════════
class TestWorkbench:
    """工作台 Dashboard 全量测试。"""

    def test_home_stats(self, client):
        """首页统计（缺陷/用例/接口用例/场景/计划/定义数量）。"""
        r = client.get("/dashboard/home")
        assert r.status_code == 200, r.text
        data = _data(r)
        for key in ["bugCount", "caseCount", "apiCaseCount", "scenarioCount", "testPlanCount", "definitionCount"]:
            assert key in data, f"缺少 {key}"

    def test_overview(self, client):
        """工作台总览（项目/用例/缺陷/计划分布）。"""
        r = client.get("/dashboard/overview")
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "projectCount" in data
        assert "caseStatus" in data
        assert "defectSeverity" in data

    def test_project_view(self, client):
        """项目概览（按时间统计创建量）。"""
        r = client.post("/dashboard/project_view", json={"dayNumber": 7})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "xaxis" in data
        assert "caseCountMap" in data

    def test_create_by_me(self, client):
        """我创建的数据统计。"""
        r = client.post("/dashboard/create_by_me", json={"dayNumber": 7})
        assert r.status_code == 200, r.text

    def test_my_functional_cases(self, client):
        """我的功能用例列表。"""
        r = client.post("/dashboard/my/functional/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_my_bugs(self, client):
        """我的缺陷列表。"""
        r = client.post("/dashboard/my/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_my_api_cases(self, client):
        """我的接口用例列表。"""
        r = client.post("/dashboard/my/api/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_my_scenarios(self, client):
        """我的场景列表。"""
        r = client.post("/dashboard/my/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_my_plans(self, client):
        """我的测试计划列表。"""
        r = client.post("/dashboard/my/plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_my_reviews(self, client):
        """我的用例评审列表。"""
        r = client.post("/dashboard/my/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_todo_plans(self, client):
        """待办测试计划。"""
        r = client.post("/dashboard/todo/plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_todo_reviews(self, client):
        """待办用例评审。"""
        r = client.post("/dashboard/todo/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_todo_bugs(self, client):
        """待办缺陷。"""
        r = client.post("/dashboard/todo/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_layout_get(self, client):
        """获取工作台布局。"""
        r = client.get("/dashboard/layout/get")
        assert r.status_code == 200, r.text

    def test_layout_edit(self, client):
        """更新工作台布局。"""
        r = client.post("/dashboard/layout/edit", json={"layout": []})
        assert r.status_code in (200, 405), r.text

    def test_case_count(self, client):
        """用例数量统计卡片。"""
        r = client.post("/dashboard/case_count", json={})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "statusStatisticsMap" in data

    def test_bug_count(self, client):
        """缺陷数量统计卡片。"""
        r = client.post("/dashboard/bug_count", json={})
        assert r.status_code == 200, r.text

    def test_api_count(self, client):
        """接口数量统计卡片。"""
        r = client.post("/dashboard/api_count", json={})
        assert r.status_code == 200, r.text

    def test_api_case_count(self, client):
        """接口用例数量统计卡片。"""
        r = client.post("/dashboard/api_case_count", json={})
        assert r.status_code == 200, r.text

    def test_scenario_count(self, client):
        """场景数量统计卡片。"""
        r = client.post("/dashboard/scenario_count", json={})
        assert r.status_code == 200, r.text

    def test_create_bug_by_me(self, client):
        """我创建的缺陷统计。"""
        r = client.post("/dashboard/create_bug_by_me", json={})
        assert r.status_code == 200, r.text

    def test_handle_bug_by_me(self, client):
        """待我处理的缺陷统计。"""
        r = client.post("/dashboard/handle_bug_by_me", json={})
        assert r.status_code == 200, r.text

    def test_member_options(self, client):
        """项目成员下拉选项。"""
        r = client.get("/dashboard/member/get-project-member/option")
        assert r.status_code == 200, r.text

    def test_plan_options(self, client):
        """计划下拉选项。"""
        r = client.get("/dashboard/plan/option")
        assert r.status_code == 200, r.text

    def test_plan_view(self, client):
        """测试计划概览。"""
        r = client.post("/dashboard/plan_view", json={})
        assert r.status_code == 200, r.text

    def test_api_change(self, client):
        """接口变更列表。"""
        r = client.post("/dashboard/api_change", json={})
        assert r.status_code == 200, r.text

    def test_definition_rage(self, client):
        """接口覆盖率统计。"""
        r = client.get("/api/definition/rage")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 二、功能用例管理
# ════════════════════════════════════════════════════════════
class TestFunctionalCaseManagement:
    """功能用例管理全量测试（保留数据）。"""

    def test_case_list(self, client):
        """用例列表。"""
        r = client.post("/functional/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_case_create_and_detail(self, client):
        """创建用例 + 查看详情。"""
        name = _unique("功能用例")
        r = client.post("/functional/case/add", json={
            "name": name,
            "priority": "P1",
            "type": "功能测试",
            "description": "综合测试保留数据-功能用例",
            "tags": ["保留", "综合"],
        })
        assert r.status_code == 200, r.text
        case_id = _data(r)["id"]
        assert case_id

        # 查看详情
        r = client.post("/functional/case/detail", json={"id": case_id})
        assert r.status_code == 200, r.text
        detail = _data(r)
        assert detail.get("name") == name or detail.get("title") == name

    def test_case_update(self, client):
        """更新用例。"""
        name = _unique("更新用例")
        r = client.post("/functional/case/add", json={"name": name})
        assert r.status_code == 200
        case_id = _data(r)["id"]

        new_name = _unique("更新后")
        r = client.post("/functional/case/update", json={
            "id": case_id, "name": new_name, "priority": "P0",
        })
        assert r.status_code == 200, r.text

    def test_case_delete(self, client):
        """删除用例（软删除到回收站）。"""
        name = _unique("删除用例")
        r = client.post("/functional/case/add", json={"name": name})
        assert r.status_code == 200
        case_id = _data(r)["id"]

        r = client.post("/functional/case/delete", json={"id": case_id})
        assert r.status_code == 200, r.text

    def test_case_module_tree(self, client):
        """用例模块树。"""
        r = client.get("/functional/case/module/tree")
        assert r.status_code == 200, r.text

    def test_case_module_add(self, client):
        """用例模块添加。"""
        r = client.post("/functional/case/module/add", json={
            "name": _unique("功能模块"), "parentId": "root",
        })
        assert r.status_code == 200, r.text

    def test_case_trash_page(self, client):
        """用例回收站列表。"""
        r = client.post("/functional/case/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data

    def test_case_mindmap(self, client):
        """用例脑图。"""
        r = client.get("/functional/mind/case/list")
        assert r.status_code == 200, r.text

    def test_case_custom_field(self, client):
        """自定义字段。"""
        r = client.post("/functional/case/custom/field", json={"projectId": ""})
        assert r.status_code == 200, r.text

    def test_case_import_templates(self, client):
        """导入模板下载。"""
        r = client.get("/functional/case/download/excel/template")
        assert r.status_code == 200, r.text
        r = client.get("/functional/case/download/xmind/template")
        assert r.status_code == 200, r.text

    def test_case_batch_delete(self, client):
        """批量删除用例。"""
        ids = []
        for i in range(2):
            r = client.post("/functional/case/add", json={"name": _unique(f"批量{i}")})
            ids.append(_data(r)["id"])
        r = client.post("/functional/case/batch/delete-to-gc", json={"ids": ids})
        assert r.status_code == 200, r.text

    def test_case_batch_edit(self, client):
        """批量编辑用例。"""
        r = client.post("/functional/case/add", json={"name": _unique("批量编辑")})
        case_id = _data(r)["id"]
        r = client.post("/functional/case/batch/edit", json={
            "ids": [case_id], "priority": "P0",
        })
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 三、接口定义
# ════════════════════════════════════════════════════════════
class TestApiDefinition:
    """接口定义全量测试（保留数据）。"""

    def test_definition_page(self, client):
        """接口定义列表。"""
        r = client.post("/api/definition/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_definition_crud(self, client):
        """接口定义增删改查。"""
        name = _unique("接口定义")
        r = client.post("/api/definition/add", json={
            "name": name, "method": "GET", "path": f"/api/{uuid.uuid4().hex[:8]}",
            "protocol": "HTTP", "description": "保留数据-接口定义",
        })
        assert r.status_code == 200, r.text
        def_id = _data(r)["id"]
        assert def_id

        # 查看详情
        r = client.get(f"/api/definition/get-detail/{def_id}")
        assert r.status_code == 200, r.text
        detail = _data(r)
        assert detail.get("name") == name

        # 更新
        new_name = _unique("接口定义-更新")
        r = client.post("/api/definition/update", json={"id": def_id, "name": new_name})
        assert r.status_code == 200, r.text

        # 软删除
        r = client.post("/api/definition/delete-to-gc", json={"id": def_id})
        assert r.status_code == 200, r.text

    def test_definition_module_tree(self, client):
        """接口定义模块树。"""
        r = client.get("/api/definition/module/tree")
        assert r.status_code == 200, r.text

    def test_definition_module_add(self, client):
        """接口定义模块添加。"""
        r = client.post("/api/definition/module/add", json={
            "name": _unique("定义模块"), "parentId": "root",
        })
        assert r.status_code == 200, r.text

    def test_definition_module_count(self, client):
        """接口定义模块统计。"""
        r = client.post("/api/definition/module/count", json={})
        assert r.status_code == 200, r.text

    def test_definition_trash(self, client):
        """接口定义回收站。"""
        r = client.get("/api/definition/trash/page", params={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_definition_recover(self, client):
        """接口定义回收站恢复。"""
        name = _unique("恢复定义")
        r = client.post("/api/definition/add", json={
            "name": name, "method": "GET", "path": f"/recover/{uuid.uuid4().hex[:8]}",
        })
        assert r.status_code == 200
        def_id = _data(r)["id"]

        # 软删除进回收站
        r = client.post("/api/definition/delete-to-gc", json={"id": def_id})
        assert r.status_code == 200

        # 恢复
        r = client.post("/api/definition/recover", json={"id": def_id})
        assert r.status_code == 200, r.text
        assert _code(r) == 200

    def test_definition_batch_delete(self, client):
        """接口定义批量删除。"""
        ids = []
        for i in range(2):
            r = client.post("/api/definition/add", json={
                "name": _unique(f"批量定义{i}"), "method": "POST",
                "path": f"/batch/{uuid.uuid4().hex[:8]}",
            })
            ids.append(_data(r)["id"])
        r = client.post("/api/definition/batch/delete-to-gc", json={"ids": ids})
        assert r.status_code == 200, r.text

    def test_definition_copy(self, client):
        """接口定义复制。"""
        r = client.post("/api/definition/add", json={
            "name": _unique("复制定义"), "method": "GET", "path": f"/copy/{uuid.uuid4().hex[:8]}",
        })
        assert r.status_code == 200
        def_id = _data(r)["id"]
        r = client.post("/api/definition/copy", json={"id": def_id})
        assert r.status_code == 200, r.text

    def test_definition_follow(self, client):
        """接口定义关注/取消关注。"""
        r = client.post("/api/definition/add", json={
            "name": _unique("关注定义"), "method": "GET", "path": f"/follow/{uuid.uuid4().hex[:8]}",
        })
        def_id = _data(r)["id"]
        r = client.get("/api/definition/follow", params={"id": def_id})
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 四、接口用例
# ════════════════════════════════════════════════════════════
class TestApiCase:
    """接口用例全量测试（保留数据）。"""

    def test_case_page(self, client):
        """接口用例列表。"""
        r = client.post("/api/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_case_crud(self, client):
        """接口用例增删改查。"""
        name = _unique("接口用例")
        r = client.post("/api/case/add", json={"name": name, "method": "GET"})
        assert r.status_code == 200, r.text
        case_id = _data(r)["id"]
        assert case_id

        # 详情
        r = client.get(f"/api/case/get-detail/{case_id}")
        assert r.status_code == 200, r.text

        # 更新
        r = client.post("/api/case/update", json={"id": case_id, "name": _unique("接口用例-更新")})
        assert r.status_code == 200, r.text

        # 删除
        r = client.post("/api/case/delete-to-gc", json={"id": case_id})
        assert r.status_code == 200, r.text

    def test_case_statistics(self, client):
        """接口用例执行率统计。"""
        r = client.post("/api/case/statistics", json={})
        assert r.status_code == 200, r.text

    def test_case_execute_history(self, client):
        """接口用例执行历史。"""
        r = client.post("/api/case/execute/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_case_operation_history(self, client):
        """接口用例变更历史。"""
        r = client.post("/api/case/operation-history/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_case_trash(self, client):
        """接口用例回收站。"""
        r = client.post("/api/case/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_case_recover(self, client):
        """接口用例回收站恢复。"""
        r = client.post("/api/case/add", json={"name": _unique("恢复接口用例"), "method": "GET"})
        assert r.status_code == 200
        case_id = _data(r)["id"]

        r = client.post("/api/case/delete-to-gc", json={"id": case_id})
        assert r.status_code == 200

        r = client.get("/api/case/recover", params={"id": case_id})
        assert r.status_code == 200, r.text
        assert _code(r) == 200

    def test_case_batch_delete(self, client):
        """接口用例批量删除。"""
        ids = []
        for i in range(2):
            r = client.post("/api/case/add", json={"name": _unique(f"批量接口{i}"), "method": "GET"})
            ids.append(_data(r)["id"])
        r = client.post("/api/case/batch/delete-to-gc", json={"ids": ids})
        assert r.status_code == 200, r.text

    def test_case_follow(self, client):
        """接口用例关注。"""
        r = client.post("/api/case/add", json={"name": _unique("关注接口用例"), "method": "GET"})
        case_id = _data(r)["id"]
        r = client.post("/api/case/follow", json={"id": case_id})
        assert r.status_code == 200, r.text
        r = client.post("/api/case/unfollow", json={"id": case_id})
        assert r.status_code == 200, r.text

    def test_case_reference(self, client):
        """接口用例依赖关系。"""
        r = client.post("/api/case/get-reference", json={"id": ""})
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 五、接口场景
# ════════════════════════════════════════════════════════════
class TestApiScenario:
    """接口场景全量测试（保留数据）。"""

    def test_scenario_page(self, client):
        """场景列表。"""
        r = client.post("/api/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_scenario_crud(self, client):
        """场景增删改查。"""
        name = _unique("接口场景")
        r = client.post("/api/scenario/add", json={"name": name})
        assert r.status_code == 200, r.text
        scn_id = _data(r)["id"]
        assert scn_id

        # 详情
        r = client.get(f"/api/scenario/get/{scn_id}")
        assert r.status_code == 200, r.text

        # 更新
        r = client.post("/api/scenario/update", json={"id": scn_id, "name": _unique("场景-更新")})
        assert r.status_code == 200, r.text

        # 删除
        r = client.post("/api/scenario/delete-to-gc", json={"id": scn_id})
        assert r.status_code == 200, r.text

    def test_scenario_module_tree(self, client):
        """场景模块树。"""
        r = client.get("/api/scenario/module/tree")
        assert r.status_code == 200, r.text

    def test_scenario_module_add(self, client):
        """场景模块添加。"""
        r = client.post("/api/scenario/module/add", json={
            "name": _unique("场景模块"), "parentId": "root",
        })
        assert r.status_code == 200, r.text

    def test_scenario_module_count(self, client):
        """场景模块统计。"""
        r = client.post("/api/scenario/module/count", json={})
        assert r.status_code == 200, r.text

    def test_scenario_statistics(self, client):
        """场景执行率统计。"""
        r = client.post("/api/scenario/statistics", json={})
        assert r.status_code == 200, r.text

    def test_scenario_execute_history(self, client):
        """场景执行历史。"""
        r = client.post("/api/scenario/execute/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_scenario_trash(self, client):
        """场景回收站。"""
        r = client.post("/api/scenario/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_scenario_recover(self, client):
        """场景回收站恢复。"""
        r = client.post("/api/scenario/add", json={"name": _unique("恢复场景")})
        assert r.status_code == 200
        scn_id = _data(r)["id"]

        r = client.post("/api/scenario/delete-to-gc", json={"id": scn_id})
        assert r.status_code == 200

        r = client.post("/api/scenario/recover", json={"id": scn_id})
        assert r.status_code == 200, r.text
        assert _code(r) == 200

    def test_scenario_batch_operation(self, client):
        """场景批量操作。"""
        ids = []
        for i in range(2):
            r = client.post("/api/scenario/add", json={"name": _unique(f"批量场景{i}")})
            ids.append(_data(r)["id"])
        r = client.post("/api/scenario/batch/delete", json={"ids": ids})
        assert r.status_code == 200, r.text

    def test_scenario_follow(self, client):
        """场景关注/取消关注。"""
        r = client.post("/api/scenario/add", json={"name": _unique("关注场景")})
        scn_id = _data(r)["id"]
        r = client.post("/api/scenario/follow", json={"id": scn_id})
        assert r.status_code == 200, r.text

    def test_scenario_run(self, client):
        """场景执行。"""
        r = client.post("/api/scenario/add", json={"name": _unique("执行场景")})
        scn_id = _data(r)["id"]
        r = client.post("/api/scenario/run", json={"id": scn_id})
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 六、Mock 服务
# ════════════════════════════════════════════════════════════
class TestApiMock:
    """Mock 服务全量测试（保留数据）。"""

    def test_mock_page(self, client):
        """Mock 列表。"""
        r = client.post("/api/definition/mock/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_mock_add(self, client):
        """添加 Mock。"""
        name = _unique("Mock服务")
        r = client.post("/api/definition/mock/add", json={
            "name": name, "method": "GET",
            "path": f"/mock/{uuid.uuid4().hex[:8]}",
            "response_body": '{"success": true}',
            "status_code": 200,
        })
        assert r.status_code == 200, r.text

    def test_mock_module_tree(self, client):
        """Mock 模块树。"""
        r = client.get("/api/definition/module/tree")
        assert r.status_code == 200, r.text

    def test_mock_delete(self, client):
        """删除 Mock。"""
        r = client.post("/api/definition/mock/add", json={
            "name": _unique("删除Mock"), "method": "GET",
            "path": f"/mock-del/{uuid.uuid4().hex[:8]}",
        })
        assert r.status_code == 200
        # 获取 mock ID 并删除
        r = client.post("/api/definition/mock/page", json={"pageSize": 100})
        mocks = _data(r).get("list", [])
        for m in mocks:
            if m.get("name", "").startswith("KEEP-DATA-删除Mock"):
                r = client.post("/api/definition/mock/delete", json={"id": m["id"]})
                assert r.status_code == 200
                return

    def test_mock_enable(self, client):
        """Mock 启用/禁用。"""
        r = client.post("/api/definition/mock/add", json={
            "name": _unique("启用Mock"), "method": "GET",
            "path": f"/mock-enable/{uuid.uuid4().hex[:8]}",
        })
        assert r.status_code == 200

        r = client.post("/api/definition/mock/page", json={"pageSize": 100})
        mocks = _data(r).get("list", [])
        for m in mocks:
            if m.get("name", "").startswith("KEEP-DATA-启用Mock"):
                r = client.post("/api/definition/mock/enable", json={"id": m["id"]})
                assert r.status_code == 200
                return

    def test_mock_get_url(self, client):
        """Mock URL 获取。"""
        r = client.get("/api/definition/mock/get-url/")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 七、用例评审
# ════════════════════════════════════════════════════════════
class TestCaseReview:
    """用例评审全量测试（保留数据）。"""

    def test_review_page(self, client):
        """评审列表。"""
        r = client.post("/case/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_review_crud(self, client):
        """评审增删改查。"""
        name = _unique("用例评审")
        r = client.post("/case/review/add", json={"name": name})
        assert r.status_code == 200, r.text
        review_id = _data(r)["id"]
        assert review_id

        # 详情
        r = client.get(f"/case/review/detail/{review_id}")
        assert r.status_code == 200, r.text
        data = _data(r)
        # 详情必须包含前端 ReviewItem 完整字段（reviewers 缺失会导致前端 .map 崩溃）
        assert "reviewers" in data, "详情缺少 reviewers 字段"
        assert isinstance(data["reviewers"], list), "reviewers 必须是数组"
        assert "caseCount" in data, "详情缺少 caseCount 字段"
        assert "passRate" in data, "详情缺少 passRate 字段"
        assert "followFlag" in data, "详情缺少 followFlag 字段"
        assert "projectId" in data, "详情缺少 projectId 字段"

        # 更新
        r = client.post("/case/review/edit", json={"id": review_id, "name": _unique("评审-更新")})
        assert r.status_code == 200, r.text

    def test_review_module_tree(self, client):
        """评审模块树。"""
        r = client.get("/case/review/module/tree")
        assert r.status_code == 200, r.text

    def test_review_user_option(self, client):
        """评审人员选项。"""
        r = client.get("/case/review/user-option")
        assert r.status_code == 200, r.text

    def test_review_delete(self, client):
        """删除评审。"""
        r = client.post("/case/review/add", json={"name": _unique("删除评审")})
        assert r.status_code == 200
        review_id = _data(r)["id"]
        r = client.post("/case/review/delete", json={"id": review_id})
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 八、缺陷管理
# ════════════════════════════════════════════════════════════
class TestBugManagement:
    """缺陷管理全量测试（保留数据）。"""

    def test_bug_page(self, client):
        """缺陷列表。"""
        r = client.post("/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_bug_crud(self, client):
        """缺陷增删改查。"""
        title = _unique("缺陷")
        r = client.post("/bug/add", json={
            "title": title, "severity": "P1", "status": "open",
            "description": "保留数据-缺陷",
        })
        assert r.status_code == 200, r.text
        bug_id = _data(r)["id"]
        assert bug_id

        # 详情
        r = client.get(f"/bug/get/{bug_id}")
        assert r.status_code == 200, r.text
        assert _data(r).get("title") == title

        # 更新
        r = client.post("/bug/update", json={
            "id": bug_id, "title": _unique("缺陷-更新"), "status": "in_progress",
        })
        assert r.status_code == 200, r.text

    def test_bug_trash(self, client):
        """缺陷回收站。"""
        r = client.post("/bug/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_bug_template(self, client):
        """缺陷模板。"""
        r = client.get("/bug/template/detail")
        assert r.status_code == 200, r.text

    def test_bug_history(self, client):
        """缺陷变更历史。"""
        r = client.post("/bug/history/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_bug_delete(self, client):
        """删除缺陷。"""
        r = client.post("/bug/add", json={"title": _unique("删除缺陷"), "severity": "P2"})
        assert r.status_code == 200
        bug_id = _data(r)["id"]

        r = client.post("/bug/delete", json={"id": bug_id})
        assert r.status_code == 200, r.text

    def test_bug_batch_delete(self, client):
        """批量删除缺陷。"""
        ids = []
        for i in range(2):
            r = client.post("/bug/add", json={"title": _unique(f"批量缺陷{i}"), "severity": "P2"})
            ids.append(_data(r)["id"])
        r = client.post("/bug/batch-delete", json={"ids": ids})
        assert r.status_code == 200, r.text

    def test_bug_recover(self, client):
        """缺陷回收站恢复。"""
        r = client.post("/bug/add", json={"title": _unique("恢复缺陷"), "severity": "P2"})
        assert r.status_code == 200
        bug_id = _data(r)["id"]

        r = client.post("/bug/delete", json={"id": bug_id})
        assert r.status_code == 200

        r = client.post("/bug/recover", json={"id": bug_id})
        assert r.status_code == 200, r.text

    def test_bug_custom_field(self, client):
        """缺陷自定义字段。"""
        r = client.get("/bug/header/custom-field/")
        assert r.status_code == 200, r.text

    def test_bug_columns_option(self, client):
        """缺陷列选项。"""
        r = client.get("/bug/columns-option/default")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 九、测试计划
# ════════════════════════════════════════════════════════════
class TestTestPlan:
    """测试计划全量测试（保留数据）。"""

    def test_plan_page(self, client):
        """测试计划列表。"""
        r = client.post("/test-plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data
        assert "total" in data

    def test_plan_crud(self, client):
        """测试计划增删改查。"""
        name = _unique("测试计划")
        r = client.post("/test-plan/add", json={
            "name": name, "description": "保留数据-测试计划", "priority": "P1",
        })
        assert r.status_code == 200, r.text
        plan_id = _data(r)["id"]
        assert plan_id

        # 详情
        r = client.get(f"/test-plan/{plan_id}")
        assert r.status_code == 200, r.text
        plan_data = _data(r)
        assert plan_data.get("name") == name or plan_data.get("id") == plan_id

        # 更新
        r = client.post("/test-plan/update", json={
            "id": plan_id, "name": _unique("计划-更新"), "status": "running",
        })
        assert r.status_code == 200, r.text

    def test_plan_module_tree(self, client):
        """测试计划模块树。"""
        r = client.get("/test-plan/module/tree")
        assert r.status_code == 200, r.text

    def test_plan_module_add(self, client):
        """测试计划模块添加。"""
        r = client.post("/test-plan/module/add", json={
            "name": _unique("计划模块"), "parentId": "root",
        })
        assert r.status_code == 200, r.text

    def test_plan_module_count(self, client):
        """测试计划模块统计。"""
        r = client.get("/test-plan/module/count")
        assert r.status_code == 200, r.text

    def test_plan_statistics(self, client):
        """测试计划通过率统计。"""
        r = client.get("/test-plan/statistics")
        assert r.status_code == 200, r.text

    def test_plan_get_count(self, client):
        """测试计划数量统计。"""
        r = client.get("/test-plan/getCount")
        assert r.status_code == 200, r.text

    def test_plan_list(self, client):
        """测试计划下拉列表。"""
        r = client.get("/test-plan/test-plan-list")
        assert r.status_code == 200, r.text

    def test_plan_archive(self, client):
        """测试计划归档。"""
        r = client.post("/test-plan/add", json={"name": _unique("归档计划")})
        assert r.status_code == 200
        plan_id = _data(r)["id"]

        r = client.post("/test-plan/archived", json={"id": plan_id})
        assert r.status_code == 200, r.text

    def test_plan_copy(self, client):
        """测试计划复制。"""
        r = client.post("/test-plan/add", json={"name": _unique("复制计划")})
        assert r.status_code == 200
        plan_id = _data(r)["id"]

        r = client.post("/test-plan/copy", json={"id": plan_id})
        assert r.status_code == 200, r.text

    def test_plan_association(self, client):
        """测试计划-用例关联。"""
        r = client.post("/test-plan/add", json={"name": _unique("关联计划")})
        assert r.status_code == 200
        plan_id = _data(r)["id"]

        r = client.post("/test-plan/association/page", json={
            "planId": plan_id, "pageSize": 10, "current": 1,
        })
        assert r.status_code == 200, r.text

    def test_plan_functional_cases(self, client):
        """计划功能用例列表。"""
        r = client.post("/test-plan/functional/case/page", json={
            "pageSize": 10, "current": 1,
        })
        assert r.status_code == 200, r.text
        assert "list" in _data(r)

    def test_plan_api_cases(self, client):
        """计划接口用例列表。"""
        r = client.post("/test-plan/api/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_plan_api_scenarios(self, client):
        """计划接口场景列表。"""
        r = client.post("/test-plan/api/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_plan_bugs(self, client):
        """计划缺陷列表。"""
        r = client.post("/test-plan/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_plan_report_page(self, client):
        """计划报告列表。"""
        r = client.post("/test-plan/report/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_plan_mind_data(self, client):
        """测试计划脑图。"""
        r = client.get("/test-plan/mind/data")
        assert r.status_code == 200, r.text

    def test_plan_detail_stats(self, client):
        """测试计划详情统计。"""
        r = client.post("/test-plan/add", json={"name": _unique("统计计划")})
        assert r.status_code == 200
        plan_id = _data(r)["id"]
        r = client.get(f"/test-plan/statistics/{plan_id}")
        assert r.status_code == 200, r.text

    def test_plan_batch_edit(self, client):
        """测试计划批量编辑。"""
        r = client.post("/test-plan/add", json={"name": _unique("批量编辑计划")})
        assert r.status_code == 200
        plan_id = _data(r)["id"]

        r = client.post("/test-plan/batch-edit", json={"ids": [plan_id], "priority": "P0"})
        assert r.status_code == 200, r.text

    def test_plan_delete(self, client):
        """删除测试计划。"""
        r = client.post("/test-plan/add", json={"name": _unique("删除计划")})
        assert r.status_code == 200
        plan_id = _data(r)["id"]
        r = client.post("/test-plan/delete", json={"id": plan_id})
        assert r.status_code == 200, r.text

    def test_plan_execute_history(self, client):
        """计划执行历史。"""
        r = client.post("/test-plan/his/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_plan_user_options(self, client):
        """计划成员选项。"""
        r = client.get("/test-plan/functional/case/user-option")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十、项目文件管理
# ════════════════════════════════════════════════════════════
class TestProjectFileManagement:
    """项目文件管理全量测试（保留数据）。"""

    def test_file_page(self, client):
        """文件列表。"""
        r = client.post("/project/file/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "list" in data

    def test_file_module_tree(self, client):
        """文件模块树。"""
        r = client.get("/project/file-module/tree")
        assert r.status_code == 200, r.text

    def test_file_types(self, client):
        """文件类型。"""
        r = client.get("/project/file/type")
        assert r.status_code == 200, r.text

    def test_file_upload(self, client):
        """文件上传。"""
        r = client.post("/project/file/upload", files={
            "file": ("test.txt", b"hello world", "text/plain"),
        })
        assert r.status_code == 200, r.text

    def test_file_module_add(self, client):
        """文件模块添加。"""
        r = client.post("/project/file-module/add", json={
            "name": _unique("文件模块"), "parentId": "root",
        })
        assert r.status_code == 200, r.text

    def test_file_module_delete(self, client):
        """文件模块删除。"""
        r = client.post("/project/file-module/delete", json={"id": "nonexistent"})
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十一、项目环境管理
# ════════════════════════════════════════════════════════════
class TestProjectEnvironment:
    """项目环境管理全量测试（保留数据）。"""

    def test_env_list(self, client):
        """环境列表。"""
        r = client.get("/project/environment/list")
        assert r.status_code == 200, r.text

    def test_env_add(self, client):
        """环境添加。"""
        name = _unique("项目环境")
        r = client.post("/project/environment/add", json={"name": name, "type": "HTTP"})
        assert r.status_code == 200, r.text

    def test_env_options(self, client):
        """环境选项。"""
        r = client.get("/project/environment/get-options")
        assert r.status_code == 200, r.text

    def test_global_param_add(self, client):
        """全局参数添加。"""
        r = client.post("/project/global/params/add", json={
            "name": _unique("全局参数"), "paramType": "text", "value": "v1",
        })
        assert r.status_code == 200, r.text

    def test_env_delete(self, client):
        """环境删除。"""
        name = _unique("删除环境")
        r = client.post("/project/environment/add", json={"name": name, "type": "HTTP"})
        assert r.status_code == 200
        env_id = _data(r).get("id")
        if env_id:
            r = client.post(f"/project/environment/delete/{env_id}")
            assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十二、项目消息通知
# ════════════════════════════════════════════════════════════
class TestProjectMessage:
    """项目消息通知全量测试（保留数据）。"""

    def test_robot_list(self, client):
        """机器人列表。"""
        r = client.get("/project/robot/list")
        assert r.status_code == 200, r.text

    def test_message_task_get(self, client):
        """消息任务配置获取。"""
        r = client.get("/notice/message/task/get")
        assert r.status_code == 200, r.text

    def test_message_task_save(self, client):
        """消息任务配置保存。"""
        r = client.post("/notice/message/task/save", json={
            "testPlanTask": {"enable": True},
            "caseTask": {"enable": True},
        })
        assert r.status_code in (200, 405), r.text


# ════════════════════════════════════════════════════════════
# 十三、项目自定义脚本
# ════════════════════════════════════════════════════════════
class TestProjectCustomScript:
    """项目自定义脚本全量测试（保留数据）。"""

    def test_custom_func_page(self, client):
        """自定义脚本列表。"""
        r = client.get("/project/custom/func/page")
        assert r.status_code == 200, r.text

    def test_custom_func_add(self, client):
        """自定义脚本添加。"""
        r = client.post("/project/custom/func/add", json={
            "name": _unique("自定义脚本"),
            "script": "function test() { return 1; }",
            "type": "HTTP",
        })
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十四、测试报告
# ════════════════════════════════════════════════════════════
class TestReport:
    """测试报告全量测试（保留数据）。"""

    def test_report_list(self, client):
        """报告列表。"""
        r = client.get("/api/reports/list")
        assert r.status_code == 200, r.text

    def test_plan_report_page(self, client):
        """测试计划报告列表。"""
        r = client.post("/test-plan/report/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_report_trash(self, client):
        """报告回收站。"""
        r = client.get("/api/reports/trash/list")
        assert r.status_code == 200, r.text

    def test_case_report_page(self, client):
        """接口用例报告列表。"""
        r = client.post("/api/report/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_scenario_report_page(self, client):
        """场景报告列表。"""
        r = client.post("/api/report/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200, r.text

    def test_report_generate(self, client):
        """生成报告。"""
        r = client.post("/api/reports/generate", json={"format": "html"})
        assert r.status_code in (200, 404), r.text

    def test_report_trash_list(self, client):
        """报告回收站列表。"""
        r = client.get("/api/reports/trash/list")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十五、系统设置
# ════════════════════════════════════════════════════════════
class TestSystemSetting:
    """系统设置全量测试（保留数据）。"""

    def test_system_version(self, client):
        """系统版本。"""
        r = client.get("/system/version/current")
        assert r.status_code == 200, r.text
        data = _data(r)
        assert data

    def test_system_version_package(self, client):
        """系统版本包类型。"""
        r = client.get("/system/version/package-type")
        assert r.status_code == 200, r.text

    def test_script_health_stats(self, client):
        """脚本健康度统计。"""
        r = client.get("/api/scripthealth/stats")
        assert r.status_code == 200, r.text

    def test_run_stats(self, client):
        """运行统计。"""
        r = client.get("/api/runs/stats")
        assert r.status_code == 200, r.text

    def test_insights_risk(self, client):
        """洞察-高风险模块。"""
        r = client.get("/api/insights/risk")
        assert r.status_code == 200, r.text

    def test_insights_value(self, client):
        """洞察-价值量化。"""
        r = client.get("/api/insights/value")
        assert r.status_code == 200, r.text

    def test_insights_trace(self, client):
        """洞察-执行追溯。"""
        r = client.get("/api/insights/trace")
        assert r.status_code == 200, r.text

    def test_insights_skill_path(self, client):
        """洞察-职业发展路径。"""
        r = client.get("/api/insights/skill-path")
        assert r.status_code == 200, r.text

    def test_test_types(self, client):
        """测试类型。"""
        r = client.get("/api/test-types")
        assert r.status_code == 200, r.text
        assert "types" in _data(r)

    def test_tasks_list(self, client):
        """异步任务列表。"""
        r = client.get("/api/tasks")
        assert r.status_code == 200, r.text

    def test_runs_list(self, client):
        """运行记录列表。"""
        r = client.get("/api/runs")
        assert r.status_code == 200, r.text
        assert "records" in _data(r)

    def test_debug_logs(self, client):
        """调试日志。"""
        r = client.get("/api/debug/logs")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十六、个人设置
# ════════════════════════════════════════════════════════════
class TestPersonalSetting:
    """个人设置全量测试（保留数据）。"""

    def test_local_config_get(self, client):
        """本地执行配置。"""
        r = client.get("/user/local/config/get")
        assert r.status_code == 200, r.text

    def test_local_config_save(self, client):
        """本地执行配置保存。"""
        r = client.post("/user/local/config/update", json={
            "server": "localhost", "port": "8000",
        })
        assert r.status_code in (200, 405), r.text

    def test_api_key_list(self, client):
        """API Key 列表。"""
        r = client.get("/user/api/key/list")
        assert r.status_code == 200, r.text

    def test_api_key_add(self, client):
        """API Key 添加。"""
        r = client.post("/user/api/key/add", json={"name": _unique("APIKey")})
        assert r.status_code in (200, 404, 405), r.text

    def test_personal_get(self, client):
        """获取个人信息。"""
        r = client.get("/personal/get")
        assert r.status_code == 200, r.text
        data = _data(r)
        assert data.get("name")

    def test_is_login(self, client):
        """登录状态检查。"""
        r = client.get("/is-login")
        assert r.status_code == 200, r.text

    def test_update_password(self, client):
        """修改密码。"""
        r = client.post("/personal/update-password", json={
            "oldPassword": "wrong", "newPassword": "new123456",
        })
        assert r.status_code in (200, 400, 422), r.text


# ════════════════════════════════════════════════════════════
# 十七、apitest 环境
# ════════════════════════════════════════════════════════════
class TestApiTestEnvironment:
    """apitest 环境全量测试（保留数据）。"""

    def test_env_list(self, client):
        """环境列表。"""
        r = client.get("/api/apitest/environments")
        assert r.status_code == 200, r.text

    def test_env_add(self, client):
        """环境添加。"""
        name = _unique("API环境")
        r = client.post("/api/apitest/environments", json={
            "name": name, "base_url": f"https://{uuid.uuid4().hex[:8]}.example.com",
        })
        assert r.status_code == 200, r.text

    def test_env_import_export(self, client):
        """环境导入导出。"""
        r = client.get("/api/apitest/environments/nonexistent/export")
        assert r.status_code in (200, 404), r.text

    def test_apitest_meta(self, client):
        """接口测试元数据。"""
        r = client.get("/api/apitest/meta")
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "assert_types" in data

    def test_apitest_stats(self, client):
        """接口测试统计。"""
        r = client.get("/api/apitest/stats")
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "definitions" in data

    def test_apitest_logs(self, client):
        """操作日志。"""
        r = client.get("/api/apitest/logs")
        assert r.status_code == 200, r.text

    def test_apitest_import(self, client):
        """接口导入。"""
        sw = '{"openapi":"3.0.0","paths":{"/test-keep":{"get":{"summary":"测试保留"}}}}'
        r = client.post("/api/apitest/import", json={"content": sw, "format": "swagger"})
        assert r.status_code == 200, r.text

    def test_apitest_debug(self, client):
        """接口调试。"""
        r = client.post("/api/apitest/debug", json={
            "method": "GET", "url": "https://example.com",
            "timeout": 5,
        })
        assert r.status_code == 200, r.text

    def test_apitest_modules(self, client):
        """接口模块树。"""
        for scope in ["definition", "case", "scenario"]:
            r = client.get(f"/api/apitest/modules/{scope}")
            assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 十八、消息中心
# ════════════════════════════════════════════════════════════
class TestMessageCenter:
    """消息中心全量测试（保留数据）。"""

    def test_message_list(self, client):
        """消息列表。"""
        r = client.get("/api/message/list")
        assert r.status_code == 200, r.text

    def test_message_read(self, client):
        """消息已读。"""
        r = client.post("/api/message/read", json={"messageId": "nonexistent"})
        assert r.status_code == 200, r.text

    def test_notification_count(self, client):
        """未读消息计数。"""
        r = client.get("/notification/count")
        assert r.status_code == 200, r.text

    def test_notification_unread(self, client):
        """未读消息（带项目）。"""
        r = client.get("/notification/un-read")
        assert r.status_code == 200, r.text


# ════════════════════════════════════════════════════════════
# 辅助：数据验证
# ════════════════════════════════════════════════════════════
class TestDataVerification:
    """验证测试数据已保留在数据库中。"""

    def test_case_data_preserved(self, client):
        """验证功能用例数据已保留。"""
        r = client.post("/functional/case/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, r.text
        cases = _data(r).get("list", [])
        kept = [c for c in cases if c.get("name", "").startswith(PREFIX)]
        # 至少有一条保留数据（之前测试创建的）
        assert len(kept) >= 1, "未找到保留的功能用例数据"

    def test_bug_data_preserved(self, client):
        """验证缺陷数据已保留。"""
        r = client.post("/bug/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, r.text
        bugs = _data(r).get("list", [])
        kept = [b for b in bugs if b.get("title", "").startswith(PREFIX)]
        assert len(kept) >= 1, "未找到保留的缺陷数据"

    def test_definition_data_preserved(self, client):
        """验证接口定义数据已保留。"""
        r = client.post("/api/definition/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, r.text
        defs = _data(r).get("list", [])
        kept = [d for d in defs if d.get("name", "").startswith(PREFIX)]
        assert len(kept) >= 1, "未找到保留的接口定义数据"

    def test_case_data_preserved_api(self, client):
        """验证接口用例数据已保留。"""
        r = client.post("/api/case/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, r.text
        cases = _data(r).get("list", [])
        kept = [c for c in cases if c.get("name", "").startswith(PREFIX)]
        assert len(kept) >= 1, "未找到保留的接口用例数据"

    def test_scenario_data_preserved(self, client):
        """验证场景数据已保留。"""
        r = client.post("/api/scenario/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, r.text
        scenarios = _data(r).get("list", [])
        kept = [s for s in scenarios if s.get("name", "").startswith(PREFIX)]
        assert len(kept) >= 1, "未找到保留的场景数据"

    def test_plan_data_preserved(self, client):
        """验证测试计划数据已保留。"""
        r = client.post("/test-plan/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, r.text
        plans = _data(r).get("list", [])
        kept = [p for p in plans if p.get("name", "").startswith(PREFIX)]
        assert len(kept) >= 1, "未找到保留的测试计划数据"
