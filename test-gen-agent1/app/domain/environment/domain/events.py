"""环境领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class EnvironmentCreated(DomainEvent):
    """环境已创建。"""

    def __init__(self, env_id: str, name: str, env_type: str = "docker"):
        super().__init__(aggregate_id=env_id)
        self.name = name
        self.env_type = env_type


class EnvironmentUpdated(DomainEvent):
    """环境已更新。"""

    def __init__(self, env_id: str, action: str = "meta"):
        super().__init__(aggregate_id=env_id)
        self.action = action


class EnvironmentStatusChanged(DomainEvent):
    """环境状态已变更。"""

    def __init__(self, env_id: str, old_status: str, new_status: str,
                 error_message: str = ""):
        super().__init__(aggregate_id=env_id)
        self.old_status = old_status
        self.new_status = new_status
        self.error_message = error_message


class EnvironmentDeleted(DomainEvent):
    """环境已删除。"""

    def __init__(self, env_id: str, permanent: bool = False):
        super().__init__(aggregate_id=env_id)
        self.permanent = permanent


class EnvironmentRestored(DomainEvent):
    """环境已从回收站恢复。"""

    def __init__(self, env_id: str):
        super().__init__(aggregate_id=env_id)


class EnvironmentTrashed(DomainEvent):
    """环境已移入回收站。"""

    def __init__(self, env_id: str):
        super().__init__(aggregate_id=env_id)


class EnvironmentAlertCreated(DomainEvent):
    """环境告警已创建。"""

    def __init__(self, env_id: str, alert_id: str, level: str = "warning",
                 message: str = ""):
        super().__init__(aggregate_id=env_id)
        self.alert_id = alert_id
        self.level = level
        self.message = message


__all__ = [
    "EnvironmentCreated", "EnvironmentUpdated", "EnvironmentStatusChanged",
    "EnvironmentDeleted", "EnvironmentRestored", "EnvironmentTrashed",
    "EnvironmentAlertCreated",
]
