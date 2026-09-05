"""报告步骤 / 后台定时任务类型 —— 前端渲染值域契约断言。

背景
====
前端的报告步骤渲染依赖各自本地字典，若后端在这些字段上输出字典之外的值会直接崩溃：
  - stepStatus.vue / statusMap：报告步骤状态 → 未知值 undefined.label 崩溃；
  - conditionStatus.vue / scenarioStepMap：场景报告步骤类型 → 未知 stepType 崩溃；
  - systemTaskTable.vue / scheduleTaskTypeMap：后台定时任务类型 → undefined 文本。

本测试锁定后端修复不复发：对所有报告详情 / 报告步骤 / 后台定时任务接口断言
  - 步骤节点的 ``status``/``execStatus`` ∈ 报告步骤状态枚举；
  - 步骤节点的 ``stepType`` ∈ 报告步骤类型枚举；
  - 定时任务列表 ``resourceType`` ∈ 定时任务类型枚举。
任何违反值域的输出直接让 CI 红灯。
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.task_enums import (
    REPORT_STEP_STATUS_SET,
    REPORT_STEP_TYPE_SET,
    SCHEDULE_RESOURCE_TYPE_SET,
    is_report_step_status,
    is_report_step_type,
    is_schedule_resource_type,
)


def _login(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code != 200:
        return
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        _login(c)
        yield c


def _data(resp):
    payload = resp.json()
    assert isinstance(payload, dict) and "data" in payload, str(payload)[:200]
    assert payload["code"] < 500, f"服务端异常: {payload['message']}"
    return payload["data"]


def _is_step_node(node):
    """步骤节点：含 stepId / stepType / 或嵌套 children 的报告步骤。"""
    return isinstance(node, dict) and (
        "stepId" in node or "stepType" in node or "requestName" in node
    )


def _walk_report_steps(root):
    """递归收集报告中所有步骤节点。"""
    found = []
    if isinstance(root, list):
        for item in root:
            found.extend(_walk_report_steps(item))
    elif isinstance(root, dict):
        if _is_step_node(root):
            found.append(root)
        for key in ("children", "steps"):
            if key in root:
                found.extend(_walk_report_steps(root[key]))
    return found


def _assert_report_step_domains(root):
    for node in _walk_report_steps(root):
        if "stepType" in node and node["stepType"] is not None:
            assert is_report_step_type(node["stepType"]), (
                f"步骤 stepType={node['stepType']!r} 不在报告步骤类型枚举 {sorted(REPORT_STEP_TYPE_SET)}"
            )
        for k in ("status", "execStatus"):
            if k in node and isinstance(node.get(k), str) and node[k]:
                assert is_report_step_status(node[k]), (
                    f"步骤 {k}={node[k]!r} 不在报告步骤状态枚举 {sorted(REPORT_STEP_STATUS_SET)}"
                )


def _assert_schedule_resource_type(data):
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for k in ("list", "items", "records"):
            if isinstance(data.get(k), list):
                items = data[k]
                break
    for item in items:
        if isinstance(item, dict) and item.get("resourceType") is not None:
            assert is_schedule_resource_type(item["resourceType"]), (
                f"resourceType={item['resourceType']!r} 不在定时任务类型枚举 {sorted(SCHEDULE_RESOURCE_TYPE_SET)}"
            )


# ════════════════════════════════════════════════════════════
# 报告步骤：status/execStatus/stepType 落在前端可识别值域
# ════════════════════════════════════════════════════════════
class TestReportStepEnum:
    def test_case_report_detail(self, client):
        d = _data(client.post("/api/report/case/get", json={}))
        _assert_report_step_domains(d)

    def test_scenario_report_detail(self, client):
        d = _data(client.post("/api/report/scenario/get", json={}))
        _assert_report_step_domains(d)

    def test_case_report_step_detail(self, client):
        d = _data(client.post("/api/report/case/get/detail", json={}))
        _assert_report_step_domains(d)

    def test_scenario_report_step_detail(self, client):
        d = _data(client.post("/api/report/scenario/get/detail", json={}))
        _assert_report_step_domains(d)

    def test_case_share_detail(self, client):
        d = _data(client.get("/api/report/case/share/c1/c1"))
        _assert_report_step_domains(d)

    def test_scenario_share_detail(self, client):
        d = _data(client.get("/api/report/scenario/share/c1/c1"))
        _assert_report_step_domains(d)


# ════════════════════════════════════════════════════════════
# 后台定时任务列表：resourceType 落在前端可识别值域
# ════════════════════════════════════════════════════════════
class TestScheduleResourceType:
    def test_system_schedule_list(self, client):
        d = _data(client.get("/system/task-center/schedule/page"))
        _assert_schedule_resource_type(d)

    def test_project_schedule_list(self, client):
        d = _data(client.get("/project/task-center/schedule/page"))
        _assert_schedule_resource_type(d)

    def test_enum_self_consistent(self):
        assert is_report_step_status("SUCCESS")
        assert is_report_step_status("COMPLETED")
        assert not is_report_step_status("whatever")
        assert is_report_step_type("API")
        assert is_report_step_type("LOOP_CONTROLLER")
        assert not is_report_step_type("TEST_PLAN_API_CASE")  # 非前端可识别，须被归一化
        assert is_schedule_resource_type("API_IMPORT")
        assert not is_schedule_resource_type("CLEAN_REPORT")
