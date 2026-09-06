"""
接口测试域模块树下沉：ApitestRepo（Repository 层）与旧 module_store 对齐回归
================================================================================
目的：模块树纯数据访问（增删改查 / 级联删除 / 事务移动 / 计数）SQL 已从旧
app.apitest.module_store 下沉到 app.repositories.apitest_repo.ApitestRepo，
本测试验证 Repository 层直连 SQL 输出与既有 module_store 对外行为完全一致，
即把 Repository 从「委托空壳」下沉为直连 SQL 后仍零回归。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.apitest import module_store as old_store  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.repositories.apitest_repo import ApitestRepo  # noqa: E402


def _uniq(prefix="MOD"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(scope, mid=None):
    conn = Database.get_conn("apitest.db")
    if mid:
        conn.execute("DELETE FROM modules WHERE id=?", (mid,))
    else:
        conn.execute("DELETE FROM modules WHERE scope=?", (scope,))
    conn.commit()


def test_add_get_list_alignment():
    """新增/查询/列表：Repository 与旧 module_store 行为一致。"""
    scope = _uniq("sc")
    mid = None
    try:
        old = old_store.add_module(scope, name=_uniq("A"), project_id="p1")
        mid = old["id"]
        # get 一致性
        assert ApitestRepo.get_module(mid) == old_store.get_module(mid)
        # 列表包含
        assert any(x["id"] == mid for x in ApitestRepo.list_modules(scope, project_id="p1"))
        assert any(x["id"] == mid for x in old_store.list_modules(scope, project_id="p1"))
    finally:
        _cleanup(scope, mid)


def test_update_delete_alignment():
    """更新返回 bool / 级联删除：两边行为一致。"""
    scope = _uniq("sc")
    parent = None
    child = None
    try:
        parent = old_store.add_module(scope, name=_uniq("parent"), project_id="p1")
        child = old_store.add_module(scope, name=_uniq("child"),
                                     parent_id=parent["id"], project_id="p1")
        # 通过 Repository 更新
        assert ApitestRepo.update_module(parent["id"], name=_uniq("p2")) is True
        # 更新不存在的模块返回 False
        assert ApitestRepo.update_module(_uniq("nope"), name="x") is False
        # 删除父级应级联删除子级（两边一致）
        assert ApitestRepo.delete_module(parent["id"]) is True
        assert old_store.get_module(parent["id"]) is None
        assert old_store.get_module(child["id"]) is None
    finally:
        _cleanup(scope, parent.get("id") if parent else None)


def test_move_module_alignment():
    """移动模块到 drop 之后：pos 与父级一致。"""
    scope = _uniq("sc")
    try:
        a = old_store.add_module(scope, name=_uniq("a"), project_id="p1")
        old_store.add_module(scope, name=_uniq("b"), project_id="p1")
        c = old_store.add_module(scope, name=_uniq("c"), project_id="p1")
        # 通过 Repository 把 a 移到 c 之后
        assert ApitestRepo.move_module(a["id"], c["id"], drop_position=1) is True
        # 两边读到的顺序应一致
        order_new = [x["id"] for x in ApitestRepo.list_modules(scope, project_id="p1")]
        order_old = [x["id"] for x in old_store.list_modules(scope, project_id="p1")]
        assert order_new == order_old
    finally:
        _cleanup(scope)


def test_count_alignment():
    """计数：Repository 与旧 module_store 一致。"""
    scope = _uniq("sc")
    try:
        old_store.add_module(scope, name=_uniq("x"), project_id="p1")
        assert ApitestRepo.count_modules(scope) == old_store.count_modules(scope)
    finally:
        _cleanup(scope)
