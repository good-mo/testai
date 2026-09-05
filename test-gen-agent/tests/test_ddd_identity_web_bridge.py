"""IdentityAndAccess DTO 契约桥 对齐单测。

验证：`IdentityAppService` / DDD 聚合输出经 `application/web_schema.py`
翻译后，与既有四层返回行（AuthRepo / OrganizationRepo 成员行）**契约兼容**
——既有调用方依赖的字段全部保留，类型/语义一致。这是身份域 A→B→C
渐进迁移中 "DTO 桥"（第 1 步）的回归防线。
"""
import uuid

from app.domain.identity.application.dto import (
    AddMemberCommand,
    CreateOrganizationCommand,
    CreateUserCommand,
    SetUserEnabledCommand,
)
from app.domain.identity.application.identity_app_service import IdentityAppService
from app.domain.identity.application.web_schema import (
    member_to_web_row,
    org_to_web_row,
    user_to_web_row,
    users_to_web_rows,
)

TAG = "dddwbridge"


def _mk(prefix="t") -> str:
    return f"{prefix}_{TAG}_{uuid.uuid4().hex[:6]}"


class TestUserBridge:
    """DDD User 输出 ↔ 既有 AuthRepo 行契约。"""

    def _svc(self):
        return IdentityAppService()

    def test_ddd_user_output_bridge_keeps_auth_row_fields(self):
        """DDD create_user 输出经桥翻译后，覆盖既有 AuthRepo 行关键字段。"""
        svc = self._svc()
        uname = _mk("user")
        u = svc.create_user(CreateUserCommand(
            username=uname, password="pw123",
            email=uname + "@x.com", name="桥接用户", phone="12345",
        ))
        row = user_to_web_row(u)
        assert row is not None
        # 既有 AuthRepo._row_to_user 去密码后返回的行字段子集
        for key in ("id", "username", "email", "phone", "avatar", "name",
                    "role", "enable", "language"):
            assert key in row, f"缺失既有契约字段: {key}"
        assert row["username"] == uname
        assert row["enable"] == 1
        # 存储元字段（既有行存在）补齐缺省，保证读取方 get 不崩
        for key in ("deleted", "create_user", "update_user"):
            assert key in row

    def test_bridge_enable_normalization(self):
        """enable 归一：DDD 停用后翻译为 enable=0，符合既有行语义。"""
        svc = self._svc()
        u = svc.create_user(CreateUserCommand(username=_mk("dis"), password="x"))
        svc.set_user_enabled(SetUserEnabledCommand(user_id=u["id"], enabled=False))
        disabled = svc.get_user(u["id"])
        assert user_to_web_row(disabled)["enable"] == 0

    def test_users_bridge_list(self):
        svc = self._svc()
        u = svc.create_user(CreateUserCommand(username=_mk("l1"), password="x"))
        rows = users_to_web_rows([u])
        assert rows and rows[0]["id"] == u["id"]

    def test_bridge_missing_row_is_none(self):
        assert user_to_web_row(None) is None


class TestOrgBridge:
    """DDD Organization / Member 输出 ↔ 既有 OrganizationRepo 行契约。"""

    def _svc(self):
        return IdentityAppService()

    def test_org_member_row_bridge(self):
        svc = self._svc()
        u = svc.create_user(CreateUserCommand(username=_mk("ow"), password="x"))
        org = svc.create_organization(CreateOrganizationCommand(name="org_" + _mk()))
        svc.add_member(AddMemberCommand(org_id=org["id"], user_id=u["id"], role="owner"))
        loaded = svc.get_organization(org["id"])
        assert loaded and loaded["members"]
        web = org_to_web_row(loaded)
        assert web is not None
        # 组织行契约
        for key in ("id", "name", "description", "status"):
            assert key in web, f"缺失组织契约字段: {key}"
        member = web["members"][0]
        # 既有 organization_members 行字段
        for key in ("id", "organization_id", "user_id", "username",
                    "name", "email", "role"):
            assert key in member, f"缺失成员契约字段: {key}"
        assert member["role"] == "owner"

    def test_member_bridge_standalone(self):
        m = member_to_web_row({
            "member_id": "m1", "organization_id": "o1", "user_id": "u1",
            "username": "alice", "role": "ADMIN",
        })
        assert m["role"] == "admin" and m["id"] == "m1"
