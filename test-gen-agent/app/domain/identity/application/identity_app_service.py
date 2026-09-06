"""身份与访问应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的用例编排入口（用户/组织/角色/邀请）；
  2. 承载用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 → 发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.entities import AggregateRoot
from app.domain.common.exceptions import AggregateNotFound, DomainValidationError
from app.domain.identity.application.dto import (
    AddMemberCommand,
    ChangeMemberRoleCommand,
    ChangePasswordCommand,
    CreateOrganizationCommand,
    CreateRoleCommand,
    CreateUserCommand,
    IssueInvitationCommand,
    OrganizationListQuery,
    SetUserEnabledCommand,
    UpdateOrganizationCommand,
    UpdateRoleCommand,
    UpdateUserCommand,
    UserListQuery,
)
from app.domain.identity.domain.entities.organization import Organization
from app.domain.identity.domain.entities.role import Role
from app.domain.identity.domain.entities.user import User
from app.domain.identity.domain.repository import (
    InvitationRepository,
    OrganizationRepository,
    RoleRepository,
    UserRepository,
)
from app.domain.identity.infrastructure.identity_repository_impl import (
    IdentityRepo,
    InvitationRepoAdapter,
    OrganizationRepoAdapter,
    RoleRepoAdapter,
    UserRepoAdapter,
)

logger = logging.getLogger(__name__)


class IdentityAppService:
    """身份与访问用例编排服务。"""

    def __init__(
        self,
        users: UserRepository = None,
        orgs: OrganizationRepository = None,
        roles: RoleRepository = None,
        invites: InvitationRepository = None,
    ):
        self._users: UserRepository = users or UserRepoAdapter()
        self._orgs: OrganizationRepository = orgs or OrganizationRepoAdapter()
        self._roles: RoleRepository = roles or RoleRepoAdapter()
        self._invites: InvitationRepository = invites or InvitationRepoAdapter()

    # ═══════════════════════════════════════════════════
    # 用户用例
    # ═══════════════════════════════════════════════════
    def create_user(self, cmd: CreateUserCommand) -> dict:
        user = User(
            user_id=self._users.next_id(),
            username=cmd.username,
            name=cmd.name or cmd.username,
            email=cmd.email,
            phone=cmd.phone,
            role=cmd.role,
        )
        if cmd.password:
            # 哈希在基础设施层调用既有安全工具落地
            self._users.save(user)
            self._users.change_password(user.id.value, cmd.password)
        else:
            self._users.save(user)
        self._publish(user)
        return user.to_dict()

    def get_user(self, user_id: str) -> Optional[dict]:
        u = self._users.find_by_id(user_id)
        return u.to_dict() if u else None

    def update_user(self, cmd: UpdateUserCommand) -> Optional[dict]:
        u = self._find_user(cmd.user_id)
        if cmd.name is not None:
            u.rename(cmd.name, cmd.operator)
        if cmd.email is not None:
            u.change_email(cmd.email, cmd.operator)
        if cmd.phone is not None:
            u._phone = cmd.phone
            u._touch()
        if cmd.role is not None:
            u._role = cmd.role
            u._touch()
        self._users.update(u)
        self._publish(u)
        return u.to_dict()

    def set_user_enabled(self, cmd: SetUserEnabledCommand) -> Optional[dict]:
        u = self._find_user(cmd.user_id)
        if cmd.enabled:
            u.enable(cmd.operator)
        else:
            u.disable(cmd.operator)
        self._users.update(u)
        self._publish(u)
        return u.to_dict()

    def change_password(self, cmd: ChangePasswordCommand) -> bool:
        u = self._find_user(cmd.user_id)
        if cmd.old_password and cmd.new_password:
            # 走带旧密码校验的既有接口
            ok = IdentityRepo().change_password(cmd.user_id, cmd.old_password, cmd.new_password)
            if ok:
                u.change_password(cmd.operator)
                self._publish(u)
            return ok
        if cmd.new_password:
            ok = self._users.change_password(cmd.user_id, cmd.new_password)
            if ok:
                u.change_password(cmd.operator)
                self._publish(u)
            return ok
        raise DomainValidationError("缺少新密码")

    def list_users(self, query: UserListQuery) -> dict:
        items, total = self._users.list(search=query.search, limit=query.limit,
                                        offset=query.offset)
        return {"list": [u.to_dict() for u in items], "total": total}

    # ═══════════════════════════════════════════════════
    # 组织用例
    # ═══════════════════════════════════════════════════
    def create_organization(self, cmd: CreateOrganizationCommand) -> dict:
        org = Organization(
            org_id=self._orgs.next_id(),
            name=cmd.name,
            description=cmd.description,
        )
        self._orgs.save(org)
        self._publish(org)
        return org.to_dict()

    def get_organization(self, org_id: str) -> Optional[dict]:
        org = self._orgs.find_by_id(org_id)
        return org.to_dict() if org else None

    def update_organization(self, cmd: UpdateOrganizationCommand) -> Optional[dict]:
        org = self._find_org(cmd.org_id)
        if cmd.name is not None:
            org.rename(cmd.name, cmd.operator)
        if cmd.description is not None:
            org.change_description(cmd.description, cmd.operator)
        self._persist_org(org)
        self._publish(org)
        return org.to_dict()

    def set_organization_enabled(self, org_id: str, enabled: bool, operator: str = "system") -> Optional[dict]:
        org = self._find_org(org_id)
        if enabled:
            org.enable(operator)
        else:
            org.disable(operator)
        self._orgs.update(org)
        # 同步存储层 status
        if enabled:
            OrganizationRepo.enable(org_id)
        else:
            OrganizationRepo.disable(org_id)
        self._publish(org)
        return org.to_dict()

    def add_member(self, cmd: AddMemberCommand) -> dict:
        org = self._find_org(cmd.org_id)
        member = org.add_member(
            member_id=self._orgs.next_id(),
            user_id=cmd.user_id,
            role=cmd.role,
            operator=cmd.operator,
        )
        row = OrganizationRepo.add_member(cmd.org_id, cmd.user_id, role=cmd.role)
        self._publish(org)
        if row is None:
            # 兼容：返回已重建聚合内成员
            return member.to_dict()
        return dict(row)

    def change_member_role(self, cmd: ChangeMemberRoleCommand) -> dict:
        org = self._find_org(cmd.org_id)
        org.change_member_role(cmd.user_id, cmd.role, cmd.operator)
        self._orgs.persist_member_change(org, cmd.user_id, cmd.role)
        self._publish(org)
        return org.to_dict()

    def remove_member(self, org_id: str, user_id: str, operator: str = "system") -> bool:
        org = self._find_org(org_id)
        org.remove_member(user_id, operator)
        OrganizationRepo.remove_member(org_id, user_id)
        self._publish(org)
        return True

    def list_organizations(self, query: OrganizationListQuery) -> dict:
        items, total = self._orgs.list(search=query.search, status=query.status,
                                       limit=query.limit, offset=query.offset)
        return {"list": [o.to_dict() for o in items], "total": total}

    # ═══════════════════════════════════════════════════
    # 角色用例
    # ═══════════════════════════════════════════════════
    def create_role(self, cmd: CreateRoleCommand) -> dict:
        role = Role(
            role_id=self._roles.next_id(),
            name=cmd.name,
            description=cmd.description,
            group_type=cmd.group_type,
            scope_id=cmd.scope_id,
            permissions=cmd.permissions,
        )
        self._roles.save(role)
        self._publish(role)
        return role.to_dict()

    def get_role(self, role_id: str) -> Optional[dict]:
        role = self._roles.find_by_id(role_id)
        return role.to_dict() if role else None

    def update_role(self, cmd: UpdateRoleCommand) -> Optional[dict]:
        role = self._find_role(cmd.role_id)
        if cmd.name is not None:
            role.rename(cmd.name, cmd.operator)
        if cmd.description is not None:
            role._description = cmd.description
            role._touch()
        if cmd.permissions is not None:
            role.set_permissions(cmd.permissions, cmd.operator)
        self._roles.update(role)
        self._publish(role)
        return role.to_dict()

    def delete_role(self, role_id: str, operator: str = "system") -> bool:
        role = self._find_role(role_id)
        role.delete(operator)
        ok = self._roles.delete(role_id)
        self._publish(role)
        return ok

    def list_roles(self, group_type: str = "SYSTEM") -> dict:
        items, total = self._roles.list(group_type=group_type)
        return {"list": [r.to_dict() for r in items], "total": total}

    # ═══════════════════════════════════════════════════
    # 邀请用例
    # ═══════════════════════════════════════════════════
    def issue_invitation(self, cmd: IssueInvitationCommand) -> dict:
        if not (cmd.email or "").strip() or "@" not in cmd.email:
            raise DomainValidationError(f"邮箱格式不合法: {cmd.email}")
        from app.domain.identity.domain.entities.invitation import Invitation
        inv_obj = Invitation(
            invite_id=self._invites.next_id(),
            email=cmd.email,
            scope=cmd.scope,
            organization_id=cmd.organization_id,
            project_id=cmd.project_id,
            role_ids=cmd.role_ids,
            create_user=cmd.create_user,
        )
        self._invites.save(inv_obj)
        inv_obj.mark_issued(cmd.operator)
        self._publish(inv_obj)
        return inv_obj.to_dict()

    def get_invitation(self, invite_id: str) -> Optional[dict]:
        inv = self._invites.find_by_invite_id(invite_id)
        return inv.to_dict() if inv else None

    def accept_invitation(self, invite_id: str, operator: str = "system") -> dict:
        inv = self._invites.find_by_invite_id(invite_id)
        if inv is None:
            raise AggregateNotFound(f"邀请不存在: {invite_id}")
        inv.accept(operator)
        self._invites.mark_used(invite_id)
        self._publish(inv)
        return inv.to_dict()

    # ═══════════════════════════════════════════════════
    # 组织旁路方法（组织 CRUD 完整面 / 成员查询 / 项目绑定 / 租户摘要）
    # 与 organization_service 方法面对齐的薄委托：直接转发既有 OrganizationRepo。
    # ═══════════════════════════════════════════════════
    def delete_organization(self, org_id: str, hard: bool = False) -> bool:
        """删除组织（soft/hard）。"""
        return OrganizationRepo.delete(org_id, hard=hard)

    def recover_organization(self, org_id: str) -> bool:
        """恢复已删除组织。"""
        return OrganizationRepo.recover(org_id)

    def get_organization_by_name(self, name: str) -> Optional[dict]:
        """按名称获取组织（未删除；薄委托既有 OrganizationRepo 保持行 schema）。"""
        return OrganizationRepo.get_by_name(name)

    def count_organizations(self, search: str = "") -> int:
        """统计组织数。"""
        return OrganizationRepo.count(search=search)

    def list_members(self, org_id: str, search: str = "",
                     limit: int = 100) -> list:
        """列出组织成员（薄委托既有 OrganizationRepo，保持既有行 schema）。"""
        return OrganizationRepo.list_members(org_id, search=search, limit=limit)

    def get_member(self, member_id: str) -> Optional[dict]:
        """按成员 id 获取组织成员行。"""
        return OrganizationRepo.get_member(member_id)

    def count_members(self, org_id: str) -> int:
        """统计组织成员数。"""
        return OrganizationRepo.count_members(org_id)

    def list_orgs_by_user(self, user_id: str) -> list:
        """反查用户所属的所有组织（未删除）。"""
        return OrganizationRepo.list_orgs_by_user(user_id)

    def list_orgs_by_users(self, user_ids: list) -> dict:
        """批量反查多个用户所属的组织。"""
        return OrganizationRepo.list_orgs_by_users(user_ids)

    def list_projects(self, org_id: str) -> list:
        """列出组织绑定的项目。"""
        return OrganizationRepo.list_projects(org_id)

    def bind_project(self, project_id: str, org_id: str) -> bool:
        """绑定项目到组织。"""
        return OrganizationRepo.bind_project(project_id, org_id)

    def tenant_summary(self) -> dict:
        """租户摘要统计。"""
        return OrganizationRepo.tenant_summary()

    def get_tenant_summary(self) -> dict:
        """租户摘要（兼容命名）。"""
        return OrganizationRepo.get_tenant_summary()
    # API Key 用例
    # ═══════════════════════════════════════════════════
    def list_api_keys(self, query: "ListApiKeysQuery" = None) -> list:
        """列出用户 API Key（对接既有 AuthRepo，auth 旁路覆盖）。"""
        uid = (query.user_id if query else "") or ""
        return AuthRepo().list_api_keys(uid)

    def create_api_key(self, cmd: "CreateApiKeyCommand") -> dict:
        """创建 API Key——薄委托既有 AuthRepo（api_keys 表为唯一权威）。"""
        return AuthRepo().create_api_key(
            cmd.user_id, description=cmd.description,
            forever=cmd.forever, expire_time=cmd.expire_time,
        )

    def revoke_api_key(self, cmd: "RevokeApiKeyCommand") -> bool:
        """吊销 API Key——落既有 AuthRepo（key 值存于 api_keys 表）。"""
        return AuthRepo().delete_api_key(cmd.key_id)

    def toggle_api_key(self, cmd: "ToggleApiKeyCommand") -> bool:
        """启停 API Key（落既有 AuthRepo）。"""
        return AuthRepo().toggle_api_key(cmd.key_id, cmd.enable)

    # ═══════════════════════════════════════════════════
    # 用户组成员用例（Role 聚合成员旁路覆盖）
    # ═══════════════════════════════════════════════════
    def list_group_members(self, query: "ListGroupMembersQuery") -> list:
        """列出用户组成员（对接既有 UserGroupRepo）。"""
        return UserGroupRepo.list_group_members(query.group_id, query.keyword or "")

    def add_group_member(self, cmd: "AddGroupMemberCommand") -> Optional[dict]:
        """添加用户组成员——薄委托既有 UserGroupRepo（成员表为唯一权威）。"""
        return UserGroupRepo.add_group_member(
            cmd.group_id, cmd.user_id,
            username=cmd.username or "", name=cmd.name or "", email=cmd.email or "",
            group_type=cmd.group_type or "SYSTEM", scope_id=cmd.scope_id or "",
        )

    def remove_group_member(self, cmd: "RemoveGroupMemberCommand") -> bool:
        """移除用户组成员（经既有 UserGroupRepo）。"""
        return UserGroupRepo.remove_group_member(cmd.group_id, cmd.user_id)

    def remove_group_member_by_id(self, user_role_id: str) -> bool:
        """按关联记录 id 移除用户组成员。"""
        return UserGroupRepo.remove_group_member_by_id(user_role_id)

    # ═══════════════════════════════════════════════════
    # 本地配置用例（local_config，用户级旁路覆盖）
    # ═══════════════════════════════════════════════════
    def add_local_config(self, cmd: "AddLocalConfigCommand") -> dict:
        """新增用户本地配置（落既有 AuthRepo）。"""
        return AuthRepo().add_local_config(cmd.user_id, cmd.user_url, cfg_type=cmd.cfg_type)

    def get_local_configs(self, user_id: str = "") -> list:
        """读取用户本地配置列表。"""
        return AuthRepo().get_local_configs(user_id)

    def update_local_config(self, cmd: "UpdateLocalConfigCommand") -> bool:
        """更新用户本地配置。"""
        return AuthRepo().update_local_config(cmd.cfg_id, cmd.user_url)

    def toggle_local_config(self, cmd: "ToggleLocalConfigCommand") -> bool:
        """启停用户本地配置。"""
        return AuthRepo().toggle_local_config(cmd.cfg_id, cmd.enable)

    # ═══════════════════════════════════════════════════
    # 内部助手
    # ═══════════════════════════════════════════════════
    def _find_user(self, user_id: str) -> User:
        u = self._users.find_by_id(user_id)
        if u is None:
            raise AggregateNotFound(f"用户不存在: {user_id}")
        return u

    def _find_org(self, org_id: str) -> Organization:
        org = self._orgs.find_by_id(org_id)
        if org is None:
            raise AggregateNotFound(f"组织不存在: {org_id}")
        return org

    def _find_role(self, role_id: str) -> Role:
        role = self._roles.find_by_id(role_id)
        if role is None:
            raise AggregateNotFound(f"角色不存在: {role_id}")
        return role

    def _persist_org(self, org: Organization) -> None:
        data = {"name": org.name, "description": org.description}
        if org.enabled:
            data["status"] = "active"
        else:
            data["status"] = "disabled"
        OrganizationRepo.update(org.id.value, data)

    def _publish(self, agg: AggregateRoot) -> None:
        for ev in agg.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
identity_app_service = IdentityAppService()
