"""调试聚合仓储接口。"""
from __future__ import annotations

from typing import List, Optional, Protocol

from app.domain.debug.domain.entities.debug_item import DebugItem


class DebugRepository(Protocol):
    """调试聚合仓储契约。"""
    def next_id(self) -> str: ...
    def save(self, item: DebugItem) -> DebugItem: ...
    def get(self, debug_id: str) -> Optional[DebugItem]: ...
    def list_all(self) -> List[DebugItem]: ...
    def delete(self, debug_id: str) -> bool: ...

__all__ = ["DebugRepository"]
