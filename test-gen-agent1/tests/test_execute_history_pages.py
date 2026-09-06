"""执行历史页数据查询修复测试。

修复前 /api/case/execute/page、/api/scenario/execute/page 等接口恒返回
{list:[],total:0}；修复后应从 api_execution_logs 真实数据源查询并返回记录。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


def _data(resp):
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


@pytest.fixture(scope="module")
def client():
    os.environ['OPENAI_API_KEY'] = 'test-key'
    from app.main import app
    with TestClient(app) as c:
        # 登录获取认证令牌
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


@pytest.fixture(scope="module")
def execution_data():
    """插入一条用例执行日志与一条场景执行日志，测试完毕后清理。"""
    from app.apitest.execution_log import log_execution
    import time

    case_log_id = None
    scn_log_id = None
    try:
        log_execution(
            exec_type="case",
            target_id="hist_test_case_001",
            target_name="历史查询用例",
            method="GET",
            url="/api/hist-test",
            passed=True,
            response_code=200,
            duration_ms=120,
            detail={"total_steps": 1, "passed_steps": 1},
        )
        log_execution(
            exec_type="scenario",
            target_id="hist_test_scn_001",
            target_name="历史查询场景",
            method="SCENARIO",
            url="",
            passed=False,
            response_code=0,
            duration_ms=500,
            error="step failed",
            detail={"total_steps": 3, "passed_steps": 1, "failed_steps": 2},
        )
        # 操作日志
        from app.apitest.store._base import _log_operation
        _log_operation("case", "hist_test_case_001", "历史查询用例", "create",
                       operator="admin", project_id="proj_test")
        _log_operation("scenario", "hist_test_scn_001", "历史查询场景", "update",
                       operator="admin", project_id="proj_test")
        yield
    finally:
        # 清理测试数据
        try:
            from app.apitest.execution_log import _get_conn
            conn = _get_conn()
            conn.execute("DELETE FROM api_execution_logs WHERE target_id IN ('hist_test_case_001','hist_test_scn_001')")
            conn.commit()
        except Exception:
            pass
        try:
            from app.apitest.store._base import _get_conn
            conn = _get_conn()
            conn.execute("DELETE FROM api_operation_logs WHERE resource_id IN ('hist_test_case_001','hist_test_scn_001')")
            conn.commit()
        except Exception:
            pass


class TestCaseExecuteHistory:
    """/api/case/execute/page"""

    def test_post_case_execute_page_returns_data(self, client, execution_data):
        """POST /api/case/execute/page 应返回真实执行日志数据。"""
        r = client.post("/api/case/execute/page", json={
            "id": "hist_test_case_001",
            "current": 1,
            "pageSize": 10,
        })
        assert r.status_code == 200
        data = _data(r)
        assert data["total"] >= 1
        assert len(data["list"]) >= 1
        item = data["list"][0]
        # 关键字段应存在
        for key in ("id", "name", "startTime", "status", "triggerMode",
                     "execStatus", "operationUser", "createUser"):
            assert key in item, f"missing field: {key}"
        assert item["name"] == "历史查询用例"
        assert item["status"] == "SUCCESS"
        assert item["triggerMode"] == "MANUAL"
        assert item["execStatus"] == "COMPLETED"

    def test_post_case_execute_page_all_records(self, client, execution_data):
        """不带 case_id 时返回全部用例执行记录。"""
        r = client.post("/api/case/execute/page", json={"current": 1, "pageSize": 10})
        assert r.status_code == 200
        data = _data(r)
        # 应该能查询到测试记录
        names = [i.get("name", "") for i in data["list"]]
        assert any("历史查询用例" in n for n in names)

    def test_get_case_execute_page(self, client, execution_data):
        """GET /api/case/execute/page 也应可用。"""
        r = client.get("/api/case/execute/page?id=hist_test_case_001")
        assert r.status_code == 200
        data = _data(r)
        assert data["total"] >= 1
        assert data["list"][0]["name"] == "历史查询用例"

    def test_case_operation_history(self, client, execution_data):
        """POST /api/case/operation-history/page 应返回操作日志。"""
        r = client.post("/api/case/operation-history/page", json={
            "id": "hist_test_case_001",
        })
        assert r.status_code == 200
        data = _data(r)
        assert data["total"] >= 1
        assert data["list"][0]["sourceId"] == "hist_test_case_001"


class TestScenarioExecuteHistory:
    """/api/scenario/execute/page"""

    def test_post_scenario_execute_page(self, client, execution_data):
        """POST /api/scenario/execute/page 应返回场景执行日志。"""
        r = client.post("/api/scenario/execute/page", json={
            "id": "hist_test_scn_001",
            "current": 1,
            "pageSize": 10,
        })
        assert r.status_code == 200
        data = _data(r)
        assert data["total"] >= 1
        item = data["list"][0]
        assert item["name"] == "历史查询场景"
        # 失败场景 status=ERROR
        assert item["status"] == "ERROR"

    def test_scenario_operation_history(self, client, execution_data):
        """POST /api/scenario/operation-history/page 应返回操作日志。"""
        r = client.post("/api/scenario/operation-history/page", json={
            "id": "hist_test_scn_001",
        })
        assert r.status_code == 200
        data = _data(r)
        assert data["total"] >= 1


class TestDefinitionAndMockHistory:
    """definition/mock 操作历史"""

    def test_definition_operation_history(self, client):
        """POST /api/definition/operation-history 应返回 200 且结构正确。"""
        r = client.post("/api/definition/operation-history", json={})
        assert r.status_code == 200
        data = _data(r)
        assert isinstance(data.get("list"), list)
        assert isinstance(data.get("total"), int)

    def test_mock_operation_history(self, client):
        """POST /api/definition/mock/operation-history/page 应返回 200。"""
        r = client.post("/api/definition/mock/operation-history/page", json={})
        assert r.status_code == 200
        data = _data(r)
        assert isinstance(data.get("list"), list)
        assert isinstance(data.get("total"), int)
