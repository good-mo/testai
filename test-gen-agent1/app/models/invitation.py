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
