"""DDD project_app_config 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/project_app_config/` DDD 层（阶段 A 就绪）后，本测试锁定阶段 C
薄门面接线契约：`app/services/project_app_config_service.py` 已收敛为对
`project_app_config_app_service` 的**薄委托门面**，7 个对外方法全部经 DDD
应用门面；对外方法签名与返回 schema 与重构前一致（默认合并 / upsert / 单值
读写语义零变化，routers/compat 零改动）。

本测试以 Service 为界验证「接线后行为与旧契约一致」，并断言确实走 DDD 门面。
"""
import uuid

from app.domain.project_app_config.application.project_app_config_service import (
    project_app_config_app_service as ddd,
)
from app.services.project_app_config_service import project_app_config_service as svc


def _pid():
    return f"pappcfg-ddd-{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_service_delegates_to_ddd_module_config(monkeypatch):
    """get/save_module_config 委托 DDD app_service。"""
    pid = _pid()
    calls = []

    def fake_get(cmd):
        calls.append(("get_module_config", cmd.project_id, cmd.module))
        return ddd._repo.get_module_config(cmd.project_id, cmd.module)

    def fake_save(cmd):
        calls.append(("save_module_config", cmd.project_id, cmd.module))
        return ddd._repo.save_module_config(cmd.project_id, cmd.module, cmd.config)

    monkeypatch.setattr(ddd, "get_module_config", fake_get)
    monkeypatch.setattr(ddd, "save_module_config", fake_save)
    try:
        got = svc.get_module_config(pid, "workstation")
        assert got == {"WORKSTATION_SYNC_RULE": True}
        svc.save_module_config(pid, "workstation", {"WORKSTATION_SYNC_RULE": False})
    finally:
        ddd._repo.set_config_value(pid, "workstation", "WORKSTATION_SYNC_RULE", True)
    assert calls and calls[0][0] == "get_module_config"
    assert any(c[0] == "save_module_config" for c in calls)


def test_service_delegates_to_ddd_all_modules(monkeypatch):
    """get_all_modules 委托 DDD list_all_modules。"""
    pid = _pid()
    called = []

    def fake_list(cmd):
        called.append(cmd.project_id)
        return ddd._repo.get_all_modules(cmd.project_id)

    monkeypatch.setattr(ddd, "list_all_modules", fake_list)
    mods = svc.get_all_modules(pid)
    assert called == [pid]
    modules = {m["module"] for m in mods}
    assert modules == {
        "workstation", "testPlan", "bugManagement", "caseManagement",
        "apiTest", "uiTest", "taskCenter", "loadTest",
    }


def test_service_delegates_to_ddd_project_version_toggle(monkeypatch):
    """projectVersion 启用开关读写委托 DDD app_service。"""
    pid = _pid()
    seen = []

    def fake_enabled(pid_):
        seen.append(("is", pid_))
        return False

    def fake_set(pid_, enabled):
        seen.append(("set", pid_, enabled))

    monkeypatch.setattr(ddd, "is_project_version_enabled", fake_enabled)
    monkeypatch.setattr(ddd, "set_project_version_enabled", fake_set)
    assert svc.is_project_version_enabled(pid) is False
    svc.set_project_version_enabled(pid, True)
    assert ("is", pid) in seen
    assert ("set", pid, True) in seen


def test_service_delegates_to_ddd_generic_rw(monkeypatch):
    """通用单值 get/set_config_value 委托 DDD app_service。"""
    pid = _pid()
    got = []

    def fake_get(cmd):
        got.append(cmd.config_key)
        return ddd._repo.get_config_value(cmd.project_id, cmd.module, cmd.config_key, cmd.default)

    def fake_set(cmd):
        ddd._repo.set_config_value(cmd.project_id, cmd.module, cmd.config_key, cmd.value)

    monkeypatch.setattr(ddd, "get_config_value", fake_get)
    monkeypatch.setattr(ddd, "set_config_value", fake_set)
    svc.set_config_value(pid, "workstation", "DDD_KEY", "v1")
    assert svc.get_config_value(pid, "workstation", "DDD_KEY") == "v1"
    assert "DDD_KEY" in got
    assert ddd._repo.get_config_value(pid, "workstation", "DDD_KEY") == "v1"


# ═══════════════════════════════════════════════════════════
# 二、接线后端到端行为与旧契约一致（默认合并 / 持久化）
# ═══════════════════════════════════════════════════════════
def test_module_config_defaults_merge_after_wiring():
    pid = _pid()
    before = svc.get_module_config(pid, "testPlan")
    assert before["TEST_PLAN_CLEAN_REPORT"] == "3M"
    assert before["TEST_PLAN_SHARE_REPORT"] == "1D"

    saved = svc.save_module_config(pid, "testPlan", {"TEST_PLAN_CLEAN_REPORT": "6M"})
    assert saved["TEST_PLAN_CLEAN_REPORT"] == "6M"
    assert saved["TEST_PLAN_SHARE_REPORT"] == "1D"

    again = svc.get_module_config(pid, "testPlan")
    assert again["TEST_PLAN_CLEAN_REPORT"] == "6M"


def test_boolean_falsy_value_preserved_after_wiring():
    """接线后 falsy 值（False/0/""）正确保留不被 or 吞掉（#711 修复延续）。"""
    pid = _pid()
    # apiTest 默认 API_URL_REPEATABLE=False 等
    cfg = svc.get_module_config(pid, "apiTest")
    assert cfg["API_URL_REPEATABLE"] is False
    # 关闭开关：存 False 读回 False
    svc.save_module_config(pid, "apiTest", {"API_URL_REPEATABLE": False})
    cfg2 = svc.get_module_config(pid, "apiTest")
    assert cfg2["API_URL_REPEATABLE"] is False
    # 空串配置也保留
    svc.set_config_value(pid, "workstation", "EMPTY_FLAG", "")
    assert svc.get_config_value(pid, "workstation", "EMPTY_FLAG") == ""
