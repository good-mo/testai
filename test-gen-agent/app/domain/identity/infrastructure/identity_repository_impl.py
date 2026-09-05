"""身份与访问聚合仓储实现（Adapter 防腐层）。

把"面向聚合的仓储接口"翻译为既有四层 Repo 命令（AuthRepo / OrganizationRepo /
UserGroupRepo / InvitationRepo），复用已验证的存储逻辑，同时让领域层获得
聚合级读写语义；后续如需换存储仅替换本文件。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.identity.domain.entities.invitation import Invitation
from app.domain.identity.domain.entities.organization import Organization
from app.domain.identity.domain.entities.role import Role
from app.domain.identity.domain.entities.user import User
from app.repositories.auth_repo import AuthRepo
from app.repositories.invitation_repo import InvitationRepo
from app.repositories.organization_repo import OrganizationRepo
from app.repositories.user_group_repo import UserGroupRepo


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ─────────────────────────────────────────────────────────
# 用户仓储适配器（对接 AuthRepo）
# ─────────────────────────────────────────────────────────
class UserRepoAdapter:
    """将既有 AuthRepo 封装为面向 User 聚合的仓储。"""

    def __init__(self, repo: AuthRepo = None):
        self._auth = repo or AuthRepo()

    def next_id(self) -> str:
        return _new_id()

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, user_id: str) -> Optional[User]:
        row = self._auth.get_user_by_id(user_id)
        if not row:
            return None
        return self._assemble(row)

    def find_by_username(self, username: str) -> Optional[User]:
        row = self._auth.get_user_by_username(username)
        if not row:
            return None
        return self._assemble(row)

    def list(self, search: str = "", limit: int = 100, offset: int = 0) -> Tuple[List[User], int]:
        rows = self._auth.list_users(search=search, limit=limit, offset=offset)
        users = [self._assemble(dict(r)) for r in rows if r]
        return users, len(users)

    def _assemble(self, row: dict) -> User:
        user = User.from_dict(dict(row))
        # 加载该用户的 API Keys（挂载为子实体）
        api_rows = self._auth.list_api_keys(user_id=user.id.value)
        keys = []
        for r in api_rows:
            keys.append({
                "key_id": r.get("id"),
                "user_id": r.get("user_id"),
                "description": r.get("description", ""),
                "api_key": r.get("access_key", ""),
                "enable": r.get("enable", 1),
                "created_at": r.get("create_time"),
            })
        user._api_keys = []
        from app.domain.identity.domain.entities.api_key import ApiKey
        for k in keys:
            user._api_keys.append(ApiKey(**k))
        return user

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, user: User) -> User:
        # 新建用户：存储层自行生成主键，落库后回填聚合 id
        self._auth.create_user(
            username=user.username, password=user.username,
            name=user.name, email=user.email, phone=user.phone,
            role=user.role,
        )
        stored = self._auth.get_user_by_username(user.username)
        if stored:
            from app.domain.common.entities import Identifier
            user.id = Identifier.of(str(stored.get("id")))
        return user

    def update(self, user: User) -> Optional[User]:
        self._auth.update_user(
            user.id.value,
            name=user.name, email=user.email, phone=user.phone,
            role=user.role, language=user.language,
        )
        self._auth.set_user_enabled(user.id.value, user.enabled)
        return self.find_by_id(user.id.value)

    def delete(self, user_id: str) -> bool:
        return self._auth.delete_user(user_id)

    def change_password(self, user_id: str, new_password: str) -> bool:
        return self._auth.reset_password(user_id, new_password)


# ─────────────────────────────────────────────────────────
# 组织仓储适配器（对接 OrganizationRepo）
# ─────────────────────────────────────────────────────────
class OrganizationRepoAdapter:
    """将既有 OrganizationRepo 封装为面向 Organization 聚合的仓储。"""

    def __init__(self, repo=None):
        self._org = repo or OrganizationRepo

    def next_id(self) -> str:
        return _new_id()

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, org_id: str) -> Optional[Organization]:
        row = self._org.get(org_id)
        if not row:
            return None
        return self._assemble(dict(row))

    def find_by_name(self, name: str) -> Optional[Organization]:
        row = self._org.get_by_name(name)
        if not row:
            return None
        return self._assemble(dict(row))

    def list(self, search: str = "", status: str = "", limit: int = 100,
             offset: int = 0) -> Tuple[List[Organization], int]:
        rows = self._org.list(search=search, status=status, limit=limit, offset=offset)
        orgs = [self._assemble(dict(r)) for r in rows if r]
        total = self._org.count(search=search)
        return orgs, total

    def _assemble(self, row: dict) -> Organization:
        row = dict(row)
        # 存储层状态语义：active=启用 / disabled=停用 / deleted=已删
        _storage_status = row.get("status")
        if _storage_status == "active":
            row["status"] = "enabled"
        org = Organization.from_dict(row)
        # 挂载成员子实体
        member_rows = self._org.list_members(org.id.value, search="", limit=9999)
        members = []
        for m in member_rows:
            if isinstance(m, dict):
                members.append({
                    "member_id": m.get("id"),
                    "organization_id": m.get("organization_id"),
                    "user_id": m.get("user_id"),
                    "username": m.get("username", ""),
                    "name": m.get("name", ""),
                    "email": m.get("email", ""),
                    "role": m.get("role", "member"),
                })
        from app.domain.identity.domain.entities.member import Member
        org._members = [Member(**mm) for mm in members]
        return org

    # ── 写 ──────────────────────────────────────────
    def save(self, org: Organization) -> Organization:
        created = self._org.create(org.name, org.description)
        created_id = created.get("id") if isinstance(created, dict) else created
        from app.domain.common.entities import Identifier
        org.id = Identifier.of(str(created_id))
        # 同步成员
        for m in org.members:
            self._org.add_member(org.id.value, m.user_id, m.role.value)
        return self.find_by_id(org.id.value) or org

    def _persist_members(self, org: Organization) -> None:
        for m in org.members:
            self._org.add_member(org.id.value, m.user_id, m.role.value)

    def update(self, org: Organization) -> Optional[Organization]:
        from app.repositories.organization_repo import OrganizationRepo
        data = {"name": org.name, "description": org.description}
        data["status"] = "active" if org.enabled else "disabled"
        OrganizationRepo.update(org.id.value, data)
        return self.find_by_id(org.id.value)

    def persist_member_change(self, org: Organization, user_id: str, role: str) -> None:
        self._org.update_member(org.id.value, user_id, role)


# ─────────────────────────────────────────────────────────
# 角色仓储适配器（对接 UserGroupRepo）
# ─────────────────────────────────────────────────────────
class RoleRepoAdapter:
    """将既有 UserGroupRepo 封装为面向 Role 聚合的仓储。"""

    def __init__(self, repo=None):
        self._ug = repo or UserGroupRepo

    def next_id(self) -> str:
        return _new_id()

    # ── 读 ──────────────────────────────────────────
    def find_by_id(self, role_id: str) -> Optional[Role]:
        row = self._ug.get_group(role_id)
        if not row:
            return None
        return self._assemble(dict(row))

    def find_by_name(self, name: str) -> Optional[Role]:
        for gt in ("SYSTEM", "ORGANIZATION", "PROJECT"):
            for g in (self._ug.list_groups(group_type=gt, scope_id="") or []):
                if str(g.get("name", "")).strip() == str(name).strip():
                    return self._assemble(dict(g))
        return None

    def list(self, group_type: str = "SYSTEM", limit: int = 100,
             offset: int = 0) -> Tuple[List[Role], int]:
        # UserGroupRepo.list_groups 不接收 limit/offset；先取全量再分页
        rows = self._ug.list_groups(group_type=group_type, scope_id="") or []
        paged = rows[int(offset):int(offset) + int(limit)]
        roles = [self._assemble(dict(r)) for r in paged if r]
        return roles, len(rows)

    def _assemble(self, row: dict) -> Role:
        # UserGroupRepo 返回 camelCase 字段（scopeId/createTime）；permissions 需单独查询
        gid = row.get("id") or row.get("group_id")
        perms = self._ug.get_group_permissions(gid) if gid else []
        return Role.from_dict({
            "id": gid,
            "name": row.get("name"),
            "description": row.get("description", ""),
            "type": row.get("type") or row.get("group_type") or "SYSTEM",
            "scope_id": row.get("scope_id") or row.get("scopeId") or "",
            "internal": row.get("internal", 0),
            "permissions": perms,
        })

    # ── 写 ──────────────────────────────────────────
    def save(self, role: Role) -> Role:
        created = self._ug.create_group(
            role.name, role.description, group_type=role.group_type,
            scope_id=role.scope_id,
        )
        role_id = created.get("id") if isinstance(created, dict) else None
        if role_id:
            from app.domain.common.entities import Identifier
            role.id = Identifier.of(str(role_id))
        self._ug.update_group_permissions(role.id.value, role.permissions.to_list())
        return self.find_by_id(role.id.value) or role

    def update(self, role: Role) -> Optional[Role]:
        self._ug.update_group(role.id.value, name=role.name, description=role.description)
        self._ug.update_group_permissions(role.id.value, role.permissions.to_list())
        return self.find_by_id(role.id.value)

    def delete(self, role_id: str) -> bool:
        return self._ug.delete_group(role_id)


# ─────────────────────────────────────────────────────────
# 邀请仓储适配器（对接 InvitationRepo）
# ─────────────────────────────────────────────────────────
class InvitationRepoAdapter:
    """将既有 InvitationRepo 封装为面向 Invitation 聚合的仓储。"""

    def __init__(self, repo=None):
        self._inv = repo or InvitationRepo

    def next_id(self) -> str:
        return _new_id()

    # ── 读 ──────────────────────────────────────────
    def find_by_invite_id(self, invite_id: str) -> Optional[Invitation]:
        row = self._inv.get_by_invite_id(invite_id)
        if not row:
            return None
        return Invitation.from_dict(dict(row))

    def is_valid(self, invite_id: str) -> bool:
        return self._inv.is_valid(invite_id)

    # ── 写 ──────────────────────────────────────────
    def save(self, inv: Invitation) -> Invitation:
        created = self._inv.create_invite(
            emails=[inv.email], scope=inv.scope,
            organization_id=inv.organization_id, project_id=inv.project_id,
            role_ids=inv.role_ids, create_user=inv.create_user,
        )
        if isinstance(created, dict):
            from app.domain.common.entities import Identifier
            inv.id = Identifier.of(str(created.get("invite_id")))
        return inv

    def mark_used(self, invite_id: str) -> bool:
        return self._inv.mark_used(invite_id)
