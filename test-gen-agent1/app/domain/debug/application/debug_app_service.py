"""调试应用服务（Application Service / Use Case 门面）。"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.debug.application.dto import (
    DeleteDebugItemCommand,
    GetDebugItemCommand,
    SaveDebugItemCommand,
)
from app.domain.debug.domain.entities.debug_item import DebugItem
from app.domain.debug.infrastructure.debug_repository_impl import DebugRepoAdapter


class DebugAppService:
    """调试用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or DebugRepoAdapter()

    def get(self, cmd: GetDebugItemCommand) -> Optional[dict]:
        item = self._repo.get(cmd.debug_id)
        return item.to_dict() if item else None

    def save(self, cmd: SaveDebugItemCommand) -> dict:
        debug_id = cmd.debug_id or str(uuid.uuid4().hex[:12])
        item = DebugItem(
            debug_id=debug_id,
            name=cmd.name, protocol=cmd.protocol, method=cmd.method,
            path=cmd.path, url=cmd.url,
            project_id=cmd.project_id, module_id=cmd.module_id,
            request_data=cmd.request_data, response_data=cmd.response_data,
            create_user=cmd.create_user, update_user=cmd.update_user,
            num=cmd.num,
        )
        saved = self._repo.save(item)
        return saved.to_dict()

    def list_all(self) -> list:
        items = self._repo.list_all()
        return [i.to_dict() for i in items]

    def delete(self, cmd: DeleteDebugItemCommand) -> bool:
        return self._repo.delete(cmd.debug_id)


debug_app_service = DebugAppService()
