"""展示配置聚合仓储实现。"""
from __future__ import annotations

from typing import List, Optional

from app.domain.display_config.domain.entities.display_item import DisplayConfigItem
from app.repositories.display_config_repo import display_config_repo


class DisplayRepoAdapter:
    """将既有 display_config_repo 封装为面向 DisplayConfigItem 的仓储。"""

    def save_many(self, items: List[DisplayConfigItem]) -> List[DisplayConfigItem]:
        data = [i.to_dict() for i in items]
        display_config_repo.save_many(data)
        return items

    def get_all(self) -> List[DisplayConfigItem]:
        rows = display_config_repo.get_all()
        return [DisplayConfigItem.from_dict(r) for r in rows]

    def get_by_key(self, key: str) -> Optional[DisplayConfigItem]:
        row = display_config_repo.get_by_key(key)
        return DisplayConfigItem.from_dict(row) if row else None

    def delete_by_key(self, key: str) -> None:
        display_config_repo.delete_by_key(key)
