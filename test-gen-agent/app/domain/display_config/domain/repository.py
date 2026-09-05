"""展示配置聚合仓储接口。"""
from __future__ import annotations

from typing import List, Optional, Protocol

from app.domain.display_config.domain.entities.display_item import DisplayConfigItem


class DisplayConfigRepository(Protocol):
    """展示配置仓储契约。"""
    def save_many(self, items: List[DisplayConfigItem]) -> List[DisplayConfigItem]: ...
    def get_all(self) -> List[DisplayConfigItem]: ...
    def get_by_key(self, key: str) -> Optional[DisplayConfigItem]: ...
    def delete_by_key(self, key: str) -> None: ...

__all__ = ["DisplayConfigRepository"]
