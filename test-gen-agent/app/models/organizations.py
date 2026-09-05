# app/models/organizations.py
"""组织（租户）域 Pydantic 请求体模型。

覆盖组织项目/组织成员等兼容路由请求体，字段为 TestPilot 风格驼峰，兼容
read_body() 归一化语义（空体/裸标量）。业务入口统一走
app.services.organization_service。
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


# ════════════════════════════════════════════════════════════
# 组织域兼容路由请求体（app/routers/organizations.py 使用）
# ------------------------------------------------------------
# 历史前端通过 axios 拦截器可能发送裸标量，故统一继承 _LenientRequest
# 以保留 read_body() 的空体/裸标量归一化语义（见 app/core/response.py）。
# 所有模型默认 extra=allow，兼容前端附加字段。
# ════════════════════════════════════════════════════════════


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量请求体。"""

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


# ── 组织项目分页 / 列表 ─────────────────────────────────


class OrgProjectPageQuery(_LenientRequest):
    """组织项目分页（org_project_page）。"""

    organizationId: str = Field("", description="组织 ID（驼峰别名）")
    orgId: str = Field("", description="组织 ID（别名）")
    keyword: str = Field("", description="搜索关键字")
    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")

    model_config = {"extra": "allow"}


class OrgProjectCreateBody(_LenientRequest):
    """组织添加项目（org_project_add）。"""

    organizationId: str = Field("default-org", description="组织 ID")
    name: str = Field("新项目", description="项目名称")
    description: str = Field("", description="项目描述")

    model_config = {"extra": "allow"}


class OrgProjectUpdateBody(_LenientRequest):
    """组织更新项目（org_project_update）。

    除固定字段外，name/description/status 等更新字段经 extra=allow 透传。
    """

    id: str = Field("", description="项目 ID")
    projectId: str = Field("", description="项目 ID（别名）")
    organizationId: str = Field("", description="组织 ID")
    userIds: Any = Field([], description="管理员用户 ID 列表")

    model_config = {"extra": "allow"}


class OrgProjectRenameBody(_LenientRequest):
    """组织重命名项目（org_project_rename）。"""

    id: str = Field("", description="项目 ID")
    projectId: str = Field("", description="项目 ID（别名）")
    name: str = Field("", description="新名称")

    model_config = {"extra": "allow"}


# ── 组织项目成员 ─────────────────────────────────────────


class OrgProjectMemberAddBody(_LenientRequest):
    """组织项目添加成员（org_project_add_member）。"""

    projectId: str = Field("", description="项目 ID")
    id: str = Field("", description="项目 ID（别名）")
    userIds: Any = Field([], description="用户 ID 列表")
    memberIds: Any = Field([], description="用户 ID 列表（别名）")
    role: str = Field("member", description="角色: admin/member")

    model_config = {"extra": "allow"}


class OrgProjectMembersAddBody(_LenientRequest):
    """组织项目批量添加成员（org_project_add_members）。"""

    projectId: str = Field("", description="项目 ID")
    id: str = Field("", description="项目 ID（别名）")
    organizationId: str = Field("", description="组织 ID")
    userIds: Any = Field([], description="用户 ID 列表")
    memberIds: Any = Field([], description="用户 ID 列表（别名）")
    role: str = Field("member", description="角色: admin/member")

    model_config = {"extra": "allow"}


class OrgProjectMemberPageQuery(_LenientRequest):
    """组织项目成员分页（org_project_member_list_post）。"""

    projectId: str = Field("", description="项目 ID")
    id: str = Field("", description="项目 ID（别名）")
    keyword: str = Field("", description="搜索关键字")
    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")

    model_config = {"extra": "allow"}


# ── 组织成员 ─────────────────────────────────────────────


class OrgMemberListPageQuery(_LenientRequest):
    """组织成员分页（org_member_list_post）。"""

    organizationId: str = Field("default-org", description="组织 ID")
    orgId: str = Field("", description="组织 ID（别名）")
    keyword: str = Field("", description="搜索关键字")
    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")

    model_config = {"extra": "allow"}


class OrgMemberAddBody(_LenientRequest):
    """组织添加成员（org_add_member）。"""

    organizationId: str = Field("default-org", description="组织 ID")
    orgId: str = Field("", description="组织 ID（别名）")
    memberIds: Any = Field([], description="成员 ID 列表")
    userIds: Any = Field([], description="成员 ID 列表（别名）")
    userRoleIds: Any = Field([], description="用户组 ID 列表")

    model_config = {"extra": "allow"}


class OrgMemberRemoveBody(_LenientRequest):
    """组织移除成员（org_remove_member POST body）。"""

    organizationId: str = Field("", description="组织 ID")
    orgId: str = Field("", description="组织 ID（别名）")
    sourceId: str = Field("", description="来源组织 ID（别名）")
    userId: Any = Field("", description="用户 ID")
    userIds: Any = Field("", description="用户 ID（数组或单个）")
    memberId: str = Field("", description="成员 ID（别名）")

    model_config = {"extra": "allow"}


class OrgMemberUpdateBody(_LenientRequest):
    """组织更新成员（org_update_member）。"""

    organizationId: str = Field("", description="组织 ID")
    orgId: str = Field("", description="组织 ID（别名）")
    memberId: str = Field("", description="成员 ID")
    userId: str = Field("", description="用户 ID（别名）")
    id: str = Field("", description="成员 ID（别名）")
    role: str = Field("", description="角色: admin/member")
    userRoleIds: Any = Field([], description="用户组 ID 列表")
    roleIds: Any = Field([], description="用户组 ID 列表（别名）")
    projectIds: Any = Field([], description="项目 ID 列表")

    model_config = {"extra": "allow"}


class OrgRoleUpdateMemberBody(_LenientRequest):
    """更新成员角色/批量加入用户组（org_role_update_member）。"""

    organizationId: str = Field("", description="组织 ID")
    orgId: str = Field("", description="组织 ID（别名）")
    memberIds: Any = Field([], description="成员 ID 列表")
    userIds: Any = Field([], description="成员 ID 列表（别名）")
    userRoleIds: Any = Field([], description="用户组 ID 列表")
    roleIds: Any = Field([], description="用户组 ID 列表（别名）")

    model_config = {"extra": "allow"}
