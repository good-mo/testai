"""project_app_configs 域下沉：repo / service 行为回归测试
========================================================================
目的：项目应用配置管理数据访问统一收敛于
  - app.repositories.project_app_config_repo（数据访问唯一权威，直连 SQLite）
  - app.services.project_app_config_service（router 唯一业务入口）

原兼容门面 app.projects.application_config 已删除，本测试直接 import repo，
锁定「模块配置读取合并默认 → 保存（upsert）→ 再读回」以及
「projectVersion 版本启用开关读写」的持久化语义，确保 repo / service
输出零回归，「保存即落库、重启可读回」不被破坏。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories import project_app_config_repo as repo  # noqa: E402
from app.services.project_app_config_service import ProjectAppConfigService  # noqa: E402

service = ProjectAppConfigService()


def _pid():
    """生成唯一 project_id，隔离各用例数据。"""
    return f"pappcfg-{uuid.uuid4().hex[:8]}"


def test_module_config_defaults_merge_and_save():
    """读取合并默认值 → 保存覆盖 → 读回持久化值，三入口一致。"""
    pid = _pid()
    # 未保存前读回默认值
    before = service.get_module_config(pid, "testPlan")
    assert before["TEST_PLAN_CLEAN_REPORT"] == "3M"   # 默认
    assert before["TEST_PLAN_SHARE_REPORT"] == "1D"

    # 保存覆盖单个 key
    saved = service.save_module_config(pid, "testPlan", {"TEST_PLAN_CLEAN_REPORT": "6M"})
    assert saved["TEST_PLAN_CLEAN_REPORT"] == "6M"
    assert saved["TEST_PLAN_SHARE_REPORT"] == "1D"    # 未覆盖仍默认

    # 重读（模拟重启读回）持久化
    again = repo.get_module_config(pid, "testPlan")
    assert again["TEST_PLAN_CLEAN_REPORT"] == "6M"

    # repo 视角一致
    old = repo.get_module_config(pid, "testPlan")
    assert old["TEST_PLAN_CLEAN_REPORT"] == "6M"


def test_boolean_and_int_deserialize():
    """布尔/整型默认值经存储读回后类型保持。"""
    pid = _pid()
    cfg = service.get_module_config(pid, "apiTest")
    assert cfg["API_URL_REPEATABLE"] is False
    assert cfg["API_SYNC_CASE"] is False
    assert cfg["ENABLE_FAKE_ERROR_NUM"] == 0

    # 保存布尔值
    service.save_module_config(pid, "apiTest", {"API_URL_REPEATABLE": True})
    cfg2 = service.get_module_config(pid, "apiTest")
    assert cfg2["API_URL_REPEATABLE"] is True


def test_custom_key_persist():
    """非默认自定义 key 也能持久化并读回。"""
    pid = _pid()
    service.save_module_config(pid, "bugManagement", {"CUSTOM_FLAG": "hello"})
    cfg = service.get_module_config(pid, "bugManagement")
    assert cfg.get("CUSTOM_FLAG") == "hello"


def test_get_all_modules_static_list():
    """get_all_modules 返回菜单管理列表（与默认 MODULES 一致）。"""
    pid = _pid()
    mods = service.get_all_modules(pid)
    assert isinstance(mods, list)
    modules = {m["module"] for m in mods}
    assert modules == {
        "workstation", "testPlan", "bugManagement", "caseManagement",
        "apiTest", "uiTest", "taskCenter", "loadTest",
    }
    # repo 视角一致
    assert repo.get_all_modules(pid) == mods


def test_project_version_enable_toggle():
    """projectVersion 启用开关读写：默认关闭 → 开启 → 关闭。"""
    pid = _pid()
    assert service.is_project_version_enabled(pid) is False

    service.set_project_version_enabled(pid, True)
    assert service.is_project_version_enabled(pid) is True

    service.set_project_version_enabled(pid, False)
    assert service.is_project_version_enabled(pid) is False

    # 单值读取一致
    raw = repo.get_config_value(pid, "projectVersion", "enabled")
    assert raw.lower() in ("false", "0", "no")


def test_generic_config_value_read_write():
    """通用 get/set_config_value 支持任意 module/key 读写。"""
    pid = _pid()
    service.set_config_value(pid, "workstation", "EXTRA", "abc")
    assert service.get_config_value(pid, "workstation", "EXTRA") == "abc"
    assert service.get_module_config(pid, "workstation").get("EXTRA") == "abc"
