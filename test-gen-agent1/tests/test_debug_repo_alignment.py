"""调试域去空壳化：DebugRepo 直连 SQL 行为回归测试
================================================================
目的：debug_items 为独立调试小域，`DebugRepo` 是 debug_items 表唯一
数据访问入口（Router → DebugService → DebugRepo 直连 SQLite）。
本测试锁定 repo 的写入 / 全量读取 / 删除、以及 snake_case → camelCase
归一化语义（含 request_data/response_data 的 JSON 解析），确保
「保存即落库、重启可读回」的持久化保证不被破坏。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.debug_repo import DebugRepo  # noqa: E402
from app.services.debug_service import DebugService  # noqa: E402


def _item():
    """构造一条完整 camelCase 调试项。"""
    return {
        "id": "dbg-align-%s" % uuid.uuid4().hex[:8],
        "name": "调试项-对齐",
        "protocol": "HTTP",
        "method": "POST",
        "path": "/api/align",
        "url": "/api/align",
        "projectId": "proj-align",
        "moduleId": "mod-root",
        "request": {"payload": {"k": "v"}},
        "response": {"code": 0},
        "createUser": "admin",
        "updateUser": "admin",
        "num": 1,
    }


def _cleanup(dbg_id):
    try:
        DebugRepo.delete(dbg_id)
    except Exception:
        pass


def test_save_then_load_roundtrip_persists():
    item = _item()
    DebugRepo.ensure_table()
    DebugRepo.save(item)
    try:
        rows = DebugRepo.load_all()
        found = [x for x in rows if x["id"] == item["id"]]
        assert len(found) == 1, "save 后应能从 DB 读回该调试项"
        got = found[0]
        # 归一化为 camelCase 输出
        for f in ("projectId", "moduleId", "request", "response", "createUser"):
            assert f in got, f"归一化输出缺字段 {f}"
        assert got["request"] == {"payload": {"k": "v"}}
        assert got["response"] == {"code": 0}
        assert got["name"] == item["name"]
    finally:
        _cleanup(item["id"])


def test_service_save_delete_persists_through_repo():
    svc = DebugService()
    item = _item()
    svc.save(item)
    try:
        # 经 service 缓存命中
        assert svc.has(item["id"]) is True
        assert svc.get(item["id"])["name"] == item["name"]
        # repo 层亦已真实落库
        rows = DebugRepo.load_all()
        assert any(x["id"] == item["id"] for x in rows)
        # 删除同时清空内存与 DB
        assert svc.delete(item["id"]) is True
        assert svc.has(item["id"]) is False
        assert not any(x["id"] == item["id"] for x in DebugRepo.load_all())
    finally:
        _cleanup(item["id"])


def test_delete_removes_db_row():
    item = _item()
    DebugRepo.save(item)
    assert any(x["id"] == item["id"] for x in DebugRepo.load_all())
    DebugRepo.delete(item["id"])
    assert not any(x["id"] == item["id"] for x in DebugRepo.load_all())


def test_invalid_json_request_degrades_to_empty_dict():
    """request_data/response_data 若存了非法 JSON，归一化应退化为 {}。"""
    # 直接构造含非法 JSON 的裸行
    conn = DebugRepo.get_conn()
    item = _item()
    conn.execute(
        "INSERT OR REPLACE INTO debug_items "
        "(id, name, request_data, response_data) VALUES (?, ?, ?, ?)",
        (item["id"], "bad-json", "not-json{{", "also-bad"),
    )
    conn.commit()
    try:
        rows = DebugRepo.load_all()
        found = [x for x in rows if x["id"] == item["id"]]
        assert found and found[0]["request"] == {} and found[0]["response"] == {}
    finally:
        _cleanup(item["id"])
