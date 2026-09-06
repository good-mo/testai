"""测试计划模块单元测试。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    c = TestClient(app)
    # 登录获取认证令牌
    r = c.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code == 200:
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
    return c


class TestTestPlan:
    """测试计划 CRUD 测试。"""

    def test_create_plan(self, client):
        """创建测试计划。"""
        r = client.post("/test-plan/add", json={
            "name": "单元测试计划",
            "description": "计划描述",
            "priority": "P1",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "单元测试计划"
        assert data["data"]["priority"] == "P1"

    def test_plan_page(self, client):
        """测试计划分页。"""
        # 先创建
        client.post("/test-plan/add", json={"name": "分页测试计划"})
        r = client.post("/test-plan/page", json={"pageSize": 10, "current": 1})
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["total"] >= 1
        assert len(data["data"]["list"]) >= 1

    def test_plan_detail(self, client):
        """获取计划详情。"""
        r = client.post("/test-plan/add", json={"name": "详情测试计划"})
        plan_id = r.json()["data"]["id"]
        r = client.get(f"/test-plan/{plan_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["id"] == plan_id

    def test_plan_update(self, client):
        """更新测试计划。"""
        r = client.post("/test-plan/add", json={"name": "更新测试计划"})
        plan_id = r.json()["data"]["id"]
        r = client.post("/test-plan/update", json={"id": plan_id, "name": "更新后的计划", "status": "running"})
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "更新后的计划"

    def test_plan_delete(self, client):
        """删除测试计划。"""
        r = client.post("/test-plan/add", json={"name": "删除测试计划"})
        plan_id = r.json()["data"]["id"]
        r = client.post("/test-plan/delete", json={"id": plan_id})
        assert r.status_code == 200
        assert r.json()["code"] == 200

    def test_plan_module_tree(self, client):
        """获取模块树。"""
        r = client.get("/test-plan/module/tree")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert len(data["data"]) >= 1

    def test_plan_module_add(self, client):
        """添加模块。"""
        r = client.post("/test-plan/module/add", json={"name": "回归测试"})
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "回归测试"

    def test_plan_module_tree_hierarchy(self, client):
        """模块树按 parent_id 构建层级，子模块正确挂在父模块下。"""
        # 创建父模块
        r = client.post("/test-plan/module/add", json={"name": "层级父模块", "parentId": "root"})
        assert r.json()["code"] == 200
        parent_id = r.json()["data"]["id"]
        # 创建子模块
        r = client.post("/test-plan/module/add", json={"name": "层级子模块", "parentId": parent_id})
        assert r.json()["code"] == 200
        child_id = r.json()["data"]["id"]
        # 模块树应体现层级
        r = client.get("/test-plan/module/tree/default-org")
        assert r.status_code == 200
        root = r.json()["data"][0]
        assert root["id"] == "root"
        # 查找父模块节点，确认其 children 包含子模块
        parent_node = next((n for n in root["children"] if n["id"] == parent_id), None)
        assert parent_node is not None, "父模块节点应在根节点下"
        child_ids = [c["id"] for c in parent_node["children"]]
        assert child_id in child_ids, "子模块应挂在父模块下"

    def test_plan_module_move_reparents(self, client):
        """模块移动（POST /test-plan/module/move）必须真实重挂父模块，而非假成功。

        原为空壳路由（return ok(None)）。本用例做行为级断言：移动后查模块树，
        子模块应出现在新父模块的 children 下。
        """
        # 建父模块与待移动子模块
        r = client.post("/test-plan/module/add", json={"name": "移动目标父模块", "parentId": "root"})
        assert r.json()["code"] == 200
        parent_id = r.json()["data"]["id"]
        r = client.post("/test-plan/module/add", json={"name": "待移动模块", "parentId": "root"})
        assert r.json()["code"] == 200
        child_id = r.json()["data"]["id"]

        # 移动：把 child 挂到 parent 下（drop_position=0 成为子级）
        r = client.post("/test-plan/module/move", json={
            "dragNodeId": child_id,
            "dropNodeId": parent_id,
            "dropPosition": 0,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["parentId"] == parent_id

        # 行为级校验：模块树中 child 应挂在 parent 的 children 下
        r = client.get("/test-plan/module/tree/default-org")
        root = r.json()["data"][0]
        parent_node = next((n for n in root["children"] if n["id"] == parent_id), None)
        assert parent_node is not None, "目标父模块应存在于根下"
        child_ids = [c["id"] for c in parent_node["children"]]
        assert child_id in child_ids, "移动后子模块应真实挂到目标父模块下"

    def test_plan_module_count_includes_all(self, client):
        """模块计数应包含所有模块，且含 root 计数。"""
        client.post("/test-plan/module/add", json={"name": "计数模块", "parentId": "root"})
        r = client.post("/test-plan/module/count", json={"projectId": "default-org"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert "all" in data
        assert "root" in data

    def test_plan_association(self, client):
        """关联用例。"""
        r = client.post("/test-plan/add", json={"name": "关联测试计划"})
        plan_id = r.json()["data"]["id"]
        r = client.post("/test-plan/association/add", json={
            "planId": plan_id,
            "caseIds": ["case-1", "case-2"],
            "caseType": "functional",
        })
        assert r.status_code == 200
        assert r.json()["code"] == 200

        r = client.post("/test-plan/association/page", json={"planId": plan_id})
        assert r.status_code == 200
        data = r.json()
        assert data["data"]["total"] == 2

    def test_plan_statistics(self, client):
        """获取计划统计。"""
        r = client.post("/test-plan/add", json={"name": "统计测试计划"})
        plan_id = r.json()["data"]["id"]
        r = client.get(f"/test-plan/statistics/{plan_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert "total" in data["data"]
        assert "passRate" in data["data"]

    def test_plan_schedule_config_persist(self, client):
        """配置定时任务真实持久化并可回读。"""
        r = client.post("/test-plan/add", json={"name": "定时任务测试计划"})
        plan_id = r.json()["data"]["id"]
        # 单条配置
        r = client.post("/test-plan/schedule-config", json={
            "resourceId": plan_id,
            "cron": "0 9 * * *",
            "enable": True,
            "runConfig": {"runMode": "SERIAL"},
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["resourceId"] == plan_id
        assert data["cron"] == "0 9 * * *"
        # 通过统计接口回读 scheduleConfig
        r = client.post("/test-plan/statistics", json=[plan_id])
        assert r.status_code == 200
        items = r.json()["data"]
        sc = items[0]["scheduleConfig"]
        assert sc and sc["cron"] == "0 9 * * *"
        assert sc["enable"] is True
        # 删除后不再有 scheduleConfig
        r = client.get(f"/test-plan/schedule-config-delete/{plan_id}")
        assert r.status_code == 200
        r = client.post("/test-plan/statistics", json=[plan_id])
        assert r.json()["data"][0]["scheduleConfig"] is None

    def test_plan_batch_schedule_config(self, client):
        """批量配置定时任务。"""
        r = client.post("/test-plan/add", json={"name": "批量定时A"})
        pid_a = r.json()["data"]["id"]
        r = client.post("/test-plan/add", json={"name": "批量定时B"})
        pid_b = r.json()["data"]["id"]
        r = client.post("/test-plan/batch-schedule-config", json={
            "selectIds": [pid_a, pid_b],
            "cron": "*/10 * * * *",
            "enable": True,
            "runConfig": {"runMode": "PARALLEL"},
            "projectId": "default-org",
        })
        assert r.status_code == 200
        r = client.post("/test-plan/statistics", json=[pid_a, pid_b])
        items = r.json()["data"]
        for it in items:
            assert it["scheduleConfig"]["cron"] == "*/10 * * * *"

    def test_plan_mind_data(self, client):
        """获取测试规划脑图数据（支持 restful 路径参数，修复 404）。"""
        # 前端以 restful 风格将 planId 拼到 URL 路径，形如 /test-plan/mind/data/{planId}
        r = client.get("/test-plan/mind/data/cc540578-a50a-4611-acfb-fa09ed5fb22f")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

        # 兼容 query 参数方式
        r2 = client.get("/test-plan/mind/data", params={"testPlanId": "abc"})
        assert r2.status_code == 200
        assert r2.json()["code"] == 200

    def test_plan_update_persists_extra_fields(self, client):
        """更新测试计划时应持久化前端提交的扩展字段（tags/通过阈值/功能开关/起止时间）。"""
        r = client.post("/test-plan/add", json={
            "name": "扩展字段计划",
            "moduleId": "root",
            "plannedStartTime": 1000,
            "plannedEndTime": 2000,
            "tags": ["冒烟"],
            "passThreshold": 90,
            "testPlanning": True,
            "automaticStatusUpdate": True,
            "repeatCase": True,
        })
        assert r.json()["code"] == 200
        plan_id = r.json()["data"]["id"]

        r = client.post("/test-plan/update", json={
            "id": plan_id,
            "name": "扩展字段计划-改",
            "moduleId": "root",
            "plannedStartTime": 3000,
            "plannedEndTime": 4000,
            "tags": ["回归", "P0"],
            "passThreshold": 80,
            "testPlanning": False,
            "automaticStatusUpdate": True,
            "repeatCase": False,
        })
        assert r.json()["code"] == 200
        data = r.json()["data"]
        assert data["name"] == "扩展字段计划-改"
        assert data["plannedStartTime"] == 3000000
        assert data["plannedEndTime"] == 4000000
        assert data["tags"] == ["回归", "P0"]
        assert data["passThreshold"] == 80
        assert data["testPlanning"] is False
        assert data["automaticStatusUpdate"] is True
        assert data["repeatCase"] is False

        # 详情回读应保持一致，避免刷新后丢字段
        r = client.get(f"/test-plan/{plan_id}")
        data = r.json()["data"]
        assert data["tags"] == ["回归", "P0"]
        assert data["passThreshold"] == 80
        assert data["plannedStartTime"] == 3000000
        assert data["testPlanning"] is False
        assert data["automaticStatusUpdate"] is True
        assert data["repeatCase"] is False


class TestReportPage:
    """测试计划报告分页接口测试。"""

    def test_report_page_pagination(self, client):
        """报告列表 SQL 级分页：不同页返回不同数据且总数正确。"""
        # 创建一个测试计划
        r = client.post("/test-plan/add", json={"name": "报告分页测试计划"})
        assert r.json()["code"] == 200

        # 请求第 1 页
        r = client.post("/test-plan/report/page", json={"pageSize": 5, "current": 1})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["current"] == 1
        assert data["pageSize"] == 5
        assert data["total"] >= 1
        assert len(data["list"]) <= 5

        # 请求第 2 页
        r2 = client.post("/test-plan/report/page", json={"pageSize": 5, "current": 2})
        data2 = r2.json()["data"]
        assert data2["current"] == 2
        assert data2["total"] == data["total"]

        # 各页不应有重复记录
        page1_ids = {item["id"] for item in data["list"]}
        page2_ids = {item["id"] for item in data2["list"]}
        assert page1_ids.isdisjoint(page2_ids)

        # 报告字段完整性
        if data["list"]:
            item = data["list"][0]
            for key in ["id", "name", "planName", "integrated", "passRate", "createTime"]:
                assert key in item, f"报告列表缺少字段 {key}"

    def test_report_page_filter_independent(self, client):
        """独立报告（integrated=[False]）应正常返回。"""
        r = client.post("/test-plan/report/page", json={
            "pageSize": 10, "current": 1,
            "filter": {"integrated": [False]},
        })
        assert r.status_code == 200
        data = r.json()["data"]
        for item in data["list"]:
            assert item["integrated"] is False

    def test_report_page_filter_integrated_empty(self, client):
        """集成报告（integrated=[True]）当前无数据时返回空。"""
        r = client.post("/test-plan/report/page", json={
            "pageSize": 10, "current": 1,
            "filter": {"integrated": [True]},
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 0
        assert data["list"] == []

    def test_report_page_project_filter(self, client):
        """按项目过滤后报告列表正确。"""
        # 用不存在的项目ID过滤
        r = client.post("/test-plan/report/page", json={
            "pageSize": 10, "current": 1, "projectId": "nonexistent-project-xyz",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 0
        assert data["list"] == []

        # 空 projectId 不限制
        r = client.post("/test-plan/report/page", json={
            "pageSize": 10, "current": 1, "projectId": "",
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] >= 1


class TestDashboard:
    """工作台测试。"""

    def test_dashboard_home(self, client):
        """工作台首页。"""
        r = client.get("/dashboard/home")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert "caseCount" in data["data"]
        assert "bugCount" in data["data"]

    def test_dashboard_overview(self, client):
        """工作台总览。"""
        r = client.get("/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert "caseStatus" in data["data"]
        assert "defectSeverity" in data["data"]


class TestSystemSettings:
    """系统设置测试。"""

    def test_user_group_list(self, client):
        """用户组列表。"""
        r = client.get("/system/user-group/list")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert len(data["data"]) >= 2

    def test_organization_list(self, client):
        """组织列表。"""
        r = client.get("/system/organization/list")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert len(data["data"]) >= 1

    def test_organization_add(self, client):
        """添加组织。"""
        r = client.post("/system/organization/add", json={"name": "测试组织"})
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "测试组织"
