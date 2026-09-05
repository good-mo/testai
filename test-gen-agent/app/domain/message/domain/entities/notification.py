"""站内通知聚合根 Notification。

站内消息中心的通知记录：接收人、标题、内容、资源关联、已读状态。
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.message.domain.events import NotificationCreated, NotificationRead
from app.domain.message.domain.value_objects.notification_status import (
    NotificationStatus,
    NotificationStatusEnum,
)


class Notification(AggregateRoot):
    """站内通知聚合根。"""

    def __init__(
        self,
        *,
        notification_id: str,
        type: str = "message",
        title: str = "",
        sub_title: str = "",
        content: str = "",
        avatar: str = "",
        resource_type: str = "",
        resource_id: str = "",
        resource_name: str = "",
        operation: str = "",
        receiver: str = "",
        operator: str = "",
        project_id: str = "",
        organization_id: str = "",
        status: str = "UNREAD",
        create_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not notification_id:
            raise DomainValidationError("通知 ID 不能为空")
        self.id = Identifier.of(notification_id)
        self._type = type or "message"
        self._title = title or ""
        self._sub_title = sub_title or ""
        self._content = content or ""
        self._avatar = avatar or ""
        self._resource_type = resource_type or ""
        self._resource_id = resource_id or ""
        self._resource_name = resource_name or ""
        self._operation = operation or ""
        self._receiver = receiver or ""
        self._operator = operator or ""
        self._project_id = project_id or ""
        self._organization_id = organization_id or ""
        self._status = NotificationStatus(status)
        self._create_time = create_time if create_time is not None else time.time()
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(NotificationCreated(
                self.id.value, self._receiver, self._title, self._resource_type))

    @property
    def title(self) -> str:
        return self._title

    @property
    def content(self) -> str:
        return self._content

    @property
    def resource_type(self) -> str:
        return self._resource_type

    @property
    def resource_id(self) -> str:
        return self._resource_id

    @property
    def resource_name(self) -> str:
        return self._resource_name

    @property
    def receiver(self) -> str:
        return self._receiver

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def status(self) -> NotificationStatus:
        return self._status

    @property
    def create_time(self) -> float:
        return self._create_time

    @property
    def is_read(self) -> bool:
        return self._status.value == NotificationStatusEnum.READ.value

    # ── 业务命令 ─────────────────────────────────────
    def mark_read(self) -> None:
        """标记为已读（幂等）。"""
        if self.is_read:
            return
        self._status = NotificationStatus(NotificationStatusEnum.READ.value)
        self.record_event(NotificationRead(self.id.value))

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "type": self._type,
            "title": self._title,
            "sub_title": self._sub_title,
            "content": self._content,
            "avatar": self._avatar,
            "resource_type": self._resource_type,
            "resource_id": self._resource_id,
            "resource_name": self._resource_name,
            "operation": self._operation,
            "receiver": self._receiver,
            "operator": self._operator,
            "project_id": self._project_id,
            "organization_id": self._organization_id,
            "status": self._status.value,
            "create_time": self._create_time,
        }

    @staticmethod
    def from_dict(data: dict) -> "Notification":
        return Notification(
            notification_id=str(data.get("id") or ""),
            type=data.get("type", "message"),
            title=data.get("title", ""),
            sub_title=data.get("sub_title", ""),
            content=data.get("content", ""),
            avatar=data.get("avatar", ""),
            resource_type=data.get("resource_type", ""),
            resource_id=data.get("resource_id", ""),
            resource_name=data.get("resource_name", ""),
            operation=data.get("operation", ""),
            receiver=data.get("receiver", ""),
            operator=data.get("operator", ""),
            project_id=data.get("project_id", ""),
            organization_id=data.get("organization_id", ""),
            status=data.get("status", "UNREAD"),
            create_time=data.get("create_time"),
        )


__all__ = ["Notification"]
