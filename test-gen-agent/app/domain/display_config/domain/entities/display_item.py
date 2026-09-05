"""展示配置值对象/实体 DisplayConfigItem。"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.display_config.domain.events import DisplayConfigUpdated


class DisplayConfigItem(AggregateRoot):
    """展示配置项（param_key → param_value）聚合根。"""

    def __init__(
        self,
        *,
        param_key: str,
        param_value: str = "",
        param_type: str = "text",
        file_name: str = "",
        updated_at: Optional[float] = None,
    ):
        if not param_key:
            raise DomainValidationError("配置键不能为空")
        self.id = Identifier.of(param_key)
        self._param_key = param_key
        self._param_value = param_value or ""
        self._param_type = param_type or "text"
        self._file_name = file_name or ""
        self._updated_at = updated_at if updated_at is not None else time.time()
        self._domain_events = []
        self.version = 0

    @property
    def param_key(self) -> str:
        return self._param_key
    @property
    def param_value(self) -> str:
        return self._param_value
    @property
    def param_type(self) -> str:
        return self._param_type
    @property
    def file_name(self) -> str:
        return self._file_name

    def update_value(self, param_value: str, file_name: str = "") -> None:
        """更新配置值。"""
        self._param_value = param_value or ""
        if file_name:
            self._file_name = file_name
        self._updated_at = time.time()
        self.record_event(DisplayConfigUpdated(self._param_key))

    def to_dict(self) -> dict:
        return {
            "paramKey": self._param_key,
            "paramValue": self._param_value,
            "type": self._param_type,
            "fileName": self._file_name,
        }

    @staticmethod
    def from_dict(data: dict) -> "DisplayConfigItem":
        return DisplayConfigItem(
            param_key=data.get("paramKey") or data.get("param_key") or "",
            param_value=data.get("paramValue") or "",
            param_type=data.get("type") or data.get("param_type") or "text",
            file_name=data.get("fileName") or data.get("file_name") or "",
            updated_at=data.get("updated_at") or data.get("update_time"),
        )
