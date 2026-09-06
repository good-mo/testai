"""资源池域去空壳化：ResourcePoolRepo 直连 SQL 行为回归测试
================================================================
目的：resource_pools 为独立小域，`ResourcePoolRepo` 是唯一数据访问入口
（Router → ResourcePoolService → ResourcePoolRepo → Database 直连 SQL）。
本测试锁定该 repo 的 CRUD / 关键字检索 / 启停开关的真实落库语义，
确保后续 Router/Service 改动不会破坏「建了即用、数据真正落库」的保证。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.resource_pool_repo import ResourcePoolRepo  # noqa: E402
from app.services.resource_pool_service import ResourcePoolService  # noqa: E402

service = ResourcePoolService()


def _uniq(prefix="RP-ALIGN"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_create_persists_and_returns_id():
    name = _uniq()
    created = ResourcePoolRepo.create(name=name, description="desc-1", enable=True)
    assert created.get("id"), "create 应返回新资源池 id"
    try:
        row = ResourcePoolRepo.get_by_id(created["id"])
        assert row is not None
        assert row["name"] == name
        assert row["description"] == "desc-1"
        assert row["enable"] == 1
        assert row["created_at"] and row["updated_at"]
    finally:
        ResourcePoolRepo.delete(created["id"])


def test_service_create_matches_repo():
    name = _uniq()
    via_svc = service.create(name=name, description="svc-desc")
    via_repo = ResourcePoolRepo.create(name=_uniq(), description="repo-desc")
    try:
        got = service.get(via_svc["id"])
        assert got["name"] == name
        assert got["description"] == "svc-desc"
    finally:
        service.delete(via_svc["id"])
        ResourcePoolRepo.delete(via_repo["id"])


def test_get_all_and_keyword_search():
    name = _uniq("SEARCH")
    pid = ResourcePoolRepo.create(name=name, description="kw-target")["id"]
    try:
        all_rows = ResourcePoolRepo.get_all()
        assert any(p["id"] == pid for p in all_rows)
        hits = ResourcePoolRepo.get_all(keyword=name)
        assert any(p["id"] == pid for p in hits)
        miss = ResourcePoolRepo.get_all(keyword="zzz-not-exist-" + uuid.uuid4().hex)
        assert all(p["id"] != pid for p in miss)
    finally:
        ResourcePoolRepo.delete(pid)


def test_update_only_whitelisted_fields():
    pid = ResourcePoolRepo.create(name=_uniq(), description="old", enable=True)["id"]
    try:
        # enable 由 1 -> 0 需经 bool 归一化
        ok = ResourcePoolRepo.update(pid, {"description": "new-desc", "enable": False})
        assert ok is True
        row = ResourcePoolRepo.get_by_id(pid)
        assert row["description"] == "new-desc"
        assert row["enable"] == 0
        # 非白名单字段不落库
        ResourcePoolRepo.update(pid, {"unknown_col": "should-ignore"})
        row2 = ResourcePoolRepo.get_by_id(pid)
        assert row2["description"] == "new-desc"
    finally:
        ResourcePoolRepo.delete(pid)


def test_set_enable_toggle():
    pid = ResourcePoolRepo.create(name=_uniq(), enable=True)["id"]
    try:
        ResourcePoolRepo.set_enable(pid, False)
        assert ResourcePoolRepo.get_by_id(pid)["enable"] == 0
        ResourcePoolRepo.set_enable(pid, True)
        assert ResourcePoolRepo.get_by_id(pid)["enable"] == 1
    finally:
        ResourcePoolRepo.delete(pid)


def test_delete_removes_row():
    pid = ResourcePoolRepo.create(name=_uniq(), description="to-delete")["id"]
    assert ResourcePoolRepo.get_by_id(pid) is not None
    assert ResourcePoolRepo.delete(pid) is True
    assert ResourcePoolRepo.get_by_id(pid) is None
    # 二次删除返回 False（rowcount=0）
    assert ResourcePoolRepo.delete(pid) is False
