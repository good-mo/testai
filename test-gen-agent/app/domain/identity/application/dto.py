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


# ==============================================================================
# 从 models/invitation.py 迁移
# ==============================================================================

# app/models/invitation.py
"""邀请注册（invitation）域 Pydantic 请求体模型。

字段自 system_compat / system_compat_extra / project_compat_member 中
`read_body` 实际使用的邀请请求体归纳。三个 scope（SYSTEM / ORGANIZATION /
PROJECT）共用同一请求体，仅前端字段名不同。
"""

from typing import Any, List

from pydantic import BaseModel, Field

SCOPE_SYSTEM = "SYSTEM"
SCOPE_ORGANIZATION = "ORGANIZATION"
SCOPE_PROJECT = "PROJECT"


class InviteCreateBody(BaseModel):
    """创建邀请（inviteUser / inviteOrgMember / inviteMember）。

    前端三种场景请求体字段一致：
      {inviteEmails: [], userRoleIds: [], organizationId?, projectId?}
    邮箱/角色兼容 str（逗号分隔）或 list 两种形态。
    """

    inviteEmails: Any = Field([], description="被邀请邮箱（str 或 list）")
    emails: Any = Field([], description="邮箱（别名）")
    emailList: Any = Field([], description="邮箱列表（别名）")
    userRoleIds: Any = Field([], description="角色（用户组）ID（str 或 list）")
    roleIds: Any = Field([], description="角色 ID（别名）")
    organizationId: str = Field("", description="组织 ID")
    orgId: str = Field("", description="组织 ID（别名）")
    organization_id: str = Field("", description="组织 ID（别名）")
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID（别名）")
    project: str = Field("", description="项目 ID（别名）")
    scope: str = Field(SCOPE_SYSTEM, description="邀请范围：SYSTEM/ORGANIZATION/PROJECT")

    @property
    def effective_emails(self) -> List[str]:
        for key in ("inviteEmails", "emails", "emailList"):
            val = getattr(self, key)
            if isinstance(val, str):
                return [e.strip() for e in val.split(",") if e.strip()]
            if isinstance(val, list):
                return [str(e) for e in val if e]
        return []

    @property
    def effective_role_ids(self) -> List[str]:
        for key in ("userRoleIds", "roleIds"):
            val = getattr(self, key)
            if isinstance(val, str):
                return [r.strip() for r in val.split(",") if r.strip()]
            if isinstance(val, list):
                return [str(r) for r in val if r]
        return []

    @property
    def effective_organization_id(self) -> str:
        return self.organizationId or self.orgId or self.organization_id or "default-org"

    @property
    def effective_project_id(self) -> str:
        return self.projectId or self.project_id or self.project or ""

    model_config = {"extra": "allow"}


__all__ = [
    "SCOPE_SYSTEM",
    "SCOPE_ORGANIZATION",
    "SCOPE_PROJECT",
    "InviteCreateBody",
]


# ==============================================================================
# 从 models/user_role.py 迁移
# ==============================================================================

# app/models/user_role.py
"""用户组 / 视图（用户角色）域 Pydantic 请求体模型。

字段自 `app/routers/system_compat_userrole.py` 中 `/user/role/*`、
`/user/platform/*`、`/user/api/key/*` 各 POST 处理器 `read_body()`
实际读取的请求体归纳。

旧实现依赖 `read_body()` 的宽松归一化（空体→{}、裸字符串→{"id": x}、
数组→{"ids":[...]}），故各请求体模型继承 `_LenientRequest` 保留该语义，
避免旧前端（axios 把 params 当 body 发送）被判 422。所有模型 `extra:
allow`，防止遗漏历史调用中新增的字段导致丢字段。
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量/数组/空请求体。

    迁移背景：旧路由用 read_body() 读取请求体时，会把裸字符串 `"x"`
    归一化成 `{"id": "x"}`、数组归一化成 `{"ids": [...]}`、空体归一化
    成 `{}`（见 app/core/response.py）。改用 Pydantic 请求体模型后，
    若不处理，FastAPI 会把上述裸标量判为 422。此处把同一段归一化上移
    到模型层，保证历史调用不被类型校验打断。
    """

    @model_validator(mode="before")
    @classmethod
    def _lenient_coerce(cls, raw):
        if isinstance(raw, str):
            return {"id": raw}
        if isinstance(raw, list):
            return {"ids": raw}
        if raw is None:
            return {}
        return raw


class UserRoleProjectAddBody(_LenientRequest):
    """添加项目用户组。

    读取字段：name / scopeId / id（id 用于数据库不可用时的兜底返回）。
    """

    name: str = Field("未命名用户组", description="用户组名称")
    scopeId: str = Field("", description="所属项目 scopeId")
    id: Optional[str] = Field("", description="用户组 ID（兜底用）")

    model_config = {"extra": "allow"}


class UserRoleProjectUpdateBody(_LenientRequest):
    """更新项目用户组。

    读取字段：id / name / description。
    """

    id: str = Field("", description="用户组 ID")
    name: Optional[str] = Field(None, description="用户组新名称")
    description: Optional[str] = Field(None, description="用户组描述")

    model_config = {"extra": "allow"}


class UserRoleProjectListBody(_LenientRequest):
    """项目用户组列表（分页）。

    读取字段：projectId / keyword / current / pageSize。
    """

    projectId: str = Field("project", description="所属项目 ID")
    keyword: str = Field("", description="搜索关键字")
    current: int = Field(1, description="页码")
    pageSize: int = Field(10, description="每页条数")

    model_config = {"extra": "allow"}


class UserRoleProjectListMemberBody(_LenientRequest):
    """项目用户组成员列表（分页）。

    读取字段：projectId / userRoleId / keyword / current / pageSize。
    """

    projectId: str = Field("", description="所属项目 ID")
    userRoleId: str = Field("", description="用户组 ID")
    keyword: str = Field("", description="搜索关键字")
    current: int = Field(1, description="页码")
    pageSize: int = Field(10, description="每页条数")

    model_config = {"extra": "allow"}


class UserRoleProjectPermissionUpdateBody(_LenientRequest):
    """更新项目用户组权限。

    读取字段：userRoleId（或别名 groupId/id）/ permissions。
    """

    userRoleId: Optional[str] = Field(None, description="用户组 ID（优先）")
    groupId: Optional[str] = Field(None, description="用户组 ID（别名）")
    id: Optional[str] = Field(None, description="用户组 ID（别名）")
    permissions: List[Any] = Field([], description="权限列表 [{id, enable} 或 权限ID]")

    @property
    def effective_role_id(self) -> str:
        return (self.userRoleId or self.groupId or self.id or "")

    model_config = {"extra": "allow"}


class UserRoleProjectMemberBody(_LenientRequest):
    """项目用户组添加/移除成员（共用）。

    读取字段：projectId / userRoleId / userIds（兼容字符串或数组）。
    """

    projectId: str = Field("", description="所属项目 ID")
    userRoleId: str = Field("", description="用户组 ID")
    userIds: Any = Field([], description="成员用户 ID（字符串或数组）")

    @property
    def effective_user_ids(self) -> List[str]:
        v = self.userIds
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            return []
        return [str(u) for u in v if u]

    model_config = {"extra": "allow"}


class UserPlatformSaveBody(_LenientRequest):
    """保存用户平台（无必需字段，仅承载任意请求体）。"""

    model_config = {"extra": "allow"}


class UserApiKeyUpdateBody(_LenientRequest):
    """更新 API Key 请求体（无必需字段）。"""

    model_config = {"extra": "allow"}


__all__ = [
    "UserRoleProjectAddBody",
    "UserRoleProjectUpdateBody",
    "UserRoleProjectListBody",
    "UserRoleProjectListMemberBody",
    "UserRoleProjectPermissionUpdateBody",
    "UserRoleProjectMemberBody",
    "UserPlatformSaveBody",
    "UserApiKeyUpdateBody",
]
