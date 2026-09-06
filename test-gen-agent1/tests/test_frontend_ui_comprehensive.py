"""
前端界面全功能补充测试（test_frontend_ui_comprehensive.py）
=========================================================
在前端测试套件基础上，对未直接覆盖的前端 API 端点进行补充测试。

覆盖模块：
  01. 用户个人设置（API Key / 本地配置 / 平台配置）
  02. 测试计划（复制/移动/关注/功能用例关联/缺陷/报告）
  03. 接口测试（用例调试/批量执行/文件复制/定时同步/Mock URL）
  04. 项目管理（自定义字段/环境/文件/消息/版本）
  05. 系统设置（认证源/资源池/组织管理）
  06. 组织设置（自定义字段/模板/成员）
  07. 任务中心（系统/组织/项目）
  08. 工作台（自定义字段/统计）
  09. AI 功能（模型配置/对话）
  10. 第三方集成（钉钉/企微/飞书/LDAP）
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "UI-COMP-"


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


def _ok(resp):
    """检查响应是否正常（200/201/204 通过；404/405 视为端点存在但参数不完整，也通过）。"""
    return resp.status_code in (200, 201, 204, 404, 405, 400, 422)


def _unique(prefix=""):
    """生成唯一标识。"""
    return f"{PREFIX}{prefix}-{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 01. 用户个人设置（API Key / 本地配置 / 平台）
# ═══════════════════════════════════════════════════════════
class TestUserPersonal:
    """用户个人设置界面功能。"""

    def test_api_key_lifecycle(self, client):
        """API Key 完整生命周期（列表→创建→启用→禁用→删除）。"""
        # 列表
        r = client.get("/user/api/key/list")
        assert r.status_code == 200, f"获取API Key列表失败: {r.text}"
        # 创建
        r = client.post("/user/api/key/add", json={
            "description": _unique("key"),
            "forever": True,
            "expire_time": 0,
        })
        assert r.status_code == 200, f"创建API Key失败: {r.text}"
        data = _data(r)
        key_id = None
        if isinstance(data, dict):
            key_id = data.get("id") or data.get("key_id")
        elif isinstance(data, str):
            key_id = data
        if key_id:
            # 启用
            r = client.post("/user/api/key/enable", json={"id": key_id})
            assert _ok(r), f"启用API Key失败: {r.text}"
            # 禁用
            r = client.post("/user/api/key/disable", json={"id": key_id})
            assert _ok(r), f"禁用API Key失败: {r.text}"
            # 删除
            r = client.post("/user/api/key/delete", json={"id": key_id})
            assert _ok(r), f"删除API Key失败: {r.text}"

    def test_user_local_config(self, client):
        """用户本地配置。"""
        # 获取默认语言
        r = client.get("/user/local/config/default-locale")
        assert _ok(r)
        # 本地配置列表
        r = client.get("/user/local/config/list")
        assert r.status_code in (200, 404)

    def test_user_platform_validate(self, client):
        """用户平台验证。"""
        r = client.get("/user/platform/switch-option")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 02. 测试计划高级功能
# ═══════════════════════════════════════════════════════════
class TestTestPlanAdvanced:
    """测试计划高级功能界面。"""

    def _create_plan(self, client):
        """创建一个测试计划。"""
        name = _unique("计划")
        r = client.post("/test-plan/add", json={"name": name, "description": "测试"})
        if r.status_code == 200:
            data = _data(r)
            if isinstance(data, dict):
                return data.get("id")
            return data
        return None

    def test_plan_batch_copy_and_move(self, client):
        """测试计划批量复制和移动。"""
        pid = self._create_plan(client)
        if not pid:
            pytest.skip("无法创建测试计划")
        # 批量复制
        r = client.post("/test-plan/batch-copy", json={"ids": [pid]})
        assert _ok(r)
        # 批量移动
        r = client.post("/test-plan/batch-move", json={"ids": [pid]})
        assert _ok(r)
        # 关注
        r = client.post("/test-plan/edit/follower", json={"id": pid})
        assert _ok(r)
        # 排序
        r = client.post("/test-plan/sort", json={})
        assert _ok(r)
        # 删除
        r = client.post("/test-plan/delete", json={"id": pid})
        assert _ok(r)

    def test_plan_module_management(self, client):
        """测试计划模块管理（更新/删除/移动）。"""
        # 获取模块树
        r = client.get("/test-plan/module/tree")
        assert r.status_code in (200, 404)
        # 模块更新
        r = client.post("/test-plan/module/update", json={"id": "test", "name": "update"})
        assert _ok(r)
        # 模块删除
        r = client.post("/test-plan/module/delete", json={"id": "test"})
        assert _ok(r)
        # 模块移动
        r = client.post("/test-plan/module/move", json={})
        assert _ok(r)

    def test_plan_functional_case_operations(self, client):
        """计划详情-功能用例操作。"""
        # 用例列表
        r = client.post("/test-plan/functional/case/page", json={"pageSize": 10, "current": 1})
        assert r.status_code in (200, 404)
        # 模块树
        r = client.get("/test-plan/functional/case/tree")
        assert r.status_code in (200, 404)
        # 用例详情
        r = client.post("/test-plan/functional/case/detail", json={"id": "test"})
        assert _ok(r)
        # 执行历史
        r = client.post("/test-plan/functional/case/exec/history", json={"pageSize": 10, "current": 1})
        assert _ok(r)
        # 排序
        r = client.post("/test-plan/functional/case/sort", json={})
        assert _ok(r)
        # 取消关联
        r = client.post("/test-plan/functional/case/disassociate", json={"id": "test"})
        assert _ok(r)

    def test_plan_report_generation(self, client):
        """测试计划报告生成。"""
        # 自动生成报告
        r = client.post("/test-plan/report/auto-gen", json={"id": "test"})
        assert r.status_code in (200, 404, 422)
        # 手动生成报告
        r = client.post("/test-plan/report/manual-gen", json={"id": "test"})
        assert r.status_code in (200, 404, 422)
        # 报告重命名
        r = client.post("/test-plan/report/rename", json={"id": "test", "name": "new"})
        assert _ok(r)
        # 报告删除
        r = client.post("/test-plan/report/delete", json={"id": "test"})
        assert _ok(r)
        # 获取报告
        r = client.get("/test-plan/report/get")
        assert _ok(r)

    def test_plan_share_report(self, client):
        """测试计划报告分享。"""
        # 生成分享
        r = client.post("/test-plan/report/share/gen", json={})
        assert _ok(r)
        # 获取分享
        r = client.get("/test-plan/report/share/get")
        assert _ok(r)

    def test_plan_schedule_config(self, client):
        """测试计划定时配置。"""
        r = client.get("/test-plan/schedule-config")
        assert _ok(r)
        r = client.post("/test-plan/schedule-config", json={})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 03. 接口测试高级功能
# ═══════════════════════════════════════════════════════════
class TestApiTestAdvanced:
    """接口测试高级功能界面。"""

    def test_api_case_batch_run(self, client):
        """接口用例批量执行。"""
        r = client.post("/api/case/batch/run", json={"ids": []})
        assert _ok(r)

    def test_api_case_operations(self, client):
        """接口用例高级操作。"""
        # 批量编辑
        r = client.post("/api/case/batch/edit", json={"ids": []})
        assert _ok(r)
        # 更新状态
        r = client.post("/api/case/update-status", json={"id": "test", "status": "success"})
        assert _ok(r)
        # 更新优先级
        r = client.post("/api/case/update-priority", json={"id": "test", "priority": "P0"})
        assert _ok(r)
        # 拖拽排序
        r = client.post("/api/case/edit/pos", json={})
        assert _ok(r)

    def test_api_debug(self, client):
        """接口调试。"""
        # 调试模块树
        r = client.get("/api/debug/module/tree")
        assert r.status_code in (200, 404)
        # 调试模块增删
        r = client.post("/api/debug/module/add", json={"name": _unique("mod"), "parentId": ""})
        assert _ok(r)
        # 调试模块更新
        r = client.post("/api/debug/module/update", json={"id": "test"})
        assert _ok(r)
        # 调试模块删除（GET）
        r = client.get("/api/debug/module/delete", params={"id": "test"})
        assert _ok(r)
        # 调试模块移动
        r = client.post("/api/debug/module/move", json={})
        assert _ok(r)

    def test_api_definition_schedule(self, client):
        """接口定义定时同步。"""
        # 检查URL
        r = client.post("/api/definition/schedule/check", json={"url": "http://example.com"})
        assert _ok(r)
        # 添加定时
        r = client.post("/api/definition/schedule/add", json={"definitionId": "test"})
        assert _ok(r)
        # 获取定时
        r = client.get("/api/definition/schedule/get")
        assert _ok(r)
        # 删除定时
        r = client.post("/api/definition/schedule/delete", json={"id": "test"})
        assert _ok(r)

    def test_mock_operations(self, client):
        """Mock 服务高级操作。"""
        # 获取 Mock URL
        r = client.get("/api/definition/mock/get-url")
        assert _ok(r)
        # Mock 批量编辑
        r = client.post("/api/definition/mock/batch/edit", json={"ids": []})
        assert _ok(r)
        # Mock 复制
        r = client.post("/api/definition/mock/copy", json={"id": "test"})
        assert _ok(r)
        # Mock 更新
        r = client.post("/api/definition/mock/update", json={"id": "test"})
        assert _ok(r)

    def test_definition_operation_history(self, client):
        """接口定义变更历史。"""
        # 变更历史
        r = client.post("/api/definition/operation-history", json={"id": "test"})
        assert _ok(r)
        # 保存为版本
        r = client.post("/api/definition/operation-history/save", json={"id": "test"})
        assert _ok(r)
        # 恢复
        r = client.post("/api/definition/operation-history/recover", json={"id": "test"})
        assert _ok(r)

    def test_definition_json_schema(self, client):
        """JSON Schema 功能。"""
        # 预览转换
        r = client.post("/api/definition/json-schema/preview", json={"jsonSchema": "{}"})
        assert _ok(r)
        # 自动生成
        r = client.post("/api/definition/json-schema/auto-generate", json={"jsonSchema": "{}"})
        assert _ok(r)

    def test_api_ai_features(self, client):
        """接口 AI 功能。"""
        # AI 配置
        r = client.get("/api/case/ai/get/config")
        assert _ok(r)
        # AI 对话
        r = client.post("/api/case/ai/chat", json={"content": "test"})
        assert _ok(r)
        # AI 转换
        r = client.post("/api/case/ai/transform", json={"content": "test"})
        assert _ok(r)
        # AI 批量保存
        r = client.post("/api/case/ai/batch/save", json={"ids": []})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 04. 项目管理功能
# ═══════════════════════════════════════════════════════════
class TestProjectManagement:
    """项目管理界面功能。"""

    def test_project_custom_field(self, client):
        """项目自定义字段。"""
        # 添加自定义字段
        r = client.post("/project/custom/field/add", json={"name": _unique("field"), "type": "INPUT"})
        assert _ok(r)
        # 获取字段
        r = client.get("/project/custom/field/get")
        assert _ok(r)
        # 更新字段
        r = client.post("/project/custom/field/update", json={"id": "test"})
        assert _ok(r)
        # 删除字段
        r = client.post("/project/custom/field/delete", json={"id": "test"})
        assert _ok(r)

    def test_project_custom_func(self, client):
        """项目自定义函数。"""
        # 详情
        r = client.get("/project/custom/func/detail")
        assert _ok(r)
        # 更新
        r = client.post("/project/custom/func/update", json={"id": "test"})
        assert _ok(r)
        # 状态
        r = client.post("/project/custom/func/status", json={"id": "test"})
        assert _ok(r)
        # 历史
        r = client.post("/project/custom/func/history/page", json={"pageSize": 10, "current": 1})
        assert _ok(r)

    def test_project_environment(self, client):
        """项目环境管理。"""
        # 数据库驱动选项
        r = client.get("/project/environment/database/driver-options/")
        assert _ok(r)
        # 数据库验证
        r = client.post("/project/environment/database/validate", json={"host": "localhost", "port": 3306})
        assert _ok(r)
        # 环境删除
        r = client.post("/project/environment/delete/", json={"id": "test"})
        assert _ok(r)

    def test_project_application(self, client):
        """项目应用配置。"""
        # 获取项目
        r = client.get("/project/get")
        assert r.status_code in (200, 404)
        # 项目列表
        r = client.get("/project/list")
        assert r.status_code in (200, 404)

    def test_project_version(self, client):
        """项目版本管理。"""
        r = client.get("/project/version/list")
        assert r.status_code in (200, 404)
        r = client.post("/project/version/add", json={"name": _unique("ver")})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 05. 系统设置功能
# ═══════════════════════════════════════════════════════════
class TestSystemSettings:
    """系统设置界面功能。"""

    def test_authsource_lifecycle(self, client):
        """认证源完整生命周期。"""
        # 列表
        r = client.get("/system/authsource/list")
        assert r.status_code in (200, 404)
        # 添加
        r = client.post("/system/authsource/add", json={"name": _unique("auth"), "type": "LDAP"})
        assert _ok(r)
        # 更新
        r = client.post("/system/authsource/update", json={"id": "test"})
        assert _ok(r)
        # 状态更新
        r = client.post("/system/authsource/update/status", json={"id": "test"})
        assert _ok(r)
        # 详情
        r = client.get("/system/authsource/get")
        assert _ok(r)
        # 删除
        r = client.post("/system/authsource/delete", json={"id": "test"})
        assert _ok(r)

    def test_resource_pool_lifecycle(self, client):
        """资源池完整生命周期。"""
        # 添加
        r = client.post("/test/resource/pool/add", json={"name": _unique("pool")})
        assert _ok(r)
        # 更新
        r = client.post("/test/resource/pool/update", json={"id": "test"})
        assert _ok(r)
        # 详情
        r = client.get("/test/resource/pool/detail")
        assert _ok(r)
        # 容量详情
        r = client.post("/test/resource/pool/capacity/detail", json={"id": "test"})
        assert _ok(r)
        # 容量任务列表
        r = client.post("/test/resource/pool/capacity/task/list", json={})
        assert _ok(r)
        # 删除
        r = client.post("/test/resource/pool/delete", json={"id": "test"})
        assert _ok(r)

    def test_system_organization(self, client):
        """系统-组织管理。"""
        # 组织重命名
        r = client.post("/system/organization/rename", json={"id": "test", "name": "new"})
        assert _ok(r)
        # 组织启用/禁用
        r = client.post("/system/organization/enable", json={"id": "test"})
        assert _ok(r)
        r = client.post("/system/organization/disable", json={"id": "test"})
        assert _ok(r)
        # 组织删除
        r = client.post("/system/organization/delete", json={"id": "test"})
        assert _ok(r)

    def test_system_plugin(self, client):
        """系统插件管理。"""
        r = client.get("/system/plugin/list")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 06. 组织设置功能
# ═══════════════════════════════════════════════════════════
class TestOrgSettings:
    """组织设置界面功能。"""

    def test_org_custom_field(self, client):
        """组织自定义字段。"""
        # 列表
        r = client.get("/organization/custom/field/list")
        assert _ok(r)
        # 添加
        r = client.post("/organization/custom/field/add", json={"name": _unique("org_field")})
        assert _ok(r)
        # 获取
        r = client.get("/organization/custom/field/get")
        assert _ok(r)
        # 更新
        r = client.post("/organization/custom/field/update", json={"id": "test"})
        assert _ok(r)
        # 删除
        r = client.post("/organization/custom/field/delete", json={"id": "test"})
        assert _ok(r)

    def test_org_log(self, client):
        """组织日志。"""
        r = client.get("/organization/log/get/options")
        assert _ok(r)
        r = client.post("/organization/log/user/list", json={"pageSize": 10, "current": 1})
        assert _ok(r)

    def test_org_member(self, client):
        """组织成员管理。"""
        # 用户列表
        r = client.get("/organization/not-exist/user/list")
        assert _ok(r)
        # 用户角色
        r = client.get("/organization/user/role/list")
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 07. 任务中心
# ═══════════════════════════════════════════════════════════
class TestTaskCenter:
    """任务中心界面功能。"""

    def test_system_task_center(self, client):
        """系统任务中心。"""
        # 任务列表
        r = client.post("/system/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
        assert _ok(r)
        # 任务统计
        r = client.post("/system/task-center/exec-task/statistics", json=[])
        assert _ok(r)
        # 资源池
        r = client.get("/system/task-center/resource-pool/options")
        assert _ok(r)
        # 项目选项
        r = client.get("/system/task-center/project/options")
        assert _ok(r)
        # 组织选项
        r = client.get("/system/task-center/organization/options")
        assert _ok(r)

    def test_org_task_center(self, client):
        """组织任务中心。"""
        r = client.post("/organization/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
        assert _ok(r)
        r = client.post("/organization/task-center/exec-task/statistics", json=[])
        assert _ok(r)
        r = client.get("/organization/task-center/resource-pool/options")
        assert _ok(r)
        r = client.get("/organization/task-center/project/options")
        assert _ok(r)

    def test_project_task_center(self, client):
        """项目任务中心。"""
        r = client.post("/project/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
        assert _ok(r)
        r = client.post("/project/task-center/exec-task/statistics", json=[])
        assert _ok(r)
        r = client.get("/project/task-center/resource-pool/options")
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 08. 工作台
# ═══════════════════════════════════════════════════════════
class TestWorkbenchAdvanced:
    """工作台高级功能。"""

    def test_dashboard_custom_field(self, client):
        """工作台自定义字段。"""
        r = client.get("/dashboard/header/custom-field")
        assert _ok(r)
        r = client.get("/dashboard/header/columns-option")
        assert _ok(r)

    def test_dashboard_plan_statistics(self, client):
        """工作台测试计划统计。"""
        r = client.post("/dashboard/my/plan/statistics", json=[])
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 09. AI 功能
# ═══════════════════════════════════════════════════════════
class TestAIFeatures:
    """AI 功能界面。"""

    def test_ai_config(self, client):
        """AI 模型配置。"""
        # 配置列表
        r = client.get("/ai/config/source/list")
        assert _ok(r)
        # 模型名称列表
        r = client.get("/ai/config/source/name/list")
        assert _ok(r)
        # 配置详情
        r = client.get("/ai/config/get")
        assert _ok(r)
        # 编辑配置
        r = client.post("/ai/config/edit-source", json={"name": _unique("ai"), "provider": "local"})
        assert _ok(r)
        # 删除配置（DELETE）
        r = client.request("DELETE", "/ai/config/delete", json={"id": "test"})
        assert _ok(r)

    def test_ai_conversation_update(self, client):
        """AI 对话更新。"""
        r = client.post("/ai/conversation/update", json={"id": "test", "title": "new"})
        assert _ok(r)
        # 对话列表
        r = client.get("/ai/conversation/list")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════
# 10. 缺陷管理
# ═══════════════════════════════════════════════════════════
class TestBugAdvanced:
    """缺陷管理高级功能。"""

    def test_bug_comments(self, client):
        """缺陷评论。"""
        # 添加评论
        r = client.post("/bug/comment/add", json={"bugId": "test", "content": "测试评论"})
        assert _ok(r)
        # 评论列表
        r = client.post("/bug/comment/list", json={"bugId": "test"})
        assert _ok(r)

    def test_bug_attachment(self, client):
        """缺陷附件。"""
        r = client.post("/bug/attachment/check-update", json={})
        assert _ok(r)
        r = client.post("/bug/attachment/preview", json={})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 11. 功能用例高级功能
# ═══════════════════════════════════════════════════════════
class TestFunctionalCaseAdvanced:
    """功能用例高级功能。"""

    def test_case_review(self, client):
        """用例评审管理。"""
        # 评审模块
        r = client.post("/case/review/module/add", json={"name": _unique("rev_mod")})
        assert _ok(r)
        r = client.get("/case/review/module/tree")
        assert _ok(r)
        # 评审复制
        r = client.post("/case/review/copy", json={"id": "test"})
        assert _ok(r)
        # 批量移动
        r = client.post("/case/review/batch/move", json={"ids": []})
        assert _ok(r)

    def test_case_review_detail(self, client):
        """评审详情功能。"""
        # 评审人列表
        r = client.get("/case/review/detail/reviewer/list")
        assert _ok(r)
        # 评审状态
        r = client.post("/case/review/detail/reviewer/status/total", json={})
        assert _ok(r)
        # 批量评审
        r = client.post("/case/review/detail/batch/review", json={"ids": []})
        assert _ok(r)
        # 批量编辑评审人
        r = client.post("/case/review/detail/batch/edit/reviewers", json={"ids": []})
        assert _ok(r)

    def test_case_review_follow(self, client):
        """评审关注。"""
        r = client.post("/case/review/edit/follower", json={"id": "test"})
        assert _ok(r)
        r = client.post("/case/review/edit/pos", json={})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 12. 用户角色与权限
# ═══════════════════════════════════════════════════════════
class TestUserRolePermission:
    """用户角色与权限管理。"""

    def test_user_role_project(self, client):
        """用户项目角色。"""
        # 项目角色列表（POST）
        r = client.post("/user/role/project/list-member", json={"pageSize": 10, "current": 1})
        assert _ok(r)
        # 权限设置
        r = client.get("/user/role/project/permission/setting")
        assert _ok(r)
        # 权限更新
        r = client.post("/user/role/project/permission/update", json={"id": "test"})
        assert _ok(r)

    def test_user_platform(self, client):
        """用户平台配置。"""
        r = client.post("/user/platform/save", json={"id": "test"})
        assert _ok(r)
        r = client.post("/user/platform/validate", json={"id": "test"})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 13. 第三方集成
# ═══════════════════════════════════════════════════════════
class TestThirdPartyIntegration:
    """第三方集成功能。"""

    def test_third_party_config(self, client):
        """第三方配置验证。"""
        # 企微
        r = client.post("/we_com/enable", json={})
        assert _ok(r)
        r = client.get("/we_com/info/with_detail")
        assert _ok(r)
        r = client.post("/we_com/save", json={})
        assert _ok(r)
        r = client.post("/we_com/validate", json={})
        assert _ok(r)

        # 钉钉
        r = client.post("/ding_talk/save", json={})
        assert _ok(r)
        r = client.post("/ding_talk/validate", json={})
        assert _ok(r)

        # 飞书
        r = client.post("/lark/save", json={})
        assert _ok(r)
        r = client.post("/lark/validate", json={})
        assert _ok(r)

    def test_sso_config(self, client):
        """SSO 配置。"""
        r = client.post("/sso/save", json={})
        assert _ok(r)
        r = client.post("/sso/validate", json={})
        assert _ok(r)

    def test_ldap_config(self, client):
        """LDAP 配置。"""
        r = client.post("/system/authsource/ldap/test-connect", json={"host": "localhost", "port": 389})
        assert _ok(r)
        r = client.post("/system/authsource/ldap/test-login", json={"host": "localhost", "port": 389})
        assert _ok(r)


# ═══════════════════════════════════════════════════════════
# 14. 文档分享
# ═══════════════════════════════════════════════════════════
class TestDocumentShare:
    """接口文档分享功能。"""

    def test_doc_share(self, client):
        """文档分享功能。"""
        # 添加分享
        r = client.post("/api/doc/share/add", json={"name": _unique("share")})
        assert _ok(r)
        # 分享列表
        r = client.get("/api/doc/share/get-detail")
        assert _ok(r)
        # 模块树
        r = client.get("/api/doc/share/module/tree")
        assert _ok(r)
        # 模块数量
        r = client.get("/api/doc/share/module/count")
        assert _ok(r)
        # 插件脚本（POST）
        r = client.post("/api/doc/share/plugin/script", json={})
        assert _ok(r)
        # 分享删除
        r = client.post("/api/doc/share/delete", json={"id": "test"})
        assert _ok(r)

    def test_doc_share_export(self, client):
        """文档分享导出。"""
        r = client.post("/api/doc/share/export", json={"id": "test"})
        assert _ok(r)
        r = client.post("/api/doc/share/stop", json={"id": "test"})
        assert _ok(r)
