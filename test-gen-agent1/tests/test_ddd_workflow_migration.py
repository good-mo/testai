"""DDD workflow 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/workflow/` DDD 层（阶段 A）此前是分层齐全却从未被生产引用的
「未接线骨架」，`workflow_service` 仍直连 `workflow_repo`（双写旁路仍在）。
本测试锁定 workflow 域的阶段 C 薄门面接线契约：
  - `app/services/workflow_service.py` 收敛为对 `workflow_app_service` 的薄委托
    门面，对外方法签名与返回结构（含 statusFlowTargets、createTime/updateTime
    毫秒）不变，调用方 `project_compat_extra` / `system_compat` 等零改动；
  - 落库语义、播种 / 流转 / 定义标记 / 排序全链路与重构前一致。

并锁定接线前修复的骨架缺陷：
  ① `WorkflowRepoAdapter.save` 新建不再忽略聚合 id
     → 创建返回的 id 与落库 id 一致（此前双 id 漂移，落库根本查不到）；
  ② `WorkflowStatus.to_dict`/`from_dict` 时间口径收敛（内部秒、对外毫秒）且
     透出只读 statusFlowTargets，与前端 WorkFlowType 一致、round-trip 无漂移。
"""
import uuid

from app.domain.workflow.application.workflow_app_service import (
    workflow_app_service as wf_ddd,
)
from app.repositories import workflow_repo
from app.services.workflow_service import workflow_service as wf_svc


def _scope(prefix="DDD-WF"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(scope_type, scope_id, scene):
    for st in workflow_repo.list_statuses(scope_type, scope_id, scene):
        workflow_repo.delete_status(st["id"])


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_service_delegates_to_ddd_app_service(monkeypatch):
    """list/get/add/update/delete/sort/flows/definition/seed 均委托 DDD 门面。"""
    calls = []

    def fake_list(cmd):
        calls.append(("list", cmd.scope_type, cmd.scope_id, cmd.scene))
        return []

    def fake_get(cmd):
        calls.append(("get", cmd.status_id))
        return None

    def fake_create(cmd):
        calls.append(("create", cmd.name))
        return {"id": "s1", "name": cmd.name}

    def fake_update(cmd):
        calls.append(("update", cmd.status_id))
        return {"id": cmd.status_id, "name": "x"}

    def fake_delete(cmd):
        calls.append(("delete", cmd.status_id))
        return True

    def fake_sort(cmd):
        calls.append(("sort", cmd.status_ids))
        return True

    def fake_update_flows(cmd):
        calls.append(("flows", cmd.status_id))
        return True

    def fake_set_def(cmd):
        calls.append(("def", cmd.status_id))
        return True

    def fake_seed(cmd):
        calls.append(("seed", cmd.scope_id))
        return []

    monkeypatch.setattr(wf_ddd, "list", fake_list)
    monkeypatch.setattr(wf_ddd, "get", fake_get)
    monkeypatch.setattr(wf_ddd, "create", fake_create)
    monkeypatch.setattr(wf_ddd, "update", fake_update)
    monkeypatch.setattr(wf_ddd, "delete", fake_delete)
    monkeypatch.setattr(wf_ddd, "sort", fake_sort)
    monkeypatch.setattr(wf_ddd, "update_flows", fake_update_flows)
    monkeypatch.setattr(wf_ddd, "set_definition", fake_set_def)
    monkeypatch.setattr(wf_ddd, "seed_defaults", fake_seed)

    wf_svc.list_statuses("PROJECT", "p", "FUNCTIONAL")
    wf_svc.get_status("s9")
    wf_svc.add_status("n", "FUNCTIONAL", "p", "PROJECT")
    wf_svc.update_status("s1", name="x")
    assert wf_svc.delete_status("s1") is True
    assert wf_svc.sort_statuses(["a", "b"]) is True
    assert wf_svc.update_flows("s1", ["t"]) is True
    assert wf_svc.set_definition("s1", "END", True) is True
    wf_svc.seed_default_statuses("PROJECT", "p", "FUNCTIONAL")

    assert calls[0] == ("list", "PROJECT", "p", "FUNCTIONAL")
    assert calls[1] == ("get", "s9")
    assert calls[2] == ("create", "n")
    assert calls[3] == ("update", "s1")
    assert calls[4] == ("delete", "s1")
    assert calls[5] == ("sort", ["a", "b"])
    assert calls[6] == ("flows", "s1")
    assert calls[7] == ("def", "s1")
    assert calls[8] == ("seed", "p")


# ═══════════════════════════════════════════════════════════
# 二、创建返回 id == 落库 id（历史双 id 漂移缺陷修复）
# ═══════════════════════════════════════════════════════════
def test_add_returns_real_stored_id():
    """service.add 经 DDD 接线后，返回 id 与落库 id 一致。"""
    sid = _scope()
    try:
        added = wf_svc.add_status("评审中", "FUNCTIONAL", sid, "PROJECT", "备注")
        assert added is not None and added["id"]
        stored = workflow_repo.get_status(added["id"])
        assert stored is not None, "落库行应存在（此前双 id 漂移导致查不到）"
        assert stored["id"] == added["id"]
        assert stored["name"] == "评审中"
    finally:
        _cleanup("PROJECT", sid, "FUNCTIONAL")


# ═══════════════════════════════════════════════════════════
# 三、前端契约：statusFlowTargets / 时间毫秒 / 字段齐全
# ═══════════════════════════════════════════════════════════
def test_service_output_contract_preserved():
    """列表/播种输出含 statusFlowTargets 与毫秒时间，字段与旧契约一致。"""
    sid = _scope()
    try:
        seeds = wf_svc.seed_default_statuses("PROJECT", sid, "FUNCTIONAL")
        assert len(seeds) == 3
        for s in seeds:
            for key in ("id", "name", "scene", "remark", "internal", "scopeType",
                        "scopeId", "pos", "statusDefinitions", "statusFlowTargets",
                        "createTime", "updateTime", "createUser"):
                assert key in s, f"状态缺字段 {key}"
            # 时间应为毫秒级别（远大于秒级别的 1e9 上界推断）
            assert isinstance(s["createTime"], int) and s["createTime"] > 1_600_000_000_000
            assert isinstance(s["updateTime"], int) and s["updateTime"] > 1_600_000_000_000
        # 播种建立的流转链在 service 列表输出中可见
        items = wf_svc.list_statuses("PROJECT", sid, "FUNCTIONAL")
        assert items[0]["statusFlowTargets"] == [items[1]["id"]]
        assert items[1]["statusFlowTargets"] == [items[2]["id"]]
        assert items[2]["statusFlowTargets"] == []
    finally:
        _cleanup("PROJECT", sid, "FUNCTIONAL")


def test_update_sort_definitions_roundtrip_persists():
    """新增后改名/定义标记读回，round-trip 无时间漂移。"""
    pid = _scope()
    try:
        wf_svc.seed_default_statuses("PROJECT", pid, "FUNCTIONAL")
        added = wf_svc.add_status("暂缓", "FUNCTIONAL", pid, "PROJECT")
        # 定义标记
        assert wf_svc.set_definition(added["id"], "END", True) is True
        # 改名
        upd = wf_svc.update_status(added["id"], name="暂缓X")
        assert upd["name"] == "暂缓X"
        # 读回：name、END 标记、流转目标
        got = {s["id"]: s for s in wf_svc.list_statuses("PROJECT", pid, "FUNCTIONAL")}
        assert got[added["id"]]["name"] == "暂缓X"
        assert "END" in got[added["id"]]["statusDefinitions"]
        # round-trip 后 createTime 仍为毫秒（不因读→改→存被放大/漂移）
        assert got[added["id"]]["createTime"] > 1_600_000_000_000
    finally:
        _cleanup("PROJECT", pid, "FUNCTIONAL")


# ═══════════════════════════════════════════════════════════
# 四、DDD update 旧语义：空 name 不改名 / 不存在返回 None
# ═══════════════════════════════════════════════════════════
def test_update_empty_name_keeps_name():
    """空 name 更新（只改 remark）不改名，与旧 repo 语义一致。"""
    pid = _scope()
    try:
        wf_svc.seed_default_statuses("PROJECT", pid, "FUNCTIONAL")
        added = wf_svc.add_status("评审中", "FUNCTIONAL", pid, "PROJECT", "备注")
        wf_svc.update_status(added["id"], name="评审中X")
        upd = wf_svc.update_status(added["id"], remark="仅改备注")
        assert upd["name"] == "评审中X"
        assert upd["remark"] == "仅改备注"
    finally:
        _cleanup("PROJECT", pid, "FUNCTIONAL")


def test_update_nonexistent_returns_none():
    """更新不存在的状态返回 None（由门面映射 404），不抛异常。"""
    assert wf_svc.update_status("no-such-id", name="x") is None


# ═══════════════════════════════════════════════════════════
# 五、seed 幂等（重复播种返回既有、不重复插入）
# ═══════════════════════════════════════════════════════════
def test_seed_idempotent():
    oid = _scope()
    try:
        s1 = wf_svc.seed_default_statuses("ORGANIZATION", oid, "BUG")
        s2 = wf_svc.seed_default_statuses("ORGANIZATION", oid, "BUG")
        assert len(s1) == 3 and len(s2) == 3
        assert {s["id"] for s in s1} == {s["id"] for s in s2}
    finally:
        _cleanup("ORGANIZATION", oid, "BUG")


# ═══════════════════════════════════════════════════════════
# 六、START 唯一约束：PROJECT / ORGANIZATION 作用域各自独立
# ═══════════════════════════════════════════════════════════
def test_start_uniqueness_per_scope():
    """对非 PROJECT 作用域设置 START 时仍只保留一个 START（修复 scope 硬编码）。"""
    oid = _scope()
    try:
        wf_svc.seed_default_statuses("ORGANIZATION", oid, "FUNCTIONAL")
        added = wf_svc.add_status("我的开始", "FUNCTIONAL", oid, "ORGANIZATION")
        assert wf_svc.set_definition(added["id"], "START", True) is True
        items = wf_svc.list_statuses("ORGANIZATION", oid, "FUNCTIONAL")
        starts = [s["name"] for s in items if "START" in s["statusDefinitions"]]
        assert starts == ["我的开始"], f"应仅 '我的开始' 为 START，实际 {starts}"
    finally:
        _cleanup("ORGANIZATION", oid, "FUNCTIONAL")
