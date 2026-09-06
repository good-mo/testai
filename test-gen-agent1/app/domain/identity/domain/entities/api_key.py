"""API Key 子实体。

属于 User 聚合边界内的子实体（无独立仓储生命周期，随用户聚合读写）。
承载 API Key 的启用/吊销状态与最后使用时间。
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import Entity, Identifier


class ApiKey(Entity):
    """个人 API 密钥子实体。"""

    def __init__(
        self,
        *,
        key_id: str,
        user_id: str,
        description: str = "",
        api_key: str = "",
        enable: int = 1,
        created_at: Optional[float] = None,
        last_used_at: Optional[float] = None,
    ):
        self.id = Identifier.of(key_id)
        self._user_id = user_id or ""
        self._description = description or ""
        self._api_key = api_key or ""
        self._enable = int(enable) if enable is not None else 1
        self._created_at = created_at if created_at is not None else time.time()
        self._last_used_at = last_used_at
        self._domain_events = []

    # ── 只读属性 ─────────────────────────────────────
    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def description(self) -> str:
        return self._description

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def enabled(self) -> bool:
        return self._enable == 1

    @property
    def revoked(self) -> bool:
        return self._enable != 1

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def last_used_at(self) -> float:
        return self._last_used_at

    # ── 业务命令 ─────────────────────────────────────
    def rename(self, description: str) -> None:
        self._description = description or ""

    def revoke(self) -> None:
        self._enable = 0

    def enable(self) -> None:
        self._enable = 1

    def mark_used(self) -> None:
        self._last_used_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "user_id": self._user_id,
            "description": self._description,
            "api_key": self._api_key,
            "enable": self._enable,
            "created_at": self._created_at,
            "last_used_at": self._last_used_at,
        }
