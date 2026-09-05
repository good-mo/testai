# app/models/auth.py
"""认证 / 用户 / 会话 Pydantic 请求体模型（在用的模型）。

覆盖：登录登出、个人信息、本地执行配置、API Key、系统用户分页/添加、
用户导入、项目成员/组织成员，以及用户组/角色/组织成员管理。

规范约束 #5：请求体一律 Pydantic，禁止手写 request.json()/body:dict。
所有字段提供默认值以兼容前端省略可选字段，保持与旧手写解析语义一致。

（原属此文件的旧 *Request 死模型 —— LogoutRequest/TokenRefreshRequest/
UserCreateRequest/UserPageQuery/APIKeyRequest/ChangePasswordRequest 等
已随 #608 逐域清理移除，统一由在用的 Body/Request 模型承担。）
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── 登录 / 登出 ─────────────────────────────────────────
class LoginRequest(BaseModel):
    """用户登录请求体。"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码（RSA 加密后传输）")
    authenticate: str = Field("LOCAL", description="认证方式")
    # TestPilot 前端兼容：无痕 / 记住我
    rememberMe: Optional[bool] = False
    noClear: Optional[bool] = False

    model_config = {"extra": "allow"}


# ── 个人信息 ────────────────────────────────────────────
class PersonalUpdateBody(BaseModel):
    """更新个人信息。"""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    language: Optional[str] = None

    model_config = {"extra": "allow"}


class PasswordUpdateBody(BaseModel):
    """修改密码。"""
    oldPassword: str = Field("", description="旧密码(需 RSA 解密)")
    newPassword: str = Field("", description="新密码(需 RSA 解密)")


class LocaleUpdateBody(BaseModel):
    language: str = Field("zh-CN", description="语言偏好")


# ── 本地执行配置 ────────────────────────────────────────
class LocalConfigAddBody(BaseModel):
    user_url: str = Field("", description="本地执行地址")
    type: str = Field("API", description="配置类型")


class LocalConfigUpdateBody(BaseModel):
    id: str = Field("", description="配置 ID")
    user_url: str = Field("", description="本地执行地址")


# ── API Key ─────────────────────────────────────────────
class ApiKeyAddBody(BaseModel):
    description: str = Field("", description="描述")
    forever: bool = Field(False, description="是否永久有效")
    expire_time: int = Field(0, description="过期时间戳")


class ApiKeyIdBody(BaseModel):
    """按 id 操作 API Key（启用/禁用/删除）。"""
    id: str = Field("", description="API Key ID")


# ── 系统用户（分页/添加/单用户操作） ─────────────────────
class SystemUserPageBody(BaseModel):
    """系统用户分页（POST）。"""
    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")
    keyword: str = Field("", description="搜索关键字")


class UserAddBody(BaseModel):
    username: str = Field("", description="用户名")
    password: str = Field("", description="密码(需 RSA 解密)")
    name: str = Field("", description="姓名")
    email: str = Field("", description="邮箱")
    phone: str = Field("", description="手机号")
    role: str = Field("user", description="角色")


class UserIdBody(BaseModel):
    """按 id 操作单个用户（删除/启停/重置密码）。"""
    id: str = Field("", description="用户 ID")
    enable: Optional[Any] = None
    status: Optional[str] = Field(None, description="启停状态（enable/disable）")
    password: str = Field("", description="新密码(需 RSA 解密)")


class UserUpdateBody(BaseModel):
    id: str = Field("", description="用户 ID")
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None


# ── 用户导入 ────────────────────────────────────────────
class ImportUserItem(BaseModel):
    username: str = Field("", description="用户名")
    password: str = Field("", description="密码")
    name: str = Field("", description="姓名")
    email: str = Field("", description="邮箱")
    phone: str = Field("", description="手机号")
    role: str = Field("user", description="角色")


class UserImportBody(BaseModel):
    """批量导入用户。"""
    users: List[ImportUserItem] = Field([], description="用户列表")
    userList: List[ImportUserItem] = Field([], description="用户列表(别名)")

    def effective_users(self) -> List[ImportUserItem]:
        return self.users or self.userList

    model_config = {"extra": "allow"}


# ── 项目成员 / 组织成员 ─────────────────────────────────
class ProjectMemberBody(BaseModel):
    """项目成员通用体（添加/移除）。字段兼容前端 camelCase 与后端 snake_case。"""
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID(别名)")
    userId: str = Field("", description="用户 ID")
    user_id: str = Field("", description="用户 ID(别名)")
    id: str = Field("", description="成员 ID(主键,通用)")
    memberIds: Any = Field([], description="成员 ID 列表")
    userIds: Any = Field([], description="成员 ID 列表(别名)")
    selectIds: Any = Field([], description="勾选成员 ID")
    username: str = Field("", description="用户名")
    name: str = Field("", description="姓名")
    email: str = Field("", description="邮箱")
    role: str = Field("member", description="角色")
    roleIds: Any = Field([], description="角色 ID 列表")
    userRoleId: str = Field("", description="用户组 ID")
    user_group: str = Field("", description="用户组")
    memberId: str = Field("", description="成员 ID(别名)")
    selectAll: bool = Field(False, description="是否全选")
    excludeIds: Any = Field([], description="排除成员 ID")

    model_config = {"extra": "allow"}

    def resolve_project_id(self) -> str:
        return self.projectId or self.project_id

    def resolve_user_id(self) -> str:
        return self.userId or self.user_id

    def resolve_role_ids(self) -> List[Any]:
        ids = self.roleIds or self.userRoleId or []
        if isinstance(ids, str):
            return [ids]
        return list(ids)


class ProjectMemberListBody(BaseModel):
    """项目成员分页查询（POST）。"""
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID(别名)")
    keyword: str = Field("", description="搜索关键字")
    filter: Dict[str, Any] = Field({}, description="过滤条件")


# ── 用户组 / 角色 / 组织成员管理（missing_admin）────────────
class UserGroupAddBody(BaseModel):
    """创建用户组（全局/组织）。"""
    name: str = Field("未命名用户组", description="用户组名称")
    description: str = Field("", description="描述")
    createUser: str = Field("admin", description="创建人")
    updateUser: str = Field("admin", description="更新人")
    pos: Any = Field(99, description="排序")
    type: str = Field("SYSTEM", description="组类型")
    scopeId: str = Field("", description="作用域 ID")
    organizationId: str = Field("", description="组织 ID")


class UserGroupUpdateBody(BaseModel):
    """更新用户组。"""
    id: str = Field("", description="用户组 ID")
    name: Optional[str] = None
    description: Optional[str] = None
    pos: Any = None
    updateUser: str = Field("admin", description="更新人")


class GroupPermissionBody(BaseModel):
    """更新用户组权限。"""
    id: str = Field("", description="用户组 ID")
    groupId: str = Field("", description="用户组 ID(别名)")
    permissions: Any = Field([], description="权限集合")
    permissionIds: Any = Field([], description="权限集合(别名)")


class GroupMemberListBody(BaseModel):
    """用户组成员查询。"""
    groupId: str = Field("", description="用户组 ID")
    roleId: str = Field("", description="角色 ID")
    id: str = Field("", description="用户组 ID(别名)")
    keyword: str = Field("", description="搜索关键字")


class GroupMemberBody(BaseModel):
    """用户组成员变更（添加/移除）。"""
    groupId: str = Field("", description="用户组 ID")
    roleId: str = Field("", description="角色 ID")
    id: str = Field("", description="用户组 ID(别名)")
    type: str = Field("ORGANIZATION", description="组类型")
    scopeId: str = Field("", description="作用域 ID")
    organizationId: str = Field("", description="组织 ID")
    userIds: Any = Field([], description="用户 ID 列表")
    memberIds: Any = Field([], description="成员 ID 列表")
    userId: str = Field("", description="用户 ID")
    user_id: str = Field("", description="用户 ID(别名)")
    username: str = Field("", description="用户名")
    name: str = Field("", description="姓名")
    email: str = Field("", description="邮箱")

    def resolve_group_id(self) -> str:
        return self.groupId or self.roleId or self.id

    def resolve_user_ids(self) -> list:
        uids = self.userIds or self.memberIds or []
        if isinstance(uids, str):
            uids = [uids]
        if not uids:
            uids = [self.userId or self.user_id]
        return [str(u) for u in uids if u]
