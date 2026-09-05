"""接口调试聚合根 DebugItem（调试暂存数据）。"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import time_from_row
from app.domain.debug.domain.events import DebugItemCreated, DebugItemUpdated


class DebugItem(AggregateRoot):
    """接口调试数据项聚合根。"""

    def __init__(
        self,
        *,
        debug_id: str,
        name: str = "未命名调试",
        protocol: str = "HTTP",
        method: str = "GET",
        path: str = "/",
        url: str = "/",
        project_id: str = "",
        module_id: str = "root",
        request_data: Optional[dict] = None,
        response_data: Optional[dict] = None,
        create_user: str = "admin",
        update_user: str = "admin",
        num: int = 0,
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not debug_id:
            raise DomainValidationError("调试 ID 不能为空")
        self.id = Identifier.of(debug_id)
        self._name = name or "未命名调试"
        self._protocol = protocol or "HTTP"
        self._method = method or "GET"
        self._path = path or "/"
        self._url = url or path or "/"
        self._project_id = project_id or ""
        self._module_id = module_id or "root"
        self._request_data = dict(request_data or {})
        self._response_data = dict(response_data or {})
        self._create_user = create_user or "admin"
        self._update_user = update_user or "admin"
        self._num = int(num or 0)
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(DebugItemCreated(self.id.value, self._name))

    @property
    def name(self) -> str:
        return self._name
    @property
    def protocol(self) -> str:
        return self._protocol
    @property
    def method(self) -> str:
        return self._method
    @property
    def path(self) -> str:
        return self._path
    @property
    def url(self) -> str:
        return self._url
    @property
    def project_id(self) -> str:
        return self._project_id
    @property
    def module_id(self) -> str:
        return self._module_id
    @property
    def request_data(self) -> dict:
        return dict(self._request_data)
    @property
    def response_data(self) -> dict:
        return dict(self._response_data)

    def update_request(self, request_data: Dict[str, Any]) -> None:
        """更新请求数据。"""
        self._request_data = dict(request_data or {})
        self._touch()
        self.record_event(DebugItemUpdated(self.id.value))

    def update_response(self, response_data: Dict[str, Any]) -> None:
        """更新响应数据。"""
        self._response_data = dict(response_data or {})
        self._touch()
        self.record_event(DebugItemUpdated(self.id.value))

    def _touch(self) -> None:
        self._update_time = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "protocol": self._protocol,
            "method": self._method,
            "path": self._path,
            "url": self._url,
            "projectId": self._project_id,
            "moduleId": self._module_id,
            "request": self._request_data,
            "response": self._response_data,
            "createTime": int(self._create_time * 1000),
            "updateTime": int(self._update_time * 1000),
            "createUser": self._create_user,
            "updateUser": self._update_user,
            "num": self._num,
        }

    @staticmethod
    def from_dict(data: dict) -> "DebugItem":
        return DebugItem(
            debug_id=str(data.get("id") or ""),
            name=data.get("name", ""),
            protocol=data.get("protocol", "HTTP"),
            method=data.get("method", "GET"),
            path=data.get("path", "/"),
            url=data.get("url", data.get("path", "/")),
            project_id=data.get("projectId", "") or data.get("project_id", ""),
            module_id=data.get("moduleId", "root") or data.get("module_id", "root"),
            request_data=data.get("request") or data.get("request_data") or {},
            response_data=data.get("response") or data.get("response_data") or {},
            create_user=data.get("createUser", "admin"),
            update_user=data.get("updateUser", "admin"),
            num=data.get("num", 0),
            create_time=time_from_row(data, "create_time", "createTime"),
            update_time=time_from_row(data, "update_time", "updateTime"),
        )
