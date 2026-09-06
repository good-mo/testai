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
