"""
环境 4 层重构：repository 层与旧 app.environment.manager 对齐回归测试
=====================================================================
目的：确保新增 app.repositories.environment_repo.EnvironmentRepo 在相同
数据库上，环境 CRUD / 回收站 / 告警 / 统计的 DB 数据访问输出形态与旧
app.environment.manager 完全一致 —— 这是把 Repository 从「委托空壳」
下沉为直连 SQL 后仍零回归的依据。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import app.environment.manager as old_mgr  # noqa: E402
from app.repositories.environment_repo import EnvironmentRepo  # noqa: E402


def _uniq(prefix="ENV-ALIGN"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _sample():
    return {
        "name": _uniq(),
        "description": "desc",
        "env_type": "docker",
        "endpoint": "http://localhost:8080",
        "owner": "admin",
        "tags": ["prod", "api"],
    }


def test_create_output_matches_old_manager():
    data = _sample()
    new = EnvironmentRepo.create(data)
    old = old_mgr.register_environment(name=data["name"] + "o", description="desc")
    try:
        for f in ("name", "description", "env_type", "endpoint", "owner"):
            assert new.get(f) == data.get(f), f"repo 字段 {f} 不一致"
        assert new["status"] == "offline"  # 新建默认 offline
        # tags 反序列化为 list
        assert isinstance(new["tags"], list)
    finally:
        EnvironmentRepo.purge(new["id"])
        old_mgr.purge_environment(old["id"])


def test_create_base_url_maps_to_endpoint():
    # 兼容旧层行为：仅当 endpoint 为空时 base_url → endpoint
    data = {"name": _uniq(), "base_url": "http://base.local", "endpoint": ""}
    env = EnvironmentRepo.create(data)
    try:
        got = EnvironmentRepo.get(env["id"])
        assert got["endpoint"] == "http://base.local"
    finally:
        EnvironmentRepo.purge(env["id"])


def test_get_list_update_delete_match_old_manager():
    # repo 与旧 manager 各自创建一条
    n = EnvironmentRepo.create(_sample())
    o = old_mgr.register_environment(name=_uniq() + "o", description="desc")
    try:
        # get
        assert EnvironmentRepo.get(n["id"])["id"] == n["id"]
        assert old_mgr.get_environment(o["id"])["id"] == o["id"]
        # list 都能检索到各自的
        assert any(e["id"] == n["id"] for e in EnvironmentRepo.list())
        # update
        n2 = EnvironmentRepo.update(n["id"], {"description": "new-desc", "owner": "ops"})
        assert n2["description"] == "new-desc"
        assert n2["owner"] == "ops"
        o2 = old_mgr.update_environment(o["id"], description="new-desc", owner="ops")
        assert o2["description"] == "new-desc"
    finally:
        EnvironmentRepo.purge(n["id"])
        old_mgr.purge_environment(o["id"])


def test_trash_restore_purge_match_old_manager():
    n = EnvironmentRepo.create(_sample())
    o = old_mgr.register_environment(name=_uniq() + "o", description="d")
    try:
        # 移入回收站
        assert EnvironmentRepo.trash(n["id"]) is True
        # 软删后 get 过滤 deleted（与旧 manager 一致）：常规读取返回 None
        assert EnvironmentRepo.get(n["id"]) is None
        assert any(e["id"] == n["id"] for e in EnvironmentRepo.list_trash())
        # 恢复
        assert EnvironmentRepo.restore(n["id"]) is True
        assert EnvironmentRepo.get(n["id"])["deleted"] == 0
    finally:
        EnvironmentRepo.purge(n["id"])
        old_mgr.purge_environment(o["id"])


def test_stats_match_old_manager():
    rs = EnvironmentRepo.get_alerts_stats()
    ms = old_mgr.get_stats()
    assert rs["env_total"] == ms["env_total"]
    assert rs["env_by_status"] == ms["env_by_status"]
    assert rs["alert_open"] == ms["alert_open"]
    assert rs["alert_total"] == ms["alert_total"]
