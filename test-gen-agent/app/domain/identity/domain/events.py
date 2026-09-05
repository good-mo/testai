"""组织/成员/认证领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，
进而驱动审计日志、通知、索引等副作用（跨聚合/跨域解耦）。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent

__all__ = [
    # User
    "UserCreated", "UserRenamed", "UserEmailChanged", "UserPasswordChanged",
    "UserDisabled", "UserEnabled", "ApiKeyCreated", "ApiKeyRevoked",
    # Organization
    "OrganizationCreated", "OrganizationRenamed", "OrganizationDisabled",
    "OrganizationEnabled", "MemberAdded", "MemberRoleChanged", "MemberRemoved",
    # UserGroup / Role
    "RoleCreated", "RoleRenamed", "RoleDeleted", "PermissionGranted",
    # Invitation
    "InvitationIssued", "InvitationAccepted", "InvitationRevoked",
]


# ── 用户 ────────────────────────────────────────────────
class UserCreated(DomainEvent):
    def __init__(self, user_id: str, username: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.username = username
        self.operator = operator


class UserRenamed(DomainEvent):
    def __init__(self, user_id: str, username: str, new_name: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.username = username
        self.new_name = new_name
        self.operator = operator


class UserEmailChanged(DomainEvent):
    def __init__(self, user_id: str, old_email: str, new_email: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.old_email = old_email
        self.new_email = new_email
        self.operator = operator


class UserPasswordChanged(DomainEvent):
    def __init__(self, user_id: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.operator = operator


class UserDisabled(DomainEvent):
    def __init__(self, user_id: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.operator = operator


class UserEnabled(DomainEvent):
    def __init__(self, user_id: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.operator = operator


class ApiKeyCreated(DomainEvent):
    def __init__(self, user_id: str, key_id: str, description: str = ""):
        super().__init__(aggregate_id=user_id)
        self.key_id = key_id
        self.description = description


class ApiKeyRevoked(DomainEvent):
    def __init__(self, user_id: str, key_id: str, operator: str = "system"):
        super().__init__(aggregate_id=user_id)
        self.key_id = key_id
        self.operator = operator


# ── 组织 ────────────────────────────────────────────────
class OrganizationCreated(DomainEvent):
    def __init__(self, org_id: str, name: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.name = name
        self.operator = operator


class OrganizationRenamed(DomainEvent):
    def __init__(self, org_id: str, old_name: str, new_name: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.old_name = old_name
        self.new_name = new_name
        self.operator = operator


class OrganizationDisabled(DomainEvent):
    def __init__(self, org_id: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.operator = operator


class OrganizationEnabled(DomainEvent):
    def __init__(self, org_id: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.operator = operator


class MemberAdded(DomainEvent):
    def __init__(self, org_id: str, user_id: str, role: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.user_id = user_id
        self.role = role
        self.operator = operator


class MemberRoleChanged(DomainEvent):
    def __init__(self, org_id: str, user_id: str, old_role: str, new_role: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role
        self.operator = operator


class MemberRemoved(DomainEvent):
    def __init__(self, org_id: str, user_id: str, operator: str = "system"):
        super().__init__(aggregate_id=org_id)
        self.user_id = user_id
        self.operator = operator


# ── 角色 / 用户组 ──────────────────────────────────────
class RoleCreated(DomainEvent):
    def __init__(self, group_id: str, name: str, operator: str = "system"):
        super().__init__(aggregate_id=group_id)
        self.name = name
        self.operator = operator


class RoleRenamed(DomainEvent):
    def __init__(self, group_id: str, old_name: str, new_name: str, operator: str = "system"):
        super().__init__(aggregate_id=group_id)
        self.old_name = old_name
        self.new_name = new_name
        self.operator = operator


class RoleDeleted(DomainEvent):
    def __init__(self, group_id: str, operator: str = "system"):
        super().__init__(aggregate_id=group_id)
        self.operator = operator


class PermissionGranted(DomainEvent):
    def __init__(self, group_id: str, permissions: list, operator: str = "system"):
        super().__init__(aggregate_id=group_id)
        self.permissions = list(permissions)
        self.operator = operator


# ── 邀请 ────────────────────────────────────────────────
class InvitationIssued(DomainEvent):
    def __init__(self, invite_id: str, email: str, scope: str = "SYSTEM", operator: str = "system"):
        super().__init__(aggregate_id=invite_id)
        self.email = email
        self.scope = scope
        self.operator = operator


class InvitationAccepted(DomainEvent):
    def __init__(self, invite_id: str, email: str, operator: str = "system"):
        super().__init__(aggregate_id=invite_id)
        self.email = email
        self.operator = operator


class InvitationRevoked(DomainEvent):
    def __init__(self, invite_id: str, operator: str = "system"):
        super().__init__(aggregate_id=invite_id)
        self.operator = operator
