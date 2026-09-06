"""组织/成员/认证领域层（domain layer）。

仅表达业务概念与规则（User/Organization/Member/Role/Invitation 聚合、
角色权限不变量），不依赖 FastAPI / sqlite / 具体存储实现。
"""
from app.domain.identity.domain.entities.invitation import Invitation
from app.domain.identity.domain.entities.organization import Organization
from app.domain.identity.domain.entities.role import Role
from app.domain.identity.domain.entities.user import User
from app.domain.identity.domain.repository import (
    InvitationRepository,
    OrganizationRepository,
    RoleRepository,
    UserRepository,
)
from app.domain.identity.domain.value_objects.account_status import (
    AccountStatus,
    AccountStatusEnum,
)
from app.domain.identity.domain.value_objects.invitation_status import (
    InvitationStatus,
    InvitationStatusEnum,
)
from app.domain.identity.domain.value_objects.member_role import (
    MemberRole,
    MemberRoleEnum,
)
from app.domain.identity.domain.value_objects.permission import PermissionSet

__all__ = [
    "User", "Organization", "Role", "Invitation",
    "UserRepository", "OrganizationRepository", "RoleRepository", "InvitationRepository",
    "AccountStatus", "AccountStatusEnum",
    "InvitationStatus", "InvitationStatusEnum",
    "MemberRole", "MemberRoleEnum",
    "PermissionSet",
]
