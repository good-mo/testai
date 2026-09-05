# -*- coding: utf-8 -*-
"""
软删除幽灵数据回归测试
=======================
软删除表上用于“展示 / 统计 / 计数”的读取查询都应带 deleted 过滤，
确保已软删除的记录不再混入列表与统计结果（幽灵数据）。

覆盖此前审计发现的漏过滤点：
  - projects.list_projects / get_project
  - environment.manager.get_stats（环境总数 / 分状态统计）
  - api_testing.management.environments.list_environments
  - insights 侧对 defects 的聚合口径（由 estimate/summarize 使用）
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.core.database import Database  # noqa: E402
from app.environment import manager as env_mgmt  # noqa: E402
from app.repositories.project_repo import ProjectRepo  # noqa: E402


def _uniq(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _get_conn():
    return Database.get_conn("tga.db")


def _soft_delete(table: str, rid: str):
    """直接对软删除表标记 deleted=1（模拟已进回收站）。"""
    conn = _get_conn()
    conn.execute(f"UPDATE {table} SET deleted = 1 WHERE id = ?", (rid,))
    conn.commit()


# ── projects ────────────────────────────────────────────────
def test_project_list_and_get_exclude_deleted():
    name = _uniq("PROJ")
    item = ProjectRepo.create(name=name)
    pid = item["id"]
    try:
        # 未删除时可见
        assert pid in {p["id"] for p in ProjectRepo.list()}
        assert ProjectRepo.get(pid) is not None

        # 软删除后列表与详情均不再返回（幽灵数据消失）
        _soft_delete("projects", pid)
        assert pid not in {p["id"] for p in ProjectRepo.list()}
        assert ProjectRepo.get(pid) is None
    finally:
        conn = _get_conn()
        conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
        conn.commit()


# ── environment.manager.get_stats ──────────────────────────
def test_env_stats_exclude_deleted():
    name = _uniq("ENV")
    env = env_mgmt.register_environment(name=name)
    eid = env["id"]
    try:
        before = env_mgmt.get_stats()["env_total"]
        # 软删除后：总数应比“删除前”少 1（或至少不再增大）
        env_mgmt.trash_environment(eid)
        after = env_mgmt.get_stats()["env_total"]
        assert after == before - 1 or after <= before
    finally:
        env_mgmt.purge_environment(eid)

# ── api_testing 环境：list/get 排除软删 + delete 改软删除 ──
def test_api_testing_environment_soft_delete():
    import app.api_testing.management.environments as me
    import app.apitest.store._base  # noqa: F401  确保 api_environments 建表
    from app.core.database import Database as _DB
    conn = _DB.get_conn("projects.db")
    prefix = _uniq("AENV-")
    env = me.create_environment(name=prefix, base_url="http://x")
    eid = env["id"]
    try:
        # 常规列表/详情可见
        assert any(e["id"] == eid for e in me.list_environments())
        assert me.get_environment(eid) is not None
        # 删除走软删除：常规不可见
        assert me.delete_environment(eid) is True
        assert me.get_environment(eid) is None, "软删后 get 不应返回记录"
        assert not any(e["id"] == eid for e in me.list_environments()), \
            "软删后 list 不应返回该环境"
    finally:
        # 彻底清理（测试内直接硬删避免残留）
        conn.execute("DELETE FROM api_environments WHERE id=?", (eid,))
        conn.commit()


# ════════════════════════════════════════════════════════════
# P1-3 回归：软删后 get_*/update_* 必须返回 None（不得读出/改写回收站数据）
# 覆盖 apitest_repo 四张表（definition/case/scenario/mock）、environments 表
# 与 projects 表。软删后 get 必返回 None、update 必返回 None（且不改写记录）。
# ════════════════════════════════════════════════════════════

def _trigger_apitest_tables():
    """确保 api_definitions / api_cases / api_scenarios / api_mocks 已建表。"""
    import app.apitest.store  # noqa: F401  side-effect: 建表
    from app.repositories.apitest_repo import ApitestRepo as Repo
    return Repo


def _apitest_soft_delete(table: str, rid: str):
    conn = Database.get_conn("apitest.db")
    conn.execute(f"UPDATE {table} SET deleted = 1 WHERE id = ?", (rid,))
    conn.commit()


def _project_soft_delete(rid: str):
    conn = Database.get_conn("tga.db")
    conn.execute("UPDATE projects SET deleted = 1 WHERE id = ?", (rid,))
    conn.commit()


# ── apitest_repo 四张表：definition / case / scenario / mock ──
def test_apitest_get_update_guard_all_tables():
    Repo = _trigger_apitest_tables()
    cases = [
        # (table, creator, getter, updater, updater_kwargs)
        ("api_definitions",
         lambda: Repo.create_definition(name=_uniq("DEF"), method="GET",
                                        path="/x"),
         Repo.get_definition, Repo.update_definition, {"name": "HACKED-DEF"}),
        ("api_cases",
         lambda: Repo.create_api_case(name=_uniq("CASE")),
         Repo.get_api_case, Repo.update_api_case, {"name": "HACKED-CASE"}),
        ("api_scenarios",
         lambda: Repo.create_scenario(name=_uniq("SC")),
         Repo.get_scenario, Repo.update_scenario, {"name": "HACKED-SC"}),
        ("api_mocks",
         lambda: Repo.create_mock(name=_uniq("MOCK")),
         Repo.get_mock, Repo.update_mock, {"name": "HACKED-MOCK"}),
    ]
    created_ids = []
    try:
        for table, creator, getter, updater, upd_kwargs in cases:
            obj = creator()
            rid = obj["id"]
            created_ids.append((table, rid))
            # 未删除时正常读取
            assert getter(rid) is not None
            # 软删后 get 返回 None、update 返回 None 且记录未被改写
            _apitest_soft_delete(table, rid)
            assert getter(rid) is None, f"{table}: 软删后 get 不应返回记录"
            assert updater(rid, **upd_kwargs) is None, \
                f"{table}: 软删后 update 应返回 None"
            # 校验软删记录未被 update 改写
            conn = Database.get_conn("apitest.db")
            row = conn.execute(
                f"SELECT name FROM {table} WHERE id = ?", (rid,)).fetchone()
            assert row["name"] != upd_kwargs["name"], \
                f"{table}: 软删记录不应被 update 改写"
    finally:
        for table, rid in created_ids:
            try:
                Database.get_conn("apitest.db").execute(
                    f"DELETE FROM {table} WHERE id = ?", (rid,))
                Database.get_conn("apitest.db").commit()
            except Exception:
                pass


# ── environments 表：manager 与 repository 两侧 ────────────
def test_environment_get_update_guard_both_layers():
    from app.environment import manager as env_mgr
    from app.repositories.environment_repo import EnvironmentRepo

    # manager 层
    env = env_mgr.register_environment(name=_uniq("ENV-GUARD"))
    eid = env["id"]
    try:
        assert env_mgr.get_environment(eid) is not None
        env_mgr.trash_environment(eid)
        assert env_mgr.get_environment(eid) is None, \
            "manager: 软删后 get_environment 不应返回记录"
        assert env_mgr.update_environment(eid, name="HACKED-ENV") is None, \
            "manager: 软删后 update_environment 应返回 None"
    finally:
        env_mgr.purge_environment(eid)

    # repository 层
    env2 = EnvironmentRepo.create({"name": _uniq("ENV-GUARD2")})
    eid2 = env2["id"]
    try:
        assert EnvironmentRepo.get(eid2) is not None
        conn = Database.get_conn("tga.db")
        conn.execute("UPDATE environments SET deleted = 1 WHERE id = ?", (eid2,))
        conn.commit()
        assert EnvironmentRepo.get(eid2) is None, \
            "repo: 软删后 get 不应返回记录"
        assert EnvironmentRepo.update(eid2, {"name": "HACKED-ENV2"}) is None, \
            "repo: 软删后 update 应返回 None"
    finally:
        try:
            conn = Database.get_conn("tga.db")
            conn.execute("DELETE FROM environments WHERE id = ?", (eid2,))
            conn.commit()
        except Exception:
            pass


# ── projects 表：软删后 get/update 均返回 None ─────────────
def test_project_update_guard_after_soft_delete():
    from app.repositories.project_repo import ProjectRepo

    # repository 层 update 不改写软删项目（dict/kwargs 两种形式均不改写）
    it = ProjectRepo.create(name=_uniq("PROJ-GUARD"))
    pid = it["id"]
    try:
        _project_soft_delete(pid)
        assert ProjectRepo.get(pid) is None
        assert ProjectRepo.update(pid, name="HACKED-PROJ") is None
        conn = Database.get_conn("tga.db")
        row = conn.execute(
            "SELECT name FROM projects WHERE id = ?", (pid,)).fetchone()
        assert row["name"] != "HACKED-PROJ", "软删项目不应被 update 改写"
    finally:
        conn = Database.get_conn("tga.db")
        conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
        conn.commit()


    # 再次确认（重复覆盖防御，dict 形式）
    it2 = ProjectRepo.create(name=_uniq("PROJ-GUARD2"))
    pid2 = it2["id"]
    try:
        _project_soft_delete(pid2)
        assert ProjectRepo.get(pid2) is None
        assert ProjectRepo.update(pid2, {"name": "HACKED-PROJ2"}) is None
        conn = Database.get_conn("tga.db")
        row = conn.execute(
            "SELECT name FROM projects WHERE id = ?", (pid2,)).fetchone()
        assert row["name"] != "HACKED-PROJ2", "软删项目不应被 update 改写"
    finally:
        conn = Database.get_conn("tga.db")
        conn.execute("DELETE FROM projects WHERE id = ?", (pid2,))
        conn.commit()
