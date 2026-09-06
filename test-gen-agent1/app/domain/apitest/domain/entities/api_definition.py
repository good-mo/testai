"""接口定义聚合根 ApiDefinition。

聚合边界内的组成：
  - ApiDefinition（聚合根）
  - 值对象：Protocol / HttpMethod / tags

职责：守护接口定义完整性与业务不变量（名称非空、协议/方法合法等）。
所有变更必须经由聚合根方法触发，业务命令在校验通过后记录领域事件，
供应用层落库 + 发布，从而与审计/版本/通知等副作用解耦。

底层数据表：api_definitions。
"""
from __future__ import annotations

import json
import time
from typing import List, Optional

from app.domain.apitest.domain.events import (
    ApiDefinitionRenamed,
    ApiDefinitionRestored,
    ApiDefinitionSoftDeleted,
    ApiDefinitionUpdated,
    ApiDefinitionVersionCreated,
)
from app.domain.apitest.domain.value_objects.protocol import Protocol, ProtocolEnum
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError


class ApiDefinition(AggregateRoot):
    """接口定义聚合根。"""

    def __init__(
        self,
        *,
        definition_id: str,
        name: str,
        protocol: str = ProtocolEnum.HTTP.value,
        method: str = "GET",
        path: str = "",
        headers: Optional[dict] = None,
        body: str = "",
        query: Optional[dict] = None,
        params: Optional[dict] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        module_id: str = "",
        project_id: str = "",
        version_id: str = "",
        ref_id: str = "",
        latest: bool = True,
        metadata: Optional[dict] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        deleted: bool = False,
    ):
        if not (name or "").strip():
            raise DomainValidationError("接口名称不能为空")
        self.id = Identifier.of(definition_id)
        self._name = (name or "").strip()
        self._protocol = Protocol(protocol)
        self._method = (method or "GET").upper()
        self._path = path or ""
        self._headers = dict(headers or {})
        self._body = body or ""
        self._query = dict(query or {})
        self._params = dict(params or {})
        self._description = description or ""
        self._tags = list(tags or [])
        self._module_id = module_id or ""
        self._project_id = project_id or ""
        self._version_id = version_id or ""
        self._ref_id = ref_id or ""
        self._latest = bool(latest)
        self._metadata = dict(metadata or {})
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._deleted = bool(deleted)
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def protocol(self) -> Protocol:
        return self._protocol

    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path

    @property
    def headers(self) -> dict:
        return dict(self._headers)

    @property
    def body(self) -> str:
        return self._body

    @property
    def query(self) -> dict:
        return dict(self._query)

    @property
    def params(self) -> dict:
        return dict(self._params)

    @property
    def description(self) -> str:
        return self._description

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def module_id(self) -> str:
        return self._module_id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def version_id(self) -> str:
        return self._version_id

    @property
    def ref_id(self) -> str:
        return self._ref_id

    @property
    def latest(self) -> bool:
        return self._latest

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

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
    def rename(self, new_name: str, operator: str = "system") -> None:
        """修改接口定义名称。"""
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("接口名称不能为空")
        if nn == self._name:
            return
        old = self._name
        self._name = nn
        self._touch()
        self.record_event(ApiDefinitionRenamed(self.id.value, old, nn, operator))

    def change_protocol(self, protocol: str, operator: str = "system") -> None:
        self._protocol = Protocol(protocol)
        self._touch()
        self.record_event(ApiDefinitionUpdated(self.id.value, self._name, operator))

    def change_method(self, method: str, operator: str = "system") -> None:
        if not (method or "").strip():
            raise DomainValidationError("请求方法不能为空")
        self._method = method.strip().upper()
        self._touch()
        self.record_event(ApiDefinitionUpdated(self.id.value, self._name, operator))

    def change_path(self, path: str, operator: str = "system") -> None:
        self._path = path or ""
        self._touch()
        self.record_event(ApiDefinitionUpdated(self.id.value, self._name, operator))

    def set_content(
        self,
        *,
        name: Optional[str] = None,
        protocol: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
        query: Optional[dict] = None,
        params: Optional[dict] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        module_id: Optional[str] = None,
        operator: str = "system",
    ) -> None:
        """原子更新接口定义内容（聚合内校验 + 更新）。"""
        if name is not None:
            self.rename(name, operator)
        if protocol is not None:
            self._protocol = Protocol(protocol)
        if method is not None:
            self._method = (method or "GET").upper()
        if path is not None:
            self._path = path or ""
        if headers is not None:
            self._headers = dict(headers)
        if body is not None:
            self._body = body or ""
        if query is not None:
            self._query = dict(query)
        if params is not None:
            self._params = dict(params)
        if description is not None:
            self._description = description or ""
        if tags is not None:
            self._tags = list(tags)
        if module_id is not None:
            self._module_id = module_id or ""
        self._touch()
        self.record_event(ApiDefinitionUpdated(self.id.value, self._name, operator))

    def delete(self, operator: str = "system", reason: str = "") -> None:
        """软删除进入回收站。"""
        if self._deleted:
            raise DomainValidationError("接口定义已在回收站，不可重复删除")
        self._deleted = True
        self._touch()
        self.record_event(ApiDefinitionSoftDeleted(self.id.value, operator, reason))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复。"""
        if not self._deleted:
            raise DomainValidationError("接口定义不在回收站，无需恢复")
        self._deleted = False
        self._touch()
        self.record_event(ApiDefinitionRestored(self.id.value, operator))

    def create_version(self, version: str = "", operator: str = "system") -> None:
        """标记为创建新版本（事件由应用层驱动版本表落库）。"""
        self._touch()
        self.record_event(ApiDefinitionVersionCreated(self.id.value, version, operator))

    # ── 持久化 ───────────────────────────────────────
    def to_dict(self) -> dict:
        """导出可落库/返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "protocol": self._protocol.value.value,
            "method": self._method,
            "path": self._path,
            "headers": dict(self._headers),
            "body": self._body,
            "query": dict(self._query),
            "params": dict(self._params),
            "description": self._description,
            "tags": list(self._tags),
            "module_id": self._module_id,
            "project_id": self._project_id,
            "version_id": self._version_id,
            "ref_id": self._ref_id,
            "latest": 1 if self._latest else 0,
            "metadata": dict(self._metadata),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "deleted": 1 if self._deleted else 0,
        }

    @staticmethod
    def from_dict(data: dict) -> "ApiDefinition":
        """从持久化字典/仓储返回行重建聚合。"""
        # 反序列化 JSON 字符串字段
        def _load_str(v, default=None):
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    return default
            return v or default

        headers = _load_str(data.get("headers"), {})
        query = _load_str(data.get("query"), {})
        params = _load_str(data.get("params"), {})
        tags = _load_str(data.get("tags"), [])
        metadata = _load_str(data.get("metadata"), {})

        return ApiDefinition(
            definition_id=str(data.get("id") or data.get("definition_id") or ""),
            name=data.get("name", ""),
            protocol=data.get("protocol", ProtocolEnum.HTTP.value),
            method=data.get("method", "GET"),
            path=data.get("path", ""),
            headers=headers if isinstance(headers, dict) else {},
            body=data.get("body", ""),
            query=query if isinstance(query, dict) else {},
            params=params if isinstance(params, dict) else {},
            description=data.get("description", ""),
            tags=tags if isinstance(tags, list) else [],
            module_id=data.get("module_id", ""),
            project_id=data.get("project_id", ""),
            version_id=data.get("version_id", ""),
            ref_id=data.get("ref_id", ""),
            latest=bool(data.get("latest", 1)),
            metadata=metadata if isinstance(metadata, dict) else {},
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            deleted=bool(data.get("deleted", 0)),
        )
