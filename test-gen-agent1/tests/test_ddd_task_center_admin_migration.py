"""DDD admin_system 空壳域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/admin_system/` 的 DDD 骨架早已就绪（分层齐全），但生产 service
一直未接线（仍经 organization_service 间接委托），属于「分层齐全但未被生产
代码引用」的空壳协调域。

本次把 `app/services/admin_service.py` 收敛为对 DDD 应用门面的**薄委托门面**：
  - `app/services/admin_service.py` → `admin_app_service`
    （组织启停/成员移除委托，替代 `admin_service → organization_service` 间接层）

对外方法签名与返回 schema 与重构前一致，router（missing_admin 等）调用方零
改动。本测试断言确实走 DDD 门面。

> 说明：task_center 协调域的 DDD 接线及其委托回归已由 main 侧
> `tests/test_task_center_service_alignment.py`（legacy manager 队列协调补齐
> DDD 门面）完整覆盖，此处不再重复。
"""
from app.domain.admin_system.application.admin_app_service import (
    admin_app_service as admin_ddd,
)
from app.domain.admin_system.application.dto import (
    DisableOrgCommand,
    EnableOrgCommand,
    RemoveMemberCommand,
)
from app.services.admin_service import admin_service


# ═══════════════════════════════════════════════════════════
# 一、admin_system：admin_service 委托 admin_app_service
# ═══════════════════════════════════════════════════════════
def test_admin_service_delegates_to_admin_app_service(monkeypatch):
    """enable/disable/remove_org_member 委托 admin_app_service，参数经 DTO。"""
    seen = []

    def fake_enable(cmd):
        assert isinstance(cmd, EnableOrgCommand)
        assert cmd.org_id == "org-1"
        seen.append("enable")
        return True

    def fake_disable(cmd):
        assert isinstance(cmd, DisableOrgCommand)
        assert cmd.org_id == "org-2"
        seen.append("disable")
        return True

    def fake_remove(cmd):
        assert isinstance(cmd, RemoveMemberCommand)
        assert cmd.org_id == "org-3" and cmd.user_id == "u-9"
        seen.append("remove")
        return True

    monkeypatch.setattr(admin_ddd, "enable_organization", fake_enable)
    monkeypatch.setattr(admin_ddd, "disable_organization", fake_disable)
    monkeypatch.setattr(admin_ddd, "remove_org_member", fake_remove)

    assert admin_service.enable_organization("org-1") is True
    assert admin_service.disable_organization("org-2") is True
    assert admin_service.remove_org_member("org-3", "u-9") is True
    assert seen == ["enable", "disable", "remove"]
