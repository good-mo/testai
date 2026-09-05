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
