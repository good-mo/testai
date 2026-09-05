"""DDD resource_pool / user_view 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/resource_pool/` 与 `app/domain/user_view/` DDD 层（阶段 A）此前是
分层齐全却从未被生产引用的「未接线骨架」。issue #708 选定 Option A「接死为活」，
本测试锁定 Round 2 的阶段 C 薄门面接线契约：
  - `app/services/resource_pool_service.py` 收敛为对 `resource_pool_app_service`
    的薄委托门面，对外方法签名与返回结构（router 消费的 snake_case DB 行）不变；
  - `app/services/user_view_service.py` 收敛为对 `user_view_app_service` 的薄委托
    门面，返回完整前端视图对象（含 id/viewType 等 meta，不再丢字段）。

并锁定两处历史缺陷的修复：
  ① resource_pool：`ResourcePoolRepoAdapter.save` 新建不再忽略聚合 id
     → 创建返回的 id 与落库 id 一致；
  ② user_view：`UserView.to_dict()` 不再只返回 payload 丢失 id/type
     → add/list/get/update 读回完整视图对象，update 合并且自定义字段保留。

本测试以 Service 为界验证接线后行为与旧契约一致，作为逐域切换回归基线。
"""
import uuid

from app.domain.resource_pool.application.resource_pool_app_service import (
    resource_pool_app_service as rp_ddd,
)
from app.domain.user_view.application.user_view_app_service import (
    user_view_app_service as uv_ddd,
)
from app.repositories.resource_pool_repo import ResourcePoolRepo
from app.repositories.user_view_repo import user_view_repo
from app.services.resource_pool_service import resource_pool_service as rp_svc
from app.services.user_view_service import user_view_service as uv_svc


def _uid(prefix="DDD-RPUV"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 一、resource_pool：薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_resource_pool_service_delegates_to_ddd(monkeypatch):
    """create/get/list/delete/set_enable 均委托 resource_pool_app_service。"""
    pid = _uid()
    calls = []

    def fake_create(cmd):
        calls.append(("create", cmd.name))
        return {"id": pid}

    def fake_list(cmd):
        calls.append(("list", cmd.keyword))
        return []

    def fake_get(cmd):
        calls.append(("get", cmd.pool_id))
        return None

    def fake_delete(cmd):
        calls.append(("delete", cmd.pool_id))
        return False

    monkeypatch.setattr(rp_ddd, "create", fake_create)
    monkeypatch.setattr(rp_ddd, "list", fake_list)
    monkeypatch.setattr(rp_ddd, "get", fake_get)
    monkeypatch.setattr(rp_ddd, "delete", fake_delete)
    created = rp_svc.create(name="delegate-pool")
    assert created.get("id") == pid
    assert rp_svc.list("kw") == []
    assert rp_svc.get(pid) is None
    assert rp_svc.delete(pid) is False
    assert calls[0][0] == "create"
    assert calls[1][0] == "list"
    assert calls[2][0] == "get"
    assert calls[3][0] == "delete"


# ═══════════════════════════════════════════════════════════
# 二、resource_pool：创建返回 id == 落库 id（历史缺陷修复）
# ═══════════════════════════════════════════════════════════
def test_resource_pool_create_id_equals_stored_id():
    name = _uid("RP-ID")
    created = rp_svc.create(name=name, description="desc", enable=True)
    pid = created.get("id")
    assert pid, "create 应返回 id"
    try:
        row = ResourcePoolRepo.get_by_id(pid)
        assert row is not None, "按 create 返回 id 应能查到落库行（id 不再漂移）"
        assert row["name"] == name
        # 门面 get 读回（snake_case 契约行）
        got = rp_svc.get(pid)
        assert got and got["id"] == pid and got["name"] == name
        assert "created_at" in got and "updated_at" in got
    finally:
        rp_svc.delete(pid)


def test_resource_pool_facade_behavior_unchanged():
    """create→list/get→update→set_enable→delete 全链路契约保持。"""
    name = _uid("RP-FLOW")
    created = rp_svc.create(name=name, enable=True)
    pid = created["id"]
    try:
        # list 命中（snake 契约行）
        hits = [r for r in rp_svc.list(name) if r["id"] == pid]
        assert len(hits) == 1 and hits[0]["name"] == name
        # update 改 enable + 字段
        assert rp_svc.update(pid, {"name": "renamed", "enable": False}) is True
        got = rp_svc.get(pid)
        assert got["name"] == "renamed"
        assert got["enable"] == 0
        # set_enable 回开
        assert rp_svc.set_enable(pid, True) is True
        assert rp_svc.get(pid)["enable"] == 1
        # update 不存在的资源池返回 False（不抛 5xx）
        assert rp_svc.update("not-exist-" + uuid.uuid4().hex, {"name": "x"}) is False
    finally:
        rp_svc.delete(pid)
        assert rp_svc.get(pid) is None


# ═══════════════════════════════════════════════════════════
# 三、user_view：薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_user_view_service_delegates_to_ddd(monkeypatch):
    """list/get/add/update/delete 均委托 user_view_app_service。"""
    vt, scope = "functional", _uid("UV-DELEGATE")
    calls = []

    def fake_list(cmd):
        calls.append(("list", cmd.view_type, cmd.scope_id))
        return []

    def fake_create(cmd):
        calls.append(("create", cmd.view_type, cmd.scope_id))
        return {"id": "x", "name": "x", "viewType": vt}

    monkeypatch.setattr(uv_ddd, "list_custom_views", fake_list)
    monkeypatch.setattr(uv_ddd, "create", fake_create)
    try:
        assert uv_svc.list_custom_views(vt, scope) == []
        added = uv_svc.add_custom_view(vt, scope, {"name": "x"})
        assert added.get("id") == "x"
    finally:
        # 清理可能残留
        for v in user_view_repo.list_custom_views(vt, scope):
            user_view_repo.delete_custom_view(v["id"])
    assert calls[0][0] == "list"
    assert calls[1][0] == "create"


# ═══════════════════════════════════════════════════════════
# 四、user_view：to_dict 不再丢 id/type，读回完整对象（历史缺陷修复）
# ═══════════════════════════════════════════════════════════
def test_user_view_add_list_get_update_delete_roundtrip():
    vt, scope = "functional", _uid("UV-FLOW")
    add_body = {
        "scopeId": scope,
        "name": "自定义视图",
        "searchMode": "OR",
        "conditions": [{"field": "priority", "operator": "eq", "value": "P1"}],
    }
    # 清理历史残留
    for v in uv_svc.list_custom_views(vt, scope):
        uv_svc.delete_custom_view(v["id"])

    added = uv_svc.add_custom_view(vt, scope, add_body)
    assert added.get("name") == "自定义视图"
    assert added.get("internal") is False
    assert added.get("viewType") == vt and added.get("scopeId") == scope
    vid = added.get("id")
    assert vid, "add 应返回 id（不再只返回 payload 丢 id）"
    try:
        # list 读回
        lst = uv_svc.list_custom_views(vt, scope)
        found = next((v for v in lst if v["id"] == vid), None)
        assert found and found["name"] == "自定义视图"
        assert found["conditions"] == add_body["conditions"]
        # get 详情读回完整字段
        detail = uv_svc.get_custom_view(vid)
        assert detail and detail["name"] == "自定义视图"
        assert detail["searchMode"] == "OR"
        assert detail["conditions"] == add_body["conditions"]
        # update 合并后自定义字段保留
        upd = uv_svc.update_custom_view(vid, {"name": "改名", "searchMode": "AND"})
        assert upd and upd["name"] == "改名" and upd["searchMode"] == "AND"
        assert upd["conditions"] == add_body["conditions"]
        # update 不存在的视图返回 None
        assert uv_svc.update_custom_view("not-exist-" + uuid.uuid4().hex,
                                         {"name": "x"}) is None
        # 独立确认落库（不依赖进程内 dict）
        db_view = user_view_repo.get_custom_view(vid)
        assert db_view and db_view["name"] == "改名"
    finally:
        assert uv_svc.delete_custom_view(vid) is True
        assert uv_svc.get_custom_view(vid) is None


def test_user_view_entity_to_dict_keeps_meta_and_roundtrip():
    """UserView.to_dict 含 meta 字段，from_dict(to_dict) 往返不丢字段。"""
    from app.domain.user_view.domain.entities.user_view import UserView

    v = UserView(
        view_id="uv1", view_type="functional", scope_id="proj",
        name="视图", search_mode="OR", pos=1,
        payload={"conditions": [{"field": "p", "operator": "eq", "value": "P1"}]},
        create_time=1700000000.0, update_time=1700000100.0,
    )
    d = v.to_dict()
    assert d["id"] == "uv1"
    assert d["viewType"] == "functional" and d["scopeId"] == "proj"
    assert d["name"] == "视图"
    assert d["conditions"] == [{"field": "p", "operator": "eq", "value": "P1"}]
    v2 = UserView.from_dict(d)
    assert v2.id.value == "uv1"
    assert v2.name == "视图" and v2.scope_id == "proj"
    assert v2._create_time == 1700000000.0 and v2._update_time == 1700000100.0
    assert v2.payload.get("conditions") == [{"field": "p", "operator": "eq", "value": "P1"}]
