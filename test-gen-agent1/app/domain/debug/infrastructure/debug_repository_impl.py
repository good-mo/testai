"""调试聚合仓储实现（Adapter / Anti-Corruption Layer）。"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.debug.domain.entities.debug_item import DebugItem
from app.repositories.debug_repo import DebugRepo


class DebugRepoAdapter:
    """将既有 DebugRepo 封装为面向 DebugItem 聚合的仓储。"""

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def save(self, item: DebugItem) -> DebugItem:
        data = item.to_dict()
        DebugRepo.save(data)
        return item

    def get(self, debug_id: str) -> Optional[DebugItem]:
        rows = DebugRepo.load_all()
        for r in rows:
            if r.get("id") == debug_id:
                return DebugItem.from_dict(r)
        return None

    def list_all(self) -> List[DebugItem]:
        rows = DebugRepo.load_all()
        return [DebugItem.from_dict(r) for r in rows]

    def delete(self, debug_id: str) -> bool:
        existed = self.get(debug_id) is not None
        DebugRepo.delete(debug_id)
        return existed
