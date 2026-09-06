"""身份与访问应用层输入/输出 DTO。

应用层面向"用户/组织/角色/邀请"操作接收显式 DTO（而非裸 dict），与 Web 层
Pydantic 请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ── 用户 ────────────────────────────────────────────────
@dataclass
class CreateUserCommand:
    username: str
    password: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    role: str = "user"
    operator: str = "system"


@dataclass
class UpdateUserCommand:
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    operator: str = "system"


@dataclass
class ChangePasswordCommand:
    user_id: str
    old_password: str = ""
    new_password: str = ""
    operator: str = "system"


@dataclass
class SetUserEnabledCommand:
    user_id: str
    enabled: bool
    operator: str = "system"


@dataclass
class UserListQuery:
    search: str = ""
    limit: int = 100
    offset: int = 0


# ── 组织 ────────────────────────────────────────────────
@dataclass
class CreateOrganizationCommand:
    name: str
    description: str = ""
    create_user: str = "admin"
    operator: str = "system"


@dataclass
class UpdateOrganizationCommand:
    org_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    operator: str = "system"


@dataclass
class AddMemberCommand:
    org_id: str
    user_id: str
    role: str = "member"
    operator: str = "system"


@dataclass
class ChangeMemberRoleCommand:
    org_id: str
    user_id: str
    role: str
    operator: str = "system"


@dataclass
class OrganizationListQuery:
    search: str = ""
    status: str = ""
    limit: int = 100
    offset: int = 0


# ── 角色 ────────────────────────────────────────────────
@dataclass
class CreateRoleCommand:
    name: str
    description: str = ""
    group_type: str = "SYSTEM"
    scope_id: str = ""
    permissions: List[str] = field(default_factory=list)
    operator: str = "system"


@dataclass
class UpdateRoleCommand:
    role_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    operator: str = "system"


# ── 邀请 ────────────────────────────────────────────────
@dataclass
class IssueInvitationCommand:
    email: str
    scope: str = "SYSTEM"
    organization_id: str = ""
    project_id: str = ""
    role_ids: List[str] = field(default_factory=list)
    create_user: str = "admin"
    operator: str = "system"


# ── API Key ────────────────────────────────────────────
@dataclass
class ListApiKeysQuery:
    user_id: str = ""


@dataclass
class CreateApiKeyCommand:
    user_id: str
    description: str = ""
    forever: bool = False
    expire_time: int = 0
    operator: str = "system"


@dataclass
class RevokeApiKeyCommand:
    key_id: str
    operator: str = "system"


@dataclass
class ToggleApiKeyCommand:
    key_id: str
    enable: bool
    operator: str = "system"


# ── 用户组成员管理（Role 聚合的成员旁路）───────────────
@dataclass
class ListGroupMembersQuery:
    group_id: str
    keyword: str = ""


@dataclass
class AddGroupMemberCommand:
    group_id: str
    user_id: str
    username: str = ""
    name: str = ""
    email: str = ""
    group_type: str = "SYSTEM"
    scope_id: str = ""
    operator: str = "system"


@dataclass
class RemoveGroupMemberCommand:
    group_id: str
    user_id: str
    operator: str = "system"


# ── 本地配置（local_config，用户级旁路）────────────────
@dataclass
class AddLocalConfigCommand:
    user_id: str
    user_url: str
    cfg_type: str = "API"
    operator: str = "system"


@dataclass
class UpdateLocalConfigCommand:
    cfg_id: str
    user_url: str
    operator: str = "system"


@dataclass
class ToggleLocalConfigCommand:
    cfg_id: str
    enable: bool
    operator: str = "system"
