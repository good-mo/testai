"""任务/报告输出值域契约断言。

背景
====
此前 Report / TaskCenter 兼容层把同一字段塞进多套互不相认的值域：
  - ``status``/``execStatus`` 被填成执行结果（SUCCESS/ERROR），
    而前端 executeStatusMap 期望执行状态（PENDING/RUNNING/...），
    导致「未知状态码」TypeError；
  - 任务中心列表 ``triggerMode`` 缺失，前端渲染出 undefined。

本测试锁定后端修复不复发：对所有任务中心 / 任务报告接口断言
  - ``status`` / ``execStatus`` ∈ 权威执行状态枚举；
  - ``result`` ∈ 权威执行结果枚举；
  - ``triggerMode`` ∈ 权威触发方式枚举。
任何违反值域的输出直接让 CI 红灯。
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.task_enums import (
    EXEC_RESULT_SET,
    EXEC_STATUS_SET,
    TRIGGER_MODE_SET,
    is_exec_status,
    is_trigger_mode,
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


def _assert_exec_status_field(obj, *keys):
    """断言对象中出现的 status/execStatus 属于执行状态枚举。"""
    for k in keys:
        if k in obj and obj[k] is not None and obj[k] != "":
            assert obj[k] in EXEC_STATUS_SET, (
                f"字段 {k}={obj[k]!r} 不在执行状态枚举 {sorted(EXEC_STATUS_SET)}"
            )


def _assert_trigger_field(obj):
    """断言 triggerMode 出现则属于触发方式枚举。"""
    if obj.get("triggerMode") is not None:
        assert obj["triggerMode"] in TRIGGER_MODE_SET, (
            f"triggerMode={obj['triggerMode']!r} 不在触发方式枚举 {sorted(TRIGGER_MODE_SET)}"
        )


def _assert_result_field(obj):
    if obj.get("result") is not None:
        assert obj["result"] in EXEC_RESULT_SET, (
            f"result={obj['result']!r} 不在执行结果枚举 {sorted(EXEC_RESULT_SET)}"
        )


def _walk_items(data):
    """从常见分页结构里提取条目列表（list / {list} / {items}）。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("list", "items", "records"):
            if isinstance(data.get(k), list):
                return data[k]
    return []


# ════════════════════════════════════════════════════════════
# 任务报告 task-report：status 必须是执行状态（修复 TypeError 崩溃）
# ════════════════════════════════════════════════════════════
class TestTaskReportEnum:
    def test_case_task_report(self, client):
        d = _data(client.get("/api/report/case/task-report/contract-noid"))
        _assert_exec_status_field(d, "status", "execStatus")
        _assert_result_field(d)

    def test_scenario_task_step(self, client):
        d = _data(client.get("/api/report/scenario/task-step/contract-noid"))
        _assert_exec_status_field(d, "status", "execStatus")
        _assert_result_field(d)

    def test_scenario_task_report(self, client):
        d = _data(client.get("/api/report/scenario/task-report/contract-noid/contract-step"))
        _assert_exec_status_field(d, "status", "execStatus")
        _assert_result_field(d)


# ════════════════════════════════════════════════════════════
# 报告详情：status/execStatus 为执行状态、result 为执行结果
# ════════════════════════════════════════════════════════════
class TestReportDetailEnum:
    def test_case_report_get_detail(self, client):
        resp = client.post("/api/report/case/get", json={})
        d = _data(resp)
        if isinstance(d, dict):
            _assert_exec_status_field(d, "status", "execStatus")
            _assert_result_field(d)
            _assert_trigger_field(d)

    def test_scenario_report_get_detail(self, client):
        resp = client.post("/api/report/scenario/get", json={})
        d = _data(resp)
        if isinstance(d, dict):
            _assert_exec_status_field(d, "status", "execStatus")
            _assert_result_field(d)
            _assert_trigger_field(d)

    def test_case_share_detail(self, client):
        for share_id, report_id in (("c1", "c1"), ("c", "noid")):
            d = _data(client.get(f"/api/report/case/share/{share_id}/{report_id}"))
            if isinstance(d, dict):
                _assert_exec_status_field(d, "status", "execStatus")
                _assert_result_field(d)
                _assert_trigger_field(d)


# ════════════════════════════════════════════════════════════
# 任务中心列表：status 为执行状态、triggerMode 为触发方式（修复 undefined）
# ════════════════════════════════════════════════════════════
class TestTaskCenterEnum:
    def test_project_task_center_exec_task_page(self, client):
        d = _data(client.post("/project/task-center/exec-task/page", json={"current": 1, "pageSize": 10}))
        for item in _walk_items(d):
            _assert_exec_status_field(item, "status", "execStatus")
            _assert_result_field(item)
            # 触发方式必须存在且属于权威枚举（不得缺失导致 undefined）
            assert "triggerMode" in item, "任务中心条目缺失 triggerMode 字段"
            assert is_trigger_mode(item["triggerMode"]), (
                f"triggerMode={item['triggerMode']!r} 非法"
            )

    def test_project_task_center_page(self, client):
        d = _data(client.get("/project/task-center/page"))
        for item in _walk_items(d):
            _assert_exec_status_field(item, "status")

    def test_status_is_exec_status_enum(self):
        # 权威枚举本身自洽
        assert is_exec_status("COMPLETED")
        assert not is_exec_status("SUCCESS")  # SUCCESS 是执行结果，不属于执行状态
