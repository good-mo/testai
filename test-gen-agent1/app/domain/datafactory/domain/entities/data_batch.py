"""数据批次实体 DataBatch。

批次是一键造数的产物：由某数据模板按 batch_size 在指定环境生成的一批
记录。批次拥有独立标识与生命周期（active→cleaned），作为模板聚合之外
的关联实体被仓储读写与清理。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import Entity, Identifier
from app.domain.datafactory.domain.events import DataBatchCleaned, DataBatchGenerated


class DataBatch(Entity):
    """数据生成批次实体。"""

    STATUS_ACTIVE = "active"
    STATUS_CLEANED = "cleaned"

    def __init__(
        self,
        *,
        batch_id: str,
        template_id: str = "",
        template_name: str = "",
        batch_size: int = 1,
        env_key: str = "",
        data: Optional[List[dict]] = None,
        status: str = STATUS_ACTIVE,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        _generated: bool = False,
    ):
        self.id = Identifier.of(batch_id)
        self._template_id = template_id or ""
        self._template_name = template_name or ""
        self._batch_size = max(1, int(batch_size or 1))
        self._env_key = env_key or ""
        self._data: List[dict] = [dict(d) for d in (data or [])]
        self._status = status or self.STATUS_ACTIVE
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0
        if _generated:
            self.record_event(DataBatchGenerated(
                self.id.value, self._template_id, self._batch_size, self._env_key))

    @property
    def template_id(self) -> str:
        return self._template_id

    @property
    def template_name(self) -> str:
        return self._template_name

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @property
    def env_key(self) -> str:
        return self._env_key

    @property
    def data(self) -> List[dict]:
        return [dict(d) for d in self._data]

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status == self.STATUS_ACTIVE

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    def clean(self, operator: str = "system") -> None:
        """清理本批次数据：仅 active 可清理。"""
        if self._status != self.STATUS_ACTIVE:
            return
        self._status = self.STATUS_CLEANED
        self._updated_at = time.time()
        self.record_event(DataBatchCleaned(self.id.value, self._env_key, operator))

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "template_id": self._template_id,
            "template_name": self._template_name,
            "batch_size": self._batch_size,
            "env_key": self._env_key,
            "data": [dict(d) for d in self._data],
            "status": self._status,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "DataBatch":
        return DataBatch(
            batch_id=str(data.get("id") or data.get("batch_id") or ""),
            template_id=data.get("template_id", ""),
            template_name=data.get("template_name", ""),
            batch_size=data.get("batch_size", 1),
            env_key=data.get("env_key", ""),
            data=data.get("data") or [],
            status=data.get("status", "active"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


__all__ = ["DataBatch"]
