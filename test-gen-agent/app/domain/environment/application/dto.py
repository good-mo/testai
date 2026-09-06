"""环境应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CreateCommand:
    """创建环境。"""
    name: str
    description: str = ""
    env_type: str = "docker"
    endpoint: str = ""
    docker_compose_path: str = ""
    container_name: str = ""
    image: str = ""
    health_check_url: str = ""
    owner: str = ""
    tags: list = field(default_factory=list)


@dataclass
class EnvQuery:
    """环境列表查询。"""
    search: str = ""
    status: str = ""
    env_type: str = ""


@dataclass
class GetCommand:
    """获取环境。"""
    env_id: str


@dataclass
class UpdateCommand:
    """更新环境。"""
    env_id: str
    data: dict = field(default_factory=dict)


@dataclass
class DeleteCommand:
    """删除环境。"""
    env_id: str
    permanent: bool = False


@dataclass
class StatusChangeCommand:
    """状态变更。"""
    env_id: str
    new_status: str
    error_message: str = ""


@dataclass
class LaunchCommand:
    """拉起环境。"""
    env_id: str


@dataclass
class StopCommand:
    """停止环境。"""
    env_id: str


@dataclass
class HealthCheckCommand:
    """健康检查。"""
    env_id: str


@dataclass
class CreateAlertCommand:
    """创建告警。"""
    env_id: str
    env_name: str
    level: str = "warning"
    message: str = ""
    detail: str = ""


@dataclass
class ListAlertsQuery:
    """告警列表。"""
    limit: int = 50
    level: str = ""


@dataclass
class ResolveAlertCommand:
    """解决告警。"""
    alert_id: str


__all__ = [
    "CreateCommand", "EnvQuery", "GetCommand", "UpdateCommand", "DeleteCommand",
    "StatusChangeCommand", "LaunchCommand", "StopCommand", "HealthCheckCommand",
    "CreateAlertCommand", "ListAlertsQuery", "ResolveAlertCommand",
]


# ==============================================================================
# 从 models/environment.py 迁移
# ==============================================================================

# app/models/environment.py
"""环境管理 Pydantic 模型。"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EnvironmentCreate(BaseModel):
    # name 允许缺省，默认由业务层设置"未命名环境"
    name: str = Field("", max_length=100)
    description: str = Field("")
    env_type: str = Field("docker")
    endpoint: str = Field("")
    docker_compose_path: str = Field("")
    container_name: str = Field("")
    image: str = Field("")
    health_check_url: str = Field("")
    owner: str = Field("")
    tags: List[str] = Field([])
    # 前端兼容 base_url 字段
    base_url: Optional[str] = None


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    env_type: Optional[str] = None
    endpoint: Optional[str] = None
    docker_compose_path: Optional[str] = None
    container_name: Optional[str] = None
    image: Optional[str] = None
    health_check_url: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────
# MeterSphere 项目环境兼容路由请求体（app/routers/project_compat_environment.py）
#
# 字段自 `/project/environment/*` 兼容路由中 `read_body()` 实际使用的请求体归纳。
# 前端为 TestPilot 驼峰风格；统一默认 `extra: allow` 避免遗漏新增字段判 400，
# 默认值语义与旧 `.get(key, default)` 一致（空体/缺字段不抛错、返回 200）。
# ─────────────────────────────────────────────────────────────────────────

class ProjEnvIdBody(BaseModel):
    """按 id 获取 / 删除项目环境、环境组（POST 分支）。"""

    id: str = Field("", description="环境 / 环境组 ID")

    model_config = {"extra": "allow"}


class ProjEnvQueryBody(BaseModel):
    """环境 / 环境组 / 脚本列表查询体（projectId + keyword）。"""

    projectId: str = Field("", description="所属项目（驼峰别名）")
    project_id: str = Field("", description="所属项目（snake 别名）")
    keyword: str = Field("", description="搜索关键字")

    @property
    def effective_project_id(self) -> str:
        return self.projectId or self.project_id

    model_config = {"extra": "allow"}


class ProjEnvGroupBody(BaseModel):
    """环境组新增 / 更新体。id 为空视为新增。"""

    id: str = Field("", description="环境组 ID（为空视为新增）")
    name: str = Field("未命名环境组", description="环境组名称")
    description: str = Field("", description="描述")
    projectId: str = Field("", description="所属项目（驼峰别名）")
    project_id: str = Field("", description="所属项目（snake 别名）")
    envGroupProject: Optional[List[Any]] = Field(None, description="环境组内环境列表")
    environmentGroupInfo: Optional[List[Any]] = Field(None, description="环境组内环境列表（别名）")

    @property
    def effective_project_id(self) -> str:
        return self.projectId or self.project_id

    @property
    def effective_env_group_project(self) -> List[Any]:
        """按优先级取 envGroupProject / environmentGroupInfo（对齐旧兼容逻辑）。"""
        if self.envGroupProject:
            return self.envGroupProject
        return self.environmentGroupInfo or []

    model_config = {"extra": "allow"}


class ProjEnvMoveBody(BaseModel):
    """项目环境 / 环境组拖拽排序体。"""

    moveId: str = Field("", description="被拖拽节点 ID")

    model_config = {"extra": "allow"}


class ProjEnvExportBody(BaseModel):
    """导出项目环境 ID 集合体。"""

    selectIds: List[str] = Field([], description="勾选待导出的环境 ID")

    model_config = {"extra": "allow"}


class ProjDbValidateBody(BaseModel):
    """数据库连接校验体。"""

    dbUrl: str = Field("", description="数据库连接 URL")
    username: str = Field("", description="数据库用户名")

    model_config = {"extra": "allow"}


class ProjEnvUpsertBody(BaseModel):
    """新增 / 更新项目环境体（multipart 的 request 字段解析后使用）。

    update 分支按 `model_dump(exclude_unset=True)` 仅取客户端实发字段，
    等价旧逻辑 `for k in (...): if k in body` 的字段透传语义。
    """

    id: str = Field("", description="环境 ID（新增可缺省）")
    name: str = Field("未命名环境", description="环境名称")
    description: str = Field("", description="描述")
    projectId: str = Field("", description="所属项目（驼峰别名）")
    project_id: str = Field("", description="所属项目（snake 别名）")
    config: Dict[str, Any] = Field(default_factory=dict, description="前端 config 扩展结构")

    @property
    def effective_project_id(self) -> str:
        return self.projectId or self.project_id

    model_config = {"extra": "allow"}
