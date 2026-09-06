"""
apitest 4 层重构：ApitestRepo 接口用例 / 场景下沉对齐回归
=========================================================
目的：接口用例（api_cases）与接口场景（api_scenarios）的 CRUD / 回收站 /
批量数据访问 SQL 已从 app.apitest.store 下沉到 app.repositories.apitest_repo
.ApitestRepo（Repository 层仓库内直连 SQL），旧 store.cases_scenarios 退化为
委托门面。本测试验证：
  1) Repository 直连 SQL 能完成 增 / 查 / 改 / 软删 / 回收站恢复 / 彻底删除；
  2) 与旧 store 门面在共享 apitest.db 上行为一致、互相可见；
即 Repository 从「委托空壳」下沉为直连 SQL 后仍零回归。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.apitest import store as store  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.repositories.apitest_repo import ApitestRepo as Repo  # noqa: E402


def _uniq(prefix="APT-CS"):
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _cleanup():
    c = Database.get_conn("apitest.db")
    c.execute("DELETE FROM api_cases")
    c.execute("DELETE FROM api_scenarios")
    c.commit()


def setup_function():
    _cleanup()


def teardown_function():
    _cleanup()


# ── 接口用例 ─────────────────────────────────────────────
def test_case_crud_via_repo():
    """Repository 直连 SQL 完成用例增查改删回收全流程。"""
    pid = _uniq()
    c = Repo.create_api_case(name="login", project_id=pid,
                             request={"url": "/login"}, asserts=[{"k": "v"}],
                             priority="P1")
    cid = c["id"]
    try:
        # 读取（request/asserts JSON 反序列化一致）
        got = Repo.get_api_case(cid)
        assert got["name"] == "login"
        assert got["request"] == '{"url": "/login"}'  # request 不参与 JSON 反序列化（与旧 store 一致）
        assert got["asserts"] == [{"k": "v"}]
        assert got["project_id"] == pid
        # 按 project 计数/列表可见
        assert Repo.count_api_cases(project_id=pid) == 1
        assert any(x["id"] == cid for x in Repo.list_api_cases(project_id=pid))
        # 更新
        upd = Repo.update_api_case(cid, name="login2", asserts=[{"a": 1}])
        assert upd["name"] == "login2"
        assert upd["asserts"] == [{"a": 1}]
        # 软删进入回收站
        assert Repo.delete_api_case(cid) is True
        assert Repo.get_api_case(cid) is None  # 软删后 get 过滤 deleted
        assert Repo.count_api_cases(project_id=pid) == 0  # 常规列表排除
        assert any(x["id"] == cid for x in Repo.list_trash_cases(project_id=pid))
        # 恢复
        assert Repo.restore_case(cid) is True
        assert Repo.count_api_cases(project_id=pid) == 1
        # 再删后彻底清空
        Repo.delete_api_case(cid)
        assert Repo.purge_case(cid) is True
        assert Repo.get_api_case(cid) is None
    finally:
        _cleanup()


def test_case_batch_repo():
    """批量软删/恢复/彻底删除 + 更新一致。"""
    pid = _uniq()
    ids = [Repo.create_api_case(name=f"c{i}", project_id=pid)["id"] for i in range(3)]
    try:
        assert Repo.batch_delete_cases(ids) == 3
        assert Repo.count_trash_cases(project_id=pid) == 3
        assert Repo.batch_restore_cases(ids) == 3
        assert Repo.count_trash_cases(project_id=pid) == 0
        assert Repo.batch_update_cases(ids, priority="P0") == 3
        assert all(Repo.get_api_case(i)["priority"] == "P0" for i in ids)
        assert Repo.batch_purge_cases(ids) == 3
        assert Repo.get_api_case(ids[0]) is None
    finally:
        _cleanup()


def test_case_old_store_delegates_to_repo():
    """旧 store 门面经 Repository 直连 SQL，与 Repo 共享库、行为一致。"""
    pid = _uniq()
    r = Repo.create_api_case(name="rc", project_id=pid)
    s = store.create_api_case(name="sc", project_id=pid)
    try:
        assert Repo.get_api_case(r["id"])["name"] == "rc"
        assert store.get_api_case(s["id"])["name"] == "sc"
        names = sorted(x["name"] for x in store.list_api_cases(project_id=pid))
        assert names == ["rc", "sc"]
        assert store.count_api_cases(project_id=pid) == 2
        # 门面软删走 Repo 直连 SQL
        assert store.delete_api_case(s["id"]) is True
        assert store.count_api_cases(project_id=pid) == 1
        assert any(x["id"] == s["id"] for x in store.list_trash_cases(project_id=pid))
        assert store.restore_case(s["id"]) is True
        assert store.count_api_cases(project_id=pid) == 2
    finally:
        _cleanup()


# ── 接口场景 ─────────────────────────────────────────────
def test_scenario_crud_via_repo():
    """Repository 直连 SQL 完成场景增查改删回收全流程。"""
    pid = _uniq()
    sc = Repo.create_scenario(name="flow", project_id=pid, steps=[{"n": 1}])
    sid = sc["id"]
    try:
        got = Repo.get_scenario(sid)
        assert got["name"] == "flow"
        assert got["steps"] == [{"n": 1}]
        assert Repo.count_scenarios(project_id=pid) == 1
        assert any(x["id"] == sid for x in Repo.list_scenarios(project_id=pid))
        upd = Repo.update_scenario(sid, name="flow2", steps=[{"n": 2}])
        assert upd["steps"] == [{"n": 2}]
        assert Repo.delete_scenario(sid) is True
        assert Repo.count_scenarios(project_id=pid) == 0
        assert any(x["id"] == sid for x in Repo.list_trash_scenarios(project_id=pid))
        assert Repo.restore_scenario(sid) is True
        assert Repo.count_scenarios(project_id=pid) == 1
        Repo.delete_scenario(sid)
        assert Repo.purge_scenario(sid) is True
        assert Repo.get_scenario(sid) is None
    finally:
        _cleanup()


def test_scenario_old_store_delegates_to_repo():
    """旧 store 门面场景与 Repo 直连 SQL 一致。"""
    pid = _uniq()
    r = Repo.create_scenario(name="rs", project_id=pid)
    s = store.create_scenario(name="ss", project_id=pid)
    try:
        assert store.get_scenario(r["id"])["name"] == "rs"
        names = sorted(x["name"] for x in store.list_scenarios(project_id=pid))
        assert names == ["rs", "ss"]
        assert store.delete_scenario(s["id"]) is True
        assert any(x["id"] == s["id"] for x in store.list_trash_scenarios(project_id=pid))
        assert store.restore_scenario(s["id"]) is True
        assert store.count_scenarios(project_id=pid) == 2
    finally:
        _cleanup()


# ── Mock 服务 ─────────────────────────────────────────────
def test_mock_crud_via_repo():
    """Repository 直连 SQL 完成 Mock 增查改删回收全流程。"""
    pid = _uniq()
    m = Repo.create_mock(name="mock1", project_id=pid, path="/api", method="POST",
                         response_headers={"Content-Type": "application/json"})
    mid = m["id"]
    try:
        got = Repo.get_mock(mid)
        assert got["name"] == "mock1"
        assert got["response_headers"] == {"Content-Type": "application/json"}
        assert got["method"] == "POST"
        assert Repo.count_mocks(project_id=pid) == 1
        assert any(x["id"] == mid for x in Repo.list_mocks(project_id=pid))
        upd = Repo.update_mock(mid, path="/api2", response_headers={"A": "1"})
        assert upd["path"] == "/api2"
        assert upd["response_headers"] == {"A": "1"}
        assert Repo.delete_mock(mid) is True
        assert Repo.count_mocks(project_id=pid) == 0
        assert any(x["id"] == mid for x in Repo.list_trash_mocks(project_id=pid))
        assert Repo.restore_mock(mid) is True
        assert Repo.count_mocks(project_id=pid) == 1
        Repo.delete_mock(mid)
        assert Repo.purge_mock(mid) is True
        assert Repo.get_mock(mid) is None
    finally:
        _cleanup_mocks()


def test_mock_old_store_delegates_to_repo():
    """旧 store 门面 Mock 与 Repo 直连 SQL 一致。"""
    pid = _uniq()
    r = Repo.create_mock(name="rm", project_id=pid)
    s = store.create_mock(name="sm", project_id=pid)
    try:
        assert store.get_mock(r["id"])["name"] == "rm"
        names = sorted(x["name"] for x in store.list_mocks(project_id=pid))
        assert names == ["rm", "sm"]
        assert store.count_mocks(project_id=pid) == 2
        assert store.delete_mock(s["id"]) is True
        assert any(x["id"] == s["id"] for x in store.list_trash_mocks(project_id=pid))
        assert store.restore_mock(s["id"]) is True
        assert store.count_mocks(project_id=pid) == 2
    finally:
        _cleanup_mocks()


def test_mock_batch_repo():
    """Mock 批量软删/恢复/彻底删除一致。"""
    pid = _uniq()
    ids = [Repo.create_mock(name=f"m{i}", project_id=pid)["id"] for i in range(3)]
    try:
        assert Repo.batch_delete_mocks(ids) == 3
        assert Repo.count_trash_mocks(project_id=pid) == 3
        assert Repo.batch_restore_mocks(ids) == 3
        assert Repo.count_trash_mocks(project_id=pid) == 0
        assert Repo.batch_purge_mocks(ids) == 3
        assert Repo.get_mock(ids[0]) is None
    finally:
        _cleanup_mocks()


def _cleanup_mocks():
    c = Database.get_conn("apitest.db")
    c.execute("DELETE FROM api_mocks")
    c.commit()
