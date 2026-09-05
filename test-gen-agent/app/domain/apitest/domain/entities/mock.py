"""Mock 服务聚合根 ApiMock。

聚合边界内的组成：
  - ApiMock（聚合根）
  - 值对象：HttpMethod / match_type / active 状态

职责：守护 Mock 服务完整性与业务不变量（名称非空、method/path 合法、
启用状态切换）。所有变更经由聚合根方法触发。

底层数据表：api_mocks。
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Optional

from app.domain.apitest.domain.events import (
    MockActiveChanged,
    MockCreated,
    MockRestored,
    MockSoftDeleted,
    MockUpdated,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError

_VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
_VALID_MATCH_TYPES = {"exact", "path", "wildcard", "script"}


class ApiMock(AggregateRoot):
    """Mock 服务聚合根。"""

    def __init__(
        self,
        *,
        mock_id: str,
        name: str,
        api_definition_id: str = "",
        method: str = "GET",
        path: str = "",
        status_code: int = 200,
        response_body: str = "",
        response_headers: Optional[dict] = None,
        delay_ms: int = 0,
        active: int = 1,
        description: str = "",
        project_id: str = "",
        match_type: str = "exact",
        match_script: str = "",
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        deleted: bool = False,
        _created: bool = False,
    ):
        if not (name or "").strip():
            raise DomainValidationError("Mock 服务名称不能为空")
        m = (method or "GET").strip().upper()
        if m not in _VALID_METHODS:
            raise DomainValidationError(f"非法请求方法: {method}")
        if match_type not in _VALID_MATCH_TYPES:
            raise DomainValidationError(
                f"非法匹配类型 '{match_type}'，仅支持 {sorted(_VALID_MATCH_TYPES)}"
            )
        self.id = Identifier.of(mock_id)
        self._name = (name or "").strip()
        self._api_definition_id = api_definition_id or ""
        self._method = m
        self._path = path or ""
        self._status_code = int(status_code or 200)
        self._response_body = response_body or ""
        self._response_headers = dict(response_headers or {})
        self._delay_ms = int(delay_ms or 0)
        self._active = bool(active)
        self._description = description or ""
        self._project_id = project_id or ""
        self._match_type = match_type or "exact"
        self._match_script = match_script or ""
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._deleted = bool(deleted)
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(MockCreated(self.id.value, self._name))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def api_definition_id(self) -> str:
        return self._api_definition_id

    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def response_body(self) -> str:
        return self._response_body

    @property
    def response_headers(self) -> dict:
        return dict(self._response_headers)

    @property
    def delay_ms(self) -> int:
        return self._delay_ms

    @property
    def active(self) -> bool:
        return self._active

    @property
    def description(self) -> str:
        return self._description

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def match_type(self) -> str:
        return self._match_type

    @property
    def match_script(self) -> str:
        return self._match_script

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def deleted(self) -> bool:
        return self._deleted

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str) -> None:
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("Mock 服务名称不能为空")
        if nn != self._name:
            self._name = nn
            self._touch()
            self.record_event(MockUpdated(self.id.value, self._name))

    def change_active(self, active: bool) -> None:
        """切换 Mock 启用/禁用状态。"""
        if bool(active) == self._active:
            return
        old = self._active
        self._active = bool(active)
        self._touch()
        self.record_event(MockActiveChanged(self.id.value, old, self._active))

    def set_content(
        self,
        *,
        name: Optional[str] = None,
        api_definition_id: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        response_headers: Optional[dict] = None,
        delay_ms: Optional[int] = None,
        active: Optional[int] = None,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        match_type: Optional[str] = None,
        match_script: Optional[str] = None,
    ) -> None:
        """原子更新 Mock 内容（聚合内校验 + 更新）。"""
        if name is not None:
            self.rename(name)
        if api_definition_id is not None:
            self._api_definition_id = api_definition_id or ""
        if method is not None:
            m = (method or "GET").strip().upper()
            if m not in _VALID_METHODS:
                raise DomainValidationError(f"非法请求方法: {method}")
            self._method = m
        if path is not None:
            self._path = path or ""
        if status_code is not None:
            self._status_code = int(status_code or 200)
        if response_body is not None:
            self._response_body = response_body or ""
        if response_headers is not None:
            self._response_headers = dict(response_headers or {})
        if delay_ms is not None:
            self._delay_ms = int(delay_ms or 0)
        if active is not None:
            self._active = bool(active)
        if description is not None:
            self._description = description or ""
        if project_id is not None:
            self._project_id = project_id or ""
        if match_type is not None:
            if match_type not in _VALID_MATCH_TYPES:
                raise DomainValidationError(
                    f"非法匹配类型 '{match_type}'，仅支持 {sorted(_VALID_MATCH_TYPES)}"
                )
            self._match_type = match_type
        if match_script is not None:
            self._match_script = match_script or ""
        self._touch()
        self.record_event(MockUpdated(self.id.value, self._name))

    def delete(self) -> None:
        """软删除进入回收站。"""
        if self._deleted:
            raise DomainValidationError("Mock 服务已在回收站，不可重复删除")
        self._deleted = True
        self._touch()
        self.record_event(MockSoftDeleted(self.id.value))

    def restore(self) -> None:
        """从回收站恢复。"""
        if not self._deleted:
            raise DomainValidationError("Mock 服务不在回收站，无需恢复")
        self._deleted = False
        self._touch()
        self.record_event(MockRestored(self.id.value))

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库/返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "api_definition_id": self._api_definition_id,
            "method": self._method,
            "path": self._path,
            "status_code": self._status_code,
            "response_body": self._response_body,
            "response_headers": dict(self._response_headers),
            "delay_ms": self._delay_ms,
            "active": 1 if self._active else 0,
            "description": self._description,
            "project_id": self._project_id,
            "match_type": self._match_type,
            "match_script": self._match_script,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "deleted": 1 if self._deleted else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "ApiMock":
        """从持久化字典/仓储返回行重建聚合。"""
        def _load_str(v, default=None):
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    return default
            return v or default

        headers = _load_str(data.get("response_headers"), {})
        if not isinstance(headers, dict):
            headers = {}
        return ApiMock(
            mock_id=str(data.get("id") or data.get("mock_id") or ""),
            name=data.get("name", ""),
            api_definition_id=data.get("api_definition_id", ""),
            method=data.get("method", "GET"),
            path=data.get("path", ""),
            status_code=data.get("status_code", 200),
            response_body=data.get("response_body", ""),
            response_headers=headers,
            delay_ms=data.get("delay_ms", 0),
            active=data.get("active", 1),
            description=data.get("description", ""),
            project_id=data.get("project_id", ""),
            match_type=data.get("match_type", "exact"),
            match_script=data.get("match_script", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted=bool(data.get("deleted", 0)),
        )
