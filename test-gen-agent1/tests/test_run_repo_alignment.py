"""
运行记录 Repository 功能回归测试
=====================================
RunRepo 已收敛为 run_records 表数据访问唯一权威（旧 app.runs.repository
兼容门面已删除）。本测试直接验证 RunRepo 的保存 / 读取 / 列表 / 统计 /
清空功能形态稳定。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.run_repo import RunRepo  # noqa: E402


def _uniq(prefix="RUN"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(record_ids):
    for rid in record_ids:
        try:
            RunRepo._get_conn().execute(
                "DELETE FROM run_records WHERE id = ?", (rid,))
        except Exception:
            pass


def test_save_and_get():
    """保存记录后可读取，字段输出形态稳定。"""
    r1 = RunRepo.save(file_path=_uniq(), source="single",
                      test_result={"passed": True, "total": 3})
    ids = [r1["id"]]
    try:
        got = RunRepo.get(r1["id"])
        assert got is not None
        assert got["file_path"] == r1["file_path"]
        assert got["test_result"]["passed"] is True
    finally:
        _cleanup(ids)


def test_list_count():
    """列表与计数按过滤条件正确。"""
    base_path = _uniq()
    ids = []
    for i in range(3):
        rec = RunRepo.save(file_path=f"{base_path}-{i}", source="single",
                           test_result={"passed": i % 2 == 0})
        ids.append(rec["id"])
    try:
        rows = RunRepo.list_records(file_path=base_path, limit=10)
        assert len(rows) == 3
        assert RunRepo.count_records(file_path=base_path) == 3
        assert RunRepo.count_records(file_path=base_path, passed=True) == 2
        assert RunRepo.count_records(file_path=base_path, passed=False) == 1
    finally:
        _cleanup(ids)


def test_stats_and_clear():
    """统计输出字段稳定；clear 清空正常。"""
    RunRepo.save(file_path=_uniq(), source="single",
                 test_result={"passed": True})
    s = RunRepo.stats()
    assert s["total"] >= 1
    assert "passed" in s and "failed" in s
    assert "by_source" in s and "avg_coverage" in s
    # clear 后计数归零
    RunRepo.clear()
    assert RunRepo.count_records() == 0
