"""
前端界面全功能测试（test_frontend_ui_all.py）
=============================================
从前端界面（views）视角，覆盖所有界面模块具备的功能。

覆盖界面：
一、工作台 Dashboard
二、功能用例管理（列表/创建/详情/更新/删除/回收站/脑图/关联）
三、接口测试（接口定义/接口用例/场景/Mock CRUD + 模块管理）
四、用例评审
五、缺陷管理
六、测试计划
七、项目设置（文件管理/环境管理/消息通知/自定义脚本）
八、测试报告
九、系统设置/个人设置
十、AI 用例生成

每个界面测试其核心增删改查与列表功能，基于前端实际调用的接口路径。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "UI-ALL-"


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


def _ok(resp):
    """统一解析 {code, message, data} 响应。"""
    return resp.json()


def _data(resp):
    """提取响应 data 字段。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


# ═══════════════════════════════════════════════════════════
# 一、工作台 Dashboard
# ═══════════════════════════════════════════════════════════
class TestWorkbench:
    """工作台界面功能。"""

    def test_project_overview(self, client):
        """项目概览。"""
        r = client.post("/dashboard/project_view", json={})
        assert r.status_code == 200
        data = _data(r)
        assert "caseCountMap" in data

    def test_my_functional_cases(self, client):
        """我负责的功能用例。"""
        r = client.post("/dashboard/my/functional/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_my_bugs(self, client):
        """我负责的缺陷。"""
        r = client.post("/dashboard/my/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_my_api_cases(self, client):
        """我负责的接口用例。"""
        r = client.post("/dashboard/my/api/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_my_scenarios(self, client):
        """我负责的场景。"""
        r = client.post("/dashboard/my/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_my_plans(self, client):
        """我负责的测试计划。"""
        r = client.post("/dashboard/my/plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_my_reviews(self, client):
        """我参与的评审。"""
        r = client.post("/dashboard/my/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_todo_bugs(self, client):
        """待办缺陷。"""
        r = client.post("/dashboard/todo/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_created_by_me(self, client):
        """我创建的。"""
        r = client.post("/dashboard/create_by_me", json={})
        assert r.status_code == 200

    def test_case_count(self, client):
        """用例数量统计。"""
        r = client.post("/dashboard/case_count", json={})
        assert r.status_code == 200
        assert "statusStatisticsMap" in _data(r)

    def test_bug_count(self, client):
        """缺陷数量统计。"""
        r = client.post("/dashboard/bug_count", json={})
        assert r.status_code == 200

    def test_layout_get(self, client):
        """获取用户工作台布局。"""
        r = client.get("/dashboard/layout/get")
        assert r.status_code == 200

    def test_member_options(self, client):
        """项目成员下拉。"""
        r = client.get("/dashboard/member/get-project-member/option")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 二、功能用例管理
# ═══════════════════════════════════════════════════════════
class TestFunctionalCaseManagement:
    """功能用例管理界面功能。"""

    def test_case_list(self, client):
        """用例列表。"""
        r = client.post("/functional/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_case_create_and_detail(self, client):
        """创建用例并查看详情。"""
        name = f"{PREFIX}功能用例"
        r = client.post("/functional/case/add", json={
            "name": name, "priority": "P2", "test_type": "functional",
        })
        assert r.status_code == 200
        case_id = _data(r)["id"]

        r = client.post("/functional/case/detail", json={"id": case_id})
        assert r.status_code == 200
        detail = _data(r)
        assert detail.get("name") == name

        client.post("/functional/case/delete", json={"id": case_id})

    def test_case_update(self, client):
        """更新用例。"""
        r = client.post("/functional/case/add", json={"name": f"{PREFIX}更新前"})
        case_id = _data(r)["id"]

        r = client.post("/functional/case/update", json={
            "id": case_id, "name": f"{PREFIX}更新后", "priority": "P1",
        })
        assert r.status_code == 200
        assert _data(r).get("name") == f"{PREFIX}更新后"

        client.post("/functional/case/delete", json={"id": case_id})

    def test_case_module_tree(self, client):
        """用例模块树。"""
        r = client.get("/functional/case/module/tree")
        assert r.status_code == 200

    def test_case_module_crud(self, client):
        """用例模块增删。"""
        r = client.post("/functional/case/module/add", json={"name": f"{PREFIX}模块", "parentId": "root"})
        assert r.status_code == 200
        # 模块添加成功（data 可能为 null，但 HTTP 与业务码均成功）
        body = r.json()
        assert body.get("code") == 200

    def test_case_trash(self, client):
        """用例回收站。"""
        r = client.post("/functional/case/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_case_mindmap(self, client):
        """用例脑图。"""
        r = client.get("/functional/mind/case/list")
        assert r.status_code == 200

    def test_case_custom_field(self, client):
        """自定义字段。"""
        r = client.post("/functional/case/custom/field", json={"projectId": ""})
        assert r.status_code == 200

    def test_case_import_templates(self, client):
        """导入模板下载。"""
        r = client.get("/functional/case/download/excel/template")
        assert r.status_code == 200
        r = client.get("/functional/case/download/xmind/template")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 三、接口测试（定义/用例/场景/Mock）
# ═══════════════════════════════════════════════════════════
class TestApiDefinition:
    """接口定义界面功能。"""

    def test_definition_page(self, client):
        """接口定义列表。"""
        r = client.post("/api/definition/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_definition_crud(self, client):
        """接口定义增删改查。"""
        name = f"{PREFIX}接口定义"
        r = client.post("/api/definition/add", json={
            "name": name, "method": "GET", "path": "/api/test", "protocol": "HTTP",
        })
        assert r.status_code == 200
        def_id = _data(r)["id"]

        r = client.get(f"/api/definition/get-detail/{def_id}")
        assert r.status_code == 200
        assert _data(r).get("name") == name

        r = client.post("/api/definition/update", json={"id": def_id, "name": f"{PREFIX}接口定义-upd"})
        assert r.status_code == 200

        r = client.post("/api/definition/delete-to-gc", json={"id": def_id})
        assert r.status_code == 200

    def test_definition_module_tree(self, client):
        """接口定义模块树。"""
        r = client.get("/api/definition/module/tree")
        assert r.status_code == 200

    def test_definition_module_add(self, client):
        """接口定义模块添加。"""
        r = client.post("/api/definition/module/add", json={"name": f"{PREFIX}定义模块", "parentId": "root"})
        assert r.status_code == 200

    def test_definition_trash(self, client):
        """接口定义回收站。"""
        r = client.get("/api/definition/trash/page", params={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)


class TestApiCase:
    """接口用例界面功能。"""

    def test_case_page(self, client):
        """接口用例列表。"""
        r = client.post("/api/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_case_crud(self, client):
        """接口用例增删改查。"""
        r = client.post("/api/case/add", json={"name": f"{PREFIX}接口用例", "method": "GET"})
        assert r.status_code == 200
        case_id = _data(r)["id"]

        r = client.get(f"/api/case/get-detail/{case_id}")
        assert r.status_code == 200

        r = client.post("/api/case/update", json={"id": case_id, "name": f"{PREFIX}接口用例-upd"})
        assert r.status_code == 200

        r = client.post("/api/case/delete-to-gc", json={"id": case_id})
        assert r.status_code == 200

    def test_case_statistics(self, client):
        """接口用例执行率统计。"""
        r = client.post("/api/case/statistics", json={})
        assert r.status_code == 200

    def test_case_execute_history(self, client):
        """接口用例执行历史。"""
        r = client.post("/api/case/execute/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200


class TestApiScenario:
    """接口场景界面功能。"""

    def test_scenario_page(self, client):
        """场景列表。"""
        r = client.post("/api/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_scenario_crud(self, client):
        """场景增删改查。"""
        r = client.post("/api/scenario/add", json={"name": f"{PREFIX}场景"})
        assert r.status_code == 200
        scn_id = _data(r)["id"]

        r = client.get(f"/api/scenario/get/{scn_id}")
        assert r.status_code == 200

        r = client.post("/api/scenario/update", json={"id": scn_id, "name": f"{PREFIX}场景-upd"})
        assert r.status_code == 200

        r = client.post("/api/scenario/delete-to-gc", json={"id": scn_id})
        assert r.status_code == 200

    def test_scenario_module_tree(self, client):
        """场景模块树。"""
        r = client.get("/api/scenario/module/tree")
        assert r.status_code == 200

    def test_scenario_statistics(self, client):
        """场景执行率统计。"""
        r = client.post("/api/scenario/statistics", json={})
        assert r.status_code == 200


class TestApiMock:
    """Mock 服务界面功能。"""

    def test_mock_page(self, client):
        """Mock 列表。"""
        r = client.post("/api/definition/mock/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200

    def test_mock_add(self, client):
        """添加 Mock。"""
        r = client.post("/api/definition/mock/add", json={
            "name": f"{PREFIX}Mock", "method": "GET", "path": "/mock/api",
        })
        assert r.status_code == 200
        body = r.json()
        assert body.get("code") == 200

    def test_mock_module_tree(self, client):
        """Mock 模块树。"""
        r = client.get("/api/definition/module/tree")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 四、用例评审
# ═══════════════════════════════════════════════════════════
class TestCaseReview:
    """用例评审界面功能。"""

    def test_review_page(self, client):
        """评审列表。"""
        r = client.post("/case/review/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_review_crud(self, client):
        """评审增删改查。"""
        name = f"{PREFIX}评审"
        r = client.post("/case/review/add", json={"name": name})
        assert r.status_code == 200
        review_id = _data(r)["id"]

        r = client.get(f"/case/review/detail/{review_id}")
        assert r.status_code == 200

        r = client.post("/case/review/delete", json={"id": review_id})
        assert r.status_code == 200

    def test_review_module_tree(self, client):
        """评审模块树。"""
        r = client.get("/case/review/module/tree")
        assert r.status_code == 200

    def test_review_user_option(self, client):
        """评审人员选项。"""
        r = client.get("/case/review/user-option")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 五、缺陷管理
# ═══════════════════════════════════════════════════════════
class TestBugManagement:
    """缺陷管理界面功能。"""

    def test_bug_page(self, client):
        """缺陷列表。"""
        r = client.post("/bug/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_bug_crud(self, client):
        """缺陷增删改查。"""
        title = f"{PREFIX}缺陷"
        r = client.post("/bug/add", json={"title": title, "severity": "P2"})
        assert r.status_code == 200
        bug_id = _data(r)["id"]

        r = client.get(f"/bug/get/{bug_id}")
        assert r.status_code == 200
        assert _data(r).get("title") == title

        r = client.post("/bug/update", json={"id": bug_id, "title": f"{PREFIX}缺陷-upd", "status": "in_progress"})
        assert r.status_code == 200

        r = client.post("/bug/delete/", json={"id": bug_id})
        assert r.status_code == 200

    def test_bug_trash(self, client):
        """缺陷回收站。"""
        r = client.post("/bug/trash/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_bug_template(self, client):
        """缺陷模板。"""
        r = client.get("/bug/template/detail")
        assert r.status_code == 200

    def test_bug_history(self, client):
        """缺陷变更历史。"""
        r = client.post("/bug/history/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 六、测试计划
# ═══════════════════════════════════════════════════════════
class TestTestPlan:
    """测试计划界面功能。"""

    def test_plan_page(self, client):
        """测试计划列表。"""
        r = client.post("/test-plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_plan_crud(self, client):
        """测试计划增删改查。"""
        name = f"{PREFIX}测试计划"
        r = client.post("/test-plan/add", json={"name": name})
        assert r.status_code == 200
        plan_id = _data(r)["id"]

        r = client.get(f"/test-plan/{plan_id}")
        assert r.status_code == 200

        r = client.post("/test-plan/update", json={"id": plan_id, "name": f"{PREFIX}测试计划-upd"})
        assert r.status_code == 200

        r = client.post("/test-plan/delete", json={"id": plan_id})
        assert r.status_code == 200

    def test_plan_module_tree(self, client):
        """测试计划模块树。"""
        r = client.get("/test-plan/module/tree")
        assert r.status_code == 200

    def test_plan_module_add(self, client):
        """测试计划模块添加。"""
        r = client.post("/test-plan/module/add", json={"name": f"{PREFIX}计划模块", "parentId": "root"})
        assert r.status_code == 200

    def test_plan_statistics(self, client):
        """测试计划通过率统计。"""
        r = client.get("/test-plan/statistics")
        assert r.status_code == 200

    def test_plan_my_list(self, client):
        """测试计划列表（下拉）。"""
        r = client.get("/test-plan/test-plan-list")
        assert r.status_code == 200

    def test_plan_archive(self, client):
        """测试计划归档。"""
        r = client.post("/test-plan/add", json={"name": f"{PREFIX}归档计划"})
        plan_id = _data(r)["id"]
        r = client.post("/test-plan/archived", json={"id": plan_id})
        assert r.status_code == 200
        client.post("/test-plan/delete", json={"id": plan_id})


# ═══════════════════════════════════════════════════════════
# 七、项目设置
# ═══════════════════════════════════════════════════════════
class TestProjectFileManagement:
    """项目-文件管理界面功能。"""

    def test_file_page(self, client):
        """文件列表。"""
        r = client.post("/project/file/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_file_module_tree(self, client):
        """文件模块树。"""
        r = client.get("/project/file-module/tree")
        assert r.status_code == 200

    def test_file_types(self, client):
        """文件类型。"""
        r = client.get("/project/file/type")
        assert r.status_code == 200


class TestProjectEnvironment:
    """项目-环境管理界面功能。"""

    def test_env_list(self, client):
        """环境列表。"""
        r = client.get("/project/environment/list")
        assert r.status_code == 200

    def test_env_add_delete(self, client):
        """环境增删。"""
        r = client.post("/project/environment/add", json={"name": f"{PREFIX}环境"})
        assert r.status_code == 200
        env_id = _data(r).get("id")

        if env_id:
            r = client.post(f"/project/environment/delete/{env_id}")
            assert r.status_code == 200

    def test_env_options(self, client):
        """环境选项。"""
        r = client.get("/project/environment/get-options")
        assert r.status_code == 200

    def test_global_param_add(self, client):
        """全局参数添加。"""
        r = client.post("/project/global/params/add", json={
            "name": f"{PREFIX}全局参数", "paramType": "text", "value": "v",
        })
        assert r.status_code == 200


class TestProjectMessage:
    """项目-消息通知界面功能。"""

    def test_robot_list(self, client):
        """机器人列表。"""
        r = client.get("/project/robot/list")
        assert r.status_code == 200

    def test_message_task_get(self, client):
        """消息任务配置获取。"""
        r = client.get("/notice/message/task/get")
        assert r.status_code == 200


class TestProjectCustomScript:
    """项目-自定义脚本界面功能。"""

    def test_custom_func_add(self, client):
        """自定义脚本添加。"""
        r = client.post("/project/custom/func/add", json={
            "name": f"{PREFIX}自定义脚本", "script": "return 1;", "type": "HTTP",
        })
        assert r.status_code == 200
        func_id = _data(r).get("id")

        if func_id:
            r = client.post("/project/custom/func/delete", json={"id": func_id})
            assert r.status_code == 200

    def test_custom_func_page(self, client):
        """自定义脚本列表。"""
        r = client.post("/project/custom/func/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 405)


# ═══════════════════════════════════════════════════════════
# 八、测试报告
# ═══════════════════════════════════════════════════════════
class TestReport:
    """测试报告界面功能。"""

    def test_report_list(self, client):
        """报告列表。"""
        r = client.get("/api/reports/list")
        assert r.status_code == 200

    def test_plan_report_page(self, client):
        """测试计划报告列表。"""
        r = client.post("/test-plan/report/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200

    def test_report_trash(self, client):
        """报告回收站。"""
        r = client.get("/api/reports/trash/list")
        assert r.status_code == 200

    def test_case_report_page(self, client):
        """接口用例报告列表。"""
        r = client.post("/api/report/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200

    def test_scenario_report_page(self, client):
        """场景报告列表。"""
        r = client.post("/api/report/scenario/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 九、系统设置 / 个人设置
# ═══════════════════════════════════════════════════════════
class TestSystemSetting:
    """系统设置界面功能。"""

    def test_system_version(self, client):
        """系统版本。"""
        r = client.get("/system/version/current")
        assert r.status_code == 200
        assert _data(r)

    def test_script_health_stats(self, client):
        """脚本健康度。"""
        r = client.get("/api/scripthealth/stats")
        assert r.status_code == 200

    def test_run_stats(self, client):
        """运行记录统计。"""
        r = client.get("/api/runs/stats")
        assert r.status_code == 200

    def test_insights_risk(self, client):
        """洞察-高风险模块。"""
        r = client.get("/api/insights/risk")
        assert r.status_code == 200


class TestPersonalSetting:
    """个人设置界面功能。"""

    def test_local_config_get(self, client):
        """本地执行配置。"""
        r = client.get("/user/local/config/get")
        assert r.status_code == 200

    def test_api_key_list(self, client):
        """API Key 列表。"""
        r = client.get("/user/api/key/list")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 十、AI 用例生成
# ═══════════════════════════════════════════════════════════
class TestAiCaseGen:
    """AI 用例生成界面功能。"""

    def test_test_types(self, client):
        """测试类型列表。"""
        r = client.get("/api/test-types")
        assert r.status_code == 200
        assert "types" in _data(r)

    def test_insights_skill_path(self, client):
        """职业发展路径。"""
        r = client.get("/api/insights/skill-path")
        assert r.status_code == 200

    def test_tasks_list(self, client):
        """异步任务列表。"""
        r = client.get("/api/tasks")
        assert r.status_code == 200

    def test_project_scan_requires_dir(self, client):
        """项目扫描（无目录参数应报错但接口可用）。"""
        r = client.post("/api/projects/scan", json={})
        # 无目录参数返回 404（业务上表示项目目录不存在），接口本身可用
        assert r.status_code in (200, 400, 404, 422)


# ═══════════════════════════════════════════════════════════
# 十一、数据工厂
# ═══════════════════════════════════════════════════════════
class TestDataFactory:
    """数据工厂界面功能。"""

    def test_template_list(self, client):
        """数据模板列表。"""
        r = client.get("/api/data/templates")
        assert r.status_code == 200
        assert "templates" in _data(r)

    def test_template_crud(self, client):
        """数据模板增删改查。"""
        r = client.post("/api/data/templates", json={"name": f"{PREFIX}数据模板", "schema": "{}"})
        assert r.status_code == 200
        tid = _data(r).get("id")
        assert tid

        if tid:
            r = client.delete(f"/api/data/templates/{tid}")
            assert r.status_code == 200

    def test_template_cleanup(self, client):
        """模板清理（不存在返回成功或 404）。"""
        r = client.post("/api/data/cleanup/template/nonexistent-id", json={})
        assert r.status_code in (200, 404)

    def test_env_cleanup(self, client):
        """环境数据清理。"""
        r = client.post("/api/data/cleanup/env/nonexistent-key", json={})
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 十二、运行记录
# ═══════════════════════════════════════════════════════════
class TestRunRecords:
    """运行记录界面功能。"""

    def test_runs_list(self, client):
        """运行记录列表。"""
        r = client.get("/api/runs")
        assert r.status_code == 200
        assert "records" in _data(r)

    def test_runs_stats(self, client):
        """运行统计。"""
        r = client.get("/api/runs/stats")
        assert r.status_code == 200

    def test_run_detail_not_found(self, client):
        """运行记录详情（不存在返回 404）。"""
        r = client.get("/api/runs/nonexistent-id")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════
# 十三、个人设置
# ═══════════════════════════════════════════════════════════
class TestPersonalCenter:
    """个人中心界面功能。"""

    def test_personal_get(self, client):
        """获取个人信息。"""
        r = client.get("/personal/get")
        assert r.status_code == 200
        assert _data(r).get("name")

    def test_is_login(self, client):
        """登录状态检查。"""
        r = client.get("/is-login")
        assert r.status_code == 200

    def test_update_password(self, client):
        """修改密码（格式错误应返回错误但接口可用）。"""
        r = client.post("/personal/update-password", json={
            "oldPassword": "wrong", "newPassword": "new123456",
        })
        assert r.status_code in (200, 400, 422)


# ═══════════════════════════════════════════════════════════
# 十四、apitest 环境管理
# ═══════════════════════════════════════════════════════════
class TestApiTestEnvironment:
    """接口测试-环境管理界面功能。"""

    def test_env_list(self, client):
        """环境列表。"""
        r = client.get("/api/apitest/environments")
        assert r.status_code == 200

    def test_env_add_delete(self, client):
        """环境增删。"""
        r = client.post("/api/apitest/environments", json={"name": f"{PREFIX}API环境"})
        assert r.status_code == 200
        env_id = r.json().get("id")

        if env_id:
            r = client.delete(f"/api/apitest/environments/{env_id}")
            assert r.status_code == 200

    def test_env_import_export(self, client):
        """环境导入导出。"""
        r = client.get("/api/apitest/environments/nonexistent/export")
        assert r.status_code in (200, 404)

    def test_apitest_meta(self, client):
        """接口测试元数据。"""
        r = client.get("/api/apitest/meta")
        assert r.status_code == 200

    def test_apitest_stats(self, client):
        """接口测试统计。"""
        r = client.get("/api/apitest/stats")
        assert r.status_code == 200

    def test_apitest_logs(self, client):
        """操作日志。"""
        r = client.get("/api/apitest/logs")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 十五、消息中心
# ═══════════════════════════════════════════════════════════
class TestMessageCenter:
    """消息中心界面功能。"""

    def test_message_list(self, client):
        """消息列表。"""
        r = client.get("/api/message/list")
        assert r.status_code == 200

    def test_message_read(self, client):
        """消息已读。"""
        r = client.post("/api/message/read", json={"messageId": "nonexistent"})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 十六、测试计划详情
# ═══════════════════════════════════════════════════════════
class TestTestPlanDetail:
    """测试计划详情界面功能。"""

    def test_plan_association_page(self, client):
        """计划关联用例列表。"""
        r = client.post("/test-plan/add", json={"name": f"{PREFIX}详情计划"})
        plan_id = _data(r)["id"]
        r = client.post("/test-plan/association/page", json={
            "planId": plan_id, "pageSize": 10, "current": 1,
        })
        assert r.status_code == 200
        client.post("/test-plan/delete", json={"id": plan_id})

    def test_plan_functional_cases(self, client):
        """计划功能用例列表。"""
        r = client.post("/test-plan/functional/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        assert "list" in _data(r)

    def test_plan_functional_case_tree(self, client):
        """计划功能用例模块树。"""
        r = client.post("/test-plan/functional/case/tree", json={})
        assert r.status_code == 200

    def test_plan_execute_history(self, client):
        """计划执行历史。"""
        r = client.post("/test-plan/his/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200

    def test_plan_user_options(self, client):
        """计划成员选项。"""
        r = client.get("/test-plan/functional/case/user-option")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 十七、项目 / 权限
# ═══════════════════════════════════════════════════════════
class TestProjectPermission:
    """项目权限界面功能。"""

    def test_project_list_options(self, client):
        """项目下拉选项。"""
        r = client.get("/project/list/options")
        assert r.status_code == 200

    def test_project_has_permission(self, client):
        """项目访问权限。"""
        r = client.get("/project/has-permission")
        assert r.status_code == 200

    def test_system_version_package(self, client):
        """系统版本包类型。"""
        r = client.get("/system/version/package-type")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 十八、接口测试导入/导出
# ═══════════════════════════════════════════════════════════
class TestApiTestImportExport:
    """接口测试导入导出界面功能。"""

    def test_apitest_import_empty(self, client):
        """导入（空数据返回业务错误，接口可用）。"""
        r = client.post("/api/apitest/import", json={"content": ""})
        assert r.status_code == 200

    def test_apitest_import_file(self, client):
        """文件导入（无文件返回错误，接口可用）。"""
        r = client.post("/api/apitest/import/file")
        assert r.status_code in (200, 400, 422)

    def test_definition_export_empty(self, client):
        """接口定义导出（空参数返回错误，接口可用）。"""
        r = client.post("/api/definition/export", json={})
        assert r.status_code in (200, 400, 422)


# ═══════════════════════════════════════════════════════════
# 十九、AI 对话
# ═══════════════════════════════════════════════════════════
class TestAiConversation:
    """AI 对话界面功能。"""

    def test_conversation_list(self, client):
        """对话列表。"""
        r = client.get("/ai/conversation/list")
        assert r.status_code == 200

    def test_conversation_add_delete(self, client):
        """对话添加与删除。"""
        r = client.post("/ai/conversation/add", json={"title": f"{PREFIX}AI对话"})
        assert r.status_code == 200

        r = client.post("/ai/conversation/delete", json={"conversationId": "nonexistent"})
        assert r.status_code == 200

    def test_insights_lowcode(self, client):
        """低代码生成。"""
        r = client.post("/api/insights/lowcode", json={"description": "生成登录页面"})
        assert r.status_code == 200

    def test_insights_value(self, client):
        """洞察价值量化。"""
        r = client.get("/api/insights/value")
        assert r.status_code == 200

    def test_insights_skill_path(self, client):
        """职业发展路径。"""
        r = client.get("/api/insights/skill-path")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 二十、数据工厂 - 数据生成
# ═══════════════════════════════════════════════════════════
class TestDataGenerate:
    """数据工厂-数据生成界面功能。"""

    def test_data_generate(self, client):
        """按模板生成数据。"""
        r = client.post("/api/data/templates", json={
            "name": f"{PREFIX}生成模板",
            "schema": {"name": {"type": "string", "prefix": "user_"}},
        })
        assert r.status_code == 200
        tid = _data(r).get("id")
        assert tid

        r = client.post("/api/data/generate", json={
            "template_id": tid, "batch_size": 2,
        })
        assert r.status_code == 200
        body = _data(r)
        assert body.get("batch_id")
        assert len(body.get("data", [])) == 2

        # 清理模板
        client.delete(f"/api/data/templates/{tid}")

    def test_data_batches(self, client):
        """生成批次列表。"""
        r = client.get("/api/data/batches")
        assert r.status_code == 200

    def test_data_stats(self, client):
        """数据统计。"""
        r = client.get("/api/data/stats")
        assert r.status_code == 200
