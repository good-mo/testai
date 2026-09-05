"""用户自定义视图聚合根 UserView。"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.user_view.domain.events import (
    UserViewCreated,
    UserViewUpdated,
)


class UserView(AggregateRoot):
    """用户自定义视图聚合根。"""

    def __init__(
        self,
        *,
        view_id: str,
        view_type: str = "",
        scope_id: str = "",
        user_id: str = "admin",
        name: str = "",
        search_mode: str = "AND",
        pos: int = 0,
        payload: Optional[dict] = None,
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not view_id:
            raise DomainValidationError("视图 ID 不能为空")
        if not view_type:
            raise DomainValidationError("视图类型不能为空")
        self.id = Identifier.of(view_id)
        self._view_type = view_type
        self._scope_id = scope_id or ""
        self._user_id = user_id or "admin"
        self._name = name or ""
        self._search_mode = search_mode or "AND"
        self._pos = int(pos or 0)
        self._payload = dict(payload or {})
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(UserViewCreated(self.id.value, self._name, self._view_type))

    @property
    def view_type(self) -> str:
        return self._view_type
    @property
    def scope_id(self) -> str:
        return self._scope_id
    @property
    def user_id(self) -> str:
        return self._user_id
    @property
    def name(self) -> str:
        return self._name
    @property
    def search_mode(self) -> str:
        return self._search_mode
    @property
    def pos(self) -> int:
        return self._pos
    @property
    def payload(self) -> dict:
        return dict(self._payload)

    def rename(self, name: str) -> None:
        """重命名视图。"""
        self._name = name or ""
        self._payload["name"] = self._name
        self._touch()

    def update_body(self, body: Dict[str, Any]) -> None:
        """更新视图完整字段（合并更新）。"""
        merged = dict(self._payload)
        for k, v in (body or {}).items():
            merged[k] = v
        self._payload = merged
        if "name" in merged:
            self._name = merged["name"] or ""
        if "searchMode" in merged:
            self._search_mode = merged["searchMode"] or "AND"
        if "pos" in merged:
            self._pos = int(merged["pos"] or 0)
        self._touch()
        self.record_event(UserViewUpdated(self.id.value))

    def _touch(self) -> None:
        self._update_time = time.time()

    def to_dict(self) -> dict:
        """返回完整前端视图对象（聚合 meta + 自定义 payload 字段）。

        修复历史缺陷：此前只返回 payload，把 id / viewType / scopeId / userId
        等 meta 字段丢弃，导致落库读回的视图无法被前端识别与定位。现以聚合
        结构化字段为权威源，把 meta 合并进 payload 后整体返回；自定义筛选
        字段（conditions 等）保留在 payload 中一并带出。
        """
        obj = dict(self._payload)
        obj["id"] = self.id.value
        obj["viewType"] = self._view_type
        obj["scopeId"] = self._scope_id
        obj["userId"] = self._user_id
        obj["name"] = self._name
        obj["searchMode"] = self._search_mode
        obj["pos"] = self._pos
        obj["internal"] = False
        obj["createTime"] = self._create_time
        obj["updateTime"] = self._update_time
        return obj

    @staticmethod
    def from_dict(data: dict) -> "UserView":
        """从完整前端视图对象重建聚合（与 to_dict 对称）。

        兼容两种输入来源：
          - 完整前端视图对象（`id`/`viewType`/`scopeId`/`name`/`searchMode` 等
            camelCase meta + 自定义 payload 字段，createTime/updateTime 秒）；
          - DB 原始行（含 `view_type`/`scope_id` 等 snake_case 列，create_time 秒）。
        自定义 payload 字段（conditions 等）保留进聚合 payload，供 update 合并。
        """
        data = data or {}
        if "payload" in data and isinstance(data["payload"], dict) and "id" not in data:
            # DB 原始行：payload 列单独存 JSON，meta 在行级列
            payload = dict(data["payload"])
            obj = dict(payload)
            obj.setdefault("id", data.get("id"))
            obj.setdefault("viewType", data.get("view_type"))
            obj.setdefault("scopeId", data.get("scope_id"))
            obj.setdefault("userId", data.get("user_id"))
            obj.setdefault("name", data.get("name"))
            obj.setdefault("searchMode", data.get("search_mode"))
            obj.setdefault("pos", data.get("pos"))
            obj.setdefault("createTime", data.get("create_time"))
            obj.setdefault("updateTime", data.get("update_time"))
            merged = obj
        else:
            merged = dict(data)

        view_id = str(merged.get("id") or data.get("id") or "")
        view_type = str(merged.get("viewType") or data.get("view_type") or data.get("viewType") or "")
        scope_id = str(merged.get("scopeId") or data.get("scope_id") or "")
        user_id = str(merged.get("userId") or data.get("user_id") or "admin")
        name = str(merged.get("name", "") or "")
        search_mode = str(merged.get("searchMode") or data.get("search_mode") or "AND")
        pos = int(merged.get("pos", 0) or 0)

        create_time = data.get("create_time")
        if create_time is None:
            ct = merged.get("createTime")
            create_time = ct if isinstance(ct, (int, float)) else None
        update_time = data.get("update_time")
        if update_time is None:
            ut = merged.get("updateTime")
            update_time = ut if isinstance(ut, (int, float)) else None

        return UserView(
            view_id=view_id,
            view_type=view_type,
            scope_id=scope_id,
            user_id=user_id,
            name=name,
            search_mode=search_mode,
            pos=pos,
            payload=merged,
            create_time=create_time,
            update_time=update_time,
        )
