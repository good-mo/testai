"""环境聚合根 Environment（测试环境资源管理）。

聚合边界：
  - Environment（聚合根）：环境配置与状态
  - 标签（tags）为聚合内值对象
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.environment.domain.events import (
    EnvironmentCreated,
    EnvironmentStatusChanged,
    EnvironmentUpdated,
)
from app.domain.environment.domain.services.env_policy import EnvLifecyclePolicy
from app.domain.environment.domain.value_objects.env_status import EnvStatus


class Environment(AggregateRoot):
    """环境聚合根。"""

    def __init__(
        self,
        *,
        env_id: str,
        name: str = "",
        description: str = "",
        env_type: str = "docker",
        status: str = "offline",
        endpoint: str = "",
        docker_compose_path: str = "",
        container_name: str = "",
        image: str = "",
        health_check_url: str = "",
        owner: str = "",
        tags: Optional[list] = None,
        error_message: str = "",
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        _created: bool = False,
    ):
        if not env_id:
            raise DomainValidationError("环境 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("环境名称不能为空")
        self.id = Identifier.of(env_id)
        self._name = (name or "").strip()
        self._description = description or ""
        self._env_type = env_type or "docker"
        self._status = EnvStatus(status)
        self._endpoint = endpoint or ""
        self._docker_compose_path = docker_compose_path or ""
        self._container_name = container_name or ""
        self._image = image or ""
        self._health_check_url = health_check_url or ""
        self._owner = owner or ""
        self._tags = list(tags or [])
        self._error_message = error_message or ""
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(EnvironmentCreated(self.id.value, self._name, self._env_type))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def env_type(self) -> str:
        return self._env_type

    @property
    def status(self) -> EnvStatus:
        return self._status

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def docker_compose_path(self) -> str:
        return self._docker_compose_path

    @property
    def container_name(self) -> str:
        return self._container_name

    @property
    def image(self) -> str:
        return self._image

    @property
    def health_check_url(self) -> str:
        return self._health_check_url

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def is_deleted(self) -> bool:
        return False  # 软删除状态在仓储层管理

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    # ── 业务命令 ─────────────────────────────────────
    def rename(self, name: str) -> None:
        if not (name or "").strip():
            raise DomainValidationError("环境名称不能为空")
        self._name = name.strip()
        self._touch()
        self.record_event(EnvironmentUpdated(self.id.value, "rename"))

    def update_meta(self, data: dict) -> None:
        """更新环境元数据。"""
        allowed = ("name", "description", "env_type", "endpoint",
                   "docker_compose_path", "container_name", "image",
                   "health_check_url", "owner", "tags", "error_message")
        for k, v in data.items():
            if k in allowed:
                if k == "name":
                    if not (v or "").strip():
                        raise DomainValidationError("环境名称不能为空")
                    self._name = v.strip()
                elif k == "tags":
                    self._tags = list(v or [])
                elif k == "env_type":
                    self._env_type = v
                elif k == "error_message":
                    self._error_message = v or ""
                else:
                    setattr(self, f"_{k}", v or "")
        self._touch()
        self.record_event(EnvironmentUpdated(self.id.value, "meta"))

    def change_status(self, new_status: str, error_message: str = "") -> None:
        """状态迁移（经策略校验）。"""
        policy = EnvLifecyclePolicy()
        old = self._status.value
        policy.ensure_transition_allowed(self._status, EnvStatus(new_status))
        self._status = EnvStatus(new_status)
        if error_message:
            self._error_message = error_message
        self._touch()
        self.record_event(EnvironmentStatusChanged(
            self.id.value, old, self._status.value, error_message))

    def set_endpoint(self, endpoint: str) -> None:
        self._endpoint = endpoint or ""
        self._touch()

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 序列化 ─────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "env_type": self._env_type,
            "status": self._status.value,
            "endpoint": self._endpoint,
            "docker_compose_path": self._docker_compose_path,
            "container_name": self._container_name,
            "image": self._image,
            "health_check_url": self._health_check_url,
            "owner": self._owner,
            "tags": list(self._tags),
            "error_message": self._error_message,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Environment":
        return Environment(
            env_id=str(data.get("id") or data.get("env_id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            env_type=data.get("env_type", "docker"),
            status=data.get("status", "offline"),
            endpoint=data.get("endpoint", ""),
            docker_compose_path=data.get("docker_compose_path", ""),
            container_name=data.get("container_name", ""),
            image=data.get("image", ""),
            health_check_url=data.get("health_check_url", ""),
            owner=data.get("owner", ""),
            tags=data.get("tags"),
            error_message=data.get("error_message", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


__all__ = ["Environment"]
