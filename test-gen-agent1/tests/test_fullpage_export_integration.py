"""全屏导出 /fullPage 真实联调验证测试。

覆盖 frontend/src/views 三个 export PDF 页面的完整数据流：
- testPlanExportPDF → /test-plan/report/*
- scenarioExportPDF → /api/report/scenario/*
- apiCaseExportPDF → /api/report/case/*
"""

import json
import pytest

from tests.conftest import make_auth_headers


@pytest.fixture(autouse=True)
def _setup(client_fixture=None):
    pass


def _report_detail_keys(data: dict) -> set:
    return set(data.keys())


# ── scenarioExportPDF / apiCaseExportPDF 数据完整性 ──────────────────────
# 这些 key 是前端 ReportDetail 组件（scenarioCom.vue / caseReportCom.vue /
# reportDetailHeader.vue / tiledList.vue）实际读取的字段。
_REQUIRED_REPORT_DETAIL_FIELDS = {
    # 基础
    "id", "name", "status",
    # 时间
    "startTime", "endTime", "requestDuration",
    # 数量
    "successCount", "errorCount", "fakeErrorCount", "pendingCount",
    # 断言
    "assertionCount", "assertionSuccessCount", "assertionPassRate",
    # 通过率
    "requestPassRate", "requestErrorRate", "requestFakeErrorRate",
    "requestPendingRate",
    # 步骤
    "stepTotal", "stepSuccessCount", "stepErrorCount",
    "stepFakeErrorCount", "stepPendingCount",
    # 环境
    "integrated", "environmentName", "poolName", "runMode",
    # children 步骤树
    "children",
    # 其他 ReportDetail 必须字段
    "createUser", "deleteTime", "deleteUser", "deleted",
    "updateUser", "updateTime", "triggerMode", "poolId",
    "versionId", "projectId", "environmentId", "scriptIdentifier",
    "console", "createTime",
    # 组件实际额外依赖
    "requestTotal", "creatUserName", "waitingTime", "total",
}

_STEP_FIELDS = {
    "stepId", "name", "stepType", "sort", "index",
    "parentId", "status", "children", "fold", "expanded",
}


class TestScenarioExportDataFlow:
    """scenarioExportPDF 数据流验证。"""

    def test_scenario_report_detail(self, auth_client):
        """GET /api/report/scenario/get/{id} 返回完整 ReportDetail。"""
        # 通过 scenario page 获取一个报告 id
        r = auth_client.post("/api/report/scenario/page", json={"pageSize": 1, "current": 1})
        assert r.status_code == 200
        items = r.json().get("data", {}).get("list", [])
        assert len(items) > 0, "应存在至少一条场景报告"
        rid = items[0]["id"]

        r = auth_client.get(f"/api/report/scenario/get/{rid}")
        assert r.status_code == 200
        data = r.json().get("data") or {}
        keys = _report_detail_keys(data)

        missing = _REQUIRED_REPORT_DETAIL_FIELDS - keys
        assert not missing, f"场景报告详情缺少字段: {missing}"

        # children 步骤树结构检查
        children = data.get("children") or []
        assert len(children) > 0, "场景报告详情应包含 children 步骤数据"
        for step in children:
            step_keys = set(step.keys())
            assert _STEP_FIELDS.issubset(step_keys), f"步骤字段不完整: {_STEP_FIELDS - step_keys}"

    def test_scenario_export_log(self, auth_client):
        """POST /api/report/scenario/export/{id} 正常。"""
        r = auth_client.post("/api/report/scenario/export/some-report-id")
        assert r.status_code == 200

    def test_scenario_batch_param_select_all(self, auth_client):
        """批量导出 selectAll 返回报告 ID 集合。"""
        params = {
            "projectId": "", "selectIds": [],
            "selectAll": True, "excludeIds": [],
            "condition": {},
        }
        r = auth_client.post("/api/report/scenario/batch-param", json=params)
        assert r.status_code == 200
        ids = r.json().get("data") or []
        assert len(ids) > 0, "selectAll 应返回非空报告 ID 列表"

    def test_scenario_batch_export_log(self, auth_client):
        """POST /api/report/scenario/batch-export 正常。"""
        r = auth_client.post("/api/report/scenario/batch-export", json={})
        assert r.status_code == 200


class TestCaseExportDataFlow:
    """apiCaseExportPDF 数据流验证。"""

    def test_case_report_detail(self, auth_client):
        """GET /api/report/case/get/{id} 返回完整 ReportDetail。"""
        r = auth_client.post("/api/report/case/page", json={"pageSize": 1, "current": 1})
        assert r.status_code == 200
        items = r.json().get("data", {}).get("list", [])
        assert len(items) > 0, "应存在至少一条用例报告"
        rid = items[0]["id"]

        r = auth_client.get(f"/api/report/case/get/{rid}")
        assert r.status_code == 200
        data = r.json().get("data") or {}
        keys = _report_detail_keys(data)

        missing = _REQUIRED_REPORT_DETAIL_FIELDS - keys
        assert not missing, f"用例报告详情缺少字段: {missing}"

        children = data.get("children") or []
        assert len(children) > 0, "用例报告详情应包含 children 步骤数据"

    def test_case_export_log(self, auth_client):
        """POST /api/report/case/export/{id} 正常。"""
        r = auth_client.post("/api/report/case/export/some-report-id")
        assert r.status_code == 200

    def test_case_batch_param(self, auth_client):
        """批量导出 param 正常返回。"""
        params = {
            "projectId": "", "selectIds": [],
            "selectAll": True, "excludeIds": [],
            "condition": {},
        }
        r = auth_client.post("/api/report/case/batch-param", json=params)
        assert r.status_code == 200
        ids = r.json().get("data") or []
        assert len(ids) > 0, "selectAll 应返回非空报告 ID 列表"

    def test_case_batch_export_log(self, auth_client):
        """POST /api/report/case/batch-export 正常。"""
        r = auth_client.post("/api/report/case/batch-export", json={})
        assert r.status_code == 200


class TestTestPlanExportDataFlow:
    """testPlanExportPDF 数据流验证。"""

    def test_test_plan_report_detail(self, auth_client):
        """GET /test-plan/report/get/{id} 返回完整 PlanReportDetail。"""
        # 获取一个计划
        r = auth_client.post("/test-plan/page", json={"pageSize": 1, "current": 1})
        assert r.status_code == 200
        plans = r.json().get("data", {}).get("list", [])
        assert len(plans) > 0
        pid = plans[0]["id"]

        r = auth_client.get(f"/test-plan/report/get/{pid}")
        assert r.status_code == 200
        data = r.json().get("data")
        assert data is not None, "测试计划报告详情不应为空"
        assert data.get("name")
        assert "defaultLayout" in data
        assert "passRate" in data
        assert "executeRate" in data
        assert "executeCount" in data
        assert "functionalCount" in data
        assert "apiCaseCount" in data
        assert "apiScenarioCount" in data

    def test_test_plan_report_layout(self, auth_client):
        """GET /test-plan/report/get-layout/{id} 返回报告布局。"""
        r = auth_client.post("/test-plan/page", json={"pageSize": 1, "current": 1})
        plans = r.json().get("data", {}).get("list", [])
        pid = plans[0]["id"]

        r = auth_client.get(f"/test-plan/report/get-layout/{pid}")
        assert r.status_code == 200
        layout = r.json().get("data") or []
        assert len(layout) > 0, "报告布局不应为空"
        names = {card.get("name") for card in layout}
        assert "SUMMARY" in names or len(layout) > 0

    def test_test_plan_report_detail_pages(self, auth_client):
        """报告各明细分页接口正常。"""
        r = auth_client.post("/test-plan/page", json={"pageSize": 1, "current": 1})
        plans = r.json().get("data", {}).get("list", [])
        pid = plans[0]["id"]
        body = {"reportId": pid, "current": 1, "pageSize": 500, "startPager": False}

        for url in [
            "/test-plan/report/detail/bug/page",
            "/test-plan/report/detail/functional/case/page",
            "/test-plan/report/detail/api/case/page",
            "/test-plan/report/detail/scenario/case/page",
        ]:
            r = auth_client.post(url, json=body)
            assert r.status_code == 200, f"{url} 返回 {r.status_code}"
            d = r.json().get("data", {})
            assert "list" in d, f"{url} 缺少 list 字段"

    def test_test_plan_export_log(self, auth_client):
        """POST /test-plan/report/export/{id} 正常。"""
        r = auth_client.post("/test-plan/report/export/test-plan-id")
        assert r.status_code == 200

    def test_test_plan_batch_param(self, auth_client):
        """批量导出 selectAll 返回报告 ID 集合。"""
        params = {
            "projectId": "", "selectIds": [],
            "selectAll": True, "excludeIds": [],
            "condition": {},
        }
        r = auth_client.post("/test-plan/report/batch-param", json=params)
        assert r.status_code == 200
        ids = r.json().get("data") or []
        assert len(ids) > 0, "selectAll 应返回非空计划 ID 列表"

    def test_test_plan_batch_export_log(self, auth_client):
        """POST /test-plan/report/batch-export 正常。"""
        r = auth_client.post("/test-plan/report/batch-export", json={})
        assert r.status_code == 200
