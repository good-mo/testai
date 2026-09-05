"""DDD debug 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/debug/` DDD 层就绪后，`app/services/debug_service.py` 收敛为对
`debug_app_service` 的薄委托门面（initialize / get / has / all_items /
next_num / save / delete），对外 camelCase 契约与调用方（debug_compat /
gap_fixes）一致。

验证：
  1. service 确实委托 DDD 门面（save/get/delete 落库经 DDD 应用服务）；
  2. 经 service 落库后能回读，删除后清空；
  3. 编辑（如拖拽改 moduleId）round-trip 无损；
  4. 与既有 DebugService 直连 DebugRepo 的持久化语义一致。
"""
import uuid

from app.domain.debug.application.debug_app_service import debug_app_service as ddd
from app.services.debug_service import DebugService
from app.services.debug_service import debug_service as svc


def _dbg_id():
    return f"dbg-ddd-{uuid.uuid4().hex[:8]}"


def _cleanup(did):
    if did:
        try:
            svc.delete(did)
        except Exception:
            pass


def _item(did):
    return {
        "id": did,
        "name": "调试项-接线",
        "protocol": "HTTP",
        "method": "POST",
        "path": "/api/x",
        "url": "/api/x",
        "projectId": "proj-1",
        "moduleId": "mod-root",
        "request": {"payload": {"k": "v"}},
        "response": {"code": 0},
        "createUser": "admin",
        "updateUser": "admin",
        "num": 1,
    }


def test_service_delegates_save_to_ddd(monkeypatch):
    """save 委托 DDD app_service（落库经 DDD 门面）。"""
    did = _dbg_id()
    called = []

    def fake_save(cmd):
        called.append((cmd.debug_id, cmd.name))
        return ddd.save(cmd)

    monkeypatch.setattr(ddd, "save", fake_save)
    try:
        svc.save(_item(did))
        assert called and called[0][0] == did
    finally:
        _cleanup(did)


def test_service_delegates_get_delete_to_ddd(monkeypatch):
    """get/delete 委托 DDD app_service。"""
    did = _dbg_id()
    svc.save(_item(did))
    gc, dc = [], []
    real_get = ddd.get
    real_delete = ddd.delete

    def fake_get(cmd):
        gc.append(cmd.debug_id)
        return real_get(cmd)

    def fake_delete(cmd):
        dc.append(cmd.debug_id)
        return real_delete(cmd)

    monkeypatch.setattr(ddd, "get", fake_get)
    monkeypatch.setattr(ddd, "delete", fake_delete)
    try:
        # 清空 store 缓存迫使 get 走 DDD
        fresh = DebugService()
        fresh._store.clear()
        fresh.get(did)
        fresh.delete(did)
        assert gc == [did]
        assert dc == [did]
    finally:
        _cleanup(did)


def test_save_get_delete_roundtrip_via_service():
    """经 service（DDD 门面）落库 → 回读 → 删除闭环。"""
    did = _dbg_id()
    svc.save(_item(did))
    try:
        assert svc.has(did) is True
        got = svc.get(did)
        assert got and got["name"] == "调试项-接线"
        assert got["projectId"] == "proj-1"
        assert got["request"] == {"payload": {"k": "v"}}
        # 从 DB 直查确认真实落盘
        from app.repositories.debug_repo import DebugRepo
        rows = DebugRepo.load_all()
        assert any(x["id"] == did for x in rows)
        assert svc.delete(did) is True
        assert svc.has(did) is False
        assert not any(x["id"] == did for x in DebugRepo.load_all())
    finally:
        _cleanup(did)


def test_edit_module_id_roundtrip_preserved():
    """编辑场景（拖拽改 moduleId）round-trip 不丢。"""
    did = _dbg_id()
    svc.save(_item(did))
    try:
        item = dict(svc.get(did))
        item["moduleId"] = "mod-other"
        svc.save(item)
        got = svc.get(did)
        assert got["moduleId"] == "mod-other"
        assert got["name"] == "调试项-接线"
    finally:
        _cleanup(did)
