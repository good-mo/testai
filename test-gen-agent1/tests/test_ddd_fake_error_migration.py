"""DDD fake_error 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/fake_error/` DDD 层（阶段 A 就绪）此后已接线：`app/services/
fake_error_service.py` 收敛为对 `fake_error_app_service` 的**薄委托门面**，
对外 6 个方法全部经 DDD 应用门面；返回结构与重构前一致（含 typeList / 中文
ruleResult / updateTime 毫秒契约，ruleResult 由域内枚举派生，round-trip
create_user/update_time 不丢字段），router/compat 零改动。

并锁定两处历史骨架缺陷的修复：
  ① `FakeErrorRule` to_dict 此前缺 typeList/updateTime，ruleResult 未按枚举
     派生，update_time 未 round-trip（读回时间漂移）；
  ② `FakeErrorRepoAdapter.save` 未传 createUser/ruleResult。

本测试以 Service 为界验证「接线后行为与旧契约一致」，并断言确实走 DDD 门面。
"""
import uuid

from app.domain.fake_error.application.fake_error_app_service import (
    fake_error_app_service as ddd,
)
from app.repositories import fake_error_repo
from app.services.fake_error_service import FakeErrorService

svc = FakeErrorService()


def _pid():
    return f"fe-ddd-{uuid.uuid4().hex[:8]}"


def _cleanup(pid):
    for it in fake_error_repo.list_rules(pid):
        fake_error_repo.delete_rules([it["id"]])


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_service_delegates_to_ddd_list_and_count(monkeypatch):
    """list_rules / get_enabled_count 委托 DDD app_service。"""
    pid = _pid()
    calls = []

    def fake_list(cmd):
        calls.append(("list", cmd.project_id))
        return []

    def fake_count(project_id):
        calls.append(("get_enabled_count", project_id))
        return 0

    monkeypatch.setattr(ddd, "list", fake_list)
    monkeypatch.setattr(ddd, "get_enabled_count", fake_count)
    try:
        assert svc.list_rules(pid) == []
        assert svc.get_enabled_count(pid) == 0
    finally:
        _cleanup(pid)
    assert calls[0][0] == "list"
    assert calls[1][0] == "get_enabled_count"


def test_service_delegates_to_ddd_mutations(monkeypatch):
    """add_rules / update_rules / delete_rules / update_enable 委托 DDD。"""
    pid = _pid()
    calls = []

    def fake_add(cmd):
        calls.append(("add_rules", len(cmd.items), cmd.project_id))
        return []

    def fake_update(cmd):
        calls.append(("update_rules", len(cmd.items)))
        return []

    def fake_delete(cmd):
        calls.append(("delete", list(cmd.ids)))
        return None

    def fake_update_enable(cmd):
        calls.append(("update_enable", list(cmd.ids), cmd.enable))
        return None

    monkeypatch.setattr(ddd, "add_rules", fake_add)
    monkeypatch.setattr(ddd, "update_rules", fake_update)
    monkeypatch.setattr(ddd, "delete", fake_delete)
    monkeypatch.setattr(ddd, "update_enable", fake_update_enable)
    try:
        assert svc.add_rules([{"name": "x"}], pid) == []
        assert svc.update_rules([{"id": "r1"}]) == []
        assert svc.delete_rules(["r1"]) is None
        assert svc.update_enable(["r1"], True) is None
    finally:
        _cleanup(pid)
    assert calls[0][0] == "add_rules" and calls[0][2] == pid
    assert calls[1][0] == "update_rules"
    assert calls[2][0] == "delete"
    assert calls[3][0] == "update_enable" and calls[3][2] is True


# ═══════════════════════════════════════════════════════════
# 二、round-trip 契约保持：typeList / 中文 ruleResult / updateTime
# ═══════════════════════════════════════════════════════════
def test_add_list_roundtrip_contract():
    """新增→列表读回，typeList / 中文 ruleResult / enable / updateTime 均保持。"""
    pid = _pid()
    try:
        created = svc.add_rules([
            {"name": "规则A", "type": ["L1", "L2"],
             "respType": "RESPONSE_CODE", "relation": "EQUALS",
             "expression": "500", "enable": True},
            {"name": "规则B", "type": "L3",
             "respType": "RESPONSE_DATA", "relation": "CONTAINS",
             "expression": "error", "enable": False},
        ], pid)
        assert len(created) == 2
        # created 返回即含完整契约
        by_name = {c["name"]: c for c in created}
        assert by_name["规则A"]["typeList"] == ["L1", "L2"]
        assert by_name["规则A"]["ruleResult"] == "Response Code 等于 500"
        assert by_name["规则A"]["projectId"] == pid
        assert by_name["规则A"]["updateTime"] > 0
        assert by_name["规则B"]["enable"] is False
        # 列表读回一致
        items = svc.list_rules(pid)
        items_by_name = {s["name"]: s for s in items}
        a = items_by_name["规则A"]
        assert a["typeList"] == ["L1", "L2"]
        assert a["ruleResult"] == "Response Code 等于 500"
        assert a["enable"] is True
        assert a["updateTime"] > 0
        # updateTime 为持久化毫秒（round-trip 不丢时间字段）
        assert a["updateTime"] == by_name["规则A"]["updateTime"]
        assert svc.get_enabled_count(pid) == 1
    finally:
        _cleanup(pid)


def test_update_enable_delete_full_flow():
    """更新 / 启停 / 删除 全链路落库读回，契约保持。"""
    pid = _pid()
    try:
        created = svc.add_rules([
            {"name": "原始", "type": "T1", "respType": "RESPONSE_CODE",
             "relation": "EQUALS", "expression": "200", "enable": True},
        ], pid)
        rid = created[0]["id"]
        # 更新：字段与 ruleResult 随枚举派生
        upd = svc.update_rules([
            {"id": rid, "name": "改名", "type": "T2",
             "respType": "RESPONSE_HEADERS", "relation": "START_WITH",
             "expression": "X-Token", "enable": True},
        ])
        assert len(upd) == 1
        assert upd[0]["name"] == "改名"
        assert upd[0]["type"] == "T2"
        assert upd[0]["ruleResult"] == "Response Headers 开始于 X-Token"
        got = svc.list_rules(pid)[0]
        assert got["ruleResult"] == "Response Headers 开始于 X-Token"
        # 启停
        svc.update_enable([rid], False)
        assert svc.list_rules(pid)[0]["enable"] is False
        assert svc.get_enabled_count(pid) == 0
        svc.update_enable([rid], True)
        assert svc.get_enabled_count(pid) == 1
        # 删除
        svc.delete_rules([rid])
        assert svc.list_rules(pid) == []
    finally:
        _cleanup(pid)
