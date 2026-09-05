"""用户视图应用服务。"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.user_view.application.dto import (
    CreateUserViewCommand,
    DeleteUserViewCommand,
    GetUserViewCommand,
    ListUserViewsCommand,
    UpdateUserViewCommand,
)
from app.domain.user_view.domain.entities.user_view import UserView
from app.domain.user_view.domain.exceptions import UserViewNotFound
from app.domain.user_view.infrastructure.user_view_repository_impl import (
    UserViewRepoAdapter,
)


class UserViewAppService:
    """用户视图用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or UserViewRepoAdapter()

    def list_custom_views(self, cmd: ListUserViewsCommand) -> list:
        views = self._repo.list_by_type(cmd.view_type, cmd.scope_id)
        return [v.to_dict() for v in views]

    def get(self, cmd: GetUserViewCommand) -> Optional[dict]:
        v = self._repo.get(cmd.view_id)
        return v.to_dict() if v else None

    def create(self, cmd: CreateUserViewCommand) -> dict:
        view = UserView(
            view_id=cmd.new_id or str(uuid.uuid4()),
            view_type=cmd.view_type,
            scope_id=cmd.scope_id,
            user_id=cmd.user_id,
            name=cmd.body.get("name", ""),
            search_mode=cmd.body.get("searchMode", "AND"),
            payload=cmd.body,
            _created=True,
        )
        saved = self._repo.save(view)
        return saved.to_dict()

    def update(self, cmd: UpdateUserViewCommand) -> Optional[dict]:
        view = self._repo.get(cmd.view_id)
        if not view:
            raise UserViewNotFound(f"视图 {cmd.view_id} 不存在")
        view.update_body(cmd.body)
        saved = self._repo.save(view)
        return saved.to_dict()

    def delete(self, cmd: DeleteUserViewCommand) -> bool:
        return self._repo.delete(cmd.view_id)


user_view_app_service = UserViewAppService()
