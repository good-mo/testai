"""消息应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RobotListQuery:
    """机器人列表查询。"""
    project_id: str = ""


@dataclass
class RobotCreateCommand:
    """创建机器人。"""
    project_id: str = ""
    name: str = ""
    platform: str = "CUSTOM"
    type: str = "CUSTOM"
    webhook: str = ""
    app_key: str = ""
    app_secret: str = ""
    enable: bool = True
    description: str = ""
    create_user: str = "admin"


@dataclass
class RobotUpdateCommand:
    """更新机器人。"""
    robot_id: str
    data: dict = field(default_factory=dict)


@dataclass
class RobotGetCommand:
    """获取机器人。"""
    robot_id: str


@dataclass
class RobotDeleteCommand:
    """删除机器人。"""
    robot_id: str


@dataclass
class RobotEnableCommand:
    """启用/停用机器人。"""
    robot_id: str
    enable: bool


@dataclass
class NotificationCreateCommand:
    """创建通知。"""
    type: str = "message"
    title: str = ""
    sub_title: str = ""
    content: str = ""
    avatar: str = ""
    resource_type: str = ""
    resource_id: str = ""
    resource_name: str = ""
    operation: str = ""
    receiver: str = ""
    operator: str = ""
    project_id: str = ""
    organization_id: str = ""


@dataclass
class NotificationQuery:
    """通知列表查询。"""
    receiver: str = ""
    status: str = ""
    type_: str = ""
    resource_type: str = ""
    keyword: str = ""
    project_id: str = ""
    current: int = 1
    page_size: int = 10


@dataclass
class NotificationReadCommand:
    """标记通知已读。"""
    notification_id: str


@dataclass
class NotificationReadAllCommand:
    """标记全部已读。"""
    receiver: str = ""
    resource_type: str = ""


__all__ = [
    "RobotListQuery", "RobotCreateCommand", "RobotUpdateCommand",
    "RobotGetCommand", "RobotDeleteCommand", "RobotEnableCommand",
    "NotificationCreateCommand", "NotificationQuery",
    "NotificationReadCommand", "NotificationReadAllCommand",
]
