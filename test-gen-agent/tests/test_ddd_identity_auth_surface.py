"""identity（auth）域旁路方法面补齐 —— auth_service 旁路方法 DDD 接线回归。

本轮目标（对应当前 ISSUE 工作项）：
  auth_service 的用户/组/成员、local_config、api_key 等旁路方法原先直连
  AuthRepo / UserGroupRepo，未进入 identity 域 DDD 门面。本次把：
    - api_key（list/create/delete/toggle）
    - 用户组成员（list/add/remove/remove_by_id）
    - local_config（add/get/update/toggle）
  补齐进 `IdentityAppService`（薄委托既有 Repo 防腐），并把 `auth_service`
  相应旁路方法收敛为对 DDD 门面的委托，保持对外契约零回归。
"""
import uuid

import pytest

from app.domain.identity.application.dto import (
    AddGroupMemberCommand,
    AddLocalConfigCommand,
    CreateApiKeyCommand,
    ListGroupMembersQuery,
    ListApiKeysQuery,
    RemoveGroupMemberCommand,
    RevokeApiKeyCommand,
    ToggleApiKeyCommand,
    ToggleLocalConfigCommand,
    UpdateLocalConfigCommand,
)
from app.domain.identity.application.identity_app_service import (
    IdentityAppService,
    identity_app_service as ddd_service,
)

TAG = "dddias"


def _mk(prefix: str = "dias") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


# ═══════════════════════════════════════════════════════
# 一、IdentityAppService 旁路方法面（DTO 门面直调）
# ═══════════════════════════════════════════════════════
class TestIdentityAppServiceBypassSurface:
    def test_ddd_service_exposes_auth_bypass_methods(self):
        """IdentityAppService 已具备 auth 旁路方法面（api_key/组员/local_config）。"""
        svc = ddd_service
        for name in ("list_api_keys", "create_api_key", "revoke_api_key",
                     "toggle_api_key", "list_group_members", "add_group_member",
                     "remove_group_member", "remove_group_member_by_id",
                     "add_local_config", "get_local_configs",
                     "update_local_config", "toggle_local_config"):
            assert hasattr(svc, name), f"IdentityAppService 缺少 {name}"


# ═══════════════════════════════════════════════════════
# 二、auth_service 委托接入验证（断言确实经 DDD 门面）
# ═══════════════════════════════════════════════════════
class _FakeIdentity:
    """记录 DDD 门面被调用的替身。"""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _spy(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return None
        return _spy


class TestAuthServiceDelegationWiring:
    def test_api_key_methods_delegate_to_ddd(self, monkeypatch):
        import app.services.auth_service as mod
        svc = mod.AuthService()
        fake = _FakeIdentity()
        monkeypatch.setattr(mod, "_ddd_service", fake)
        svc.list_api_keys("u1")
        svc.create_api_key("u1", description="d")
        svc.delete_api_key("k1")
        svc.toggle_api_key("k1", True)
        names = [c[0] for c in fake.calls]
        assert "list_api_keys" in names
        assert "create_api_key" in names
        assert "revoke_api_key" in names  # delete 委托 revoke
        assert "toggle_api_key" in names
        # 参数确实经 DTO
        create_call = [c for c in fake.calls if c[0] == "create_api_key"][0]
        cmd = create_call[1][0]
        assert isinstance(cmd, CreateApiKeyCommand) and cmd.user_id == "u1"

    def test_local_config_methods_delegate_to_ddd(self, monkeypatch):
        import app.services.auth_service as mod
        svc = mod.AuthService()
        fake = _FakeIdentity()
        monkeypatch.setattr(mod, "_ddd_service", fake)
        svc.add_local_config("u1", "http://x")
        svc.get_local_configs("u1")
        svc.update_local_config("c1", "http://y")
        svc.toggle_local_config("c1", True)
        names = [c[0] for c in fake.calls]
        assert {"add_local_config", "get_local_configs",
                "update_local_config", "toggle_local_config"} <= set(names)

    def test_group_member_methods_delegate_to_ddd(self, monkeypatch):
        import app.services.auth_service as mod
        svc = mod.AuthService()
        fake = _FakeIdentity()
        monkeypatch.setattr(mod, "_ddd_service", fake)
        svc.list_group_members("g1")
        svc.add_group_member("g1", "u1", username="n")
        svc.remove_group_member("g1", "u1")
        svc.remove_group_member_by_id("r1")
        names = [c[0] for c in fake.calls]
        assert {"list_group_members", "add_group_member",
                "remove_group_member", "remove_group_member_by_id"} <= set(names)
        add_call = [c for c in fake.calls if c[0] == "add_group_member"][0]
        assert isinstance(add_call[1][0], AddGroupMemberCommand)


# ═══════════════════════════════════════════════════════
# 三、端到端契约回归（真实 DB，对外行为零变化）
# ═══════════════════════════════════════════════════════
class TestAuthServiceEndToEnd:
    def _mk_user(self):
        from app.services.auth_service import auth_service
        uname = "u_" + _mk()
        u = auth_service.create_user(uname, "pw123", email=uname + "@x.com")
        return auth_service, u, uname

    def test_api_key_roundtrip_via_facade(self):
        from app.services.auth_service import auth_service
        uname = "u_" + _mk()
        u = auth_service.create_user(uname, "pw123")
        uid = u["id"]
        try:
            k = auth_service.create_api_key(uid, description="desc1")
            assert k and k.get("id") and k.get("access_key")
            keys = auth_service.list_api_keys(uid)
            assert any(x["id"] == k["id"] for x in keys)
            assert auth_service.toggle_api_key(k["id"], False) is True
            keys2 = auth_service.list_api_keys(uid)
            assert any(x["id"] == k["id"] and x.get("enable") in (0, False)
                       for x in keys2)
            assert auth_service.delete_api_key(k["id"]) is True
            keys3 = auth_service.list_api_keys(uid)
            assert all(x["id"] != k["id"] for x in keys3)
        finally:
            _del_user_by_username(uname)
            _del_api_keys_of(uname)

    def test_local_config_roundtrip_via_facade(self):
        from app.services.auth_service import auth_service
        uname = "u_" + _mk()
        u = auth_service.create_user(uname, "pw123")
        uid = u["id"]
        try:
            cfg = auth_service.add_local_config(uid, "http://localhost:8080")
            assert cfg and cfg.get("id")
            cfgs = auth_service.get_local_configs(uid)
            assert any(x.get("id") == cfg["id"] for x in cfgs)
            assert auth_service.update_local_config(cfg["id"], "http://new") is True
            assert auth_service.toggle_local_config(cfg["id"], True) is True
            cfgs2 = auth_service.get_local_configs(uid)
            row = next(x for x in cfgs2 if x.get("id") == cfg["id"])
            assert row.get("user_url") == "http://new"
        finally:
            _del_user_by_username(uname)
            _del_local_configs_of(uname)

    def test_group_member_roundtrip_via_facade(self):
        from app.services.auth_service import auth_service
        uname = "u_" + _mk()
        u = auth_service.create_user(uname, "pw123")
        uid = u["id"]
        gname = "grp_" + _mk()
        g = auth_service.create_group(gname, description="d", group_type="SYSTEM")
        gid = g["id"]
        try:
            m = auth_service.add_group_member(
                gid, uid, username=uname, name=uname, email="")
            assert m and m.get("userId") == uid
            members = auth_service.list_group_members(gid)
            assert any(x.get("userId") == uid for x in members)
            assert auth_service.remove_group_member(gid, uid) is True
            members2 = auth_service.list_group_members(gid)
            assert all(x.get("userId") != uid for x in members2)
        finally:
            _del_user_by_username(uname)
            _del_group(gname, gid)


# ═══════════════════════════════════════════════════════
# 清理助手（幂等）
# ═══════════════════════════════════════════════════════
def _auth_conn():
    from app.core.database import Database
    return Database.get_conn("auth.db")


def _del_user_by_username(username: str) -> None:
    try:
        conn = _auth_conn()
        rows = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)).fetchall()
        for (uid,) in rows:
            conn.execute("DELETE FROM user_group_members WHERE user_id=?", (uid,))
            conn.execute("DELETE FROM api_keys WHERE user_id=?", (uid,))
            conn.execute("DELETE FROM user_local_configs WHERE user_id=?", (uid,))
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    except Exception:
        pass


def _del_api_keys_of(username: str) -> None:
    try:
        conn = _auth_conn()
        rows = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)).fetchall()
        for (uid,) in rows:
            conn.execute("DELETE FROM api_keys WHERE user_id=?", (uid,))
        conn.commit()
    except Exception:
        pass


def _del_local_configs_of(username: str) -> None:
    try:
        conn = _auth_conn()
        rows = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)).fetchall()
        for (uid,) in rows:
            conn.execute("DELETE FROM user_local_configs WHERE user_id=?", (uid,))
        conn.commit()
    except Exception:
        pass


def _del_group(gname: str, gid: str) -> None:
    try:
        conn = _auth_conn()
        conn.execute("DELETE FROM user_group_members WHERE group_id=?", (gid,))
        conn.execute("DELETE FROM user_group_permissions WHERE group_id=?", (gid,))
        conn.execute("DELETE FROM user_groups WHERE id=?", (gid,))
        conn.commit()
    except Exception:
        pass
