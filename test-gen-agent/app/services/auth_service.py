# app/services/auth_service.py
"""认证业务逻辑层（identity 域 DDD 接入 · 阶段 C 薄门面）。

认证/会话/RSA/用户组等底层能力仍下沉 app.repositories（AuthRepo/UserGroupRepo），
身份聚合（用户名非空、邮箱格式、账号可用状态）收敛到 identity 域 DDD
（`IdentityAppService` / `web_schema` DTO 桥），本四层 Service 对既有调用方
保持薄委托：用户管理的核心用例（创建/读取/更新/停用/列表）改经 DDD 应用服务
守护不变量后再经 `user_to_web_row` 翻译回既有行 schema，对外字段形状零破坏。
"""
from __future__ import annotations

from typing import List, Optional

from app.domain.common.exceptions import (
    AggregateNotFound,
    DomainValidationError,
    InvariantViolation,
)
from app.domain.identity.application.delegation import guard_user_update_email
from app.domain.identity.application.dto import (
    AddGroupMemberCommand,
    AddLocalConfigCommand,
    ChangePasswordCommand,
    CreateApiKeyCommand,
    CreateRoleCommand,
    CreateUserCommand,
    ListApiKeysQuery,
    ListGroupMembersQuery,
    RemoveGroupMemberCommand,
    RevokeApiKeyCommand,
    SetUserEnabledCommand,
    ToggleApiKeyCommand,
    ToggleLocalConfigCommand,
    UpdateLocalConfigCommand,
    UpdateRoleCommand,
    UpdateUserCommand,
    UserListQuery,
)
from app.domain.identity.application.identity_app_service import (
    identity_app_service as _ddd_service,
)
from app.domain.identity.application.web_schema import (
    user_to_web_row,
    users_to_web_rows,
)
from app.logging_config import get_logger
from app.repositories.auth_repo import AuthRepo
from app.repositories.user_group_repo import UserGroupRepo


class AuthService:
    """认证与用户管理服务（identity 域 DDD 薄门面）。"""

    def __init__(self):
        self._repo = AuthRepo()

    @property
    def store(self):
        """兼容旧调用：经 AuthRepo 访问。"""
        return self._repo

    # ── 认证（会话/RSA 走既有 AuthRepo，与聚合无关）─────────
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        return self._repo.authenticate(username, password)

    def create_session(self, user_id: str, **kwargs) -> dict:
        return self._repo.create_session(user_id, **kwargs)

    def get_session_user(self, token: str) -> Optional[dict]:
        return self._repo.get_session_user(token)

    def delete_session(self, token: str) -> bool:
        return self._repo.delete_session(token)

    # ── 用户管理（经 identity 域 DDD 守护不变量）────────────
    def list_users(self, search: str = "", limit: int = 50,
                   offset: int = 0) -> list:
        result = _ddd_service.list_users(UserListQuery(
            search=search, limit=limit, offset=offset))
        return users_to_web_rows(result.get("list") or [])

    def create_user(self, username: str, password: str, **kwargs) -> dict:
        """创建用户（identity 域 DDD：守护用户名/邮箱/状态不变量）。"""
        cmd = CreateUserCommand(
            username=username, password=password or "",
            name=kwargs.get("name") or username,
            email=kwargs.get("email") or "",
            phone=kwargs.get("phone") or "",
            role=kwargs.get("role") or "user",
            operator=kwargs.get("operator") or "system",
        )
        row = _ddd_service.create_user(cmd)
        return user_to_web_row(row) or {}

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        return user_to_web_row(_ddd_service.get_user(user_id)) if user_id else None

    def get_user_by_username(self, username: str) -> Optional[dict]:
        # DDD 应用服务未暴露 username 查询，经领域仓储适配器 + 桥保持契约
        from app.domain.identity.infrastructure.identity_repository_impl import (
            UserRepoAdapter,
        )
        u = UserRepoAdapter().find_by_username(username)
        return user_to_web_row(u.to_dict()) if u else None

    def update_user(self, user_id: str, **kwargs) -> Optional[dict]:
        if not user_id:
            return None
        # DDD 规则下沉：邮箱格式由领域校验守护（提供则须合法）
        if kwargs.get("email") is not None:
            allowed, err = guard_user_update_email(kwargs.get("email"))
            if not allowed:
                raise ValueError(err)
        cmd = UpdateUserCommand(
            user_id=user_id,
            name=kwargs.get("name"),
            email=kwargs.get("email"),
            phone=kwargs.get("phone"),
            role=kwargs.get("role"),
            operator=kwargs.get("operator") or "system",
        )
        # 透传 DDD 未建模的存储元字段（avatar/language/本地字段等）直接落库
        extra = {k: v for k, v in kwargs.items()
                 if k in ("avatar", "language", "last_organization_id",
                          "last_project_id") and v is not None}
        if extra:
            self._repo.update_user(user_id, **extra)
        u = _ddd_service.update_user(cmd)
        return user_to_web_row(u) if u else None

    def delete_user(self, user_id: str) -> bool:
        return self._repo.delete_user(user_id)

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """重置密码——委托 DDD（管理员免旧密码重置）。"""
        try:
            return _ddd_service.change_password(ChangePasswordCommand(
                user_id=user_id, new_password=new_password or "",
            ))
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning(
                "重置密码被领域规则拦截: %s", exc)
            return False

    def set_user_enabled(self, user_id: str, enabled: bool) -> bool:
        if not user_id:
            return False
        try:
            _ddd_service.set_user_enabled(SetUserEnabledCommand(
                user_id=user_id, enabled=bool(enabled),
                operator="system"))
            return True
        except Exception:
            return False

    # ── API Keys（经 identity 域 DDD 门面）─────────────
    def list_api_keys(self, user_id: str = "") -> list:
        return _ddd_service.list_api_keys(ListApiKeysQuery(user_id=user_id or ""))

    def create_api_key(self, user_id: str, description: str = "",
                       forever: bool = False, expire_time: int = 0) -> dict:
        return _ddd_service.create_api_key(CreateApiKeyCommand(
            user_id=user_id, description=description, forever=forever,
            expire_time=expire_time,
        ))

    def delete_api_key(self, key_id: str) -> bool:
        return _ddd_service.revoke_api_key(RevokeApiKeyCommand(key_id=key_id))

    # ── RSA ──────────────────────────────────────────────
    def get_rsa_public_key(self) -> str:
        return self._repo.get_rsa_public_key()

    def rsa_decrypt(self, data: str) -> str:
        return self._repo.rsa_decrypt(data)

    def change_password(self, user_id: str, old_password: str,
                        new_password: str) -> bool:
        """用户改密码——委托 DDD：旧密码校验 + 密码变更状态机。"""
        try:
            return _ddd_service.change_password(ChangePasswordCommand(
                user_id=user_id, old_password=old_password,
                new_password=new_password,
            ))
        except (AggregateNotFound, DomainValidationError, InvariantViolation):
            return False

    def cleanup_expired_sessions(self) -> int:
        return self._repo.cleanup_expired_sessions()

    def toggle_api_key(self, key_id: str, enable: bool = False) -> bool:
        return _ddd_service.toggle_api_key(ToggleApiKeyCommand(
            key_id=key_id, enable=bool(enable)))

    # ── 本地配置（经 identity 域 DDD 门面）──────────────
    def add_local_config(self, user_id: str, user_url: str,
                        cfg_type: str = "API") -> dict:
        return _ddd_service.add_local_config(AddLocalConfigCommand(
            user_id=user_id, user_url=user_url, cfg_type=cfg_type))

    def get_local_configs(self, user_id: str = "") -> list:
        return _ddd_service.get_local_configs(user_id or "")

    def update_local_config(self, cfg_id: str, user_url: str) -> bool:
        return _ddd_service.update_local_config(UpdateLocalConfigCommand(
            cfg_id=cfg_id, user_url=user_url))

    def toggle_local_config(self, cfg_id: str, enable: bool) -> bool:
        return _ddd_service.toggle_local_config(ToggleLocalConfigCommand(
            cfg_id=cfg_id, enable=bool(enable)))

    # ── 用户组（角色）管理 ───────────────────────────
    # 数据访问委托 UserGroupRepo（用户组表唯一 DB 入口）。
    def list_groups(self, group_type: str = "SYSTEM", scope_id: str = "") -> list:
        return UserGroupRepo.list_groups(group_type, scope_id)

    def get_group(self, group_id: str) -> Optional[dict]:
        return UserGroupRepo.get_group(group_id)

    def create_group(self, name: str, description: str = "",
                     group_type: str = "SYSTEM", scope_id: str = "",
                     create_user: str = "admin", pos: int = 99) -> dict:
        """创建角色/用户组——委托 DDD：角色名非空由领域聚合守护。"""
        try:
            created = _ddd_service.create_role(CreateRoleCommand(
                name=name, description=description or "",
                group_type=group_type, scope_id=scope_id or "",
            ))
        except (DomainValidationError, ValueError) as exc:
            raise ValueError(str(exc)) from exc
        # 读回归一化（UserGroupRepo camelCase 格式）
        gid = created.get("id", "")
        return UserGroupRepo.get_group(gid) if gid else created

    def update_group(self, group_id: str, name: str = None,
                     description: str = None, pos: int = None,
                     update_user: str = "admin") -> Optional[dict]:
        """更新角色/用户组——委托 DDD：内置角色保护 / 名称非空。"""
        try:
            _ddd_service.update_role(UpdateRoleCommand(
                role_id=group_id, name=name, description=description,
            ))
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning(
                "更新用户组被领域规则拦截: %s", exc)
            return None
        # 补充 pos 等 DDD 不覆盖的字段
        if pos is not None:
            UserGroupRepo.update_group(group_id, pos=pos)
        return UserGroupRepo.get_group(group_id)

    def delete_group(self, group_id: str) -> bool:
        """删除角色/用户组——委托 DDD：内置角色不可删保护。"""
        try:
            return _ddd_service.delete_role(group_id)
        except (AggregateNotFound, DomainValidationError, InvariantViolation) as exc:
            get_logger(__name__).warning(
                "删除用户组被领域规则拦截: %s", exc)
            return False

    def get_group_permissions(self, group_id: str) -> List[str]:
        return UserGroupRepo.get_group_permissions(group_id)

    def update_group_permissions(self, group_id: str,
                                 permissions: List[str]) -> bool:
        return UserGroupRepo.update_group_permissions(group_id, permissions)

    def list_group_members(self, group_id: str, keyword: str = "") -> list:
        return _ddd_service.list_group_members(ListGroupMembersQuery(
            group_id=group_id, keyword=keyword or ""))

    def add_group_member(self, group_id: str, user_id: str,
                         username: str = "", name: str = "", email: str = "",
                         group_type: str = "SYSTEM",
                         scope_id: str = "") -> Optional[dict]:
        return _ddd_service.add_group_member(AddGroupMemberCommand(
            group_id=group_id, user_id=user_id, username=username, name=name,
            email=email, group_type=group_type, scope_id=scope_id))

    def remove_group_member(self, group_id: str, user_id: str) -> bool:
        return _ddd_service.remove_group_member(RemoveGroupMemberCommand(
            group_id=group_id, user_id=user_id))

    def remove_group_member_by_id(self, user_role_id: str) -> bool:
        return _ddd_service.remove_group_member_by_id(user_role_id)

    def get_user_options(self, exclude_group_id: str = "",
                         keyword: str = "") -> list:
        return UserGroupRepo.get_user_options(
            exclude_group_id=exclude_group_id, keyword=keyword,
        )

    def remove_user_org_memberships(self, user_id: str) -> int:
        """移除某用户所有 ORGANIZATION 类型用户组成员关系。"""
        return UserGroupRepo.remove_user_org_memberships(user_id)


auth_service = AuthService()
