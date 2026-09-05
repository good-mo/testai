"""identity 域迁移三步（A→B→C）回归测试。

覆盖：
  1. 第一步 DTO 契约桥：DDD 聚合 dict → 既有 Web schema 逐字段对齐（零回归）。
  2. 第二/三步 Service 委托守卫（delegation.py 保持向后兼容的守卫契约）。
  3. 阶段 C：Service 门面对 DDD 应用门面（identity_app_service）的委托接入——
     组织移除成员 owner 保护 / 改名校验 / 成员角色合法性均经 DDD 聚合守护；
     用户改邮箱格式校验仍经守卫委托拦截。
"""
import uuid

import pytest

from app.domain.identity.application.contract import (
    org_status_from_storage,
    org_status_to_storage,
    to_web_organization,
    to_web_user,
)
from app.domain.identity.application.delegation import (
    guard_org_change_member_role,
    guard_org_remove_member,
    guard_org_rename,
    guard_user_update_email,
)


def _mk(prefix: str = "dddimig") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def _fake_org(*, members=None, status="enabled"):
    """构造一个 mimic Organization.to_dict() 的 dict 供守卫判定。"""
    return {
        "id": _mk("org"),
        "name": "组织_" + _mk(),
        "description": "",
        "status": status,
        "created_at": 1.0,
        "updated_at": 1.0,
        "members": members or [],
    }


def _member(user_id: str, role: str):
    return {"id": _mk("m"), "user_id": user_id, "role": role}


class _FakeSvc:
    """注入守卫的可控 IdentityAppService 替身。"""

    def __init__(self, org=None, user=None):
        self._org = org
        self._user = user

    def get_organization(self, org_id):
        return self._org

    def get_user(self, user_id):
        return self._user


# ═══════════════════════════════════════════════════════
# 第一步 · DTO 契约桥
# ═══════════════════════════════════════════════════════
class TestContractBridge:
    def test_user_to_web_schema_alignment(self):
        """DDD 用户 dict → 既有 AuthRepo Web schema：字段逐一对齐。"""
        ddd_user = {
            "id": "u1", "username": "alice", "name": "Alice",
            "email": "a@b.com", "phone": "138", "avatar": "",
            "role": "admin", "enable": 0, "status": "disabled",
            "language": "zh-CN", "last_organization_id": "org1",
            "last_project_id": "proj1",
            "api_keys": [], "created_at": 1234.5, "updated_at": 2345.6,
        }
        web = to_web_user(ddd_user)
        # 关键字段与既有 AuthRepo._extract_user_from_join 一致
        assert web["id"] == "u1" and web["enable"] == 0
        assert web["create_time"] == 1234.5 and web["update_time"] == 2345.6
        # 去掉 DDD 专属字段，避免污染既有契约
        assert "status" not in web and "api_keys" not in web

    def test_user_enable_normalized_to_int(self):
        assert to_web_user({"id": "u", "username": "x", "enable": 1})["enable"] == 1

    def test_org_to_web_schema_alignment(self):
        """DDD 组织(enabled) → 既有存储 schema(active)；成员保留。"""
        ddd_org = {
            "id": "o1", "name": "租户", "description": "d",
            "status": "enabled", "created_at": 1.0, "updated_at": 2.0,
            "members": [{"id": "m1", "organization_id": "o1",
                         "user_id": "u1", "role": "owner"}],
        }
        web = to_web_organization(ddd_org)
        assert web["status"] == "active"  # enabled → active
        assert web["members"][0]["role"] == "owner"
        assert web["create_time"] == 1.0

    def test_status_mapping_roundtrip(self):
        assert org_status_to_storage("enabled") == "active"
        assert org_status_to_storage("disabled") == "disabled"
        assert org_status_from_storage("active") == "enabled"
        assert org_status_from_storage("disabled") == "disabled"


# ═══════════════════════════════════════════════════════
# 第二/三步 · Service 委托守卫（规则下沉）
# ═══════════════════════════════════════════════════════
class TestDelegationGuards:
    def test_org_rename_empty_rejected(self):
        allowed, err = guard_org_rename("  ")
        assert not allowed and err

    def test_org_rename_valid(self):
        allowed, err = guard_org_rename("新名称")
        assert allowed and err is None

    def test_remove_only_owner_rejected(self):
        org = _fake_org(members=[_member("owner_u", "owner")])
        svc = _FakeSvc(org=org)
        allowed, err = guard_org_remove_member("o1", "owner_u", svc=svc)
        assert not allowed and "所有者" in err

    def test_remove_non_owner_allowed(self):
        org = _fake_org(members=[_member("owner_u", "owner"),
                                 _member("m_u", "member")])
        svc = _FakeSvc(org=org)
        allowed, _ = guard_org_remove_member("o1", "m_u", svc=svc)
        assert allowed

    def test_remove_one_of_two_owners_allowed(self):
        org = _fake_org(members=[_member("owner_a", "owner"),
                                 _member("owner_b", "owner")])
        svc = _FakeSvc(org=org)
        allowed, _ = guard_org_remove_member("o1", "owner_a", svc=svc)
        assert allowed

    def test_change_role_only_owner_downgrade_rejected(self):
        org = _fake_org(members=[_member("owner_u", "owner")])
        svc = _FakeSvc(org=org)
        allowed, err = guard_org_change_member_role("o1", "owner_u", "member", svc=svc)
        assert not allowed and "所有者" in err

    def test_change_role_member_to_admin_allowed(self):
        org = _fake_org(members=[_member("owner_u", "owner"),
                                 _member("m_u", "member")])
        svc = _FakeSvc(org=org)
        allowed, _ = guard_org_change_member_role("o1", "m_u", "admin", svc=svc)
        assert allowed

    def test_change_role_invalid_role_rejected(self):
        org = _fake_org(members=[_member("m_u", "member")])
        svc = _FakeSvc(org=org)
        allowed, err = guard_org_change_member_role("o1", "m_u", "superuser", svc=svc)
        assert not allowed and "非法成员角色" in err

    def test_guard_missing_org_allow_fallback(self):
        """读不到组织（None）时放行给既有 repo 兜底，绝不死锁。"""
        svc = _FakeSvc(org=None)
        allowed, err = guard_org_remove_member("ghost", "u1", svc=svc)
        assert allowed and err is None

    def test_user_email_invalid_rejected(self):
        allowed, err = guard_user_update_email("not-an-email")
        assert not allowed and "邮箱" in err

    def test_user_email_valid(self):
        allowed, err = guard_user_update_email("ok@x.com")
        assert allowed and err is None

    def test_user_email_empty_pass(self):
        allowed, _ = guard_user_update_email(None)
        assert allowed


# ═══════════════════════════════════════════════════════
# Service 委托接入生效验证（monkeypatch 守卫，不依赖真实 DB）
# ═══════════════════════════════════════════════════════
class _FakeIdentitySvc:
    """可控替身：模拟 IdentityAppService 的 DDD 校验行为。"""

    def __init__(self):
        self.remove_ok = True
        self.remove_error = None
        self.rename_error = None
        self.role_error = None

    def remove_member(self, org_id, user_id, operator="system"):
        if self.remove_error:
            raise self.remove_error
        return self.remove_ok

    def update_organization(self, cmd):
        if self.rename_error:
            raise self.rename_error
        return {"id": cmd.org_id, "name": cmd.name or "", "status": "enabled"}

    def change_member_role(self, cmd):
        if self.role_error:
            raise self.role_error
        return {}


class TestServiceDelegationWiring:
    def test_org_remove_member_ddd_intercept_rejects(self, monkeypatch):
        """OrganizationService.remove_member 经 DDD 拦截（仅剩 owner）返回 False。"""
        from app.services import organization_service as osvc_mod

        svc = osvc_mod.OrganizationService()
        fake = _FakeIdentitySvc()
        from app.domain.common.exceptions import InvariantViolation
        fake.remove_error = InvariantViolation("组织至少需要保留一名所有者")
        monkeypatch.setattr(osvc_mod, "_ddd_identity", fake)
        assert svc.remove_member("o1", "u1") is False

    def test_org_remove_member_ddd_ok(self, monkeypatch):
        """OrganizationService.remove_member 经 DDD 放行返回 True。"""
        from app.services import organization_service as osvc_mod

        svc = osvc_mod.OrganizationService()
        fake = _FakeIdentitySvc()
        fake.remove_ok = True
        monkeypatch.setattr(osvc_mod, "_ddd_identity", fake)
        assert svc.remove_member("o1", "u2") is True

    def test_org_rename_ddd_rejects_empty(self, monkeypatch):
        """OrganizationService.rename 经 DDD 空名校验返回 None。"""
        from app.services import organization_service as osvc_mod

        svc = osvc_mod.OrganizationService()
        fake = _FakeIdentitySvc()
        from app.domain.common.exceptions import DomainValidationError
        fake.rename_error = DomainValidationError("组织名称不能为空")
        monkeypatch.setattr(osvc_mod, "_ddd_identity", fake)
        assert svc.rename("o1", "  ") is None

    def test_org_update_member_ddd_rejects_invalid_role(self, monkeypatch):
        """OrganizationService.update_member 经 DDD 角色校验返回 None。"""
        from app.services import organization_service as osvc_mod

        svc = osvc_mod.OrganizationService()
        fake = _FakeIdentitySvc()
        from app.domain.common.exceptions import DomainValidationError
        fake.role_error = DomainValidationError("非法成员角色")
        monkeypatch.setattr(osvc_mod, "_ddd_identity", fake)
        assert svc.update_member("o1", "u1", role="superuser") is None

    def test_auth_update_user_email_guard_rejects(self):
        from app.services.auth_service import AuthService

        svc = AuthService()
        # 非法邮箱经 DDD 规则拦截 → 抛 ValueError
        with pytest.raises(ValueError):
            svc.update_user("u1", email="not-an-email")
