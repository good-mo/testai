"""
数据工厂 Repository 功能回归测试
====================================
DatafactoryRepo 已收敛为 data_templates / data_batches 表数据访问唯一
权威（旧 app.datafactory.repository 兼容门面已删除）。本测试直接验证
DatafactoryRepo 的模板 CRUD / 造数 / 清理 / 统计功能形态稳定。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.datafactory_repo import DatafactoryRepo  # noqa: E402


def _uniq(prefix="DF"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup_template(tid):
    if not tid:
        return
    try:
        DatafactoryRepo._get_conn().execute(
            "DELETE FROM data_templates WHERE id = ?", (tid,))
    except Exception:
        pass


def test_create_get_list():
    """创建模板后可读取 / 列出，字段形态稳定。"""
    t = DatafactoryRepo.create_template(name=_uniq(), category="user",
                                        schema={"field": "value"})
    try:
        got = DatafactoryRepo.get_template(t["id"])
        assert got is not None
        assert got["name"] == t["name"]
        assert got["schema"] == {"field": "value"}
        assert any(x["id"] == t["id"]
                   for x in DatafactoryRepo.list_templates(limit=100))
    finally:
        _cleanup_template(t["id"])


def test_update_delete():
    """更新 / 删除同一模板结果正确。"""
    t = DatafactoryRepo.create_template(name=_uniq())
    tid = t["id"]
    try:
        u1 = DatafactoryRepo.update_template(tid, description="updated")
        assert u1["description"] == "updated"
        DatafactoryRepo.update_template(tid, category="custom")
        assert DatafactoryRepo.get_template(tid)["category"] == "custom"
        assert DatafactoryRepo.delete_template(tid) is True
        assert DatafactoryRepo.get_template(tid) is None
    finally:
        _cleanup_template(tid)


def test_generate_data():
    """按模板造数与清理批次功能正常。"""
    t = DatafactoryRepo.create_template(
        name=_uniq(), category="user",
        schema={
            "username": {"strategy": "sequence", "value": "user_{n}"},
            "email": {"strategy": "fixed", "value": "test@test.com"},
        },
    )
    tid = t["id"]
    try:
        gen1 = DatafactoryRepo.generate_data(tid, batch_size=3)
        assert gen1["batch_size"] == 3
        assert len(gen1["data"]) == 3
        assert len(DatafactoryRepo.list_batches(limit=10)) >= 1
        assert DatafactoryRepo.cleanup_batch(gen1["batch_id"]) is True
    finally:
        _cleanup_template(tid)


def test_stats_consistent():
    """统计输出字段稳定。"""
    s = DatafactoryRepo.stats()
    assert s["template_count"] >= 0
    assert "active_batches" in s
    assert "by_category" in s
