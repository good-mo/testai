"""fake_error 域下沉：fake_error_repo / fake_error_service 行为回归测试
====================================================================
目的：误报规则（错误注入）数据访问统一收敛于
  - app.repositories.fake_error_repo（数据访问唯一权威，直连 SQLite）
  - app.services.fake_error_service（router 唯一业务入口）

原兼容门面 app.projects.fake_error_store 已删除，本测试直接 import repo，
锁定 fake_error 域「新增 → 列表 → 更新 → 启用计数 → 启停 → 删除」
全链路落库语义，确保 service/repo 输出零回归，
「保存即落库、重启可读回」的持久化保证不被破坏。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories import fake_error_repo  # noqa: E402
from app.services.fake_error_service import FakeErrorService  # noqa: E402

service = FakeErrorService()


def _pid():
    """生成唯一 project_id，隔离各用例数据。"""
    return f"fer-align-{uuid.uuid4().hex[:8]}"


def _cleanup(pid):
    """清理本用例新增的规则。"""
    for it in fake_error_repo.list_rules(pid):
        fake_error_repo.delete_rules([it["id"]])


def test_add_list_roundtrip_and_enabled_count():
    """新增规则后可列表读回、启用计数正确，service 与旧门面一致。"""
    pid = _pid()
    try:
        created = service.add_rules([
            {
                "name": "规则A", "type": ["L1", "L2"],
                "respType": "RESPONSE_CODE", "relation": "EQUALS",
                "expression": "500", "enable": True,
            },
            {
                "name": "规则B", "type": "L3",
                "respType": "RESPONSE_DATA", "relation": "CONTAINS",
                "expression": "error", "enable": False,
            },
        ], pid)
        assert len(created) == 2
        # 列表读回
        items = service.list_rules(pid)
        assert len(items) == 2
        by_name = {s["name"]: s for s in items}
        a = by_name["规则A"]
        assert a["projectId"] == pid
        assert a["enable"] is True
        assert a["typeList"] == ["L1", "L2"]
        assert a["respType"] == "RESPONSE_CODE"
        assert a["relation"] == "EQUALS"
        assert a["expression"] == "500"
        assert a["ruleResult"] == "Response Code 等于 500"
        b = by_name["规则B"]
        assert b["enable"] is False
        assert b["ruleResult"] == "Response Data 包含 error"
        # 启用计数：只有 规则A 启用
        assert service.get_enabled_count(pid) == 1
        # repo 视角一致
        old_items = fake_error_repo.list_rules(pid)
        assert len(old_items) == 2
    finally:
        _cleanup(pid)


def test_update_enable_delete_flow():
    """更新规则内容 / 启停 / 删除均落库读回。"""
    pid = _pid()
    try:
        created = service.add_rules([
            {"name": "原始", "type": "T1", "respType": "RESPONSE_CODE",
             "relation": "EQUALS", "expression": "200", "enable": True},
        ], pid)
        rid = created[0]["id"]
        # 更新
        upd = service.update_rules([
            {"id": rid, "name": "改名", "type": "T2",
             "respType": "RESPONSE_HEADERS", "relation": "START_WITH",
             "expression": "X-Token", "enable": True},
        ])
        assert len(upd) == 1
        assert upd[0]["name"] == "改名"
        assert upd[0]["respType"] == "RESPONSE_HEADERS"
        assert upd[0]["ruleResult"] == "Response Headers 开始于 X-Token"
        # 启停
        service.update_enable([rid], False)
        items = service.list_rules(pid)
        assert items[0]["enable"] is False
        assert service.get_enabled_count(pid) == 0
        service.update_enable([rid], True)
        assert service.get_enabled_count(pid) == 1
        # 删除
        service.delete_rules([rid])
        assert service.list_rules(pid) == []
        assert service.get_enabled_count(pid) == 0
    finally:
        _cleanup(pid)

