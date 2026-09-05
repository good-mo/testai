"""消息机器人聚合根 Robot。

项目消息机器人：配置平台 webhook/app_key 等参数，启停状态。
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.message.domain.events import (
    RobotCreated,
    RobotDeleted,
    RobotEnabledChanged,
    RobotUpdated,
)
from app.domain.message.domain.value_objects.notification_status import RobotPlatform


class Robot(AggregateRoot):
    """消息机器人聚合根。"""

    BUILTIN_PLATFORMS = ("IN_SITE", "MAIL")

    def __init__(
        self,
        *,
        robot_id: str,
        project_id: str = "",
        name: str = "未命名机器人",
        platform: str = "CUSTOM",
        type: str = "CUSTOM",
        webhook: str = "",
        app_key: str = "",
        app_secret: str = "",
        enable: bool = True,
        description: str = "",
        create_user: str = "admin",
        update_user: str = "admin",
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not robot_id:
            raise DomainValidationError("机器人 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("机器人名称不能为空")
        self.id = Identifier.of(robot_id)
        self._project_id = project_id or ""
        self._name = (name or "").strip()
        self._platform = RobotPlatform(platform)
        self._type = type or "CUSTOM"
        self._webhook = webhook or ""
        self._app_key = app_key or ""
        self._app_secret = app_secret or ""
        self._enable = bool(enable)
        self._description = description or ""
        self._create_user = create_user or "admin"
        self._update_user = update_user or "admin"
        self._create_time = create_time if create_time is not None else time.time()
        self._update_time = update_time if update_time is not None else self._create_time
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(RobotCreated(
                self.id.value, self._name, self._platform.value))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def platform(self) -> RobotPlatform:
        return self._platform

    @property
    def type(self) -> str:
        return self._type

    @property
    def webhook(self) -> str:
        return self._webhook

    @property
    def app_key(self) -> str:
        return self._app_key

    @property
    def app_secret(self) -> str:
        return self._app_secret

    @property
    def enable(self) -> bool:
        return self._enable

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_builtin(self) -> bool:
        return self._platform.value in self.BUILTIN_PLATFORMS

    @property
    def create_time(self) -> float:
        return self._create_time

    @property
    def update_time(self) -> float:
        return self._update_time

    @property
    def create_user(self) -> str:
        return self._create_user

    @property
    def update_user(self) -> str:
        return self._update_user

    # ── 业务命令 ─────────────────────────────────────
    def update_meta(self, data: dict) -> None:
        """更新机器人元数据。"""
        allowed = ("name", "platform", "type", "webhook",
                   "app_key", "app_secret", "enable", "description")
        for k, v in data.items():
            if k == "name":
                if not (v or "").strip():
                    raise DomainValidationError("机器人名称不能为空")
                self._name = v.strip()
            elif k == "platform":
                self._platform = RobotPlatform(v)
            elif k == "enable":
                old = self._enable
                self._enable = bool(v)
                if old != self._enable:
                    self.record_event(RobotEnabledChanged(self.id.value, self._enable))
            elif k in allowed:
                setattr(self, f"_{k}", v if v is not None else "")
        self._update_time = time.time()
        self.record_event(RobotUpdated(self.id.value, "meta"))

    def set_enable(self, enable: bool) -> None:
        old = self._enable
        self._enable = bool(enable)
        self._update_time = time.time()
        if old != self._enable:
            self.record_event(RobotEnabledChanged(self.id.value, self._enable))

    def mark_deleted(self) -> None:
        self.record_event(RobotDeleted(self.id.value))

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "project_id": self._project_id,
            "name": self._name,
            "platform": self._platform.value,
            "type": self._type,
            "webhook": self._webhook,
            "app_key": self._app_key,
            "app_secret": self._app_secret,
            "enable": self._enable,
            "description": self._description,
            "create_user": self._create_user,
            "update_user": self._update_user,
            "create_time": self._create_time,
            "update_time": self._update_time,
        }

    @staticmethod
    def from_dict(data: dict) -> "Robot":
        return Robot(
            robot_id=str(data.get("id") or ""),
            project_id=data.get("project_id", ""),
            name=data.get("name", "未命名机器人"),
            platform=data.get("platform", "CUSTOM"),
            type=data.get("type", "CUSTOM"),
            webhook=data.get("webhook", ""),
            app_key=data.get("app_key", ""),
            app_secret=data.get("app_secret", ""),
            enable=bool(data.get("enable", True)),
            description=data.get("description", ""),
            create_user=data.get("create_user", "admin"),
            update_user=data.get("update_user", "admin"),
            create_time=data.get("create_time"),
            update_time=data.get("update_time"),
        )


__all__ = ["Robot"]
