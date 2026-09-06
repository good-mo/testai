"""DDD export_task 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/export_task/` DDD 层就绪后，本测试锁定阶段 C 薄门面接线契约：
`app/services/export_task_service.py` 已收敛为对 `export_task_app_service`
的**薄委托门面**，5 个模块级函数（register_task / get_task / remove_task /
active_task / wait_task）全部经 DDD 应用门面；对外函数签名与返回 schema 与
重构前一致（进程内任务注册表读写语义零变化，functional_export_service /
websocket 调用方零改动）。

本测试以 Service 为界验证「接线后行为与旧契约一致」，并断言确实走 DDD 门面。
"""
import uuid

from app.domain.export_task.application.dto import (
    GetTaskCommand,
    RegisterTaskCommand,
    RemoveTaskCommand,
)
from app.domain.export_task.application.export_task_app_service import (
    export_task_app_service as ddd,
)
from app.services.export_task_service import (
    active_task,
    get_task,
    register_task,
    remove_task,
    wait_task,
)


def _fid():
    return f"expdd-{uuid.uuid4().hex[:8]}"


def _clean(file_id):
    try:
        ddd.remove(RemoveTaskCommand(file_id=file_id))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_register_get_remove_delegate_to_ddd(monkeypatch):
    """register/get/remove 委托 DDD app_service，参数经 DTO 翻译。"""
    file_id = _fid()
    seen = []
    orig_register, orig_get, orig_remove = ddd.register, ddd.get, ddd.remove

    def fake_register(cmd):
        assert isinstance(cmd, RegisterTaskCommand)
        seen.append(("register", cmd.file_id, cmd.count))
        return orig_register(cmd)

    def fake_get(cmd):
        assert isinstance(cmd, GetTaskCommand)
        seen.append(("get", cmd.file_id))
        return orig_get(cmd)

    def fake_remove(cmd):
        assert isinstance(cmd, RemoveTaskCommand)
        seen.append(("remove", cmd.file_id))
        return orig_remove(cmd)

    monkeypatch.setattr(ddd, "register", fake_register)
    monkeypatch.setattr(ddd, "get", fake_get)
    monkeypatch.setattr(ddd, "remove", fake_remove)
    try:
        register_task(file_id, "t1", "/tmp/a.csv", "a.csv", 5)
        assert ("register", file_id, 5) in seen
        assert get_task(file_id)["fileId"] == file_id
        assert ("get", file_id) in seen
        remove_task(file_id)
        assert ("remove", file_id) in seen
    finally:
        _clean(file_id)


def test_active_task_delegates_to_ddd_latest(monkeypatch):
    """active_task 委托 DDD latest。"""
    file_id = _fid()
    called = []
    orig_latest = ddd.latest

    def fake_latest():
        called.append(1)
        return orig_latest()

    monkeypatch.setattr(ddd, "latest", fake_latest)
    try:
        register_task(file_id, "t1", "/p", "f.csv", 2)
        res = active_task()
        assert called == [1]
        assert res is not None and res["fileId"] == file_id
    finally:
        _clean(file_id)


# ═══════════════════════════════════════════════════════════
# 二、端到端契约一致（注册→读取→轮询→移除）
# ═══════════════════════════════════════════════════════════
def test_end_to_end_register_get_wait_remove():
    """真实走 DDD 门面：register → get → wait_task → remove 语义零变化。"""
    file_id = _fid()
    try:
        r = register_task(file_id, "task-xyz", "/tmp/o.csv", "o.csv", 4)
        assert r["fileId"] == file_id
        assert r["taskId"] == "task-xyz"
        assert r["filename"] == "o.csv"
        assert r["count"] == 4
        assert r["is_successful"] is True

        g = get_task(file_id)
        assert g["fileId"] == file_id
        assert g["taskId"] == "task-xyz"

        w = wait_task(file_id, timeout=0.5, interval=0.05)
        assert w and w["fileId"] == file_id

        remove_task(file_id)
        assert get_task(file_id) is None
        assert wait_task(file_id, timeout=0.05, interval=0.01) is None
    finally:
        _clean(file_id)


def test_register_missing_fields_defaults():
    """旧契约下可只传 file_id（其余字段默认），委托后仍成立。"""
    file_id = _fid()
    try:
        r = register_task(file_id, "", "", "", 0, True)
        assert r["fileId"] == file_id
        assert r["count"] == 0
        assert r["is_successful"] is True
    finally:
        _clean(file_id)
