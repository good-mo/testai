"""资源池聚合仓储实现。"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.resource_pool.domain.entities.resource_pool import ResourcePool
from app.repositories.resource_pool_repo import ResourcePoolRepo


class ResourcePoolRepoAdapter:
    """将既有 ResourcePoolRepo 封装为面向 ResourcePool 的仓储。"""

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def save(self, pool: ResourcePool) -> ResourcePool:
        existing = self.get(pool.id.value)
        if existing:
            ResourcePoolRepo.update(
                pool.id.value,
                {"name": pool.name, "description": pool.description,
                 "enable": pool.enable},
            )
        else:
            # 新建时以聚合根的 id 落库，保证返回 id == 落库 id（修复双 id 漂移缺陷）
            ResourcePoolRepo.create(
                name=pool.name, description=pool.description,
                enable=pool.enable, pool_id=pool.id.value,
            )
        return pool

    def get(self, pool_id: str) -> Optional[ResourcePool]:
        row = ResourcePoolRepo.get_by_id(pool_id)
        return ResourcePool.from_dict(dict(row)) if row else None

    def list(self, keyword: str = "") -> List[ResourcePool]:
        rows = ResourcePoolRepo.get_all(keyword=keyword)
        return [ResourcePool.from_dict(dict(r)) for r in rows]

    def delete(self, pool_id: str) -> bool:
        return ResourcePoolRepo.delete(pool_id)

    def set_enable(self, pool_id: str, enable: bool) -> bool:
        return ResourcePoolRepo.set_enable(pool_id, enable)
