"""DDD 身份与访问（IdentityAndAccess）试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：账号状态、成员角色、权限集合、状态机、邀请有效期。
  2. 应用服务全链路（对接真实 AuthRepo/OrganizationRepo/... 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError, InvariantViolation
from app.domain.identity.application.dto import (
    AddMemberCommand,
    ChangeMemberRoleCommand,
    CreateOrganizationCommand,
    CreateRoleCommand,
    CreateUserCommand,
    IssueInvitationCommand,
    SetUserEnabledCommand,
)
from app.domain.identity.application.identity_app_service import IdentityAppService
from app.domain.identity.domain.entities.invitation import Invitation
from app.domain.identity.domain.entities.organization import Organization
from app.domain.identity.domain.entities.role import Role
from app.domain.identity.domain.entities.user import User
from app.domain.identity.domain.value_objects.account_status import (
    AccountStatus,
)
from app.domain.identity.domain.value_objects.member_role import MemberRole, MemberRoleEnum
from app.domain.identity.domain.value_objects.permission import PermissionSet

TAG = "dddida"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:6]}"


def _user(**kw):
    kw.setdefault("user_id", _mk())
    kw.setdefault("username", "user_" + _mk())
    return User(**kw)


def _org(**kw):
    kw.setdefault("org_id", _mk())
    kw.setdefault("name", "组织_" + _mk())
    return Organization(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_account_status(self):
        assert AccountStatus(1).enabled is True
        assert AccountStatus("disabled").enabled is False
        assert str(AccountStatus(0)) == "disabled"
        with pytest.raises(DomainValidationError):
            AccountStatus("weird")

    def test_member_role(self):
        assert str(MemberRole("ADMIN")) == "admin"
        assert MemberRole(MemberRoleEnum.OWNER.value).can_manage()
        assert not MemberRole(MemberRoleEnum.MEMBER.value).can_manage()
        with pytest.raises(DomainValidationError):
            MemberRole("superuser")

    def test_permission_set(self):
        ps = PermissionSet(["case:create", "*"])
        assert ps.has("anything")
        ps2 = PermissionSet(["case:create"])
        assert ps2.has("case:create") and not ps2.has("run:start")

    def test_user_username_required(self):
        with pytest.raises(DomainValidationError):
            User(user_id=_mk(), username="  ")

    def test_user_email_format(self):
        u = _user()
        with pytest.raises(DomainValidationError):
            u.change_email("not-an-email")


class TestUserAggregate:
    def test_enable_disable(self):
        u = _user()
        u.disable()
        assert not u.enabled and u.status.enabled is False
        u.enable()
        assert u.enabled

    def test_rename_empty_rejected(self):
        u = _user()
        with pytest.raises(DomainValidationError):
            u.rename("  ")

    def test_api_key_management(self):
        u = _user()
        k = u.add_api_key(key_id=_mk(), description="ci")
        assert len(u.api_keys) == 1
        u.revoke_api_key(k.id.value)
        assert u.api_keys[0].revoked


class TestOrganizationAggregate:
    def test_owner_guard_remove(self):
        o = _org()
        o.add_member(member_id=_mk(), user_id="u_owner", role="owner")
        with pytest.raises(InvariantViolation):
            o.remove_member("u_owner")

    def test_owner_guard_downgrade_single(self):
        o = _org()
        o.add_member(member_id=_mk(), user_id="u_owner", role="owner")
        with pytest.raises(InvariantViolation):
            o.change_member_role("u_owner", "member")

    def test_member_role_change(self):
        o = _org()
        o.add_member(member_id=_mk(), user_id="a", role="owner")
        o.add_member(member_id=_mk(), user_id="b", role="member")
        o.change_member_role("b", "admin")
        assert o.get_member_by_user("b").role.value == "admin"

    def test_org_name_required(self):
        with pytest.raises(DomainValidationError):
            Organization(org_id=_mk(), name="")


class TestRoleAggregate:
    def test_permissions(self):
        r = Role(role_id=_mk(), name="role_" + _mk())
        r.grant_permission("case:create")
        assert r.permissions.has("case:create")
        r.revoke_permission("case:create")
        assert not r.permissions.has("case:create")

    def test_internal_not_deletable(self):
        r = Role(role_id=_mk(), name="r_" + _mk(), internal=1)
        with pytest.raises(InvariantViolation):
            r.delete()


class TestInvitationAggregate:
    def test_status_lifecycle(self):
        inv = Invitation(invite_id=_mk(), email="a@b.com", ttl=100)
        assert inv.status().value == "pending"
        inv.accept()
        assert inv.used

    def test_used_cannot_accept_twice(self):
        inv = Invitation(invite_id=_mk(), email="a@b.com", ttl=100)
        inv.accept()
        with pytest.raises(InvariantViolation):
            inv.accept()

    def test_expired(self):
        import time
        inv = Invitation(invite_id=_mk(), email="a@b.com",
                         expire_time=time.time() - 10)
        with pytest.raises(InvariantViolation):
            inv.accept()


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（对接真实存储）
# ═══════════════════════════════════════════════════════════
class TestAppService:
    def _svc(self):
        return IdentityAppService()

    def test_user_crud(self):
        svc = self._svc()
        uname = "user_" + _mk()
        u = svc.create_user(CreateUserCommand(username=uname, password="pw123",
                                              email=uname + "@x.com"))
        assert u["username"] == uname and u["enable"] == 1
        got = svc.get_user(u["id"])
        assert got is not None and got["username"] == uname
        svc.set_user_enabled(SetUserEnabledCommand(user_id=u["id"], enabled=False))
        assert svc.get_user(u["id"])["enable"] == 0
        svc.set_user_enabled(SetUserEnabledCommand(user_id=u["id"], enabled=True))
        assert svc.get_user(u["id"])["enable"] == 1

    def test_org_with_members(self):
        svc = self._svc()
        uname1 = "a_" + _mk()
        uname2 = "b_" + _mk()
        u1 = svc.create_user(CreateUserCommand(username=uname1, password="x"))
        u2 = svc.create_user(CreateUserCommand(username=uname2, password="x"))
        org = svc.create_organization(CreateOrganizationCommand(name="org_" + _mk()))
        svc.add_member(AddMemberCommand(org_id=org["id"], user_id=u1["id"], role="owner"))
        svc.add_member(AddMemberCommand(org_id=org["id"], user_id=u2["id"], role="member"))
        svc.change_member_role(ChangeMemberRoleCommand(
            org_id=org["id"], user_id=u2["id"], role="admin"))
        loaded = svc.get_organization(org["id"])
        roles = {m["user_id"]: m["role"] for m in loaded["members"]}
        assert roles[u2["id"]] == "admin"

    def test_role_crud(self):
        svc = self._svc()
        r = svc.create_role(CreateRoleCommand(
            name="role_" + _mk(), permissions=["case:create"]))
        assert "case:create" in svc.get_role(r["id"])["permissions"]

    def test_invitation_flow(self):
        svc = self._svc()
        d = svc.issue_invitation(IssueInvitationCommand(email=_mk() + "@x.com"))
        assert d["status"] == "pending"
        svc.accept_invitation(d["invite_id"])
        assert svc.get_invitation(d["invite_id"])["status"] == "used"


# ═══════════════════════════════════════════════════════════
# 四、阶段 B/C 迁移回归
#   门面委托 identity 域 DDD：invitation/auth/organization 服务
#   对外方法形状与契约零回归（阶段 C 薄门面）。
# ═══════════════════════════════════════════════════════════
class TestIdentityServiceFacade:
    """invitation_service 收敛为 DDD 薄门面后契约回归。"""

    def test_invitation_service_delegates_and_keeps_invite_id(self):
        from app.repositories.invitation_repo import invitation_repo
        from app.services.invitation_service import invitation_service
        email = _mk() + "@x.com"
        inv = invitation_service.create_invite(
            [email], scope="SYSTEM", create_user="admin")
        assert inv is not None and inv["invite_id"]
        try:
            iid = inv["invite_id"]
            # 服务(DDD)与 repo 读回的 invite_id 一致
            via_svc = invitation_service.get_by_invite_id(iid)
            via_repo = invitation_repo.get_by_invite_id(iid)
            assert via_svc and via_svc["invite_id"] == via_repo["invite_id"]
            assert invitation_service.is_valid(iid) is True
            assert invitation_service.mark_used(iid) is True
            assert invitation_service.is_valid(iid) is False
        finally:
            _del_invite(email)

    def test_invitation_empty_returns_none(self):
        from app.services.invitation_service import invitation_service
        assert invitation_service.create_invite([]) is None


class TestAuthServiceFacade:
    """auth_service 用户管理委托 identity 域 DDD 后契约回归。"""

    def test_user_crud_via_facade(self):
        from app.repositories.auth_repo import AuthRepo
        from app.services.auth_service import auth_service
        uname = "u_" + _mk()
        u = auth_service.create_user(uname, "pw123", email=uname + "@x.com")
        assert u and u["username"] == uname and u["enable"] == 1
        try:
            # 读回字段覆盖既有 AuthRepo 行契约
            for key in ("id", "username", "name", "email", "enable",
                        "create_time", "language"):
                assert key in u, f"缺失字段 {key}"
            assert auth_service.get_user_by_id(u["id"])["username"] == uname
            assert auth_service.get_user_by_username(uname)["id"] == u["id"]
            # 经 DDD 落库后真实密码可认证
            assert AuthRepo().authenticate(uname, "pw123") is not None
            # 停用归一
            auth_service.set_user_enabled(u["id"], False)
            assert auth_service.get_user_by_id(u["id"])["enable"] == 0
            # 列表搜索
            found = [x for x in auth_service.list_users(search=uname)]
            assert found and found[0]["id"] == u["id"]
        finally:
            _del_user(uname)


class TestOrganizationServiceFacade:
    """organization_service 成员 add/remove 委托 DDD owner 守卫后契约回归。"""

    def test_org_member_owner_guard_via_facade(self):
        from app.services.auth_service import auth_service
        from app.services.organization_service import organization_service
        oname = "org_" + _mk()
        org = organization_service.create(oname, "d")
        assert org and org.get("id")
        oid = org["id"]
        u1 = auth_service.create_user("ow_" + _mk(), "x")
        u2 = auth_service.create_user("mb_" + _mk(), "x")
        try:
            m = organization_service.add_member(oid, u1["id"], role="owner")
            assert m and m["user_id"] == u1["id"] and m["role"] == "owner"
            organization_service.add_member(oid, u2["id"], role="member")
            # owner 唯一性守卫：不能删除唯一 owner（经 DDD 聚合拦截返回 False）
            assert organization_service.remove_member(oid, u1["id"]) is False
            # 非 owner 成员可正常移除
            assert organization_service.remove_member(oid, u2["id"]) is True
            members = organization_service.list_members(oid)
            assert all(m["user_id"] != u2["id"] for m in members)
        finally:
            _del_org(oid)
            _del_user(u1["username"])
            _del_user(u2["username"])


# ── 清理助手（幂等）──────────────────────────────────────
def _del_user(username: str) -> None:
    try:
        from app.core.database import Database
        conn = Database.get_conn("auth.db")
        conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
    except Exception:
        pass


def _del_invite(email: str) -> None:
    try:
        from app.core.database import Database
        conn = Database.get_conn("auth.db")
        conn.execute("DELETE FROM invitations WHERE email=?", (email,))
        conn.commit()
    except Exception:
        pass


def _del_org(org_id: str) -> None:
    try:
        from app.core.database import Database
        conn = Database.get_conn("projects.db")
        conn.execute("DELETE FROM organization_members WHERE organization_id=?",
                     (org_id,))
        conn.execute("DELETE FROM organizations WHERE id=?", (org_id,))
        conn.commit()
    except Exception:
        pass
