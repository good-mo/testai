"""消息领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class RobotCreated(DomainEvent):
    """消息机器人已创建。"""

    def __init__(self, robot_id: str, name: str, platform: str = "CUSTOM"):
        super().__init__(aggregate_id=robot_id)
        self.name = name
        self.platform = platform


class RobotUpdated(DomainEvent):
    """消息机器人已更新。"""

    def __init__(self, robot_id: str, action: str = "meta"):
        super().__init__(aggregate_id=robot_id)
        self.action = action


class RobotDeleted(DomainEvent):
    """消息机器人已删除。"""

    def __init__(self, robot_id: str):
        super().__init__(aggregate_id=robot_id)


class RobotEnabledChanged(DomainEvent):
    """机器人启停变更。"""

    def __init__(self, robot_id: str, enable: bool):
        super().__init__(aggregate_id=robot_id)
        self.enable = enable


class MessageTaskUpserted(DomainEvent):
    """消息设置已保存。"""

    def __init__(self, task_id: str, project_id: str = "",
                 task_type: str = "", event: str = ""):
        super().__init__(aggregate_id=task_id)
        self.project_id = project_id
        self.task_type = task_type
        self.event = event


class NotificationCreated(DomainEvent):
    """站内通知已创建。"""

    def __init__(self, notification_id: str, receiver: str = "",
                 title: str = "", resource_type: str = ""):
        super().__init__(aggregate_id=notification_id)
        self.receiver = receiver
        self.title = title
        self.resource_type = resource_type


class NotificationRead(DomainEvent):
    """站内通知已读。"""

    def __init__(self, notification_id: str):
        super().__init__(aggregate_id=notification_id)


__all__ = [
    "RobotCreated", "RobotUpdated", "RobotDeleted", "RobotEnabledChanged",
    "MessageTaskUpserted", "NotificationCreated", "NotificationRead",
]
