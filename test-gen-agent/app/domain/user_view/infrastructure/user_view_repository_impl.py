"""用户视图聚合仓储实现。"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.user_view.domain.entities.user_view import UserView
from app.repositories.user_view_repo import user_view_repo


class UserViewRepoAdapter:
    """将既有 user_view_repo 封装为面向 UserView 的仓储。"""

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def save(self, view: UserView) -> UserView:
        existing = self.get(view.id.value)
        if existing:
            user_view_repo.update_custom_view(view.id.value, view.payload)
        else:
            user_view_repo.add_custom_view(
                view.view_type, view.scope_id, view.payload,
                user_id=view.user_id, new_id=view.id.value,
            )
        return view

    def get(self, view_id: str) -> Optional[UserView]:
        row = user_view_repo.get_custom_view(view_id)
        return UserView.from_dict(dict(row)) if row else None

    def list_by_type(self, view_type: str, scope_id: str = "") -> List[UserView]:
        rows = user_view_repo.list_custom_views(view_type, scope_id)
        return [UserView.from_dict(dict(r)) for r in rows]

    def delete(self, view_id: str) -> bool:
        return user_view_repo.delete_custom_view(view_id)
