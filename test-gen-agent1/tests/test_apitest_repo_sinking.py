"""
apitest 4 层重构：ApitestRepo 剩余委托空壳下沉回归
=========================================================
目的：验证 api_definitions / api_environments / api_follows /
api_execution_logs / api_test_cases / mock_services / assertion_rules
的 SQL 已从 store / management 下沉到 ApitestRepo 后行为一致。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.api_testing import management as mgmt  # noqa: E402
from app.apitest import store as store  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.repositories.apitest_repo import ApitestRepo as Repo  # noqa: E402


def _uniq(prefix="APT-SINK"):
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _cleanup():
    c = Database.get_conn("apitest.db")
    c.execute("DELETE FROM api_definitions")
    c.execute("DELETE FROM api_definition_versions")
    c.execute("DELETE FROM api_environments")
    c.execute("DELETE FROM api_follows")
    c.execute("DELETE FROM api_execution_logs")
    c.execute("DELETE FROM api_test_cases")
    c.execute("DELETE FROM mock_services")
    c.execute("DELETE FROM assertion_rules")
    c.execute("DELETE FROM api_scenarios")
    c.commit()


def setup_function():
    _cleanup()


def teardown_function():
    _cleanup()


# ── api_definitions ──────────────────────────────────────
def test_definition_crud_via_repo():
    """Repository 直连 SQL 完成接口定义增查改删全流程。"""
    pid = _uniq()
    d = Repo.create_definition(name="login", path="/login", project_id=pid)
    did = d["id"]
    try:
        got = Repo.get_definition(did)
        assert got["name"] == "login"
        assert Repo.count_definitions(project_id=pid) >= 1
        assert any(x["id"] == did for x in Repo.list_definitions(project_id=pid))
        upd = Repo.update_definition(did, name="login2", headers={"a": "b"})
        assert upd["name"] == "login2"
        assert upd["headers"] == {"a": "b"}
        assert Repo.delete_definition(did) is True
        assert any(x["id"] == did for x in Repo.list_trash_definitions(project_id=pid))
        assert Repo.count_trash_definitions(project_id=pid) >= 1
        assert Repo.restore_definition(did) is True
        # cleanup
        Repo.delete_definition(did)
        assert Repo.purge_definition(did) is True
    finally:
        _cleanup()


def test_definition_batch_repo():
    """批量删除/恢复/清理接口定义。"""
    pid = _uniq()
    ids = [Repo.create_definition(name=f"d{i}", project_id=pid)["id"] for i in range(3)]
    try:
        assert Repo.batch_delete_definitions(ids) == 3
        assert Repo.batch_restore_definitions(ids) == 3
        assert Repo.batch_update_definitions(ids, name="renamed") == 3
        assert Repo.batch_purge_definitions(ids) == 3
    finally:
        _cleanup()


def test_definition_version_and_schedule_repo():
    """版本创建/回滚 + 调度列表。"""
    pid = _uniq()
    d = Repo.create_definition(name="ver-test", project_id=pid)
    did = d["id"]
    try:
        # 创建新版本
        ver = Repo.create_definition_version(did, version="v2")
        assert ver is not None
        assert ver["version_id"] != d["version_id"]
        # 列出版本
        versions = Repo.list_definition_versions(ver["ref_id"] or did)
        assert len(versions) >= 1
        # 调度列表（表可能为空，但不应抛异常）
        schedules = Repo.list_schedules()
        assert isinstance(schedules, list)
    finally:
        _cleanup()


# ── api_environments ─────────────────────────────────────
def test_environment_crud_via_repo():
    """环境 CRUD 下沉后 Repository 直连 SQL 行为一致。"""
    pid = _uniq()
    env = Repo.create_environment(name="env1", base_url="http://x.com", project_id=pid)
    eid = env["id"]
    try:
        assert Repo.get_environment(eid)["name"] == "env1"
        assert Repo.count_environments(project_id=pid) >= 1
        assert any(x["id"] == eid for x in Repo.list_environments(project_id=pid))
        assert Repo.update_environment(eid, name="env2")["name"] == "env2"
        assert Repo.export_environment(eid)["name"] == "env2"
        # store delegation
        assert store.get_environment(eid)["name"] == "env2"
        # import
        imp = Repo.import_environment(
            {"name": "env-imp", "config": {"httpConfig": []}}, project_id=pid)
        assert imp["name"] == "env-imp"
        assert Repo.delete_environment(eid) is True
    finally:
        _cleanup()


# ── api_follows ──────────────────────────────────────────
def test_follows_crud_via_repo():
    """关注/取消关注/查询下沉直连。"""
    rid = _uniq()
    uid = "test-user"
    try:
        assert Repo.follow_resource(rid, "case", uid) is True
        assert Repo.is_followed(rid, "case", uid) is True
        assert uid in Repo.list_followers(rid, "case")
        assert Repo.toggle_follow(rid, "case", uid) is False  # now unfollowed
        assert Repo.is_followed(rid, "case", uid) is False
        assert Repo.follow_resource(rid, "case", uid) is True
        assert Repo.unfollow_resource(rid, "case", uid) is True
        assert Repo.is_followed(rid, "case", uid) is False
        # store delegation
        assert store.follow_resource("case", rid, uid) is True
        assert store.is_followed("case", rid, uid) is True
    finally:
        _cleanup()


# ── api_execution_logs ───────────────────────────────────
def test_execution_logs_via_repo():
    """执行日志查询下沉直连。"""
    target = _uniq()
    from app.apitest import execution_log
    try:
        execution_log.log_execution(
            exec_type="case", target_id=target, target_name="Test Run",
            passed=True, response_code=200)
        assert len(Repo.list_execution_logs(target_id=target)) >= 1
        assert Repo.count_execution_logs(target_id=target) >= 1
        assert Repo.clear_execution_logs(exec_type="case") >= 0
    finally:
        _cleanup()


# ── V1 api_test_cases ────────────────────────────────────
def test_v1_api_test_cases_via_repo():
    """V1 api_test_cases CRUD 下沉后行为一致。"""
    pid = _uniq()
    tc = Repo.mgmt_create_api_test_case(name="tc1", path="/test", project_id=pid)
    tcid = tc["id"]
    try:
        assert Repo.mgmt_get_api_test_case(tcid)["name"] == "tc1"
        assert any(x["id"] == tcid for x in Repo.mgmt_list_api_test_cases(project_id=pid))
        assert Repo.mgmt_update_api_test_case(tcid, name="tc2")["name"] == "tc2"
        # management delegation
        assert mgmt.get_api_test_case(tcid)["name"] == "tc2"
        assert Repo.mgmt_delete_api_test_case(tcid) is True
        assert any(x["id"] == tcid for x in Repo.mgmt_list_trash_cases())
        assert Repo.mgmt_restore_case(tcid) is True
        # permanent delete
        assert Repo.mgmt_delete_api_test_case(tcid, permanent=True) is True
    finally:
        _cleanup()


# ── V1 mock_services ─────────────────────────────────────
def test_v1_mock_services_via_repo():
    """V1 mock_services CRUD 下沉后行为一致。"""
    pid = _uniq()
    ms = Repo.mgmt_create_mock_service(name="mock1", project_id=pid)
    msid = ms["id"]
    try:
        assert Repo.mgmt_get_mock_service(msid)["name"] == "mock1"
        assert any(x["id"] == msid for x in Repo.mgmt_list_mock_services())
        assert Repo.mgmt_update_mock_service(msid, name="mock2")["name"] == "mock2"
        # management delegation
        assert mgmt.get_mock_service(msid)["name"] == "mock2"
        assert Repo.mgmt_delete_mock_service(msid) is True
        assert any(x["id"] == msid for x in Repo.mgmt_list_trash_mocks())
        assert Repo.mgmt_restore_mock(msid) is True
        assert Repo.mgmt_delete_mock_service(msid, permanent=True) is True
    finally:
        _cleanup()


# ── assertion_rules ──────────────────────────────────────
def test_assertion_rules_via_repo():
    """断言规则 CRUD 下沉直连。"""
    try:
        rule = Repo.create_assertion_rule(name="rule1", rule_type="status_code")
        rid = rule["id"]
        assert Repo.get_assertion_rule(rid)["name"] == "rule1"
        assert len(Repo.list_assertion_rules()) >= 1
        # management delegation
        assert mgmt.get_assertion_rule(rid)["name"] == "rule1"
        assert Repo.delete_assertion_rule(rid) is True
    finally:
        _cleanup()


# ── 操作日志 ─────────────────────────────────────────────
def test_operation_logs_via_repo():
    """操作日志查询下沉直连。"""
    try:
        assert isinstance(Repo.list_operation_logs(limit=5), list)
        assert Repo.count_operation_logs() >= 0
        # very old cleanup should not fail
        assert isinstance(Repo.clear_operation_logs(days=36500), int)
    finally:
        _cleanup()
