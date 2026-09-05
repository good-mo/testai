# app/models/system_compat.py
"""system_compat 域兼容路由请求体模型。

对应 `app/routers/system_compat.py` 中手写 `read_body` + `.get()` 解析的
POST/GET 兼容端点。涵盖组织管理 / 组织成员 / 项目成员 / 系统用户 / 视图 /
模板等跨域操作，各 body 独立建档，保持与旧 `read_body` 归一化一致的宽松
语义（空体/裸标量/数组不抛 422），接入后行为零回归。
"""

from typing import Any, List

from pydantic import BaseModel, Field, model_validator


def _first(*values: Any, default: Any = "") -> Any:
    """返回首个非空值（None 与空串视为缺省，对齐旧 .get(key, default) 语义）。"""
    for v in values:
        if v is not None and v != "":
            return v
    return default


def _int(val: Any, default: int) -> int:
    """宽松转 int，失败回落 default。"""
    try:
        return int(val) if val is not None and val != "" else default
    except (TypeError, ValueError):
        return default


def _to_list(val: Any) -> List[Any]:
    """宽松转列表：str（逗号分隔）或标量 -> list。"""
    if val is None:
        return []
    if isinstance(val, str):
        return [x.strip() for x in val.split(",") if x.strip()]
    if isinstance(val, (list, tuple)):
        return list(val)
    return [val]


class _LenientRequest(BaseModel):
    """历史兼容：容忍裸字符串/数组/空请求体，语义与旧 read_body 一致。"""

    model_config = {"extra": "allow", "populate_by_name": True}

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


class _LenientPageBody(_LenientRequest):
    """通用宽松分页基类：current/pageSize 兼容驼峰与整型字符串。"""

    current: Any = Field(None, description="当前页")
    pageSize: Any = Field(None, description="每页条数")
    keyword: Any = Field(None, description="搜索关键字")

    @property
    def effective_current(self) -> int:
        return _int(self.current, 1)

    @property
    def effective_page_size(self) -> int:
        return _int(self.pageSize, 10)

    @property
    def effective_keyword(self) -> str:
        return str(_first(self.keyword, default="")).strip()


class SysOrgPageBody(_LenientPageBody):
    """系统组织列表分页（/system/organization/list）。

    兼容字段：keyword / pageSize / current / organizationId / orgId。
    """

    organizationId: Any = Field(None, description="组织 ID（驼峰）")
    orgId: Any = Field(None, description="组织 ID（别名）")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.organizationId, self.orgId, default=""))


class OrgProjectUserListPageBody(_LenientPageBody):
    """组织项目用户列表分页（/organization/project/user-list）。

    兼容字段：organizationId / orgId / current / pageSize / keyword。
    """

    organizationId: Any = Field(None, description="组织 ID（驼峰）")
    orgId: Any = Field(None, description="组织 ID（别名）")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.organizationId, self.orgId, default=""))


class SystemProjectPageBody(_LenientPageBody):
    """系统项目分页 POST（/system/project/page）。

    兼容字段：current / pageSize / keyword。
    """


class SysOrgIdBody(_LenientRequest):
    """组织 CRUD 通用 body：取 id / orgId / organizationId 任意一个。"""

    id: Any = Field(None, description="组织 ID（优先）")
    orgId: Any = Field(None, description="组织 ID（别名）")
    organizationId: Any = Field(None, description="组织 ID（别名）")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.id, self.orgId, self.organizationId, default=""))


class SysOrgRenameBody(_LenientRequest):
    """重命名组织（/system/organization/rename）。

    兼容字段：id / orgId + name。
    """

    id: Any = Field(None, description="组织 ID")
    orgId: Any = Field(None, description="组织 ID（别名）")
    name: Any = Field(None, description="新名称")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.id, self.orgId, default=""))

    @property
    def effective_name(self) -> str:
        return str(_first(self.name, default=""))


class SysOrgAddMemberBody(_LenientRequest):
    """组织添加成员（/system/organization/add-member）。

    兼容字段：organizationId / orgId + userIds + role。
    """

    organizationId: Any = Field(None, description="组织 ID")
    orgId: Any = Field(None, description="组织 ID（别名）")
    userIds: Any = Field(None, description="用户 ID 列表")
    role: Any = Field(None, description="角色，缺省 member")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.organizationId, self.orgId, default="default-org"))

    @property
    def effective_user_ids(self) -> List[str]:
        return [str(x) for x in _to_list(self.userIds)]

    @property
    def effective_role(self) -> str:
        return str(_first(self.role, default="member"))


class SysOrgRemoveMemberBody(_LenientRequest):
    """组织移除成员（/system/organization/remove-member/）。

    兼容字段：organizationId / orgId / sourceId + userId / userIds。
    """

    organizationId: Any = Field(None, description="组织 ID")
    orgId: Any = Field(None, description="组织 ID（别名）")
    sourceId: Any = Field(None, description="来源组织 ID（别名）")
    userId: Any = Field(None, description="用户 ID")
    userIds: Any = Field(None, description="用户 ID（单个或多个）")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.organizationId, self.orgId, self.sourceId, default=""))

    @property
    def effective_user_id(self) -> str:
        first = _first(self.userId, self.userIds, default="")
        if isinstance(first, (list, tuple)):
            return str(first[0]) if first else ""
        return str(first)


class SysOrgUpdateMemberBody(_LenientRequest):
    """更新组织成员（/system/organization/update-member）。

    兼容字段：organizationId / orgId + userId / id + role。
    """

    organizationId: Any = Field(None, description="组织 ID")
    orgId: Any = Field(None, description="组织 ID（别名）")
    userId: Any = Field(None, description="用户 ID")
    id: Any = Field(None, description="用户 ID（别名）")
    role: Any = Field(None, description="新角色")

    @property
    def effective_org_id(self) -> str:
        return str(_first(self.organizationId, self.orgId, default=""))

    @property
    def effective_user_id(self) -> str:
        return str(_first(self.userId, self.id, default=""))

    @property
    def effective_role(self) -> str:
        return str(_first(self.role, default=""))


class SysProjectIdBody(_LenientRequest):
    """项目 CRUD 通用 body：取 id / projectId 任意一个。"""

    id: Any = Field(None, description="项目 ID")
    projectId: Any = Field(None, description="项目 ID（别名）")
    project_id: Any = Field(None, description="项目 ID（蛇形别名）")

    @property
    def effective_project_id(self) -> str:
        return str(_first(self.id, self.projectId, self.project_id, default=""))


class SysProjectRenameBody(_LenientRequest):
    """重命名项目（/system/project/rename）。"""

    id: Any = Field(None, description="项目 ID")
    projectId: Any = Field(None, description="项目 ID（别名）")
    name: Any = Field(None, description="新名称")

    @property
    def effective_project_id(self) -> str:
        return str(_first(self.id, self.projectId, default=""))

    @property
    def effective_name(self) -> str:
        return str(_first(self.name, default=""))


class SysProjectAddMemberBody(_LenientRequest):
    """系统项目添加成员（/system/project/add-member）。

    兼容字段：projectId / project_id + memberIds / userIds。
    """

    projectId: Any = Field(None, description="项目 ID")
    project_id: Any = Field(None, description="项目 ID（蛇形别名）")
    memberIds: Any = Field(None, description="成员 ID 列表")
    userIds: Any = Field(None, description="用户 ID 列表（别名）")

    @property
    def effective_project_id(self) -> str:
        return str(_first(self.projectId, self.project_id, default=""))

    @property
    def effective_user_ids(self) -> List[str]:
        return [str(x) for x in _to_list(_first(self.memberIds, self.userIds, default=[]))]


class SysViewIdBody(_LenientRequest):
    """用户视图操作：scopeId + id。"""

    id: Any = Field(None, description="视图 ID")
    scopeId: Any = Field(None, description="范围 ID")

    @property
    def effective_id(self) -> str:
        return str(_first(self.id, default=""))

    @property
    def effective_scope_id(self) -> str:
        return str(_first(self.scopeId, default=""))


class SysTemplateIdBody(_LenientRequest):
    """模板操作：取 id。"""

    id: Any = Field(None, description="模板 ID")

    @property
    def effective_id(self) -> str:
        return str(_first(self.id, default=""))


class SysInviteCheckBody(_LenientRequest):
    """邀请检查（/system/user/check-invite & /system/user/invite 共用）。

    兼容字段：inviteId / invite_id / id。
    """

    inviteId: Any = Field(None, description="邀请 ID")
    invite_id: Any = Field(None, description="邀请 ID（蛇形别名）")
    id: Any = Field(None, description="邀请 ID（别名）")

    @property
    def effective_invite_id(self) -> str:
        return str(_first(self.inviteId, self.invite_id, self.id, default=""))


class SysRegisterByInviteBody(_LenientRequest):
    """邀请注册（/system/user/register-by-invite）。

    兼容字段：inviteId / invite_id + name / username + password + phone + email。
    """

    inviteId: Any = Field(None, description="邀请 ID")
    invite_id: Any = Field(None, description="邀请 ID（蛇形别名）")
    name: Any = Field(None, description="用户名")
    username: Any = Field(None, description="用户名（别名）")
    password: Any = Field(None, description="密码（RSA 加密）")
    phone: Any = Field(None, description="手机号")
    email: Any = Field(None, description="邮箱")

    @property
    def effective_invite_id(self) -> str:
        return str(_first(self.inviteId, self.invite_id, default=""))

    @property
    def effective_username(self) -> str:
        return str(_first(self.name, self.username, default="")).strip()

    @property
    def effective_password(self) -> str:
        return str(_first(self.password, default=""))

    @property
    def effective_phone(self) -> str:
        return str(_first(self.phone, default=""))

    @property
    def effective_email(self) -> str:
        return str(_first(self.email, default=""))


class SysOrgLogFilterBody(_LenientRequest):
    """组织操作日志过滤（/organization/log/list）。

    兼容字段：current/pageSize/operUser/startTime/endTime/projectIds/
    organizationIds/type/module/content/keyword/level。
    """

    current: Any = Field(None, description="页码")
    pageSize: Any = Field(None, description="每页条数")
    operUser: Any = Field(None, description="操作人")
    startTime: Any = Field(None, description="开始时间戳")
    endTime: Any = Field(None, description="结束时间戳")
    projectIds: Any = Field(None, description="项目 ID 列表")
    organizationIds: Any = Field(None, description="组织 ID 列表")
    type: Any = Field(None, description="日志类型")
    module: Any = Field(None, description="模块")
    content: Any = Field(None, description="内容关键字")
    keyword: Any = Field(None, description="关键字")
    level: Any = Field(None, description="级别")

    @property
    def effective_current(self) -> int:
        return _int(self.current, 1)

    @property
    def effective_page_size(self) -> int:
        return _int(self.pageSize, 10)

    @property
    def effective_oper_user(self) -> str:
        return str(_first(self.operUser, default="")).strip()

    @property
    def effective_start_time(self) -> Any:
        return self.startTime

    @property
    def effective_end_time(self) -> Any:
        return self.endTime

    @property
    def effective_project_ids(self) -> List[Any]:
        return _to_list(self.projectIds)

    @property
    def effective_organization_ids(self) -> List[Any]:
        return _to_list(self.organizationIds)

    @property
    def effective_type(self) -> str:
        return str(_first(self.type, default="")).strip()

    @property
    def effective_module(self) -> str:
        return str(_first(self.module, default="")).strip()

    @property
    def effective_content(self) -> str:
        return str(_first(self.content, default="")).strip()

    @property
    def effective_keyword(self) -> str:
        return str(_first(self.keyword, default="")).strip()

    @property
    def effective_level(self) -> str:
        return str(_first(self.level, default="")).strip() or "ORGANIZATION"


__all__ = [
    "SysOrgPageBody",
    "OrgProjectUserListPageBody",
    "SystemProjectPageBody",
    "SysOrgIdBody",
    "SysOrgRenameBody",
    "SysOrgAddMemberBody",
    "SysOrgRemoveMemberBody",
    "SysOrgUpdateMemberBody",
    "SysProjectIdBody",
    "SysProjectRenameBody",
    "SysProjectAddMemberBody",
    "SysViewIdBody",
    "SysTemplateIdBody",
    "SysInviteCheckBody",
    "SysRegisterByInviteBody",
    "SysOrgLogFilterBody",
]
