"""资源池应用服务。"""
from __future__ import annotations

from typing import Optional

from app.domain.resource_pool.application.dto import (
    CreatePoolCommand,
    DeletePoolCommand,
    GetPoolCommand,
    ListPoolsCommand,
    SetEnableCommand,
    UpdatePoolCommand,
)
from app.domain.resource_pool.domain.entities.resource_pool import ResourcePool
from app.domain.resource_pool.domain.exceptions import ResourcePoolNotFound
from app.domain.resource_pool.infrastructure.resource_pool_repo_impl import (
    ResourcePoolRepoAdapter,
)


class ResourcePoolAppService:
    """资源池用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or ResourcePoolRepoAdapter()

    def create(self, cmd: CreatePoolCommand) -> dict:
        pool = ResourcePool(
            pool_id=self._repo.next_id(),
            name=cmd.name,
            description=cmd.description,
            enable=cmd.enable,
            _created=True,
        )
        saved = self._repo.save(pool)
        return saved.to_dict()

    def list(self, cmd: ListPoolsCommand) -> list:
        pools = self._repo.list(cmd.keyword)
        return [p.to_dict() for p in pools]

    def get(self, cmd: GetPoolCommand) -> Optional[dict]:
        pool = self._repo.get(cmd.pool_id)
        return pool.to_dict() if pool else None

    def update(self, cmd: UpdatePoolCommand) -> bool:
        pool = self._repo.get(cmd.pool_id)
        if not pool:
            raise ResourcePoolNotFound(f"资源池 {cmd.pool_id} 不存在")
        pool.update(name=cmd.name, description=cmd.description)
        self._repo.save(pool)
        return True

    def delete(self, cmd: DeletePoolCommand) -> bool:
        return self._repo.delete(cmd.pool_id)

    def set_enable(self, cmd: SetEnableCommand) -> bool:
        return self._repo.set_enable(cmd.pool_id, cmd.enable)


resource_pool_app_service = ResourcePoolAppService()
