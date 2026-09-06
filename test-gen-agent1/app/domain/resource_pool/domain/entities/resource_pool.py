"""资源池聚合根 ResourcePool。"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import time_from_row
from app.domain.resource_pool.domain.events import (
    ResourcePoolCreated,
    ResourcePoolUpdated,
)


class ResourcePool(AggregateRoot):
    """资源池聚合根。"""

    def __init__(
        self,
        *,
        pool_id: str,
        name: str = "未命名资源池",
        description: str = "",
        enable: bool = True,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        _created: bool = False,
    ):
        if not pool_id:
            raise DomainValidationError("资源池 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("资源池名称不能为空")
        self.id = Identifier.of(pool_id)
        self._name = (name or "").strip()
        self._description = description or ""
        self._enable = bool(enable)
        now = time.time()
        self._created_at = created_at if created_at is not None else now
        self._updated_at = updated_at if updated_at is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(ResourcePoolCreated(self.id.value, self._name))

    @property
    def name(self) -> str:
        return self._name
    @property
    def description(self) -> str:
        return self._description
    @property
    def enable(self) -> bool:
        return self._enable

    def rename(self, name: str) -> None:
        if not (name or "").strip():
            raise DomainValidationError("资源池名称不能为空")
        self._name = (name or "").strip()
        self._touch()

    def update(self, *, name: Optional[str] = None,
               description: Optional[str] = None) -> None:
        if name is not None:
            self.rename(name)
        if description is not None:
            self._description = description
        self.record_event(ResourcePoolUpdated(self.id.value))
        self._touch()

    def enable_pool(self) -> None:
        self._enable = True
        self._touch()

    def disable_pool(self) -> None:
        self._enable = False
        self._touch()

    def _touch(self) -> None:
        self._updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "enable": self._enable,
            "createdAt": int(self._created_at * 1000) if self._created_at else 0,
            "updatedAt": int(self._updated_at * 1000) if self._updated_at else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "ResourcePool":
        return ResourcePool(
            pool_id=str(data.get("id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            enable=bool(data.get("enable", True)),
            created_at=time_from_row(data, "created_at", "createdAt"),
            updated_at=time_from_row(data, "updated_at", "updatedAt"),
        )
